# -*- coding: utf-8 -*-
"""
漫剧剧本四维体检 audit.py
用法：
    python audit.py <生成器.py>   # E1 = build("...", [ ... ]) 结构
    python audit.py <正文.md>     # 已渲染的正文（## 第N集）
输出：独角戏 / 集内重复 / 集间相似度 / 场景重名 / 爽点信号分布
"""
import io, re, sys, difflib

# ★按剧种分流（2026-09-16 加 · "换类型必须换表"的机制化）
#   本 skill 的声口词表默认按**农村年代剧**调（"农村人说话不能文绉绉"）。
#   但跑**古装架空**剧时，本地人说"方才／即刻／见分晓"是**世界语言**、不是声口病;
#   硬报 = 拿年代剧的尺子量古装剧（与"未校准不许宣判"同一条铁律）。
#   '年代'（默认）= 原行为，全类计分。
#   '古装'        = 「文言/古语」「武侠/古装腔」两类**只对 ANACHRONIST 计分**
#                   ——古装剧里真正该查的是**穿越者/现代人说文言**（与声线冲突）；
#                   其余角色的命中降为"参考·不计分"，供人判不占结论。
GENRE = '年代'
ANACHRONIST = []        # 穿越者/现代人角色名（古装剧用，如 ['陆沉']）

HIT = ['脸绿', '绿', '服', '噎', '缩', '解气', '打脸', '哼走', '悻', '跪', '塌', '栽',
       '判', '报应', '冷汗', '颤', '抖', '拍案', '拍桌', '拍匾', '冷笑']
SHAME = ['踢', '锁', '赶', '轰', '骂', '贱', '野鸳鸯', '断供', '堵', '泼', '抢', '扔', '摔',
         '泪', '红眼', '眼圈']
# 同一人物的简/全称别名（对白标签常用简称，出场人物栏常用全称）
ALIAS = {'大伯': '大伯周有财', '老崔': '铁匠老崔', '赌友': '有银赌友', '翠姑': '村花翠姑',
         '路人甲': '路人', '路人乙': '路人', '村民丙': '村民',
         '看客甲': '排队看客', '看客乙': '排队看客'}

# 术语漂移表：canon=本项目认定的唯一叫法，值为"禁止混用"的异名
# 按项目改：年代剧把货币/称谓写进来；古装剧把现代词写进来。留空 {} 即跳过该项。
DRIFT = {
    '房契': ['地契', '房本', '屋契', '宅基证', '文契'],
    '块/毛票': ['银两', '两银', '银子', '文钱', '大洋', '铜板'],
}


def parse_gen(path):
    """返回 {ep: [(kind, a, b, c), ...]}"""
    lines = io.open(path, encoding='utf-8').read().split('\n')
    starts = []
    for i, l in enumerate(lines):
        m = re.match(r"^(E\d+)\s*=\s*build\(", l)
        if m:
            starts.append((int(m.group(1)[1:]), i))
    seg = {}
    for k, (ep, i) in enumerate(starts):
        end = starts[k + 1][1] if k + 1 < len(starts) else len(lines)
        seg[ep] = lines[i:end]
    out = {}
    for ep, ls in seg.items():
        items = []
        for l in ls:
            sc = re.match(r'^\s*\("([^"]+)",\s*"([^"]+)"', l)
            if sc:
                items.append(('scene', sc.group(1), sc.group(2), ''))
                continue
            md = re.match(r"^\s*\('(d|hook)','([^']+)','([^']+)','([^']+)'\),?\s*$", l)
            if md:
                items.append(('d', md.group(2), md.group(3), md.group(4)))
                continue
            mn = re.match(r"^\s*\('n','(.+)'\),?\s*$", l)
            if mn:
                items.append(('n', '', '', mn.group(1)))
                continue
            mc = re.match(r"^\s*\('card','(.+)'\),?\s*$", l)
            if mc:
                items.append(('card', '', '', mc.group(1)))
        out[ep] = items
    return out


DLG_MD = re.compile(r'^\*{0,2}([^：:△（*]{1,12})\*{0,2}\s*(?:（[^）]*）)?\s*[：:](.*)$')


def _strip_q(t):
    t = t.strip()
    if len(t) >= 2 and t[0] in '"\u201c' and t[-1] in '"\u201d':
        t = t[1:-1]
    return t


def parse_md(path):
    """解析已渲染正文。**对白体例兼容三种**（2026-09-16 加宽）：
        **角色**（动作）："台词"   ← 若原项目（粗体＋引号）
        **角色**（动作）：台词     ← 粗体无引号
        角色（动作）：台词         ← 无粗体无引号（如《大梁第一澡堂》）
    ⚠ 加宽前本函数只认第一种 ⇒ 喂进别处体例的正文会解析出"**对白 0 句**"，
      而 ①独角戏随即报"0 处" —— **这是本脚本最容易出的"假绿"**。
      ⇒ 凡在别的项目上跑：**先看首行"对白 N 句"，N=0 就是没解析进来，别信任何读数。**
    另：`出场人物：…` 会挂到最近的 `场景：…` 上，供 ⑥ 出场人物遗漏检查使用。
    """
    txt = io.open(path, encoding='utf-8').read()
    eps = re.split(r'\n## ', txt)
    out = {}
    for blk in eps:
        m = re.match(r'第(\d+)集', blk)
        if not m:
            continue
        ep = int(m.group(1))
        items = []
        for l in blk.split('\n'):
            l = l.strip()
            if not l:
                continue
            sc = re.match(r'^场景：(.+)$', l)
            if sc:
                items.append(['scene', sc.group(1), '', ''])
                continue
            cs = re.match(r'^出场人物：(.+)$', l)
            if cs:
                for k in range(len(items) - 1, -1, -1):
                    if items[k][0] == 'scene':
                        items[k][2] = cs.group(1)
                        break
                continue
            md = re.match(r'^\*\*(.+?)\*\*(?:（(.+?)）)?\s*[：:]"?\s*(.*?)"?\s*$', l)
            if md:
                items.append(['d', md.group(1), md.group(2) or '', _strip_q(md.group(3))])
                continue
            if l.startswith('△'):
                items.append(['n', '', '', l[1:]])
                continue
            if l.startswith('【本集卡点】'):
                items.append(['card', '', '', l])
                continue
            mm = DLG_MD.match(l)
            if mm and mm.group(1) not in ('场景', '出场人物'):
                items.append(['d', mm.group(1), '', _strip_q(mm.group(2))])
        out[ep] = [tuple(x) for x in items]
    return out


def report(seg):
    eps = sorted(seg)
    n_d = sum(1 for e in eps for it in seg[e] if it[0] == 'd')
    n_n = sum(1 for e in eps for it in seg[e] if it[0] == 'n')
    print(f"共 {len(eps)} 集 | 对白 {n_d} 句 | 叙述 {n_n} 行\n")

    # 1) 独角戏
    print("=" * 60)
    print("① 独角戏（同角色连续对白 ≥3 句，对手未接话）")
    bad = 0
    for e in eps:
        seq = [it for it in seg[e] if it[0] == 'd']
        i = 0
        while i < len(seq):
            j = i
            while j + 1 < len(seq) and seq[j + 1][1] == seq[i][1]:
                j += 1
            if j - i + 1 >= 3:
                bad += 1
                print(f"  E{e}: [{seq[i][1]}] 连说 {j - i + 1} 句  起于“{seq[i][3][:16]}”")
            i = j + 1
    print(f"  → 命中 {bad} 处\n")

    # 2) 集内重复
    print("=" * 60)
    print("② 集内重复（同集两行叙述前 12 字相同）")
    for e in eps:
        narr = [it[3] for it in seg[e] if it[0] == 'n']
        dup = []
        for a in range(len(narr)):
            for b in range(a + 1, len(narr)):
                if narr[a][:12] and narr[a][:12] == narr[b][:12]:
                    dup.append(narr[a][:30])
        if dup:
            print(f"  E{e}: {len(dup)} 对  {dup[:2]}")
    print()

    # 3) 场景重名
    print("=" * 60)
    print("③ 场景重名（同集两场景名完全相同 → 疑似场景2重演场景1）")
    for e in eps:
        sc = [it[1] for it in seg[e] if it[0] == 'scene']
        if len(sc) >= 2 and len(set(sc)) < len(sc):
            print(f"  E{e}: {sc}")
    print()

    # 4) 集间相似度
    print("=" * 60)
    print("④ 集间相似度（相邻 >0.30 / 隔集 >0.35 = 剧情重复嫌疑）")
    def join(e):
        return "".join(it[3] for it in seg[e] if it[0] == 'd')
    for k, e in enumerate(eps):
        if k + 1 < len(eps):
            a, b = join(e), join(eps[k + 1])
            if a and b:
                r = difflib.SequenceMatcher(None, a, b).ratio()
                if r > 0.30:
                    print(f"  E{e} vs E{eps[k+1]}: 对白相似 {r:.2f}")
    print("  ⚠ 注意：程序只抓字面重复；“同义改写式重复”（发财？骗来的↔金的，也是骗的）抓不到，需人工读。\n")

    # 5) 爽点分布
    print("=" * 60)
    print("⑤ 爽点／受辱信号分布（前 12 集持续 ≤3 = 留人风险）")
    print("   ※ 〔对白内〕列 2026-09-16 加：★只扫 △ 会**系统性低报**——")
    print("     爽点信号（成了/赚了/服了）多在对白里，不在旁白里。两列都要看。")
    for e in eps:
        t = "".join(it[3] for it in seg[e] if it[0] == 'n')
        td = "".join(it[3] for it in seg[e] if it[0] == 'd')
        h = sum(t.count(x) for x in HIT)
        s = sum(t.count(x) for x in SHAME)
        h2 = sum(td.count(x) for x in HIT)
        s2 = sum(td.count(x) for x in SHAME)
        print(f"  E{e:02d} 爽点{h:3d} {'#' * min(40, h):<40} 受辱{s:2d}   〔对白内 爽{h2} 辱{s2}〕")

    # 6) 出场人物遗漏（有台词的说话人没写进"出场人物"栏）
    #    排版铁律：场景/出场人物切换两行标注，人物不可遗漏
    print("=" * 60)
    print("⑥ 出场人物遗漏（说话人未列入该场'出场人物'栏）")
    miss_n = 0
    for e in eps:
        cur, cast, spk = None, [], []
        for it in seg[e] + [('scene', None, None, '')]:
            if it[0] == 'scene':
                if cur is not None and cast:
                    miss = [x for x in dict.fromkeys(spk)
                            if x not in cast and ALIAS.get(x, x) not in cast]
                    if miss:
                        miss_n += 1
                        print(f"  E{e} [{cur}] 漏={miss}  出场={cast}")
                cur, cast, spk = it[1], [x for x in re.split(r'[、,]', it[2] or '') if x], []
            elif it[0] in ('d', 'hook') and cur is not None:
                spk.append(it[1])
    print(f"  → 命中 {miss_n} 处\n")

    # 6b) 反向检查（2026-09-16 加 · 与 6) 互为镜像，SKILL.md 已立此条但脚本此前未实现）
    #     6) 查"说了话却没列名"；6b) 查"列了名却整场从不出现"（删繁提速类来件的通病）。
    #     ★两个陷阱：
    #       ① "出场人物："行本身不能计入"正文出现"，否则恒为 0 —— 本实现只把
    #          对白说话人/对白内容/旁白内容拼进 blob，**从不拼 cast**，天然规避。
    #       ② 单字简称口径必须加**量词负向断言**，否则"几张""那满"会把
    #          「张桂兰」「石小满」判成出席。
    #     口径三档：全称 → 后两字简称 → 单字(末字)+量词断言。三个都不中 ⇒ 挂名。
    print("=" * 60)
    print("⑥b 出场人物挂名（列进'出场人物'栏，但整场正文从不出现）")
    QTY = set("一二三四五六七八九十百千两几半些这那每")
    # ★反向别名（2026-09-16 加·实测撞出）：ALIAS 是"正文简称 → 全称"，
    #   反着读就是"全称 → 正文里可能用的各种称呼"。不反读会把
    #   「出场人物：张桂兰 / 正文：姨母」误报成挂名。
    NICK = {}
    for k, v in ALIAS.items():
        NICK.setdefault(v, []).append(k)
    ghost_n, ghost_eps = 0, set()
    for e in eps:
        cur, cast, buf, bufn = None, [], [], []
        for it in seg[e] + [('scene', None, None, '')]:
            if it[0] == 'scene':
                if cur is not None and cast:
                    blob = "".join(buf)                 # ★只含正文，不含 cast 本身
                    blobn = "".join(bufn)               # ★只含 △ 旁白（单字口径用）
                    ghost = []
                    for nm in cast:
                        forms = [nm] + NICK.get(nm, [])
                        # ★口径1 只认**长度≥2**的全称/别名（查 blob：对白＋旁白）。
                        #   单字别名（如 ALIAS 里的 '白'→白少卿）**不许走这里**——
                        #   否则 E20 台词"没**白**修"会把「白少卿」救回、⑥b 假报归零。
                        #   单字一律下沉到口径3（只查 △）。
                        if any(f and len(f) >= 2 and f in blob for f in forms):
                            continue
                        short = nm[-2:] if len(nm) >= 3 else nm
                        if short != nm and short in blob:            # 口径2 后两字简称
                            continue
                        # 口径3 单字 —— ★首字(姓)与末字(名尾)都要试：
                        #   实测"赵大宝"正文写"赵"、"邱月娥"写"邱"、"白少卿"写"白"，
                        #   只试末字会**漏判**、把真人报成挂名。两字都过才算没出现。
                        # ★★且**只扫 △ 旁白**（blobn），不扫对白：
                        #   实测 E20 台词"这桶总算没**白**修"把「白少卿」救回 ⇒ ⑥b 假归零；
                        #   本剧体例是 **△ 里用单字指人**（`△陆…／△邱…／△白…`）、
                        #   对白里单字多为普通词（没白修／洗浴之王）⇒ 单字口径必须在旁白里查。
                        ok = False
                        for ch in {nm[0], nm[-1]}:
                            for m in re.finditer(re.escape(ch), blobn):
                                if m.start() > 0 and blobn[m.start() - 1] in QTY:
                                    continue                # "几张""那满" 不算
                                ok = True
                                break
                            if ok:
                                break
                        if ok:
                            continue
                        ghost.append(nm)
                    if ghost:
                        ghost_n += 1
                        ghost_eps.add(e)
                        print(f"  E{e} [{str(cur)[:22]}] 挂名={ghost}")
                cur, cast, buf, bufn = it[1], [x for x in re.split(r'[、,]', it[2] or '') if x], [], []
            elif it[0] in ('d', 'n', 'hook') and cur is not None:
                buf.append((it[1] or '') + (it[3] or ''))
                if it[0] == 'n':
                    bufn.append((it[1] or '') + (it[3] or ''))
    if ghost_n:
        print(f"  → 挂名 {ghost_n} 场 · 涉及 {len(ghost_eps)} 集：{sorted(ghost_eps)}")
        print("  → ★取'删名'还是'补戏'＝主编口径；脚本只报不改（补戏＝把被概述掉的回合演回来）")
    else:
        print("  → 挂名 0 场 ✔")
    print()


    # 7) 声口体检（文言／古装腔／书面成语／现代商业词 → 与年代人设不符）
    #    "农村人说话不能文绉绉"：机器全绿也可能满嘴文言，必须单独卡一道
    print("=" * 60)
    print("⑦ 声口体检（文言·古装腔·书面成语·现代商业词）")
    print("   ※ 必扫全三类行：对白／旁白(△)／卡点——只扫对白会漏一大半")
    BOOK = {
        "文言/古语": ["作甚", "且看", "见分晓", "九泉", "凡品", "浮在面", "安能", "奈何", "何以",
                    "莫要", "切莫", "休要", "倘若", "纵使", "即便", "如是", "乃至", "方才", "适才",
                    "即刻", "须臾", "旋即", "继而", "既而", "然则", "何曾", "岂料", "孰料", "端的",
                    "好生", "命数", "宿命", "境地", "体统", "做派", "颜面", "在其次"],
        "武侠/古装腔": ["承让", "抱拳", "刀在人在", "出招", "野鸳鸯", "江湖", "内力", "门派",
                     "掌门", "大侠", "恩公"],
        "书面成语": ["天衣无缝", "童叟无欺", "万事俱备", "熟能生巧", "真凭实据", "逼良为娼",
                   "一清二楚", "心中有数", "心知肚明", "来日方长", "后会有期", "既往不咎",
                   "自食其果", "咎由自取", "众目睽睽", "理直气壮", "不言而喻", "不动声色",
                   "深藏不露", "静观其变", "拭目以待", "如坐针毡"],
        "现代商业/公文": ["渠道", "坐实", "正名", "封神", "赋能", "闭环", "复盘", "抓手",
                      "对齐", "打法", "颗粒度", "末代传人", "顶层设计"],
    }
    hit = {k: [] for k in BOOK}
    ref = {k: [] for k in BOOK}      # ★古装剧：世界语言，只列不计分
    KIND = {'d': '对白', 'hook': '钩', 'n': '旁白', 'card': '卡点'}
    for e in eps:
        for it in seg[e]:
            if it[0] not in KIND:
                continue
            say = it[3]
            who_name = ALIAS.get(it[1], it[1]) if it[1] else ''
            for k, L in BOOK.items():
                f = [w for w in L if w in say]
                if f:
                    # ★ 上下文切片（2026-09-16 加）：子串匹配**没有词边界**，
                    #   "价合适才定" 会被切出"适才" ⇒ 假阳性。
                    #   打印命中词的前 3 / 后 3 字，切词误伤一眼可辨：
                    #   `适才⟨价合|定⟩` = 误伤；`方才⟨白公子|坐过⟩` = 真命中。
                    ctx = []
                    for w in f:
                        p = say.find(w)
                        ctx.append(f"{w}⟨{say[max(0,p-3):p]}|{say[p+len(w):p+len(w)+3]}⟩")
                    who = (it[1] + "：" ) if it[1] else ""
                    line = f"E{e:02d}【{KIND[it[0]]}】{who}{say}  ← {ctx}"
                    # ★按剧种分流（2026-09-16 加）：古装剧里"文言/武侠"两类
                    #   只对穿越者计分，本地人命中降为参考。
                    if (GENRE == '古装' and k in ('文言/古语', '武侠/古装腔')
                            and who_name not in ANACHRONIST):
                        ref[k].append(line)
                    else:
                        hit[k].append(line)
    tot = sum(len(v) for v in hit.values())
    for k in BOOK:
        if hit[k]:
            print(f"  [{k}] {len(hit[k])} 条")
            for h in hit[k]:
                print("     ", h)
    rt = sum(len(v) for v in ref.values())
    if rt:
        print(f"  [参考·不计分] {rt} 条 —— 古装世界语言，非穿越者说不算声口病（人工判）")
        for k in BOOK:
            for h in ref[k]:
                print(f"     ({k}) {h}")
    if tot == 0 and rt == 0:
        print("  → 声口疑似 0 处 ✔")
    else:
        print(f"  → 声口疑似合计 {tot} 处（逐条人工判：人物有意说书面语=人设标记可留；")
        print("     穿越/不合身份=改。特别注意'物证/走正道'等有语境可通的词，别误杀）")
    print()

    # 8) 逻辑四查（2026-09-13 新增 · 主编第三轮批评「整个剧本逻辑也有问题」后立法）
    #    机器能抓的四类；"前言不搭后语"机器抓不到，但这四类先过一遍能挖掉一大半。
    print("=" * 60)
    print("⑧ 逻辑四查（批注泄漏／术语漂移／外文残留／动作标注重复）")

    def body(e):
        """取该集全部正文文本（对白/旁白/卡点/场景名），排除集标题"""
        out = []
        for it in seg[e]:
            if it[0] in ('d', 'hook', 'n', 'card'):
                out.append((KIND.get(it[0], it[0]), it[1], it[3]))
            elif it[0] == 'scene':
                out.append(('场景', '', it[1]))
        return out

    # 8-1 批注泄漏：编剧编号写进正文（旁白/对白/卡点），读者看得见＝直接穿帮
    LEAK = re.compile(r'(?:跟|想起|他想|参见|见|同|如|比)\s*E\d{1,2}|E\d{1,2}\s*(?:那|这)|第\d{1,2}集那')
    hits = []
    for e in eps:
        for kind, who, txt in body(e):
            if txt and LEAK.search(txt):
                hits.append(f"E{e:02d}【{kind}】{txt[:46]}")
    if hits:
        for h in hits:
            print("     ", h)
        print(f"  → 批注泄漏 {len(hits)} 处（旁白是给观众看的，绝不许出现集数编号）")
    else:
        print("  → 批注泄漏 0 处 ✔")

    # 8-2 术语漂移：同一物件/概念的"混用异名"（按项扫，命中即人工统一口径）
    if DRIFT:
        hd = {}
        for e in eps:
            for kind, who, txt in body(e):
                for canon, bad in DRIFT.items():
                    for b in bad:
                        if b in (txt or ''):
                            hd.setdefault((canon, b), []).append(e)
        if hd:
            for (canon, b), es in sorted(hd.items()):
                print(f"     异名「{b}」应统一为「{canon}」 → 出现在 E{min(es)}-E{max(es)} 共 {len(es)} 处")
            print("  → 术语漂移：同一物件全剧只许一个叫法，逐项统一后再扫")
        else:
            print("  → 术语漂移 0 处 ✔")

    # 8-3 外文残留（AI 生成事故高发：中英混杂）
    EN = re.compile(r'[A-Za-z]{3,}')
    hits = []
    for e in eps:
        for kind, who, txt in body(e):
            for w in EN.findall(txt or ''):
                hits.append(f"E{e:02d}【{kind}】…{w}…  {txt[:40]}")
    if hits:
        for h in hits:
            print("     ", h)
        print(f"  → 外文残留 {len(hits)} 处（正文不得夹带英文单词）")
    else:
        print("  → 外文残留 0 处 ✔")

    # 8-4 动作标注同集反复 ≥3（阅读单调；标注是给观众看的，不是内部备注）
    hits = []
    for e in eps:
        c = {}
        for it in seg[e]:
            if it[0] in ('d', 'hook') and it[2]:
                c[it[2]] = c.get(it[2], 0) + 1
        for k, v in c.items():
            if v >= 3:
                hits.append(f"E{e:02d}：（{k}）×{v}")
    if hits:
        for h in hits:
            print("     ", h)
        print(f"  → 动作标注重复 {len(hits)} 处（（笑）类通用标注可留，具体动作用词须换）")
    else:
        print("  → 动作标注重复 0 处 ✔")
    print()

    # 9) 旁白小说腔（2026-09-13 新增 · 主编第四轮批评「通篇都是毛病·小说话表达」后立法）
    #    剧本旁白只写"看得见的动作/画面"；一旦出现作者判断、回环、抒情收束、夸张比喻，
    #    就是小说笔法——读者听不到、演不出，且会把短剧写成散文。
    print("⑨ 旁白小说腔（只扫 △ 旁白；对白里的同类说法是人话，不扫）")
    LYRIC = [
        ("判断腔 这X是Y",       r'这[^，。！？]{1,8}是[^，。！？]{4,14}[。！]'),
        ("对举腔 不是X，是Z",   r'这[^，。！？]{1,8}不是[^，。！？]{2,10}，是[^，。！？]{4,14}'),
        ("回环腔 那X是Y的X",    r'那[^，。！？]{1,6}是[^，。！？]{2,10}的[^，。！？]{1,4}[。，]'),
        ("夸张腔 比啥都/比谁都", r'比[啥谁]都|比[^，。！？]{0,4}都[^，。！？]{0,3}(实|强|香|甜|硬|稳|疼|重|亮|快)'),
        ("评论腔 这局/开场/回甜", r'这局|这盘棋|才刚开场|回甜|苦里|甜里|有奔头'),
        ("总结腔 是熬/挣/换来的", r'是挣来的|是熬出来的|是换来的|是压出来的|是磨出来的|是杀出来的|是拿回|路是自己'),
        ("比喻尾巴 像…似的",     r'像[^，。！？]{2,6}似的|像个[^，。！？]{1,6}的'),
        # ↓ 2026-09-13 二次加宽：明喻不只在"似的"里，正文里全都是"像X"
        ("旁白明喻 像X/跟X似的/仿佛", r'像[^，。！？]{1,10}[，。]|跟[^，。！？]{1,6}似的|仿佛|好比'),
        ("旁白拟人/代言 也认下/替他/像也", r'也认下|替他沉默|像也|像在|像给|像把|像开了|像落了'),
        # ↓ 2026-09-13 加宽：拿改前快照回测，发现旧 7 条漏掉下面三大家族
        ("抒情收尾 那点X散了/成了", r'那[点些口]?[^，。！？]{0,7}(散了|没了|成了|实了|稳了|定了|回来了|都成了|全没了|全没了|全没了)'),
        ("判断收尾 才像/这夜不/才像个家", r'这才像|这夜不|这日子|才像个家|才像个|才算|才有个家|才像家'),
        ("评论插话 心里那口/算顺了/打得响/最疼", r'心里那[口点]|算顺了|打得响|最疼|不言语'),
        ("判断插入 望这姑娘/望这幕/望那点光", r'望这姑娘|望这幕|望那点光|眼里(热|红了)了?下|都顿了下'),
        # ↓ 2026-09-13 三次加宽：第六轮人工逐句读 E1-E5，机器仍全绿却一眼见病，
        #   根因是"形容词式判断"和"程度副词收尾"两族没进表。拿 before_w27 快照回测。
        ("评论腔2 十足/碎得稀烂/一笔勾销", r'[^，。！？]{0,4}十足|碎得稀烂|一笔勾销|架子碎'),
        ("抒情收尾2 收了半分/头回有了/那点暖", r'收了[半几]分|头回有了|一回有了|那点暖|有了活气|有了热气|有了盼头'),
        ("判断收尾2 从来没这么/挣来了", r'从来没这么|挣来了|脸面挣|够享|够本'),
        ("总结腔2 半辈子/一辈子V", r'半辈子的[^，。！？]{2,8}|一辈子的[^，。！？]{2,8}的'),
        # ↓ 2026-09-13 四次加宽：第七轮逐句读 E21-E30，机器全绿而人一眼见病，
        #   根因是"比较腔（比X还Y）""判断定义腔（这X是Y的）""内心外化（藏不住/露了怯）"三族没进表。
        ("比较腔2 比X还Y／比X更Y", r'比[^，。！？]{1,8}还[^，。！？]{1,5}[。，]|比[^，。！？]{1,8}更[^，。！？]{1,5}[。，]'),
        ("判断定义腔 这X是Y的", r'这[^，。！？]{1,6}是[^，。！？]{2,10}的[。，]'),
        ("内心外化 藏不住/露了怯/踩脸", r'藏不住|露了怯|漏了怯|踩着[^，。！？]{0,4}脸|比想的还'),
        ("判断插入2 咯噔/却合拍/给得实诚", r'心里咯噔|却合拍|给得实诚|话都说不利索'),
    ]
    # 卡点行（【本集卡点】）也会渲染进正文、观众看得见，同样禁编剧抒情腔
    CARD_SICK = [
        ("编剧腔 生情/一见",   r'初识生情|暗生情|情愫|一见钟'),
        ("编剧腔 暗蓄/立誓/讳莫", r'暗蓄|立誓|讳莫如深|暗流|伏线'),
        ("编剧腔 判断式",     r'而不|已生|之中，|之间，'),
        # ↓ 三次加宽：第六轮在 E1 卡点抓到"感情线初种"这类剧本术语腔
        ("编剧腔 感情线/初种", r'感情线|初种|种下|萌发|感情升温'),
    ]
    lyric_hits = []
    card_hits = []
    for e in eps:
        for it in seg[e]:
            if len(it) < 4:
                continue
            if it[0] == 'n':
                for name, p in LYRIC:
                    mm = re.search(p, it[3])
                    if not mm:
                        continue
                    # 误报排除①：命中段里带引号＝在复述某人说过的话，不是作者抒情
                    if '"' in mm.group(0) or '\u201c' in mm.group(0):
                        continue
                    lyric_hits.append((e, name, mm.group(0), it[3]))
                    break
            elif it[0] == 'card':
                for name, p in CARD_SICK:
                    mm = re.search(p, it[3])
                    if not mm:
                        continue
                    card_hits.append((e, name, mm.group(0), it[3]))
                    break
    if lyric_hits:
        for e, name, seg_, line in lyric_hits:
            print(f"      E{e:02d}【{name}】…{seg_}…")
            print(f"           <{line[:56]}>")
        print(f"  → 旁白小说腔 {len(lyric_hits)} 处（逐条改：删掉作者评论/比喻，只留动作与画面）")
    else:
        print("  → 旁白小说腔 0 处 ✔")
    if card_hits:
        for e, name, seg_, line in card_hits:
            print(f"      E{e:02d}【{name}】…{seg_}…")
            print(f"           <{line[:56]}>")
        print(f"  → 卡点行编剧腔 {len(card_hits)} 处（卡点也要写成看得见的动作，别写作者判断）")
    else:
        print("  → 卡点行编剧腔 0 处 ✔")
    print()


if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else None
    if not p:
        print(__doc__); sys.exit(1)
    seg = parse_gen(p) if p.endswith('.py') else parse_md(p)
    if not seg:
        print("解析为空，请检查文件格式"); sys.exit(1)
    report(seg)
