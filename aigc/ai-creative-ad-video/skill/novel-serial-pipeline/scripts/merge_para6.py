#!/usr/bin/env python3
"""并段 v6：在对白与叙述之间做「同一段合并」
规则：★「对白段」＋ 紧跟其后的「短叙述段（≤18 汉字）」⇒ 合成一段
      （例：'\"这是我打的。\"' + '他说。'  ⇒  '\"这是我打的。\"他说。'）
同时：前 N 段（短拍区）不参与。
用法：python3 _audit/merge_para6.py <file> [keep_head=10]
"""
import io,re,sys
SEP="@@SEP@@"
def n(p): return len(re.findall(r'[\u4e00-\u9fff]',p))
def is_dlg(p): return any(c in p for c in '"“「')
def protected(p):
    s=p.strip()
    if s.startswith('#') or s.startswith('>') or s==SEP: return True
    if s.startswith('**') and s.rstrip().endswith('**'): return True
    return False
def process(fn, keep_head=10, cap=18):
    t=io.open(fn,encoding="utf-8").read()
    t2=re.sub(r'(?m)^---$',SEP,t)
    paras=[p.strip() for p in re.split(r'\n\s*\n',t2) if p.strip()]
    ci=[i for i,p in enumerate(paras) if p.startswith('## ')]
    start=(ci[-1]+1) if ci else 0
    head=paras[:start+keep_head]; tail=paras[start+keep_head:]
    out=[]; i=0; cnt=0
    while i < len(tail):
        cur=tail[i]
        if i+1 < len(tail):
            nx=tail[i+1]
            # 对白段 ＋ 紧跟的短叙述段 ⇒ 并
            if is_dlg(cur) and (not is_dlg(nx)) and (not protected(nx)) and n(nx)<=cap:
                out.append(cur.rstrip()+nx.lstrip()); cnt+=1; i+=2; continue
            # 短叙述段 ＋ 紧跟的对白段 ⇒ 并（叙述在前，例：'他说：' 后接引号）
            if (not is_dlg(cur)) and (not protected(cur)) and n(cur)<=cap and is_dlg(nx) and not protected(cur):
                out.append(cur.rstrip()+nx.lstrip()); cnt+=1; i+=2; continue
        out.append(cur); i+=1
    res=re.sub(r'(?m)^'+SEP+r'$','---',"\n\n".join(head+out))
    io.open(fn,"w",encoding="utf-8").write(res if res.endswith("\n") else res+"\n")
    allp=head+out
    narr=[p for p in allp if not is_dlg(p) and not protected(p)]
    dlg=[p for p in allp if is_dlg(p)]
    nl=[n(p) for p in narr]
    print("  合并=%d｜段=%d（对白 %d／%.0f%%）｜叙述段均长=%d｜短段=%d%%" % (
        cnt,len(allp),len(dlg),len(dlg)/len(allp)*100,round(sum(nl)/len(nl)),
        round(sum(1 for x in nl if x<25)/len(nl)*100)))
if __name__=="__main__":
    keep=int(sys.argv[2]) if len(sys.argv)>2 else 10
    process(sys.argv[1],keep)
