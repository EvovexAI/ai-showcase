# 🎬 宣传视频制作系统 (ai-video-promo-003)

从 **ai-video-decompose (1002)** 拆解出的**制作策划 + 配音**专用系统。
后端逻辑与 [douyin-video-pipeline](../douyin-video-pipeline) 对齐，
但精简掉了下载/拆解/视觉识别等只属于「拆解侧」的部分。

## 📋 项目结构

```
ai-video-promo-003/
├── scripts/                          # 制作 + 配音 + 工作台核心脚本
│   ├── promo_server.py               # 本地 Web/HTTP 服务器（端口 8766）
│   ├── volc_tts.py                   # 火山 OpenSpeech v3 TTS 客户端
│   ├── tts_settings.py               # 配音设置（公开/掩码、env 回退）
│   ├── evoflow_client.py             # EvoFlow OpenAI 兼容 chat
│   ├── workbench_api.py              # 工作台 REST API（tasks/skills/drafts/...）
│   ├── skill_runners.py              # Cursor 技能运行器
│   ├── automation_scheduler.py       # 自动化任务调度
│   ├── export_tts_voices.py          # 把 EvoFlow voices 导出到 config/tts_voices.json
│   ├── paths.py                      # 路径 + productions 工具
│   └── requirements.txt              # Python 依赖（httpx）
│
├── web/                              # Web UI（从 1004 复制）
│   ├── index.html                    # 起号拆解台 SPA
│   └── assets/
│       ├── app.js                    # 前端主脚本
│       ├── nav.js                    # 侧边栏导航
│       ├── style.css                 # 样式
│       └── tts-speaker-picker.js     # 配音人选 UI
│
├── config/                           # 配置文件
│   ├── tts.json                      # TTS 资源 ID + 默认音色
│   ├── tts_voices.json               # 完整音色清单（291 个）
│   └── .env.example                  # 环境变量样例
│
├── productions/                      # 生成的策划稿（JSON + audio/*.mp3）
├── workbench/                        # 工作台本地数据（自动创建）
├── pyproject.toml
├── README.md
└── INTEGRATION_GUIDE.md
```

## 🚀 快速开始

### 1. 安装依赖

```powershell
cd ai-video-promo-003
pip install -r scripts/requirements.txt
```

### 2. 配置 TTS

复制 `config/.env.example` → `config/.env`，填入火山语音 API Key：

```powershell
$env:ARK_API_KEY = "ark-xxxx..."   # Agent Plan Key（ark- 开头）
# 或
$env:VOLCENGINE_SPEECH_API_KEY = "xxxx..."
```

也可以直接在 Web UI 的「设置 → 配音」里填入并保存。

### 3. 启动制作服务器

```powershell
python scripts/promo_server.py
```

打开 http://localhost:8766 即可使用。

## 🎙 核心功能

### 1️⃣ 配音系统

使用火山 TTS（OpenSpeech v3）进行自动配音：
- 资源：`seed-tts-2.0`（默认）
- 默认音色：小何 2.0（`zh_female_xiaohe_uranus_bigtts`）
- 完整音色清单：291 个（从 `config/tts_voices.json` 加载）
- 支持 Agent Plan Key（`ark-` 开头自动走 plan 端点 + 失败回退）
- 试听 + 批量生成策划稿分镜配音

### 2️⃣ 策划系统

按 1004 一样的 productions 格式管理策划稿：
- 分镜（shots）含 time_range / visual / voiceover / subtitle
- 支持 AI 润色分镜（`/api/productions/{id}/ai-revise`，EvoFlow 驱动）
- 支持一键配音（`/api/productions/{id}/synthesize`）
- 配音输出到 `productions/{plan_id}/audio/shot_NN_<hash>.mp3`

### 3️⃣ 工作台 API

与 1004 一致——tasks / skills / experiences / topic-collections / library / drafts
/ automations / 夜班任务 / 批量派 AI / 飞书推送 / 写作润色 / 增粉报告 / 同步 push-pull。
详见 `http://localhost:8766/api/workbench/...`。

## 🔌 API 速查（1003 自有端点）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| GET | `/api/settings/tts` | 读取 TTS 设置（apiKey 已掩码） |
| POST | `/api/settings/tts` | 更新 TTS 设置（`{apiKey, ttsResourceId, ttsSpeaker}`） |
| GET | `/api/productions` | 策划列表 |
| POST | `/api/productions` | 新建策划稿（`{title, goal?, ...}`） |
| GET | `/api/productions/{id}` | 读取策划稿（含 audio_manifest） |
| PATCH | `/api/productions/{id}` | 更新策划稿 |
| DELETE | `/api/productions/{id}` | 删除策划稿 |
| POST | `/api/productions/{id}/ai-revise` | AI 润色分镜（`{instruction}`） |
| POST | `/api/productions/{id}/synthesize` | 启动配音任务（异步 job_id） |
| GET | `/api/productions/{id}/audio/{file}` | 读取配音 mp3 |
| POST | `/api/tts/preview` | 启动 TTS 试听（`{text, speaker?}`） |
| GET | `/api/tts/preview/{job_id}.mp3` | 试听音频 |
| GET | `/api/jobs/{id}` | 查询异步任务状态 |
| GET/POST/PATCH/DELETE | `/api/workbench/*` | 工作台 API 透传 |

## 📁 脚本说明

| 脚本 | 用途 |
|------|------|
| `promo_server.py` | 本地 HTTP 服务器（端口 8766），跑通所有端点 |
| `volc_tts.py` | 火山 OpenSpeech v3 客户端 |
| `tts_settings.py` | TTS 配置管理（公开/掩码/env 回退） |
| `evoflow_client.py` | EvoFlow OpenAI 兼容 chat |
| `workbench_api.py` | 工作台 REST API（与 1004 一致） |
| `skill_runners.py` | Cursor 技能运行器 |
| `automation_scheduler.py` | 自动化任务调度 |
| `export_tts_voices.py` | 从 EvoFlow volcengine-tts-speakers.js 导出 tts_voices.json |
| `paths.py` | 路径 + productions 工具 |

## 🔧 配置文件

### config/tts.json
```json
{
  "ttsResourceId": "seed-tts-2.0",
  "ttsSpeaker": "zh_female_xiaohe_uranus_bigtts"
}
```

### config/.env.example
```
VOLCENGINE_API_KEY=your-volcengine-api-key-here
TTS_RESOURCE_ID=seed-tts-2.0
TTS_SPEAKER=zh_female_xiaohe_uranus_bigtts
```

## 🔗 关联项目

- **ai-video-decompose (1002)** — 视频拆解系统（**来源项目**，但当前 1002 仓库里
  已经不包含策划/配音代码，全部在本仓库 1003 与 1004 中维护）
- **ai-douyin-video-pipeline (1004)** — 起号流水线（含本仓库相同的后端 + 拆解侧）
- **ai-poster-editor (1001)** — 海报编辑系统

## ⚠️ 注意事项

1. **端口冲突**：1003 默认 `8766`，1004 默认 `8765`，互不冲突。
2. **API 密钥**：TTS 需要 Agent Plan Key (`ark-` 开头) 或旧版 OpenSpeech Key。
3. **存储**：`productions/` 与 `workbench/data/` 自动创建；建议 `.gitignore` 排除。
4. **EvoFlow**：可选集成——未配置时 `evoflow_chat` 自动降级为本地提示。

## 🎯 下一步

1. ✓ 配置 TTS API 密钥
2. ✓ 启动 `python scripts/promo_server.py` 访问 http://localhost:8766
3. ✓ 在「设置 → 配音」填写 API Key
4. ✓ 创建策划稿并一键配音
5. ⏳ 集成 EvoFlow 让 AI 帮你润色分镜
6. ⏳ 把 1002 的拆解结果拉过来当策划输入

---

**制作策划 × 配音 × 工作台 = 完整的宣传视频自动化流水线** 🎬
