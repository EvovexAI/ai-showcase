---
name: douyin-video-pipeline
description: >-
  短视频内容拆解流水线（content）：钩子/人群/黄金句/节奏/起号报告。
  抖音短链原生；其它平台 yt-dlp。入口 :8765 API / CLI / Web。
  AIGC 反推请用独立项目 1008-aigc-prompt-reverse（:8768）。
  Use for 视频拆解、口播分析、爆款对标、起号。
---

# 视频拆解流水线（内容洞察 / 起号）

项目根 `$PROJ`：`D:\dev\github\feishu_downloads/ai-showcase/self-media/douyin-video-pipeline`

> **反推 AIGC 提示词**已独立为 `feishu_downloads/ai-showcase/aigc/aigc-prompt-reverse`（端口 8768）。本技能只做 `content`。

下载 → 口播转写 → **关键帧** → 章节 → 内容洞察报告（双写 `data/reports/` + 页面）。

| `analysis_mode` | 何时用 | 关键帧默认 | 产出 |
|-----------------|--------|-----------|------|
| `content` | 学爆款、起号、钩子人群 | `transcript` | 速览 + 可学习点 + 结构/情绪 |

**意图识别**  
- 「拆解 / 分析 / 起号 / 钩子」→ 本技能（1004）  
- 「反推提示词 / AIGC / 即梦 / Seedance / 复刻」→ 改走 **1008** / 技能 `aigc-prompt-reverse`

---

## Agent 标准作业

```
1. 起服务（若需）：py -3.12 $PROJ/scripts/web_server.py → curl.exe -s http://127.0.0.1:8765/api/health
2. POST /api/analyze
   { "share_text":"…", "analysis_mode":"content", "keyframe_mode":"transcript" }
3. 轮询 /api/jobs/{id} → done
4. 汇报：⚡一句话速览 + 🎯可参考学习的点 + 报告路径
```

Web：`http://127.0.0.1:8765`
