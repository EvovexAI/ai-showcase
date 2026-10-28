#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selfaudit_final.py —— ★「完本偷懒自查」：独立于门禁的第 8 道排查（7 项）

用途：正文/全套文档完成后，用**独立实现的尺子**交叉复量，抓"门禁全绿也照过"的问题。
原则：另写脚本、不复用门禁；**自查脚本自己也是尺子，先用母本校准再宣判正文**。

用法：
  python3 selfaudit_final.py --copy 正文-XX-全60集.md --mother 母本原文-XX-60集.txt \
                             --table 05b-台词四功能核销表-XX-全60集.md [--relax 18,39,41,43,52,60]

7 项：
  1 卡点行「引语式引用」⊆ 本集正文（台词 ∪ △ 道具文字；排除 `"XX"两个字` 概念强调）
  2 指纹⑧ 同场同说话人「前 3 字」重复 ≥3（称呼语需另行人判）
  3 指纹③ 连续 2 个 △ 且不含人物主体（PPL 正则必须含全部主角/主配名）
  4 集尾钩是否复读本集台词（2-gram Jaccard ≥0.75）
  5 ★前后半"贴母本"对比（后半 >> 前半 ⇒ 后半照抄母本）
  6 ★核销表人判位是否留空（自动放行／已裁定／真待办 三态）
  7 数字类跨集一致性（同一数量词出现在哪些集）

退出码：0＝无硬缺口；2＝有 ★ 项待办（真待办 > 0）。
"""
import re, os, io, sys, argparse
from collections import defaultdict, Counter


def norm(s):
    return re.sub(r'[^\u4e00-\u9fff]', '', s)


def ngrams(s, n=2):
    t = norm(s)
    return set(t[i:i + n] for i in range(len(t) - n + 1))


DQ = re.compile(r'^\*\*([^*]+)\*\*(?:（([^）]*)）)?\s*[：:]\s*"(.*)"\s*$')
ACT = re.compile(r'^[△▲]')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--copy', required=True, help='正文全本 md')
    ap.add_argument('--mother', default=None, help='母本 txt（跑自查 5 用）')
    ap.add_argument('--table', default=None, help='全本 05b 核销表 md（跑自查 6 用）')
    ap.add_argument('--ppl', default=None, help='人物主体正则（默认内置本剧常见词；新剧请传）')
    a = ap.parse_args()

    raw = io.open(a.copy, encoding='utf-8').read()
    secs = re.split(r'(?m)^##\s*第\s*(\d+)\s*集', raw)
    eps = [(int(secs[i]), secs[i + 1]) for i in range(1, len(secs), 2)]
    N = len(eps)
    hard = 0

    print('=' * 78)
    print('【自查 1】卡点行「引语式引用」是否 ⊆ 本集正文')
    print('=' * 78)
    bad = 0
    for no, body in eps:
        dlgs, acts, caps = [], [], []
        for ln in body.split('\n'):
            s = ln.strip()
            m = DQ.match(s)
            if m:
                dlgs.append(m.group(3))
            if ACT.match(s):
                acts.append(s)
            if '【本集卡点】' in s:
                caps.append(s)
        pool = dlgs + acts
        for c in caps:
            c2 = re.sub(r'[“"][^”"]{1,8}[”"]\s*(两个字|三个字|这个字)', '◯', c)
            for q in re.findall(r'[“"]([^”"]+)[”"]', c2):
                if len(norm(q)) < 3:
                    continue
                if not any(q in d or d in q for d in pool):
                    print(f'  ⚠ E{no} 卡点引用「{q}」在正文（台词∪△）中找不到')
                    bad += 1
    print(f'  → 脱钩 {bad} 处（期望 0）\n')
    hard += bad

    print('=' * 78)
    print('【自查 2】指纹⑧：同场同说话人「前 3 字」重复 ≥3')
    print('=' * 78)
    h8 = 0
    for no, body in eps:
        for blk in re.split(r'(?m)^场景：', body):
            byw = defaultdict(list)
            for ln in blk.split('\n'):
                m = DQ.match(ln.strip())
                if m and len(m.group(3)) >= 3:
                    byw[m.group(1)].append(m.group(3))
            for who, ts in byw.items():
                for h, c in Counter(t[:3] for t in ts).items():
                    if c >= 3:
                        print(f'  ⚠ E{no} {who} 开头「{h}」×{c}  {[t for t in ts if t.startswith(h)]}')
                        h8 += 1
    print(f'  → {h8} 处（称呼语开头需人判：人设标记/首尾呼应可保留）\n')

    print('=' * 78)
    print('【自查 3】指纹③：连续 2 个 △ 且不含人物主体')
    print('=' * 78)
    PPL = re.compile(a.ppl) if a.ppl else re.compile(
        r'他|她|我|你|娘|爹|哥|姐|嫂|婶|奶|厂长|工人|女工|男工|会计|干事|大夫|护士|'
        r'门卫|司机|孩子|众人|大家|旁人|邻居|路人|摊主|业务员|秘书|服务员|民警|掌柜|邮递员')
    h3 = 0
    for no, body in eps:
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        run, buf = 0, []
        for s in lines:
            if ACT.match(s):
                buf.append(s)
                if PPL.search(s):
                    run, buf = 0, []
                else:
                    run += 1
                    if run >= 2:
                        print(f'  ⚠ E{no} 连续无量人物 △：{[b[:26] for b in buf[-2:]]}')
                        h3 += 1
                        run, buf = 0, []
            else:
                run, buf = 0, []
    print(f'  → {h3} 处（参考，非硬判；静场/伏笔可保留）\n')

    print('=' * 78)
    print('【自查 4】集尾钩是否复读本集其他台词（相似≥0.75）')
    print('=' * 78)
    h4 = 0
    for no, body in eps:
        dlgs = [m.group(3) for m in (DQ.match(l.strip()) for l in body.split('\n')) if m]
        if len(dlgs) < 2:
            continue
        tail = dlgs[-1]; A = ngrams(tail)
        for d in dlgs[:-1]:
            B = ngrams(d)
            if A and B:
                j = len(A & B) / len(A | B)
                if j >= 0.75 and len(norm(tail)) >= 5:
                    print(f'  ⚠ E{no} 末行「{tail}」≈ 本集「{d}」({j:.2f})')
                    h4 += 1
    print(f'  → {h4} 处（期望 0）\n')
    hard += h4

    if a.mother and os.path.exists(a.mother):
        print('=' * 78)
        print('【自查 5】★前后半"贴母本"对比（与母本句相似≥0.65）')
        print('=' * 78)
        mtxt = io.open(a.mother, encoding='utf-8').read()
        mdlg = set()
        for ln in mtxt.split('\n'):
            m = re.match(r'^[^\s：:]{1,12}[：:]\s*(.+)$', ln.strip())
            if m:
                mq = re.findall(r'[“"]([^”"]+)[”"]', m.group(1))
                t = mq[0] if mq else m.group(1)
                if len(norm(t)) >= 6:
                    mdlg.add(t)
        mg = [(t, ngrams(t)) for t in mdlg]
        half = N // 2
        for label, lo, hi in ((f'前半 E1-{half}', 1, half), (f'后半 E{half+1}-{N}', half + 1, N)):
            hits, samples = 0, []
            for no, body in eps:
                if not (lo <= no <= hi):
                    continue
                for ln in body.split('\n'):
                    m = DQ.match(ln.strip())
                    if not m:
                        continue
                    d = m.group(3)
                    if len(norm(d)) < 8:
                        continue
                    A = ngrams(d)
                    for t, B in mg:
                        if B and len(A & B) / len(A | B) >= 0.65:
                            hits += 1
                            if len(samples) < 8:
                                samples.append((no, d, t, round(len(A & B) / len(A | B), 2)))
                            break
            print(f'  {label}：与母本高相似句 {hits} 处')
            for no, d, t, j in samples:
                print(f'     E{no}「{d}」 ≈ 母本「{t}」({j})')
        print('  ★判读：后半 >> 前半 ⇒ 后半照抄母本；相当或更少 ⇒ 反证"下半部没抄"\n')

    if a.table and os.path.exists(a.table):
        print('=' * 78)
        print('【自查 6】★核销表人判位是否留空（三态）')
        print('=' * 78)
        zone = None; n_auto = n_done = n_pend = 0; seg_all = seg_un = 0
        rows = []
        for ln in io.open(a.table, encoding='utf-8'):
            s = ln.strip()
            if s.startswith('## 一、'):
                zone = 's'; continue
            if s.startswith('## 二、'):
                zone = 'g'; continue
            if s.startswith('## 三、'):
                zone = None; continue
            if not s.startswith('|'):
                continue
            c = [x.strip() for x in s.strip('|').split('|')]
            if zone == 's' and len(c) == 7 and c[0].startswith('E'):
                if '☐' in c[-1]:
                    n_pend += 1
                    if len(rows) < 5:
                        rows.append(c)
                elif c[-1] == '' and c[-2].isdigit() and int(c[-2]) >= 1:
                    n_auto += 1
                else:
                    n_done += 1
            if zone == 'g' and len(c) == 4 and c[0].startswith('E'):
                seg_all += 1
                if '☑留' not in c[-1]:
                    seg_un += 1
        print(f'  句级：自动放行(命中≥1) {n_auto}｜已裁定 {n_done}｜★真待办(含☐) {n_pend}')
        print(f'  段级：共 {seg_all} 行｜★未裁定 {seg_un} 行')
        for r in rows:
            print(f'     样本：{r}')
        hard += n_pend + seg_un
        print()

    print('=' * 78)
    print('【自查 7】数字类跨集一致性（同一数量词出现在 ≥3 集）')
    print('=' * 78)
    seen = defaultdict(set)
    for no, body in eps:
        for m in re.finditer(r'((?:[一二三四五六七八九十百千万两零]+|\d+)(?:千|百|十|万)?'
                             r'(?:坛|块|斤|口|个|人|次|成|分|年|月|天))', body):
            if len(norm(m.group(1))) >= 2:
                seen[m.group(1)].add(no)
    for k in sorted(seen, key=lambda x: (-len(seen[x]), x)):
        if len(seen[k]) >= 3:
            print(f'  · 「{k}」出现在 {len(seen[k])} 集：E{sorted(seen[k])}')
    print('  （人工核：同一数字跨集是否指同一件事）\n')

    print('=' * 78)
    print(f'★硬项合计（自查1+4+6）：{hard}')
    print('结论：' + ('✅ 无硬缺口' if hard == 0 else '⚠ 有硬项待办，逐条处置后再跑'))
    print('=' * 78)
    sys.exit(0 if hard == 0 else 2)


if __name__ == '__main__':
    main()
