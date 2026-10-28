#!/usr/bin/env python3
"""Live smoke: health → seed → S1–S4. All must pass to claim「已调通」."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evoflow_api import EvoFlowClient, ROOT, load_config, load_seed_state
from run_scenario import _save_run, run_s1, run_s2, run_s3, run_s4
from seed_demo import seed

SMOKE_LOG = ROOT / "data" / "runs"


def _row(name: str, ok: bool, elapsed_ms: float, detail: str = "") -> dict:
    return {
        "check": name,
        "ok": ok,
        "elapsed_ms": round(elapsed_ms, 1),
        "detail": (detail or "")[:400],
    }


def run_smoke(client: EvoFlowClient) -> dict:
    rows: list[dict] = []
    t0 = time.time()

    # 1. Health + wait until extended routers ready (avoid 503 loading_extended)
    t = time.time()
    h = client.health()
    ready = client.wait_gateway_ready(timeout_sec=90)
    health_ok = (
        h.get("ok") is not False
        and not (h.get("error") and not h.get("dry_run"))
        and (client.dry_run or bool(ready.get("gateway_ready")))
    )
    detail = str(
        ready.get("status")
        or ready.get("phase")
        or h.get("status")
        or h.get("error")
        or ready.get("detail")
        or "ok"
    )
    if ready.get("timed_out"):
        detail = f"ready_timeout:{detail}"
    rows.append(_row("health", health_ok, (time.time() - t) * 1000, detail))
    if not health_ok and not client.dry_run:
        return {
            "ok": False,
            "live": not client.dry_run,
            "accepted_as_live": False,
            "rows": rows,
            "error": "网关探活/ready 失败，阻断调通验收",
            "note": "存在失败项，禁止写「已调通」",
            "elapsed_ms": round((time.time() - t0) * 1000, 1),
        }

    # 2. Seed
    t = time.time()
    seeded = seed(client)
    seed_ok = bool(seeded.get("ok"))
    st = seeded.get("seed") or load_seed_state()
    detail = (
        f"emp={st.get('employee_code')} kb={st.get('kb_id')} app={st.get('app_id')}"
        if seed_ok
        else str(seeded.get("error") or seeded)
    )
    rows.append(_row("seed", seed_ok, (time.time() - t) * 1000, detail))

    # 3–6 scenarios (clear employee between dispatch-heavy ones)
    emp = str(st.get("employee_code") or client.cfg.get("default_employee_code") or "")
    scenarios = [
        ("S1", lambda: run_s1(client)),
        ("S2", lambda: run_s2(client)),
        ("S3", lambda: run_s3(client)),
        ("S4", lambda: run_s4(client)),
    ]
    scenario_results: dict[str, dict] = {}
    for name, fn in scenarios:
        if emp and name in {"S2", "S4"}:
            client.ensure_idle(emp, timeout_sec=45)
        t = time.time()
        try:
            result = fn()
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        scenario_results[name] = result
        path = _save_run(f"smoke-{name.lower()}", result)
        result["saved"] = str(path)
        ok = bool(result.get("ok"))
        detail = ""
        if not ok:
            detail = str(result.get("error") or result.get("acceptance") or "")
        else:
            acc = result.get("acceptance") or {}
            detail = json.dumps(acc, ensure_ascii=False)
        rows.append(_row(name, ok, (time.time() - t) * 1000, detail))
        if emp and name in {"S1", "S2"}:
            # Free the employee before next dispatch-heavy scenario; skip after S4
            client.ensure_idle(emp, timeout_sec=25)

    all_ok = all(r["ok"] for r in rows)
    live = not client.dry_run
    # Plan rule: dry-run must NEVER count as「已调通」
    accepted = bool(all_ok and live)

    report = {
        "ok": all_ok,
        "live": live,
        "accepted_as_live": accepted,
        "require_live_for_accept": bool(client.cfg.get("require_live_for_accept", True)),
        "base_url": client.cfg.get("base_url"),
        "has_api_key": bool(client.cfg.get("api_key")),
        "seed": st,
        "rows": rows,
        "scenarios": {k: {"ok": v.get("ok"), "acceptance": v.get("acceptance"), "saved": v.get("saved")} for k, v in scenario_results.items()},
        "elapsed_ms": round((time.time() - t0) * 1000, 1),
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "note": (
            "全部关键断言通过，可作为「已调通」汇报"
            if accepted
            else (
                "dry-run 仅离线预览，禁止冒充调通"
                if not live
                else "存在失败项，禁止写「已调通」"
            )
        ),
    }
    return report


def _print_table(rows: list[dict]) -> None:
    print(f"{'CHECK':<10} {'OK':<6} {'ms':>8}  DETAIL")
    print("-" * 72)
    for r in rows:
        flag = "PASS" if r["ok"] else "FAIL"
        print(f"{r['check']:<10} {flag:<6} {r['elapsed_ms']:>8}  {r['detail'][:50]}")


def main() -> int:
    ap = argparse.ArgumentParser(description="1007 smoke / acceptance")
    ap.add_argument("--live", action="store_true", help="Force live gateway")
    ap.add_argument("--allow-dry-run", action="store_true", help="Run smoke in dry-run (preview only)")
    args = ap.parse_args()

    cfg = load_config()
    if args.live:
        cfg["dry_run"] = False
    if not args.allow_dry_run and not args.live:
        # Prefer live when config says so, or when key present
        if cfg.get("api_key") or cfg.get("dry_run") is False:
            cfg["dry_run"] = False
        else:
            print(
                "ERROR: 未配置实网。在 evoflow.json 设 dry_run=false（本机网关可无 key），"
                "或填 api_key 后 --live；离线预览用 --allow-dry-run。",
                file=sys.stderr,
            )
            return 2

    client = EvoFlowClient(cfg)
    report = run_smoke(client)
    SMOKE_LOG.mkdir(parents=True, exist_ok=True)
    out = SMOKE_LOG / f"smoke_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["saved"] = str(out)

    _print_table(report["rows"])
    print()
    print(json.dumps({k: report[k] for k in ("ok", "live", "accepted_as_live", "note", "saved", "elapsed_ms")}, ensure_ascii=False, indent=2))
    if report.get("accepted_as_live"):
        return 0
    if report.get("ok") and not report.get("live"):
        return 3  # preview ok but not accepted
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
