#!/usr/bin/env python3
"""Local demo UI: one page per business scenario (S1–S4) + setup."""

from __future__ import annotations

import json
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evoflow_api import EvoFlowClient, ROOT, load_config, load_seed_state
from run_scenario import _save_run, run_s1, run_s2, run_s3, run_s4
from seed_demo import seed
from smoke_check import run_smoke

WEB = ROOT / "web"
SCENARIOS = ROOT / "scenarios"
HOST, PORT = "127.0.0.1", 8877

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _read_scenarios() -> list[dict]:
    items = []
    for p in sorted(SCENARIOS.glob("s*.json")):
        try:
            items.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return items


def _json(handler: BaseHTTPRequestHandler, data: dict | list, status: int = 200) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    n = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(n) if n else b"{}"
    try:
        return json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        return {}


def _serve_file(handler: BaseHTTPRequestHandler, path: Path, content_type: str) -> None:
    if not path.exists() or not path.is_file():
        handler.send_error(404)
        return
    data = path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-cache")
    handler.end_headers()
    handler.wfile.write(data)


def _cfg_public() -> dict:
    cfg = load_config()
    seed_st = load_seed_state()
    # Local gateway often needs no api_key; honour dry_run only
    preview_only = bool(cfg.get("dry_run"))
    return {
        "base_url": cfg["base_url"],
        "dry_run": cfg["dry_run"],
        "has_api_key": bool(cfg.get("api_key")),
        "preview_only": preview_only,
        "require_live_for_accept": bool(cfg.get("require_live_for_accept", True)),
        "default_employee_code": cfg.get("default_employee_code") or seed_st.get("employee_code") or "",
        "default_app_id": cfg.get("default_app_id") or seed_st.get("app_id") or "",
        "default_kb_id": cfg.get("default_kb_id") or seed_st.get("kb_id") or "",
        "seed": seed_st,
        "mode_label": "仅预览，未调通" if preview_only else "已接实网",
    }


def _run_job(job_id: str, scenario: str, payload: dict) -> None:
    cfg = load_config()
    # Default: follow config. Explicit live=true forces real gateway.
    if payload.get("live") is True:
        cfg["dry_run"] = False
    elif payload.get("live") is False:
        cfg["dry_run"] = True
    client = EvoFlowClient(cfg)
    try:
        with _jobs_lock:
            _jobs[job_id]["status"] = "running"
            _jobs[job_id]["message"] = "执行中…"
        sid = scenario.lower().replace("-", "")
        if sid.startswith("s1") or sid == "1":
            result = run_s1(
                client,
                agent_code=str(payload.get("agent_code") or ""),
                goal=str(payload.get("goal") or ""),
            )
            tag = "s1"
        elif sid.startswith("s2") or sid == "2":
            result = run_s2(
                client,
                agent_code=str(payload.get("agent_code") or ""),
                kb_id=str(payload.get("kb_id") or ""),
                goal=str(payload.get("goal") or ""),
                search_query=str(payload.get("search_query") or "短视频钩子 开场"),
            )
            tag = "s2"
        elif sid.startswith("s3") or sid == "3":
            result = run_s3(
                client,
                app_id=str(payload.get("app_id") or ""),
                product=str(payload.get("product") or "便携榨汁杯"),
                selling_points=str(payload.get("selling_points") or "无线便携、30 秒出汁、可洗刀头"),
                audience=str(payload.get("audience") or "上班族"),
            )
            tag = "s3"
        else:
            result = run_s4(
                client,
                agent_code=str(payload.get("agent_code") or ""),
                app_id=str(payload.get("app_id") or ""),
                topic=str(payload.get("topic") or "便携榨汁杯 · 上班族早餐场景"),
                audience=str(payload.get("audience") or "上班族"),
                goal=str(payload.get("goal") or ""),
            )
            tag = "s4"
        result["config"] = {
            "base_url": cfg["base_url"],
            "dry_run": cfg["dry_run"],
            "has_api_key": bool(cfg.get("api_key")),
        }
        if result.get("ok") and cfg["dry_run"]:
            result["note"] = "dry-run 预览成功，不算已调通"
        path = _save_run(tag, result)
        with _jobs_lock:
            _jobs[job_id].update(
                {
                    "status": "done" if result.get("ok") else "error",
                    "message": "完成" if result.get("ok") else (result.get("error") or "失败"),
                    "result": result,
                    "saved": str(path),
                }
            )
    except Exception as exc:
        with _jobs_lock:
            _jobs[job_id].update({"status": "error", "message": str(exc)})


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path in {"/", "/index.html"}:
            return _serve_file(self, WEB / "index.html", "text/html; charset=utf-8")
        if path.startswith("/assets/"):
            name = path[len("/assets/") :]
            ct = "application/javascript" if name.endswith(".js") else "text/css"
            return _serve_file(self, WEB / "assets" / name, ct)

        if path == "/api/health":
            return _json(self, {"ok": True, **_cfg_public()})

        if path == "/api/scenarios":
            return _json(self, {"items": _read_scenarios()})

        if path == "/api/seed-state":
            return _json(self, {"ok": True, "seed": load_seed_state(), **_cfg_public()})

        if path.startswith("/api/jobs/"):
            job_id = path.split("/")[-1]
            with _jobs_lock:
                job = _jobs.get(job_id)
            if not job:
                return _json(self, {"ok": False, "error": "job not found"}, 404)
            return _json(self, job)

        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        payload = _read_json(self)

        if path == "/api/seed":
            cfg = load_config()
            if payload.get("live"):
                cfg["dry_run"] = False
            client = EvoFlowClient(cfg)
            result = seed(client)
            return _json(self, result, 200 if result.get("ok") else 500)

        if path == "/api/smoke":
            cfg = load_config()
            if payload.get("live"):
                cfg["dry_run"] = False
            if not cfg.get("api_key") and payload.get("live"):
                return _json(self, {"ok": False, "error": "缺少 api_key，无法实网 smoke"}, 400)
            allow_dry = bool(payload.get("allow_dry_run"))
            if cfg.get("dry_run") and not allow_dry:
                return _json(
                    self,
                    {
                        "ok": False,
                        "error": "当前为预览模式。勾选实网或 allow_dry_run 仅预览。",
                        "preview_only": True,
                    },
                    400,
                )
            client = EvoFlowClient(cfg)
            report = run_smoke(client)
            return _json(self, report, 200 if report.get("ok") else 500)

        if path == "/api/run":
            scenario = str(payload.get("scenario") or "").strip()
            if not scenario:
                return _json(self, {"ok": False, "error": "缺少 scenario"}, 400)
            job_id = uuid.uuid4().hex[:12]
            with _jobs_lock:
                _jobs[job_id] = {
                    "id": job_id,
                    "status": "queued",
                    "message": "排队中",
                    "scenario": scenario,
                }
            threading.Thread(target=_run_job, args=(job_id, scenario, payload), daemon=True).start()
            return _json(self, {"ok": True, "job_id": job_id})

        self.send_error(404)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"1007 demo UI → http://{HOST}:{PORT}/", flush=True)
    print("Hash routes: #/  #/s1 #/s2 #/s3 #/s4  #/setup", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye", flush=True)


if __name__ == "__main__":
    main()
