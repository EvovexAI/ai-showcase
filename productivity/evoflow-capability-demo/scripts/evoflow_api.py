#!/usr/bin/env python3
"""EvoFlow gateway client for 1007 business-scenario demos.

Employees  GET/POST /api/proactive/roles*  (+ /employees create)
Knowledge  /api/knowledge/owned/bases*
Workflow   /api/apps*  (+ create/publish/run)
Health     /health
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "evoflow.json"
EXAMPLE_PATH = ROOT / "config" / "evoflow.example.json"
SEED_STATE_PATH = ROOT / "data" / "seed-state.json"

DEMO_PREFIX = "demo-1007"


def load_config() -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    if EXAMPLE_PATH.exists():
        try:
            cfg.update(json.loads(EXAMPLE_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass
    base = os.getenv("EVOFLOW_GATEWAY_URL") or cfg.get("base_url") or "http://127.0.0.1:8080"
    key = os.getenv("EVOFLOW_API_KEY") or cfg.get("api_key") or ""
    dry = os.getenv("EVOFLOW_DRY_RUN")
    if dry is not None:
        dry_run = dry.strip().lower() in {"1", "true", "yes", "on"}
    elif "dry_run" in cfg:
        # Explicit config wins (local gateway often needs no Bearer)
        dry_run = bool(cfg.get("dry_run"))
    else:
        # Default: no key → preview; with key → live
        dry_run = not bool(str(key).strip())
    return {
        "base_url": str(base).rstrip("/"),
        "api_key": str(key).strip(),
        "timeout_seconds": float(cfg.get("timeout_seconds") or 120),
        "default_employee_code": str(cfg.get("default_employee_code") or "").strip(),
        "default_app_id": str(cfg.get("default_app_id") or "").strip(),
        "default_kb_id": str(cfg.get("default_kb_id") or "").strip(),
        "dry_run": dry_run,
        "require_live_for_accept": bool(cfg.get("require_live_for_accept", True)),
    }


def load_seed_state() -> dict[str, Any]:
    if not SEED_STATE_PATH.exists():
        return {}
    try:
        data = json.loads(SEED_STATE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_seed_state(state: dict[str, Any]) -> Path:
    SEED_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEED_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return SEED_STATE_PATH


class EvoFlowClient:
    def __init__(self, cfg: dict[str, Any] | None = None) -> None:
        self.cfg = cfg or load_config()

    @property
    def dry_run(self) -> bool:
        return bool(self.cfg.get("dry_run"))

    def force_live(self) -> None:
        self.cfg["dry_run"] = False

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        retries: int = 6,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        method = method.upper()
        q = ""
        if query:
            parts = []
            for k, v in query.items():
                if v is None or v == "":
                    continue
                parts.append(f"{quote(str(k))}={quote(str(v))}")
            if parts:
                q = "?" + "&".join(parts)
        url = f"{self.cfg['base_url']}{path}{q}"
        trace = {
            "method": method,
            "path": path,
            "url": url,
            "body": body,
            "dry_run": self.dry_run,
        }

        if self.dry_run:
            return {"ok": True, "dry_run": True, "trace": trace, "mock": self._mock(method, path, body)}

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.cfg.get("api_key"):
            headers["Authorization"] = f"Bearer {self.cfg['api_key']}"
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        # Probe endpoints must not inherit the long run timeout (gateway can stall under load)
        if timeout is None:
            if path.endswith("/busy") or path.endswith("/stop") or path.startswith("/health"):
                timeout = 12.0
            else:
                timeout = float(self.cfg["timeout_seconds"])

        last: dict[str, Any] = {}
        for attempt in range(max(1, retries)):
            req = Request(url, data=data, headers=headers, method=method)
            try:
                with urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    payload = json.loads(raw) if raw.strip() else {}
                    if not isinstance(payload, dict):
                        payload = {"data": payload}
                    payload["_trace"] = trace
                    payload.setdefault("ok", True)
                    return payload
            except HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")[:1200]
                last = {
                    "ok": False,
                    "error": f"HTTP {e.code}",
                    "detail": err_body,
                    "trace": trace,
                }
                # Gateway cold-start: extended routers still loading
                if e.code == 503 and "loading_extended" in err_body and attempt + 1 < retries:
                    time.sleep(2.0 + attempt)
                    continue
                return last
            except URLError as e:
                last = {"ok": False, "error": "connection_failed", "detail": str(e.reason), "trace": trace}
                if attempt + 1 < retries:
                    time.sleep(1.5 + attempt)
                    continue
                return last
            except Exception as e:
                last = {"ok": False, "error": type(e).__name__, "detail": str(e), "trace": trace}
                if attempt + 1 < retries:
                    time.sleep(1.0 + attempt)
                    continue
                return last
        return last

    def _mock(self, method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if path in {"/health", "/api/health", "/health/ready"} and method == "GET":
            return {"status": "ready", "phase": "ready", "extended_routers": True, "dry_run": True}
        if path == "/api/proactive/roles" and method == "GET":
            return {
                "roles": [
                    {
                        "agent_code": f"{DEMO_PREFIX}-analyst",
                        "role_name": "演示拆解师",
                        "status": "active",
                        "knowledge_vault_ids": [f"{DEMO_PREFIX}-kb"],
                    }
                ],
                "count": 1,
            }
        if path == "/api/proactive/employees" and method == "POST":
            code = (body or {}).get("agent_code") or f"{DEMO_PREFIX}-analyst"
            return {
                "ok": True,
                "agent_code": code,
                "role_name": (body or {}).get("role_name") or "演示拆解师",
                "knowledge_vault_ids": (body or {}).get("knowledge_vault_ids") or [],
            }
        if path.startswith("/api/proactive/roles/") and method == "PUT":
            return {"ok": True, "agent_code": path.split("/")[-1], **(body or {})}
        if (
            path.startswith("/api/proactive/roles/")
            and method == "GET"
            and path.count("/") == 4
            and not path.endswith(("/busy", "/work-board"))
            and "/dispatch" not in path
        ):
            code = path.split("/")[-1]
            return {
                "agent_code": code,
                "role_name": "拆解师",
                "status": "active",
                "knowledge_vault_ids": [f"{DEMO_PREFIX}-kb"],
            }
        if "/dispatch" in path and method == "POST":
            return {
                "ok": True,
                "accepted": True,
                "round_id": f"dry-{uuid.uuid4().hex[:8]}",
                "goal": (body or {}).get("goal"),
            }
        if path.endswith("/busy"):
            return {"busy": False, "agent_code": path.split("/")[-2]}
        if path.endswith("/stop") and method == "POST":
            return {"ok": True, "stopped": True, "agent_code": path.split("/")[-2]}
        if path.endswith("/work-board"):
            return {
                "tasks": [
                    {
                        "task_id": "dry-task-1",
                        "name": "演示任务",
                        "status": "done",
                        "description": "dry-run 工作台样例",
                    }
                ]
            }
        if path == "/api/knowledge/owned/bases" and method == "GET":
            return {
                "items": [
                    {
                        "id": f"{DEMO_PREFIX}-kb",
                        "name": "演示·爆款钩子库",
                        "description": "dry-run KB",
                    }
                ]
            }
        if path == "/api/knowledge/owned/bases" and method == "POST":
            return {
                "id": f"{DEMO_PREFIX}-kb",
                "name": (body or {}).get("name") or "演示·爆款钩子库",
            }
        if "/documents/manual" in path and method == "POST":
            return {"id": f"dry-doc-{uuid.uuid4().hex[:6]}", "title": (body or {}).get("title")}
        if path.endswith("/search") and method == "POST":
            return {
                "items": [
                    {
                        "title": "钩子样例：先抛结果",
                        "snippet": "普通人用 AI 做副业，第一周就出了第一条播放过万的口播。",
                        "score": 0.92,
                    }
                ],
                "total": 1,
            }
        if path == "/api/apps" and method == "GET":
            return {
                "items": [
                    {
                        "id": f"{DEMO_PREFIX}-app",
                        "name": "演示·商品短视频脚本",
                        "status": "published",
                        "execution_mode": "workflow",
                    }
                ]
            }
        if path == "/api/apps" and method == "POST":
            return {
                "id": f"{DEMO_PREFIX}-app",
                "name": (body or {}).get("name") or "演示·商品短视频脚本",
                "status": "draft",
            }
        if path.endswith("/publish") and method == "POST":
            return {"id": path.split("/")[-2], "status": "published"}
        if path.startswith("/api/apps/") and path.count("/") == 3 and method == "GET":
            return {
                "id": path.split("/")[-1],
                "name": "演示·商品短视频脚本",
                "status": "published",
                "execution_mode": "workflow",
                "parameters": [
                    {"name": "product", "label": "商品", "required": True},
                    {"name": "selling_points", "label": "卖点", "required": False},
                    {"name": "audience", "label": "人群", "required": False},
                    {"name": "topic", "label": "主题", "required": False},
                    {"name": "brief", "label": "调研简报", "required": False},
                ],
                "steps": [
                    {"name": "卖点提炼", "goal": "提炼 3 个核心卖点"},
                    {"name": "口播稿", "goal": "写 30 秒口播"},
                    {"name": "分镜", "goal": "拆 4–6 镜"},
                ],
            }
        if path.endswith("/run") and method == "POST":
            return {"run_id": f"dry-run-{uuid.uuid4().hex[:8]}", "status": "running"}
        if "/runs/" in path and method == "GET":
            return {
                "run_id": path.split("/")[-1],
                "status": "completed",
                "summary": "dry-run：卖点→口播→分镜已模拟完成",
            }
        if path.endswith("/runs") or "/runs?" in path:
            return {"items": [], "total": 0}
        return {"message": "dry-run mock", "path": path}

    @staticmethod
    def _payload(resp: dict[str, Any]) -> dict[str, Any]:
        if resp.get("dry_run") and isinstance(resp.get("mock"), dict):
            return resp["mock"]
        return resp

    # ── health ──

    def health(self) -> dict[str, Any]:
        return self.request("GET", "/health", retries=3)

    def health_ready(self) -> dict[str, Any]:
        return self.request("GET", "/health/ready", retries=3)

    def wait_gateway_ready(self, *, timeout_sec: float = 90) -> dict[str, Any]:
        """Block until /health/ready says extended routers are up (or dry-run)."""
        if self.dry_run:
            return {"ok": True, "dry_run": True, "status": "ready"}
        deadline = time.time() + timeout_sec
        last: dict[str, Any] = {}
        while time.time() < deadline:
            last = self.health_ready()
            if last.get("ok") is False:
                time.sleep(2.0)
                continue
            payload = self._payload(last)
            status = str(payload.get("status") or "").lower()
            phase = str(payload.get("phase") or "").lower()
            if status in {"ready", "ok", "healthy"} or phase == "ready" or payload.get("extended_routers"):
                last["gateway_ready"] = True
                return last
            time.sleep(2.0)
        last["gateway_ready"] = False
        last["timed_out"] = True
        return last

    # ── employees ──

    def list_employees(self, status: str | None = "active") -> dict[str, Any]:
        return self.request("GET", "/api/proactive/roles", query={"status": status} if status else None)

    def get_employee(self, agent_code: str) -> dict[str, Any]:
        return self.request("GET", f"/api/proactive/roles/{agent_code}")

    def create_employee(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/api/proactive/employees", body=payload)

    def update_employee(self, agent_code: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("PUT", f"/api/proactive/roles/{agent_code}", body=payload)

    def dispatch(
        self,
        agent_code: str,
        goal: str,
        *,
        description: str = "",
        priority: str = "normal",
        source: str = "demo-1007",
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/api/proactive/roles/{agent_code}/dispatch",
            body={
                "goal": goal,
                "description": description,
                "priority": priority,
                "source": source,
            },
        )

    def employee_busy(self, agent_code: str) -> dict[str, Any]:
        return self.request("GET", f"/api/proactive/roles/{agent_code}/busy", retries=2, timeout=10)

    def stop_employee(self, agent_code: str) -> dict[str, Any]:
        """Stop in-flight work (keep role active). Clears 409 busy for next dispatch."""
        return self.request("POST", f"/api/proactive/roles/{agent_code}/stop", retries=2, timeout=15)

    def work_board(self, agent_code: str, limit: int = 20) -> dict[str, Any]:
        return self.request(
            "GET",
            f"/api/proactive/roles/{agent_code}/work-board",
            query={"limit": limit},
        )

    def wait_until_idle(self, agent_code: str, *, timeout_sec: float = 15, interval: float = 1.5) -> dict[str, Any]:
        deadline = time.time() + timeout_sec
        last: dict[str, Any] = {}
        while time.time() < deadline:
            last = self.employee_busy(agent_code)
            if last.get("ok") is False and not last.get("dry_run"):
                return last
            busy = bool(self._payload(last).get("busy"))
            if not busy:
                last["idle"] = True
                return last
            time.sleep(interval)
        last["idle"] = False
        last["timed_out"] = True
        return last

    def ensure_idle(self, agent_code: str, *, timeout_sec: float = 60) -> dict[str, Any]:
        """Prefer natural idle; if still busy, stop then wait again."""
        last = self.wait_until_idle(agent_code, timeout_sec=min(8.0, timeout_sec), interval=1.0)
        if last.get("idle"):
            return last
        stopped = self.stop_employee(agent_code)
        last = self.wait_until_idle(agent_code, timeout_sec=min(20.0, timeout_sec), interval=1.0)
        last["stopped"] = stopped
        # If busy probe stalls under load, still allow next dispatch attempt
        if not last.get("idle") and last.get("error"):
            last["idle_best_effort"] = True
        return last

    # ── knowledge ──

    def list_kb(self) -> dict[str, Any]:
        return self.request("GET", "/api/knowledge/owned/bases")

    def create_kb(self, name: str, description: str = "") -> dict[str, Any]:
        return self.request(
            "POST",
            "/api/knowledge/owned/bases",
            body={"name": name, "description": description},
        )

    def ingest_manual(self, kb_id: str, title: str, content: str) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/api/knowledge/owned/bases/{kb_id}/documents/manual",
            body={"title": title, "content": content},
        )

    def search_kb(self, kb_id: str, query: str, *, top_k: int = 5) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/api/knowledge/owned/bases/{kb_id}/search",
            body={"query": query, "mode": "hybrid", "topK": top_k},
        )

    # ── workflow / apps ──

    def list_apps(self) -> dict[str, Any]:
        return self.request("GET", "/api/apps")

    def get_app(self, app_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/apps/{app_id}")

    def create_app(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/api/apps", body=payload)

    def update_app(self, app_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("PUT", f"/api/apps/{app_id}", body=payload)

    def publish_app(self, app_id: str) -> dict[str, Any]:
        return self.request("POST", f"/api/apps/{app_id}/publish")

    def run_app(
        self,
        app_id: str,
        parameters: dict[str, str] | None = None,
        *,
        run_kind: str = "debug",
        trigger_kind: str = "manual",
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/api/apps/{app_id}/run",
            body={
                "parameters": parameters or {},
                "run_kind": run_kind,
                "trigger_kind": trigger_kind,
            },
        )

    def run_status(self, run_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/apps/runs/{run_id}")

    def list_runs(self, app_id: str, limit: int = 5) -> dict[str, Any]:
        return self.request("GET", f"/api/apps/{app_id}/runs", query={"limit": limit})

    def wait_run(
        self,
        run_id: str,
        *,
        timeout_sec: float = 90,
        interval: float = 2.0,
    ) -> dict[str, Any]:
        terminal = {"completed", "failed", "cancelled", "canceled", "error", "timeout"}
        deadline = time.time() + timeout_sec
        last: dict[str, Any] = {}
        while time.time() < deadline:
            last = self.run_status(run_id)
            if last.get("ok") is False and not last.get("dry_run"):
                return last
            status = ""
            if last.get("dry_run"):
                status = str((last.get("mock") or {}).get("status") or "")
            else:
                status = str(last.get("status") or "")
            if status.lower() in terminal:
                return last
            time.sleep(interval)
        last["timed_out"] = True
        return last
