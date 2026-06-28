"""Persisted schedule state for the heartbeat.

Each check has a `next_due` timestamp persisted to disk. On restart, the
heartbeat reads this to decide what's due — so restarting doesn't reset every
timer or fire everything at once. The schedule lives in durable state, not
only in memory.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parent.parent / "dela_state" / "schedule.json"


def _load() -> dict[str, float]:
    if not _STORE.exists():
        return {}
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(state: dict[str, float]) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def next_due(check_name: str) -> float:
    """Return the next due time for a check, or 0 if never scheduled."""
    return _load().get(check_name, 0.0)


def is_due(check_name: str, now: float | None = None) -> bool:
    t = now or time.time()
    return t >= next_due(check_name)


def mark_run(check_name: str, interval_seconds: float, now: float | None = None) -> None:
    """Set the next due time for a check to now + interval."""
    t = now or time.time()
    state = _load()
    state[check_name] = t + interval_seconds
    _save(state)


def set_due(check_name: str, when: float) -> None:
    state = _load()
    state[check_name] = when
    _save(state)
