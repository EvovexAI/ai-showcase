#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merge_05b.py —— 把各 part 核销表的人判合并进「全本」核销表

★按 (集, 台词文本) 多重集对齐（而非句序）——正文插句后句序会位移，按序会错配。
★功能标记与裁定**都要搬**——只搬裁定会让"≥2 类"占比大幅掉档（实测 46%→10%）。
段级按 (集, 段序) 对齐。

用法：
  python3 merge_05b.py --target "05b-…-全60集.md" --parts "05b-…-part*.md"
未能在 part 表中找到的句（＝正文新增/改动句）会列出，需**单独补判**。
"""
import re, io, sys, glob, argparse
from collections import defaultdict

ROW = re.compile(r'^\|\s*E(\d+)\s*\|\s*(\d+)\s*\|([^|]*)\|([^|]*)\|\s*([☑?☐]+)\s*\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|\s*$')
SEG = re.compile(r'^\|\s*E(\d+)\s*\|\s*(\d+)\s*\|([^|]*)\|\s*([^|]*?)\s*\|\s*$')


def scan(path):
    sent = defaultdict(list)
    seg = {}
    zone = None
    occ = {}
    for ln in io.open(path, encoding='utf-8'):
        s = ln.rstrip('\n')
        if s.startswith('## 一、'):
            zone = 'sent'; continue
        if s.startswith('## 二、'):
            zone = 'seg'; continue
        if s.startswith('## 三、'):
            zone = None; continue
        if zone == 'sent':
            m = ROW.match(s)
            if m:
                sent[int(m.group(1))].append((m.group(4).strip(), m.group(5).strip(),
                                              m.group(6).strip(), m.group(7).strip()))
        elif zone == 'seg':
            m = SEG.match(s)
            if m:
                ep = int(m.group(1)); occ[ep] = occ.get(ep, 0) + 1
                seg[(ep, occ[ep])] = (m.group(3).strip(), m.group(4).strip())
    return sent, seg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', required=True, help='全本核销表 md（被写入）')
    ap.add_argument('--parts', required=True, help='part 表 glob，如 "05b-…-part*.md"')
    a = ap.parse_args()

    files = sorted(glob.glob(a.parts)) or [a.parts]
    pool = defaultdict(list)
    part_seg = {}
    for p in files:
        s1, s2 = scan(p)
        for ep, rows in s1.items():
            for t in rows:
                pool[(ep, t[0])].append(t)
        part_seg.update(s2)

    lines = io.open(a.target, encoding='utf-8').read().split('\n')
    zone = None; occ = {}; n_sent = n_seg = 0; unmatched = []
    for i, s in enumerate(lines):
        if s.startswith('## 一、'):
            zone = 'sent'; continue
        if s.startswith('## 二、'):
            zone = 'seg'; continue
        if s.startswith('## 三、'):
            zone = None; continue
        if zone == 'sent':
            m = ROW.match(s)
            if not m:
                continue
            ep = int(m.group(1)); text = m.group(4).strip()
            q = pool.get((ep, text))
            if q:
                t = q.pop(0)
                cells = s.split('|')
                cells[-4] = ' %s ' % t[1]      # 功能标记（含人工补标的①）
                cells[-3] = ' %s ' % t[2]      # 命中数
                cells[-2] = ' %s ' % t[3]      # 裁定
                lines[i] = '|'.join(cells); n_sent += 1
            else:
                unmatched.append((ep, text))
        elif zone == 'seg':
            m = SEG.match(s)
            if not m:
                continue
            ep = int(m.group(1)); occ[ep] = occ.get(ep, 0) + 1
            t = part_seg.get((ep, occ[ep]))
            if t:
                cells = s.split('|')
                cells[-2] = ' %s ' % t[1]
                lines[i] = '|'.join(cells); n_seg += 1

    io.open(a.target, 'w', encoding='utf-8').write('\n'.join(lines))
    print('句级合并 %d 行｜段级合并 %d 行' % (n_sent, n_seg))
    print('★未在 part 表中找到（＝正文新增/改动句，需单独补判）%d 条：' % len(unmatched))
    for ep, t in unmatched:
        print('   E%d 「%s」' % (ep, t))
    sys.exit(0 if not unmatched else 2)


if __name__ == '__main__':
    main()
