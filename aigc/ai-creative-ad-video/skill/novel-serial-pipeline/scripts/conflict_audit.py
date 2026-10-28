#!/usr/bin/env python3
"""矛盾点与爽点体检：逐章量「对手 / 围观 / 冲突 / 得手 / 爽点强调 / 章末钩子」。
用法：python3 _audit/conflict_audit.py <目录>
判据来自总纲：当量 = 围观 × 赌注 × 有心 × 回响；小打脸当众须 ≥6；平路 ≤3 章。
"""
import io,re,sys,glob,os

# 对手分层（按总纲人物册）
L1=['林大贵']                     # 亲戚层
L2=['赵德发','曹广顺','姓黄的','戴眼镜']  # 体制层
L3=['孙广才','刘二奎']              # 同行层
L4=['老宋','齐志明']               # 生意层（前期对手）
L5=['周小婉']                     # 女反派
L6=['姓钱的']                     # 外来
VCONF=r'抢|夺|拦|堵|吵|打|砸|罚|收|赖|踹|骂|威胁|扣|截|告|查|逼|赶|占|骗|坑|偷|顶|驳|撂|堵回|退|拒'
VWATCH=r'全屯|院里|井台|场院|人堆|人圈|人都|都看着|围过来|围上来|一群人|半屯|满屯|看热闹|门口站|一圈'
MONEY=r'\d+\s*(?:斤|元|块|毛|张|个|头|只|副|桶|袋|斗|尺|枪|把|条)'
HOOK=r'\*\*断在这儿\*\*：(.+)'

def han(s): return len(re.findall(r'[\u4e00-\u9fff]',s))

def load(d):
    cand={}
    for fn in glob.glob(os.path.join(d,'*第*章*.md')):
        b=os.path.basename(fn)
        if '合订' in b or '细纲' in b or '诊断' in b or '体检' in b or '报告' in b: continue
        m=re.search(r'第(\d+)章',b)
        if m and '重生1973' in b: cand[int(m.group(1))]=fn
    return cand

def body_of(fn):
    raw=io.open(fn,encoding='utf-8').read().split('\n')
    i0=next((i for i,l in enumerate(raw) if re.match(r'^## 第\s*\d+\s*章',l)),0)
    return '\n'.join(l for l in raw[i0:] if not l.strip().startswith('**断在这儿**'))

def audit(d):
    cand=load(d); rows=[]
    for n in sorted(cand):
        t=body_of(cand[n])
        title=re.match(r'^## 第\s*\d+\s*章\s*(.*)',t.split('\n')[0]).group(1).strip()
        full=io.open(cand[n],encoding='utf-8').read()
        hook=(re.search(HOOK,full) or [None,''])[1]
        foes=[]
        for lab,lst in [('亲',L1),('体',L2),('行',L3),('商',L4),('女',L5),('外',L6)]:
            if any(x in t for x in lst): foes.append(lab)
        watch=len(re.findall(VWATCH,t))
        conf=len(re.findall(VCONF,t))
        money=len(re.findall(MONEY,t))
        bold=len(re.findall(r'\*\*[^*]+\*\*',t))
        rows.append(dict(n=n,title=title,han=han(t),foes=''.join(foes),nfoe=len(foes),
                         watch=watch,conf=conf,money=money,bold=bold,
                         hook=hook,hook_q=1 if '？' in hook or '?' in hook else 0,
                         flat=1 if (len(foes)==0 and conf==0) else 0))
    return rows

VOLS=[('卷一 活下去',1,20),('卷二 立住',21,40),('卷三 出屯',41,60),('卷四 出名',61,80),('卷五 回头看',81,100)]

if __name__=='__main__':
    d=sys.argv[1] if len(sys.argv)>1 else '.'
    rows=audit(d); R={r['n']:r for r in rows}
    # 逐章表
    print('章  章名            汉字  对手  围观 冲突 得手 爽点  平路')
    for r in rows:
        print('%3d %-12s %5d  %-4s %4d %4d %4d %4d  %s'%(
            r['n'],r['title'][:12],r['han'],r['foes'] or '—',r['watch'],r['conf'],r['money'],r['bold'],
            '★平路' if r['flat'] else ''))
    print()
    print('卷           章数 均汉字 无对手章 平路章 均围观 均冲突 均得手 均爽点 钩子带问 当众章(围观≥3)')
    for name,a,b in VOLS:
        rs=[R[n] for n in range(a,b+1) if n in R]
        f=lambda k: round(sum(x[k] for x in rs)/len(rs),2)
        print('%-12s %3d  %5d  %6d  %5d  %6.2f %6.2f %6.2f %6.2f  %6d  %6d'%(
            name,len(rs),round(sum(x['han'] for x in rs)/len(rs)),sum(1 for x in rs if x['nfoe']==0),
            sum(x['flat'] for x in rs),f('watch'),f('conf'),f('money'),f('bold'),
            sum(x['hook_q'] for x in rs),sum(1 for x in rs if x['watch']>=3)))
    print()
    flat=[r['n'] for r in rows if r['flat']]
    print('平路章（无对手且无冲突动词）：%d 章 → %s'%(len(flat),flat))
    nofoo=[r['n'] for r in rows if r['nfoe']==0]
    print('无对手章：%d 章 → %s'%(len(nofoo),nofoo))
    # 最长连续无对手
    run=[];best=[]
    for r in rows:
        if r['nfoe']==0: run.append(r['n'])
        else:
            if len(run)>len(best): best=run
            run=[]
    if len(run)>len(best): best=run
    print('最长连续无对手：%d 章 → %s'%(len(best),best))
    # 强围观章（围观≥3 且 有对手）
    strong=[r['n'] for r in rows if r['watch']>=3 and r['nfoe']>0]
    print('当众打脸候选（围观≥3 且有对手）：%d 章'%len(strong))
