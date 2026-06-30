"""Model router — auto-selects the best model for each task based on complexity.

Saves tokens and cost by routing simple tasks (math, formatting, yes/no) to a
cheaper model and complex tasks (coding, multi-step analysis) to a premium model.

Classification signals:
  - Input length (short = simple)
  - Code blocks present (``` = complex)
  - Keywords (calculate/format = simple; design/implement/architect = complex)
  - Tool usage (multiple tools = complex)
  - Question type (factual = simple; creative/analytical = complex)

Tiers:
  - "fast":    cheap model for trivial tasks (math, formatting, lookups)
  - "default": the configured model for standard tasks
  - "premium": expensive model for complex tasks (coding, architecture)

Configuration via live_config:
  - model_router_enabled: bool (default: False — opt-in)
  - model_fast: model name for fast tier (default: falls back to config.MODEL)
  - model_premium: model name for premium tier (default: falls back to config.MODEL)

When disabled or no tier models are configured, the router returns None and the
brain uses the default model (config.MODEL) as before.
"""
from __future__ import annotations

import re
from typing import Any

from dela import config


# Keywords that signal task complexity
_TRIVIAL_KEYWORDS = {
    # Math / calculations
    "calculate", "what is", "what's", "how much", "how many", "add", "subtract",
    "multiply", "divide", "sum", "average", "percentage",
    # Formatting
    "format", "capitalize", "uppercase", "lowercase", "trim", "replace",
    "sort", "count", "length",
    # Yes/no questions
    "is it", "can you", "does it", "will it", "should i",
    # Simple lookups
    "what time", "what date", "what day", "list the",
}

_COMPLEX_KEYWORDS = {
    # Coding / engineering
    "implement", "design", "architect", "refactor", "debug", "fix bug",
    "write code", "create function", "add feature", "build",
    "optimize", "performance", "algorithm", "data structure",
    # Analysis
    "analyze", "compare", "evaluate", "assess", "investigate",
    "research", "review", "audit", "diagnose",
    # Multi-step
    "workflow", "pipeline", "orchestrate", "coordinate", "plan",
    "step by step", "multi-step",
    # Creative
    "generate", "compose", "draft", "write a", "create a presentation",
    # Security
    "security", "vulnerability", "patch", "fix", "remediate",
}

# Patterns that strongly indicate complexity
_CODE_BLOCK_RE = re.compile(r"```")
_MULTI_LINE_RE = re.compile(r"\n.{50,}", re.DOTALL)
_URL_RE = re.compile(r"https?://")
_QUESTION_RE = re.compile(r"^(what|why|how|when|where|who|can|should|would|could|is|are|do|does)\b", re.I)


def _classify(user_text: str, history: list[dict] | None = None) -> str:
    """Classify the task complexity and return a tier name.

    Returns "fast", "default", or "premium".
    """
    text = user_text.strip()
    text_lower = text.lower()
    score = 0  # higher = more complex

    # ── Length signals ──
    if len(text) < 50:
        score -= 2  # very short = likely simple
    elif len(text) < 150:
        score -= 1
    elif len(text) > 500:
        score += 2  # long = likely complex
    elif len(text) > 250:
        score += 1

    # ── Code blocks ──
    code_blocks = _CODE_BLOCK_RE.findall(text)
    if code_blocks:
        score += 3  # code present = complex

    # ── Multi-line with substance ──
    if _MULTI_LINE_RE.search(text):
        score += 1

    # ── URLs (research tasks) ──
    if _URL_RE.search(text):
        score += 1

    # ── Keyword signals ──
    trivial_hits = sum(1 for kw in _TRIVIAL_KEYWORDS if kw in text_lower)
    complex_hits = sum(1 for kw in _COMPLEX_KEYWORDS if kw in text_lower)
    score += complex_hits * 2
    score -= trivial_hits

    # ── History signals (if provided) ──
    if history:
        tool_msgs = sum(1 for m in history if m.get("role") == "tool")
        if tool_msgs > 2:
            score += 2  # already used several tools = multi-step
        elif tool_msgs > 0:
            score += 1

    # ── Simple factual questions ──
    if _QUESTION_RE.match(text) and len(text) < 80 and not complex_hits:
        score -= 1

    # ── Decide tier ──
    if score <= -2:
        return "fast"
    elif score >= 3:
        return "premium"
    else:
        return "default"


def route_model(
    user_text: str,
    history: list[dict] | None = None,
    explicit_model: str | None = None,
) -> str | None:
    """Return the model name to use for this turn, or None to use the default.

    If explicit_model is provided, it always wins (manual override).
    If the router is disabled, returns None (use default).
    """
    if explicit_model:
        return explicit_model

    from dela import live_config

    enabled = live_config.get("model_router_enabled", True)
    if not enabled or str(enabled).lower() in ("false", "0", "no", "off"):
        return None

    tier = _classify(user_text, history)

    if tier == "fast":
        model = live_config.get("model_fast", None)
        if model and model not in ("default", "__default__"):
            return model
    elif tier == "premium":
        model = live_config.get("model_premium", None)
        if model and model not in ("default", "__default__"):
            return model

    # "default" tier or no model configured for the tier → use config.MODEL (None = default)
    return None


def get_routing_info(user_text: str, history: list[dict] | None = None) -> dict[str, Any]:
    """Return detailed routing info for debugging/display."""
    tier = _classify(user_text, history)
    model = route_model(user_text, history)
    return {
        "tier": tier,
        "model": model or config.MODEL,
        "routed": model is not None and model != config.MODEL,
        "input_length": len(user_text),
        "has_code": bool(_CODE_BLOCK_RE.search(user_text)),
        "has_urls": bool(_URL_RE.search(user_text)),
    }
