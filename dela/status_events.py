"""Status events log — append-only lifecycle transition log for projects and blackboards.

Every status change, decision, conflict, dispatch, and completion is recorded
as a structured event. This powers a timeline view in the UI and provides a
full audit trail of how a project evolved over time.

Events are stored in dela_state/status_events.jsonl (JSON Lines format — one
event per line, append-only). JSONL is chosen over a single JSON array
because it's truly append-only (no need to read+parse+modify+write the whole
file to add one event).

Event types:
  - project_created, project_completed
  - blackboard_created, blackboard_status_changed, blackboard_archived
  - specialist_dispatched, specialist_returned
  - execution_plan_set, execution_started, execution_completed
  - decision_recorded, conflict_resolved
  - dag_task_started, dag_task_done, dag_task_failed
  - learning_recorded, learning_distilled
  - routing_cached, routing_hit
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_LOG = Path(__file__).resolve().parent.parent / "dela_state" / "status_events.jsonl"


def log(
    event_type: str,
    entity_id: str = "",
    entity_type: str = "",
    actor: str = "",
    detail: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a status event. Returns the event dict."""
    event = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ts": time.time(),
        "event_type": event_type,
        "entity_id": entity_id,
        "entity_type": entity_type,  # "project", "blackboard", "task", "agent"
        "actor": actor,
        "detail": detail,
        "metadata": metadata or {},
    }

    _LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return event


def tail(n: int = 20) -> list[dict[str, Any]]:
    """Return the last N events."""
    if not _LOG.exists():
        return []
    lines = _LOG.read_text(encoding="utf-8").splitlines()
    events = []
    for line in lines[-n:]:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


def for_entity(entity_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Get all events for a specific entity (project, blackboard, etc.)."""
    if not _LOG.exists():
        return []
    events = []
    for line in _LOG.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
            if event.get("entity_id") == entity_id:
                events.append(event)
        except json.JSONDecodeError:
            pass
    return events[-limit:]


def timeline(entity_id: str) -> str:
    """Human-readable timeline for an entity."""
    events = for_entity(entity_id)
    if not events:
        return f"No events for '{entity_id}'."

    lines = [f"Timeline for {entity_id} ({len(events)} events):"]
    for e in events:
        icon = _ICONS.get(e["event_type"], "•")
        detail = f": {e['detail']}" if e.get("detail") else ""
        lines.append(f"  {e['timestamp']} {icon} {e['event_type']}{detail}")

    return "\n".join(lines)


def timeline_text(limit: int = 20) -> str:
    """Human-readable recent events log."""
    events = tail(limit)
    if not events:
        return "No status events recorded yet."

    lines = [f"Recent events ({len(events)}):"]
    for e in events:
        icon = _ICONS.get(e["event_type"], "•")
        entity = f"[{e['entity_id']}]" if e.get("entity_id") else ""
        detail = f" {e['detail']}" if e.get("detail") else ""
        lines.append(f"  {e['timestamp']} {icon} {e['event_type']} {entity}{detail}")

    return "\n".join(lines)


# Event type → display icon
_ICONS = {
    "project_created": "[+]",
    "project_completed": "[✓]",
    "blackboard_created": "[+]",
    "blackboard_status_changed": "[→]",
    "blackboard_archived": "[↓]",
    "specialist_dispatched": "[>]",
    "specialist_returned": "[<]",
    "execution_plan_set": "[≡]",
    "execution_started": "[▶]",
    "execution_completed": "[✓]",
    "decision_recorded": "[!]",
    "conflict_resolved": "[⚙]",
    "dag_task_started": "[▶]",
    "dag_task_done": "[✓]",
    "dag_task_failed": "[✗]",
    "learning_recorded": "[★]",
    "learning_distilled": "[★]",
    "routing_cached": "[⚡]",
    "routing_hit": "[⚡]",
}