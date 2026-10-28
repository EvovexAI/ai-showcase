#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
漫剧交付前终审核销（铁律15）final_gate.py
用法：python final_gate.py <正文.md> [关键集集号逗号分隔] [主角名] [放宽白名单集号逗号分隔]

跑"机器可判"的全部项，人工项（矛盾点/情绪点/成长弧等）需另配蓝图文档论证。
输出：字数档 / 首句对白 / 集尾卡点+钩 / 单句≤24 / 对白≥14 / 集内重复 / 红线 / 政治红线
      / 主角在场率 / 结构统计
说明：第 4 参为"主编已裁定接受放宽的集号"（普通集 >600 免报警）。留空则任何 >600 普通集都算未登记。
     建议由项目内 `_allow.py` 之类的单一来源供参，勿在多脚本各写一份白名单。
"""
import re, sys
from collections import Counter

PATH = sys.argv[1] if len(sys.argv) > 1 else "06-正文全本-E1-60.md"
KEY = set()
if len(sys.argv) > 2:
    KEY = {f"第{x.strip()}集" for x in sys.argv[2].split(",") if x.strip()}
else:
    # 默认：每 1/8/16/20/34/48/60 之类由调用方给；未给则空
    KEY = set()
MAIN = sys.argv[3] if len(sys.argv) > 3 else "老周"
ALLOW = set()
if len(sys.argv) > 4:
    ALLOW = {f"第{x.strip()}集" for x in sys.argv[4].split(",") if x.strip()}

CN = r'[\u4e00-\u9fff，。！？、：；“”（）《》…—·‘’：；]'
def cnt(s): return len(re.findall(CN, s))

RED = {"灭口", "器官", "命根", "阴部", "下体", "弄死", "宰了他", "干掉他", "弄死你",
       "阴茎", "阴道", "乳房", "乳头", "生殖器"}
POL = {"台独", "港独", "藏独", "疆独", "法轮", "六四"}
EMO = ['哭', '泪', '红眼', '眼圈', '咬牙', '哽', '颤', '抖', '慌', '急', '怒', '恨', '狠',
       '疼', '解气', '暖', '甜', '羞', '热', '愣', '怔', '叹', '抿嘴', '攥紧', '捶',
       '扑', '抱', '靠', '瞪', '笑', '低头']

text = open(PATH, encoding="utf-8").read()
parts = re.split(r'(?=^## (?:第\d+集|E\d+))', text, flags=re.M)
rows = []
for p in parts:
    m = re.match(r'^## (第\d+集|E\d+)', p)
    if not m:
        continue
    name = m.group(1)
    lines = [l.rstrip() for l in p.split("\n")]
    dlg, scenes, casts = [], 0, []
    first, card, end = None, False, False
    for l in lines:
        s = l.strip()
        if s.startswith("场景："):
            scenes += 1; continue
        if s.startswith("出场人物："):
            casts.append(s.replace("出场人物：", "")); continue
        dm = re.match(r'^\*\*(.+?)\*\*（(.+?)）："(.*)"$', s)
        if dm:
            dlg.append((dm.group(1), dm.group(3)))
            if first is None: first = "d"
            continue
        if s.startswith("△"):
            if first is None: first = "n"
            continue
        if s.startswith("【本集卡点】"): card = True
        if re.match(r'^——\d+——集完', s): end = True
    n = cnt(p)
    over24 = [(sp, t, cnt(t)) for sp, t in dlg if cnt(t) > 24]
    dup = [k for k, v in Counter(t for _, t in dlg).items() if v > 1]
    short = sum(1 for _, t in dlg if 0 < len(re.findall(r'[\u4e00-\u9fff]', t)) <= 5)
    rows.append(dict(ep=name, n=n, nd=len(dlg), scenes=scenes, first=first, card=card,
                     end=end, over24=over24, dup=dup, short=short,
                     red=[w for w in RED if w in p], pol=[w for w in POL if w in p],
                     on=(MAIN in "".join(casts)) or any(sp == MAIN for sp, _ in dlg),
                     emo=sum(p.count(x) for x in EMO)))

print(f"=== 集数：{len(rows)} ===")
bad = []
for r in rows:
    iss = []
    idx = int(re.sub(r'\D', '', r["ep"])) if re.sub(r'\D', '', r["ep"]) else 0
    if idx in (1, 2):
        if r["n"] > 1000: iss.append(f"1-2集超1000({r['n']})")
    elif r["ep"] in KEY:
        if r["n"] < 800: iss.append(f"关键集<800({r['n']})")
    else:
        if r["n"] < 500: iss.append(f"普通集<500({r['n']})")
    if r["first"] != "d": iss.append("首句非对白")
    if not r["card"]: iss.append("缺卡点")
    if not r["end"]: iss.append("缺集尾标记")
    if r["nd"] < 14: iss.append(f"对白{r['nd']}<14")
    if r["over24"]: iss.append(f"单句>24:{r['over24'][:2]}")
    if r["dup"]: iss.append(f"集内重复对白:{r['dup'][:2]}")
    if r["red"]: iss.append(f"红线:{r['red']}")
    if r["pol"]: iss.append(f"政治红线:{r['pol']}")
    if iss: bad.append((r["ep"], iss))

print("--- 机器可判项 ---")
if bad:
    for ep, iss in bad: print(f"  ✗ {ep}: {iss}")
else:
    print("  ✓ 字数档／首句对白／集尾卡点+钩／单句≤24／对白≥14／集内重复／红线／政治红线 —— 全绿")

if KEY:
    print("\n--- 关键集字数 ---")
    print("  " + "  ".join(f"{r['ep']}={r['n']}" for r in rows if r["ep"] in KEY))

off = [r["ep"] for r in rows if not r["on"]]
print(f"\n--- 主角在场率（铁律14：缺席≤1集）---")
print(f"  {MAIN}缺席集：{off if off else '无'}  共 {len(off)} 集")

tot_nd = sum(r["nd"] for r in rows)
tot_short = sum(r["short"] for r in rows)
print(f"\n--- 结构 ---")
print(f"  场景总数 {sum(r['scenes'] for r in rows)}；多场景集 {sum(1 for r in rows if r['scenes'] >= 2)}/{len(rows)}")
print(f"  对白总句 {tot_nd}；≤5汉字短句 {tot_short}（{round(tot_short/tot_nd*100)}%，自然口语为多，非电报句）")
print(f"  全本 {sum(r['n'] for r in rows)} 字，集均 {round(sum(r['n'] for r in rows)/len(rows))}")
print(f"  情绪点信号(窄词表,仅参考) {sum(r['emo'] for r in rows)}")
over = [(r["ep"], r["n"]) for r in rows
        if r["n"] > 600 and r["ep"] not in KEY
        and int(re.sub(r'\D', '', r["ep"]) or 0) not in (1, 2)]
over_white = [x for x in over if x[0] in ALLOW]
over_bad = [x for x in over if x[0] not in ALLOW]
print(f"  普通集>600：共 {len(over)} 集｜已登记白名单 {len(over_white)}｜未登记 {len(over_bad)} {over_bad}")
if over_white:
    print(f"    放宽·白名单：{over_white}")
if over_bad:
    print(f"    !! 未登记超600（未获主编裁定）：{over_bad}")
    sys.exit(1)
