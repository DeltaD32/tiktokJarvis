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


def analytics() -> dict:
    """Return structured analytics data parsed from the audit log."""
    import json as _json
    from collections import Counter

    result = {
        "model_calls": _model_calls,
        "estimated_cost_usd": round(_estimated_cost, 4),
        "tool_calls": 0,
        "gate_granted": 0,
        "gate_denied": 0,
        "heartbeat_notices": 0,
        "kill_switch_events": 0,
        "tool_breakdown": {},
        "recent_events": [],
    }

    if not _LOG.exists():
        return result

    lines = _LOG.read_text(encoding="utf-8").splitlines()
    tool_counter: Counter = Counter()
    recent: list[dict] = []

    for line in lines:
        if line.startswith("["):
            try:
                ts_end = line.index("]")
                ts = line[1:ts_end]
                rest = line[ts_end + 2:]
            except ValueError:
                continue  # malformed line — skip

            if rest.startswith("TOOL "):
                result["tool_calls"] += 1
                # Extract tool name
                parts = rest[5:].split("(", 1)
                if parts:
                    tool_name = parts[0].strip()
                    tool_counter[tool_name] += 1
                    recent.append({"type": "tool", "name": tool_name, "ts": ts})
            elif rest.startswith("MODEL "):
                recent.append({"type": "model", "ts": ts})
            elif rest.startswith("GATE "):
                if "GRANTED" in rest:
                    result["gate_granted"] += 1
                    recent.append({"type": "gate", "verdict": "granted", "ts": ts})
                elif "DENIED" in rest:
                    result["gate_denied"] += 1
                    recent.append({"type": "gate", "verdict": "denied", "ts": ts})
            elif rest.startswith("HEARTBEAT "):
                result["heartbeat_notices"] += 1
                recent.append({"type": "heartbeat", "ts": ts})
            elif rest.startswith("KILL_SWITCH "):
                result["kill_switch_events"] += 1
                recent.append({"type": "kill_switch", "ts": ts})

    result["tool_breakdown"] = dict(tool_counter.most_common(20))
    result["recent_events"] = recent[-30:]
    return result


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
