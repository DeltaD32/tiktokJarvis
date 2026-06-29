"""State browser tools — let the model inspect, search, and edit all state."""

from __future__ import annotations

from dela.tools import register


@register(
    name="search_state",
    description=(
        "Search across ALL of Dela's state — memory, projects, blackboards, sessions, "
        "workflows, agent memory, notices, tasks, routing cache, audit log, events. "
        "Use this when the user asks 'what do you remember about X' or 'search for Y' "
        "or wants to find something across all stored data. Returns matching items "
        "with their type, ID, and a snippet. Read-only."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."},
            "limit": {"type": "integer", "description": "Max results (default 20)."},
        },
        "required": ["query"],
    },
)
def search_state_tool(args: dict) -> str:
    from dela.state_browser import search_state
    results = search_state(args["query"], limit=args.get("limit", 20))
    if not results:
        return f"No results found for '{args['query']}' across all state."
    lines = [f"Found {len(results)} match(es) for '{args['query']}':"]
    for r in results:
        snippet = r.get("snippet", "")[:150]
        lines.append(f"  [{r['type']}] {r.get('id', r.get('line', '?'))}: {snippet}")
    return "\n".join(lines)


@register(
    name="list_state_types",
    description=(
        "List all state types Dela manages, with item counts. Use this when the user "
        "wants to see what data Dela is storing or get an overview of all state. Read-only."
    ),
    parameters={"type": "object", "properties": {}},
)
def list_state_types_tool(args: dict) -> str:
    from dela.state_browser import list_state_types
    types = list_state_types()
    lines = ["Dela state types:"]
    for t in types:
        lines.append(f"  {t['type']} ({t['items']} items): {t['description']}")
    return "\n".join(lines)


@register(
    name="read_state",
    description=(
        "Read a specific state type (memory, projects, blackboards, sessions, workflows, "
        "agent_memory, notices, tasks, routing, audit, events, cost, styles). Optionally "
        "read a specific item by ID. Use this when the user wants to inspect stored data. "
        "Read-only."
    ),
    parameters={
        "type": "object",
        "properties": {
            "state_type": {"type": "string", "description": "The state type to read."},
            "item_id": {"type": "string", "description": "Optional: specific item ID to read."},
        },
        "required": ["state_type"],
    },
)
def read_state_tool(args: dict) -> str:
    from dela.state_browser import read_state
    import json
    result = read_state(args["state_type"], item_id=args.get("item_id"))
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)[:2000]