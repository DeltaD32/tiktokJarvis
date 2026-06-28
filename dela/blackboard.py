"""Blackboard — shared workspace for multi-agent collaboration.

A blackboard is a JSON file where multiple agents contribute sections to a
single task. The orchestrator creates it, specialists append their analyses,
the orchestrator assembles an execution plan, and a worker executes it.

Status state machine:
  deliberating → awaiting_approval → executing → done | blocked
                                         ↑ (user approves)

This is the classical Blackboard Architecture (1970s AI research), adapted
for Dela: JSON instead of markdown, dela_state/ for storage, no BMW-specific
assumptions. Each blackboard belongs to a project (see projects.py).

The blackboard memory system (see blackboard_memory.py) auto-distills
completed blackboards into durable project learnings and cleans up old files
so the blackboard directory doesn't grow unbounded.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_BB_ROOT = Path(__file__).resolve().parent.parent / "dela_state" / "blackboards"

# Status constants
DELIBERATING = "deliberating"
AWAITING_APPROVAL = "awaiting_approval"
EXECUTING = "executing"
DONE = "done"
BLOCKED = "blocked"
ARCHIVED = "archived"

VALID_TRANSITIONS = {
    DELIBERATING: {AWAITING_APPROVAL, EXECUTING, BLOCKED, DONE},
    AWAITING_APPROVAL: {EXECUTING, BLOCKED},
    EXECUTING: {DONE, BLOCKED},
    BLOCKED: {DELIBERATING, EXECUTING, DONE},
    DONE: {ARCHIVED},
    ARCHIVED: set(),
}


def _bb_path(blackboard_id: str) -> Path:
    return _BB_ROOT / f"{blackboard_id}.json"


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _now_ts() -> float:
    return time.time()


def create(
    task_description: str,
    context: str = "",
    project_id: str = "",
    created_by: str = "orchestrator",
) -> dict[str, Any]:
    """Create a new blackboard. Returns the blackboard dict."""
    _BB_ROOT.mkdir(parents=True, exist_ok=True)

    # Generate a unique ID: timestamp + short counter
    ts = time.strftime("%Y%m%d-%H%M%S")
    existing = list(_BB_ROOT.glob(f"bb-{ts}*.json"))
    blackboard_id = f"bb-{ts}-{len(existing)+1:03d}"

    bb = {
        "id": blackboard_id,
        "project_id": project_id,
        "status": DELIBERATING,
        "task_description": task_description,
        "context": context,
        "created_by": created_by,
        "created_at": _now_ts(),
        "updated_at": _now_ts(),
        "sections": {},        # section_name → {author, written, content}
        "execution_plan": None,  # set by orchestrator
        "execution_result": None,  # set by worker
        "decisions": [],       # list of decision records
        "conflicts": [],       # list of conflict records
        "history": [],         # append-only log of status changes
    }

    _bb_path(blackboard_id).write_text(
        json.dumps(bb, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    _log_event(bb, "created", created_by)
    return bb


def load(blackboard_id: str) -> dict[str, Any] | None:
    """Load a blackboard by ID."""
    path = _bb_path(blackboard_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save(bb: dict[str, Any]) -> None:
    """Save a blackboard back to disk."""
    bb["updated_at"] = _now_ts()
    _bb_path(bb["id"]).write_text(
        json.dumps(bb, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def append_section(
    blackboard_id: str,
    agent: str,
    section_name: str,
    content: str,
) -> dict[str, Any] | None:
    """Append or replace a section on the blackboard.

    Idempotent: if a section with the same name exists, it's replaced
    (the agent is updating its contribution). Each section records who
    wrote it and when.
    """
    bb = load(blackboard_id)
    if bb is None:
        return None

    bb["sections"][section_name] = {
        "author": agent,
        "written": _now(),
        "content": content,
    }
    _log_event(bb, f"section '{section_name}' by {agent}", agent)
    save(bb)
    return bb


def get_section(blackboard_id: str, section_name: str) -> str | None:
    """Read a single section's content."""
    bb = load(blackboard_id)
    if bb is None:
        return None
    section = bb.get("sections", {}).get(section_name)
    return section["content"] if section else None


def list_sections(blackboard_id: str) -> list[dict[str, str]]:
    """List all sections with metadata (author, written) but not content."""
    bb = load(blackboard_id)
    if bb is None:
        return []
    return [
        {"name": name, "author": s["author"], "written": s["written"]}
        for name, s in bb.get("sections", {}).items()
    ]


def set_execution_plan(blackboard_id: str, plan: str, author: str = "orchestrator") -> bool:
    """Set the execution plan (orchestrator-only). This is the assembled
    worker-executable plan from all specialist contributions."""
    bb = load(blackboard_id)
    if bb is None:
        return False
    bb["execution_plan"] = plan
    _log_event(bb, f"execution plan set by {author}", author)
    save(bb)
    return True


def set_execution_result(blackboard_id: str, result: str, author: str = "worker") -> bool:
    """Set the execution result (worker-only)."""
    bb = load(blackboard_id)
    if bb is None:
        return False
    bb["execution_result"] = result
    _log_event(bb, f"execution result by {author}", author)
    save(bb)
    return True


def set_status(blackboard_id: str, status: str, actor: str = "system") -> bool:
    """Transition the blackboard to a new status.

    Validates the transition against the state machine. Returns False
    if the transition is invalid.
    """
    bb = load(blackboard_id)
    if bb is None:
        return False

    current = bb["status"]
    if status not in VALID_TRANSITIONS.get(current, set()):
        return False

    bb["status"] = status
    _log_event(bb, f"status: {current} → {status} by {actor}", actor)
    save(bb)
    return True


def get_status(blackboard_id: str) -> str | None:
    bb = load(blackboard_id)
    return bb["status"] if bb else None


def is_gate_open(blackboard_id: str) -> bool:
    """Check if the blackboard is in 'executing' status — the worker's
    absolute gate check. The worker must not execute if this returns False."""
    return get_status(blackboard_id) == EXECUTING


def record_decision(blackboard_id: str, decision: str, rationale: str, actor: str) -> bool:
    """Record a durable decision on the blackboard."""
    bb = load(blackboard_id)
    if bb is None:
        return False
    bb["decisions"].append({
        "decision": decision,
        "rationale": rationale,
        "actor": actor,
        "timestamp": _now(),
    })
    _log_event(bb, f"decision: {decision[:60]}", actor)
    save(bb)
    return True


def record_conflict(
    blackboard_id: str,
    description: str,
    resolution: str,
    resolver: str,
) -> bool:
    """Record a conflict and its resolution."""
    bb = load(blackboard_id)
    if bb is None:
        return False
    bb["conflicts"].append({
        "description": description,
        "resolution": resolution,
        "resolver": resolver,
        "timestamp": _now(),
    })
    _log_event(bb, f"conflict resolved: {resolution[:60]}", resolver)
    save(bb)
    return True


def archive(blackboard_id: str) -> bool:
    """Archive a completed blackboard (moves to archived status)."""
    return set_status(blackboard_id, ARCHIVED, "system")


def list_active() -> list[dict[str, Any]]:
    """List all non-archived blackboards."""
    if not _BB_ROOT.exists():
        return []
    results = []
    for path in _BB_ROOT.glob("*.json"):
        try:
            bb = json.loads(path.read_text(encoding="utf-8"))
            if bb.get("status") != ARCHIVED:
                results.append({
                    "id": bb["id"],
                    "status": bb["status"],
                    "task": bb["task_description"][:80],
                    "project": bb.get("project_id", ""),
                    "sections": len(bb.get("sections", {})),
                })
        except (json.JSONDecodeError, OSError):
            pass
    return results


def list_all() -> list[dict[str, Any]]:
    """List all blackboards including archived."""
    if not _BB_ROOT.exists():
        return []
    results = []
    for path in _BB_ROOT.glob("*.json"):
        try:
            bb = json.loads(path.read_text(encoding="utf-8"))
            results.append({
                "id": bb["id"],
                "status": bb["status"],
                "task": bb["task_description"][:80],
                "project": bb.get("project_id", ""),
                "sections": len(bb.get("sections", {})),
                "archived": bb.get("status") == ARCHIVED,
            })
        except (json.JSONDecodeError, OSError):
            pass
    return results


def _log_event(bb: dict[str, Any], event: str, actor: str) -> None:
    """Append to the blackboard's history log."""
    bb.setdefault("history", []).append({
        "event": event,
        "actor": actor,
        "timestamp": _now(),
    })


def summary(blackboard_id: str) -> str:
    """Human-readable summary of a blackboard for the model."""
    bb = load(blackboard_id)
    if bb is None:
        return f"Blackboard '{blackboard_id}' not found."

    lines = [
        f"Blackboard: {bb['id']}",
        f"Status: {bb['status']}",
        f"Task: {bb['task_description']}",
        f"Project: {bb.get('project_id', '—')}",
        f"Sections ({len(bb.get('sections', {}))}):",
    ]
    for name, s in bb.get("sections", {}).items():
        lines.append(f"  - {name} (by {s['author']}, {s['written']})")
    if bb.get("execution_plan"):
        lines.append(f"Execution Plan: set ({len(bb['execution_plan'])} chars)")
    if bb.get("execution_result"):
        lines.append(f"Execution Result: set ({len(bb['execution_result'])} chars)")
    if bb.get("decisions"):
        lines.append(f"Decisions: {len(bb['decisions'])}")
    if bb.get("conflicts"):
        lines.append(f"Conflicts: {len(bb['conflicts'])}")
    return "\n".join(lines)