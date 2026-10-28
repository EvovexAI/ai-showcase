---
name: aigc-prompt-reverse
description: >-
  短视频 AIGC 提示词反推：关键帧图（约 20 秒 5～6 张）+ 音频 → 多模态模型理解 →
  反推视频生成提示词。权威稿 prompts/reverse-system.md。入口 :8768。
  Use for 反推提示词、AIGC、video-to-prompt、即梦、Seedance、复刻。
---

# AIGC 提示词反推

项目根：`D:\dev\github\feishu_downloads/ai-showcase/aigc/aigc-prompt-reverse`

## 方法（简单）

```
原视频 → 关键帧图（少量均匀）+ 音频 → 模型（看图听声）→ 生成提示词 → 去生成视频
```

- 频次：约 **20 秒取 5～6 张**（`interval_seconds ≈ 3.5`）  
- 系统提示词：`prompts/reverse-system.md`（页面可改）

| 参数 | 推荐 |
|------|------|
| `analysis_mode` | `prompt_reverse` |
| `keyframe_mode` | `interval` |
| `interval_seconds` | `3.5` |

## Agent 作业

```
1. 起服务 → :8768/api/health
2. POST /api/analyze { share_text, analysis_mode:prompt_reverse, keyframe_mode:interval, interval_seconds:3.5 }
3. 轮询 done
4. 读 scenes/*.jpg + 对照音频；按 reverse-system.md 写生成提示词
5. 回写 prompt_reverse.json + report.md → 汇报
```

Web：`http://127.0.0.1:8768`
