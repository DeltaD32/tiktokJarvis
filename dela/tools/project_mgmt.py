"""Project management tools — multi-agent coordination via blackboards.

These tools let Dela's lead agent orchestrate multi-step projects:
  - Create projects and blackboards
  - Queue specialists for sequential execution
  - Dispatch to the blackboard (specialist writes a section)
  - Assemble the execution plan from all sections
  - Advance the specialist queue
  - Resolve conflicts with formal tiebreakers
  - Check project and blackboard status

The lead agent (or the secretary sub-agent) calls these tools. Specialists
don't call them — they write sections to the blackboard via dispatch_subagent.
"""

from __future__ import annotations

from dela.tools import register


@register(
    name="create_project",
    description=(
        "Create a new multi-agent project for coordinating complex tasks across "
        "multiple specialists. Use this when a task is big enough to need multiple "
        "agents working on different aspects — e.g. 'redesign the API and update the docs' "
        "needs a programming expert and a documentation expert. The project tracks "
        "the specialist queue, decisions, conflicts, and blackboards. Requires confirmation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "A short name for the project."},
            "description": {"type": "string", "description": "What the project is about."},
        },
        "required": ["name"],
    },
    requires_confirmation=True,
)
def create_project(args: dict) -> str:
    from dela import projects

    project = projects.create_project(args["name"], args.get("description", ""))
    return (
        f"Project created: {project['name']} ({project['id']})\n"
        f"Use create_blackboard to start a task within this project."
    )


@register(
    name="create_blackboard",
    description=(
        "Create a blackboard — a shared workspace where multiple agents contribute "
        "sections to a single task. The orchestrator creates it, specialists append "
        "their analyses, then the orchestrator assembles an execution plan. Use this "
        "for complex tasks that need input from multiple specialists. Requires confirmation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "task_description": {"type": "string", "description": "What the task is."},
            "context": {"type": "string", "description": "Background context for the task."},
            "project_id": {"type": "string", "description": "The project this blackboard belongs to (optional)."},
        },
        "required": ["task_description"],
    },
    requires_confirmation=True,
)
def create_blackboard(args: dict) -> str:
    from dela import blackboard, projects

    bb = blackboard.create(
        task_description=args["task_description"],
        context=args.get("context", ""),
        project_id=args.get("project_id", ""),
    )

    # Link to project if specified
    if args.get("project_id"):
        projects.register_blackboard(args["project_id"], bb["id"])

    return (
        f"Blackboard created: {bb['id']}\n"
        f"Status: {bb['status']}\n"
        f"Task: {bb['task_description']}\n"
        f"Use dispatch_to_blackboard to send specialists to contribute sections."
    )


@register(
    name="dispatch_to_blackboard",
    description=(
        "Dispatch a specialist sub-agent to contribute a section to a blackboard. "
        "The specialist runs with its own SOUL and scoped tools, reads the blackboard "
        "context, and writes its analysis as a section. Use this to get input from "
        "different domain experts on a shared task."
    ),
    parameters={
        "type": "object",
        "properties": {
            "blackboard_id": {"type": "string", "description": "The blackboard to contribute to."},
            "agent": {
                "type": "string",
                "description": "The sub-agent to dispatch (e.g. 'researcher', 'presenter').",
            },
            "task": {"type": "string", "description": "What the specialist should analyze or contribute."},
            "section_name": {"type": "string", "description": "Name for the section (e.g. 'Security Analysis')."},
        },
        "required": ["blackboard_id", "agent", "task", "section_name"],
    },
)
def dispatch_to_blackboard(args: dict) -> str:
    from dela import blackboard, handoff
    from dela.agents import get_agent
    from dela.brain import run_subagent

    bb_id = args["blackboard_id"]
    bb = blackboard.load(bb_id)
    if bb is None:
        return f"Blackboard '{bb_id}' not found."

    agent_name = args["agent"]
    soul = get_agent(agent_name)
    if soul is None:
        available = [a.name for a in _get_agents_list()]
        return f"No sub-agent named '{agent_name}'. Available: {', '.join(available)}"

    # Build the handoff
    ho = handoff.create_handoff(
        blackboard_id=bb_id,
        project_id=bb.get("project_id", ""),
        task=args["task"],
    )

    # Run the sub-agent
    prompt = soul.build_prompt() + "\n\n" + handoff.handoff_to_prompt(ho)
    result = run_subagent(
        agent_name=agent_name,
        task=args["task"] + f"\n\nContext: {bb.get('context', '')}\nBlackboard task: {bb['task_description']}",
        system_prompt_text=prompt,
        tool_whitelist=soul.tool_whitelist,
    )

    # Write the result as a section on the blackboard
    blackboard.append_section(bb_id, agent_name, args["section_name"], result)

    return (
        f"Specialist '{agent_name}' contributed section '{args['section_name']}' to blackboard '{bb_id}'.\n"
        f"Result summary: {result[:200]}"
    )


@register(
    name="set_execution_plan",
    description=(
        "Assemble the execution plan from all specialist sections on a blackboard. "
        "The plan is worker-executable: numbered steps with exact file paths and code. "
        "Call this after all specialists have contributed. Requires confirmation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "blackboard_id": {"type": "string", "description": "The blackboard to plan for."},
            "plan": {"type": "string", "description": "The assembled execution plan (numbered steps, exact paths/code)."},
        },
        "required": ["blackboard_id", "plan"],
    },
    requires_confirmation=True,
)
def set_execution_plan(args: dict) -> str:
    from dela import blackboard

    ok = blackboard.set_execution_plan(args["blackboard_id"], args["plan"])
    if not ok:
        return f"Blackboard '{args['blackboard_id']}' not found."
    return f"Execution plan set on blackboard '{args['blackboard_id']}'. Ready for approval gate."


@register(
    name="advance_queue",
    description=(
        "Advance the specialist queue for a project. Marks the current specialist as done "
        "and returns the next one. Use this after a specialist has finished contributing. "
        "Returns the next specialist or 'queue exhausted' if done."
    ),
    parameters={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "The project to advance."},
        },
        "required": ["project_id"],
    },
)
def advance_queue(args: dict) -> str:
    from dela import projects

    next_spec = projects.advance_queue(args["project_id"])
    if next_spec is None:
        return "Queue exhausted. All specialists have contributed."

    return (
        f"Next specialist: {next_spec['agent']}\n"
        f"Task: {next_spec['task']}\n"
        f"Status: {next_spec['status']}"
    )


@register(
    name="resolve_conflict",
    description=(
        "Resolve a conflict between specialist contributions on a blackboard. "
        "Tiebreaker order: (1) prior decisions, (2) simpler solution wins, "
        "(3) domain authority, (4) user escalation. Records the resolution for "
        "future enforcement. Requires confirmation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "blackboard_id": {"type": "string", "description": "The blackboard with the conflict."},
            "project_id": {"type": "string", "description": "The project (for decision recording)."},
            "description": {"type": "string", "description": "What the conflict is about."},
            "resolution": {"type": "string", "description": "The chosen resolution."},
            "rationale": {"type": "string", "description": "Why this resolution was chosen."},
        },
        "required": ["blackboard_id", "description", "resolution", "rationale"],
    },
    requires_confirmation=True,
)
def resolve_conflict(args: dict) -> str:
    from dela import blackboard, projects

    blackboard.record_conflict(
        args["blackboard_id"], args["description"], args["resolution"], "orchestrator"
    )

    if args.get("project_id"):
        projects.record_decision(
            args["project_id"], args["resolution"], args["rationale"], "orchestrator"
        )
        projects.record_conflict(
            args["project_id"], args["description"], args["resolution"], "orchestrator"
        )

    return f"Conflict resolved: {args['resolution']}"


@register(
    name="get_blackboard_status",
    description=(
        "Get the full status of a blackboard: current status, all sections, "
        "execution plan, decisions, conflicts. Use this to review progress before "
        "assembling the execution plan. Read-only."
    ),
    parameters={
        "type": "object",
        "properties": {
            "blackboard_id": {"type": "string", "description": "The blackboard to check."},
        },
        "required": ["blackboard_id"],
    },
)
def get_blackboard_status(args: dict) -> str:
    from dela import blackboard
    return blackboard.summary(args["blackboard_id"])


@register(
    name="get_project_status",
    description=(
        "Get the full status of a project: blackboards, specialist queue, "
        "decisions, conflicts, learnings. Use this to check overall progress. Read-only."
    ),
    parameters={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "The project to check."},
        },
        "required": ["project_id"],
    },
)
def get_project_status(args: dict) -> str:
    from dela import projects
    return projects.get_project_status(args["project_id"])


@register(
    name="approve_blackboard",
    description=(
        "Approve a blackboard for execution — transitions it from awaiting_approval "
        "to executing. This is the governance gate: high-stakes multi-agent plans "
        "require explicit user approval before the worker executes. Requires confirmation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "blackboard_id": {"type": "string", "description": "The blackboard to approve."},
        },
        "required": ["blackboard_id"],
    },
    requires_confirmation=True,
)
def approve_blackboard(args: dict) -> str:
    from dela import blackboard

    ok = blackboard.set_status(args["blackboard_id"], blackboard.EXECUTING, "user")
    if not ok:
        return f"Could not approve blackboard '{args['blackboard_id']}'. Check its current status."

    return f"Blackboard '{args['blackboard_id']}' approved for execution. Gate is open."


def _get_agents_list():
    from dela.agents import list_agents
    return list_agents()