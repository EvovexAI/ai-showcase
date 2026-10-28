# EvoFlow 项目接入套件(evoflow-onboarding-kit)

把 ai-showcase 下任何工具型项目接入 EvoFlow 全链路的**通用操作体系**:UI 扩展面板 → 知识库 → 技能库 → 专属员工。一次打样(1005 抖音博主分析器),以后新项目按套件执行。

## 目录

```
evoflow-onboarding-kit/
├── SKILL.md                     ← 打法主体(已注册为平台技能,可直接引用)
├── scripts/
│   ├── register-extension.js    ← 注册/更新 UI 扩展(幂等+自动备份)
│   ├── sync-kb.js               ← 报告目录 → owned 知识库(建库+导入+增量)
│   └── hire-employee.js         ← 装技能+生成JSON+agents/hire 一条龙
├── configs/
│   └── employee.example.json    ← 员工配置模板(agent_code/soul/SOP/KPI)
└── templates/
    └── evoflow.extension.json   ← 扩展 manifest 模板(managed 模式)
```

## 快速开始(新项目接入)

```bash
# ① 扩展:复制模板到项目根,改 id/端口/启动命令,然后
node scripts/register-extension.js --project D:/path/to/项目

# ② 知识库:报告目录接入
node scripts/sync-kb.js --name "我的项目报告库" --folder D:/path/to/项目/data/reports --desc "…"

# ③+④ 技能+员工:填好 configs/xxx.json 后
node scripts/hire-employee.js --config configs/xxx.json --install-skill D:/path/to/项目/skills/my-skill
```

完整纪律、字段坑、验收清单见 `SKILL.md`。

## 已打样的项目

| 项目 | 扩展 | 知识库 | 员工 |
|---|---|---|---|
| 1005 抖音博主分析器 | douyin-blogger-analyzer (:8787) | 抖音博主分析报告库 (kb_e2a8f73a…) | douyin-blogger-analyst |
| 1004 抖音视频拆解 | douyin-video-pipeline (:8765) | 抖音拆解报告库 (kb_72da6f1d…) | douyin-analyst |
