"""Project store — persistent multi-agent project coordination state.

Projects group related blackboards and track:
  - Specialist queues (sequential handoff order)
  - Cross-task decisions (enforced on future work)
  - Dependencies between blackboards
  - Project-level status

JSON-based, stored in dela_state/projects/. No SQLite dependency — consistent
with Dela's existing state pattern. The secretary agent is the only agent
that writes to project state; specialists and workers read it.

This is the coordination layer that makes the blackboard system work for
multi-step projects that span multiple blackboards and multiple agents.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from dela import user_context


def _proj_root() -> Path:
    return user_context.resolve_state_dir("projects")


def _proj_path(project_id: str) -> Path:
    return _proj_root() / f"{project_id}.json"


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _now_ts() -> float:
    return time.time()


def create_project(name: str, description: str = "") -> dict[str, Any]:
    """Create a new project. Returns the project dict."""
    _proj_root().mkdir(parents=True, exist_ok=True)

    ts = time.strftime("%Y%m%d-%H%M%S")
    slug = name.lower().replace(" ", "-").replace("/", "-")[:40]
    project_id = f"proj-{ts}-{slug}"

    # Avoid collisions
    i = 2
    while _proj_path(project_id).exists():
        project_id = f"proj-{ts}-{slug}-{i}"
        i += 1

    project = {
        "id": project_id,
        "name": name,
        "description": description,
        "status": "active",
        "created_at": _now_ts(),
        "updated_at": _now_ts(),
        "blackboards": [],          # list of blackboard IDs
        "specialist_queue": [],     # [{"agent": name, "task": desc, "status": "pending|running|done", "blackboard": bb_id}]
        "decisions": [],            # [{"decision": str, "rationale": str, "actor": str, "timestamp": str}]
        "conflicts": [],            # [{"description": str, "resolution": str, "resolver": str, "timestamp": str}]
        "dependencies": [],         # [{"blackboard": bb_id, "depends_on": bb_id, "resolved": bool}]
        "learnings": [],            # distilled learnings (from blackboard_memory)
    }

    _proj_path(project_id).write_text(
        json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return project


def load(project_id: str) -> dict[str, Any] | None:
    path = _proj_path(project_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save(project: dict[str, Any]) -> None:
    project["updated_at"] = _now_ts()
    _proj_path(project["id"]).write_text(
        json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def register_blackboard(project_id: str, blackboard_id: str) -> bool:
    """Link a blackboard to a project."""
    project = load(project_id)
    if project is None:
        return False
    if blackboard_id not in project["blackboards"]:
        project["blackboards"].append(blackboard_id)
        save(project)
    return True


def enqueue_specialists(project_id: str, specialists: list[dict[str, str]]) -> bool:
    """Queue specialists for sequential execution.

    specialists: [{"agent": "programming-expert", "task": "Analyze the API"}]
    """
    project = load(project_id)
    if project is None:
        return False
    for s in specialists:
        project["specialist_queue"].append({
            "agent": s["agent"],
            "task": s["task"],
            "status": "pending",
            "blackboard": s.get("blackboard", ""),
        })
    save(project)
    return True


def advance_queue(project_id: str) -> dict[str, Any] | None:
    """Mark the current running specialist as done and return the next one.

    Returns the next specialist dict, or None if the queue is empty/exhausted.
    """
    project = load(project_id)
    if project is None:
        return None

    queue = project["specialist_queue"]

    # Mark any running specialist as done
    for item in queue:
        if item["status"] == "running":
            item["status"] = "done"

    # Find the next pending specialist
    for item in queue:
        if item["status"] == "pending":
            item["status"] = "running"
            save(project)
            return item

    save(project)
    return None  # queue exhausted


def get_queue_status(project_id: str) -> list[dict[str, Any]]:
    """Return the full queue with statuses."""
    project = load(project_id)
    if project is None:
        return []
    return project.get("specialist_queue", [])


def get_current_specialist(project_id: str) -> dict[str, Any] | None:
    """Return the currently running specialist, if any."""
    project = load(project_id)
    if project is None:
        return None
    for item in project.get("specialist_queue", []):
        if item["status"] == "running":
            return item
    return None


def record_decision(project_id: str, decision: str, rationale: str, actor: str) -> bool:
    """Record a durable architectural/project decision."""
    project = load(project_id)
    if project is None:
        return False
    project["decisions"].append({
        "decision": decision,
        "rationale": rationale,
        "actor": actor,
        "timestamp": _now(),
    })
    save(project)
    return True


def get_prior_decisions(project_id: str) -> list[dict[str, str]]:
    """Get all prior decisions for a project (enforced on future work)."""
    project = load(project_id)
    if project is None:
        return []
    return project.get("decisions", [])


def record_conflict(
    project_id: str, description: str, resolution: str, resolver: str
) -> bool:
    """Record a conflict and its resolution."""
    project = load(project_id)
    if project is None:
        return False
    project["conflicts"].append({
        "description": description,
        "resolution": resolution,
        "resolver": resolver,
        "timestamp": _now(),
    })
    save(project)
    return True


def set_dependency(project_id: str, blackboard: str, depends_on: str) -> bool:
    """Declare that one blackboard depends on another completing first."""
    project = load(project_id)
    if project is None:
        return False
    project["dependencies"].append({
        "blackboard": blackboard,
        "depends_on": depends_on,
        "resolved": False,
    })
    save(project)
    return True


def check_dependencies(project_id: str, blackboard_id: str) -> bool:
    """Check if all dependencies for a blackboard are resolved."""
    from dela.blackboard import DONE

    project = load(project_id)
    if project is None:
        return True  # no project = no dependencies

    for dep in project.get("dependencies", []):
        if dep["blackboard"] == blackboard_id and not dep["resolved"]:
            dep_bb = dep["depends_on"]
            from dela.blackboard import get_status
            dep_status = get_status(dep_bb)
            if dep_status == DONE:
                dep["resolved"] = True
            else:
                return False  # dependency not yet done

    save(project)
    return True


def add_learning(project_id: str, learning: str, source: str = "") -> bool:
    """Add a distilled learning to the project (from blackboard_memory)."""
    project = load(project_id)
    if project is None:
        return False
    project["learnings"].append({
        "learning": learning,
        "source": source,
        "timestamp": _now(),
    })
    save(project)
    return True


def get_project_status(project_id: str) -> str:
    """Human-readable project status for the model."""
    project = load(project_id)
    if project is None:
        return f"Project '{project_id}' not found."

    lines = [
        f"Project: {project['name']} ({project['id']})",
        f"Status: {project['status']}",
        f"Blackboards: {len(project['blackboards'])}",
        f"Queue: {len(project['specialist_queue'])} items",
    ]

    queue = project.get("specialist_queue", [])
    for item in queue:
        lines.append(f"  - [{item['status']}] {item['agent']}: {item['task'][:60]}")

    if project.get("decisions"):
        lines.append(f"Decisions: {len(project['decisions'])}")
    if project.get("conflicts"):
        lines.append(f"Conflicts: {len(project['conflicts'])}")
    if project.get("learnings"):
        lines.append(f"Learnings: {len(project['learnings'])}")

    return "\n".join(lines)


def find_project_for_task(task_description: str) -> dict[str, Any] | None:
    """Fuzzy-match a task description to an existing project."""
    if not _proj_root().exists():
        return None

    task_lower = task_description.lower()
    best_match = None
    best_score = 0

    for path in _proj_root().glob("*.json"):
        try:
            project = json.loads(path.read_text(encoding="utf-8"))
            if project.get("status") != "active":
                continue

            # Simple keyword overlap scoring
            name = project.get("name", "").lower()
            desc = project.get("description", "").lower()
            combined = f"{name} {desc}"

            words = set(task_lower.split())
            project_words = set(combined.split())
            overlap = len(words & project_words)
            score = overlap / max(len(words), 1)

            if score > best_score and score > 0.2:
                best_score = score
                best_match = project
        except (json.JSONDecodeError, OSError):
            pass

    return best_match


def list_projects(active_only: bool = True) -> list[dict[str, Any]]:
    """List all projects."""
    if not _proj_root().exists():
        return []
    results = []
    for path in _proj_root().glob("*.json"):
        try:
            project = json.loads(path.read_text(encoding="utf-8"))
            if active_only and project.get("status") != "active":
                continue
            results.append({
                "id": project["id"],
                "name": project["name"],
                "status": project["status"],
                "blackboards": len(project.get("blackboards", [])),
                "queue_pending": sum(1 for q in project.get("specialist_queue", []) if q["status"] == "pending"),
            })
        except (json.JSONDecodeError, OSError):
            pass
    return results