# -*- coding: utf-8 -*-
import json, subprocess, time, shutil, os
ROOT='D:/dev/github/evo/edu/ai-demos/1006-ai-creative-ad-video'
CLI=shutil.which('pippit-tool-cli')
shots=json.load(open('05-meta/shotlist.json',encoding='utf-8'))['shots']
log=open('_runs/video-runs.jsonl','a',encoding='utf-8')
have=set(f.replace('.png','') for f in os.listdir('40-keyframes'))
for s in shots:
    sid=s['shot_id']
    if sid not in have:
        print(sid,'SKIP-no-keyframe'); continue
    prompt=s['video_prompt']+' 负面：'+s['negative']
    cmd=[CLI,'generate-video','--model','seedance2.0_fast_vision','--prompt',prompt,
         '--duration','4','--ratio','9:16','--resolution','480p','--seed','20261020',
         '--image',os.path.join(ROOT,'40-keyframes',sid+'.png'),'--source','doubao_office']
    t0=time.time(); ok=False
    for attempt in (1,2):
        try:
            r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
        except Exception as e:
            print(sid,'EXC',e); time.sleep(2); continue
        out=(r.stdout or '')+(r.stderr or '')
        try:
            j=json.loads(out[out.index('{'):out.rindex('}')+1])
            if 'thread_id' in j:
                log.write(json.dumps({'shot_id':sid,'stage':'video','thread_id':j['thread_id'],'run_id':j['run_id'],'elapsed':round(time.time()-t0,1),'result':'submitted','attempt':attempt},ensure_ascii=False)+'\n'); log.flush()
                print(sid,'OK',j['thread_id'][-12:]); ok=True; break
        except Exception:
            print(sid,'FAIL',out[-120:].replace('\n',' ')); time.sleep(2)
    if not ok:
        log.write(json.dumps({'shot_id':sid,'stage':'video','result':'submit-failed'},ensure_ascii=False)+'\n'); log.flush()
log.close(); print('VIDEOS-SUBMITTED')
