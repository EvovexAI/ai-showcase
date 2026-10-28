# -*- coding: utf-8 -*-
"""生成流水线（合并原 _runs/tmp 下 8 个散脚本，2026-10-20 收拢；v2 增加 verify）

用法（在仓库根目录执行）:
  python _runs/pipeline.py submit-images             # 提交前置图（3三视图+5四视图+3道具, 16:9）
  python _runs/pipeline.py submit-keyframes          # 提交 15 张首帧（9:16, 自动带 ref_images）
  python _runs/pipeline.py submit-keyframes S10      # 只补提交指定镜
  python _runs/pipeline.py submit-videos             # 提交全部视频（4s/480p/9:16/同seed）
  python _runs/pipeline.py submit-videos S07 S11     # 只重拍指定镜
  python _runs/pipeline.py poll images  [轮数=3]     # 轮询图片任务并落位（mp4预览自动ffmpeg抽帧）
  python _runs/pipeline.py poll videos  [轮数=3]     # 轮询视频任务并落位到 09-video/final
  python _runs/pipeline.py verify                    # 盘点交付物数量与文件健康度
  python _runs/pipeline.py verify <图片/视频路径>     # 裁四角快照到 _runs/tmp/wmcheck/ 供水印目检

依赖: 06-spec/image-prompts.jsonl（26行指令台账）、05-meta/shotlist.json、pippit-tool-cli、ffmpeg(可选兜底)
台账: _runs/image-runs.jsonl / _runs/video-runs.jsonl（只追加）
"""
import json, os, shutil, subprocess, sys, time, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = shutil.which('pippit-tool-cli')
IMG_MODEL, VID_MODEL = '智能图片V2.5 Fast', 'seedance2.0_fast_vision'
SEED, DURATION = '20261020', '4'   # 全片统一 seed（style-lock §0）
IMG_LOG, VID_LOG = '_runs/image-runs.jsonl', '_runs/video-runs.jsonl'


def _abs(p):
    return os.path.join(ROOT, p.replace(chr(92), '/'))


def _cli(args, timeout=240):
    r = subprocess.run([CLI] + args, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=timeout)
    out = (r.stdout or '') + (r.stderr or '')
    j = json.loads(out[out.index('{'):out.rindex('}') + 1])
    return j


def _log(path, row):
    with open(os.path.join(ROOT, path), 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def prompts():
    with open(os.path.join(ROOT, '06-spec', 'image-prompts.jsonl'), encoding='utf-8') as f:
        return [json.loads(l) for l in f]


def shots():
    with open(os.path.join(ROOT, '05-meta', 'shotlist.json'), encoding='utf-8') as f:
        return json.load(f)['shots']


def _submit(cmd, logfile, row):
    tag = row.get('asset_id') or row.get('shot_id')
    for attempt in (1, 2):
        try:
            j = _cli(cmd)
            if 'thread_id' in j:
                row.update(thread_id=j['thread_id'], run_id=j['run_id'],
                           result='submitted', attempt=attempt)
                _log(logfile, row)
                print(tag, 'OK', j['thread_id'][-12:])
                return True
        except Exception as e:
            print(tag, 'attempt', attempt, 'FAIL', str(e)[:90])
            time.sleep(3)
    row['result'] = 'submit-failed'
    _log(logfile, row)
    return False


def submit_images(only=()):
    """前置图：三视图/四视图/道具正视，16:9，无参考图"""
    for l in prompts():
        if l['type'] == 'keyframe' or (only and l['asset_id'] not in only):
            continue
        cmd = [CLI, 'generate-image', '--model', IMG_MODEL, '--prompt', l['prompt'],
               '--ratio', '2', '--resolution', '1K', '--source', 'doubao_office']
        _submit(cmd, IMG_LOG, {'asset_id': l['asset_id'], 'type': l['type'], 'stage': 'pre-asset'})


def submit_keyframes(only=()):
    """首帧：9:16，必须带 ref_images（三视图/四视图/道具），禁止空参"""
    for l in prompts():
        if l['type'] != 'keyframe' or (only and l['asset_id'] not in only):
            continue
        cmd = [CLI, 'generate-image', '--model', IMG_MODEL, '--prompt', l['prompt'],
               '--ratio', '3', '--resolution', '1K', '--source', 'doubao_office']
        for ref in l['ref']:
            cmd += ['--image', _abs(ref)]
        _submit(cmd, IMG_LOG, {'asset_id': l['asset_id'], 'type': 'keyframe',
                               'stage': 'keyframe', 'refs': len(l['ref'])})


def submit_videos(only=()):
    """逐镜 I2V：seedance2.0_fast_vision / 4s / 480p / 9:16 / 全片同 seed"""
    kf = os.path.join(ROOT, '40-keyframes')
    have = {f[:-4] for f in os.listdir(kf)} if os.path.isdir(kf) else set()
    for s in shots():
        sid = s['shot_id']
        if (only and sid not in only) or sid not in have:
            print(sid, 'SKIP(no-keyframe)')
            continue
        cmd = [CLI, 'generate-video', '--model', VID_MODEL,
               '--prompt', s['video_prompt'] + ' 负面：' + s['negative'],
               '--duration', DURATION, '--ratio', '9:16', '--resolution', '480p',
               '--seed', SEED, '--image', os.path.join(kf, sid + '.png'),
               '--source', 'doubao_office']
        _submit(cmd, VID_LOG, {'shot_id': sid, 'stage': 'video'})


def poll(kind, rounds=3):
    """轮询下载并落位：images→30-assets/40-keyframes，videos→09-video/final"""
    logfile = IMG_LOG if kind == 'images' else VID_LOG
    stages = ('pre-asset', 'keyframe', 'keyframe-retry') if kind == 'images' else ('video',)
    outs = {l['asset_id']: l['out'] for l in prompts()}
    idkey = 'asset_id' if kind == 'images' else 'shot_id'
    jobs = {}
    with open(os.path.join(ROOT, logfile), encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            if r.get('result') == 'submitted' and r.get('stage') in stages:
                jobs[r[idkey]] = (r['thread_id'], r['run_id'])
    pending = dict(jobs)
    log = open(os.path.join(ROOT, logfile), 'a', encoding='utf-8')
    for rnd in range(rounds):
        for aid in list(pending):
            tid, rid = pending[aid]
            dl = os.path.join(ROOT, '_runs', 'downloads', aid)
            os.makedirs(dl, exist_ok=True)
            try:
                j = _cli(['query-result', '--thread-id', tid, '--run-id', rid,
                          '--download-dir', dl], timeout=180)
            except Exception as e:
                print(aid, 'exc', str(e)[:60]); continue
            if not j.get('completed'):
                continue
            files = glob.glob(dl + '/**/*.*', recursive=True)
            if not files:
                print(aid, 'completed-no-file'); continue
            if kind == 'images':
                f0 = files[0]
                tgt = os.path.join(ROOT, outs.get(aid, '40-keyframes/%s.png' % aid))
                if f0.lower().endswith('.mp4') and tgt.endswith('.png') and shutil.which('ffmpeg'):
                    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f0,
                                    '-frames:v', '1', tgt], check=False)
                else:
                    shutil.copyfile(f0, tgt)
            else:
                f0 = [f for f in files if f.lower().endswith('.mp4')][0]
                tgt = os.path.join(ROOT, '09-video', 'final', aid + '.mp4')
                shutil.copyfile(f0, tgt)
            rel = os.path.relpath(tgt, ROOT).replace(chr(92), '/')
            log.write(json.dumps({idkey: aid, 'stage': ('keyframe' if kind == 'images' else 'video'),
                                  'thread_id': tid, 'run_id': rid, 'result': 'completed',
                                  'file': rel, 'round': rnd}, ensure_ascii=False) + '\n')
            log.flush()
            print(aid, 'COMPLETED ->', rel)
            del pending[aid]
        if not pending:
            break
        time.sleep(15)
    print('PENDING:', sorted(pending))


def verify(wm=None):
    """无参：盘点三个交付目录数量+文件健康度；传路径：裁四角快照供水印目检"""
    if wm:
        src = _abs(wm)
        outdir = os.path.join(ROOT, '_runs', 'tmp', 'wmcheck')
        os.makedirs(outdir, exist_ok=True)
        base = os.path.splitext(os.path.basename(src))[0]
        for tag, pos in (('TL', '0:0'), ('TR', 'iw-240:0'),
                         ('BL', '0:ih-140'), ('BR', 'iw-240:ih-140')):
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src,
                            '-vf', 'crop=240:140:%s' % pos,
                            os.path.join(outdir, base + '_' + tag + '.png')], check=False)
        print('四角快照 ->', outdir)
        return
    expect = [('30-assets', 11), ('40-keyframes', 15), ('09-video/final', 15)]
    for d, n in expect:
        files = [f for f in glob.glob(os.path.join(ROOT, d, '**', '*.*'), recursive=True)
                 if os.path.getsize(f) > 10240]
        ok = 'OK' if len(files) >= n else '!! MISSING'
        print('%-16s %2d / %d  %s' % (d, len(files), n, ok))


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or not CLI:
        print(__doc__); sys.exit(0 if a else 1)
    cmd, rest = a[0], a[1:]
    if cmd == 'submit-images':
        submit_images(tuple(rest))
    elif cmd == 'submit-keyframes':
        submit_keyframes(tuple(rest))
    elif cmd == 'submit-videos':
        submit_videos(tuple(rest))
    elif cmd == 'poll':
        poll(rest[0], int(rest[1]) if len(rest) > 1 else 3)
    elif cmd == 'verify':
        verify(rest[0] if rest else None)
    else:
        print(__doc__)
