---
name: evoflow-project-onboarding
description: >-
  把本地项目一键接入 EvoFlow 全链路的通用打法:UI 扩展面板(可点开) + owned 知识库(报告可检索) +
  技能装库 + 专属员工(SOP 自动干活)。当用户说「把这个项目接入 EvoFlow/扩展面板」「配个专属员工」、
  「把报告放进知识库」「用上次的接入打法」「onboarding kit」时使用。样例:1005 抖音博主分析器。
---

# EvoFlow 项目接入套件(四件套)

把一个本地工具型项目接入 EvoFlow 的标准动作,按顺序做四件事。全部验证过的路径,坑都标了。

## 总览

```
① UI 扩展   → 面板「扩展」里可见可点开(managed 托管起服务)
② 知识库    → 项目产出的报告进 owned KB,可检索(resync 增量)
③ 技能装库  → skills/custom 可被 agents/employees 引用
④ 专属员工  → agents create + employees hire,soul 写 SOP,自动按流程干活
```

## 前置检查

- [ ] 项目能在本机跑起来(启动命令 + 端口 + healthcheck 端点)
- [ ] 有产物可进知识库(报告目录/文档目录),或明确本步跳过
- [ ] 项目内有技能文档 `skills/<name>/SKILL.md`(front-matter 的 description 写清触发词,否则路由不到)
- [ ] evoflow CLI 可用(`evoflow skills list --compact` 能出 JSON)

## ① UI 扩展(面板可见)

1. 从 `templates/evoflow.extension.json` 复制到项目根,改:id/name/nav.title/entry 端口/service.start/ports/bridge allowlist
2. 注册:`node scripts/register-extension.js --project <项目根>`(幂等,自动备份注册表)
3. 让用户在面板 **设置→扩展** 点刷新(或重启面板)

坑:
- dev 环境注册表在 `~/.evoflow-dev/ui-extensions/registry.json`(**不是** `~/.evoflow`)
- `service.start.windows` 必须是数组;npm 命令用 `.cmd`(如 `pnpm.cmd`)
- 目标服务响应头不能带 `X-Frame-Options`/严格 CSP,否则 iframe 打不开
- healthcheck 建议给一个真实探活端点(如 /api/health),比根路径稳

## ② 知识库(报告可检索)

```bash
node scripts/sync-kb.js --name "<知识库名>" --folder <项目>/data/reports --desc "…"
```
- 自动建库(同名复用)、导入、记住同步源;返回 `{created,updated,unchanged,skipped}`
- 后续增量:`resync_base('<kb_id>')`(幂等);把这条命令写进项目 SKILL.md 的固定步骤
- 用 EvoFlow venv 解释器进程内直调,不依赖网关(网关没起也能用)

API 签名坑(2026-10-14 实测):
- `create_base({"name","description"})` 是单 payload 参数,不是 `(name, desc)`
- `search` 是 async;`search_keyword` 同步返回 list;`list_documents(kb)` 同步
- 验证命中用 `search_keyword`(不依赖向量/embedding,最稳)

## ③ 技能装库

把项目 `skills/<name>/` 拷进 `%USERPROFILE%\.evoflow-dev\skills\custom\<name>\`,
只拷 SKILL.md 级文档即可被识别(默认 enabled)。核验:`evoflow skills list --compact | 过滤 name`。

## ④ 专属员工

1. 复制 `configs/employee.example.json` 填实(agent_code 唯一、soul 写 SOP+边界+汇报格式、触发词写进 description)
2. `node scripts/hire-employee.js --config configs/xxx.json --install-skill <项目>/skills/<name>`
   (自动:装技能 → 生成 agent/hire JSON 落 `~/.evoflow-dev/outputs/` → `evoflow agents create` + `employees hire`)
3. 核验:`evoflow employees list --compact`(看 status=active、heartbeat、skills)

关键字段纪律:
- `risk_threshold` 只收枚举 low/medium/high,自然语言会被拒
- `autonomy_level`:full_auto / approval_for_risky / approval_for_all
- **tools 必须显式配**:不配 = 全量 29 个工具(含 supervisor/terminal/process 等高危面;tool_groups 组名实际不过滤,真白名单是 agent.tools;tool_search 与系统工具可旁路)
- **知识库直接绑员工**:hire/update payload 传 `knowledge_vault_ids`(数组)+ `kb_injection`(mode: off/auto/agent/both,默认 auto top_k 24;检索 hybrid;on_failure ignore 不阻塞),配好后员工每轮对话自动注入检索结果(心跳巡逻自动跳过;注入配置存双路径:角色层 + agent extra_json 镜像;若 CLI 更新后 agent 层镜像未落,用 venv 直调 `evoflow.admin.employees._persist_agent_kb_injection(code, {...})` + `backfill_agent_kb_vault_ids()` 兜底)
- soul 必钉死:项目绝对路径、启动命令与端口纪律(先探活/单实例)、SOP 步骤、边界、汇报格式
- 心跳默认 `0 9-19/2 * * *`(9-19 点每 2 小时)

## 完整样例(可直接参考)

- 1005 抖音博主分析器(本次全链路):`D:/dev/github/feishu_downloads/ai-showcase/self-media/douyin-blogger-analyzer`
  - 扩展:`1005/evoflow.extension.json`;KB:「抖音博主分析报告库」kb_e2a8f73a8d9a4fafad6159b251ab1b41
  - 员工:douyin-blogger-analyst(抖音账号分析师,内容运营部)
  - 技能:douyin-blogger-analysis
- 1004 抖音视频拆解:扩展 id douyin-video-pipeline(:8765)、KB「抖音拆解报告库」、员工 douyin-analyst

## 一页验收清单

- [ ] 面板刷新后扩展可见,点开能加载(iframe 正常)
- [ ] `sync-kb.js` 跑通,`search_keyword` 能命中报告关键词
- [ ] `skills list` 看到新技能且 enabled
- [ ] `employees list` 看到员工 active、inherits_agent=true
- [ ] 手工触发一次员工任务,SOP 按 soul 执行(起服务→干活→报告→resync)
