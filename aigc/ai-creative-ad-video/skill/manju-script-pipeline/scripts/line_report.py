# -*- coding: utf-8 -*-
"""逐行诊断：打印每集的 对白行（引号内汉字）与 △ 行（汉字），用于精修配平。
用法：python3 _audit/line73.py <草稿.md>
"""
import importlib.util, io, os, sys

# ★可移植：检查器脚本 = 第 2 个位置参数；不给就自动找
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
    sys.exit("❌ 找不到检查器脚本（check*full.py）—— 用法：line_report.py <草稿.md> [检查器.py]")
spec = importlib.util.spec_from_file_location("c53", _find_checker())
c53 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c53)

path = sys.argv[1]
if not os.path.isabs(path):
    path = os.path.join(os.getcwd(), path)
txt = io.open(path, encoding="utf-8").read()
for e in c53.split_eps(txt):
    no, body = c53.ep_no(e), c53.body_of(e)
    raw = body.splitlines()
    dlg = [l for l in raw if c53.is_dlg(l)]
    act = [l for l in raw if c53.is_act(l)]
    dh = sum(c53.han_count(c53.dlg_text(l)) for l in dlg)
    ah = sum(c53.han_count(c53.QUOTE_RE.sub("", l)) for l in act)
    print(f"===== E{no:03d}  对白 {len(dlg)}行/{dh}汉   △ {len(act)}行/{ah}汉")
    seq = []
    for l in dlg:
        m = c53.SPK_RE.search(l)
        q = c53.dlg_text(l)
        h = c53.han_count(q)
        seq.append((m.group(1) if m else "?", h))
        print(f"   白 {h:>3}  {q[:34]}")
    i = 0
    while i < len(seq):
        j = i + 1
        while j < len(seq) and seq[j][0] == seq[i][0]:
            j += 1
        rl = j - i
        if rl == 2:
            t = seq[i][1] + seq[i + 1][1]
            mark = "✅递进对" + ("（强）" if t >= 38 else "")
            print(f"      ↳ 相邻2行 {seq[i][0]} 合计 {t} {mark if t >= 30 else '✗ <30'}")
        elif rl >= 3:
            print(f"      ↳ ⚠ 同人相邻 {rl} 句：{seq[i][0]}")
        i = j
    for l in act:
        h = c53.han_count(c53.QUOTE_RE.sub("", l))
        print(f"   △  {h:>3}  {l.strip()[:40]}")
    print()
