"""Durable execution — session persistence and interruption recovery.

Saves conversation history to dela_state/sessions/<session_id>.json after
each turn. On startup, scans for interrupted sessions and recovers
conservatively:

  - If a turn completed → mark as done, keep the result
  - If a tool call completed → preserve its result, don't re-run
  - If uncertain → mark as interrupted, don't blindly replay

This means Dela can be killed mid-turn and resume gracefully — accepted
work is never lost, and tool calls with side effects are never replayed.

Adapted from Flue's durable execution concept, simplified for Dela's
single-process JSON-based architecture (no SQLite, no Cloudflare).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_SESSIONS_DIR = Path(__file__).resolve().parent.parent / "dela_state" / "sessions"

ACTIVE = "active"
INTERRUPTED = "interrupted"
DONE = "done"


def _session_path(session_id: str) -> Path:
    return _SESSIONS_DIR / f"{session_id}.json"


def save_session(
    session_id: str,
    history: list[dict],
    status: str = ACTIVE,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Save a session's history and status to disk."""
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "id": session_id,
        "status": status,
        "history": history,
        "saved_at": time.time(),
        "metadata": metadata or {},
    }
    _session_path(session_id).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_session(session_id: str) -> dict[str, Any] | None:
    """Load a saved session by ID."""
    path = _session_path(session_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def mark_interrupted(session_id: str) -> None:
    """Mark a session as interrupted (e.g. on SIGTERM)."""
    data = load_session(session_id)
    if data and data.get("status") == ACTIVE:
        data["status"] = INTERRUPTED
        _session_path(session_id).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def mark_done(session_id: str) -> None:
    """Mark a session as done (turn completed successfully)."""
    data = load_session(session_id)
    if data:
        data["status"] = DONE
        _session_path(session_id).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def list_sessions(status: str | None = None) -> list[dict[str, Any]]:
    """List all sessions, optionally filtered by status."""
    if not _SESSIONS_DIR.exists():
        return []
    results = []
    for path in _SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if status is None or data.get("status") == status:
                results.append({
                    "id": data["id"],
                    "status": data["status"],
                    "messages": len(data.get("history", [])),
                    "saved_at": data.get("saved_at", 0),
                })
        except (json.JSONDecodeError, OSError):
            pass
    return results


def recover_interrupted() -> list[dict[str, Any]]:
    """Find and recover all interrupted sessions.

    Recovery rules (conservative — never replay side effects):
      - If the last message is an assistant reply → turn completed, mark done
      - If the last message is a tool result → tool completed, mark done
        (the model can decide what to do with it on next turn)
      - If the last message is a user message or assistant tool_calls without
        a following tool result → uncertain, mark interrupted and note it

    Returns a list of recovery reports.
    """
    interrupted = list_sessions(status=INTERRUPTED)
    reports = []

    for session_info in interrupted:
        data = load_session(session_info["id"])
        if not data:
            continue

        history = data.get("history", [])
        if not history:
            data["status"] = DONE
            _save_raw(data)
            reports.append({"id": data["id"], "action": "marked done (empty history)"})
            continue

        last = history[-1]
        last_role = last.get("role", "")

        if last_role == "assistant" and not last.get("tool_calls"):
            # Turn completed — the assistant gave a final reply
            data["status"] = DONE
            _save_raw(data)
            reports.append({"id": data["id"], "action": "marked done (assistant reply found)"})
        elif last_role == "tool":
            # Tool call completed but turn didn't finish — mark done so the
            # model can continue from the tool result on next interaction
            data["status"] = DONE
            data.setdefault("metadata", {})["recovered_from_interrupt"] = True
            data["metadata"]["recovery_note"] = "Last tool call completed; turn was interrupted before model could respond."
            _save_raw(data)
            reports.append({"id": data["id"], "action": "marked done (tool result preserved, turn can continue)"})
        elif last_role == "user" or (last_role == "assistant" and last.get("tool_calls")):
            # Uncertain — the model was mid-turn or a tool call may have started
            # but we don't have the result. Mark as interrupted and note it.
            data["status"] = INTERRUPTED
            data.setdefault("metadata", {})["recovery_note"] = (
                "Turn was interrupted mid-execution. Tool calls may have started "
                "but their results are unknown. Do NOT replay — start a fresh turn."
            )
            _save_raw(data)
            reports.append({"id": data["id"], "action": "left interrupted (uncertain — do not replay)"})
        else:
            data["status"] = DONE
            _save_raw(data)
            reports.append({"id": data["id"], "action": "marked done (unknown state resolved)"})

    return reports


def _save_raw(data: dict) -> None:
    _session_path(data["id"]).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def delete_session(session_id: str) -> bool:
    """Delete a saved session."""
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
        return True
    return False


def get_or_create_history(session_id: str = "default") -> list[dict]:
    """Get the history for a session, or create a new one.

    This is the main entry point for durable sessions. The brain uses this
    to get a per-session history that persists across restarts.
    """
    data = load_session(session_id)
    if data and data.get("status") in (ACTIVE, DONE, INTERRUPTED):
        return data.get("history", [])
    return []


def auto_save_after_turn(session_id: str, history: list[dict]) -> None:
    """Save the session after a turn completes. Called by the brain."""
    save_session(session_id, history, status=ACTIVE)