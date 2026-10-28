#!/usr/bin/env python3
"""Idempotent seed: demo employee + knowledge base + ecommerce script app.

Writes data/seed-state.json with employee_code / kb_id / app_id.
Use --live to hit the real gateway (requires api_key).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evoflow_api import (
    DEMO_PREFIX,
    EvoFlowClient,
    load_config,
    load_seed_state,
    save_seed_state,
)

HOOK_DOCS = [
    {
        "title": "钩子·先抛结果",
        "content": (
            "# 爆款钩子：先抛结果\n\n"
            "开场句示例：普通人用 AI 做副业，第一周就出了第一条播放过万的口播。\n\n"
            "适用：自媒体起号、副业选题。要点：先给结果数字，再讲怎么做到。"
        ),
    },
    {
        "title": "钩子·痛点反问",
        "content": (
            "# 爆款钩子：痛点反问\n\n"
            "开场句示例：还在熬夜剪一条抖音？其实 3 个模板就够你发一周。\n\n"
            "适用：工具/效率类。要点：点出痛点再给解药。"
        ),
    },
    {
        "title": "钩子·对比反差",
        "content": (
            "# 爆款钩子：对比反差\n\n"
            "开场句示例：同款榨汁杯，有人拍成说明书，有人拍成「上班族 30 秒早餐」。差别就在开场。\n\n"
            "适用：电商短视频。要点：同类商品不同叙事。"
        ),
    },
]

APP_PAYLOAD = {
    "name": f"{DEMO_PREFIX}·商品短视频脚本",
    "description": "1007 演示：卖点提炼 → 口播 → 分镜",
    "category": "ecommerce",
    "tags": ["demo-1007", "ecommerce", "short-video"],
    "execution_mode": "workflow",
    "source": "demo-1007",
    "parameters": [
        {"name": "product", "label": "商品名", "required": True},
        {"name": "selling_points", "label": "卖点", "required": False},
        {"name": "audience", "label": "人群", "required": False},
        {"name": "topic", "label": "主题", "required": False},
        {"name": "brief", "label": "调研简报", "required": False},
    ],
    "goal_template": (
        "为商品「{{product}}」写短视频脚本。"
        "卖点：{{selling_points}}；人群：{{audience}}；"
        "主题：{{topic}}；调研简报：{{brief}}"
    ),
    "steps": [
        {
            "name": "卖点提炼",
            "goal": "根据商品与卖点，提炼不超过 3 条核心卖点，各一句。",
            "assigned_agent": "demo-1007-analyst",
        },
        {
            "name": "口播稿",
            "goal": "写一段约 30 秒的口播稿，含钩子开场与行动号召。",
            "assigned_agent": "demo-1007-analyst",
        },
        {
            "name": "分镜要点",
            "goal": "拆成 4–6 个镜头，每镜写画面+旁白要点。",
            "assigned_agent": "demo-1007-analyst",
        },
    ],
}


def _find_existing_employee(client: EvoFlowClient, preferred: str) -> str:
    if preferred:
        got = client.get_employee(preferred)
        if got.get("ok") is not False and not (got.get("error") and not got.get("dry_run")):
            payload = client._payload(got)
            if payload.get("agent_code") or payload.get("role_name"):
                return preferred
    listed = client.list_employees(status=None)
    roles = client._payload(listed).get("roles") or []
    for r in roles:
        code = str(r.get("agent_code") or "")
        if code.startswith(DEMO_PREFIX):
            return code
    return ""


def _find_existing_kb(client: EvoFlowClient, preferred: str) -> str:
    if preferred:
        return preferred
    listed = client.list_kb()
    items = client._payload(listed).get("items") or []
    for it in items:
        name = str(it.get("name") or "")
        if DEMO_PREFIX in name or "爆款钩子" in name:
            return str(it.get("id") or "")
    return ""


def _find_existing_app(client: EvoFlowClient, preferred: str) -> str:
    if preferred:
        got = client.get_app(preferred)
        if got.get("ok") is not False and not (got.get("error") and not got.get("dry_run")):
            payload = client._payload(got)
            if payload.get("id"):
                return preferred
    listed = client.list_apps()
    items = client._payload(listed).get("items") or client._payload(listed).get("apps") or []
    for it in items:
        name = str(it.get("name") or "")
        tags = it.get("tags") or []
        if DEMO_PREFIX in name or "demo-1007" in tags:
            return str(it.get("id") or "")
    return ""


def seed(client: EvoFlowClient) -> dict:
    cfg = client.cfg
    prev = load_seed_state()
    log: list[dict] = []

    # Prefer explicit config overrides (skip create)
    preferred_emp = cfg.get("default_employee_code") or prev.get("employee_code") or ""
    preferred_kb = cfg.get("default_kb_id") or prev.get("kb_id") or ""
    preferred_app = cfg.get("default_app_id") or prev.get("app_id") or ""

    # ── Knowledge base ──
    kb_id = _find_existing_kb(client, preferred_kb)
    kb_created = False
    if not kb_id:
        r = client.create_kb(f"{DEMO_PREFIX}·爆款钩子库", "自媒体钩子样例（1007 演示）")
        log.append({"step": "kb.create", "result": r})
        kb_id = str(client._payload(r).get("id") or "")
        kb_created = bool(kb_id)
        if not kb_id and r.get("ok") is False:
            return {"ok": False, "error": "创建知识库失败", "log": log, "detail": r}
    else:
        log.append({"step": "kb.reuse", "kb_id": kb_id})

    docs_ingested = 0
    if kb_id and (kb_created or not prev.get("docs_ingested")):
        for doc in HOOK_DOCS:
            ir = client.ingest_manual(kb_id, doc["title"], doc["content"])
            log.append({"step": "kb.ingest", "title": doc["title"], "result": ir})
            if ir.get("ok") is not False:
                docs_ingested += 1

    # ── Employee ──
    emp_code = _find_existing_employee(client, preferred_emp)
    if not emp_code:
        code = f"{DEMO_PREFIX}-analyst"
        r = client.create_employee(
            {
                "agent_code": code,
                "role_name": "拆解师",
                "agent_name": "演示拆解师",
                "department": "自媒体",
                "responsibilities": [
                    "拆解对标短视频结构与钩子",
                    "检索知识库中的爆款钩子案例",
                    "输出可直接套用的开场句",
                ],
                "knowledge_vault_ids": [kb_id] if kb_id else [],
                "autonomy_level": "approval_for_all",
                "status": "active",
                "description": "1007 演示员工：自媒体拆解师",
                "soul": "你是自媒体拆解师，回答要短、可执行，优先引用知识库案例。",
            }
        )
        log.append({"step": "employee.create", "result": r})
        payload = client._payload(r)
        emp_code = str(payload.get("agent_code") or code)
        if r.get("ok") is False and not r.get("dry_run"):
            # 409 conflict → try reuse
            if "409" in str(r.get("error") or "") or "exist" in str(r.get("detail") or "").lower():
                emp_code = code
            else:
                return {"ok": False, "error": "创建员工失败", "log": log, "detail": r}
    else:
        log.append({"step": "employee.reuse", "agent_code": emp_code})

    if emp_code and kb_id:
        ur = client.update_employee(emp_code, {"knowledge_vault_ids": [kb_id]})
        log.append({"step": "employee.bind_kb", "result": ur})

    # ── App ──
    app_id = _find_existing_app(client, preferred_app)
    if not app_id:
        r = client.create_app(APP_PAYLOAD)
        log.append({"step": "app.create", "result": r})
        app_id = str(client._payload(r).get("id") or "")
        if not app_id and r.get("ok") is False:
            return {"ok": False, "error": "创建编排应用失败", "log": log, "detail": r}
        if app_id:
            # Publish requires assigned_agent on each step
            agent_for_steps = emp_code or f"{DEMO_PREFIX}-analyst"
            steps = []
            for i, step in enumerate(APP_PAYLOAD.get("steps") or [], start=1):
                s = dict(step)
                s.setdefault("ref", str(i))
                s["assigned_agent"] = agent_for_steps
                steps.append(s)
            ur = client.update_app(app_id, {"steps": steps})
            log.append({"step": "app.assign_agents", "result": ur})
            pr = client.publish_app(app_id)
            log.append({"step": "app.publish", "result": pr})
            if pr.get("ok") is False and not pr.get("dry_run"):
                return {"ok": False, "error": "发布编排应用失败", "log": log, "detail": pr}
    else:
        log.append({"step": "app.reuse", "app_id": app_id})
        # Ensure published
        got = client.get_app(app_id)
        status = str(client._payload(got).get("status") or "").lower()
        if status and status != "published":
            pr = client.publish_app(app_id)
            log.append({"step": "app.publish", "result": pr})

    state = {
        "employee_code": emp_code,
        "kb_id": kb_id,
        "app_id": app_id,
        "docs_ingested": docs_ingested or prev.get("docs_ingested") or 0,
        "dry_run": client.dry_run,
        "base_url": cfg.get("base_url"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "prefix": DEMO_PREFIX,
    }
    path = save_seed_state(state)
    ok = bool(emp_code and kb_id and app_id)
    return {"ok": ok, "seed": state, "saved": str(path), "log": log}


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed 1007 demo resources")
    ap.add_argument("--live", action="store_true", help="Force live gateway calls")
    args = ap.parse_args()
    cfg = load_config()
    if args.live:
        cfg["dry_run"] = False
    client = EvoFlowClient(cfg)
    result = seed(client)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("ok") and client.dry_run:
        print("\nNOTE: dry-run seed — NOT a live connectivity proof. Use --live after configuring api_key.", file=sys.stderr)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
