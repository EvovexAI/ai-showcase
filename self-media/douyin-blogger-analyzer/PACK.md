# 抖音博主分析 · 资源包

## 导入什么

本仓库根目录即资源包（含 `evoflow.organization.json`）。装进去的是：

| 产物 | 显示名 |
|------|--------|
| 扩展 | 抖音博主分析器（:8787） |
| 员工 / 智能体 | 抖音博主分析师 |
| 技能 | douyin-blogger-analysis |
| 知识库 | 抖音博主报告库 |

## 往哪导（手动）

1. EvoFlow → **设置 → 资源中心 → 市场**
2. **导入本地** → 选文件夹（本仓库根）或打好的 zip
3. 预检 → 安装
4. **已装** 里应看到「抖音博主分析场景包」

路径：`#/settings?tab=resources&panel=market`

## 让 AI 导

对值班员工 / 陪练师说：

> 请把 `D:\dev\github\feishu_downloads/ai-showcase/self-media/douyin-blogger-analyzer` 按资源包安装（根目录有 evoflow.organization.json）。

（若环境已接 `evoflow org install` / 组织安装 API，由 Agent 调安装；否则引导你打开上述设置页手动选目录。）

## 格式

根文件必须是：

```text
evoflow.organization.json   # schema:1, kind:team, id/name/version, primitives, team
evoflow.extension.json      # Agent 应用面板
employees/  agents/  skills/  data/reports/
```

不是资产中心的 `.evoflow-pack`（那是画像/记忆备份）。
