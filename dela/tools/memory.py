"""Memory tools — let the model record, update, and forget durable facts.

These are the model's way of managing its own long-term memory as it learns.
Adding/updating a fact is consequential (it shapes future behavior), so these
require confirmation — the user stays in control of what gets remembered.
"""

from __future__ import annotations

from dela import memory
from dela.tools import register


@register(
    name="remember_fact",
    description="Store a durable fact about the user or their world — a preference, identity, or decision. Use this when the user tells you something worth remembering across conversations. Each fact is one plain statement. Confirm with the user before storing.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "One plain statement of the fact, e.g. 'The user prefers morning meetings.'",
            },
            "category": {
                "type": "string",
                "description": "A short category: 'preference', 'identity', 'decision', 'project', or 'general'.",
                "enum": ["preference", "identity", "decision", "project", "general"],
            },
        },
        "required": ["text"],
    },
    requires_confirmation=True,
)
def remember_fact(args: dict) -> str:
    text = args["text"].strip()
    if not text:
        return "Can't remember an empty fact."
    category = args.get("category", "general")
    fact = memory.add(text, category)
    return f"Remembered (fact {fact['id']}): {fact['text']}"


@register(
    name="update_fact",
    description="Update an existing stored fact by its id when the user corrects or refines something you already know. Confirm the change with the user.",
    parameters={
        "type": "object",
        "properties": {
            "id": {"type": "integer", "description": "The numeric id of the fact to update."},
            "text": {"type": "string", "description": "The new plain statement for this fact."},
        },
        "required": ["id", "text"],
    },
    requires_confirmation=True,
)
def update_fact(args: dict) -> str:
    fact = memory.update(args["id"], args["text"].strip())
    if fact is None:
        return f"No fact with id {args['id']}. Use remember_fact to add a new one."
    return f"Updated fact {fact['id']}: {fact['text']}"


@register(
    name="forget_fact",
    description="Remove a stored fact by its id when the user tells you something is no longer true or relevant. Confirm which fact before forgetting.",
    parameters={
        "type": "object",
        "properties": {
            "id": {"type": "integer", "description": "The numeric id of the fact to forget."},
        },
        "required": ["id"],
    },
    requires_confirmation=True,
)
def forget_fact(args: dict) -> str:
    if memory.remove(args["id"]):
        return f"Forgot fact {args['id']}."
    return f"No fact with id {args['id']}."
