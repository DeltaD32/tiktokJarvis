"""The heartbeat — a background loop that lets Dela act without being spoken to.

Separate from the conversation loop. Wakes up on an interval, runs scheduled
checks that are due, and files anything noteworthy to the noticeboard. The
noticeboard holds notices for the user; the entry point surfaces them on return.

Principles baked in from the start:
  - Quiet by default. Most checks produce nothing most of the time. Only
    urgent notices earn an interruption; the rest accumulate in the calm log.
  - Don't drop what I wasn't there to see. Notices are durable — held until
    dismissed. Catch-up-on-return, never deliver-once-and-lose-it.
  - Respect quiet hours. Non-urgent surfacing waits for waking hours.
  - Never block forever waiting on a human. Checks time out into safe defaults.
  - Survive restarts. The schedule is persisted; restarting doesn't reset
    timers or fire everything at once.
  - Don't pile up overlapping runs. If a check is still working when its next
    turn comes, skip the new run.
  - Kill switch. One call pauses all proactive behavior.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime

from dela import audit, gate, hb_config, noticeboard, schedule
from dela.checks import CHECKS

_thread: threading.Thread | None = None
_stop = threading.Event()
_killed = threading.Event()  # kill switch — pauses everything until cleared
_running: set[str] = set()  # checks currently running (no overlap)
_lock = threading.Lock()


def start() -> None:
    """Start the heartbeat in a background thread. No-op if already running."""
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    # Heartbeat runs with no human present — consequential actions auto-deny.
    # The brain's gate uses whatever confirmer the entry point set; if the
    # heartbeat ever triggers a turn (Tier 5+), it must use SilentConfirmer.
    _thread = threading.Thread(target=_loop, daemon=True, name="dela-heartbeat")
    _thread.start()


def stop() -> None:
    """Stop the heartbeat (graceful — finishes the current tick)."""
    _stop.set()


def kill() -> None:
    """Kill switch — pause all proactive behavior immediately."""
    _killed.set()
    audit.kill_switch("paused")


def resume() -> None:
    """Clear the kill switch — proactive behavior resumes."""
    _killed.clear()
    audit.kill_switch("resumed")


def is_killed() -> bool:
    return _killed.is_set()


def _in_quiet_hours(now: datetime | None = None) -> bool:
    cfg = hb_config.load()
    qh = cfg.get("quiet_hours", {})
    if not qh.get("enabled", False):
        return False
    now = now or datetime.now()
    start_h, start_m = (int(x) for x in qh["start"].split(":"))
    end_h, end_m = (int(x) for x in qh["end"].split(":"))
    cur = now.hour * 60 + now.minute
    s = start_h * 60 + start_m
    e = end_h * 60 + end_m
    if s <= e:
        return s <= cur < e
    # wraps midnight (e.g. 22:00 - 08:00)
    return cur >= s or cur < e


def _loop() -> None:
    while not _stop.is_set():
        if _killed.is_set():
            _stop.wait(5)
            continue

        try:
            _tick()
        except Exception:
            # The heartbeat must never die — a bad check shouldn't kill the loop.
            pass

        cfg = hb_config.load()
        interval = float(cfg.get("heartbeat_interval_seconds", 30))
        _stop.wait(interval)


def _tick() -> None:
    cfg = hb_config.load()
    checks_cfg = cfg.get("checks", {})
    now = time.time()

    for name, params in checks_cfg.items():
        if not params.get("enabled", False):
            continue
        if name not in CHECKS:
            continue
        if not schedule.is_due(name, now):
            continue

        with _lock:
            if name in _running:
                continue  # still working from last tick — skip, don't stack
            _running.add(name)

        interval = float(params.get("interval_seconds", 300))
        # Mark next due before running so a slow check doesn't snowball.
        schedule.mark_run(name, interval, now)

        try:
            result = CHECKS[name](params)
        except Exception as e:
            result = {
                "source": name,
                "message": f"Check '{name}' errored: {e}",
                "severity": noticeboard.INFO,
            }
        finally:
            with _lock:
                _running.discard(name)

        if result is not None:
            # In quiet hours, downgrade non-urgent notices to info (calm log).
            # Urgent notices still file — they just won't interrupt until waking hours.
            sev = result.get("severity", noticeboard.INFO)
            if _in_quiet_hours() and sev != noticeboard.URGENT:
                sev = noticeboard.INFO
            noticeboard.file(
                source=result["source"],
                message=result["message"],
                severity=sev,
            )
            audit.heartbeat_notice(result["source"], result["message"], sev)
