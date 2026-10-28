#!/usr/bin/env python3
"""并段 v5：★跳过"短拍区"（章内前 N 段），只并后面的短叙述段。
用法：python3 _audit/merge_para5.py <file> [keep_head=10]
理由：开场与情绪高点必须"一句一段"（短拍），但中后段不能碎成一句一段。
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
def merge_once(paras, cap=60, total=130):
    out=[];i=0;c=0
    while i<len(paras):
        cur=paras[i]
        if is_dlg(cur) or protected(cur) or n(cur)>cap:
            out.append(cur); i+=1; continue
        if i+1<len(paras):
            nx=paras[i+1]
            if (not is_dlg(nx)) and (not protected(nx)) and n(nx)<=cap and n(cur)+n(nx)<=total:
                out.append(cur.rstrip()+nx.lstrip()); c+=1; i+=2; continue
        if out:
            pv=out[-1]
            if (not is_dlg(pv)) and (not protected(pv)) and n(pv)<=cap and n(pv)+n(cur)<=total:
                out[-1]=pv.rstrip()+cur.lstrip(); c+=1; i+=1; continue
        out.append(cur); i+=1
    return out,c

def process(fn, keep_head=10):
    t=io.open(fn,encoding="utf-8").read()
    t2=re.sub(r'(?m)^---$',SEP,t)
    paras=[p.strip() for p in re.split(r'\n\s*\n',t2) if p.strip()]
    # 找章标题位置，其后 keep_head 段为短拍区
    ci=[i for i,p in enumerate(paras) if p.startswith('## ')]
    start=(ci[-1]+1) if ci else 0
    head=paras[:start+keep_head]
    tail=paras[start+keep_head:]
    tot=0
    for _ in range(8):
        tail,c=merge_once(tail); tot+=c
        if c==0: break
    out=re.sub(r'(?m)^'+SEP+r'$','---',"\n\n".join(head+tail))
    io.open(fn,"w",encoding="utf-8").write(out if out.endswith("\n") else out+"\n")
    allp=head+tail
    narr=[p for p in allp if not is_dlg(p) and not protected(p)]
    nl=[n(p) for p in narr]
    print(f"  {fn[:32]} 短拍区={keep_head} 段 ｜合并={tot} ｜叙述段={len(narr)} 均长={round(sum(nl)/len(nl))} 短段={round(sum(1 for x in nl if x<25)/len(nl)*100)}%")

if __name__=="__main__":
    keep=int(sys.argv[2]) if len(sys.argv)>2 else 10
    for fn in [sys.argv[1]]: process(fn,keep)
