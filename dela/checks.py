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


def _check_blackboard_cleanup(params: dict[str, Any]) -> dict | None:
    """Distill and clean up completed blackboards. Files a notice if anything was cleaned."""
    from dela.blackboard_memory import cleanup_completed_blackboards, cleanup_old_blackboards

    completed = cleanup_completed_blackboards()
    old = cleanup_old_blackboards()

    distilled = completed.get("distilled", 0)
    deleted = old.get("deleted", 0)

    if distilled == 0 and deleted == 0:
        return None  # nothing to report — quiet by default

    msg_parts = []
    if distilled:
        msg_parts.append(f"distilled {distilled} completed blackboard(s) into project memory")
    if deleted:
        msg_parts.append(f"cleaned up {deleted} old archived blackboard(s)")
    msg = "Blackboard cleanup: " + " and ".join(msg_parts) + "."

    return {"source": "blackboard_cleanup", "message": msg, "severity": noticeboard.INFO}


def _check_scheduled_workflows(params: dict[str, Any]) -> dict | None:
    """Run any workflows whose cron schedule is due. Files a notice if any ran."""
    import json
    from pathlib import Path
    from dela.workflows import _WORKFLOWS_DIR, load_workflow, execute_workflow
    from dela.schedule import is_due, mark_run

    if not _WORKFLOWS_DIR.exists():
        return None

    ran = []
    for path in _WORKFLOWS_DIR.glob("*.json"):
        try:
            wf = json.loads(path.read_text(encoding="utf-8"))
            schedule = wf.get("schedule", "")
            if not schedule:
                continue

            wf_key = f"workflow:{wf.get('name', path.stem)}"
            if not is_due(wf_key):
                continue

            # Mark next due (parse cron — simplified: assume interval in seconds or cron expr)
            # For simplicity, use a fixed 3600s interval if cron parsing isn't available
            mark_run(wf_key, 3600)

            # Execute the workflow
            result = execute_workflow(wf.get("name", path.stem))
            ran.append({
                "name": wf.get("name", path.stem),
                "completed": result.get("completed", 0),
                "failed": result.get("failed", 0),
            })
        except Exception:
            pass

    if not ran:
        return None

    msg = "Scheduled workflows ran: " + ", ".join(
        f"{r['name']} ({r['completed']} done)" for r in ran
    )
    return {"source": "scheduled_workflows", "message": msg, "severity": noticeboard.INFO}


def _check_security_scan(params: dict[str, Any]) -> dict | None:
    """Run a security scan and file a notice if critical findings are detected."""
    from dela.security import run_full_scan

    report = run_full_scan()
    critical = report["summary"]["critical"]
    warning = report["summary"]["warning"]

    if critical > 0:
        crit_titles = [f["title"] for f in report["findings"] if f["severity"] == "critical"]
        msg = f"Security scan found {critical} critical issue(s): {'; '.join(crit_titles[:3])}"
        return {"source": "security_scan", "message": msg, "severity": noticeboard.URGENT}
    elif warning > 0:
        msg = f"Security scan found {warning} warning(s). Score: {report['score']}/100."
        return {"source": "security_scan", "message": msg, "severity": noticeboard.ATTENTION}
    return None


# Registry of check name -> function.
CHECKS: dict[str, Any] = {
    "systems_health": _check_systems_health,
    "tasks_due": _check_tasks_due,
    "blackboard_cleanup": _check_blackboard_cleanup,
    "scheduled_workflows": _check_scheduled_workflows,
    "security_scan": _check_security_scan,
}
