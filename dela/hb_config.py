"""Load the heartbeat config file (heartbeat_config.json).

This is the file you tune: intervals, thresholds, quiet hours, which checks
are on. Editing a value here changes behavior with no code edit. If the file
is missing, defaults are used so Dela still runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CFG_PATH = Path(__file__).resolve().parent.parent / "heartbeat_config.json"

_DEFAULTS: dict[str, Any] = {
    "heartbeat_interval_seconds": 30,
    "quiet_hours": {"enabled": False, "start": "22:00", "end": "08:00"},
    "checks": {},
}


def load() -> dict[str, Any]:
    if not _CFG_PATH.exists():
        return _DEFAULTS.copy()
    try:
        cfg = json.loads(_CFG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _DEFAULTS.copy()
    # Merge with defaults so missing keys don't crash.
    merged = _DEFAULTS.copy()
    merged.update(cfg)
    if "quiet_hours" not in cfg:
        merged["quiet_hours"] = _DEFAULTS["quiet_hours"]
    if "checks" not in cfg:
        merged["checks"] = _DEFAULTS["checks"]
    return merged


def path() -> Path:
    return _CFG_PATH
