# 资源包（一键装齐）使用说明

本仓库现在同时是一个 **EvoFlow 资源包**：根目录的 `evoflow.organization.json` 把「扩展 + 技能 ×2 + 抖音拆解师 + 拆解报告知识库」声明成一个场景包，导入一次全装齐。

## 包内容

| 组件 | 来源 | 安装行为 |
|------|------|---------|
| UI 扩展 `aigc-prompt-reverse` | 仓库根 `evoflow.extension.json` | folder-link 登记本仓库路径（`service.link: true`），不复制 |
| 技能 `aigc-prompt-reverse` / `evoflow-onboarding` | `skills/` | 复制到生效技能根的 `custom/` |
| 员工 `aigc-prompt-reverser`（抖音拆解师） | `agents/` + `employees/` | 已存在时按冲突策略处理（`replace` 会重建并补绑知识库） |
| 知识库「抖音拆解报告库」 | `data/reports/` | 按名称幂等 get-or-create + 导入文档（content_hash 去重）；员工经 `${KB_REF:reports}` 占位符自动绑定 |

## 安装方式

- **面板**：设置 → 资源中心 → 市场 → **导入本地** → 选本仓库根目录（含 `evoflow.organization.json`）。已装过同名员工时建议冲突策略选 `replace`。
- **CLI**：`evoflow org install --type path --path <本仓库根>`（加 `--conflict-policy replace`）。

## 核验（替代旧脚本 B1–B4）

1. 面板「扩展」出现「视频拆解」（folder-link 指向本仓库）
2. 技能列表有 `aigc-prompt-reverse` / `evoflow-onboarding`
3. 员工「抖音拆解师」存在，知识库绑定显示「抖音拆解报告库」
4. 对员工说「搜一下知识库里的钩子案例」能命中报告

## 注意

- **zip 分发**：打包 zip 时排除 `outputs/`、`uploads/`、`node_modules/` 等运行时目录。zip 导入时 folder-link 扩展指向的是解压临时目录（zip 场景天生不便携）；要分发给别人，把 `extensions` 条目改成把 `web/`、`scripts/`、`requirements.txt`、`evoflow.extension.json` 收进 `extensions/aigc-prompt-reverse/` 用 `from` 复制形态。
- 旧安装脚本 `scripts/install-into-evoflow.ps1` 仍可用（B4 知识库同步走 gateway API 与资源包幂等兼容），但装完包后通常不再需要它。
