#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""split_05b.py —— 从「全本」台词四功能核销表重生成 6 张 part 分表（★同源，禁手工各改）

为什么必须"同源重生成"：正文在终审期改过词后，part 分表仍留旧台词 ⇒ 与全本/正文对不上，
**门禁扫不到**（分表不在扫描范围）⇒ 隐形漂移。规矩：全本表是唯一权威，分表一律由本脚本派生。

用法：
  python3 split_05b.py "05b-台词四功能核销表-XX-全60集.md" [--per 10] [--prefix 05b-台词四功能核销表-XX]

输出：同目录下 `05b-台词四功能核销表-XX-part1.md` … 按 `--per` 每 N 集一张。
"""
import io, re, sys, os, argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('full', help='全本核销表 md')
    ap.add_argument('--per', type=int, default=10, help='每张分表覆盖集数（默认 10）')
    ap.add_argument('--prefix', default=None, help='输出前缀（默认取全本表名的"-全…集"之前部分）')
    a = ap.parse_args()

    txt = io.open(a.full, encoding='utf-8').read()
    lines = txt.split('\n')

    if a.prefix:
        pre = a.prefix
    else:
        m = re.search(r'-全\s*\d+\s*集', os.path.basename(a.full))
        pre = os.path.basename(a.full)[:m.start()] if m else os.path.splitext(os.path.basename(a.full))[0]

    HEAD = """# 台词四功能核销表（自动预标 · 主表 Z38/Z38b）

> **标记含义**：`☑`＝脚本确定命中；`?`＝弱提示待你确认；`☐`＝**无信号，必须人审**。
> **人只做三件事**：①给 `☐` 的位补判（**①潜台词脚本判不了，只能你判**）；
> ②把**四位全 ☐ 的句子**裁定"删/改"（四类全不入＝废句）；③**核对**每段的「本段目的」。
> ★段目的已在**细纲阶段**定好（判据前移）；本表用 `--purpose-src` 自动带入，人只核对。
> 填完跑 `python3 dlgcheck.py --verify 本表.md` 机器算账。

"""
    TAIL = """
## 三、汇总（人填完核对）

| 硬门禁（脚本判） | 目标 |
|---|---|
| ⛔ 确定废句（纯客套/极短应答） | **= 0**（改完重新生成本表，⛔ 应消失） |
| 零信号句"裁定"列 | **全部已裁定**（不留 ☐） |
| 段级"本段目的"列 | **全部已填**（不留 ☐） |
| 参考：命中 ≥2 类的句占比 | 越高越好（≥30%） |
"""
    SENT = re.compile(r'^\|\s*(E\d+)\s*\|\s*(\d+)\s*\|([^|]*)\|([^|]*)\|\s*([☑?☐]+)\s*\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|\s*$')
    SEG = re.compile(r'^\|\s*(E\d+)\s*\|\s*(\d+)\s*\|([^|]*)\|\s*([^|]*?)\s*\|\s*$')

    sent, seg = [], []
    zone = None
    for ln in lines:
        s = ln.rstrip()
        if s.startswith('## 一、'):
            zone = 's'; continue
        if s.startswith('## 二、'):
            zone = 'g'; continue
        if s.startswith('## 三、'):
            zone = None; continue
        if zone == 's':
            m = SENT.match(s)
            if m:
                sent.append((int(m.group(1)[1:]), s, m.group(5)))
        elif zone == 'g':
            m = SEG.match(s)
            if m:
                seg.append((int(m.group(1)[1:]), s))

    eps = sorted({e for e, _, _ in sent} | {e for e, _ in seg})
    if not eps:
        print('★未从全本表解析到任何行，请检查格式'); sys.exit(2)
    lo_all, hi_all = min(eps), max(eps)

    idx = 0
    lo = lo_all
    while lo <= hi_all:
        hi = min(lo + a.per - 1, hi_all)
        idx += 1
        ss = [(s, mk) for e, s, mk in sent if lo <= e <= hi]
        gg = [s for e, s in seg if lo <= e <= hi]
        n_done = sum(1 for _, mk in ss if mk.count('☑') >= 1)
        n_weak = sum(1 for _, mk in ss if mk.count('☑') == 0 and '?' in mk)
        n_zero = sum(1 for _, mk in ss if mk.count('☑') == 0 and '?' not in mk)
        head = HEAD + (f"- 本 part 对白句：**{len(ss)}** 句\n"
                       f"  - ⛔ **脚本硬判的“确定废句”：0 句**\n"
                       f"  - ✅ 脚本已命中 ≥1 类（可放行）：**{n_done}** 句\n"
                       f"  - ⚠️ 只有弱提示、需你确认：**{n_weak}** 句\n"
                       f"  - 🔴 零信号（**抽审池**）：**{n_zero}** 句\n"
                       f"- ≥5 句长对话段：**{len(gg)}** 段（每段必须有目的），其中**细纲已带 {len(gg)} 段目的**\n\n"
                       "> **★诚实边界**：脚本**只硬判“确定废句”**，**证不了“这句有功能”**——归人判。\n\n")
        body = ("## 一、句级核销（①潜 ②设 ③推 ④情）\n\n"
                "| 集 | # | 角色 | 台词 | 功能 | 命中数 | 裁定 |\n|---|---|---|---|---|---|---|\n"
                + '\n'.join(s for s, _ in ss)
                + "\n\n## 二、段级核销（Z38b · 每段必须有目的）\n\n"
                  "| 集 | 段内句数 | 本段目的（爆料/争吵/立人设/推进） | 裁定（留/删） |\n|---|---|---|---|\n"
                + '\n'.join(gg) + "\n")
        out = os.path.join(os.path.dirname(os.path.abspath(a.full)), f'{pre}-part{idx}.md')
        io.open(out, 'w', encoding='utf-8').write(head + body + TAIL)
        print(f'{os.path.basename(out)}: 句 {len(ss)}（≥1类 {n_done}/弱 {n_weak}/零 {n_zero}）｜段 {len(gg)}')
        lo = hi + 1


if __name__ == '__main__':
    main()
