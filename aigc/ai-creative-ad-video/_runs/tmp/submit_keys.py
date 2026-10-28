# -*- coding: utf-8 -*-
import json, subprocess, time, shutil, os
ROOT='D:/dev/github/evo/edu/ai-demos/1006-ai-creative-ad-video'
CLI=shutil.which('pippit-tool-cli')
lines=[json.loads(l) for l in open('06-spec/image-prompts.jsonl',encoding='utf-8')]
keys=[l for l in lines if l['type']=='keyframe']
log=open('_runs/image-runs.jsonl','a',encoding='utf-8')
for l in keys:
    cmd=[CLI,'generate-image','--model','智能图片V2.5 Fast','--prompt',l['prompt'],'--ratio','3','--resolution','1K','--source','doubao_office']
    for ref in l['ref']:
        cmd += ['--image', os.path.join(ROOT, ref.replace(chr(92), '/'))]
    t0=time.time(); ok=False
    for attempt in (1,2):
        try:
            r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
        except Exception as e:
            print(l['asset_id'],'attempt',attempt,'EXC:',e); time.sleep(3); continue
        out=(r.stdout or '')+(r.stderr or '')
        try:
            j=json.loads(out[out.index('{'):out.rindex('}')+1])
            if 'thread_id' in j:
                log.write(json.dumps({'asset_id':l['asset_id'],'type':'keyframe','stage':'keyframe','thread_id':j['thread_id'],'run_id':j['run_id'],'elapsed':round(time.time()-t0,1),'result':'submitted','attempt':attempt,'refs':len(l['ref'])},ensure_ascii=False)+'\n'); log.flush()
                print(l['asset_id'],'OK',j['thread_id'][-12:],j['run_id'][-12:]); ok=True; break
        except Exception:
            print(l['asset_id'],'attempt',attempt,'FAIL:',out[-140:].replace('\n',' ')); time.sleep(3)
    if not ok:
        log.write(json.dumps({'asset_id':l['asset_id'],'type':'keyframe','stage':'keyframe','result':'submit-failed'},ensure_ascii=False)+'\n'); log.flush()
log.close(); print('SUBMIT-DONE')
