"""The audit trail — a plain log of what Dela did and why.

Every consequential event is logged: tool calls (and their results), heartbeat
notices, confirmation requests (and the answer), model calls (for cost). When
something surprises you, this is how you find out what happened. The log is
plain text, append-only, and human-readable.

A running cost tally is kept so a runaway loop is visible immediately — not an
invoice, just a visible counter that updates as calls accumulate.
"""

from __future__ import annotations

import time
from pathlib import Path

_LOG = Path(__file__).resolve().parent.parent / "dela_state" / "audit.log"
_COST = Path(__file__).resolve().parent.parent / "dela_state" / "cost_tally.json"

_model_calls = 0
_estimated_cost = 0.0


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _write(line: str) -> None:
    _LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def tool_call(name: str, args: dict, result: str, confirmed: bool | None = None) -> None:
    tag = ""
    if confirmed is True:
        tag = " [confirmed by user]"
    elif confirmed is False:
        tag = " [DENIED by user]"
    elif confirmed is None and name:
        pass
    _write(f"[{_ts()}] TOOL {name}({args}){tag} -> {result[:200]}")


def confirmation_request(tool_name: str, description: str, granted: bool) -> None:
    verdict = "GRANTED" if granted else "DENIED"
    _write(f"[{_ts()}] GATE {tool_name}: {description} -> {verdict}")


def heartbeat_notice(source: str, message: str, severity: str) -> None:
    _write(f"[{_ts()}] HEARTBEAT [{severity}] {source}: {message}")


def model_call(model: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
    """Record a model call and update the cost tally.

    Token counts are estimated when the provider doesn't report them. The cost
    is a rough estimate — enough to spot a runaway loop, not an invoice.
    """
    global _model_calls, _estimated_cost
    _model_calls += 1
    # Rough cost estimate per call (conservative; varies by model).
    rate = 0.002  # ~$0.002 per call as a visible counter
    _estimated_cost += rate
    _write(
        f"[{_ts()}] MODEL {model} call #{_model_calls} "
        f"(in~{input_tokens} out~{output_tokens}) est_cost~${_estimated_cost:.4f}"
    )
    _save_cost()


def _save_cost() -> None:
    import json

    _COST.parent.mkdir(parents=True, exist_ok=True)
    _COST.write_text(
        json.dumps(
            {"model_calls": _model_calls, "estimated_cost_usd": round(_estimated_cost, 4)},
            indent=2,
        ),
        encoding="utf-8",
    )


def cost_summary() -> str:
    return f"{_model_calls} model calls, est. cost ${_estimated_cost:.4f}"


def kill_switch(state: str) -> None:
    _write(f"[{_ts()}] KILL_SWITCH {state}")


def _write_event(event: str) -> None:
    """Write a generic event line (used by tracing for sub-agent events, etc.)."""
    _write(f"[{_ts()}] {event}")


def tail(n: int = 20) -> str:
    """Return the last n lines of the audit log for display."""
    if not _LOG.exists():
        return "(audit log is empty)"
    lines = _LOG.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-n:])
