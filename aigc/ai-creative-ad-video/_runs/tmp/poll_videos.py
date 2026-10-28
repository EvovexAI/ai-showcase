# -*- coding: utf-8 -*-
import json, subprocess, time, os, shutil, sys
ROOT=os.getcwd(); CLI=shutil.which('pippit-tool-cli')
ROUNDS=int(sys.argv[1]) if len(sys.argv)>1 else 1   # 默认只跑1轮快查
jobs={}
for line in open('_runs/video-runs.jsonl',encoding='utf-8'):
    r=json.loads(line)
    if r.get('result')=='submitted': jobs[r['shot_id']]=(r['thread_id'],r['run_id'])
log=open('_runs/video-runs.jsonl','a',encoding='utf-8')
for rnd in range(ROUNDS):
    done_now=[]
    for sid in sorted(jobs):
        tid,rid=jobs[sid]
        dl=os.path.join(ROOT,'_runs','downloads',sid)
        os.makedirs(dl,exist_ok=True)
        try:
            r=subprocess.run([CLI,'query-result','--thread-id',tid,'--run-id',rid,'--download-dir',dl],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
        except Exception as e:
            print(sid,'exc',str(e)[:60]); continue
        out=(r.stdout or '')+(r.stderr or '')
        try: j=json.loads(out[out.index('{'):out.rindex('}')+1])
        except Exception: print(sid,'parse-fail'); continue
        if j.get('completed'):
            vids=[f for f in os.listdir(dl) if f.endswith('.mp4')] if os.path.isdir(dl) else []
            if vids:
                tgt=os.path.join(ROOT,'09-video','final',sid+'.mp4')
                shutil.copyfile(os.path.join(dl,vids[0]),tgt)
                log.write(json.dumps({'shot_id':sid,'stage':'video','thread_id':tid,'run_id':rid,'result':'completed','file':'09-video/final/'+sid+'.mp4','round':rnd},ensure_ascii=False)+'\n'); log.flush()
                print(sid,'COMPLETED'); done_now.append(sid)
            else:
                print(sid,'completed-no-file')
        else:
            print(sid,'running')
    for s in done_now: del jobs[s]
    if not jobs: break
    if rnd<ROUNDS-1: time.sleep(15)
print('PENDING:',sorted(jobs))
