"""Agent self-learning memory — per-agent namespaces for experiential learning.

Each agent has its own memory namespace (e.g. "researcher::learnings") where
it records what worked, what to avoid, and patterns it discovered. At the
start of each task, the agent recalls relevant learnings. Over time, agents
get smarter instead of starting fresh every dispatch.

Three learning types:
  - WORKED:   approaches that succeeded — reuse on similar tasks
  - AVOID:    approaches that failed or caused problems — don't repeat
  - PATTERN:  reusable patterns discovered across tasks

Decay scoring: each learning has a score that starts at 1.0 and decays over
time. Learnings that are recalled and confirmed (still relevant) get a boost.
Learnings that are never recalled eventually fall below the threshold and are
pruned. This keeps the store from growing unbounded with stale entries.

Distillation: when a project completes, the secretary can distill cross-cutting
learnings into the "shared::learnings" namespace for all agents to access.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_STORE = Path(__file__).resolve().parent.parent / "dela_state" / "agent_memory.json"

WORKED = "worked"
AVOID = "avoid"
PATTERN = "pattern"

DECAY_RATE = 0.95       # per 30 days
DECAY_INTERVAL = 30 * 86400  # seconds
MIN_SCORE = 0.1         # below this, prune
RECALL_BOOST = 1.15     # score multiplier when recalled and confirmed
MAX_PER_AGENT = 100     # prune oldest/lowest if exceeding


def _load() -> dict[str, list[dict[str, Any]]]:
    if not _STORE.exists():
        return {}
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict[str, list[dict[str, Any]]]) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _ns(agent: str) -> str:
    """Namespace key for an agent."""
    return f"{agent}::learnings"


def _apply_decay(entry: dict[str, Any], now: float) -> dict[str, Any]:
    """Apply time-based decay to a learning entry's score."""
    age = now - entry.get("last_touched", entry.get("created_at", now))
    decay_periods = age / DECAY_INTERVAL
    entry["score"] = entry.get("score", 1.0) * (DECAY_RATE ** decay_periods)
    entry["score"] = max(entry["score"], 0.0)
    return entry


def learn(
    agent: str,
    learning_type: str,
    content: str,
    domain: str = "",
    task_context: str = "",
) -> dict[str, Any]:
    """Record a learning for an agent.

    learning_type: WORKED, AVOID, or PATTERN
    content: the learning itself (one clear sentence)
    domain: optional domain tag for filtering (e.g. "api-design", "pptx")
    task_context: optional context about the task that produced this learning
    """
    data = _load()
    ns = _ns(agent)
    entries = data.setdefault(ns, [])

    entry = {
        "id": f"lrn-{int(time.time() * 1000) % 1000000:06d}",
        "type": learning_type,
        "content": content,
        "domain": domain,
        "task_context": task_context,
        "score": 1.0,
        "created_at": time.time(),
        "last_touched": time.time(),
        "recall_count": 0,
    }
    entries.append(entry)

    # Prune if exceeding max
    if len(entries) > MAX_PER_AGENT:
        entries.sort(key=lambda e: e.get("score", 0), reverse=True)
        data[ns] = entries[:MAX_PER_AGENT]

    _save(data)
    return entry


def recall(
    agent: str,
    domain: str = "",
    limit: int = 10,
    min_score: float = 0.15,
) -> list[dict[str, Any]]:
    """Recall relevant learnings for an agent.

    Returns entries sorted by score (highest first), after applying decay.
    Optionally filtered by domain. Low-score entries are pruned during recall.
    """
    data = _load()
    ns = _ns(agent)
    entries = data.get(ns, [])
    now = time.time()

    # Apply decay and filter
    kept = []
    for entry in entries:
        _apply_decay(entry, now)
        if entry["score"] >= MIN_SCORE:
            kept.append(entry)
        # else: pruned (not kept)

    # Update store if we pruned anything
    if len(kept) != len(entries):
        data[ns] = kept
        _save(data)

    # Filter by domain if specified
    if domain:
        kept = [e for e in kept if domain.lower() in e.get("domain", "").lower() or not e.get("domain")]

    # Sort by score, take top N
    kept.sort(key=lambda e: e["score"], reverse=True)
    return kept[:limit]


def recall_as_prompt(agent: str, domain: str = "") -> str:
    """Recall learnings and format them as a text block for the agent's prompt.

    Call this at the start of a sub-agent's task to inject relevant experience.
    """
    entries = recall(agent, domain=domain, limit=8)
    if not entries:
        return ""

    lines = ["What you've learned from past tasks (use this experience):"]
    for e in entries:
        tag = e["type"].upper()
        lines.append(f"  [{tag}] {e['content']}")

    return "\n".join(lines) + "\n"


def confirm_recall(agent: str, learning_id: str) -> bool:
    """Confirm that a recalled learning was relevant — boosts its score."""
    data = _load()
    ns = _ns(agent)
    for entry in data.get(ns, []):
        if entry["id"] == learning_id:
            entry["score"] = min(entry.get("score", 1.0) * RECALL_BOOST, 2.0)
            entry["recall_count"] = entry.get("recall_count", 0) + 1
            entry["last_touched"] = time.time()
            _save(data)
            return True
    return False


def distill_project_learnings(project_id: str, summary: str) -> int:
    """Distill cross-cutting learnings from a completed project into shared namespace.

    Called by the secretary when a project completes. The summary is the
    distilled project knowledge. Returns the number of shared learnings added.
    """
    # Store in the shared namespace
    learn("shared", PATTERN, summary, domain=project_id, task_context="project distillation")
    return 1


def get_agent_memory_status(agent: str) -> str:
    """Human-readable memory status for an agent."""
    data = _load()
    ns = _ns(agent)
    entries = data.get(ns, [])

    by_type = {}
    for e in entries:
        t = e.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    avg_score = sum(e.get("score", 0) for e in entries) / max(len(entries), 1)

    lines = [
        f"Agent memory for '{agent}': {len(entries)} entries",
        f"  By type: {by_type}",
        f"  Avg score: {avg_score:.2f}",
    ]
    return "\n".join(lines)


def list_all_namespaces() -> list[str]:
    """List all agent memory namespaces."""
    return list(_load().keys())