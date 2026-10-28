#!/usr/bin/env python3
"""Paths and default local data for smart-coach."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MATERIALS = DATA / "materials"
SESSIONS = DATA / "sessions"
OUTLINE_PATH = DATA / "outline.json"
PROGRESS_PATH = DATA / "progress.json"
META_PATH = DATA / "meta.json"

DEFAULT_OUTLINE = {
    "course_title": "未命名课程",
    "updated_at": "",
    "nodes": [],
}

DEFAULT_PROGRESS = {
    "course_title": "未命名课程",
    "percent": 0,
    "next_focus": "",
    "last_session_at": "",
    "weak_points": [],
    "mastery": {},
    "notes": "",
}

DEFAULT_META = {
    "course_title": "未命名课程",
    "kb_hint": "陪练资料库",
    "materials_count": 0,
}


def ensure_data_dirs() -> None:
    MATERIALS.mkdir(parents=True, exist_ok=True)
    SESSIONS.mkdir(parents=True, exist_ok=True)
    if not OUTLINE_PATH.exists():
        OUTLINE_PATH.write_text(
            json.dumps(DEFAULT_OUTLINE, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if not PROGRESS_PATH.exists():
        PROGRESS_PATH.write_text(
            json.dumps(DEFAULT_PROGRESS, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if not META_PATH.exists():
        META_PATH.write_text(
            json.dumps(DEFAULT_META, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_materials() -> list[dict]:
    ensure_data_dirs()
    items = []
    for p in sorted(MATERIALS.iterdir()):
        if not p.is_file() or p.name.startswith(".") or p.name == ".gitkeep":
            continue
        items.append(
            {
                "name": p.name,
                "size": p.stat().st_size,
                "path": str(p.relative_to(ROOT)).replace("\\", "/"),
            }
        )
    return items


def list_sessions(limit: int = 5) -> list[dict]:
    ensure_data_dirs()
    files = sorted(SESSIONS.glob("*.md"), reverse=True)
    out = []
    for p in files[:limit]:
        text = p.read_text(encoding="utf-8", errors="replace")
        preview = text.strip().splitlines()
        summary = ""
        for line in preview:
            if line.strip() and not line.startswith("#"):
                summary = line.strip()
                break
        if not summary and preview:
            summary = preview[0].lstrip("# ").strip()
        out.append(
            {
                "name": p.name,
                "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                "summary": summary[:200],
                "mtime": p.stat().st_mtime,
            }
        )
    return out


def compute_percent(outline: dict, progress: dict) -> int:
    nodes = outline.get("nodes") or []
    if not nodes:
        return int(progress.get("percent") or 0)
    mastery = progress.get("mastery") or {}
    score = 0.0
    for node in nodes:
        nid = str(node.get("id") or "")
        level = mastery.get(nid, "unseen")
        if level == "mastered":
            score += 1.0
        elif level == "practicing":
            score += 0.4
    return int(round(100 * score / len(nodes)))
