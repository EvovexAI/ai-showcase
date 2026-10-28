# -*- coding: utf-8 -*-
"""漫剧正文「三类隐形硬缺陷」体检（跨项目可用）。

为什么单独写：这三类**中文字符类 grep 永远抓不到**，但它们全是硬违规。
  ① 异常字符：说话人标签/正文里混进拉丁或非法字节（实测踩过说话人标签被写坏成 `ç` U+00E7，
     中文 grep 完全命中不了，还连带藏住了一句该改的旧措辞）。
  ② 说话人 ↔ 出场人物 核销：某场里有人有台词，但 `出场人物：` 没列他
     （＝"场景两行制"体例要求，也是门禁 ④b「N2c 说话人未入场」的根因）。
  ③ △ 行高相似：同一集里两条动作描写近乎重复（＝凑字数的痕迹）。

用法：
    python3 defect_scan.py 正文.md [--cast-csv 群演正则] [--sim 0.60]
退出码：发现 P0（①/②）→ 2；只有 ③ 提示 → 0。
"""
import argparse, difflib, io, re, sys, unicodedata

# 白名单：CJK 汉字 / CJK 标点 / 全角 / ASCII 可打印 / 常用中文排版符号
OK = re.compile(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u0020-\u007e'
                r'\u2010-\u2015\u2018\u2019\u201c\u201d\u2026\u00b7\u3010\u3011'
                r'\u2460-\u2473\u2605\u2606\u00a7\u2264\u2265\u25b3\u2192\u2194'
                r'\u2500-\u257f\u25a0\u25a1\u000a]')
DLG = re.compile(r'^\*\*(?P<who>[^*]+)\*\*(?:（[^）]*）)?\s*[：:]\s*(?P<q>.*)$')
EP = re.compile(r'^##\s*第\s*(\d+)\s*集')
# 群演/泛称：允许出现在任何场而不必逐个列出（按项目体例改这一行）
# ★第2次校准（2026-09-18 · 52《女猎户》E41–E120 全本轮 · 修「假绿」形态）：
#   旧值含裸 `村民` ⇒ 它 match 掉 `村民甲`／`村民乙`／`村民丙`，把**带甲乙丙的具体说话人**
#   当"群演"放过 ⇒ E49「村民丙」、E102「村民甲」两处**有台词但没列出场人物**被漏判
#   （实测：旧版报「0 处」，而同源判据 namecheck 报「N2c 3 处」）。
#   而体例纪律恰恰相反：**只要台词前写了具体名（甲/乙/丙），`出场人物：` 就必须列出**。
#   修法＝给群体词加**负向断言**：后面紧跟甲乙丙丁戊己庚辛的，不算群演。
DEFAULT_CROWD = (r'((?:村民|众人|群众|挑水|同村|闲汉|孩子|人们|大伙|围观|有人|大家|村里人)'
                 r'(?![甲乙丙丁戊己庚辛]))')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--crowd", default=DEFAULT_CROWD)
    ap.add_argument("--sim", type=float, default=0.60)
    a = ap.parse_args()
    txt = io.open(a.path, encoding="utf-8").read()
    lines = txt.split("\n")
    p0 = []

    # ① 异常字符（跳过抬头 `>` 引用的元信息行——那是执行件允许的工作行）
    bad = {}
    for l in lines:
        if l.lstrip().startswith(">") or l.lstrip().startswith("|"):
            continue
        for ch in l:
            if not OK.match(ch):
                bad.setdefault(ch, 0)
                bad[ch] += 1
    if bad:
        for i, l in enumerate(lines, 1):
            if l.lstrip().startswith(">") or l.lstrip().startswith("|"):
                continue
            for ch in l:
                if not OK.match(ch):
                    p0.append(" ① 异常字符 L%d  U+%04X %s  ← %s"
                              % (i, ord(ch), unicodedata.name(ch, "?"), l.strip()[:60]))
                    break
    print("① 异常字符：%s" % (", ".join("U+%04X×%d" % (ord(k), v) for k, v in bad.items()) or "0 个 ✓"))

    # ①b 行尾「（NN）」数字标注 —— 典型的「内部配比标记被误写进正文」
    #     （2026-09-17 实测：一次混进 89 处，把「内容字」虚抬 ~354，直接造成"字数莫名超标"）
    tag = [(i, l.rstrip()) for i, l in enumerate(lines, 1)
           if re.search(r"（\d{1,2}）\s*$", l) and not l.lstrip().startswith(">")]
    if tag:
        for i, l in tag[:8]:
            p0.append(" ①b 行尾数字标注 L%d  ← %s" % (i, l.strip()[-56:]))
        if len(tag) > 8:
            p0.append(" ①b …另有 %d 处" % (len(tag) - 8))
    print("①b 行尾数字标注：%d 处%s" % (len(tag), "  ← 必须清零（不进正文）" if tag else " ✓"))

    # ② 说话人 ↔ 出场人物；③ △ 相似
    crowd = re.compile(a.crowd)
    epno, cast, scen, ep_delta = None, None, None, []
    n2c = n3 = 0

    def flush_sim():
        nonlocal n3
        for i in range(len(ep_delta)):
            for j in range(i + 1, len(ep_delta)):
                r = difflib.SequenceMatcher(None, ep_delta[i][1], ep_delta[j][1]).ratio()
                if r >= a.sim:
                    n3 += 1
                    p0.append(" ③ △ 相似 %.2f：%s  ↔  %s"
                              % (r, ep_delta[i][1][:38], ep_delta[j][1][:38]))

    for l in lines:
        s = l.strip()
        m = EP.match(s)
        if m:
            flush_sim()
            epno, ep_delta, cast, scen = m.group(1), [], None, None
            continue
        if s.startswith("场景："):
            scen = s[3:]
        elif s.startswith("出场人物："):
            cast = [x.strip() for x in re.split(r"[、,，/]", s[5:]) if x.strip()]
        elif s.startswith("△"):
            ep_delta.append((epno, s))
        else:
            d = DLG.match(s)
            if d and cast is not None:
                who = d.group("who").strip()
                if who not in cast and not crowd.match(who):
                    n2c += 1
                    p0.append(" ② 说话人未列出场人物：E%s 场[%s] 说话人「%s」不在 %s"
                              % (epno, scen, who, cast))
    flush_sim()
    print("② 说话人未列：%d 处 ｜ ③ △ 高相似(≥%.2f)：%d 对" % (n2c, a.sim, n3))
    print("-" * 80)
    for x in p0:
        print(x)
    hard = [x for x in p0 if x.startswith(" ①") or x.startswith(" ②")]
    print("=" * 80)
    print("结论：%s" % ("★有 P0（异常字符/说话人未列）⇒ 必须修" if hard else "P0 干净"))
    sys.exit(2 if hard else 0)


if __name__ == "__main__":
    main()
