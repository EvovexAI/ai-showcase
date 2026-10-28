#!/usr/bin/env python3
"""Smart coach local panel — progress / materials / sessions. Port 8769."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).parent))
from paths import (
    DEFAULT_META,
    DEFAULT_OUTLINE,
    DEFAULT_PROGRESS,
    MATERIALS,
    META_PATH,
    OUTLINE_PATH,
    PROGRESS_PATH,
    ROOT,
    SESSIONS,
    compute_percent,
    ensure_data_dirs,
    list_materials,
    list_sessions,
    read_json,
    write_json,
)

PORT = 8769
WEB = ROOT / "web"


def json_response(handler: BaseHTTPRequestHandler, data: dict, status: int = 200) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def safe_filename(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", name, flags=re.UNICODE)
    return name or f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def parse_multipart_file(content_type: str, body: bytes) -> tuple[str, bytes]:
    """Extract first file field from multipart/form-data without cgi."""
    m = re.search(r"boundary=([^;]+)", content_type, flags=re.I)
    if not m:
        raise ValueError("missing multipart boundary")
    boundary = m.group(1).strip().strip('"').encode("ascii", errors="ignore")
    if not boundary:
        raise ValueError("empty boundary")
    parts = body.split(b"--" + boundary)
    for part in parts:
        if b"Content-Disposition" not in part:
            continue
        header, _, payload = part.partition(b"\r\n\r\n")
        if not payload:
            header, _, payload = part.partition(b"\n\n")
        if not payload:
            continue
        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        elif payload.endswith(b"\n"):
            payload = payload[:-1]
        if payload.endswith(b"--"):
            payload = payload[:-2].rstrip(b"\r\n")
        disp = header.decode("utf-8", errors="replace")
        if "filename=" not in disp:
            continue
        fm = re.search(r'filename="([^"]*)"', disp) or re.search(r"filename=([^;\r\n]+)", disp)
        filename = (fm.group(1).strip() if fm else "") or "upload.bin"
        return filename, payload
    raise ValueError("missing file field")


def build_overview() -> dict:
    ensure_data_dirs()
    outline = read_json(OUTLINE_PATH, DEFAULT_OUTLINE)
    progress = read_json(PROGRESS_PATH, DEFAULT_PROGRESS)
    meta = read_json(META_PATH, DEFAULT_META)
    materials = list_materials()
    percent = compute_percent(outline, progress)
    progress["percent"] = percent
    course = (
        outline.get("course_title")
        or progress.get("course_title")
        or meta.get("course_title")
        or "未命名课程"
    )
    next_focus = progress.get("next_focus") or ""
    if not next_focus and outline.get("nodes"):
        mastery = progress.get("mastery") or {}
        for node in outline["nodes"]:
            nid = str(node.get("id") or "")
            if mastery.get(nid, "unseen") != "mastered":
                next_focus = node.get("title") or nid
                break
    current_chapter = ""
    if next_focus:
        current_chapter = next_focus
    elif outline.get("nodes"):
        current_chapter = outline["nodes"][0].get("title") or ""

    return {
        "ok": True,
        "course_title": course,
        "percent": percent,
        "current_chapter": current_chapter,
        "next_focus": next_focus or "上传资料后，让陪练师梳一份大纲",
        "weak_points": progress.get("weak_points") or [],
        "notes": progress.get("notes") or "",
        "last_session_at": progress.get("last_session_at") or "",
        "materials": materials,
        "materials_count": len(materials),
        "sessions": list_sessions(5),
        "outline": outline,
        "progress": progress,
        "coach_hint": "在 EvoFlow 里对「陪练师」说：继续陪练 / 按资料梳大纲 / 问一个概念",
        "prompts_path": "prompts/coach-system.md",
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path in ("/", "/index.html"):
            return self._serve_file(WEB / "index.html", "text/html; charset=utf-8")
        if path.startswith("/assets/"):
            rel = path[len("/assets/") :]
            fp = WEB / "assets" / rel
            if not fp.is_file():
                return json_response(self, {"ok": False, "error": "not found"}, 404)
            ctype = "text/css" if fp.suffix == ".css" else "application/javascript"
            if fp.suffix == ".svg":
                ctype = "image/svg+xml"
            return self._serve_file(fp, ctype)

        if path == "/api/health":
            return json_response(self, {"ok": True, "service": "smart-coach", "port": PORT})

        if path == "/api/overview":
            return json_response(self, build_overview())

        if path == "/api/outline":
            return json_response(self, {"ok": True, "outline": read_json(OUTLINE_PATH, DEFAULT_OUTLINE)})

        if path == "/api/progress":
            return json_response(self, {"ok": True, "progress": read_json(PROGRESS_PATH, DEFAULT_PROGRESS)})

        if path == "/api/materials":
            return json_response(self, {"ok": True, "materials": list_materials()})

        if path == "/api/sessions":
            return json_response(self, {"ok": True, "sessions": list_sessions(20)})

        if path.startswith("/api/sessions/") and path.endswith("/raw"):
            name = Path(path.split("/")[-2]).name
            fp = SESSIONS / name
            if not fp.is_file():
                return json_response(self, {"ok": False, "error": "not found"}, 404)
            return self._serve_file(fp, "text/markdown; charset=utf-8")

        return json_response(self, {"ok": False, "error": "not found"}, 404)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return json_response(self, {"ok": False, "error": "invalid json"}, 400)

        if path == "/api/progress":
            ensure_data_dirs()
            current = read_json(PROGRESS_PATH, DEFAULT_PROGRESS)
            if isinstance(data, dict):
                current.update(data)
            outline = read_json(OUTLINE_PATH, DEFAULT_OUTLINE)
            current["percent"] = compute_percent(outline, current)
            write_json(PROGRESS_PATH, current)
            return json_response(self, {"ok": True, "progress": current})

        if path == "/api/outline":
            ensure_data_dirs()
            outline = data.get("outline") if isinstance(data.get("outline"), dict) else data
            if not isinstance(outline, dict):
                return json_response(self, {"ok": False, "error": "outline must be object"}, 400)
            outline["updated_at"] = datetime.now().isoformat(timespec="seconds")
            write_json(OUTLINE_PATH, outline)
            meta = read_json(META_PATH, DEFAULT_META)
            if outline.get("course_title"):
                meta["course_title"] = outline["course_title"]
                write_json(META_PATH, meta)
            return json_response(self, {"ok": True, "outline": outline})

        return json_response(self, {"ok": False, "error": "not found"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/materials":
            return self._upload_material()

        if path == "/api/sessions":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return json_response(self, {"ok": False, "error": "invalid json"}, 400)
            ensure_data_dirs()
            stamp = datetime.now().strftime("%Y%m%d-%H%M")
            title = (data.get("title") or "陪练会话").strip()
            body = (data.get("body") or data.get("summary") or "").strip()
            name = f"{stamp}.md"
            content = f"# {title}\n\n{body}\n"
            fp = SESSIONS / name
            fp.write_text(content, encoding="utf-8")
            progress = read_json(PROGRESS_PATH, DEFAULT_PROGRESS)
            progress["last_session_at"] = datetime.now().isoformat(timespec="seconds")
            if data.get("next_focus"):
                progress["next_focus"] = data["next_focus"]
            if data.get("mastery_updates") and isinstance(data["mastery_updates"], dict):
                mastery = progress.setdefault("mastery", {})
                mastery.update(data["mastery_updates"])
            if data.get("weak_points") is not None:
                progress["weak_points"] = data["weak_points"]
            outline = read_json(OUTLINE_PATH, DEFAULT_OUTLINE)
            progress["percent"] = compute_percent(outline, progress)
            write_json(PROGRESS_PATH, progress)
            return json_response(
                self,
                {"ok": True, "session": {"name": name, "path": f"data/sessions/{name}"}, "progress": progress},
            )

        if path == "/api/sync-kb":
            # Local stub: remind agent/kit to import data/materials. No gateway call here.
            materials = list_materials()
            return json_response(
                self,
                {
                    "ok": True,
                    "message": "本地资料已就绪。请用 evoflow-onboarding-kit 的 sync-kb，或让陪练师把 data/materials 导入「陪练资料库」。",
                    "folder": str(MATERIALS),
                    "count": len(materials),
                },
            )

        return json_response(self, {"ok": False, "error": "not found"}, 404)

    def _upload_material(self) -> None:
        ensure_data_dirs()
        ctype = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if "multipart/form-data" in ctype:
            try:
                filename, payload = parse_multipart_file(ctype, raw)
            except ValueError as exc:
                return json_response(self, {"ok": False, "error": str(exc)}, 400)
            name = safe_filename(filename)
            dest = MATERIALS / name
            dest.write_bytes(payload)
        else:
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return json_response(self, {"ok": False, "error": "invalid json"}, 400)
            name = safe_filename(data.get("name") or "note.md")
            text = data.get("content") or data.get("text") or ""
            dest = MATERIALS / name
            dest.write_text(text, encoding="utf-8")

        meta = read_json(META_PATH, DEFAULT_META)
        meta["materials_count"] = len(list_materials())
        write_json(META_PATH, meta)
        return json_response(
            self,
            {
                "ok": True,
                "material": {
                    "name": dest.name,
                    "path": str(dest.relative_to(ROOT)).replace("\\", "/"),
                },
                "materials": list_materials(),
            },
        )

    def _serve_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            return json_response(self, {"ok": False, "error": "not found"}, 404)
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    ensure_data_dirs()
    # Seed a tiny sample material if no real files (ignore .gitkeep)
    real = [p for p in MATERIALS.iterdir() if p.is_file() and not p.name.startswith(".")]
    if not real:
        sample = MATERIALS / "样例-学习笔记.md"
        sample.write_text(
            "# 样例学习笔记\n\n"
            "## 1. 什么是智能陪练\n"
            "陪练师根据资料梳大纲，再用短问答帮你巩固。\n\n"
            "## 2. 学员怎么用\n"
            "上传资料 → 让陪练师梳大纲 → 说「继续陪练」→ 随时提问。\n\n"
            "## 3. 掌握度档位\n"
            "未学 / 练习中 / 已掌握。\n",
            encoding="utf-8",
        )
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Smart coach panel → http://127.0.0.1:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye", flush=True)


if __name__ == "__main__":
    main()
