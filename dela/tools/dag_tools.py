"""DAG scheduler tool — let the model decompose and run parallel tasks."""

from __future__ import annotations

from dela.scheduler import Scheduler, TaskSpec, decompose_from_json
from dela.tools import register


@register(
    name="run_dag",
    description=(
        "Run a DAG (directed acyclic graph) of tasks in parallel. Each task specifies "
        "an agent, a description, dependencies (which tasks must complete first), and "
        "an optional file scope (files the task will touch — tasks with overlapping "
        "scopes serialize automatically). Use this for complex multi-step work where "
        "some tasks can run concurrently. Requires confirmation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "description": "List of tasks in the DAG.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Unique task ID (e.g. 't1')."},
                        "agent": {"type": "string", "description": "Agent to dispatch (e.g. 'researcher')."},
                        "description": {"type": "string", "description": "What the task should do."},
                        "depends_on": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Task IDs that must complete before this one.",
                        },
                        "file_scope": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Files this task will read/write (for lease safety).",
                        },
                    },
                    "required": ["id", "agent", "description"],
                },
            },
            "concurrency": {"type": "integer", "description": "Max parallel tasks (default 3)."},
            "blackboard_id": {"type": "string", "description": "Optional blackboard for governance gate."},
        },
        "required": ["tasks"],
    },
    requires_confirmation=True,
)
def run_dag(args: dict) -> str:
    tasks_data = args.get("tasks", [])
    concurrency = args.get("concurrency", 3)
    blackboard_id = args.get("blackboard_id", "")

    if not tasks_data:
        return "No tasks provided."

    # Build TaskSpecs
    plan = {"tasks": tasks_data}
    task_specs = decompose_from_json(plan)

    if not task_specs:
        return "Failed to parse tasks."

    # Create scheduler
    sched = Scheduler(task_specs, concurrency=concurrency, blackboard_id=blackboard_id)

    # Validate
    errors = sched.validate()
    if errors:
        return f"DAG validation failed:\n" + "\n".join(f"  - {e}" for e in errors)

    # Define the runner — dispatch each task as a sub-agent
    from dela.agents import get_agent
    from dela.brain import run_subagent

    def _runner(task: TaskSpec) -> str:
        soul = get_agent(task.agent)
        if soul is None:
            return f"No agent named '{task.agent}'"

        prompt = soul.build_prompt()
        return run_subagent(
            agent_name=task.agent,
            task=task.description,
            system_prompt_text=prompt,
            tool_whitelist=soul.tool_whitelist,
        )

    # Run
    result = sched.run(_runner)

    # Format result
    lines = [
        f"DAG complete: {result['completed']}/{result['total']} tasks done, {result['failed']} failed.",
    ]
    for tid, task_result in result.get("results", {}).items():
        lines.append(f"  {tid}: {task_result[:100]}")

    return "\n".join(lines)