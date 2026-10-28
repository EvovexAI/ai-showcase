"""Cron scheduler for workbench automations."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from paths import ROOT

WORKBENCH_DIR = ROOT / "workbench"
DATA_DIR = WORKBENCH_DIR / "data"
AUTOMATIONS_FILE = DATA_DIR / "automations.json"

_run_automation: Callable[[str], dict[str, Any]] | None = None
_thread: threading.Thread | None = None
_stop = threading.Event()


def _parse_cron_field(field: str, value: int, min_v: int, max_v: int) -> bool:
    if field == "*":
        return True
    if field.isdigit():
        return value == int(field)
    if field.startswith("*/"):
        step = int(field[2:])
        return (value - min_v) % step == 0
    return False


def cron_matches(expr: str, now: datetime) -> bool:
    parts = expr.strip().split()
    if len(parts) != 5:
        return False
    minute, hour, dom, month, dow = parts
    return (
        _parse_cron_field(minute, now.minute, 0, 59)
        and _parse_cron_field(hour, now.hour, 0, 23)
        and _parse_cron_field(dom, now.day, 1, 31)
        and _parse_cron_field(month, now.month, 1, 12)
        and (dow == "*" or True)
    )


def _load_automations() -> list[dict[str, Any]]:
    if not AUTOMATIONS_FILE.exists():
        return []
    return list(json.loads(AUTOMATIONS_FILE.read_text(encoding="utf-8")).get("items") or [])


def _tick() -> None:
    if not _run_automation:
        return
    now = datetime.now()
    for auto in _load_automations():
        schedule = auto.get("schedule")
        if not schedule:
            continue
        last = auto.get("last_run_at") or ""
        if last and last[:16] == now.strftime("%Y-%m-%dT%H:%M"):
            continue
        if cron_matches(schedule, now):
            try:
                _run_automation(auto["id"])
            except Exception:
                pass


def _loop() -> None:
    while not _stop.is_set():
        _tick()
        _stop.wait(60)


def start_scheduler(run_automation: Callable[[str], dict[str, Any]]) -> None:
    global _run_automation, _thread
    _run_automation = run_automation
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, daemon=True, name="workbench-scheduler")
    _thread.start()


def stop_scheduler() -> None:
    _stop.set()
