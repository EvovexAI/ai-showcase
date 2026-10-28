---
name: evoflow-capability-demo
description: >-
  1007 EvoFlow 业务场景台：自媒体/电商四条故事（S1 派工、S2 员工+知识库、S3 电商编排、S4 调研+编排）。
  一页一场景 UI :8877；seed_demo + smoke_check 真调通验收。禁止把 dry-run 冒充已调通。
---

# 1007 · 自媒体/电商业务场景台

项目根：`feishu_downloads/ai-showcase/productivity/evoflow-capability-demo`（`$PROJ`）。

## 业务场景（不是能力说明书）

| ID | 故事 | 能力 |
|----|------|------|
| S1 | 派拆解师拆抖音给钩子 | 员工 dispatch |
| S2 | 先查知识库爆款钩子再写开场 | 员工 + KB |
| S3 | 商品短视频脚本编排 | apps run |
| S4 | 调研简报 → 编排成片大纲 | 员工 + 编排 |

定义：`$PROJ/scenarios/s1-*.json` … `s4-*.json`。

## Agent 标准作业

```
1. 读 README + 本 SKILL
2. 确保 config/evoflow.json 有 api_key（否则只能预览）
3. py -3.12 $PROJ/scripts/seed_demo.py --live
4. py -3.12 $PROJ/scripts/smoke_check.py --live
5. 仅当 accepted_as_live=true 才向用户报告「已调通」
6. 可选：web_server.py → http://127.0.0.1:8877  #/s1…#/s4  #/setup
```

离线演示步骤形状：`smoke_check.py --allow-dry-run` 或 UI 不勾实网——**必须明确告知未调通**。

## 关键接口

### 员工

- `GET /api/proactive/roles`
- `POST /api/proactive/employees`（种子）
- `PUT /api/proactive/roles/{code}`（绑定 `knowledge_vault_ids`）
- `POST /api/proactive/roles/{code}/dispatch`
- `GET …/busy` · `GET …/work-board`

### 知识库

- `POST /api/knowledge/owned/bases`
- `POST …/bases/{id}/documents/manual`
- `POST …/bases/{id}/search`

### 编排

- `POST /api/apps` → `POST …/{id}/publish`
- `POST /api/apps/{id}/run` → `GET /api/apps/runs/{run_id}`

探活：`GET /health`。

## 约束

- **禁止** dry-run / 模拟成功冒充「已调通」。
- **禁止** 把四个场景表单摊在同一屏；UI 必须一页一场景。
- 演示资源前缀 `demo-1007-*`；配置了 default_* 则跳过创建。
- 派工 409 busy：先轮询 busy，勿连打。
- 不要嵌入 EvoFlow 整站面板。

## 配置

`base_url`、`api_key`、`dry_run`、`require_live_for_accept`、  
`default_employee_code` / `default_kb_id` / `default_app_id`。  
种子结果：`data/seed-state.json`；运行日志：`data/runs/*.json`。
