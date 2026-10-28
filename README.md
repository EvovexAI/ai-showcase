# AI Showcase — EvovexAI AI 实战演示系列

EvovexAI 的 AI 应用实战演示合集：小而完整、开箱即跑、无内置密钥。

项目按**业务分类**组织：`<分类>/<意义名>`。总览页：[`overview/index.html`](./overview/index.html)（数据真源 [`projects.overview.json`](./projects.overview.json)）。

## 分类与项目

### 电商（`ecommerce/`）

| 项目 | 端口 | 简介 |
|---|---|---|
| `ecommerce-content-studio` 商策造物 · 电商智能创作中枢 | 5173/8790 | 收录黎小 1022 项目：全网洞察 + 主图/SKU/详情页/视频生成（生图依赖 BOLI CLI） |

### 自媒体（`self-media/`）

| 项目 | 端口 | 简介 |
|---|---|---|
| `ai-video-decompose` AI 视频拆解（Web） | 3001/3002 | Next.js：链接 → 转写 → 关键帧 → 分镜 |
| `ai-video-promo` 宣传视频制作 | 8766 | TTS 配音 + 分镜策划 + 工作台 API |
| `douyin-video-pipeline` 抖音视频拆解工作台 | 8765 | 内容拆解 / 起号报告（EvoFlow 打样） |
| `douyin-blogger-analyzer` 抖音博主分析器 | 8787 | 账号看板 / 钩子分析 / 多账号对比 |

### 个人效率（`productivity/`）

| 项目 | 端口 | 简介 |
|---|---|---|
| `evoflow-capability-demo` EvoFlow 业务场景台 | 8877 | S1–S4 员工/知识库/编排演示 |
| `smart-coach` 智能陪练（学员） | 8769 | 进度面板 + EvoFlow 陪练师梳/练/答 |

### AIGC（`aigc/`）

| 项目 | 端口 | 简介 |
|---|---|---|
| `ai-poster-editor` AI 海报编辑器 | 8899 | 纯前端海报编辑 + AI 生图/抠绿/布局优化 |
| `ai-creative-ad-video` AI 创意广告视频 | — | 小云雀 CLI：一句话 → 样片 → 成片 |
| `aigc-prompt-reverse` AIGC 反推提示词 | 8768 | 反推 T2V/I2V 可粘贴 Prompt |

### 套件（仓库根）

| 项目 | 简介 |
|---|---|
| `evoflow-onboarding-kit` EvoFlow 接入套件 | 扩展 / 知识库 / 员工一键接入 |

## 仓库结构

```
ai-showcase/
├── ecommerce/            # 电商类
├── self-media/           # 自媒体类
├── productivity/         # 个人效率类
├── aigc/                 # AIGC 类
├── evoflow-onboarding-kit/  # 跨分类接入套件
├── overview/             # 项目总览页 + 维护规范 + 介绍页模板
├── */*/intro.html        # 各项目介绍页（由 overview/gen_intros.py 生成）
├── docs/                 # 跨项目说明（员工资源、资源包条款等）
├── projects.overview.json
├── assets/ memory/ outputs/ uploads/   # 运行期/共享附属
└── README.md
```

重复或临时副本已移到归档目录 `D:\dev\github\evo\edu\_ai-demos-archive\`（含旧 `ai-video-decompose`、`_1004-extract`、旧编号 zip 等）。

## 原则

- 每个项目尽量零依赖或极少依赖，克隆即跑
- 不硬编码任何密钥、内网 IP、公司域名
- 每个项目附 SETUP/使用文档
- 目录命名：`<分类>/<意义名>`（意义名小写连字符），分类四选一：ecommerce / self-media / productivity / aigc
- 新增/改项目前先读 [`overview/MAINTENANCE.md`](./overview/MAINTENANCE.md)

## License

MIT
