"""The noticeboard — where proactive notices land and wait for the user.

Notices filed by the heartbeat live here. They are durable (survive restarts),
dismissible (the user can clear them), and held for return (if the user is away,
the notice is still here when they come back). This is the "calm log" the spec
calls for — most things accumulate quietly; only truly urgent ones interrupt.

A notice is a small, plain record:
  {id, source, message, severity, created_at, dismissed}

severity is one of: "info" (calm log), "attention" (surface on return),
"urgent" (earn an interruption). The heartbeat decides which to file; the
entry point decides how loudly to show them.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from dela import user_context


def _store() -> Path:
    return user_context.resolve_state_path("notices.json")

INFO = "info"
ATTENTION = "attention"
URGENT = "urgent"

# Hook set by the server (if running) to push new notices to connected clients.
# None when running headless (CLI text/voice). Keeps the heartbeat decoupled.
_on_file_hook = None


def set_on_file_hook(hook) -> None:
    global _on_file_hook
    _on_file_hook = hook


def _load() -> list[dict]:
    if not _store().exists():
        return []
    try:
        return json.loads(_store().read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(notices: list[dict]) -> None:
    _store().parent.mkdir(parents=True, exist_ok=True)
    _store().write_text(json.dumps(notices, indent=2, ensure_ascii=False), encoding="utf-8")


def file(source: str, message: str, severity: str = INFO) -> dict | None:
    """Add a notice, unless an identical one is already active (dedup).

    The same condition firing every tick shouldn't pile up identical notices.
    If there's already an active (non-dismissed) notice with the same source and
    message, we skip. Once dismissed, a new occurrence can file again. Returns
    the notice, or None if it was deduped.
    """
    notices = _load()
    for n in notices:
        if (
            not n["dismissed"]
            and n["source"] == source
            and n["message"] == message
        ):
            return None  # already active — don't pile up
    next_id = (max((n["id"] for n in notices), default=0)) + 1
    notice = {
        "id": next_id,
        "source": source,
        "message": message,
        "severity": severity,
        "created_at": time.time(),
        "dismissed": False,
    }
    notices.append(notice)
    _save(notices)
    if _on_file_hook is not None:
        _on_file_hook(notice)
    return notice


def dismiss(notice_id: int) -> bool:
    """Mark a notice as dismissed. Returns True if found."""
    notices = _load()
    for n in notices:
        if n["id"] == notice_id:
            n["dismissed"] = True
            _save(notices)
            return True
    return False


def dismiss_all() -> int:
    """Dismiss all active notices. Returns the count dismissed."""
    notices = _load()
    count = 0
    for n in notices:
        if not n["dismissed"]:
            n["dismissed"] = True
            count += 1
    if count:
        _save(notices)
    return count


def active() -> list[dict]:
    """Return notices not yet dismissed, oldest first."""
    return [n for n in _load() if not n["dismissed"]]


def active_of(severity: str) -> list[dict]:
    return [n for n in active() if n["severity"] == severity]


def all() -> list[dict]:
    """Return every notice, including dismissed (for the log view)."""
    return _load()


def pending_on_return() -> list[dict]:
    """Notices worth surfacing when the user comes back: attention + urgent."""
    return [n for n in active() if n["severity"] in (ATTENTION, URGENT)]
