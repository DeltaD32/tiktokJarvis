"""UI tools — let Dela open panels in the web frontend to show progress.

These tools are no-ops when no frontend is connected (broadcast_fn is None).
The server sets _broadcast_fn on startup so tool calls reach connected clients.
"""
from __future__ import annotations

from typing import Callable

from dela.tools import register

# Set by dela.server on startup. None when running headless (text/voice CLI).
_broadcast_fn: Callable[[dict], None] | None = None


def _broadcast(payload: dict) -> None:
    if _broadcast_fn is not None:
        _broadcast_fn(payload)


@register(
    name="show_panel",
    description=(
        "Open a UI panel in the frontend to show the user relevant information. "
        "Use 'tasks' to show the task list, 'notices' for proactive notices, "
        "'audit' for the recent activity log, 'memory' for stored facts, "
        "'tools' for the tool browser, 'analytics' for usage stats, "
        "'security' for the security audit, or 'state' for the state browser."
    ),
    parameters={
        "type": "object",
        "properties": {
            "panel": {
                "type": "string",
                "enum": ["tasks", "notices", "audit", "memory", "tools", "analytics", "security", "state"],
                "description": "Which panel to open.",
            },
            "message": {
                "type": "string",
                "description": "Optional headline message to show at the top of the panel.",
            },
        },
        "required": ["panel"],
    },
    requires_confirmation=False,
)
def show_panel(args: dict) -> str:
    panel = args["panel"]
    message = args.get("message", "")
    _broadcast({"type": "open_panel", "panel": panel, "message": message})
    return f"Opened {panel} panel{': ' + message if message else ''}."
