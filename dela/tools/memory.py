"""Memory tools — let the model record, update, query, and forget durable facts."""
from __future__ import annotations

from dela import memory
from dela.tools import register


@register(
    name="remember_fact",
    description=(
        "Store a durable fact about the user or their world. "
        "Each fact is one plain statement. Skips duplicates automatically."
    ),
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The fact statement, e.g. 'The user prefers morning meetings.'"},
            "category": {"type": "string", "description": "Category: preference, identity, decision, project, or general.",
                         "enum": ["preference", "identity", "decision", "project", "general"]},
        },
        "required": ["text"],
    },
    requires_confirmation=False,
)
def remember_fact(args: dict) -> str:
    text = args["text"].strip()
    if not text:
        return "Can't remember an empty fact."
    category = args.get("category", "general")
    fact = memory.add(text, category)
    if fact.get("duplicate"):
        return f"Already know: {fact['text'][:80]}"
    if fact.get("error"):
        return fact["error"]
    return f"Remembered (fact {fact['id']}): {fact['text']}"


@register(
    name="update_fact",
    description="Update an existing stored fact by its id.",
    parameters={
        "type": "object",
        "properties": {
            "id": {"type": "integer", "description": "The numeric id of the fact to update."},
            "text": {"type": "string", "description": "The new plain statement for this fact."},
        },
        "required": ["id", "text"],
    },
    requires_confirmation=False,
)
def update_fact(args: dict) -> str:
    fact = memory.update(args["id"], args["text"].strip())
    if fact is None:
        return f"No fact with id {args['id']}. Use remember_fact to add a new one."
    return f"Updated fact {fact['id']}: {fact['text']}"


@register(
    name="forget_fact",
    description="Remove a stored fact by its id.",
    parameters={
        "type": "object",
        "properties": {
            "id": {"type": "integer", "description": "The numeric id of the fact to forget."},
        },
        "required": ["id"],
    },
    requires_confirmation=False,
)
def forget_fact(args: dict) -> str:
    if memory.remove(args["id"]):
        return f"Forgot fact {args['id']}."
    return f"No fact with id {args['id']}."


@register(
    name="list_facts",
    description="List stored facts, optionally filtered by category.",
    parameters={
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "Optional category filter."},
        },
        "required": [],
    },
    requires_confirmation=False,
)
def list_facts(args: dict) -> str:
    category = args.get("category")
    facts = memory.list_facts(category=category)
    if not facts:
        return "No facts stored" + (f" under category '{category}'." if category else " yet.")
    lines = [f"  [{f['id']}] [{f['category']}] {f['text']}" for f in facts]
    return "Stored facts:\n" + "\n".join(lines)


@register(
    name="search_facts",
    description="Search stored facts by text query. Returns best matches first.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term or phrase."},
            "category": {"type": "string", "description": "Optional category to narrow search."},
        },
        "required": ["query"],
    },
    requires_confirmation=False,
)
def search_facts(args: dict) -> str:
    query = args["query"].strip()
    category = args.get("category")
    results = memory.search_facts(query, category=category)
    if not results:
        return f"No facts found matching '{query}'."
    lines = [f"  [{f['id']}] [{f['category']}] {f['text']}" for f in results]
    return f"Facts matching '{query}':\n" + "\n".join(lines)
