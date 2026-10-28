---
name: evoflow-onboarding
description: >-
  把「视频拆解工作台」(feishu_downloads/ai-showcase/self-media/douyin-video-pipeline) 一键接入 EvoFlow(UFO) 的安装与操作说明。
  当用户说「把这个项目接入 EvoFlow/UFO」「安装技能」「让视频拆解师干活」「接入扩展面板」、
  「导入 UFO 并新建技能」时使用。自动执行 B1 扩展注册 + B2 技能装库 + B4 知识库同步，
  并核验 B3 员工与 B5 日常使用。样例项目:1004 抖音视频拆解。
---

# 视频拆解工作台 · EvoFlow(UFO) 接入与操作技能

> 本技能 = **给智能体看的安装/操作说明书**。照着执行即可把项目接入 EvoFlow，
> 之后日常拆视频也按本说明操作。
> 项目根 `$PROJ` = **用户消息里给出的解压路径**（以用户实际路径为准，不要假设盘符；
> 本文件会随技能一起复制进 EvoFlow 技能库，原目录相对路径不再有效）。
> 一条命令即可完成接入：

```powershell
powershell -ExecutionPolicy Bypass -File "$PROJ\scripts\install-into-evoflow.ps1"
```

---

## 1. 这个技能是什么（30 秒）

把一条视频变成**能直接抄作业的拆解报告**：粘贴分享链接 → 自动下载 → 口播转写 →
关键帧 → 章节 → 洞察分析（钩子/人群/黄金句/节奏/结构）→ Markdown 报告。
报告双写：本地 `data/reports/` + EvoFlow 知识库「视频拆解报告库」。

**已接入 EvoFlow 的形态（四件套）**：

| 1004 里的东西 | EvoFlow 里的形态 | 状态 |
|---|---|---|
| `evoflow.extension.json` | 扩展应用（面板侧栏入口，托管 8765） | 注册即生效 |
| `skills/douyin-video-pipeline/` | 技能（教 AI 操作流水线） | 本脚本负责装库 |
| `data/reports/` | 知识库（Vault，报告可检索） | 本脚本负责同步 |
| — | 员工「视频拆解师」(video-analyst) | 你按第 3 节创建 |

**接入完整顺序**：跑脚本（B1+B2+B4）→ 你创建员工（B3）→ 验收（B5）。缺员工 = 无法使用。

---

## 2. 安装（接入）—— 幂等，可反复跑

**环境准备归你（Agent）**：用户不做任何安装。开跑前先自检并补齐
Python 3.12（系统级，勾 PATH）、ffmpeg（加入 PATH）、`requirements.txt` 依赖；
缺什么装什么，装完再执行接入脚本。

```powershell
powershell -ExecutionPolicy Bypass -File "$PROJ\scripts\install-into-evoflow.ps1"
```

脚本自动做 B1+B2+B4（不需要 `evoflow` CLI，本机 CLI 会卡死）：

| 步骤 | 动作 | 验证 |
|---|---|---|
| B1 | 写 `~/.evoflow/ui-extensions/registry.json`，注册 `douyin-video-pipeline` | 面板「扩展」出现「视频拆解」 |
| B2 | 把 `skills/*` 拷进 `~/.evoflow/profiles/default/skills/custom/` | 技能列表两个技能 enabled |
| B4 | 建/复用知识库「视频拆解报告库」并导入 `data/reports` | 搜「钩子」能命中 |

> 注意：EvoFlow 数据目录用**用户正式环境 `~/.evoflow`**（不带 `-dev`；
> `-dev` 只是开发调试目录，用户机器上不存在，脚本不写那里）。

> 知识库同步走 EvoFlow 内置 gateway（`/api/knowledge/owned/*`），无需额外 python 环境。
> 若提示 gateway 不可达：确认 EvoFlow 桌面端已启动，再重跑本脚本即可。

### 手动核验（不必依赖脚本回显）

```powershell
# 扩展注册表
Get-Content "$env:USERPROFILE\.evoflow\ui-extensions\registry.json" -Raw
# 技能
Get-ChildItem "$env:USERPROFILE\.evoflow\profiles\default\skills\custom" -Directory | Select-Object -ExpandProperty Name
# 员工（B3 由你负责创建；没有就回第 3 节）
# 面板「智能体员工」页看「视频拆解师」状态 active
```

---

## 3. 员工（B3）—— 新环境没有，由你创建

**新解压的环境默认没有员工**，接入时必须创建（这是安装的一部分，不要跳过）：

1. 先查：在面板「智能体员工」页确认是否已有「视频拆解师」
2. 没有 → 用你的平台能力创建（agents create + employees hire / 员工页雇佣皆可），按此模板：

- **岗位名称**：视频拆解师（agent_code 建议 `video-analyst` / `douyin-analyst`）
- **职责**：内容拆解（钩子/起号）；归档知识库。AIGC 反推请用独立项目 1008
- **挂载技能**：douyin-video-pipeline、evoflow-onboarding
- **绑定知识库**：视频拆解报告库（B4 创建的那个）
- **管辖工作空间**：`<解压路径>`（即第 2 节 `$PROJ`，务必与实际解压路径一致）
- **交接审批策略**：谨慎型；**上班频率**：手动触发

---

## 4. 日常使用（B5）—— 两种姿势随时切

### 姿势 A：让员工拆（推荐）

- **「让视频拆解师拆解这条视频：<链接>」** → `analysis_mode=content`

员工会执行（详见 `douyin-video-pipeline` 技能）：

```
1. 起服务（若 8765 未响应）：py -3.12 "$PROJ\scripts\web_server.py"  # 系统 Python 3.12
2. POST /api/analyze（content + keyframe_mode）
3. 轮询 done → 汇报速览与可学习点
4. 同步知识库：import-folder 或重跑 install-into-evoflow.ps1
```

AIGC 反推请走 **1008-aigc-prompt-reverse**（:8768）。

### 姿势 B：自己看面板

扩展应用 → 内容拆解 → 粘贴链接点「开始拆解」。

---

## 5. 拆解自检（提交前必读）

- 分享文案里**必须含短链** `https://v.douyin.com/xxxx/`，只有「复制打开抖音…」没链会报
  `No Douyin URL found`——**不是 bug，是缺链，别浪费 job**，先找用户要链。
- 3 分钟视频约 1–3 分钟；首次运行要多等几分钟下载转写模型。

---

## 6. 常见问题

| 症状 | 处理 |
|---|---|
| 扩展装了侧栏没出现 | 重启面板或 设置→扩展→刷新；确认 registry 里有 `douyin-video-pipeline` |
| 服务起不来/转写报 librosa 错 | 用的是 venv Python——改用 `py -3.12 scripts/web_server.py` |
| PowerShell 里 curl 报「参数二义性」 | 用 `curl.exe`；中文 JSON 先落盘再 `--data-binary @文件` |
| job not found | job 是内存态，服务重启即丢；同一生命周期内取状态 |
| 端口 8765 被占 | `Get-NetTCPConnection -LocalPort 8765 -State Listen \| %{ Stop-Process -Id $_.OwningProcess -Force }` |

---

## 7. 卸载/清理

```powershell
# 扩展：删 registry.json 里 id=douyin-video-pipeline 的那条
# 技能：删 ~/.evoflow/profiles/default/skills/custom/{douyin-video-pipeline,evoflow-onboarding}
# 员工：面板「智能体员工」页停用 video-analyst
```
