#!/usr/bin/env python3
"""生成合订本（读稿版）v2：自动按「第N章」排序单章文件。
用法：python3 _audit/build_hezb.py <out.md> <max_chapter> [目录=.]
"""
import io,re,sys,glob,os
def han(s): return len(re.findall(r'[\u4e00-\u9fff]',s))
out=sys.argv[1]; mx=int(sys.argv[2]); d=sys.argv[3] if len(sys.argv)>3 else '.'
cand={}
for fn in glob.glob(os.path.join(d,'*第*章*.md')):
    b=os.path.basename(fn)
    if '合订' in b or '细纲' in b or '诊断' in b: continue
    m=re.search(r'第(\d+)章',b)
    if m and '重生1973' in b:
        n=int(m.group(1))
        if n<=mx and '重生1973' in b: cand[n]=fn
files=[cand[k] for k in sorted(cand) if k<=mx]
body=[]; total=0; rows=[]
for n in sorted(cand):
    if n>mx: continue
    fn=cand[n]
    raw=io.open(fn,encoding='utf-8').read().split('\n')
    # 从第一个「## 第 N 章」起取正文（丢掉书/章标题行、拍 块、分隔线）
    i0=next((i for i,l in enumerate(raw) if re.match(r'^## 第\s*\d+\s*章',l)),0)
    keep=[]; foot=None
    for l in raw[i0:]:
        s=l.strip()
        if re.match(r'^\*\*（第 ?\d+ ?章 · 完.*）\*\*$',s): continue
        if s=='---': continue
        if s.startswith('**断在这儿**：'): foot=s.replace('**',''); continue
        if s=='**断在这儿**': continue
        keep.append(l)
    txt=re.sub(r'\n{3,}','\n\n','\n'.join(keep)).strip()
    title=txt.split('\n')[0].lstrip('# ').strip()
    n2=han(txt); total+=n2; rows.append((title,n2))
    body.append(txt+'\n')
    if foot: body.append(foot+'\n')
    body.append('---\n')
head=("# 《重生1973：我一杆枪，喂饱全屯》\n\n"
      "> 一九七三 · 长白山下 · 松岭屯 · 长篇 · 100 章\n\n"
      "> **本合订＝第 1–%d 章** · 读稿版 · 正文汉字 %d\n\n---\n"%(len(files),total))
io.open(out,'w',encoding='utf-8').write(head+'\n'.join(body))
for t,n in rows: print('%-18s %5d'%(t,n))
print('---- %d 章 ｜ 正文汉字 %d ｜ 约合 %d 字'%(len(files),total,round(total*1.25)))
