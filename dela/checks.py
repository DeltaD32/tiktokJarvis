"""Scheduled checks for the heartbeat.

Each check is a small unit: what to look at, and how to decide whether the
outcome is worth surfacing. A check returns a notice dict (source, message,
severity) or None. The heartbeat handles when to run; the check handles what
to look at. Adding a new check = one function + a line in heartbeat_config.json.

Checks must be idempotent and never block forever on a human — they run in a
background thread. Network timeouts are bounded.
"""

from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from typing import Any

from dela import noticeboard
from dela.tools.project import _load as _load_tasks


def _check_systems_health(params: dict[str, Any]) -> dict | None:
    """Ping configured targets; file a notice if any are down."""
    targets = params.get("targets", [])
    if not targets:
        return None
    down = []
    for target in targets:
        if target.startswith(("http://", "https://")):
            try:
                req = urllib.request.Request(target, method="HEAD", headers={"User-Agent": "Dela/0.1"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status >= 400:
                        down.append(f"{target} (HTTP {resp.status})")
            except Exception as e:
                down.append(f"{target} ({e})")
        else:
            host, _, port = target.partition(":")
            try:
                port_i = int(port) if port else 80
                with socket.create_connection((host, port_i), timeout=10):
                    pass
            except Exception as e:
                down.append(f"{target} ({e})")

    if not down:
        return None
    msg = "Systems check: " + "; ".join(down) + " — unreachable."
    sev = noticeboard.URGENT if len(down) == len(targets) else noticeboard.ATTENTION
    return {"source": "systems_health", "message": msg, "severity": sev}


def _check_tasks_due(params: dict[str, Any]) -> dict | None:
    """Surface open tasks due within the look-ahead window."""
    look_ahead_h = float(params.get("look_ahead_hours", 24))
    now = time.time()
    horizon = now + look_ahead_h * 3600
    tasks = _load_tasks()
    due_soon = []
    for t in tasks:
        if t.get("status") != "open":
            continue
        due = t.get("due", "n/a")
        if due == "n/a":
            continue
        try:
            due_ts = time.mktime(time.strptime(due, "%Y-%m-%d"))
        except ValueError:
            continue
        if due_ts <= horizon:
            if due_ts < now:
                due_soon.append(f"'{t['title']}' is OVERDUE (was {due})")
            else:
                due_soon.append(f"'{t['title']}' is due {due}")

    if not due_soon:
        return None
    msg = "Task reminder: " + "; ".join(due_soon) + "."
    sev = noticeboard.ATTENTION if any("OVERDUE" in d for d in due_soon) else noticeboard.INFO
    return {"source": "tasks_due", "message": msg, "severity": sev}


# Registry of check name -> function.
CHECKS: dict[str, Any] = {
    "systems_health": _check_systems_health,
    "tasks_due": _check_tasks_due,
}
