"""Workbench REST API — local JSON storage under 起号/workbench/data/."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from paths import (
    ROOT,
    analysis_dir,
    list_projects,
    load_meta,
    load_production,
    production_file,
    productions_dir,
    resolve_project,
)

WORKBENCH_DIR = ROOT / "workbench"
DATA_DIR = WORKBENCH_DIR / "data"
DRAFTS_DIR = DATA_DIR / "drafts"
MOCK_DIR = DATA_DIR / "mock"
NOTES_MEETINGS_DIR = DATA_DIR / "notes" / "meetings"
REPORTS_DIR = DATA_DIR / "reports"
UPLOADS_DIR = DATA_DIR / "uploads"
CALENDAR_DIR = DATA_DIR / "calendar"
WEBHOOK_SECRET = os.getenv("WORKBENCH_WEBHOOK_SECRET", "")

JobStarter = Callable[[str, dict[str, Any]], str]
SkillRunner = Callable[[str, dict[str, Any]], dict[str, Any]]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _read_items(name: str) -> list[dict[str, Any]]:
    path = DATA_DIR / name
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("items") or [])
    except Exception:
        return []


def _write_items(name: str, items: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / name
    path.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def viral_videos_list(query: dict[str, str] | None = None) -> list[dict[str, Any]]:
    q = query or {}
    out: list[dict[str, Any]] = []
    for project in list_projects():
        meta = load_meta(project)
        analysis = analysis_dir(project)
        report_path = analysis / "report.json"
        if not report_path.exists():
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        scenes = report.get("scenes") or []
        cover_url = None
        if scenes:
            rel = str(scenes[0].get("frame_path", "")).replace("\\", "/")
            if rel:
                cover_url = f"/media/{project.name}/{rel}"
        chapters = report.get("aligned") or report.get("chapters") or []
        item = {
            "aweme_id": project.name,
            "title": report.get("title") or meta.get("title", ""),
            "author": meta.get("author_nickname", ""),
            "duration_label": report.get("duration_label", ""),
            "duration_seconds": report.get("duration_seconds", 0),
            "script_chars": report.get("script", {}).get("total_chars", 0),
            "chapter_count": len(chapters),
            "scene_count": len(scenes),
            "hashtags": report.get("hashtags") or meta.get("hashtags") or [],
            "cover_url": cover_url,
            "analyzed_at": meta.get("last_analysis_at") or meta.get("updated_at", ""),
            "report_url": f"/api/projects/{project.name}/report",
            "detail_url": f"/#/analyze/{project.name}/overview",
        }
        out.append(item)

    search = (q.get("q") or "").strip().lower()
    if search:
        out = [v for v in out if search in v["title"].lower() or search in v["author"].lower()]

    tags = [t.strip() for t in (q.get("tags") or "").split(",") if t.strip()]
    if tags:
        out = [v for v in out if any(t in v.get("hashtags") or [] for t in tags)]

    min_chars = int(q["min_chars"]) if q.get("min_chars", "").isdigit() else None
    max_chars = int(q["max_chars"]) if q.get("max_chars", "").isdigit() else None
    if min_chars is not None:
        out = [v for v in out if v["script_chars"] >= min_chars]
    if max_chars is not None:
        out = [v for v in out if v["script_chars"] <= max_chars]

    author = (q.get("author") or "").strip()
    if author:
        out = [v for v in out if v["author"] == author]

    sort_key = q.get("sort") or "analyzed_at"
    reverse = (q.get("order") or "desc").lower() != "asc"
    if sort_key in {"script_chars", "chapter_count", "scene_count", "duration_seconds", "analyzed_at"}:
        out.sort(key=lambda x: x.get(sort_key) or 0, reverse=reverse)
    else:
        out.sort(key=lambda x: x.get("analyzed_at") or "", reverse=True)
    return out


def shell_counts() -> dict[str, int]:
    drafts = list(DRAFTS_DIR.glob("*.md")) if DRAFTS_DIR.exists() else []
    return {
        "tasks": len(_read_items("tasks.json")),
        "skills": len(_read_items("skills.json")),
        "topicCollections": len(_read_items("topic-collections.json")),
        "viralVideos": len(viral_videos_list()),
        "library": len(_read_items("library.json")),
        "writing": len(drafts),
        "experiences": len(_read_items("experiences.json")),
    }


def creators_list() -> list[dict[str, Any]]:
    by_author: dict[str, dict[str, Any]] = {}
    for v in viral_videos_list():
        author = v.get("author") or "未知"
        if author not in by_author:
            by_author[author] = {"author": author, "video_count": 0, "video_ids": []}
        by_author[author]["video_count"] += 1
        by_author[author]["video_ids"].append(v["aweme_id"])
    return sorted(by_author.values(), key=lambda x: -x["video_count"])


def list_drafts() -> list[dict[str, Any]]:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for md in sorted(DRAFTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        meta_path = DRAFTS_DIR / f"{md.stem}.meta.json"
        meta = _read_json(meta_path) if meta_path.exists() else {}
        items.append(
            {
                "id": md.stem,
                "title": meta.get("title") or md.stem,
                "updated_at": meta.get("updated_at") or _now(),
                "preview": md.read_text(encoding="utf-8")[:120],
            }
        )
    return items


def get_draft(draft_id: str) -> dict[str, Any] | None:
    path = DRAFTS_DIR / f"{draft_id}.md"
    if not path.exists():
        return None
    meta = _read_json(DRAFTS_DIR / f"{draft_id}.meta.json")
    return {
        "id": draft_id,
        "title": meta.get("title") or draft_id,
        "content": path.read_text(encoding="utf-8"),
        "updated_at": meta.get("updated_at") or _now(),
    }


def save_draft(draft_id: str | None, title: str, content: str) -> dict[str, Any]:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    did = draft_id or _uid("draft-")
    (DRAFTS_DIR / f"{did}.md").write_text(content, encoding="utf-8")
    meta = {"title": title, "updated_at": _now()}
    (DRAFTS_DIR / f"{did}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"id": did, **meta, "content": content}


def automations_list() -> list[dict[str, Any]]:
    return _read_items("automations.json") or [
        {"id": "daily-fans", "name": "增长日报", "description": "全平台粉丝汇总"},
        {"id": "night-shift", "name": "夜班任务", "description": "读会议纪要沉淀知识库"},
        {"id": "weekly-report", "name": "周报月报", "description": "汇总任务与策划进度"},
    ]


def _evoflow_chat(prompt: str, *, skill_id: str | None = None, context: dict[str, Any] | None = None) -> tuple[str, bool, str]:
    from evoflow_client import try_chat_or_hint

    return try_chat_or_hint(prompt, skill_id=skill_id, context=context)


def evoflow_status() -> dict[str, Any]:
    from evoflow_client import load_evoflow_config

    cfg = load_evoflow_config()
    return {
        "enabled": bool(cfg.get("enabled")),
        "configured": bool(cfg.get("api_key")),
        "base_url": cfg.get("base_url"),
        "default_model": cfg.get("default_model"),
        "skill_models": cfg.get("skill_models") or {},
    }


def sync_status() -> dict[str, Any]:
    from workbench_jobs import sync_meta

    meta = sync_meta()
    return {
        "mode": "local",
        "cloud_sync": bool(meta.get("last_sync_at")),
        "data_dir": str(DATA_DIR),
        "revision": meta.get("revision", 0),
        "last_sync_at": meta.get("last_sync_at"),
        "message": "本地 JSON 模式" if not meta.get("last_sync_at") else "已同步",
    }


def list_inbox() -> list[dict[str, Any]]:
    from workbench_jobs import list_inbox as _inbox

    return _inbox(unread_only=True)


def mark_inbox_read(job_id: str) -> dict[str, Any]:
    from workbench_jobs import mark_inbox_read as _read

    row = _read(job_id)
    if not row:
        raise ValueError("inbox item not found")
    return row


def batch_dispatch(body: dict[str, Any], *, start_job: JobStarter | None = None) -> dict[str, Any]:
    task_ids = list(body.get("task_ids") or [])
    if not task_ids:
        raise ValueError("task_ids 不能为空")
    tasks = _read_items("tasks.json")
    selected = [t for t in tasks if t.get("id") in task_ids]
    if not selected:
        raise ValueError("未找到任务")
    prompt = "请批量处理以下任务，逐条给出执行建议：\n" + "\n".join(
        f"- {t.get('title')}: {t.get('note') or ''}" for t in selected
    )
    job_id = _uid("job-")
    if start_job:
        job_id = start_job(prompt, {"task_ids": task_ids, "batch": True})
    for t in tasks:
        if t.get("id") in task_ids:
            t["dispatch_job_id"] = job_id
            t["dispatch_result"] = "批量派 AI 执行中…"
            t["updated_at"] = _now()
    _write_items("tasks.json", tasks)
    return {"job_id": job_id, "count": len(selected)}


def add_collection_items(col_id: str, body: dict[str, Any]) -> dict[str, Any]:
    items = _read_items("topic-collections.json")
    for col in items:
        if col.get("id") != col_id:
            continue
        vids = list(col.get("video_ids") or [])
        pids = list(col.get("production_ids") or [])
        for vid in body.get("video_ids") or []:
            if vid not in vids:
                vids.append(vid)
        for pid in body.get("production_ids") or []:
            if pid not in pids:
                pids.append(pid)
        col["video_ids"] = vids
        col["production_ids"] = pids
        col["updated_at"] = _now()
        _write_items("topic-collections.json", items)
        return col
    raise ValueError("collection not found")


def webhook_dispatch(body: dict[str, Any], *, start_job: JobStarter | None = None) -> dict[str, Any]:
    secret = str(body.get("secret") or "")
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
        raise ValueError("webhook secret 无效")
    prompt = str(body.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("缺少 prompt")
    job_id = _uid("job-")
    if start_job:
        job_id = start_job(prompt, {"source": "webhook", "skill_id": body.get("skill_id")})
    return {"job_id": job_id}


def writing_ai_rewrite(body: dict[str, Any]) -> dict[str, Any]:
    text = str(body.get("text") or "").strip()
    if not text:
        raise ValueError("缺少 text")
    instruction = str(body.get("instruction") or "润色改写，保持原意")
    prompt = f"{instruction}：\n\n{text}"
    result, used, msg = _evoflow_chat(prompt)
    return {"text": result, "via_evoflow": used, "status_message": msg}


def apply_batch_dispatch_result(task_ids: list[str], job_id: str, result: str, *, used_evoflow: bool) -> None:
    tasks = _read_items("tasks.json")
    for t in tasks:
        if t.get("id") in task_ids:
            t["dispatch_job_id"] = job_id
            t["dispatch_result"] = result[:4000]
            t["dispatch_via"] = "evoflow" if used_evoflow else "local"
            t["updated_at"] = _now()
    _write_items("tasks.json", tasks)


def apply_dispatch_result(task_id: str | None, job_id: str, result: str, *, used_evoflow: bool) -> None:
    if not task_id:
        return
    tasks = _read_items("tasks.json")
    for t in tasks:
        if t.get("id") == task_id:
            t["dispatch_job_id"] = job_id
            t["dispatch_result"] = result[:4000]
            t["dispatch_via"] = "evoflow" if used_evoflow else "local"
            t["updated_at"] = _now()
    _write_items("tasks.json", tasks)


def run_automation(automation_id: str) -> dict[str, Any]:
    runs = _read_items("automation-runs.json")
    run = {
        "id": _uid("run-"),
        "automation_id": automation_id,
        "status": "done",
        "started_at": _now(),
        "finished_at": _now(),
        "summary": "",
    }
    if "fan" in automation_id or automation_id == "daily-fans" or automation_id == "auto-daily-fans":
        try:
            from fans_crawler import crawl_daily_fans

            report = crawl_daily_fans()
        except Exception as exc:
            report = _read_json(MOCK_DIR / "daily-fan-report.json")
            report["errors"] = [str(exc)]
        run["summary"] = f"总粉丝 {report.get('total_fans', 0) / 10000:.1f}w · 日增 {report.get('daily_delta', 0)}"
        run["output"] = report
    elif "night" in automation_id:
        processed: list[dict[str, Any]] = []
        try:
            from feishu_client import fetch_today_meeting_notes

            notes = fetch_today_meeting_notes()
            for n in notes:
                prompt = f"请把以下会议纪要提炼为 3–5 条可执行经验，并列出待办（中文）：\n\n{n['text'][:6000]}"
                summary, used, _ = _evoflow_chat(prompt)
                processed.append({"file": n["name"], "summary": summary[:800], "via_evoflow": used, "source": "feishu"})
                items = _read_items("experiences.json")
                items.insert(0, {
                    "id": _uid("exp-"),
                    "content": summary[:2000],
                    "type": "plus",
                    "category_tags": ["会议纪要", "夜班", "飞书"],
                    "topic_tags": [n["name"][:40]],
                    "level": "normal",
                    "created_at": _now(),
                })
                _write_items("experiences.json", items)
                tasks = _read_items("tasks.json")
                tasks.insert(0, {
                    "id": _uid("task-"),
                    "title": f"跟进：{n['name'][:30]}",
                    "note": summary[:500],
                    "status": "todo",
                    "column": "todo",
                    "subtasks": [],
                    "tags": ["夜班", "飞书"],
                    "created_at": _now(),
                    "updated_at": _now(),
                })
                _write_items("tasks.json", tasks)
        except Exception as exc:
            processed.append({"error": str(exc), "source": "feishu"})
        NOTES_MEETINGS_DIR.mkdir(parents=True, exist_ok=True)
        for md in sorted(NOTES_MEETINGS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
            text = md.read_text(encoding="utf-8")
            prompt = f"请把以下会议纪要提炼为 3–5 条可执行经验（中文）：\n\n{text[:6000]}"
            summary, used, _ = _evoflow_chat(prompt)
            processed.append({"file": md.name, "summary": summary[:800], "via_evoflow": used, "source": "local"})
        CALENDAR_DIR.mkdir(parents=True, exist_ok=True)
        ics = CALENDAR_DIR / f"night-{datetime.now().strftime('%Y%m%d')}.ics"
        ics.write_text("BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n", encoding="utf-8")
        run["summary"] = f"已处理 {len(processed)} 条会议纪要"
        run["output"] = {"processed": processed, "calendar": str(ics)}
    else:
        tasks = _read_items("tasks.json")
        done = sum(1 for t in tasks if t.get("status") == "done")
        prod_count = len(list(productions_dir().glob("*.json")))
        viral_count = len(viral_videos_list())
        prompt = (
            f"请写本周起号工作台周报：完成任务 {done} 项，策划 {prod_count} 个，拆解 {viral_count} 个。"
            "列出亮点与下周建议（Markdown）。"
        )
        text, used, _ = _evoflow_chat(prompt)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        week_path = REPORTS_DIR / f"weekly-{datetime.now().strftime('%Y%m%d')}.md"
        week_path.write_text(text if used else f"# 周报\n\n完成任务 {done} 项 · 策划 {prod_count} 个\n", encoding="utf-8")
        run["summary"] = text[:200] if used else f"本周完成任务 {done} 项 · 策划 {prod_count} 个"
        run["output"] = {"report": text, "path": str(week_path), "via_evoflow": used}
    runs.insert(0, run)
    _write_items("automation-runs.json", runs[:50])
    return run


def _skill_prompt(skill_id: str, skill: dict[str, Any], body: dict[str, Any]) -> str:
    name = skill.get("name") or skill_id
    parts = [f"运行 Skill「{name}」。"]
    if body.get("prompt"):
        parts.append(str(body["prompt"]))
    if body.get("url"):
        parts.append(f"链接：{body['url']}")
    if body.get("video_id") or body.get("aweme_id"):
        vid = body.get("video_id") or body.get("aweme_id")
        parts.append(f"视频 ID：{vid}")
        project = resolve_project(str(vid))
        report_path = analysis_dir(project) / "report.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            parts.append(f"已有拆解：{report.get('title', '')} · {len(report.get('scenes') or [])} 镜")
    if body.get("production_id"):
        pid = str(body["production_id"])
        pf = production_file(pid)
        if pf.exists():
            prod = load_production(pid)
            parts.append(f"策划稿：{prod.get('title', pid)} · {len(prod.get('shots') or [])} 镜")
    return "\n".join(parts)


def run_skill(
    skill_id: str,
    body: dict[str, Any],
    *,
    run_skill_fn: SkillRunner | None = None,
) -> dict[str, Any]:
    skills = _read_items("skills.json")
    skill = next((s for s in skills if s.get("id") == skill_id), None)
    if not skill:
        raise ValueError(f"Skill not found: {skill_id}")

    run_id = _uid("sr-")
    runs = _read_items("skill-runs.json")
    run = {
        "id": run_id,
        "skill_id": skill_id,
        "status": "running",
        "input": body,
        "started_at": _now(),
    }
    runs.insert(0, run)
    _write_items("skill-runs.json", runs[:100])

    try:
        if run_skill_fn:
            result = run_skill_fn(skill_id, body)
            output = json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
            run["output"] = output
            run["job_id"] = result.get("job_id") if isinstance(result, dict) else None
            run["status"] = "done" if not result.get("job_id") else "running"
        else:
            prompt = _skill_prompt(skill_id, skill, body)
            output, used_evoflow, status_msg = _evoflow_chat(prompt, skill_id=skill_id, context=body)
            run["output"] = output
            run["via_evoflow"] = used_evoflow
            run["status_message"] = status_msg
            run["status"] = "done"
    except Exception as exc:
        run["status"] = "error"
        run["output"] = str(exc)

    run["finished_at"] = _now() if run["status"] in {"done", "error"} else None
    runs = _read_items("skill-runs.json")
    for i, r in enumerate(runs):
        if r.get("id") == run_id:
            runs[i] = run
            break
    _write_items("skill-runs.json", runs[:100])

    for s in skills:
        if s.get("id") == skill_id:
            s["run_count"] = int(s.get("run_count") or 0) + 1
            s["last_run_at"] = _now()
    _write_items("skills.json", skills)
    return run


def push_skill_to_feishu(skill_id: str, body: dict[str, Any]) -> dict[str, Any]:
    content = str(body.get("content") or body.get("output") or "").strip()
    if not content:
        runs = _read_items("skill-runs.json")
        latest = next((r for r in runs if r.get("skill_id") == skill_id), None)
        content = str(latest.get("output") or "") if latest else ""
    if not content:
        raise ValueError("无内容可推送")
    from feishu_client import push_doc_content

    title = str(body.get("title") or f"Skill {skill_id} 输出")
    return push_doc_content(title, content)


def dispatch_task(
    task_id: str | None,
    body: dict[str, Any],
    *,
    start_job: JobStarter | None = None,
) -> dict[str, Any]:
    prompt = str(body.get("prompt") or "").strip()
    skill_id = str(body.get("skill_id") or "").strip()
    if not prompt and task_id:
        tasks = _read_items("tasks.json")
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if task:
            prompt = f"请处理任务：{task.get('title')}\n{task.get('note') or ''}"

    if not prompt:
        raise ValueError("缺少 prompt 或 task_id")

    job_id = _uid("job-")
    if start_job:
        job_id = start_job(prompt, {"task_id": task_id, "skill_id": skill_id})

    if task_id:
        tasks = _read_items("tasks.json")
        for t in tasks:
            if t.get("id") == task_id:
                t["dispatch_job_id"] = job_id
                t["dispatch_result"] = "EvoFlow 执行中…"
                t["updated_at"] = _now()
        _write_items("tasks.json", tasks)

    return {"job_id": job_id, "message": "已派 AI"}


def handle_get(path: str, query: dict[str, str] | None = None) -> tuple[dict[str, Any], int] | None:
    parts = [p for p in path.split("/") if p]
    q = query or {}

    if path == "/api/workbench/shell-counts":
        counts = shell_counts()
        counts["inbox"] = len(list_inbox())
        return {"counts": counts}, 200

    if path == "/api/workbench/viral-videos":
        return {"items": viral_videos_list(q)}, 200

    if len(parts) >= 4 and parts[2] == "viral-videos" and len(parts) == 4:
        from skill_runners import viral_video_detail

        detail = viral_video_detail(parts[3])
        if detail:
            return detail, 200
        return {"error": "not found"}, 404

    if path == "/api/workbench/creators":
        return {"items": creators_list()}, 200

    if path == "/api/workbench/tasks":
        return {"items": _read_items("tasks.json")}, 200

    if path == "/api/workbench/skills":
        return {"items": _read_items("skills.json")}, 200

    if path == "/api/workbench/skill-runs":
        return {"items": _read_items("skill-runs.json")}, 200

    if path == "/api/workbench/experiences":
        return {"items": _read_items("experiences.json")}, 200

    if path == "/api/workbench/topic-collections":
        return {"items": _read_items("topic-collections.json")}, 200

    if path == "/api/workbench/library":
        return {"items": _read_items("library.json")}, 200

    if path == "/api/workbench/drafts":
        return {"items": list_drafts()}, 200

    if len(parts) >= 4 and parts[0] == "api" and parts[1] == "workbench" and parts[2] == "drafts":
        draft = get_draft(parts[3])
        if draft:
            return draft, 200
        return {"error": "not found"}, 404

    if path == "/api/workbench/automations":
        return {"items": automations_list()}, 200

    if path == "/api/workbench/automation-runs":
        return {"items": _read_items("automation-runs.json")}, 200

    if path == "/api/workbench/reports/daily-fans/latest":
        try:
            from fans_crawler import latest_daily_fans

            report = latest_daily_fans()
        except Exception:
            report = None
        if not report:
            report = _read_json(MOCK_DIR / "daily-fan-report.json")
        if not report:
            return {"error": "no report"}, 404
        return report, 200

    if path == "/api/workbench/inbox":
        return {"items": list_inbox()}, 200

    if path == "/api/workbench/evoflow/status":
        return evoflow_status(), 200

    if path == "/api/workbench/sync/status":
        return sync_status(), 200

    if len(parts) >= 4 and parts[2] == "topic-collections" and len(parts) == 4:
        items = _read_items("topic-collections.json")
        col = next((c for c in items if c.get("id") == parts[3]), None)
        if col:
            return col, 200
        return {"error": "not found"}, 404

    if path == "/api/workbench/hub":
        counts = shell_counts()
        counts["inbox"] = len(list_inbox())
        productions = []
        for p in sorted(productions_dir().glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                productions.append(
                    {"id": data.get("id"), "title": data.get("title"), "shots": len(data.get("shots") or [])}
                )
            except Exception:
                pass
        return {"counts": counts, "productions": productions, "viral_preview": viral_videos_list()[:3], "inbox_count": counts.get("inbox", 0)}, 200

    return None


def handle_post(
    path: str,
    body: dict[str, Any],
    *,
    start_job: JobStarter | None = None,
    run_skill_fn: SkillRunner | None = None,
) -> tuple[dict[str, Any], int]:
    if path == "/api/workbench/tasks":
        items = _read_items("tasks.json")
        task = {
            "id": _uid("task-"),
            "title": str(body.get("title") or "新任务").strip(),
            "note": str(body.get("note") or ""),
            "status": "todo",
            "column": "todo",
            "subtasks": body.get("subtasks") or [],
            "tags": body.get("tags") or [],
            "skill_id": body.get("skill_id"),
            "created_at": _now(),
            "updated_at": _now(),
        }
        items.append(task)
        _write_items("tasks.json", items)
        return task, 201

    if path == "/api/workbench/experiences":
        items = _read_items("experiences.json")
        exp = {
            "id": _uid("exp-"),
            "content": str(body.get("content") or "").strip(),
            "type": body.get("type") or "neutral",
            "category_tags": body.get("category_tags") or [],
            "topic_tags": body.get("topic_tags") or [],
            "level": body.get("level") or "normal",
            "created_at": _now(),
        }
        items.append(exp)
        _write_items("experiences.json", items)
        return exp, 201

    if path == "/api/workbench/topic-collections":
        items = _read_items("topic-collections.json")
        col = {
            "id": _uid("tc-"),
            "title": str(body.get("title") or "新合集").strip(),
            "description": str(body.get("description") or ""),
            "video_ids": body.get("video_ids") or [],
            "production_ids": body.get("production_ids") or [],
            "tags": body.get("tags") or [],
            "created_at": _now(),
            "updated_at": _now(),
        }
        items.append(col)
        _write_items("topic-collections.json", items)
        return col, 201

    if path == "/api/workbench/library":
        items = _read_items("library.json")
        book = {
            "id": _uid("book-"),
            "title": str(body.get("title") or "").strip(),
            "author": str(body.get("author") or ""),
            "summary": str(body.get("summary") or ""),
            "domain_tags": body.get("domain_tags") or [],
            "topic_tags": body.get("topic_tags") or [],
            "status": body.get("status") or "want",
            "added_at": _now(),
        }
        items.append(book)
        _write_items("library.json", items)
        return book, 201

    if path == "/api/workbench/drafts":
        draft = save_draft(None, str(body.get("title") or "未命名"), str(body.get("content") or ""))
        return draft, 201

    if path == "/api/workbench/dispatch":
        try:
            return dispatch_task(body.get("task_id"), body, start_job=start_job), 200
        except ValueError as exc:
            return {"error": str(exc)}, 400

    if path == "/api/workbench/tasks/batch-dispatch":
        try:
            return batch_dispatch(body, start_job=start_job), 200
        except ValueError as exc:
            return {"error": str(exc)}, 400

    if path == "/api/workbench/webhook/dispatch":
        try:
            return webhook_dispatch(body, start_job=start_job), 200
        except ValueError as exc:
            return {"error": str(exc)}, 400

    if path == "/api/workbench/sync/push":
        from workbench_jobs import sync_push

        return sync_push(), 200

    if path == "/api/workbench/sync/pull":
        from workbench_jobs import sync_pull

        rev = int(body.get("revision") or 0)
        files = body.get("files") or {}
        return sync_pull(rev, files), 200

    if path == "/api/workbench/writing/ai-rewrite":
        try:
            return writing_ai_rewrite(body), 200
        except ValueError as exc:
            return {"error": str(exc)}, 400

    parts = [p for p in path.split("/") if p]
    if len(parts) >= 5 and parts[2] == "tasks" and parts[4] == "dispatch":
        try:
            return dispatch_task(parts[3], body, start_job=start_job), 200
        except ValueError as exc:
            return {"error": str(exc)}, 400

    if len(parts) >= 5 and parts[2] == "skills" and parts[4] == "run":
        try:
            return run_skill(parts[3], body, run_skill_fn=run_skill_fn), 200
        except ValueError as exc:
            return {"error": str(exc)}, 400

    if len(parts) >= 5 and parts[2] == "skills" and parts[4] == "push-feishu":
        try:
            return push_skill_to_feishu(parts[3], body), 200
        except (ValueError, RuntimeError) as exc:
            return {"error": str(exc)}, 400

    if len(parts) >= 6 and parts[2] == "topic-collections" and parts[4] == "items":
        try:
            return add_collection_items(parts[3], body), 200
        except ValueError as exc:
            return {"error": str(exc)}, 400

    if len(parts) >= 5 and parts[2] == "inbox" and parts[4] == "read":
        try:
            return mark_inbox_read(parts[3]), 200
        except ValueError as exc:
            return {"error": str(exc)}, 404

    if len(parts) >= 5 and parts[2] == "automations" and parts[4] == "run":
        return run_automation(parts[3]), 200

    return {"error": "not found"}, 404


def handle_patch(path: str, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    parts = [p for p in path.split("/") if p]

    def _patch_items(filename: str, item_id: str) -> tuple[dict[str, Any], int]:
        items = _read_items(filename)
        for i, item in enumerate(items):
            if item.get("id") == item_id:
                merged = {**item, **body, "updated_at": _now()}
                items[i] = merged
                _write_items(filename, items)
                return merged, 200
        return {"error": "not found"}, 404

    if len(parts) >= 4 and parts[2] == "tasks":
        return _patch_items("tasks.json", parts[3])

    if len(parts) >= 4 and parts[2] == "experiences":
        return _patch_items("experiences.json", parts[3])

    if len(parts) >= 4 and parts[2] == "topic-collections":
        return _patch_items("topic-collections.json", parts[3])

    if len(parts) >= 4 and parts[2] == "library":
        return _patch_items("library.json", parts[3])

    if len(parts) >= 4 and parts[2] == "drafts":
        draft_id = parts[3]
        existing = get_draft(draft_id)
        if not existing:
            return {"error": "not found"}, 404
        title = str(body.get("title") or existing.get("title") or draft_id)
        content = str(body.get("content") if "content" in body else existing.get("content") or "")
        return save_draft(draft_id, title, content), 200

    return {"error": "not found"}, 404


def handle_delete(path: str) -> tuple[dict[str, Any], int]:
    parts = [p for p in path.split("/") if p]

    def _delete_item(filename: str, item_id: str) -> tuple[dict[str, Any], int]:
        items = _read_items(filename)
        new_items = [x for x in items if x.get("id") != item_id]
        if len(new_items) == len(items):
            return {"error": "not found"}, 404
        _write_items(filename, new_items)
        return {"ok": True}, 200

    if len(parts) >= 4 and parts[2] == "tasks":
        return _delete_item("tasks.json", parts[3])
    if len(parts) >= 4 and parts[2] == "experiences":
        return _delete_item("experiences.json", parts[3])
    if len(parts) >= 4 and parts[2] == "topic-collections":
        return _delete_item("topic-collections.json", parts[3])
    if len(parts) >= 4 and parts[2] == "library":
        return _delete_item("library.json", parts[3])

    if len(parts) >= 4 and parts[2] == "drafts":
        draft_id = parts[3]
        md = DRAFTS_DIR / f"{draft_id}.md"
        meta = DRAFTS_DIR / f"{draft_id}.meta.json"
        if not md.exists():
            return {"error": "not found"}, 404
        md.unlink(missing_ok=True)
        meta.unlink(missing_ok=True)
        return {"ok": True}, 200

    return {"error": "not found"}, 404
