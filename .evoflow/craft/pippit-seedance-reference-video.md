---
name: pippit-seedance-reference-video
description: Use when creating or debugging a pippit-tool-cli / Seedance image-to-video or reference-video ad clip, especially when cost, watermark, voiceover, or prompt action constraints matter.
argument-hint: "[output-dir] [reference-video] [scene-image]"
user-invocable: true
allowed-tools: Bash, Read, Write
---

# Pippit + Seedance reference video pipeline

## When to use

Use for `pippit-tool-cli generate-image`, `generate-video --task-type reference`, ffmpeg reference cuts, delogo cleanup, or low-cost Seedance trials. Do not use as proof that current prices or server-side compliance labels are unchanged; re-check credit cost and output labels.

## Inputs to gather

1. Output directory and required aspect ratio (`16:9`, `9:16`, `1:1`).
2. Source/reference video and the exact time range containing subject/effects.
3. Scene description and a separate scene image plan.
4. Audio requirement: no speech, or exact Chinese voiceover line plus BGM/SFX.
5. Credit budget; default to a 480p/10s/fast trial unless the user explicitly authorizes high resolution.
6. Inspect every corner for source watermarks and note actual frame dimensions.

## Procedure

1. Cut a short reference with ffmpeg, for example:
   `ffmpeg -i src.mp4 -t 15 -c:v libx264 -crf 18 -c:a aac first15s.mp4`
2. Clean source watermarks before generation. Measure boxes from enlarged frames with crop/scale; apply delogo to every corner/time range where a mark appears.
3. Re-extract reference frames from the delogoed video; do not reuse frames extracted before cleanup.
4. Generate the scene image with explicit integer ratio enum: 2=16:9, 3=9:16, 6=1:1. For `智能图片V2.5 Pro`, provide both `--resolution` and `--effort`.
5. Build the video prompt with separate roles: reference video = subject/action/effects style only; reference image = scene/environment. Include exact action start, middle, landing, and continuation beats.
6. For a flyover/jump shot, include the literal constraint: `短暂腾空飞越一次，禁止持续悬停`.
7. Generate first at low cost: 10s, 480p/fast tier when available. Poll with `query-result --thread-id --run-id --download-dir`.
8. Verify the trial against a checklist: required action beats, subject identity, scene match, no mimicked watermark/text, audio policy, duration, resolution.
9. If audio must be speech-free, write `全程无人声无旁白无对话无歌词` in the prompt and verify locally with faster-whisper; `no speech` is the pass condition.
10. Remove any server-added `AI生成` compliance label locally after download; it cannot be reliably removed by prompt. Re-encode and inspect multiple frames.
11. Only after trial approval, rerun at 720p/1080p and record credit cost.

## CLI details

- Multiple image inputs require repeated `--image path` flags; one flag cannot receive `a + b`.
- Upload 504 or cloud sync failures are commonly transient: retry the same request before changing assets.
- On Windows, global npm binaries may be under `C:\Users\admin\AppData\Roaming\npm`. First CLI install can take about four minutes; do not kill it merely because npx appears slow.
- Check credits with `get-credit-balance`.

## Efficiency plan

- Use 480p/10s/fast for action and watermark validation.
- Resolve source watermarks before spending generation credits.
- Poll once after the model-specific expected interval rather than continuously: image roughly 1–1.5 minutes; Seedance 2.5 10s/720p reference video roughly 5 minutes.
- Keep prompt wording modular: scene, action arc, reference roles, camera, audio, negative constraints.

## Pitfalls and fixes

- Mimicked Douyin/TikTok-style text appears -> source watermark was learned -> delogo source video and re-extract frames.
- Car hovers continuously -> missing negative constraint -> add `短暂腾空飞越一次，禁止持续悬停` and specify landing plus continued driving.
- `AI生成` remains despite prompt -> server-side compliance mark -> remove locally from final output.
- High credit burn -> 1080p reference generation -> validate with 480p fast first.
- Image path suffix error -> multiple paths in one `--image` -> repeat the flag.

## Verification checklist

- Reference video has no visible watermark at multiple timestamps and all corners.
- Scene image matches requested road/city context, lighting, and blocked traffic setup.
- Prompt contains the full action arc and no-hover constraint.
- Trial clip hits every requested action beat.
- Audio matches speech/no-speech requirement; use transcription for no-speech validation.
- Final clip has no mimicked text and local compliance-label removal is visually clean.
- Credit cost, model, resolution, duration, output filename, and asset paths are recorded.
