# -*- coding: utf-8 -*-
"""剧本「门禁不判、只能自查」的七项，一把跑完。

覆盖：
  ① 首句必对白（出场人物行后的第一个非空行）
  ② 集尾必台词
  ③ 卡点行恰 1 条
  ④ 末行 ≠ 卡点前一句（门禁只判「末行是对白」，不判重复）
  ⑤ 单句 ≥24 汉字（口径冲突项，门禁只报数不判红）
  ⑥ 同人连说 ≥3 句（会顶穿 自说自话 线）
  ⑦ 跨集 △ 撞句（与指定正文文件比对）
  ⑧ 连续重复行（相邻两行完全相同）—— 门禁完全不判，**只在自查里**
     ★⑧ 是补上的：53 剧本第十三轮 E67 溜过一版（批量插入 △ 时把已存在的对白又插了一遍），
       当时自查表里没有这一项 ⇒ **自查表本身也会漏项，加检查项比"多看一眼"可靠**。

用法：
    python3 selfcheck.py <待查.md> [对比正文.md]
    # 对比正文.md 给了才做 ⑦；不给就只查 ①–⑥
检查器 check*full.py 自动在 cwd／上级目录里找。

出处：53《重生1973》剧本第十三轮（E65–E68）实测沉淀。
"""
import glob
import importlib.util
import io
import os
import re
import sys


_Q = re.compile(r'[\u201c"](.+?)[\u201d"]')


def _say(line):
    """取「引号内的台词」；取不到就退回整行。用于比"末行 vs 卡点前一句"是否同句。"""
    m = _Q.search(line or "")
    return m.group(1) if m else (line or "").strip()


def load():
    cands = []
    cands += glob.glob(os.path.join(os.getcwd(), "check*full.py"))
    cands += glob.glob(os.path.join(os.path.dirname(os.getcwd()), "check*full.py"))
    for c in cands:
        if os.path.exists(c):
            spec = importlib.util.spec_from_file_location("c53", c)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            return m
    sys.exit("❌ 找不到检查器脚本（check*full.py）—— 请在含该脚本的目录下运行")


def analyse(c53, path):
    txt = io.open(path, encoding="utf-8").read()
    eps = c53.split_eps(txt)
    acts = []
    print("=" * 74)
    print("文件：", path)
    for e in eps:
        no = c53.ep_no(e)
        raw = c53.body_of(e).splitlines()
        lines = [l for l in raw if l.strip()]

        first = None
        for i, l in enumerate(lines):
            if re.match(r'^\s*[-*+]*\s*\**出场人物\**\s*[：:]', l):
                first = lines[i + 1] if i + 1 < len(lines) else None
                break
        first_ok = bool(first and c53.is_dlg(first))

        last = None
        for l in reversed(lines):
            if any(k in l for k in c53.SKIP_TAIL):
                continue
            last = l
            break
        last_ok = bool(last and c53.is_dlg(last))

        cd = sum(1 for l in raw if '【本集卡点】' in l)
        ci = [i for i, l in enumerate(lines) if '【本集卡点】' in l]
        before = lines[ci[-1] - 1] if ci else ""
        # ★「卡点行之前的第一行须是对白」只在**卡点放集尾**的体例下成立。
        #   本项目体例＝【本集卡点】在**末行之前**（…正文 → 卡点 → 末行 → 集完），
        #   此时"卡点前一行"就是正文最后一行，**允许是 △**（景物/动作收尾）⇒ 该判据不适用。
        card_is_tail = bool(ci) and ci[-1] == len(lines) - 1
        card_before_txt = ("OK" if (before and c53.is_dlg(before)) else "✗") if card_is_tail else "—"
        # ★比「引号内台词」而不是整行：卡点前后常是同一句台词、只换（动作）⇒ 整行比会漏判
        dup = (_say(last) == _say(before)) if (last and before) else False

        big = [c53.han_count(c53.dlg_text(l)) for l in raw if c53.is_dlg(l)]
        big = [x for x in big if x >= 24]

        seq = []
        for l in raw:
            if c53.is_dlg(l):
                m = c53.SPK_RE.search(l)
                seq.append(m.group(1) if m else "?")
        tri = []
        i = 0
        while i < len(seq):
            j = i + 1
            while j < len(seq) and seq[j] == seq[i]:
                j += 1
            if j - i >= 3:
                tri.append((seq[i], j - i))
            i = j

        # ⑧ 连续重复行（相邻两行完全相同）—— 门禁不判
        dbl = []
        for k in range(1, len(lines)):
            if lines[k] == lines[k - 1]:
                dbl.append((k + 1, lines[k][:34]))

        print("E%03d 首句%s 集尾%s 卡点%d%s 卡点前%s 末行vs卡点前 %s 单句>=24:%d 同人>=3:%s 重复行:%d"
              % (no, "OK" if first_ok else "✗", "OK" if last_ok else "✗",
                 cd, "✓" if cd == 1 else "✗",
                 card_before_txt,
                 "✗重复" if dup else "OK", len(big), tri, len(dbl)))
        for d in dbl:
            print("     ⚠ 重复行 @%d: %s" % d)
        acts += [l.strip() for l in raw if c53.is_act(l) and l.strip()]
    return acts


if __name__ == "__main__":
    c53 = load()
    a = analyse(c53, sys.argv[1])
    if len(sys.argv) > 2:
        body = io.open(sys.argv[2], encoding="utf-8").read()
        old = set(l.strip() for l in body.splitlines() if c53.is_act(l) and l.strip())
        hit = [l for l in a if l in old]
        print("\n跨集 △ 撞句（本文件 ∩ %s）：%d" % (sys.argv[2], len(hit)))
        for h in hit:
            print("   ", h[:48])
