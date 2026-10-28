# 1006 · AI 生创意广告视频（小云雀 CLI 工作流）

用**小云雀（Pippit）官方 CLI**（`pippit-tool-cli`）从一句话到一支创意广告成片：脚本定稿 → 480p 样片预览 → 确认后转 1080p 成片。沉淀了完整的 CLI 操作、创意广告提示词套路库、积分策略和命令封装脚本。

> 已验证环境：Windows 11 + Node.js 22 + `@pippit-dev/cli` v1.0.41（2026-10-15 实测跑通全链路：安装 → 登录 → 生视频 → 下载成片）。

## 快速开始

```powershell
# 1. 安装 CLI（已装可跳过）
npx @pippit-dev/cli@latest install

# 2. 登录（浏览器授权，账号必须是"开通会员的那个账号"）
pippit-tool-cli login
pippit-tool-cli status          # 确认 logged_in: true

# 3. 查积分
pippit-tool-cli get-credit-balance

# 4. 一键生成创意广告（参数化封装，见 scripts/generate-ad.ps1）
powershell -File scripts\generate-ad.ps1 -Prompt "一杯咖啡在城市上空穿梭，掠过地标，卡点节奏，最后定格新品" -Model Seedance_2.5 -Duration 10 -Ratio 9:16 -Resolution 720p

# 5. 查询并下载成片
powershell -File scripts\query-result.ps1 -ThreadId skill_xxx -RunId skill_xxx
```

## 推荐流程（省积分、出片稳）

```
选题/脚本定稿  →  480p 样片（便宜）  →  预览确认  →  一键转 1080p 成片
```

- 用 `Seedance_2.5_draft` 走两阶段：样片 480p、成片 1080p（样片 7 天内可转，两阶段分别计费）
- 卡点广告给 `--audio` 传 BGM 做节奏参考；精确控制开头结尾用首尾帧（`--generate-type 1`）
- 积分实测：Seedance 2.5 · 10 秒 · 720p ≈ **200 积分/支**

## 目录结构

```
feishu_downloads/ai-showcase/aigc/ai-creative-ad-video/
├── README.md                  # 本文件：项目入口
├── SKILL.md                   # 可复用技能文档（AI Agent 可直接套用）
├── scripts/                   # PowerShell 命令封装
│   ├── ensure-cli.ps1         # 安装/登录状态检查
│   ├── generate-ad.ps1        # 生视频（支持样片/成片/首尾帧/参考素材）
│   ├── query-result.ps1       # 查询 + 下载
│   └── draft-to-final.ps1     # Draft 样片 → 成片
├── prompts/
│   └── 创意广告套路库.md       # 无厘头/卡点/穿梭/拼接/神转折 提示词模板
├── docs/
│   ├── cli-cheatsheet.md      # CLI 命令速查
│   ├── 积分与参数.md           # 模型/参数/积分测算与省钱策略
│   └── official/              # 官方资料归档（文档目录见 official/README.md）
│       ├── README.md          # 官方资料索引：每个文档干嘛、什么时候看
│       ├── seedance-2.5-手册要点.md   # Seedance 2.5 官方手册核心提炼（能力/素材/prompt/时间戳/负向/省钱）
│       └── prompt-指南-即梦与通用公式.md # 提示词核心原则、最佳实践模板、运镜技巧、注意事项
├── examples/                  # 真实案例
│   └── <日期>-<主题>/            # 真实案例（prompt/命令/成本/结果）
└── output/                    # 生成产物输出目录
```

## 依赖

- Node.js 16+（CLI 安装器要求；实测 22 正常）
- 小云雀账号 + 会员/积分（消耗**登录账号自己的积分**）
- Windows PowerShell（脚本为 .ps1；命令本身跨平台）

## 相关

- 官方 CLI 仓库：<https://github.com/Pippit-dev/cli>（npm: `@pippit-dev/cli`）
- 官方技能（随安装器装到 `~/.agents/skills/`）：`xyq-skill` / `xyq-short-drama-skill` / `xyq-marketing-skill`
