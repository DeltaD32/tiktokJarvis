"""Agent memory tools — let the model recall and record experiential learnings.

These tools bridge the agent_memory module to the model. The lead agent can
recall an agent's learnings before dispatching it, and record new learnings
when a sub-agent returns with insights.
"""

from __future__ import annotations

from dela.agent_memory import WORKED, AVOID, PATTERN, recall_as_prompt, learn, get_agent_memory_status
from dela.tools import register


@register(
    name="recall_agent_memory",
    description=(
        "Recall what a sub-agent has learned from past tasks — approaches that worked, "
        "things to avoid, and reusable patterns. Use this BEFORE dispatching a sub-agent "
        "to inject its experience into the task. The recalled learnings make the agent "
        "smarter on similar tasks. Read-only."
    ),
    parameters={
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "description": "The agent name (e.g. 'researcher', 'presenter', 'secretary').",
            },
            "domain": {
                "type": "string",
                "description": "Optional domain filter (e.g. 'api-design', 'pptx').",
            },
        },
        "required": ["agent"],
    },
)
def recall_agent_memory(args: dict) -> str:
    agent = args["agent"]
    domain = args.get("domain", "")
    prompt = recall_as_prompt(agent, domain=domain)
    return prompt if prompt else f"No learnings recorded for agent '{agent}' yet."


@register(
    name="record_agent_learning",
    description=(
        "Record a learning for a sub-agent — what worked, what to avoid, or a reusable "
        "pattern. Use this AFTER a sub-agent returns with insights, to capture the "
        "experience for future tasks. Each learning has a type and a one-sentence content. "
        "Requires confirmation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "agent": {"type": "string", "description": "The agent name."},
            "learning_type": {
                "type": "string",
                "enum": ["worked", "avoid", "pattern"],
                "description": "Type of learning.",
            },
            "content": {
                "type": "string",
                "description": "One clear sentence describing the learning.",
            },
            "domain": {
                "type": "string",
                "description": "Optional domain tag (e.g. 'api-design').",
            },
        },
        "required": ["agent", "learning_type", "content"],
    },
    requires_confirmation=True,
)
def record_agent_learning(args: dict) -> str:
    entry = learn(
        agent=args["agent"],
        learning_type=args["learning_type"],
        content=args["content"],
        domain=args.get("domain", ""),
    )
    return f"Learning recorded for '{args['agent']}': [{args['learning_type'].upper()}] {args['content']}"


@register(
    name="get_agent_memory_status",
    description=(
        "Check the memory status of an agent — how many learnings, by type, and "
        "average decay score. Use this to see if an agent has accumulated experience. "
        "Read-only."
    ),
    parameters={
        "type": "object",
        "properties": {
            "agent": {"type": "string", "description": "The agent name."},
        },
        "required": ["agent"],
    },
)
def get_agent_memory_status_tool(args: dict) -> str:
    return get_agent_memory_status(args["agent"])