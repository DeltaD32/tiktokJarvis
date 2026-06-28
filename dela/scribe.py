"""Scribe — automatic memory recording at task end.

After every sub-agent run, the scribe extracts learnings from the result and
records them in agent memory. This ensures that experience is captured even
if the agent itself doesn't explicitly call record_agent_learning.

The scribe uses simple heuristics to detect what to record:
  - If the result mentions success → record as WORKED
  - If the result mentions failure/error/avoid → record as AVOID
  - Always record a PATTERN summary of what was done

This is non-blocking — scribe failures never break the task flow.
"""

from __future__ import annotations

from dela.agent_memory import WORKED, AVOID, PATTERN, learn


def scribe(agent_name: str, task: str, result: str) -> None:
    """Auto-record learnings from a completed sub-agent task.

    Called after run_subagent returns. Extracts learnings heuristically
    and writes them to agent memory. Non-blocking.
    """
    try:
        result_lower = result.lower()

        # Detect success patterns → WORKED
        success_words = ("success", "completed", "done", "found", "created", "generated")
        if any(w in result_lower for w in success_words):
            # Extract a concise learning from the result
            learning = _extract_learning(result, task)
            if learning:
                learn(agent_name, WORKED, learning, task_context=task[:100])

        # Detect failure patterns → AVOID
        failure_words = ("failed", "error", "couldn't", "avoid", "do not", "should not")
        if any(w in result_lower for w in failure_words):
            learning = _extract_failure(result, task)
            if learning:
                learn(agent_name, AVOID, learning, task_context=task[:100])

        # Always record a pattern summary
        summary = _extract_pattern(task, result)
        if summary:
            learn(agent_name, PATTERN, summary, task_context=task[:100])

    except Exception:
        pass  # Scribe is non-blocking — never break the task flow


def _extract_learning(result: str, task: str) -> str:
    """Extract a concise WORKED learning from the result."""
    # Take the first meaningful sentence (skip headers/blips)
    for line in result.split("\n"):
        line = line.strip()
        if len(line) > 20 and not line.startswith("[") and not line.startswith("Sub-agent"):
            # Truncate to a reasonable learning length
            return line[:150]
    return ""


def _extract_failure(result: str, task: str) -> str:
    """Extract a concise AVOID learning from the result."""
    for line in result.split("\n"):
        line = line.strip().lower()
        if any(w in line for w in ("failed", "error", "couldn't", "avoid")):
            return line[:150]
    return f"Encountered issues during: {task[:100]}"


def _extract_pattern(task: str, result: str) -> str:
    """Extract a concise PATTERN summary."""
    # One sentence: what was the task, what was the outcome
    task_short = task[:60].replace("\n", " ").strip()
    result_short = result[:100].replace("\n", " ").strip()
    return f"Task '{task_short}' → {result_short}"