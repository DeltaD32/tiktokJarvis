"""Heartbeat tools — let the model check on proactive status and surface things.

The model can list pending notices and dismiss ones it's relayed. This bridges
the heartbeat (background) and the conversation (foreground): when a user asks
"did anything come up?", the model can pull from the noticeboard.
"""

from __future__ import annotations

from dela import noticeboard
from dela.tools import register


@register(
    name="list_notices",
    description="List pending proactive notices — things the heartbeat noticed while you were away or busy. Use this when the user asks if anything came up, what they missed, or what Dela noticed. Read-only.",
    parameters={
        "type": "object",
        "properties": {
            "include_dismissed": {
                "type": "boolean",
                "description": "If true, include already-dismissed notices too. Default false.",
            }
        },
    },
)
def list_notices(args: dict) -> str:
    include = args.get("include_dismissed", False)
    if include:
        ns = noticeboard.all()
    else:
        ns = noticeboard.active()
    if not ns:
        return "No pending notices."
    lines = [f"- [{n['id']}|{n['severity']}] {n['message']}" for n in ns]
    return f"{len(ns)} notice(s):\n" + "\n".join(lines)


@register(
    name="dismiss_notice",
    description="Dismiss a proactive notice by its id once it's been addressed or relayed to the user. Confirm which notice before dismissing.",
    parameters={
        "type": "object",
        "properties": {
            "id": {"type": "integer", "description": "The numeric id of the notice to dismiss."},
        },
        "required": ["id"],
    },
    requires_confirmation=True,
)
def dismiss_notice(args: dict) -> str:
    if noticeboard.dismiss(args["id"]):
        return f"Dismissed notice {args['id']}."
    return f"No notice with id {args['id']}."
