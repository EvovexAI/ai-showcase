# -*- coding: utf-8 -*-
import json, subprocess, time, os, glob, shutil
ROOT='D:/dev/github/evo/edu/ai-demos/1006-ai-creative-ad-video'
CLI=shutil.which('pippit-tool-cli')
outs={l['asset_id']:l['out'] for l in (json.loads(x) for x in open('06-spec/image-prompts.jsonl',encoding='utf-8'))}
jobs={}
for line in open('_runs/image-runs.jsonl',encoding='utf-8'):
    r=json.loads(line)
    if r.get('result')=='submitted' and r.get('stage')=='keyframe':
        jobs[r['asset_id']]=(r['thread_id'],r['run_id'])
log=open('_runs/image-runs.jsonl','a',encoding='utf-8')
pending=dict(jobs)
for rnd in range(15):
    for aid in list(pending):
        tid,rid=pending[aid]
        dl=os.path.join(ROOT,'_runs','downloads',aid)
        os.makedirs(dl,exist_ok=True)
        try:
            r=subprocess.run([CLI,'query-result','--thread-id',tid,'--run-id',rid,'--download-dir',dl],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
        except Exception as e:
            print(aid,'query-exc',e); continue
        out=(r.stdout or '')+(r.stderr or '')
        try: j=json.loads(out[out.index('{'):out.rindex('}')+1])
        except Exception:
            print(aid,'parse-fail',out[-90:].replace('\n',' ')); continue
        if j.get('completed'):
            files=[f for f in glob.glob(dl+'/**/*.*',recursive=True) if f.lower().endswith(('.png','.jpg','.jpeg','.webp'))]
            if files:
                tgt=os.path.join(ROOT,outs[aid])
                os.makedirs(os.path.dirname(tgt),exist_ok=True)
                shutil.copyfile(files[0],tgt)
                log.write(json.dumps({'asset_id':aid,'stage':'keyframe','thread_id':tid,'run_id':rid,'result':'completed','file':outs[aid],'round':rnd},ensure_ascii=False)+'\n'); log.flush()
                print(aid,'COMPLETED'); del pending[aid]
            else:
                print(aid,'completed-no-file')
    if not pending: break
    time.sleep(20)
print('STILL-PENDING:',list(pending))
