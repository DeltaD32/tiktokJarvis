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

    # Track agent status
    from dela.agent_status import mark_busy, mark_ready, mark_error
    mark_busy(agent_name, task)

    prompt = soul.build_prompt()
    try:
        result = run_subagent(
            agent_name=agent_name,
            task=task,
            system_prompt_text=prompt,
            tool_whitelist=soul.tool_whitelist,
        )
        mark_ready(agent_name)
        return f"[Sub-agent '{agent_name}' result]:\n{result}"
    except Exception as e:
        mark_error(agent_name, str(e))
        raise


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


@register(
    name="dispatch_parallel",
    description=(
        "Dispatch MULTIPLE specialist sub-agents in PARALLEL to work on related tasks "
        "simultaneously. Provide a list of {agent, task} pairs. All agents start at once "
        "and results are collected into a combined report. Use this when you need multiple "
        "agents working concurrently — e.g., researcher fetching external data while "
        "system_expert inspects code, or presenter designing slides while secretary "
        "coordinates. Each agent runs with its own tools and isolated context. "
        "Results are interleaved with [agent-name] headers."
    ),
    parameters={
        "type": "object",
        "properties": {
            "jobs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "agent": {"type": "string", "description": "Sub-agent name to dispatch"},
                        "task": {"type": "string", "description": "What this sub-agent should do"},
                    },
                    "required": ["agent", "task"],
                },
                "description": "List of {agent, task} pairs to run in parallel",
            },
        },
        "required": ["jobs"],
    },
)
def dispatch_parallel(args: dict) -> str:
    """Run multiple sub-agents in parallel threads and collect their results."""
    import concurrent.futures
    import threading

    get_agent, list_agents = _get_agents()
    run_subagent = _get_brain()
    from dela.agent_status import mark_busy, mark_ready, mark_error

    jobs = args.get("jobs", [])
    if not jobs:
        return "[error] No jobs provided to dispatch_parallel"

    results: dict[str, str] = {}
    errors: list[str] = []

    def _run_job(agent_name: str, task: str) -> None:
        soul = get_agent(agent_name)
        if soul is None:
            errors.append(f"No sub-agent named '{agent_name}'")
            return
        from dela.routing_cache import record as _record_route
        _record_route(task, agent_name, target_type="agent")
        mark_busy(agent_name, task)
        prompt = soul.build_prompt()
        try:
            result = run_subagent(
                agent_name=agent_name,
                task=task,
                system_prompt_text=prompt,
                tool_whitelist=soul.tool_whitelist,
            )
            results[agent_name] = result
            mark_ready(agent_name)
        except Exception as e:
            mark_error(agent_name, str(e))
            errors.append(f"[{agent_name}] {e}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as executor:
        futures = []
        for job in jobs:
            futures.append(executor.submit(_run_job, job["agent"], job["task"]))

        # Wait for all to complete
        concurrent.futures.wait(futures)

    # Build combined report
    parts = []
    if results:
        parts.append(f"=== Parallel sub-agent report ({len(results)} completed) ===")
        for i, job in enumerate(jobs):
            agent_name = job["agent"]
            if agent_name in results:
                parts.append(f"\n--- [{agent_name}] ---\n{results[agent_name]}")
    if errors:
        parts.append(f"\n--- Errors ---\n" + "\n".join(errors))
    return "\n".join(parts)