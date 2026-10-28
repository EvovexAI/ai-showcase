"""Shared path helpers for the 起号 Douyin pipeline.

Layout contract:
  <repo>/            — code only (scripts/ web/ skills/ config/)
  <repo>/data/       — ALL runtime data (safe to exclude when exporting the project)
    data/videos/{aweme_id}/       one dir per video (meta/video/analysis)
    data/reports/YYYY-MM/*.md     insight-report knowledge base
    data/downloads/               transient downloads
    data/uploads/                 uploads
    data/productions/             generated plan assets
    data/last-video.txt           'last' pointer
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
VIDEOS_DIR = DATA_DIR / "videos"
PRODUCTIONS_DIR = DATA_DIR / "productions"
DOWNLOADS_DIR = DATA_DIR / "downloads"
UPLOADS_DIR = DATA_DIR / "uploads"
REPORTS_KB_DIR = DATA_DIR / "reports"
LAST_VIDEO_FILE = DATA_DIR / "last-video.txt"
CONFIG_DIR = ROOT / "config"          # code-side config templates travel with the repo
SKILLS_DIR = ROOT / "skills"


def _safe_slug(text: str, limit: int = 24) -> str:
    """Filesystem-safe short slug from a title."""
    text = re.sub(r"[\\/:*?\"<>|#\s]+", "", text or "")
    return text[:limit] or "untitled"


def reports_kb_dir() -> Path:
    """Fixed knowledge-base dir for insight reports: data/reports/YYYY-MM/."""
    REPORTS_KB_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_KB_DIR


def report_kb_path(aweme_id: str, title: str = "", analyzed_at: str = "") -> Path:
    """Canonical report location: data/reports/{YYYY-MM}/{标题}_{MMDD}_{id后6位}.md

    标题是核心信息放最前；日期用 4 位短格式（MMDD）放标题后；
    aweme_id 取后 6 位仅用于同名去重。
    """
    from datetime import datetime as _dt

    date_part = ""
    if analyzed_at:
        date_part = analyzed_at[:10].replace("/", "-")
    if not re.match(r"\d{4}-\d{2}-\d{2}", date_part or ""):
        date_part = _dt.now().strftime("%Y-%m-%d")
    month_dir = reports_kb_dir() / date_part[:7]
    month_dir.mkdir(parents=True, exist_ok=True)
    short_date = date_part[5:7] + date_part[8:10]  # MMDD
    id_tail = (aweme_id or "")[-6:]
    name = _safe_slug(title, limit=40)
    stem = f"{name}_{short_date}" + (f"_{id_tail}" if id_tail else "")
    return month_dir / f"{stem}.md"


def tts_settings_file() -> Path:
    return CONFIG_DIR / "tts.json"


def production_audio_dir(plan_id: str) -> Path:
    path = productions_dir() / sanitize_plan_id(plan_id) / "audio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_dir(aweme_id: str) -> Path:
    return VIDEOS_DIR / aweme_id


def video_file(project: Path) -> Path:
    return project / "video.mp4"


def meta_file(project: Path) -> Path:
    return project / "meta.json"


def analysis_dir(project: Path) -> Path:
    return project / "analysis"


def vision_dir(project: Path) -> Path:
    return project / "analysis" / "vision"


def write_last_project(project: Path) -> None:
    LAST_VIDEO_FILE.write_text(str(project.resolve()), encoding="utf-8")


def read_last_project() -> Path | None:
    if not LAST_VIDEO_FILE.exists():
        return None
    raw = LAST_VIDEO_FILE.read_text(encoding="utf-8").strip()
    path = Path(raw)
    return path if path.exists() else None


def load_meta(project: Path) -> dict:
    path = meta_file(project)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_meta(project: Path, meta: dict) -> None:
    project.mkdir(parents=True, exist_ok=True)
    meta_file(project).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def create_or_update_meta(
    project: Path,
    *,
    aweme_id: str,
    title: str,
    source_url: str = "",
    share_text: str = "",
    desc: str = "",
    author_nickname: str = "",
    author_unique_id: str = "",
    hashtags: list[str] | None = None,
    canonical_url: str = "",
) -> dict:
    meta = load_meta(project)
    updates: dict = {
        "aweme_id": aweme_id,
        "title": title,
        "source_url": source_url or meta.get("source_url", ""),
        "share_text": share_text or meta.get("share_text", ""),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    if desc:
        updates["desc"] = desc
    if author_nickname:
        updates["author_nickname"] = author_nickname
    if author_unique_id:
        updates["author_unique_id"] = author_unique_id
    if hashtags:
        updates["hashtags"] = hashtags
    if canonical_url:
        updates["canonical_url"] = canonical_url
    elif aweme_id and not meta.get("canonical_url"):
        updates["canonical_url"] = f"https://www.douyin.com/video/{aweme_id}"

    meta.update(updates)
    if "created_at" not in meta:
        meta["created_at"] = meta["updated_at"]
    save_meta(project, meta)
    return meta


def resolve_project(raw: str) -> Path:
    """Resolve aweme id, project dir, video.mp4 path, or 'last'."""
    text = raw.strip()
    if text in {"last", "latest"}:
        project = read_last_project()
        if project is None:
            raise FileNotFoundError("No last-video.txt pointer found")
        return project

    path = Path(text)
    if path.is_dir() and (path / "video.mp4").exists():
        return path.resolve()
    if path.is_dir() and meta_file(path).exists():
        return path.resolve()
    if path.name == "video.mp4" and path.exists():
        return path.parent.resolve()

    if path.exists() and path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
        # Legacy flat file — infer project from [id] suffix if present.
        m = re.search(r"\[(\d+)\]$", path.stem)
        if m:
            return project_dir(m.group(1))
        raise ValueError(f"Legacy video file without aweme id: {path}")

    if re.fullmatch(r"\d{8,}", text):
        project = project_dir(text)
        if project.exists():
            return project.resolve()
        raise FileNotFoundError(f"Project not found for aweme id: {text}")

    raise FileNotFoundError(f"Cannot resolve project from: {raw!r}")


def list_projects() -> list[Path]:
    if not VIDEOS_DIR.exists():
        return []
    return sorted(
        [p for p in VIDEOS_DIR.iterdir() if p.is_dir() and meta_file(p).exists()],
        key=lambda p: load_meta(p).get("updated_at", ""),
        reverse=True,
    )


def productions_dir() -> Path:
    path = PRODUCTIONS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_plan_id(raw: str) -> str:
    slug = re.sub(r"[^\w\-]+", "-", raw.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "untitled"


def production_file(plan_id: str) -> Path:
    return productions_dir() / f"{sanitize_plan_id(plan_id)}.json"


def list_productions() -> list[dict]:
    out: list[dict] = []
    for path in sorted(productions_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        shots = data.get("shots") or []
        out.append(
            {
                "id": data.get("id") or path.stem,
                "title": data.get("title") or path.stem,
                "updated_at": data.get("updated_at", ""),
                "total_duration": data.get("total_duration", ""),
                "shot_count": len(shots),
                "shots": [
                    {
                        "index": s.get("index", i + 1),
                        "time_range": s.get("time_range", ""),
                    }
                    for i, s in enumerate(shots)
                ],
            }
        )
    return out


def load_production(plan_id: str) -> dict:
    path = production_file(plan_id)
    if not path.exists():
        raise FileNotFoundError(f"Production plan not found: {plan_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_production(plan: dict) -> Path:
    plan_id = sanitize_plan_id(plan.get("id") or plan.get("title") or "untitled")
    plan["id"] = plan_id
    plan["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path = production_file(plan_id)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def new_production_template(*, title: str = "新视频策划") -> dict:
    return {
        "id": sanitize_plan_id(title),
        "title": title,
        "goal": "",
        "aspect_ratio": "9:16",
        "total_duration": "60s",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "shots": [
            {
                "index": 1,
                "time_range": "0:00-0:05",
                "duration_seconds": 5,
                "visual": "开场画面描述",
                "voiceover": "口播文案",
                "action": "录屏或操作说明",
                "subtitle": "",
            }
        ],
        "full_script": "",
        "notes": "",
    }
