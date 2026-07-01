"""Blackboard memory — auto-distillation and cleanup of completed blackboards.

This is the cleanup system that keeps the blackboard directory from growing
unbounded. When a blackboard reaches 'done' status:

  1. **Distill** — Extract key learnings (what worked, what was decided, what
     to avoid next time) from the blackboard's sections, decisions, and
     execution result. Store these as project learnings (durable) and as
     agent self-learning memory entries (per-agent).

  2. **Archive** — Move the blackboard to archived status. The file stays on
     disk (for audit) but is no longer listed as active.

  3. **Cleanup** — Periodically, very old archived blackboards (older than
     the retention period) are deleted entirely. Their distilled learnings
     live on in the project store and agent memory, so the raw blackboard
     file is no longer needed.

This means the blackboard directory stays clean: only active and recently-
completed blackboards are present. The knowledge lives on in memory, not in
stale files.

The distillation is done by the brain itself (the model summarizes the
blackboard) or by a simple heuristic extraction if the brain isn't available.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from dela import blackboard, projects

_RETENTION_DAYS = 30  # archived blackboards older than this are deleted


def distill_blackboard(blackboard_id: str, distilled_summary: str = "") -> dict[str, Any]:
    """Distill a completed blackboard into durable learnings.

    If distilled_summary is provided (e.g. from the brain), use it.
    Otherwise, extract a heuristic summary from the blackboard's sections,
    decisions, and execution result.

    Returns the distillation result dict.
    """
    bb = blackboard.load(blackboard_id)
    if bb is None:
        return {"error": f"Blackboard '{blackboard_id}' not found."}

    if bb["status"] != blackboard.DONE:
        return {"error": f"Blackboard status is '{bb['status']}', must be 'done' to distill."}

    # If no summary provided, do heuristic extraction
    if not distilled_summary:
        distilled_summary = _heuristic_distill(bb)

    result = {
        "blackboard_id": blackboard_id,
        "task": bb["task_description"],
        "summary": distilled_summary,
        "decisions": bb.get("decisions", []),
        "conflicts": bb.get("conflicts", []),
        "sections": list(bb.get("sections", {}).keys()),
        "distilled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Store learnings in the project
    project_id = bb.get("project_id", "")
    if project_id:
        projects.add_learning(project_id, distilled_summary, f"blackboard:{blackboard_id}")

        # Also record decisions as project-level decisions if not already there
        for dec in bb.get("decisions", []):
            # Check if already recorded (avoid duplicates)
            existing = projects.get_prior_decisions(project_id)
            if not any(d.get("decision") == dec.get("decision") for d in existing):
                projects.record_decision(
                    project_id,
                    dec.get("decision", ""),
                    dec.get("rationale", ""),
                    dec.get("actor", "unknown"),
                )

    # Store agent self-learning memory
    _store_agent_memory(bb, distilled_summary)

    # Archive the blackboard
    blackboard.archive(blackboard_id)

    return result


def _heuristic_distill(bb: dict[str, Any]) -> str:
    """Extract a summary from a blackboard without the brain.

    This is a fallback when the brain isn't available. It's simple:
    list the task, sections, decisions, and result.
    """
    lines = [f"Task: {bb['task_description']}"]

    sections = bb.get("sections", {})
    if sections:
        lines.append(f"Contributions from {len(sections)} section(s):")
        for name, s in sections.items():
            author = s.get("author", "?")
            # Take first 100 chars of content as a hint
            content_hint = s.get("content", "")[:100].replace("\n", " ")
            lines.append(f"  - {name} (by {author}): {content_hint}...")

    decisions = bb.get("decisions", [])
    if decisions:
        lines.append(f"Decisions ({len(decisions)}):")
        for d in decisions:
            lines.append(f"  - {d.get('decision', '?')}")

    conflicts = bb.get("conflicts", [])
    if conflicts:
        lines.append(f"Conflicts resolved ({len(conflicts)}):")
        for c in conflicts:
            lines.append(f"  - {c.get('description', '?')} → {c.get('resolution', '?')}")

    result = bb.get("execution_result", "")
    if result:
        lines.append(f"Result: {result[:200]}")

    return "\n".join(lines)


def _store_agent_memory(bb: dict[str, Any], summary: str) -> None:
    """Store per-agent learnings from the blackboard.

    Each section's author gets a learning entry in agent memory.
    """
    from dela import memory

    for section_name, section in bb.get("sections", {}).items():
        author = section.get("author", "unknown")
        # Store as a memory fact with category "agent_learning"
        # This is a different kind of memory — not about the user, but about
        # what the agent learned on this task. We store it with a special
        # category prefix to distinguish it from user facts.
        learning_text = f"[Agent {author} on '{bb['task_description'][:60]}']: {summary[:200]}"
        # Don't use remember_fact (that's for user facts and requires confirmation).
        # Write directly to the memory store with a special category.
        try:
            memory.add(learning_text, category="agent_learning")
        except Exception:
            pass  # Memory write is non-blocking


def cleanup_old_blackboards() -> dict[str, int]:
    """Delete archived blackboards older than the retention period.

    Returns counts: {"archived": N, "deleted": M, "remaining": K}
    """
    from dela.blackboard import _bb_root, ARCHIVED

    root = _bb_root()
    if not root.exists():
        return {"archived": 0, "deleted": 0, "remaining": 0}

    now = time.time()
    cutoff = now - (_RETENTION_DAYS * 86400)

    archived_count = 0
    deleted_count = 0
    remaining = 0

    for path in root.glob("*.json"):
        try:
            bb = json.loads(path.read_text(encoding="utf-8"))
            if bb.get("status") == ARCHIVED:
                archived_count += 1
                # Check age by updated_at
                updated = bb.get("updated_at", 0)
                if updated < cutoff:
                    path.unlink()
                    deleted_count += 1
                else:
                    remaining += 1
            else:
                remaining += 1
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "archived": archived_count,
        "deleted": deleted_count,
        "remaining": remaining,
    }


def cleanup_completed_blackboards() -> dict[str, int]:
    """Distill and archive all blackboards in 'done' status.

    Called periodically (e.g. by the heartbeat) to keep the blackboard
    directory clean. Each completed blackboard is distilled (learnings
    extracted to project memory + agent memory), then archived.

    Returns counts: {"distilled": N, "errors": M}
    """
    from dela.blackboard import list_active, DONE

    distilled = 0
    errors = 0

    for bb_info in list_active():
        if bb_info["status"] == DONE:
            try:
                distill_blackboard(bb_info["id"])
                distilled += 1
            except Exception:
                errors += 1

    return {"distilled": distilled, "errors": errors}