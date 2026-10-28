# -*- coding: utf-8 -*-
"""73 剧本「写稿期离线预检」：直接复用 check53full.py 的函数，对**草稿文件**出逐集读数。
用途：写新集时先在草稿上跑到全绿，再追加进正文，避免反复改主文件。

用法：
    python3 _audit/pre73.py <草稿.md> [--expect-eps N]
"""
import importlib.util, io, os, re, sys

# ★可移植：检查器脚本 = 第 2 个位置参数；不给就自动找（cwd／脚本上级目录里的 check*full.py）
def _find_checker():
    import glob
    cands = []
    if len(sys.argv) > 2:
        cands.append(sys.argv[2])
    cands += glob.glob(os.path.join(os.getcwd(), "check*full.py"))
    cands += glob.glob(os.path.join(os.path.dirname(os.getcwd()), "check*full.py"))
    cands += [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "check53full.py")]
    for c in cands:
        if os.path.exists(c):
            return c
    sys.exit("❌ 找不到检查器脚本（check*full.py）—— 用法：pre_episode.py <草稿.md> [检查器.py]")
spec = importlib.util.spec_from_file_location("c53", _find_checker())
c53 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c53)

path = sys.argv[1]
if not os.path.isabs(path):
    path = os.path.join(os.getcwd(), path)
txt = io.open(path, encoding="utf-8").read()
eps = c53.split_eps(txt)
if not eps:
    sys.exit("❌ 未解析出任何集")

cfg = c53.load_params()
print("=" * 118)
print(f"草稿：{os.path.basename(path)} ｜ 已写集 {len(eps)}（第 {c53.ep_no(eps[0])}–{c53.ep_no(eps[-1])} 集）")
print("集    |  字 | 带     | 汉 | △行/汉 | 白行/汉 | 占比% | 均长 | 递进 | 强递 | 参考24 | 场 | 两行 | 三连 | 首尾 | 卡 | 达标")
print("-" * 118)
adv36_by_ep = {}
for e in eps:
    no, body = c53.ep_no(e), c53.body_of(e)
    raw = body.splitlines()
    ch = c53.content_chars(body)
    act_lines = [l for l in raw if c53.is_act(l)]
    act = len(act_lines)
    act_han = sum(c53.han_count(c53.QUOTE_RE.sub("", l)) for l in act_lines)
    dlg_lines = [l for l in raw if c53.is_dlg(l)]
    dlg = len(dlg_lines)
    texts = [c53.dlg_text(l) for l in dlg_lines]
    dlg_han = sum(c53.han_count(t) for t in texts)
    han = act_han + dlg_han
    ratio = dlg_han / han * 100 if han else 0
    avg = dlg_han / dlg if dlg else 0
    l24 = sum(1 for t in texts if c53.han_count(t) >= c53.REF24)
    seq = []
    for _l, _t in zip(dlg_lines, texts):
        m = c53.SPK_RE.search(_l)
        if m:
            seq.append((m.group(1), c53.han_count(_t)))
    selfn = adv = adv36 = 0
    i = 0
    while i < len(seq):
        j = i + 1
        while j < len(seq) and seq[j][0] == seq[i][0]:
            j += 1
        rl = j - i
        if rl >= 3:
            selfn += 1
        elif rl == 2:
            pair = seq[i][1] + seq[i + 1][1]
            if pair >= cfg["adv_pair_min"]:
                adv += 1
            if pair >= cfg["adv_pair36_min"]:
                adv36 += 1
        i = j
    adv36_by_ep[no] = adv36
    scene_n = len([l for l in raw if re.match(r"^\s*[-*+]*\s*\**场景\**\s*[：:]", l)])
    flag = []
    if not (cfg["guard_lo"] <= ch <= cfg["guard_hi"]):
        flag.append("字")
    if not (cfg["han_lo"] <= han <= cfg["han_hi"]):
        flag.append("汉")
    if act < cfg["act_floor"]:
        flag.append("△")
    if not (cfg["act_han_lo"] <= act_han <= cfg["act_han_hi"]):
        flag.append("△汉")
    if dlg < cfg["dlg_floor"]:
        flag.append("白行")
    if dlg_han < cfg["dlg_han_min"]:
        flag.append("白汉")
    if ratio < cfg["dlg_ratio_min"]:
        flag.append("占比")
    if avg < cfg["dlg_avg_min"]:
        flag.append("均长")
    if adv < cfg["long24_min"]:
        flag.append("递进")
    print(f"E{no:03d} | {ch:>4} | {cfg['guard_lo']}–{cfg['guard_hi']} | {han:>3} | "
          f"{act:>3}/{act_han:>4} | {dlg:>3}/{dlg_han:>4} | {ratio:>4.1f} | {avg:>5.2f} | "
          f"{adv:>3} | {adv36:>3} | {l24:>5} | {scene_n:>2} | "
          f"{'✓' if not flag else '✗ ' + ','.join(flag)}")
print("-" * 118)
wins = {}
for no in sorted(adv36_by_ep):
    wins.setdefault((no - 1) // cfg["long36_win"], []).append(no)
out = []
for g, epl in sorted(wins.items()):
    full = [g * cfg["long36_win"] + k + 1 for k in range(cfg["long36_win"])]
    got = sum(adv36_by_ep.get(x, 0) for x in epl)
    out.append(f"E{full[0]}-{full[-1]}={got if all(x in adv36_by_ep for x in full) else '缺整窗'}")
print("⑪ 强递进对 3 集窗口：" + " ｜ ".join(out))
