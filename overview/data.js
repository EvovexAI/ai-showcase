// 由 projects.overview.json 生成（2026-10-15）——渲染快照，UI 仅读这里
window.PROJECTS_OVERVIEW = {
  generatedAt: "2026-10-15",
  source: "ai-demos 机审扫描（README / evoflow.extension.json / package.json / 目录结构）",
  stats: {
    projects: 6,
    byLanguage: { "JavaScript": 3, "Python": 2, "TypeScript": 1 },
    byResourceType: { "本地Web服务": 4, "纯前端应用": 1, "接入套件": 1 },
    evoTotal: { knowledgeBases: 2, employees: 2, skills: 4, extensions: 2 }
  },
  projects: [
    {
      id: "1001",
      dir: "1001-ai-poster-editor",
      name: "AI 海报编辑器",
      description: "纯前端海报编辑器 + AI 生成：描述生成背景（通义万象）、绿幕素材自动抠绿、AI 布局优化（多轮 diff 预览/撤回）、一键成稿；拖拽/图层面板/艺术字/导出 PNG·JPG，附零依赖 REST API。",
      tags: ["自媒体电商", "内容创作", "AI 生图"],
      language: "JavaScript",
      techStack: ["Vanilla JS 零框架", "Node 内置模块零依赖 API"],
      resourceType: "纯前端应用",
      launch: "node server.cjs → http://127.0.0.1:8899",
      ports: ["8899"],
      status: "可用",
      evo: { knowledgeBases: [], employees: [], skills: [], extensions: [] },
      contains: "js/ 14 个模块、css/、index.html、server.cjs、proxy.cjs；文档 README/SETUP/API/AGENTS",
      source: "根 README + 目录结构"
    },
    {
      id: "1002",
      dir: "1002-ai-video-decompose",
      name: "AI 视频拆解（Web 全栈版）",
      description: "抖音视频一键拆解的 Next.js 重构版：链接 → 下载 → 转写 → 关键帧 → 章节 → 分镜，支持脚本(MD)/章节表(JSON)/分镜表(JSON) 导出与详情页可视化。",
      tags: ["自媒体电商", "内容分析", "视频处理"],
      language: "TypeScript",
      techStack: ["Next.js 14", "React 18", "Fastify", "Prisma + SQLite", "pnpm monorepo (turbo)"],
      resourceType: "本地Web服务",
      launch: "pnpm dev → http://localhost:3002/video-decompose",
      ports: ["3001 API", "3002 Web"],
      status: "原型（含 dev.db 样例数据）",
      evo: { knowledgeBases: [], employees: [], skills: [], extensions: [] },
      contains: "apps/api 10 个 TS 模块、apps/web 4 个页面、prisma/dev.db；文档 WORKFLOW/SUMMARY/DEMO/INTEGRATION_GUIDE",
      source: "package.json + SUMMARY.md + 目录实况"
    },
    {
      id: "1003",
      dir: "1003-ai-video-promo",
      name: "宣传视频制作系统",
      description: "从 1002 拆出的制作+配音子系统：火山 TTS（seed-tts-2.0，291 音色）、分镜策划稿（AI 润色）、一键配音、工作台 API（任务/技能/草稿/自动化/飞书推送），与 1004 后端对齐、砍掉拆解侧。",
      tags: ["自媒体电商", "内容创作", "TTS 配音"],
      language: "Python",
      techStack: ["httpx", "火山 OpenSpeech v3 TTS", "EvoFlow 兼容客户端", "Web UI 复用 1004"],
      resourceType: "本地Web服务",
      launch: "python scripts/promo_server.py → http://localhost:8766",
      ports: ["8766"],
      status: "可用（TTS 需配 Key）",
      evo: { knowledgeBases: [], employees: [], skills: [], extensions: [] },
      contains: "scripts/ 9 个模块、web/ 前端、config/ TTS 配置；文档 README/INTEGRATION_GUIDE",
      source: "README + package.json"
    },
    {
      id: "1004",
      dir: "1004-douyin-video-pipeline",
      name: "抖音视频拆解工作台",
      description: "把一条视频变成「能直接抄作业」的拆解报告：抖音分享链接直达（B站/YouTube 走 yt-dlp）→ 下载 → Whisper 转写 → 关键帧 → 章节 → 规则引擎洞察（钩子/人群/黄金句/节奏/结构）→ 可视化报告 + Markdown 存档。全程本地，洞察免费无付费模型。",
      tags: ["自媒体电商", "内容分析", "爆款拆解"],
      language: "Python",
      techStack: ["yt-dlp", "Whisper", "ffmpeg", "内置规则引擎"],
      resourceType: "本地Web服务",
      launch: "python scripts/web_server.py → http://127.0.0.1:8765",
      ports: ["8765"],
      status: "可用（已转私有仓库，zip 分发）",
      evo: {
        knowledgeBases: ["抖音拆解报告库 (kb_72da6f1d…)"],
        employees: ["douyin-analyst"],
        skills: ["douyin-video-pipeline", "evoflow-onboarding"],
        extensions: ["视频拆解工作台 :8765"]
      },
      contains: "scripts/ 11 个模块、web/ 前端、skills/ 2 个技能；文档 README/EVOFLOW-SETUP",
      source: "README + evoflow.extension.json + onboarding-kit 打样表"
    },
    {
      id: "1005",
      dir: "1005",
      name: "抖音博主分析器",
      description: "采集抖音博主公开数据做分析看板：数据看板/内容分析/标题钩子分类/多账号对比；数据双轨（accounts.json 机器真源 + data/reports/*.md 知识库喂养层），支持 API 直灌与浏览器采集技能。",
      tags: ["自媒体电商", "数据分析", "对标账号"],
      language: "JavaScript",
      techStack: ["Node 18+ 零依赖服务", "playwright-core（采集）"],
      resourceType: "本地Web服务",
      launch: "node server.js → http://127.0.0.1:8787",
      ports: ["8787"],
      status: "可用（EvoFlow 接入打样项目）",
      evo: {
        knowledgeBases: ["抖音博主分析报告库 (kb_e2a8f73a…)"],
        employees: ["douyin-blogger-analyst"],
        skills: ["douyin-blogger-analysis"],
        extensions: ["抖音博主分析 :8787"]
      },
      contains: "server.js、scripts/collect-douyin.js、skills/ 1 个技能；文档 README",
      source: "README + package.json + evoflow.extension.json"
    },
    {
      id: "kit",
      dir: "evoflow-onboarding-kit",
      name: "EvoFlow 项目接入套件",
      description: "把 ai-demos 任意工具型项目接入 EvoFlow 全链路的通用操作体系：UI 扩展面板 → 知识库 → 技能库 → 专属员工，四个脚本一条龙（注册扩展/同步知识库/雇佣员工），已在 1004、1005 打样。",
      tags: ["基础设施", "EvoFlow 生态", "自动化接入"],
      language: "JavaScript",
      techStack: ["Node 零依赖脚本", "manifest 模板", "平台 API 打通"],
      resourceType: "接入套件",
      launch: "node scripts/register-extension.js / sync-kb.js / hire-employee.js",
      ports: [],
      status: "可用",
      evo: {
        knowledgeBases: [],
        employees: [],
        skills: ["evoflow-onboarding (SKILL.md 已注册平台技能)"],
        extensions: []
      },
      contains: "SKILL.md、scripts/ 3 个脚本、configs/employee.example.json、templates/extension 模板",
      source: "README + 目录结构"
    }
  ],
  notes: [
    "_1004-extract 为 1004 的临时提取副本，不计入正式项目",
    "1002 现状为 pnpm monorepo（Next.js 版），旧文档中的 Python 脚本结构已过时",
    "端口分配：8899 / 8765 / 8766 / 8787 / 3001-3002，互不冲突"
  ]
};
