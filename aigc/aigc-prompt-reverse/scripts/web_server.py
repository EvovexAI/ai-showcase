#!/usr/bin/env python3
"""Local web UI server for the 起号 Douyin pipeline."""

from __future__ import annotations

import importlib.util
import json
import mimetypes
import shutil
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_download = _load_module("download_douyin", "download-douyin.py")
_analyze = _load_module("analyze_douyin", "analyze_douyin.py")
_paths = _load_module("paths", "paths.py")
_tts_settings = _load_module("tts_settings", "tts_settings.py")
_volc_tts = _load_module("volc_tts", "volc_tts.py")
_vision = _load_module("vision_describe", "vision_describe.py")

download = _download.download
extract_url = _download.extract_url
refresh_meta = _download.refresh_meta
analyze = _analyze.analyze
prepare_vision_manifest = _vision.prepare_vision_manifest
merge_descriptions = _vision.merge_descriptions
md_report_to_html = _analyze.md_to_html
ROOT = _paths.ROOT
analysis_dir = _paths.analysis_dir
list_projects = _paths.list_projects
load_meta = _paths.load_meta
resolve_project = _paths.resolve_project
video_file = _paths.video_file
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

WEB_DIR = ROOT / "web"
HOST = "127.0.0.1"
PORT = 8768

# 反推系统提示词：用户可在页面编辑；.default.md 为出厂备份
SYSTEM_PROMPT_FILE = ROOT / "prompts" / "reverse-system.md"
SYSTEM_PROMPT_DEFAULT_FILE = ROOT / "prompts" / "reverse-system.default.md"


def load_system_prompt() -> dict:
    SYSTEM_PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SYSTEM_PROMPT_FILE.exists() and SYSTEM_PROMPT_DEFAULT_FILE.exists():
        SYSTEM_PROMPT_FILE.write_text(
            SYSTEM_PROMPT_DEFAULT_FILE.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    content = ""
    if SYSTEM_PROMPT_FILE.exists():
        content = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    default_content = ""
    if SYSTEM_PROMPT_DEFAULT_FILE.exists():
        default_content = SYSTEM_PROMPT_DEFAULT_FILE.read_text(encoding="utf-8")
    elif content:
        default_content = content
    is_custom = bool(default_content) and content.strip() != default_content.strip()
    return {
        "content": content,
        "default_content": default_content,
        "is_custom": is_custom,
        "path": str(SYSTEM_PROMPT_FILE.relative_to(ROOT)).replace("\\", "/"),
    }


def save_system_prompt(content: str) -> dict:
    text = (content or "").strip()
    if not text:
        raise ValueError("系统提示词不能为空")
    if len(text) > 200_000:
        raise ValueError("系统提示词过长（上限约 20 万字符）")
    SYSTEM_PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    # 首次保存前若尚无 default，先备份当前权威稿
    if not SYSTEM_PROMPT_DEFAULT_FILE.exists() and SYSTEM_PROMPT_FILE.exists():
        SYSTEM_PROMPT_DEFAULT_FILE.write_text(
            SYSTEM_PROMPT_FILE.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    SYSTEM_PROMPT_FILE.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
    return load_system_prompt()


def reset_system_prompt() -> dict:
    if not SYSTEM_PROMPT_DEFAULT_FILE.exists():
        raise FileNotFoundError("找不到出厂默认提示词 prompts/reverse-system.default.md")
    SYSTEM_PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    SYSTEM_PROMPT_FILE.write_text(
        SYSTEM_PROMPT_DEFAULT_FILE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return load_system_prompt()

jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


def _query_dict(parsed) -> dict[str, str]:
    return {k: v[0] if len(v) == 1 else ",".join(v) for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}


def project_payload_title(project: Path) -> str:
    try:
        meta = load_meta(project)
    except Exception:
        meta = {}
    title = meta.get("title") or meta.get("desc") or ""
    if not title:
        report_path = analysis_dir(project) / "report.json"
        if report_path.exists():
            try:
                title = json.loads(report_path.read_text(encoding="utf-8")).get("title", "")
            except Exception:
                pass
    return title or project.name


def meta_report_kb_path(project: Path) -> str:
    try:
        return load_meta(project).get("report_kb_path", "")
    except Exception:
        return ""


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
    return json.loads(raw.decode("utf-8") or "{}")


def set_job(job_id: str, **fields) -> None:
    with jobs_lock:
        jobs.setdefault(job_id, {})
        jobs[job_id].update(fields)


def run_reanalyze(
    job_id: str,
    project_id: str,
    *,
    force: bool = False,
    keyframe_mode: str = "transcript",
    frame_count: int = 30,
    interval_seconds: float = 3.5,
    vision_prep: bool = False,
    analysis_mode: str = "content",
) -> None:
    try:
        project = resolve_project(project_id)
        aweme_id = project.name
        out = analysis_dir(project)
        mode_label = "反推提示词" if analysis_mode == "prompt_reverse" else "内容拆解"

        set_job(
            job_id,
            status="running",
            step="analyze",
            message=(
                f"完整重转写口播（{mode_label}）…"
                if force
                else f"重新切分镜头与章节（{mode_label}）…"
            ),
            progress=30,
            project_id=aweme_id,
        )

        scenes_dir = out / "scenes"
        if scenes_dir.exists():
            shutil.rmtree(scenes_dir)

        analyze(
            project,
            out,
            full=True,
            vision_prep=vision_prep,
            force=force,
            keyframe_mode=keyframe_mode,
            frame_count=frame_count,
            interval_seconds=interval_seconds,
            analysis_mode=analysis_mode,
        )

        set_job(
            job_id,
            status="done",
            step="done",
            message="重新拆解完成",
            progress=100,
            project_id=aweme_id,
        )
    except Exception as exc:
        import traceback as _tb
        try:
            with open(ROOT / "data" / "reanalyze_error.log", "a", encoding="utf-8") as _f:
                _f.write(_tb.format_exc() + "\n" + "=" * 60 + "\n")
        except Exception:
            pass
        set_job(job_id, status="error", message=str(exc), progress=100)


def run_pipeline(
    job_id: str,
    share_text: str,
    *,
    keyframe_mode: str = "transcript",
    frame_count: int = 30,
    interval_seconds: float = 3.5,
    vision_prep: bool = False,
    analysis_mode: str = "content",
) -> None:
    try:
        set_job(job_id, status="running", step="download", message="正在下载视频…", progress=10)
        url = extract_url(share_text)
        project = download(url, share_text=share_text)
        aweme_id = project.name

        mode_label = "反推提示词" if analysis_mode == "prompt_reverse" else "内容拆解"
        set_job(
            job_id,
            step="analyze",
            message=f"正在转写口播、提取关键帧（{mode_label}）…",
            progress=40,
            project_id=aweme_id,
        )
        analyze(
            project,
            analysis_dir(project),
            full=True,
            vision_prep=vision_prep,
            keyframe_mode=keyframe_mode,
            frame_count=frame_count,
            interval_seconds=interval_seconds,
            analysis_mode=analysis_mode,
        )

        set_job(
            job_id,
            status="done",
            step="done",
            message="反推完成" if analysis_mode == "prompt_reverse" else "拆解完成",
            progress=100,
            project_id=aweme_id,
        )
    except Exception as exc:
        set_job(job_id, status="error", message=str(exc), progress=100)


def run_vision_prep(job_id: str, project_id: str) -> None:
    try:
        project = resolve_project(project_id)
        set_job(
            job_id,
            status="running",
            step="vision_prep",
            message="正在生成视觉任务清单（不调用模型）…",
            progress=40,
            project_id=project.name,
        )
        prepare_vision_manifest(project)
        set_job(
            job_id,
            status="done",
            step="done",
            message="视觉任务清单已生成",
            progress=100,
            project_id=project.name,
        )
    except Exception as exc:
        set_job(job_id, status="error", message=str(exc), progress=100)


def vision_status(project: Path, report: dict | None = None) -> dict:
    analysis = analysis_dir(project)
    vision = analysis / "vision"
    manifest_path = vision / "manifest.json"
    desc_path = vision / "descriptions.json"
    manifest: dict = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    rep_count = len(manifest.get("representative_scenes", []))
    task_count = manifest.get("total_scenes", 0)
    merged_count = 0
    if report:
        merged_count = sum(1 for sc in report.get("scenes", []) if sc.get("vision"))

    if desc_path.exists() and merged_count:
        state = "merged"
    elif desc_path.exists():
        state = "described"
    elif manifest_path.exists():
        state = "manifest_ready"
    else:
        state = "none"

    return {
        "state": state,
        "has_manifest": manifest_path.exists(),
        "has_descriptions": desc_path.exists(),
        "representative_count": rep_count,
        "task_count": task_count,
        "merged_scene_count": merged_count,
    }


def project_meta_display(project: Path, report: dict | None = None) -> dict:
    meta = load_meta(project)
    report = report or {}
    aweme_id = meta.get("aweme_id") or project.name
    hashtags = meta.get("hashtags") or report.get("hashtags") or []
    share_url = meta.get("source_url") or ""
    if not share_url and meta.get("share_text"):
        try:
            share_url = extract_url(meta["share_text"])
        except Exception:
            pass

    return {
        "aweme_id": aweme_id,
        "title": report.get("title") or meta.get("desc") or meta.get("title", ""),
        "desc": meta.get("desc") or meta.get("title", ""),
        "author": meta.get("author_nickname", ""),
        "author_id": meta.get("author_unique_id", ""),
        "hashtags": hashtags,
        "source_url": share_url,
        "share_text": meta.get("share_text", ""),
        "canonical_url": meta.get("canonical_url") or f"https://www.douyin.com/video/{aweme_id}",
        "created_at": meta.get("created_at", ""),
        "last_analysis_at": meta.get("last_analysis_at", ""),
    }


def analysis_status(project: Path) -> str:
    """done = report.json exists; partial = transcript only; pending = not started."""
    analysis = analysis_dir(project)
    if (analysis / "report.json").exists():
        return "done"
    if (analysis / "transcript.txt").exists() or (analysis / "transcript.srt").exists():
        return "partial"
    return "pending"


def project_summary(project: Path) -> dict:
    meta = load_meta(project)
    analysis = analysis_dir(project)
    report_path = analysis / "report.json"
    report: dict = {}
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))

    scenes = report.get("scenes", [])
    cover_url = None
    if scenes:
        rel = scenes[0].get("frame_path", "").replace("\\", "/")
        if rel:
            cover_url = f"/media/{project.name}/{rel}"

    chapters = report.get("aligned") or report.get("chapters", [])

    return {
        "id": project.name,
        "title": report.get("title") or meta.get("title", ""),
        "author": meta.get("author_nickname", ""),
        "duration_label": report.get("duration_label", ""),
        "updated_at": meta.get("last_analysis_at") or meta.get("updated_at", ""),
        "has_report": report_path.exists(),
        "analysis_status": analysis_status(project),
        "analysis_mode": report.get("analysis_mode") or meta.get("analysis_mode") or "content",
        "cover_url": cover_url,
        "script_chars": report.get("script", {}).get("total_chars", 0),
        "chapter_count": len(chapters),
        "scene_count": len(scenes),
    }


def project_payload(project: Path) -> dict:
    meta = load_meta(project)
    analysis = analysis_dir(project)
    report = {}
    report_path = analysis / "report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))

    scenes = []
    for sc in report.get("scenes", []):
        rel = sc.get("frame_path", "").replace("\\", "/")
        scenes.append(
            {
                **sc,
                "image_url": f"/media/{project.name}/{rel}",
            }
        )

    return {
        "id": project.name,
        "meta": project_meta_display(project, report),
        "title": report.get("title") or meta.get("title", ""),
        "duration_label": report.get("duration_label", ""),
        "script": {
            "total_chars": report.get("script", {}).get("total_chars", 0),
            "segment_count": report.get("script", {}).get("segment_count", 0),
        },
        "voice": report.get("voice", {}),
        "hashtags": report.get("hashtags", []),
        "chapters": report.get("aligned") or report.get("chapters", []),
        "segments": report.get("script", {}).get("segments", []),
        "scenes": scenes,
        "has_report": report_path.exists(),
        "analysis_status": analysis_status(project),
        "video_url": f"/media/{project.name}/video.mp4",
        "keyframe_mode": report.get("keyframe_mode", "scene"),
        "frame_count": report.get("frame_count"),
        "analysis_mode": report.get("analysis_mode") or meta.get("analysis_mode") or "content",
        "media": report.get("media") or {},
        "vision": vision_status(project, report),
        "report_url": f"/api/projects/{project.name}/report",
    }


def build_ai_revise_prompt(plan: dict, instruction: str) -> str:
    file_path = production_file(plan.get("id", "untitled"))
    return f"""请修改起号视频制作策划稿。

**文件路径**：`{file_path}`

**修改要求**：
{instruction.strip() or "（用户未填写具体要求，请整体优化口播节奏、分镜清晰度和录屏操作说明）"}

**当前策划 JSON**：
```json
{json.dumps(plan, ensure_ascii=False, indent=2)}
```

**请你**：
1. 直接编辑上述 JSON 文件（保持 `shots[].index` 连续）
2. 同步更新 `full_script`（完整口播稿）
3. 每镜保留：time_range、duration_seconds、visual、voiceover、action
4. 口播总时长尽量贴合 `total_duration`
5. 改完后告知用户刷新网页查看

不要调用付费视觉 API；只改文本策划。"""


def production_summary_list() -> list[dict]:
    return list_productions()


def production_payload(plan_id: str) -> dict:
    plan = load_production(plan_id)
    plan["file_path"] = str(production_file(plan_id).relative_to(ROOT))
    plan["audio"] = load_production_audio_manifest(plan_id)
    return plan


def load_production_audio_manifest(plan_id: str) -> dict:
    manifest_path = production_audio_dir(plan_id) / "manifest.json"
    if not manifest_path.exists():
        return {"items": [], "generated_at": ""}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {"items": [], "generated_at": ""}


def run_production_tts(
    job_id: str,
    plan_id: str,
    *,
    shot_indices: list[int] | None = None,
    include_full_script: bool = True,
    speaker: str | None = None,
) -> None:
    try:
        if not tts_configured():
            raise ValueError("未配置火山 TTS API Key，请先在设置页填写")

        plan = load_production(plan_id)
        api_key, resource_id, default_speaker = get_resolved_credentials()
        use_speaker = (speaker or "").strip() or default_speaker
        audio_dir = production_audio_dir(plan_id)
        manifest_path = audio_dir / "manifest.json"
        existing = load_production_audio_manifest(plan_id)
        items_by_key = {item.get("key"): item for item in existing.get("items", []) if item.get("key")}

        targets: list[tuple[str, str, str]] = []
        shots = plan.get("shots") or []
        wanted = set(shot_indices) if shot_indices else None

        for shot in shots:
            idx = int(shot.get("index") or 0)
            if wanted is not None and idx not in wanted:
                continue
            text = str(shot.get("voiceover") or "").strip()
            if not text:
                continue
            key = f"shot-{idx:02d}"
            filename = f"镜{idx:02d}.mp3"
            targets.append((key, filename, text))

        if include_full_script:
            full = str(plan.get("full_script") or "").strip()
            if full:
                targets.append(("full_script", "完整口播.mp3", full))

        if not targets:
            raise ValueError("没有可合成的口播（各镜 voiceover 与 full_script 均为空）")

        set_job(
            job_id,
            status="running",
            step="tts",
            message=f"正在合成 0/{len(targets)}…",
            progress=5,
            plan_id=plan_id,
            total=len(targets),
            done=0,
        )

        for i, (key, filename, text) in enumerate(targets, start=1):
            set_job(
                job_id,
                message=f"正在合成 {i}/{len(targets)}：{filename}",
                progress=int(5 + (i - 1) / len(targets) * 90),
                done=i - 1,
            )
            audio_bytes, used_speaker = synthesize_speech(
                text,
                api_key=api_key,
                speaker=use_speaker,
                resource_id=resource_id,
            )
            out_path = audio_dir / filename
            out_path.write_bytes(audio_bytes)
            items_by_key[key] = {
                "key": key,
                "filename": filename,
                "text": text,
                "speaker": used_speaker,
                "url": f"/api/productions/{sanitize_plan_id(plan_id)}/audio/{filename}",
                "bytes": len(audio_bytes),
            }

        manifest = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "speaker": use_speaker,
            "items": sorted(items_by_key.values(), key=lambda x: x.get("key", "")),
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        set_job(
            job_id,
            status="done",
            step="done",
            message=f"配音完成，共 {len(targets)} 个文件",
            progress=100,
            plan_id=plan_id,
            manifest=manifest,
            done=len(targets),
        )
    except Exception as exc:
        set_job(job_id, status="error", message=str(exc), progress=100, plan_id=plan_id)


def _start_pipeline_job(share_text: str, **kwargs) -> str:
    job_id = uuid.uuid4().hex[:12]
    set_job(job_id, status="queued", step="queued", message="排队中…", progress=0, created_at=time.time())
    threading.Thread(
        target=run_pipeline,
        args=(job_id, share_text),
        kwargs=kwargs,
        daemon=True,
    ).start()
    return job_id


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = _query_dict(parsed)

        if path in {"/", "/index.html"}:
            return self._serve_file(WEB_DIR / "index.html", "text/html; charset=utf-8")

        if path.startswith("/assets/"):
            target = (WEB_DIR / path.lstrip("/")).resolve()
            if not str(target).startswith(str(WEB_DIR.resolve())):
                return self._not_found()
            if target.is_file():
                ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                return self._serve_file(target, ctype, cache=False)
            return self._not_found()

        if path == "/api/projects":
            items = [project_summary(p) for p in list_projects()]
            return json_response(self, {"projects": items})

        if path == "/api/productions":
            return json_response(self, {"plans": production_summary_list()})

        if path == "/api/settings/tts":
            return json_response(self, public_tts_settings())

        if path == "/api/settings/system-prompt":
            try:
                return json_response(self, load_system_prompt())
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 500)

        if path.startswith("/api/productions/"):
            parts = [p for p in path.split("/") if p]
            # /api/productions/{id}/audio/{file}
            if len(parts) >= 5 and parts[3] == "audio":
                plan_id = parts[2]
                filename = unquote(parts[4])
                if ".." in filename or "/" in filename or "\\" in filename:
                    return self._not_found()
                target = (production_audio_dir(plan_id) / filename).resolve()
                audio_root = production_audio_dir(plan_id).resolve()
                if not str(target).startswith(str(audio_root)) or not target.is_file():
                    return self._not_found()
                return self._serve_file(target, "audio/mpeg", cache=False)

            if len(parts) >= 3:
                plan_id = parts[2]
                try:
                    return json_response(self, production_payload(plan_id))
                except Exception as exc:
                    return json_response(self, {"error": str(exc)}, 404)

        if path.startswith("/api/projects/"):
            parts = [p for p in path.split("/") if p]
            # /api/projects/{id} or /api/projects/{id}/report
            if len(parts) >= 3:
                pid = parts[2]
                try:
                    project = resolve_project(pid)
                except Exception as exc:
                    return json_response(self, {"error": str(exc)}, 404)
                if len(parts) >= 4 and parts[3] == "report":
                    report_md = analysis_dir(project) / "report.md"
                    if report_md.is_file():
                        if (query or {}).get("view") == "html":
                            html = md_report_to_html(report_md.read_text(encoding="utf-8"))
                            return json_response(
                                self,
                                {
                                    "id": project.name,
                                    "title": project_payload_title(project),
                                    "html": html,
                                    "kb_path": meta_report_kb_path(project),
                                    "raw_url": f"/api/projects/{project.name}/report",
                                },
                            )
                        return self._serve_file(report_md, "text/markdown; charset=utf-8")
                    return self._not_found()
                return json_response(self, project_payload(project))

        if path.startswith("/api/jobs/"):
            job_id = path.split("/")[-1]
            with jobs_lock:
                job = jobs.get(job_id)
            if not job:
                return json_response(self, {"error": "job not found"}, 404)
            return json_response(self, job)

        if path.startswith("/media/"):
            parts = path.split("/")
            if len(parts) < 4:
                return self._not_found()
            pid, *rel_parts = parts[2:]
            try:
                project = resolve_project(pid)
            except Exception:
                return self._not_found()
            rel = "/".join(rel_parts)
            if rel == "video.mp4":
                target = video_file(project)
            else:
                target = (analysis_dir(project) / rel).resolve()
            if not str(target).startswith(str(project.resolve())):
                return self._not_found()
            if target.is_file():
                ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                if rel == "video.mp4":
                    return self._serve_file_range(target, ctype)
                return self._serve_file(target, ctype)
            return self._not_found()

        return self._not_found()

    def do_PATCH(self) -> None:
        return json_response(self, {"error": "not found"}, 404)

    def do_DELETE(self) -> None:
        return json_response(self, {"error": "not found"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/analyze":
            data = read_json(self)
            share_text = (data.get("share_text") or "").strip()
            if not share_text:
                return json_response(self, {"error": "请粘贴分享文案或链接"}, 400)

            analysis_mode = (data.get("analysis_mode") or "prompt_reverse").strip()
            if analysis_mode not in {"content", "prompt_reverse"}:
                analysis_mode = "prompt_reverse"

            keyframe_mode = (data.get("keyframe_mode") or "").strip()
            if keyframe_mode not in {"transcript", "custom", "scene", "interval"}:
                keyframe_mode = "interval" if analysis_mode == "prompt_reverse" else "transcript"
            frame_count = int(data.get("frame_count") or 30)
            interval_seconds = float(data.get("interval_seconds") or 3.5)
            vision_prep = bool(data.get("vision_prep"))

            job_id = uuid.uuid4().hex[:12]
            set_job(
                job_id,
                status="queued",
                step="queued",
                message="排队中…",
                progress=0,
                created_at=time.time(),
            )
            threading.Thread(
                target=run_pipeline,
                args=(job_id, share_text),
                kwargs={
                    "keyframe_mode": keyframe_mode,
                    "frame_count": frame_count,
                    "interval_seconds": interval_seconds,
                    "vision_prep": vision_prep,
                    "analysis_mode": analysis_mode,
                },
                daemon=True,
            ).start()
            return json_response(self, {"job_id": job_id})

        if path.startswith("/api/projects/") and path.endswith("/reanalyze"):
            pid = path.split("/")[-2]
            try:
                project = resolve_project(pid)
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 404)

            data = read_json(self)
            force = bool(data.get("force"))
            analysis_mode = (data.get("analysis_mode") or "prompt_reverse").strip()
            if analysis_mode not in {"content", "prompt_reverse"}:
                analysis_mode = "prompt_reverse"
            keyframe_mode = (data.get("keyframe_mode") or "").strip()
            if keyframe_mode not in {"transcript", "custom", "scene", "interval"}:
                keyframe_mode = "interval" if analysis_mode == "prompt_reverse" else "transcript"
            frame_count = int(data.get("frame_count") or 30)
            interval_seconds = float(data.get("interval_seconds") or 3.5)
            vision_prep = bool(data.get("vision_prep"))

            job_id = uuid.uuid4().hex[:12]
            set_job(
                job_id,
                status="queued",
                step="queued",
                message="排队中…",
                progress=0,
                project_id=project.name,
                created_at=time.time(),
            )
            threading.Thread(
                target=run_reanalyze,
                args=(job_id, project.name),
                kwargs={
                    "force": force,
                    "keyframe_mode": keyframe_mode,
                    "frame_count": frame_count,
                    "interval_seconds": interval_seconds,
                    "vision_prep": vision_prep,
                    "analysis_mode": analysis_mode,
                },
                daemon=True,
            ).start()
            return json_response(self, {"job_id": job_id})

        if path.startswith("/api/projects/") and path.endswith("/vision-prep"):
            pid = path.split("/")[-2]
            try:
                project = resolve_project(pid)
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 404)
            job_id = uuid.uuid4().hex[:12]
            set_job(
                job_id,
                status="queued",
                step="queued",
                message="排队中…",
                progress=0,
                project_id=project.name,
                created_at=time.time(),
            )
            threading.Thread(
                target=run_vision_prep,
                args=(job_id, project.name),
                daemon=True,
            ).start()
            return json_response(self, {"job_id": job_id})

        if path.startswith("/api/projects/") and path.endswith("/vision-merge"):
            pid = path.split("/")[-2]
            try:
                project = resolve_project(pid)
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 404)
            try:
                merge_descriptions(project)
                return json_response(self, project_payload(project))
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 400)

        if path.startswith("/api/projects/") and path.endswith("/refresh-meta"):
            pid = path.split("/")[-2]
            try:
                project = resolve_project(pid)
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 404)
            try:
                refresh_meta(project)
                report = {}
                report_path = analysis_dir(project) / "report.json"
                if report_path.exists():
                    report = json.loads(report_path.read_text(encoding="utf-8"))
                return json_response(self, {"meta": project_meta_display(project, report)})
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 500)

        if path == "/api/productions":
            data = read_json(self)
            title = (data.get("title") or "新视频策划").strip()
            plan = new_production_template(title=title)
            if data.get("template") == "evoflow-web-coding":
                try:
                    plan = load_production("evoflow-web-coding")
                    plan = {**plan, "id": sanitize_plan_id(title), "title": title}
                except Exception:
                    pass
            path_saved = save_production(plan)
            plan["file_path"] = str(path_saved.relative_to(ROOT))
            return json_response(self, plan, 201)

        if path == "/api/settings/tts":
            data = read_json(self)
            try:
                return json_response(self, save_tts_settings(data))
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 400)

        if path == "/api/settings/system-prompt":
            data = read_json(self)
            try:
                return json_response(self, save_system_prompt(str(data.get("content") or "")))
            except ValueError as exc:
                return json_response(self, {"error": str(exc)}, 400)
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 500)

        if path == "/api/settings/system-prompt/reset":
            try:
                return json_response(self, reset_system_prompt())
            except FileNotFoundError as exc:
                return json_response(self, {"error": str(exc)}, 404)
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 500)

        if path == "/api/settings/tts/preview":
            data = read_json(self)
            text = str(data.get("text") or "你好，这是起号配音试听。").strip()
            if not tts_configured():
                return json_response(self, {"error": "未配置火山 TTS API Key"}, 400)
            try:
                api_key, resource_id, default_speaker = get_resolved_credentials()
                speaker = str(data.get("speaker") or default_speaker).strip()
                audio_bytes, used_speaker = synthesize_speech(
                    text,
                    api_key=api_key,
                    speaker=speaker,
                    resource_id=resource_id,
                    preview=True,
                )
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(audio_bytes)))
                self.send_header("X-Tts-Speaker", used_speaker)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Expose-Headers", "X-Tts-Speaker")
                self.end_headers()
                self.wfile.write(audio_bytes)
                return
            except ValueError as exc:
                return json_response(self, {"error": str(exc)}, 400)
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 502)

        if path.startswith("/api/productions/") and path.endswith("/tts"):
            plan_id = path.split("/")[-2]
            try:
                load_production(plan_id)
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 404)

            data = read_json(self)
            shot_indices = data.get("shot_indices")
            if shot_indices is not None and not isinstance(shot_indices, list):
                shot_indices = None
            include_full_script = bool(data.get("include_full_script", True))
            speaker = str(data.get("speaker") or "").strip() or None

            job_id = uuid.uuid4().hex[:12]
            set_job(
                job_id,
                status="queued",
                step="queued",
                message="排队中…",
                progress=0,
                plan_id=plan_id,
                created_at=time.time(),
            )
            threading.Thread(
                target=run_production_tts,
                args=(job_id, plan_id),
                kwargs={
                    "shot_indices": shot_indices,
                    "include_full_script": include_full_script,
                    "speaker": speaker,
                },
                daemon=True,
            ).start()
            return json_response(self, {"job_id": job_id})

        if path.startswith("/api/productions/") and path.endswith("/save"):
            plan_id = path.split("/")[-2]
            data = read_json(self)
            data["id"] = sanitize_plan_id(data.get("id") or plan_id)
            try:
                path_saved = save_production(data)
                data["file_path"] = str(path_saved.relative_to(ROOT))
                return json_response(self, data)
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 400)

        if path.startswith("/api/productions/") and path.endswith("/ai-prompt"):
            plan_id = path.split("/")[-2]
            data = read_json(self)
            instruction = (data.get("instruction") or "").strip()
            inline_plan = data.get("plan")
            try:
                plan = inline_plan if isinstance(inline_plan, dict) else load_production(plan_id)
                prompt = build_ai_revise_prompt(plan, instruction)
                return json_response(
                    self,
                    {
                        "prompt": prompt,
                        "file_path": str(production_file(plan.get("id", plan_id)).relative_to(ROOT)),
                    },
                )
            except Exception as exc:
                return json_response(self, {"error": str(exc)}, 400)

        return json_response(self, {"error": "not found"}, 404)

    def _serve_file(self, path: Path, content_type: str, *, cache: bool = True) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        if not cache:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _serve_file_range(self, path: Path, content_type: str) -> None:
        """Serve media with HTTP Range support so <video> can seek."""
        size = path.stat().st_size
        range_header = self.headers.get("Range")

        if range_header and range_header.startswith("bytes="):
            spec = range_header[6:].strip()
            if "-" in spec:
                start_s, end_s = spec.split("-", 1)
                try:
                    start = int(start_s) if start_s else 0
                    end = int(end_s) if end_s else size - 1
                except ValueError:
                    start, end = 0, size - 1
                end = min(end, size - 1)
                if start >= size or start > end:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    return
                with path.open("rb") as fh:
                    fh.seek(start)
                    data = fh.read(end - start + 1)
                self.send_response(206)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
                return

        with path.open("rb") as fh:
            data = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _not_found(self) -> None:
        self.send_response(404)
        self.end_headers()


def main() -> int:
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"视频分析面板: {url}")
    print("Ctrl+C 停止")
    try:
        if sys.platform == "win32":
            subprocess.Popen(["cmd", "/c", "start", url], shell=False)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
