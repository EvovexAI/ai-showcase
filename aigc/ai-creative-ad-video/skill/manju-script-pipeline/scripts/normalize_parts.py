#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""normalize_parts.py —— 统一正文各 part 的排版体例（幂等）：块间恰 1 空行；`场景：` 与 `出场人物：` 紧邻。
不删改任何文字（去空白字数不变）。

用法：
  python3 normalize_parts.py "正文part*.md"
"""
import io, sys, glob, argparse


def norm(text):
    out = []
    for ln in text.split('\n'):
        s = ln.rstrip()
        if not s:
            continue
        if s.startswith('## 第'):
            if out and out[-1] != '':
                out.append('')
            out.append(s); out.append('')
            continue
        if s.startswith('场景：'):
            if out and out[-1] != '':
                out.append('')
            out.append(s)          # 场景行后**不留空行**（下一行必须紧跟出场人物行）
            continue
        out.append(s); out.append('')
    while out and out[-1] == '':
        out.pop()
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pattern', help='part 文件 glob，如 "正文part*.md"')
    a = ap.parse_args()
    files = sorted(glob.glob(a.pattern))
    if not files:
        print('★未匹配到文件：', a.pattern); sys.exit(2)
    for p in files:
        t = io.open(p, encoding='utf-8').read()
        n = norm(t)
        if n != t:
            io.open(p, 'w', encoding='utf-8').write(n)
            print('规整 %s（%d→%d 行）' % (p, t.count('\n'), n.count('\n')))
        else:
            print('已是标准体例 %s' % p)


if __name__ == '__main__':
    main()
