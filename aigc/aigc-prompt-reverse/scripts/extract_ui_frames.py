#!/usr/bin/env python3
"""Extract UI reference keyframes from a decomposed video report."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS))
from paths import ROOT, analysis_dir, resolve_project, video_file  # noqa: E402

REFERENCE_FRAMES = [
    "sent_0002_0-12.jpg",
    "sent_0004_0-28.jpg",
    "sent_0005_0-35.jpg",
    "sent_0006_0-43.jpg",
    "sent_0026_3-17.jpg",
]


def extract(aweme_id: str = "7657058079216848178") -> int:
    project = resolve_project(aweme_id)
    vf = video_file(project)
    report_path = analysis_dir(project) / "report.json"
    if not report_path.exists():
        print(f"No report: {report_path}")
        return 1
    if not vf.exists():
        print(f"No video.mp4 at {vf} — copy frames manually when video is available")
        return 1

    report = json.loads(report_path.read_text(encoding="utf-8"))
    scenes = {Path(s.get("frame_path", "").replace("\\", "/")).name: s for s in report.get("scenes") or []}
    out_dir = analysis_dir(project) / "scenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for name in REFERENCE_FRAMES:
        scene = scenes.get(name)
        if not scene:
            print(f"Skip missing scene meta: {name}")
            continue
        t = float(scene.get("start") or 0)
        dest = out_dir / name
        cmd = [
            "ffmpeg", "-y", "-ss", str(t), "-i", str(vf),
            "-frames:v", "1", "-q:v", "2", str(dest),
        ]
        subprocess.run(cmd, check=False, capture_output=True)
        if dest.exists():
            print(f"OK {dest}")
            count += 1
    print(f"Extracted {count} reference frames → {out_dir}")
    return 0 if count else 1


if __name__ == "__main__":
    aid = sys.argv[1] if len(sys.argv) > 1 else "7657058079216848178"
    raise SystemExit(extract(aid))
