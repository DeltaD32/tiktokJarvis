"""Conversation compaction — auto-summarize older messages when near the context limit.

When the conversation history grows too large for the model's context window,
compaction summarizes older messages into a compact block while keeping the
most recent messages intact. This prevents long sessions from breaking.

Token estimation uses a simple heuristic (4 chars ≈ 1 token) — good enough
for threshold detection without a tokenizer dependency.

Adapted from Flue's CompactionConfig concept: reserveTokens (headroom before
compaction triggers) and keepRecentTokens (recent messages preserved unchanged).
"""

from __future__ import annotations

from typing import Any

from dela import config, provider
from dela.provider import Message, ProviderError

# Default: compact when history exceeds ~100K chars (~25K tokens).
# Keeps the last ~20K chars (~5K tokens) intact.
_DEFAULT_THRESHOLD_CHARS = 100_000
_DEFAULT_KEEP_RECENT_CHARS = 20_000


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


def _history_char_count(history: list[Message]) -> int:
    """Total character count of all message contents in history."""
    total = 0
    for msg in history:
        content = msg.get("content", "") or ""
        total += len(str(content))
        # Tool calls and results add to the size
        if "tool_calls" in msg:
            import json
            total += len(json.dumps(msg["tool_calls"]))
    return total


def should_compact(history: list[Message]) -> bool:
    """Check if the history exceeds the compaction threshold."""
    threshold = int(getattr(config, "COMPACTION_THRESHOLD_CHARS", _DEFAULT_THRESHOLD_CHARS))
    return _history_char_count(history) > threshold


def compact(history: list[Message]) -> list[Message]:
    """Compact the conversation history by summarizing older messages.

    Keeps the most recent messages (up to keep_recent_chars) intact.
    Summarizes everything before that into a single system-context message.

    Returns a new history list. If compaction fails (model unreachable),
    returns the original history unchanged — never breaks the conversation.
    """
    keep_recent = int(getattr(config, "COMPACTION_KEEP_RECENT_CHARS", _DEFAULT_KEEP_RECENT_CHARS))

    # Find the split point: keep the last N chars worth of messages
    recent_chars = 0
    split_idx = len(history)
    for i in range(len(history) - 1, -1, -1):
        msg = history[i]
        content = str(msg.get("content", "") or "")
        recent_chars += len(content)
        if recent_chars > keep_recent:
            split_idx = i + 1
            break

    if split_idx <= 1:
        return history  # nothing to compact

    older = history[:split_idx]
    recent = history[split_idx:]

    # Summarize the older messages
    summary = _summarize(older)
    if summary is None:
        return history  # summarization failed — keep original

    # Build the compacted history: summary message + recent messages
    compacted = [{
        "role": "system",
        "content": f"[Conversation summary — earlier messages compacted]\n\n{summary}\n\n[End of summary. Recent messages follow.]",
    }]
    compacted.extend(recent)
    return compacted


def _summarize(messages: list[Message]) -> str | None:
    """Use the model to summarize a list of messages into a concise summary."""
    # Build a text representation of the messages
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = str(msg.get("content", "") or "")
        if role == "tool":
            name = msg.get("name", "tool")
            lines.append(f"[Tool result from {name}]: {content[:500]}")
        elif role == "assistant" and "tool_calls" in msg:
            import json
            calls = msg.get("tool_calls", [])
            call_names = [c.get("function", {}).get("name", "?") for c in calls]
            lines.append(f"[Assistant called tools: {', '.join(call_names)}]")
            if content:
                lines.append(f"  {content[:300]}")
        else:
            lines.append(f"[{role}]: {content[:800]}")

    conversation_text = "\n".join(lines)

    summary_prompt = (
        f"Summarize the following conversation history concisely. "
        f"Preserve key facts, decisions, tool results, and the current task context. "
        f"Keep it under 500 words.\n\n{conversation_text}"
    )

    try:
        result = provider.assemble(
            "You are a conversation summarizer. Be concise and preserve key information.",
            [{"role": "user", "content": summary_prompt}],
        )
        return result
    except ProviderError:
        return None


def maybe_compact(history: list[Message]) -> list[Message]:
    """Compact the history if needed. Returns the (possibly compacted) history."""
    if should_compact(history):
        return compact(history)
    return history