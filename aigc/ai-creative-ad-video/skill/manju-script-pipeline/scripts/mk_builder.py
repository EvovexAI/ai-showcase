#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
漫剧换皮仿写 · 后半段骨架构建器模板（mk_builder.py）
-----------------------------------------------------------------
专为 E31-60 等大段批量写作设计，注入 gen_template.EPS 之前做结构自检。

自检项:
  1) TYPE 序列必须 == SKE (22位, 严格 14'd'+8'a')
  2) 同角色连说 >=3 即 FAIL (铁律23 自说自话)
  3) 每行须以 场景:/出场人物:/△/对白 之一开头
  4) 卡点(card) 与 集尾钩(hook) 非空

用法: 填 EPIS 列表 → python3 mk_builder.py
  通过则打印可注入 gen_template.EPS 的源码; 不通过则报具体错误行。

SKE 骨架 (22 beats): 14对白 + 8动作
  d a d a d d a d a d d a d a d d a d d a d d
"""
import sys

# 22位骨架: 14'd' + 8'a'
SKE = ['d','a','d','a','d','d','a','d','a','d','d','a','d','a',
       'd','d','a','d','d','a','d','d']

def D(r, v, t):
    return ('d', r, v, t)
def A(t):
    return ('a', t)

# ===== DEMO EPIS (实例化时整段替换为真实后半段数据) =====
# 元素: (n, scene, chars, beats[22], card, hook)
EPIS = [
 (31, '场景：镇银行 日 内', '出场人物：林春禾、柜员、赵铁柱',
   [D('林春禾','递卡','同志，取号。'),
    A('春禾攥着金卡，手心出汗。'),
    D('柜员','笑','姐，里面不少钱吧。'),
    A('春禾点头，不语。'),
    D('林春禾','望屏','九十九根，一根不少。'),
    D('柜员','惊叹','姐，您这是中彩票了？'),
    A('春禾浅笑。'),
    D('林春禾','收卡','别声张。'),
    A('她把卡揣进内兜。'),
    D('柜员','压声','懂，懂。'),
    D('林春禾','步出','该还的，得还。'),
    A('她走进阳光里。'),
    D('赵铁柱','迎','春禾，成了？'),
    A('春禾比个手势。'),
    D('林春禾','笑','成了。'),
    D('赵铁柱','挠头','接下来咋办？'),
    A('春禾望向远处新房。'),
    D('林春禾','定','买房，接我娘。'),
    D('赵铁柱','笑','春禾，你真行。'),
    A('两人击掌。'),
    D('林春禾','望','这钱，干净。'),
    D('赵铁柱','点头','干净。')],
   '【本集卡点】金卡变现落地，春禾盘算买房接娘，底气第一次足。',
   '**林春禾**（望新房）："娘，咱有家了。"'),
]

# ===== 自检 =====
def validate():
    ok = True
    for ep in EPIS:
        n, scene, chars, beats, card, hook = ep
        types = [b[0] for b in beats]
        # 1) TYPE vs SKE
        if types != SKE:
            ok = False
            # 找第一个错位
            for i,(t,s) in enumerate(zip(types, SKE)):
                if t != s:
                    print(f"E{n} TYPE MISMATCH @slot{i}: got '{t}' want '{s}'")
                    break
        # 2) 连说>=3
        sp = [b[1] for b in beats if b[0]=='d']
        run = 1; mx = 1
        for j in range(1, len(sp)):
            if sp[j] == sp[j-1]:
                run += 1; mx = max(mx, run)
            else:
                run = 1
        if mx >= 3:
            ok = False
            print(f"E{n} 同角色连说>=3: {mx} ('{sp[0]}')")
        # 3) 行格式
        if not scene.startswith('场景：'):
            ok = False; print(f"E{n} 场景行格式错: {scene!r}")
        if not chars.startswith('出场人物：'):
            ok = False; print(f"E{n} 出场人物行格式错: {chars!r}")
        for b in beats:
            if b[0]=='a' and not isinstance(b[1], str):
                ok = False; print(f"E{n} A beat 格式错: {b!r}")
        # 4) 卡点/钩非空
        if not card.strip():
            ok = False; print(f"E{n} 卡点为空")
        if not hook.strip():
            ok = False; print(f"E{n} 集尾钩为空")
        # 钩须是对白格式
        if not ('（' in hook and '）' in hook and '：' in hook and '"' in hook):
            ok = False; print(f"E{n} 集尾钩非对白格式: {hook!r}")
    return ok

def emit_source():
    # 打印可注入 gen_template.EPS 的源码
    print("# ---- 注入 gen_template.EPS ----")
    for n, scene, chars, beats, card, hook in EPIS:
        print(f" {n}: ep({n}, {scene!r}, {chars!r}, [")
        for b in beats:
            if b[0]=='d':
                print(f"   D({b[1]!r},{b[2]!r},{b[3]!r}),")
            else:
                print(f"   A({b[1]!r}),")
        print(f"  ], {card!r}, {hook!r}),")

def main():
    if validate():
        print("★ 骨架自检通过 ★")
        emit_source()
    else:
        print("!! 自检未过, 见上错误, 修正后再注入")
        sys.exit(1)

if __name__ == '__main__':
    main()
