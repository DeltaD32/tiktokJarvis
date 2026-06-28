"""Routing cache tools — let the model check and manage the routing cache."""

from __future__ import annotations

from dela.routing_cache import lookup, status_text, clear
from dela.tools import register


@register(
    name="check_routing_cache",
    description=(
        "Check if a similar past request was routed to a specific agent or skill. "
        "Returns the cached routing decision if the similarity is above threshold. "
        "Use this to skip deliberation on repeated or similar requests. Read-only."
    ),
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "The request to look up."},
        },
        "required": ["prompt"],
    },
)
def check_routing_cache(args: dict) -> str:
    result = lookup(args["prompt"])
    if result is None:
        return "No cached routing match found. Proceed with normal deliberation."
    return (
        f"Cache hit (similarity: {result['similarity']}): "
        f"route to {result['target_type']} '{result['target']}' "
        f"(matched past prompt: \"{result['cached_prompt'][:80]}...\")"
    )


@register(
    name="routing_cache_status",
    description="Show the routing cache statistics — number of entries and routes by target. Read-only.",
    parameters={"type": "object", "properties": {}},
)
def routing_cache_status(args: dict) -> str:
    return status_text()