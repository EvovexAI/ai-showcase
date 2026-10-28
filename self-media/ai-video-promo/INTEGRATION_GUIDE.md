# 宣传视频制作系统集成指南

## 来源

本项目从 **ai-video-decompose (1002)** 的制作策划和配音模块拆解而出，
后端逻辑与 [douyin-video-pipeline](../douyin-video-pipeline) 对齐。

## 与 1002、1004 的关系

```
ai-video-decompose (1002) ─ 视频拆解侧
        │
        │   ← 历史上 1002 仓库的策划/配音代码被剥离
        │
        ├─→ ai-video-promo-003 (本仓库)        ← 制作 + 配音 + 工作台
        │       port 8766 · Python-only 复刻
        │
        └─→ ai-douyin-video-pipeline (1004)    ← 制作 + 配音 + 拆解
                port 8765 · 完整 web UI + 前端
```

**1003 vs 1004 关键差异**：

| 维度 | 1003（本仓库） | 1004 |
|---|---|---|
| 端口 | 8766 | 8765 |
| 拆解侧 | ✗ | ✓（download/analyze/vision） |
| TTS | ✓ | ✓ |
| 策划 | ✓ | ✓ |
| 工作台 | ✓ | ✓ |
| Web UI | ✓（来自 1004） | ✓（原生） |
| miniprogram / cloud-run | ✗ | ✓ |

1003 是 1004 的**精简 Python-only 复刻**——保持 1003 仓库自包含、无前端框架依赖。

## 核心模块

### 1. 火山 TTS 引擎 (`volc_tts.py`)

**职责**: 文本转语音、音频生成（OpenSpeech v3）

**主要 API**:
- `synthesize_speech(text, *, api_key, speaker=None, resource_id=None, preview=False)`
  返回 `(mp3_bytes, speaker_used)`。

**使用示例**:

```python
from volc_tts import synthesize_speech
from tts_settings import get_resolved_credentials

api_key, resource, speaker = get_resolved_credentials()
audio, used = synthesize_speech(
    text="欢迎使用 EvoFlow 制作系统",
    api_key=api_key,
    speaker="zh_female_xiaohe_uranus_bigtts",
    resource_id=resource,
)
open("voiceover.mp3", "wb").write(audio)
```

### 2. TTS 配置管理 (`tts_settings.py`)

**职责**: 管理 TTS 配置和语音库

**主要 API**:
- `load_tts_settings()` → dict
- `save_tts_settings(updates)` → dict（公开形式）
- `public_tts_settings()` → dict（apiKey 已掩码，含完整 voices 列表）
- `get_resolved_credentials()` → `(api_key, resource_id, speaker)`
- `tts_configured()` → bool

**掩码规则**: `mask_api_key("ark-abc1234567899e8e")` → `"ark-********9e8e"`,
避免在前端 / 日志里泄露完整 Key。`save_tts_settings` 收到含 `********` 的旧值
会被识别为未修改，跳过写入。

**环境变量回退顺序**（自动识别）:
1. `VOLCENGINE_SPEECH_API_KEY`
2. `BYTEPLUS_SEED_SPEECH_API_KEY`
3. `ARK_API_KEY`
4. `VOLCENGINE_API_KEY`
5. `VOLCENGINE_TTS_ACCESS_TOKEN`

若已设置 env，则不再覆盖文件里的值。

### 3. EvoFlow 集成 (`evoflow_client.py`)

**职责**: 与 EvoFlow 制作流水线集成（OpenAI 兼容 chat）

**主要 API**:
- `chat_completion(prompt, *, model=None, system=None, skill_id=None)` → `(text, meta)`
- `try_chat_or_hint(prompt, *, skill_id=None, context=None)` → `(text, used_evoflow, status)`
  永不抛错——未启用时降级为本地提示。
- `load_evoflow_config()` → dict

**预置 Skill 提示词**:
- `douyin-analyze` — 抖音拆解助手
- `viral-collect` — 爆款搜集
- `plan-from-report` — 视频策划助手
- `cover-gen` — 封面生成助手

### 4. 工作台 API (`workbench_api.py`)

**职责**: 与 Cursor 工作台集成

**主要 API**:
- `handle_get(path, query)` / `handle_post(path, body, *, start_job, run_skill_fn)`
  / `handle_patch(path, body)` / `handle_delete(path)` → `(data, status)`
- `shell_counts()` / `viral_videos_list()` / `list_drafts()` 等

**前端约定**: `/api/workbench/*` 透传到 `handle_*`。

## 工作流

```
策划输入 (web UI)
  ↓
[创建 productions/{id}.json]
  ↓
[AI 润色分镜] (evoflow_client.py)
  ↓
[批量配音] (volc_tts.py, 每段 → audio/shot_NN.mp3)
  ↓
[交付 EvoFlow 制作] (evoflow_client.py → submit job)
  ↓
[等待渲染]
  ↓
[导出成片]
```

## 配置流程

### 步骤 1: 环境变量

```powershell
# PowerShell
$env:ARK_API_KEY = "ark-xxxx..."
$env:VOLCENGINE_SPEECH_API_KEY = "xxxx..."
# 可选：EvoFlow
$env:EVOFLOW_GATEWAY_URL = "http://127.0.0.1:8080"
$env:EVOFLOW_API_KEY = "..."
```

### 步骤 2: 配置文件

`config/tts.json`:
```json
{
  "ttsResourceId": "seed-tts-2.0",
  "ttsSpeaker": "zh_female_xiaohe_uranus_bigtts"
}
```

`config/tts_voices.json`: 完整音色清单（已从 1004 复制，291 条）。

### 步骤 3: 启动

```powershell
cd ai-video-promo-003
pip install -r scripts/requirements.txt
python scripts/promo_server.py
# → http://localhost:8766
```

## 功能集成示例

```python
#!/usr/bin/env python3
"""完整的宣传视频生成流程。"""
from pathlib import Path
import httpx

API = "http://127.0.0.1:8766"

def create_promo(script_text: str, plan_id: str) -> dict:
    # 1. 创建策划稿
    httpx.post(f"{API}/api/productions", json={"title": plan_id, "full_script": script_text})
    # 2. 启动配音
    job = httpx.post(f"{API}/api/productions/{plan_id}/synthesize").json()
    # 3. 轮询任务
    while True:
        status = httpx.get(f"{API}/api/jobs/{job['job_id']}").json()
        if status["status"] in {"done", "error"}:
            return status
```

## 扩展点

### 1. 添加新的 TTS 音色

直接编辑 `config/tts_voices.json`，或运行：
```powershell
python scripts/export_tts_voices.py
```

### 2. 集成其他制作平台

继承 `EvoFlowClient`（或 `evoflow_client` 的函数），实现同样的 chat 协议。

### 3. 自定义工作台端点

在 `workbench_api.py` 的 `handle_get/handle_post` 中加分支即可，
无需修改 `promo_server.py`。

## 故障排查

### 问题 1: TTS API Key 报错

**症状**: `RuntimeError: 未配置火山语音 API Key`

**解决**:
1. Web UI → 设置 → 配音 → 填写 Key（`ark-` 开头）
2. 或设置环境变量 `$env:ARK_API_KEY = "..."`
3. Key 不能含 `********`——这表示前端把掩码值原样回传了，请重新输入

### 问题 2: 配音音色错误

**症状**: 试听时音色不对

**解决**:
1. 确认 `config/tts.json` 里的 `ttsSpeaker` 是合法 voice id
2. 资源 ID 需匹配——`seed-tts-2.0` 对应 `*_uranus_bigtts` 系列；
   `seed-icl-2.0` 对应 `s_*` 系列。`volc_tts.resolve_tts_resource_id()` 会自动推断。

### 问题 3: EvoFlow 调用失败

**症状**: AI 润色 / 技能运行返回「本地模式」提示

**解决**:
1. 在 `workbench/config/evoflow.json` 填入 `base_url` 和 `api_key`
2. 或设置 `EVOFLOW_GATEWAY_URL` + `EVOFLOW_API_KEY` 环境变量
3. EvoFlow 必须开放 `/v1/chat/completions` 端点（OpenAI 兼容）

## 下一步

1. ✓ 配 TTS Key
2. ✓ 跑 `python scripts/promo_server.py`
3. ✓ 创建第一个策划稿
4. ⏳ 集成 EvoFlow 让 AI 帮你润色
5. ⏳ 把 1002 的拆解结果回灌为 1003 的策划输入

---

**集成指南完毕** 📚
