#!/usr/bin/env python3
"""Run S1–S4 business scenarios against EvoFlow (or dry-run preview)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evoflow_api import EvoFlowClient, ROOT, load_config, load_seed_state

SCENARIOS = ROOT / "scenarios"
RUNS = ROOT / "data" / "runs"


def _save_run(scenario_id: str, result: dict) -> Path:
    RUNS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = RUNS / f"{scenario_id}_{stamp}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _resolve_employee(client: EvoFlowClient, agent_code: str) -> str:
    seed = load_seed_state()
    code = (
        agent_code
        or client.cfg.get("default_employee_code")
        or seed.get("employee_code")
        or ""
    )
    if code:
        return code
    r = client.list_employees()
    roles = client._payload(r).get("roles") or []
    if roles:
        return str(roles[0].get("agent_code") or "")
    return "demo-1007-analyst" if client.dry_run else ""


def _resolve_app(client: EvoFlowClient, app_id: str) -> str:
    seed = load_seed_state()
    aid = app_id or client.cfg.get("default_app_id") or seed.get("app_id") or ""
    if aid:
        return aid
    r = client.list_apps()
    items = client._payload(r).get("items") or client._payload(r).get("apps") or []
    if items:
        return str(items[0].get("id") or "")
    return "demo-1007-app" if client.dry_run else ""


def _resolve_kb(client: EvoFlowClient, kb_id: str) -> str:
    seed = load_seed_state()
    kid = kb_id or client.cfg.get("default_kb_id") or seed.get("kb_id") or ""
    if kid:
        return kid
    r = client.list_kb()
    items = client._payload(r).get("items") or []
    if items:
        return str(items[0].get("id") or "")
    return "demo-1007-kb" if client.dry_run else ""


def run_s1(client: EvoFlowClient, *, agent_code: str = "", goal: str = "") -> dict:
    log: list[dict] = []
    goal = goal or (
        "请拆解这条抖音，用三条要点写出开场钩子与可抄结构："
        "https://v.douyin.com/WmUD_EkHqT0/"
    )
    r1 = client.list_employees()
    log.append({"step": "employees.list", "result": r1})
    code = _resolve_employee(client, agent_code)
    if not code:
        return {"ok": False, "error": "缺少 agent_code（先 seed 或填 config）", "log": log}

    r2 = client.dispatch(code, goal, description="1007·S1 自媒体派工")
    log.append({"step": "employees.dispatch", "agent_code": code, "result": r2})
    r3 = client.employee_busy(code)
    log.append({"step": "employees.busy", "result": r3})
    r4 = client.work_board(code)
    log.append({"step": "employees.work_board", "result": r4})

    dispatch_ok = r2.get("ok") is not False and (
        r2.get("dry_run") or r2.get("accepted") or r2.get("ok") or r2.get("round_id")
    )
    busy_ok = r3.get("ok") is not False and ("busy" in client._payload(r3) or r3.get("dry_run"))
    ok = bool(dispatch_ok and busy_ok)
    return {
        "ok": ok,
        "scenario": "s1",
        "agent_code": code,
        "goal": goal,
        "dispatch_id": client._payload(r2).get("round_id") or client._payload(r2).get("id"),
        "log": log,
        "acceptance": {
            "dispatch_ok": bool(dispatch_ok),
            "busy_readable": bool(busy_ok),
        },
    }


def run_s2(
    client: EvoFlowClient,
    *,
    agent_code: str = "",
    kb_id: str = "",
    goal: str = "",
    search_query: str = "短视频钩子 开场",
) -> dict:
    log: list[dict] = []
    goal = goal or (
        "必须先检索绑定的知识库中的爆款钩子案例，再基于命中内容写出 3 条可直接使用的"
        "短视频开场句（主题：普通人用 AI 做副业）。不要编造未检索到的案例。"
    )
    code = _resolve_employee(client, agent_code)
    kid = _resolve_kb(client, kb_id)
    if not code or not kid:
        return {"ok": False, "error": "缺少 employee_code 或 kb_id（先 seed）", "log": log}

    r0 = client.get_employee(code)
    log.append({"step": "employees.get", "result": r0})
    payload0 = client._payload(r0)
    vaults = payload0.get("knowledge_vault_ids")
    if not vaults:
        cfg = payload0.get("config") or {}
        vaults = cfg.get("knowledge_vault_ids") if isinstance(cfg, dict) else None
    vaults = list(vaults or [])

    r1 = client.search_kb(kid, search_query)
    log.append({"step": "knowledge.search", "kb_id": kid, "result": r1})
    hits = client._payload(r1).get("items") or client._payload(r1).get("results") or []
    hit_count = len(hits) if isinstance(hits, list) else 0

    # Avoid 409 busy from a previous scenario dispatch
    r_idle = client.ensure_idle(code, timeout_sec=90)
    log.append({"step": "employees.ensure_idle", "result": r_idle})

    r2 = client.dispatch(code, goal, description="1007·S2 员工+知识库")
    log.append({"step": "employees.dispatch", "result": r2})
    if r2.get("ok") is False and "409" in str(r2.get("error") or ""):
        r_idle2 = client.ensure_idle(code, timeout_sec=60)
        log.append({"step": "employees.ensure_idle_retry", "result": r_idle2})
        r2 = client.dispatch(code, goal, description="1007·S2 员工+知识库（retry）")
        log.append({"step": "employees.dispatch_retry", "result": r2})

    has_kb = bool(vaults) or client.dry_run
    search_ok = hit_count >= 1 or (client.dry_run and r1.get("ok") is not False)
    dispatch_ok = r2.get("ok") is not False
    ok = bool(has_kb and search_ok and dispatch_ok)
    return {
        "ok": ok,
        "scenario": "s2",
        "agent_code": code,
        "kb_id": kid,
        "knowledge_vault_ids": vaults,
        "search_hits": hit_count,
        "goal": goal,
        "log": log,
        "acceptance": {
            "employee_has_kb": has_kb,
            "search_hits_ge_1": search_ok,
            "dispatch_ok": dispatch_ok,
        },
    }


def run_s3(
    client: EvoFlowClient,
    *,
    app_id: str = "",
    product: str = "便携榨汁杯",
    selling_points: str = "无线便携、30 秒出汁、可洗刀头",
    audience: str = "上班族 / 健身党",
    topic: str = "",
    brief: str = "",
) -> dict:
    log: list[dict] = []
    aid = _resolve_app(client, app_id)
    if not aid:
        return {"ok": False, "error": "缺少 app_id（先 seed）", "log": log}

    r1 = client.get_app(aid)
    log.append({"step": "apps.get", "result": r1})
    status = str(client._payload(r1).get("status") or "").lower()

    params = {
        "product": product,
        "selling_points": selling_points,
        "audience": audience,
    }
    if topic:
        params["topic"] = topic
    if brief:
        params["brief"] = brief

    r2 = client.run_app(aid, params)
    log.append({"step": "apps.run", "result": r2})
    run_id = str(client._payload(r2).get("run_id") or client._payload(r2).get("id") or "")
    # Acceptance needs a readable status, not necessarily terminal (runs can be long)
    r3 = client.wait_run(run_id, timeout_sec=45) if run_id else {"ok": False, "error": "no run_id"}
    log.append({"step": "apps.run_status", "run_id": run_id, "result": r3})
    final_status = str(client._payload(r3).get("status") or "") if run_id else ""

    published = status == "published" or client.dry_run
    ok = bool(run_id and published and (r2.get("ok") is not False))
    return {
        "ok": ok,
        "scenario": "s3",
        "app_id": aid,
        "run_id": run_id,
        "parameters": params,
        "final_status": final_status or None,
        "log": log,
        "acceptance": {
            "published": published,
            "has_run_id": bool(run_id),
            "status_readable": bool(run_id and (final_status or r3.get("ok") is not False)),
        },
    }


def run_s4(
    client: EvoFlowClient,
    *,
    agent_code: str = "",
    app_id: str = "",
    topic: str = "便携榨汁杯 · 上班族早餐场景",
    audience: str = "上班族",
    goal: str = "",
) -> dict:
    log: list[dict] = []
    goal = goal or (
        "围绕「便携榨汁杯」整理 3 条竞品短视频钩子手法，并各给一句可套用开场，输出简洁简报。"
    )
    code = _resolve_employee(client, agent_code)
    aid = _resolve_app(client, app_id)
    if not code or not aid:
        return {"ok": False, "error": "缺少 employee_code 或 app_id（先 seed）", "log": log}

    r0 = client.ensure_idle(code, timeout_sec=90)
    log.append({"step": "employees.ensure_idle", "result": r0})

    r1 = client.dispatch(code, goal, description="1007·S4 调研简报")
    log.append({"step": "employees.dispatch", "agent_code": code, "result": r1})
    if r1.get("ok") is False and "409" in str(r1.get("error") or ""):
        r0b = client.ensure_idle(code, timeout_sec=60)
        log.append({"step": "employees.ensure_idle_retry", "result": r0b})
        r1 = client.dispatch(code, goal, description="1007·S4 调研简报（retry）")
        log.append({"step": "employees.dispatch_retry", "result": r1})
    dispatch_id = client._payload(r1).get("round_id") or client._payload(r1).get("id")

    # S4 only needs a successful dispatch id; do not block long on finishing the round
    r2 = client.wait_until_idle(code, timeout_sec=15, interval=2.0)
    log.append({"step": "employees.wait_idle", "result": r2})

    brief = f"[调研派工摘要] {goal[:120]}"
    params = {
        "product": topic.split("·")[0].strip() if "·" in topic else topic,
        "topic": topic,
        "audience": audience,
        "brief": brief,
        "selling_points": "见调研简报",
    }
    r3 = client.run_app(aid, params)
    log.append({"step": "apps.run", "result": r3})
    run_id = str(client._payload(r3).get("run_id") or client._payload(r3).get("id") or "")
    r4 = client.wait_run(run_id, timeout_sec=45) if run_id else {"ok": False, "error": "no run_id"}
    log.append({"step": "apps.run_status", "run_id": run_id, "result": r4})

    dispatch_ok = r1.get("ok") is not False and not (
        r1.get("error") and not r1.get("dry_run")
    )
    ok = bool(dispatch_ok and run_id)
    return {
        "ok": ok,
        "scenario": "s4",
        "agent_code": code,
        "app_id": aid,
        "dispatch_id": dispatch_id,
        "run_id": run_id,
        "topic": topic,
        "log": log,
        "acceptance": {
            "has_dispatch": bool(dispatch_ok and (dispatch_id or client.dry_run)),
            "has_run_id": bool(run_id),
        },
    }


# Back-compat aliases for any leftover callers
run_01 = run_s1
run_02 = lambda client, **kw: run_s3(  # noqa: E731
    client,
    app_id=kw.get("app_id", ""),
    product=kw.get("parameters", {}).get("topic") or kw.get("topic") or "演示商品",
    audience=kw.get("parameters", {}).get("audience") or kw.get("audience") or "",
    topic=kw.get("parameters", {}).get("topic") or "",
)
run_03 = run_s4

RUNNERS = {
    "s1": run_s1,
    "s2": run_s2,
    "s3": run_s3,
    "s4": run_s4,
    "01": run_s1,
    "02": run_s3,
    "03": run_s4,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Run 1007 scenario S1–S4")
    ap.add_argument("scenario", choices=sorted(RUNNERS.keys()), help="s1|s2|s3|s4")
    ap.add_argument("--live", action="store_true", help="Force live (no dry-run)")
    ap.add_argument("--agent-code", default="")
    ap.add_argument("--app-id", default="")
    ap.add_argument("--kb-id", default="")
    ap.add_argument("--goal", default="")
    ap.add_argument("--product", default="便携榨汁杯")
    ap.add_argument("--topic", default="")
    ap.add_argument("--audience", default="上班族")
    args = ap.parse_args()

    cfg = load_config()
    if args.live:
        cfg["dry_run"] = False
    client = EvoFlowClient(cfg)
    key = args.scenario.lower()
    fn = RUNNERS[key]
    if key in {"s1", "01"}:
        result = fn(client, agent_code=args.agent_code, goal=args.goal)
    elif key in {"s2"}:
        result = fn(
            client,
            agent_code=args.agent_code,
            kb_id=args.kb_id,
            goal=args.goal,
        )
    elif key in {"s3", "02"}:
        result = fn(
            client,
            app_id=args.app_id,
            product=args.product,
            audience=args.audience,
            topic=args.topic,
        )
    else:
        result = fn(
            client,
            agent_code=args.agent_code,
            app_id=args.app_id,
            topic=args.topic or "便携榨汁杯 · 上班族早餐场景",
            audience=args.audience,
            goal=args.goal,
        )

    result["config"] = {
        "base_url": cfg["base_url"],
        "dry_run": cfg["dry_run"],
        "has_api_key": bool(cfg.get("api_key")),
    }
    if result.get("ok") and cfg["dry_run"]:
        result["note"] = "dry-run preview only — NOT accepted as live connectivity"
    sid = str(result.get("scenario") or key)
    path = _save_run(sid, result)
    result["saved"] = str(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
