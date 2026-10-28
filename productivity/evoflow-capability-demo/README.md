# 1007 · 自媒体 / 电商业务场景台（EvoFlow）

一场景一页的**业务演示台**：用真实网关种子出员工、知识库、编排，再跑通四条故事。  
**dry-run 只是离线预览，禁止当作「已调通」汇报。**

| 编号 | 业务故事 | 能力 |
|------|----------|------|
| **S1** | 自媒体：派「拆解师」拆一条抖音，给钩子建议 | 最简员工 |
| **S2** | 自媒体：拆解师先查知识库爆款钩子，再写 3 条开场 | 员工 + 知识库 |
| **S3** | 电商：一键跑「商品短视频脚本」编排（卖点→口播→分镜） | 纯编排 |
| **S4** | 调研岗出竞品简报 → 塞进编排成片大纲 | 员工 + 编排 |

场景定义：`scenarios/s1-*.json` … `s4-*.json`（含 `persona` / `story` / `inputs` / `acceptance`）。

---

## 快速开始

```powershell
cd d:\dev\github\feishu_downloads/ai-showcase/productivity/evoflow-capability-demo
copy config\evoflow.example.json config\evoflow.json
# 编辑 evoflow.json：填写 api_key；实网时 dry_run=false

py -3.12 scripts\web_server.py
# http://127.0.0.1:8877  →  #/ 目录  #/s1…#/s4 专页  #/setup 连接与种子
```

无 `api_key` 时 UI 显示「仅预览，未调通」。

---

## 真调通验收（必须）

```powershell
# 1) 种子：员工 / KB / App → data/seed-state.json
py -3.12 scripts\seed_demo.py --live

# 2) Smoke：health + seed + S1–S4 全绿才算已调通
py -3.12 scripts\smoke_check.py --live
```

验收清单：

1. 网关探活成功（`GET /health`）
2. `seed-state.json` 含 `employee_code` / `kb_id` / `app_id`
3. S1 dispatch ok；busy 可读
4. S2 员工绑定 KB；search 命中 ≥1；dispatch ok
5. S3 拿到 `run_id`，状态可读
6. S4 日志同时有 dispatch 与 `run_id`
7. UI：从目录进 S2，页面上看不到 S3/S4 表单

`smoke_check` 的 `accepted_as_live=true` 才允许对外说「已调通」。  
离线预览：`py -3.12 scripts\smoke_check.py --allow-dry-run`（退出码 3，不算调通）。

单场景：

```powershell
py -3.12 scripts\run_scenario.py s1 --live
py -3.12 scripts\run_scenario.py s2 --live
py -3.12 scripts\run_scenario.py s3 --live
py -3.12 scripts\run_scenario.py s4 --live
```

运行日志：`data/runs/*.json`。

---

## 配置

`config/evoflow.json`：

| 字段 | 说明 |
|------|------|
| `base_url` | 默认 `http://127.0.0.1:8080` |
| `api_key` | Bearer Token；空则只能预览 |
| `dry_run` | 有 key 时建议 `false` |
| `require_live_for_accept` | `true`：验收必须实网 |
| `default_employee_code` / `default_kb_id` / `default_app_id` | 若已填则种子跳过创建、只绑定 |

环境变量：`EVOFLOW_GATEWAY_URL` / `EVOFLOW_API_KEY` / `EVOFLOW_DRY_RUN`。  
演示资源前缀：`demo-1007-*`，避免误伤生产员工。

---

## 项目结构

```
scripts/evoflow_api.py   # 网关客户端
scripts/seed_demo.py     # 幂等种子 → data/seed-state.json
scripts/run_scenario.py  # s1–s4 运行器
scripts/smoke_check.py   # 调通验收
scripts/web_server.py    # UI :8877
web/                     # 一页一场景（hash 路由）
scenarios/               # 业务故事 JSON
```

本项目是场景演示台，不嵌入 EvoFlow 整站面板。
