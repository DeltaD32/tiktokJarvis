"""The confirmation gate — stops consequential actions until the user says yes.

Any tool flagged `requires_confirmation=True` must pass through here before it
runs. The gate asks the user via a pluggable `Confirmer` — text mode prints and
reads input, voice mode speaks and listens, heartbeat mode times out into a
safe default (do nothing, leave a note). The gate sits between the model
choosing a tool and the tool running, so it covers spoken, typed, and
heartbeat-initiated actions alike.

Confirmation is per-action and never generalizes: one yes doesn't
pre-authorize the next. Each consequential action asks on its own.
"""

from __future__ import annotations

import threading
import time
from typing import Protocol


class Confirmer(Protocol):
    def confirm(self, description: str, timeout: float | None = None) -> bool:
        """Ask the user to confirm an action. Returns True on explicit yes."""
        ...


class TextConfirmer:
    """Print what's about to happen, wait for a yes/no from stdin."""

    def confirm(self, description: str, timeout: float | None = None) -> bool:
        print(f"\n  [confirmation needed] {description}")
        try:
            answer = input("  Allow? (yes/no) > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer in ("yes", "y", "yeah", "ok", "sure", "go ahead")


class SilentConfirmer:
    """Auto-deny everything. Used when no human is present (heartbeat-only runs)."""

    def confirm(self, description: str, timeout: float | None = None) -> bool:
        return False


class TimeoutConfirmer:
    """Wrap a confirmer with a timeout — if the human doesn't answer in time,
    default to deny. This is the "never block forever waiting on a human" rule.
    """

    def __init__(self, inner: Confirmer, default_timeout: float = 30.0) -> None:
        self._inner = inner
        self._default_timeout = default_timeout

    def confirm(self, description: str, timeout: float | None = None) -> bool:
        t = timeout if timeout is not None else self._default_timeout
        result = {"v": False}
        done = threading.Event()

        def _ask() -> None:
            result["v"] = self._inner.confirm(description, timeout=t)
            done.set()

        thread = threading.Thread(target=_ask, daemon=True)
        thread.start()
        if not done.wait(t):
            return False  # timed out — safe default is deny
        return result["v"]


# The active confirmer, set by the entry point. Defaults to silent (deny all)
# so the brain is safe to use without an interactive entry point (e.g. tests).
_active: Confirmer = SilentConfirmer()


def set_confirmer(confirmer: Confirmer) -> None:
    global _active
    _active = confirmer


def get_confirmer() -> Confirmer:
    return _active


def ask(tool_name: str, description: str) -> bool:
    """Ask the user to confirm a consequential tool action.

    Returns True only on an explicit yes. Per-action — one yes never
    pre-authorizes the next call.
    """
    return _active.confirm(f"{tool_name}: {description}")
