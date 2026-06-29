"""Sub-agent dispatch tool — lets the lead agent spawn a specialist sub-agent.

The lead agent calls this tool with a task and an agent name. The sub-agent
runs with its own SOUL (system prompt + tool whitelist) and isolated history.
The result goes back to the lead agent as the tool result.

Sub-agents can't ask the user for confirmation — they run autonomously and
report back. If a sub-agent's tools require confirmation, those tools are
simply not available to it (the whitelist excludes them).
"""

from __future__ import annotations

from dela.tools import register


def _get_agents():
    """Deferred import to avoid circular dependency (agents -> tools -> subagent -> agents)."""
    from dela.agents import get_agent, list_agents
    return get_agent, list_agents


def _get_brain():
    from dela.brain import run_subagent
    return run_subagent


@register(
    name="dispatch_subagent",
    description=(
        "Dispatch a specialist sub-agent to handle a complex, multi-step task. "
        "The sub-agent runs autonomously with its own tools and reports back a summary. "
        "Use this when a task needs focused research or multi-step tool use that you "
        "don't want to handle turn-by-turn."
    ),
    parameters={
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "description": "The name of the sub-agent to dispatch. Available agents will be listed.",
            },
            "task": {
                "type": "string",
                "description": "A clear description of what the sub-agent should do.",
            },
        },
        "required": ["agent", "task"],
    },
)
def dispatch_subagent(args: dict) -> str:
    get_agent, list_agents = _get_agents()
    run_subagent = _get_brain()

    agent_name = args["agent"]
    task = args["task"]

    soul = get_agent(agent_name)
    if soul is None:
        return f"No sub-agent named '{agent_name}'. Available: {', '.join(a.name for a in list_agents())}"

    # Record this routing decision in the cache for future lookups
    from dela.routing_cache import record as _record_route
    _record_route(task, agent_name, target_type="agent")

    prompt = soul.build_prompt()
    result = run_subagent(
        agent_name=agent_name,
        task=task,
        system_prompt_text=prompt,
        tool_whitelist=soul.tool_whitelist,
    )
    return f"[Sub-agent '{agent_name}' result]:\n{result}"


@register(
    name="dispatch_system_expert",
    description=(
        "Dispatch the system_expert sub-agent to answer architecture questions, "
        "advise on where to add new features, inspect the codebase, or implement "
        "new capabilities (tools, agents, skills, channels, checks). Use this when "
        "the user wants to extend Dela, understand its internals, or asks 'how does "
        "X work' about Dela's own code. The system expert knows every module, seam, "
        "and pattern, and can write code via run_code."
    ),
    parameters={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "The architecture question, feature request, or implementation task for the system expert.",
            },
        },
        "required": ["task"],
    },
)
def dispatch_system_expert(args: dict) -> str:
    return dispatch_subagent({"agent": "system_expert", "task": args["task"]})