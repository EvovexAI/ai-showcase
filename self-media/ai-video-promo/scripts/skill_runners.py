"""Real skill execution for workbench."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Callable

from paths import (
    ROOT,
    analysis_dir,
    load_meta,
    new_production_template,
    resolve_project,
    save_production,
)

WORKBENCH_DIR = ROOT / "workbench"
DATA_DIR = WORKBENCH_DIR / "data"
SUGGESTIONS_FILE = DATA_DIR / "viral-suggestions.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _shots_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    chapters = report.get("aligned") or report.get("chapters") or []
    shots: list[dict[str, Any]] = []
    for i, ch in enumerate(chapters[:20]):
        shots.append(
            {
                "index": i + 1,
                "time_range": ch.get("time_range") or f"章{i + 1}",
                "duration_seconds": int(ch.get("duration_seconds") or 5),
                "visual": (ch.get("title") or ch.get("summary") or "")[:200],
                "voiceover": (ch.get("script_excerpt") or ch.get("text") or "")[:500],
                "action": "",
                "subtitle": ch.get("title") or "",
            }
        )
    if not shots:
        shots = new_production_template()["shots"]
    return shots


def run_douyin_analyze(body: dict[str, Any], *, start_pipeline: Callable[..., str]) -> dict[str, Any]:
    share = str(body.get("share_text") or body.get("url") or body.get("prompt") or "").strip()
    if not share:
        raise ValueError("douyin-analyze 需要 share_text 或 url")
    job_id = start_pipeline(
        share,
        keyframe_mode=str(body.get("keyframe_mode") or "transcript"),
        frame_count=int(body.get("frame_count") or 30),
        vision_prep=bool(body.get("vision_prep")),
    )
    return {"job_id": job_id, "message": "抖音拆解已启动", "type": "pipeline"}


def run_plan_from_report(body: dict[str, Any]) -> dict[str, Any]:
    vid = str(body.get("video_id") or body.get("aweme_id") or "").strip()
    if not vid:
        raise ValueError("plan-from-report 需要 video_id")
    project = resolve_project(vid)
    report_path = analysis_dir(project) / "report.json"
    if not report_path.exists():
        raise ValueError(f"未找到拆解报告: {vid}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    title = str(body.get("title") or report.get("title") or f"策划-{vid}")[:80]
    plan = new_production_template(title=title)
    plan["goal"] = f"对标视频 {vid}"
    plan["shots"] = _shots_from_report(report)
    script = (report.get("script") or {}).get("full_text") or ""
    plan["full_script"] = script[:8000]
    plan["notes"] = f"自动生成自 report.json · {vid}"
    path = save_production(plan)
    return {
        "production_id": plan["id"],
        "path": str(path),
        "shots": len(plan["shots"]),
        "message": f"已生成策划稿 {plan['id']}",
    }


def run_cover_gen(body: dict[str, Any]) -> dict[str, Any]:
    pid = str(body.get("production_id") or "").strip()
    if not pid:
        return {"message": "cover-gen：请提供 production_id；HyperFrames 渲染待 production 目录配置"}
    prod_dir = ROOT / "productions" / pid
    return {
        "message": f"封面生成占位：请在 {prod_dir} 运行 hyperframes snapshot",
        "production_id": pid,
        "hint": "npx hyperframes snapshot --url ...",
    }


def run_viral_collect(body: dict[str, Any], *, evoflow_chat: Callable[..., tuple[str, bool, str]]) -> dict[str, Any]:
    prompt = str(body.get("prompt") or "按平台与互动门槛搜集对标视频，输出 JSON 列表")
    text, used, msg = evoflow_chat(prompt, skill_id="viral-collect", context=body)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"id": uuid.uuid4().hex[:12], "created_at": _now(), "output": text, "via_evoflow": used}
    existing = []
    if SUGGESTIONS_FILE.exists():
        try:
            existing = json.loads(SUGGESTIONS_FILE.read_text(encoding="utf-8")).get("items") or []
        except Exception:
            existing = []
    existing.insert(0, entry)
    SUGGESTIONS_FILE.write_text(
        json.dumps({"items": existing[:50]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"suggestion_id": entry["id"], "output": text, "via_evoflow": used, "status_message": msg}


def execute_skill(
    skill_id: str,
    body: dict[str, Any],
    *,
    start_pipeline: Callable[..., str] | None = None,
    evoflow_chat: Callable[..., tuple[str, bool, str]] | None = None,
) -> dict[str, Any]:
    if skill_id == "douyin-analyze":
        if not start_pipeline:
            raise RuntimeError("start_pipeline not configured")
        return run_douyin_analyze(body, start_pipeline=start_pipeline)
    if skill_id == "plan-from-report":
        return run_plan_from_report(body)
    if skill_id == "cover-gen":
        return run_cover_gen(body)
    if skill_id == "viral-collect":
        if not evoflow_chat:
            raise RuntimeError("evoflow_chat not configured")
        return run_viral_collect(body, evoflow_chat=evoflow_chat)
    raise ValueError(f"Unknown skill: {skill_id}")


def viral_video_detail(aweme_id: str) -> dict[str, Any] | None:
    try:
        project = resolve_project(aweme_id)
    except Exception:
        return None
    meta = load_meta(project)
    report_path = analysis_dir(project) / "report.json"
    if not report_path.exists():
        return None
    report = json.loads(report_path.read_text(encoding="utf-8"))
    script = (report.get("script") or {}).get("full_text") or ""
    return {
        "aweme_id": aweme_id,
        "title": report.get("title") or meta.get("title", ""),
        "author": meta.get("author_nickname", ""),
        "duration_label": report.get("duration_label", ""),
        "script_chars": (report.get("script") or {}).get("total_chars", 0),
        "hashtags": report.get("hashtags") or [],
        "chapters": report.get("aligned") or report.get("chapters") or [],
        "script_preview": script[:800],
        "scene_count": len(report.get("scenes") or []),
    }
