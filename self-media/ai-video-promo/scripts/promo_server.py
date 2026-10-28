#!/usr/bin/env python3
"""
宣传视频制作服务器 - 集成配音、策划和工作台
Promo Video Production Server — TTS settings, storyboard plans, workbench, web UI.

设计目标：
  - 与 ai-video-decompose (1002) 解耦：1003 只负责「制作 + 配音」侧。
  - 后端复刻自 feishu_downloads/ai-showcase/self-media/douyin-video-pipeline 的 web_server.py，但去掉了
    download/analyze/vision 等拆解侧端点，保留：
      * TTS 设置读写（公开 + 掩码）
      * TTS 试听（preview）
      * 策划 (productions) CRUD + 音频生成
      * Workbench API 透传（tasks/skills/drafts/...）
      * /api/workbench/jobs（合成任务）
  - 端口默认 8766（避免与 1004 的 8765 冲突）。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import mimetypes
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS))

logger = logging.getLogger("promo_server")


# ---------- 动态加载兄弟模块（与 1004 web_server.py 同样的风格） ----------

def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_paths = _load_module("paths", "paths.py")
_tts_settings = _load_module("tts_settings", "tts_settings.py")
_volc_tts = _load_module("volc_tts", "volc_tts.py")
_evoflow = _load_module("evoflow_client", "evoflow_client.py")
_workbench = _load_module("workbench_api", "workbench_api.py")
_skill_runners = _load_module("skill_runners", "skill_runners.py")
_automation = _load_module("automation_scheduler", "automation_scheduler.py")

ROOT = _paths.ROOT
list_productions = _paths.list_productions
load_production = _paths.load_production
save_production = _paths.save_production
new_production_template = _paths.new_production_template
production_file = _paths.production_file
sanitize_plan_id = _paths.sanitize_plan_id
PRODUCTIONS_DIR = _paths.PRODUCTIONS_DIR
production_audio_dir = _paths.production_audio_dir

load_tts_settings = _tts_settings.load_tts_settings
save_tts_settings = _tts_settings.save_tts_settings
public_tts_settings = _tts_settings.public_tts_settings
tts_configured = _tts_settings.tts_configured
get_resolved_credentials = _tts_settings.get_resolved_credentials

synthesize_speech = _volc_tts.synthesize_speech
try_chat_or_hint = _evoflow.try_chat_or_hint

WORKBENCH_DIR = ROOT / "workbench"
WEB_DIR = ROOT / "web"
HOST = "127.0.0.1"
PORT = 8766

jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


# ---------- 工具函数 ----------

def _query_dict(parsed) -> dict[str, str]:
    return {k: v[0] if len(v) == 1 else ",".join(v) for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}


def json_response(handler: BaseHTTPRequestHandler, data: dict, status: int = 200) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", 0))
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        return json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def set_job(job_id: str, **fields) -> None:
    with jobs_lock:
        job = jobs.get(job_id, {})
        job.update(fields)
        job["updated_at"] = time.time()
        jobs[job_id] = job


def get_job(job_id: str) -> dict | None:
    with jobs_lock:
        return jobs.get(job_id)


# ---------- 业务：策划 / 配音 ----------

def production_payload(plan_id: str) -> dict:
    plan = load_production(plan_id)
    audio_dir = production_audio_dir(plan_id)
    manifest: list[dict] = []
    if audio_dir.exists():
        for mp3 in sorted(audio_dir.glob("*.mp3")):
            stat = mp3.stat()
            manifest.append(
                {
                    "filename": mp3.name,
                    "url": f"/api/productions/{plan_id}/audio/{mp3.name}",
                    "size_bytes": stat.st_size,
                    "updated_at": stat.st_mtime,
                }
            )
    plan["audio_manifest"] = manifest
    return plan


def build_production_revise_prompt(plan: dict, instruction: str) -> str:
    return (
        f"你是宣传片策划助手。请基于以下策划稿，按指令调整（中文回答）：\n\n"
        f"指令：{instruction}\n\n"
        f"策划稿：\n```json\n{json.dumps(plan, ensure_ascii=False, indent=2)[:6000]}\n```"
    )


def ai_revise_plan(plan: dict, instruction: str) -> dict:
    prompt = build_production_revise_prompt(plan, instruction)
    text, used, status = try_chat_or_hint(prompt, skill_id="plan-from-report")
    return {"text": text, "via_evoflow": used, "status_message": status}


def run_production_tts(job_id: str, plan_id: str, speaker: str | None = None) -> None:
    """后台生成策划稿每段配音 mp3。"""
    try:
        set_job(job_id, status="running", step="loading", message="加载策划稿…", progress=5)
        plan = load_production(plan_id)
        shots = list(plan.get("shots") or [])
        if not shots:
            raise ValueError("策划稿没有分镜（shots）可配音")
        api_key, resource, default_speaker = get_resolved_credentials()
        if not api_key:
            raise ValueError("未配置 TTS API Key，请先在「设置 → 配音」填写")
        use_speaker = (speaker or default_speaker).strip()

        audio_dir = production_audio_dir(plan_id)
        total = len(shots)
        for i, shot in enumerate(shots):
            text = (shot.get("voiceover") or shot.get("subtitle") or "").strip()
            if not text:
                continue
            set_job(
                job_id,
                step="synth",
                message=f"配音 {i + 1}/{total}：{text[:20]}…",
                progress=int(5 + 90 * (i / total)),
            )
            audio, used_speaker = synthesize_speech(
                text, api_key=api_key, speaker=use_speaker, resource_id=resource
            )
            digest = hashlib.md5(audio).hexdigest()[:8]
            out = audio_dir / f"shot_{i + 1:02d}_{digest}.mp3"
            out.write_bytes(audio)
            shot.setdefault("audio", {})[used_speaker] = out.name
        plan["updated_at"] = time.time()
        save_production(plan)
        set_job(
            job_id,
            status="done",
            step="done",
            message=f"✓ 已生成 {total} 段配音",
            progress=100,
            plan_id=plan_id,
        )
    except Exception as exc:
        logger.exception("production tts failed: %s", exc)
        set_job(job_id, status="error", step="error", message=str(exc), progress=100)


def tts_preview_job(job_id: str, text: str, speaker: str) -> None:
    try:
        set_job(job_id, status="running", step="synth", message="试听合成中…", progress=30)
        api_key, resource, default_speaker = get_resolved_credentials()
        if not api_key:
            raise ValueError("未配置 TTS API Key")
        use_speaker = (speaker or default_speaker).strip()
        audio, used = synthesize_speech(
            text, api_key=api_key, speaker=use_speaker, resource_id=resource, preview=True
        )
        cache_dir = ROOT / "productions" / "_tts_preview"
        cache_dir.mkdir(parents=True, exist_ok=True)
        out = cache_dir / f"{job_id}.mp3"
        out.write_bytes(audio)
        set_job(
            job_id,
            status="done",
            step="done",
            message=f"✓ 试听已生成（{used}）",
            progress=100,
            audio_url=f"/api/tts/preview/{job_id}.mp3",
        )
    except Exception as exc:
        logger.exception("tts preview failed: %s", exc)
        set_job(job_id, status="error", step="error", message=str(exc), progress=100)


# ---------- Workbench 透传 ----------

def _try_workbench_get(path: str, query: dict | None = None):
    return _workbench.handle_get(path, query)


def _try_workbench_post(path: str, body: dict):
    return _workbench.handle_post(path, body, start_job=_workbench_start_job, run_skill_fn=_workbench_run_skill)


def _try_workbench_patch(path: str, body: dict):
    return _workbench.handle_patch(path, body)


def _try_workbench_delete(path: str):
    return _workbench.handle_delete(path)


def _workbench_start_job(prompt: str, ctx: dict) -> str:
    job_id = uuid.uuid4().hex[:12]
    set_job(job_id, status="running", step="chat", message="派 AI 执行中…", progress=20, prompt=prompt, ctx=ctx)

    def _worker():
        try:
            text, used, status = try_chat_or_hint(prompt, context=ctx)
            set_job(
                job_id,
                status="done",
                step="done",
                message=status or ("EvoFlow 已返回" if used else "本地提示已生成"),
                progress=100,
                output=text,
                via_evoflow=used,
            )
            task_id = (ctx or {}).get("task_id")
            if task_id:
                _workbench.apply_dispatch_result(
                    task_id, job_id, text, used_evoflow=used
                )
        except Exception as exc:
            logger.exception("workbench job failed: %s", exc)
            set_job(job_id, status="error", step="error", message=str(exc), progress=100)

    threading.Thread(target=_worker, daemon=True).start()
    return job_id


def _workbench_run_skill(skill_id: str, body: dict) -> dict:
    return _skill_runners.run_skill(skill_id, body)


# ---------- HTTP Handler ----------

class Handler(BaseHTTPRequestHandler):
    server_version = "PromoServer/0.1"

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return

    # --- CORS ---

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # --- GET ---

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        # 静态资源
        if path in {"/", "/index.html"}:
            return self._serve_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
        if path.startswith("/assets/"):
            return self._serve_assets(path)
        if path.startswith("/workbench/") or path == "/workbench":
            return self._serve_file(WEB_DIR / "index.html", "text/html; charset=utf-8")

        # Workbench API 透传
        wb = _try_workbench_get(path, _query_dict(parsed))
        if wb is not None:
            return json_response(self, wb[0], wb[1])

        # 1003 自有 API
        if path == "/api/health":
            return json_response(self, {"ok": True, "service": "ai-video-promo", "port": PORT})
        if path == "/api/settings/tts":
            return json_response(self, public_tts_settings())
        if path == "/api/productions":
            return json_response(self, {"plans": list_productions()})

        if path.startswith("/api/productions/"):
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 5 and parts[3] == "audio":
                return self._serve_production_audio(parts[2], unquote(parts[4]))
            if len(parts) >= 3:
                try:
                    return json_response(self, production_payload(parts[2]))
                except Exception as exc:
                    return json_response(self, {"error": str(exc)}, 404)

        if path.startswith("/api/tts/preview/") and path.endswith(".mp3"):
            name = path.rsplit("/", 1)[-1]
            target = (ROOT / "productions" / "_tts_preview" / name).resolve()
            root = (ROOT / "productions" / "_tts_preview").resolve()
            if not str(target).startswith(str(root)) or not target.is_file():
                return self._not_found()
            return self._serve_file(target, "audio/mpeg", cache=False)

        if path.startswith("/api/jobs/"):
            job_id = path.rsplit("/", 1)[-1]
            job = get_job(job_id)
            if not job:
                return json_response(self, {"error": "job not found"}, 404)
            return json_response(self, job)

        if path == "/api/workbench/evoflow/status":
            from evoflow_client import load_evoflow_config

            cfg = load_evoflow_config()
            return json_response(
                self,
                {
                    "enabled": bool(cfg.get("enabled")),
                    "configured": bool(cfg.get("api_key")),
                    "base_url": cfg.get("base_url"),
                    "default_model": cfg.get("default_model"),
                },
            )

        return self._not_found()

    # --- POST ---

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        body = read_json(self)

        # Workbench 透传
        if path.startswith("/api/workbench/"):
            wb = _try_workbench_post(path, body)
            return json_response(self, wb[0], wb[1])

        if path == "/api/settings/tts":
            try:
                return json_response(self, save_tts_settings(body), 200)
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 400)

        if path == "/api/productions":
            title = str(body.get("title") or "新视频策划").strip()
            plan = new_production_template(title=title)
            plan.update({k: v for k, v in body.items() if k in {"goal", "aspect_ratio", "total_duration", "full_script", "notes"}})
            path_saved = save_production(plan)
            return json_response(self, {"id": plan["id"], "path": str(path_saved)}, 201)

        if path.startswith("/api/productions/") and path.endswith("/ai-revise"):
            plan_id = path.split("/")[-2]
            try:
                plan = load_production(plan_id)
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 404)
            instruction = str(body.get("instruction") or "").strip() or "润色分镜文案"
            return json_response(self, ai_revise_plan(plan, instruction))

        if path.startswith("/api/productions/") and path.endswith("/synthesize"):
            plan_id = path.split("/")[-2]
            try:
                load_production(plan_id)
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 404)
            job_id = uuid.uuid4().hex[:12]
            set_job(job_id, status="queued", step="queued", message="排队中…", progress=0, plan_id=plan_id)
            threading.Thread(
                target=run_production_tts,
                args=(job_id, plan_id),
                kwargs={"speaker": body.get("speaker")},
                daemon=True,
            ).start()
            return json_response(self, {"job_id": job_id})

        if path == "/api/tts/preview":
            text = str(body.get("text") or "").strip()
            if not text:
                return json_response(self, {"error": "缺少 text"}, 400)
            speaker = str(body.get("speaker") or "").strip()
            job_id = uuid.uuid4().hex[:12]
            set_job(job_id, status="queued", step="queued", message="排队中…", progress=0)
            threading.Thread(
                target=tts_preview_job, args=(job_id, text, speaker), daemon=True
            ).start()
            return json_response(self, {"job_id": job_id})

        return self._not_found()

    # --- PATCH ---

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        body = read_json(self)
        if path.startswith("/api/workbench/"):
            wb = _try_workbench_patch(path, body)
            return json_response(self, wb[0], wb[1])
        if path.startswith("/api/productions/"):
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 3:
                plan_id = parts[2]
                try:
                    plan = load_production(plan_id)
                except Exception as exc:
                    return json_response(self, {"error": str(exc)}, 404)
                plan.update({k: v for k, v in body.items() if k != "id"})
                save_production(plan)
                return json_response(self, plan)
        return self._not_found()

    # --- DELETE ---

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith("/api/workbench/"):
            wb = _try_workbench_delete(path)
            return json_response(self, wb[0], wb[1])
        if path.startswith("/api/productions/"):
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 3:
                plan_id = parts[2]
                target = production_file(plan_id)
                if target.exists():
                    target.unlink()
                    return json_response(self, {"ok": True})
                return json_response(self, {"error": "not found"}, 404)
        return self._not_found()

    # --- 私有 helper ---

    def _serve_assets(self, path: str):
        target = (WEB_DIR / path.lstrip("/")).resolve()
        root = WEB_DIR.resolve()
        if not str(target).startswith(str(root)):
            return self._not_found()
        if target.is_file():
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            return self._serve_file(target, ctype, cache=False)
        return self._not_found()

    def _serve_production_audio(self, plan_id: str, filename: str):
        if ".." in filename or "/" in filename or "\\" in filename:
            return self._not_found()
        audio_dir = production_audio_dir(plan_id).resolve()
        target = (audio_dir / filename).resolve()
        if not str(target).startswith(str(audio_dir)) or not target.is_file():
            return self._not_found()
        return self._serve_file(target, "audio/mpeg", cache=False)

    def _serve_file(self, path: Path, content_type: str, cache: bool = True) -> None:
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return self._not_found()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if not cache:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _not_found(self) -> None:
        json_response(self, {"error": "not found"}, 404)


# ---------- 启动 ----------

def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    WORKBENCH_DIR.mkdir(parents=True, exist_ok=True)
    (WORKBENCH_DIR / "data" / "drafts").mkdir(parents=True, exist_ok=True)
    PRODUCTIONS_DIR.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(
        f"""
╔═══════════════════════════════════════════════════════════╗
║   🎬 AI Video Promo - 宣传视频制作服务 (port {PORT})       ║
║                                                           ║
║   Web UI:   http://localhost:{PORT}                          ║
║   TTS:      /api/settings/tts                             ║
║   Plans:    /api/productions                              ║
║   WB:       /api/workbench/*                              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down…")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
