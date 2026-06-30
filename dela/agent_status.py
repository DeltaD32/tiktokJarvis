"""Agent status tracker — tracks whether each sub-agent is ready, busy, or errored.

Agents are dispatched on-demand (not running continuously), so status is:
  - "ready":  agent is idle and available for dispatch
  - "busy":   agent is currently executing a task
  - "error":  agent's last run failed

Status is tracked in-memory (no persistence needed — resets on restart).
The dispatch_subagent tool updates status before/after each run.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

_lock = threading.Lock()
_status: dict[str, dict] = {}
_listeners: list = []  # callbacks(name, state, task) on status change

def on_change(cb) -> None:
    _listeners.append(cb)

def _notify(name: str, state: str, task: str = "") -> None:
    for cb in _listeners:
        try: cb(name, state, task)
        except Exception: pass


@dataclass
class AgentStatus:
    name: str
    state: str = "ready"
    last_task: str = ""
    last_dispatch: float = 0.0
    dispatch_count: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "last_task": self.last_task,
            "last_dispatch_ago_s": round(time.time() - self.last_dispatch, 1) if self.last_dispatch else None,
            "dispatch_count": self.dispatch_count,
        }


_agents: dict[str, AgentStatus] = {}


def _ensure(name: str) -> AgentStatus:
    with _lock:
        if name not in _agents:
            _agents[name] = AgentStatus(name=name)
        return _agents[name]


def mark_busy(name: str, task: str) -> None:
    s = _ensure(name)
    with _lock:
        s.state = "busy"
        s.last_task = task
        s.last_dispatch = time.time()
        s.dispatch_count += 1
    _notify(name, "busy", task)


def mark_ready(name: str) -> None:
    s = _ensure(name)
    with _lock:
        s.state = "ready"
    _notify(name, "ready")


def mark_error(name: str, error: str) -> None:
    s = _ensure(name)
    with _lock:
        s.state = "error"
        s.last_task = f"ERROR: {error[:120]}"
    _notify(name, "error", error[:120])


def get_status(name: str) -> str:
    s = _ensure(name)
    with _lock:
        return s.state


def all_status() -> dict[str, dict]:
    """Return status for all known agents."""
    with _lock:
        return {name: agent.to_dict() for name, agent in _agents.items()}


def init_agents(agent_names: list[str]) -> None:
    """Initialize status for all registered agents."""
    for name in agent_names:
        _ensure(name)
