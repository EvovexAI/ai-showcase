#!/usr/bin/env python3
"""One-off: export EvoFlow volcengine-tts-speakers.js to config/tts_voices.json."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT.parent / "haze-ctrl" / "evopanel" / "src" / "lib" / "volcengine-tts-speakers.js"
OUT = ROOT / "config" / "tts_voices.json"

def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    items: list[dict[str, str]] = []
    for m in re.finditer(r"\{\s*value:\s*'([^']+)',\s*label:\s*'([^']+)'\s*\}", text):
        items.append({"id": m.group(1), "label": m.group(2)})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} voices -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
