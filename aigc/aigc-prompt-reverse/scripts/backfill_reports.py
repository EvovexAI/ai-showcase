#!/usr/bin/env python3
"""Backfill: rebuild report.md with insights + knowledge-base copies for existing projects (v2 run)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from analyze_douyin import analyze  # noqa: E402
from paths import VIDEOS_DIR, analysis_dir  # noqa: E402


def main() -> int:
    ok = skip = fail = 0
    for project in sorted(VIDEOS_DIR.iterdir()):
        if not project.is_dir() or not project.name.isdigit():
            continue
        report = analysis_dir(project) / "report.json"
        if not report.exists():
            skip += 1
            continue
        try:
            analyze(project, analysis_dir(project), full=True)
            ok += 1
            print("ok:", project.name)
        except Exception as exc:
            fail += 1
            print("fail:", project.name, str(exc)[:160])
    print(f"done: ok={ok} skip={skip} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
