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
        "Use 'report' to display a structured report with custom content and a title. "
        "Use 'tasks', 'notices', 'audit', 'memory', 'tools', 'analytics', "
        "'security', 'state', or 'workflows' for standard panels."
    ),
    parameters={
        "type": "object",
        "properties": {
            "panel": {
                "type": "string",
                "enum": ["report", "tasks", "notices", "audit", "memory", "tools", "analytics", "security", "state", "workflows"],
                "description": "Which panel to open. Use 'report' for structured analysis reports with custom content.",
            },
            "message": {
                "type": "string",
                "description": "Optional headline message to show at the top of the panel.",
            },
            "content": {
                "type": "string",
                "description": "For 'report' panel: the full report content (markdown-formatted). Required when panel='report'.",
            },
            "title": {
                "type": "string",
                "description": "For 'report' panel: the report title.",
            },
        },
        "required": ["panel"],
    },
    requires_confirmation=False,
)
def show_panel(args: dict) -> str:
    panel = args["panel"]
    message = args.get("message", "")
    payload: dict = {"type": "open_panel", "panel": panel, "message": message}
    if panel == "report":
        payload["content"] = args.get("content", "")
        payload["title"] = args.get("title", "Report")
    _broadcast(payload)
    return f"Opened {panel} panel{': ' + message if message else ''}."
