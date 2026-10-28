# -*- coding: utf-8 -*-
import json, subprocess, sys, time
ROOT='D:/dev/github/evo/edu/ai-demos/1006-ai-creative-ad-video'
_q=lambda s:s.replace('"','')
lines=[json.loads(l) for l in open('06-spec/image-prompts.jsonl',encoding='utf-8')]
pre=[l for l in lines if l['type'] in ('threeview','fourview','prop-front')]
skip=sys.argv[1] if len(sys.argv)>1 else ''  # 已提交的 asset_id
log=open('_runs/image-runs.jsonl','a',encoding='utf-8')
for l in pre:
    if l['asset_id']==skip: continue
    cmd='pippit-tool-cli generate-image --model "智能图片V2.5 Fast" --prompt ' + _q(l['prompt']) + ' --ratio 2 --resolution 1K --source doubao_office'
    t0=time.time(); ok=False
    for attempt in (1,2):
        r=subprocess.run(cmd,shell=True,capture_output=True,text=True,encoding='utf-8',timeout=180)
        out=(r.stdout or '')+(r.stderr or '')
        try:
            j=json.loads(out[out.index('{'):out.rindex('}')+1])
            if 'thread_id' in j:
                log.write(json.dumps({'asset_id':l['asset_id'],'type':l['type'],'stage':'pre-asset','thread_id':j['thread_id'],'run_id':j['run_id'],'elapsed':round(time.time()-t0,1),'result':'submitted','attempt':attempt},ensure_ascii=False)+'\n'); log.flush()
                print(l['asset_id'],'OK',j['thread_id'],j['run_id']); ok=True; break
        except Exception:
            pass
        print(l['asset_id'],'attempt',attempt,'FAIL:',out[-200:]); time.sleep(3)
    if not ok:
        log.write(json.dumps({'asset_id':l['asset_id'],'type':l['type'],'stage':'pre-asset','result':'submit-failed'},ensure_ascii=False)+'\n'); log.flush()
log.close()
