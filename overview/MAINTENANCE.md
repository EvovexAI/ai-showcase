# 项目总览维护指南（给人和 AI 都能照做的填写规范）

> 数据真源：`projects.overview.json` → 展示载体：`overview/index.html`（HTML 顶部 `DATA` 数据区是它的内嵌副本，两处必须同步）。
> 新项目接入流程：**机审扫描 → 填 JSON → 同步 HTML → 自检**，全程不需要动页面样式和渲染逻辑。

---

## 一、机审扫描清单（填数据前先做）

对新项目目录依次查这些文件，**一切以文件实况为准，过时文档不采信**：

| 查什么 | 文件 | 得到什么 |
|---|---|---|
| 项目定位 | `README.md` 首屏 + 功能段 | name / description / tags 素材 |
| 语言判定 | `package.json`、`.py/.ts/.js` 文件计数、`requirements.txt` | language / techStack（README 与实际冲突时信 package.json） |
| 项目类型 | 目录结构（有无 server、web/、纯 html） | resourceType |
| EvoFlow 接入 | 项目根 `evoflow.extension.json` + `evoflow-onboarding-kit/README.md` 打样表 + `skills/*/SKILL.md` | evo 四项资产 |
| 启动方式 | README 快速开始 / package.json scripts | launch / ports / status |
| 内容清单 | `find 目录/*` 顶层两三层 | contains |

**语言判定规则**：以代码主体和 package.json 为准。教训：1002 旧文档写 Python/Vue，实际是 TypeScript/Next.js —— 已按实况纠正。

---

## 二、字段字典（projects[] 每一项）

```jsonc
{
  "id": "ai-creative-ad-video",      // 语义 slug：与目录名一致；套件用短名（如 kit）
  "dir": "aigc/ai-creative-ad-video",  // 工作区实际目录名（含分类前缀），必须一字不差
  "name": "项目名",                 // 取 README 标题或 extension.json 的 name，去掉 emoji
  "description": "1~3 句：做什么 + 核心能力 + 技术要点",   // 基于 README/package.json，不夸大
  "category": "aigc",                // ★ 分类：ecommerce / self-media / productivity / aigc（套件用 kit）
  "tags": ["自媒体电商", "内容创作"],  // 能力标签
  "language": "JavaScript",        // 枚举：JavaScript | TypeScript | Python
  "techStack": ["框架/关键依赖", "特色组件"],   // 3~5 个，按重要性排序
  "resourceType": "本地Web服务",     // 枚举：本地Web服务 | 纯前端应用 | 接入套件 | CLI工作流
  "launch": "node server.js → http://127.0.0.1:8787",   // 启动命令 → 访问地址
  "ports": ["8787"],               // 端口列表，多端口标注用途如 "3001 API"
  "status": "可用（TTS 需配 Key）",   // 可用 | 原型 | 可用（附关键限制），说明缺什么才能跑
  "evo": {                          // EvoFlow 接入资产，没有的留空数组 []
    "knowledgeBases": ["抖音拆解报告库 (kb_72da6f1d…)"],   // 库名 + kb id 前 10 位
    "employees": ["douyin-analyst"],                        // agent_code
    "skills": ["douyin-video-pipeline"],                    // skills/*/SKILL.md 的技能名
    "extensions": ["视频拆解工作台 :8765"]                   // manifest name + 端口
  },
  "contains": "scripts/ N 个模块、web/ 前端；文档 README/SETUP",  // 目录+文档一句话清单
  "source": "README + package.json + 目录实况"               // 本次数据依据了哪些文件，方便复查
}
```

---

## 三、顶层字段同步规则（最容易漏）

填完项目后必须重算：

- `stats.projects` = projects 数组长度
- `stats.byLanguage` / `stats.byResourceType` = 按 language / resourceType 重新计数
- `stats.evoTotal` = 各项目 evo 四个数组长度分别求和（注意 skills 是逐项累加，1004 有 2 个）
- `generatedAt` = 更新日期
- `notes[]`：临时副本/提取目录**只进 notes 不进 projects**；文档与实况冲突也记在这里。重复/临时项应移到归档 `D:\dev\github\evo\edu\_ai-demos-archive\`，不要留在仓库根目录

---

## 四、收尾两步

1. **同步 HTML**：把 JSON 的 `projects / stats / notes` 原样替换进 `overview/index.html` 顶部 `// ===== 数据区 =====` 里的 `DATA` 对象（JSON 键改 JS 对象字面量，去掉引号键的引号也行）。页面渲染逻辑不用动。
2. **自检**：
   - JSON 能被解析（无重复键、无逗号错误）
   - stats 数字与明细一致
   - 浏览器打开 index.html：卡片数 = projects 数，搜索/筛选/表格视图正常

---

## 五、新项目空白模板

```json
{
  "id": "",
  "dir": "",
  "category": "",
  "name": "",
  "description": "",
  "tags": ["", ""],
  "language": "",
  "techStack": [],
  "resourceType": "",
  "launch": "",
  "ports": [],
  "status": "",
  "evo": { "knowledgeBases": [], "employees": [], "skills": [], "extensions": [] },
  "contains": "",
  "source": ""
}
```

> 更省事的路径：直接对 AI 说「把 `<目录名>` 按总览规范机审并加进去」，AI 按本指南执行即可。
>
> 项目介绍页：每个项目可配一份介绍页，复制 [`project-template.html`](./project-template.html) 到项目目录后按「✏️」注释逐处替换（八个区块：定位/目标/使用对象/解决问题/配合使用/日常使用（EvoFlow 四种发起+沉淀闭环）/小白上手/0→1 提示词）。
