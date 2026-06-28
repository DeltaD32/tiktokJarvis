"""Status events tools — let the model view the project/blackboard timeline."""

from __future__ import annotations

from dela.status_events import timeline, timeline_text, for_entity
from dela.tools import register


@register(
    name="get_timeline",
    description=(
        "Get the event timeline for a project, blackboard, or entity. Shows all "
        "lifecycle transitions (created, status changes, dispatches, decisions, "
        "completions) in chronological order. Use this to review how a project "
        "evolved or to check the history of a specific blackboard. Read-only."
    ),
    parameters={
        "type": "object",
        "properties": {
            "entity_id": {
                "type": "string",
                "description": "The project ID or blackboard ID to get the timeline for. Leave empty for recent events.",
            },
        },
    },
)
def get_timeline(args: dict) -> str:
    entity_id = args.get("entity_id", "")
    if entity_id:
        return timeline(entity_id)
    return timeline_text(30)