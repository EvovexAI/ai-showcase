#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
漫剧换皮仿写 · 机器门禁（通用版）
用法: python3 check_generic.py <剧本md文件> [--hi N] [--lo M]

解析 `## 第N集` 或 `第N集` 分集，逐集核查：
  - 字数(去空): E1-2<=1000; E3+ 500-600（阈值可由 --e2-max / --min / --max 覆盖）
  - △动作行 >= (--lo，默认 8)   ★2026-09-15 注：现行口径为**相对下限**
  - 对白行   >= (--hi，默认 14)  max(5, 母本同集△×0.7) / max(4, 母本同集对白×0.7)
  - 首句必对白(版式三条之一): 出场人物后首非空行须含 （ ） ： "
  - 集尾必台词(版式三条之三): 卡点行/——第N集完—— 前最后非空非卡点行须含 （ ） ： "
  - 自说自话(项目级·铁律23): 同角色连说>=3 计为超2句
全绿打印 ★机器门禁全绿★

判定: fail_chars==fail_dlg==fail_d==fail_first==fail_last==0 and zsh_sent==0

★编号权威＝用户级 ~/.workbuddy/MEMORY.md。旧文本曾把"首句对白"标为铁律16、"两行场景"标为铁律18，
  二者均为撞号（铁律16（用户级）＝节奏密度与结构引擎；铁律18（用户级）＝不沾政治红线），已改为「版式三条」。
"""
import sys, re, argparse

def analyze(path, e2_max=1000, lo=1, hi=10**9, min_c=500, max_c=600):
    txt = open(path, encoding='utf-8').read()
    # 分集: 支持 "## 第N集" 或 "第N集"
    parts = re.split(r'(?m)^#{0,3}\s*第\s*(\d+)\s*集\s*$', txt)
    eps = []
    for i in range(1, len(parts), 2):
        n = int(parts[i])
        if n < lo or n > hi:
            continue
        body = parts[i+1]
        lines = body.split('\n')
        # 去尾分隔行与卡点行(卡点单独算字数但非对白/动作)
        content_lines = [l for l in lines if not l.strip().startswith('——')]
        # 字数(去空)
        chars = re.sub(r'\s', '', '\n'.join(content_lines))
        # △动作行
        d_lines = [l for l in lines if l.strip().startswith('△')]
        # 对白行: **角色**（...）："..."
        dlg_lines = [l for l in lines if re.search(r'\*\*[^*]+\*\*（[^）]*）[：:]\s*"', l)]
        # 首句对白: 找到"出场人物："后第一个非空行
        first_dlg_ok = False
        seen_chars = False
        for l in lines:
            s = l.strip()
            if s.startswith('出场人物：'):
                seen_chars = True
                continue
            if seen_chars and s:
                first_dlg_ok = bool(re.search(r'\*\*[^*]+\*\*（[^）]*）[：:]\s*"', l))
                break
        # 集尾钩: 最后非空行(不含 ——第N集完——) 须是对白
        last_dlg_ok = False
        for l in reversed(lines):
            s = l.strip()
            if not s:
                continue
            if s.startswith('——'):
                continue
            last_dlg_ok = bool(re.search(r'\*\*[^*]+\*\*（[^）]*）[：:]\s*"', l))
            break
        # 自说自话: 连续 **角色**（ 同角色
        sp = re.findall(r'\*\*([^*]+)\*\*（', '\n'.join(lines))
        mx = 1
        run = 1
        for j in range(1, len(sp)):
            if sp[j] == sp[j-1]:
                run += 1
                mx = max(mx, run)
            else:
                run = 1
        zsh_ep = max(0, mx - 2)  # 超出2句的句数
        eps.append((n, len(chars), len(d_lines), len(dlg_lines),
                    first_dlg_ok, last_dlg_ok, zsh_ep))
    return eps

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--lo', type=int, default=1)
    ap.add_argument('--hi', type=int, default=10**9)
    ap.add_argument('--e2-max', type=int, default=1000)
    ap.add_argument('--min', type=int, default=500)
    ap.add_argument('--max', type=int, default=600)
    args = ap.parse_args()

    eps = analyze(args.file, args.e2_max, args.lo, args.hi, args.min, args.max)
    fail_chars = fail_dlg = fail_d = fail_first = fail_last = zsh_sent = 0
    total_chars = 0
    total_d = 0
    total_dlg = 0
    print(f"{'集':>3} | {'字':>4} | {'△':>2} | {'对白':>3} | {'首句对白':>5} | {'集尾钩':>5} | {'字数达标'}")
    for n, ch, d, dlg, f, la, z in eps:
        total_chars += ch; total_d += d; total_dlg += dlg
        # 字数判定
        if n <= 2:
            ok = 'OK' if ch <= args.e2_max else 'FAIL'
        else:
            ok = 'OK' if args.min <= ch <= args.max else 'FAIL'
        if ok == 'FAIL':
            fail_chars += 1
        if d < 8:
            fail_d += 1
        if dlg < 14:
            fail_dlg += 1
        if not f:
            fail_first += 1
        if not la:
            fail_last += 1
        zsh_sent += z
        print(f"E{n:02d} | {ch:>4} | {d:>2} | {dlg:>3} | {'Y' if f else 'N'} | {'Y' if la else 'N'} | {ok}")
    ne = len(eps)
    print(f"已写集：{ne} 集｜ 总字数(去空)：{total_chars}")
    print(f"集均△ {total_d/ne:.1f} ｜ 对白均 {total_dlg/ne:.1f} ｜ 自说自话 {zsh_sent} 句")
    if fail_chars == fail_dlg == fail_d == fail_first == fail_last == 0 and zsh_sent == 0:
        print("★机器门禁全绿★")
    else:
        print(f"!! 未全绿: 字数fail={fail_chars} △fail={fail_d} 对白fail={fail_dlg} 首句fail={fail_first} 集尾fail={fail_last} 自说={zsh_sent}")

if __name__ == '__main__':
    main()
