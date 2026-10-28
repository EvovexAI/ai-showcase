#!/usr/bin/env python3
"""结构三项 + 基本读数：一级标题=1 ／ 独占 --- =2 ／ 全文汉字 = 声明值
用法：python3 _audit/chk.py <file> [file2 ...]
"""
import io,re,sys
BAD=r'[，。！？；：、](?=[，。！？；：、])'
MIS=r'山神|敬山|拜山|忌讳|报应|兆头|批斗|成分|口号|语录'
for fn in sys.argv[1:]:
    t=io.open(fn,encoding="utf-8").read()
    h1=len(re.findall(r'(?m)^#\s',t))
    sep=len(re.findall(r'(?m)^---$',t))
    han=len(re.findall(r'[\u4e00-\u9fff]',t))
    paras=[p.strip() for p in re.split(r'\n\s*\n',t) if p.strip()]
    dlg=[p for p in paras if any(c in p for c in '"“「')]
    punct=len(re.findall(BAD,t))
    bad=re.findall(MIS,t)
    print("%-34s h1=%d  sep=%d  汉字=%d  段=%d  对白段=%d(%.0f%%)  标点连写=%d  红线=%s"
          %(fn.split('/')[-1][:34],h1,sep,han,len(paras),len(dlg),len(dlg)/len(paras)*100,punct,("OK" if not bad else bad)))
