"""Semantic routing cache — learn from past routing decisions to skip deliberation.

When Dela routes a request to a sub-agent or skill, the routing decision is
recorded. On the next similar request, the cache is searched and if a match
is found above the similarity threshold, the same routing is used — skipping
the full deliberation pipeline.

Similarity is computed using a lightweight lexical overlap score (Jaccard on
token sets) rather than embedding vectors. This avoids a dependency on an
external embedding API and works fully offline. The tradeoff is that semantic
matches (different words, same meaning) won't be caught — but lexical matches
are fast, free, and good enough for a single-user assistant where the same
user tends to phrase similar requests similarly.

As the cache grows, Dela gets faster at routing: common request patterns
short-circuit directly to the right agent/skill without deliberation.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from dela import user_context


def _store() -> Path:
    return user_context.resolve_state_path("routing_cache.json")

SIMILARITY_THRESHOLD = 0.65  # Jaccard overlap to trigger a cache hit
MAX_ENTRIES = 200             # prune oldest if exceeding


def _load() -> list[dict[str, Any]]:
    if not _store().exists():
        return []
    try:
        return json.loads(_store().read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(data: list[dict[str, Any]]) -> None:
    _store().parent.mkdir(parents=True, exist_ok=True)
    _store().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _tokenize(text: str) -> set[str]:
    """Simple tokenization: lowercase, split on non-alphanumeric, drop short tokens."""
    tokens = set()
    for word in text.lower().split():
        # Strip punctuation
        clean = "".join(c for c in word if c.isalnum())
        if len(clean) >= 3:
            tokens.add(clean)
    return tokens


def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def record(prompt: str, target: str, target_type: str = "agent", confidence: float = 1.0) -> None:
    """Record a routing decision for future lookup.

    target: the agent name or skill name that was chosen
    target_type: "agent" or "skill"
    confidence: how confident the routing was (1.0 = explicit user choice)
    """
    data = _load()
    tokens = _tokenize(prompt)

    entry = {
        "prompt": prompt[:200],  # truncate for storage
        "tokens": list(tokens),
        "target": target,
        "target_type": target_type,
        "confidence": confidence,
        "timestamp": time.time(),
        "hit_count": 0,
    }

    data.append(entry)

    # Prune if exceeding max (keep highest confidence + most recent)
    if len(data) > MAX_ENTRIES:
        data.sort(key=lambda e: (e.get("confidence", 0), e.get("timestamp", 0)), reverse=True)
        data = data[:MAX_ENTRIES]

    _save(data)


def lookup(prompt: str) -> dict[str, Any] | None:
    """Search the cache for a similar past routing decision.

    Returns the best match above the threshold, or None.
    The returned dict has: target, target_type, similarity, prompt (the cached prompt).
    """
    data = _load()
    if not data:
        return None

    query_tokens = _tokenize(prompt)
    best_match = None
    best_score = 0.0

    for entry in data:
        cached_tokens = set(entry.get("tokens", []))
        score = _jaccard(query_tokens, cached_tokens)
        if score > best_score:
            best_score = score
            best_match = entry

    if best_match and best_score >= SIMILARITY_THRESHOLD:
        # Boost the hit count (popular routes stay relevant)
        best_match["hit_count"] = best_match.get("hit_count", 0) + 1
        _save(data)
        return {
            "target": best_match["target"],
            "target_type": best_match["target_type"],
            "similarity": round(best_score, 3),
            "cached_prompt": best_match["prompt"],
        }

    return None


def clear() -> None:
    """Clear the entire cache."""
    _save([])


def status() -> dict[str, Any]:
    """Return cache statistics."""
    data = _load()
    by_target: dict[str, int] = {}
    for entry in data:
        key = f"{entry['target_type']}:{entry['target']}"
        by_target[key] = by_target.get(key, 0) + 1

    return {
        "entries": len(data),
        "by_target": by_target,
        "threshold": SIMILARITY_THRESHOLD,
    }


def status_text() -> str:
    """Human-readable cache status."""
    s = status()
    lines = [f"Routing cache: {s['entries']} entries (threshold: {s['threshold']})"]
    for target, count in sorted(s["by_target"].items(), key=lambda x: -x[1]):
        lines.append(f"  {target}: {count} route(s)")
    return "\n".join(lines)