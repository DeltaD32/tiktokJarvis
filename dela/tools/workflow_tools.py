"""Workflow tools — create, list, design, save, and run workflows.

These tools let the model (and the workflow_designer sub-agent) interact
with the workflow system. Users can:
  - design_workflow: brainstorm a workflow with the designer sub-agent
  - create_workflow: create a workflow definition directly
  - save_workflow: save a workflow definition to disk
  - list_workflows: list all saved workflows
  - get_workflow: get a specific workflow's full definition
  - run_workflow: execute a workflow using the DAG scheduler
"""

from __future__ import annotations

from dela.tools import register


@register(
    name="list_workflows",
    description=(
        "List all saved workflows with their names, descriptions, step counts, "
        "and schedules. Use this when the user asks what workflows exist or "
        "wants to see their automation library. Read-only."
    ),
    parameters={"type": "object", "properties": {}},
)
def list_workflows_tool(args: dict) -> str:
    from dela.workflows import list_workflows
    wfs = list_workflows()
    if not wfs:
        return "No workflows saved. Use design_workflow or create_workflow to make one."
    lines = ["Saved workflows:"]
    for wf in wfs:
        schedule = f" [schedule: {wf['schedule']}]" if wf.get("schedule") else ""
        lines.append(f"  - {wf['name']}: {wf['description'][:60]} ({wf['steps']} steps){schedule}")
    return "\n".join(lines)


@register(
    name="get_workflow",
    description=(
        "Get the full definition of a specific workflow by name. Shows all steps, "
        "agents, tasks, and dependencies. Use this when the user wants to review "
        "or refine an existing workflow. Read-only."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "The workflow name."},
        },
        "required": ["name"],
    },
)
def get_workflow_tool(args: dict) -> str:
    from dela.workflows import load_workflow, workflow_to_text
    wf = load_workflow(args["name"])
    if wf is None:
        return f"Workflow '{args['name']}' not found."
    return workflow_to_text(wf)


@register(
    name="save_workflow",
    description=(
        "Save a workflow definition to disk. The workflow must have a name, "
        "description, and a list of steps. Each step needs an id, name, agent, "
        "task, and optional depends_on. Use this after designing a workflow "
        "with the user. Requires confirmation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Workflow name (lowercase, hyphenated)."},
            "description": {"type": "string", "description": "What the workflow does."},
            "steps": {
                "type": "array",
                "description": "List of workflow steps.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Step ID (e.g. 's1')."},
                        "name": {"type": "string", "description": "Human-readable step name."},
                        "agent": {"type": "string", "description": "Agent to run this step."},
                        "task": {"type": "string", "description": "What the agent should do."},
                        "depends_on": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Step IDs that must complete first.",
                        },
                    },
                    "required": ["id", "name", "agent", "task"],
                },
            },
            "schedule": {"type": "string", "description": "Optional cron expression for scheduling."},
        },
        "required": ["name", "description", "steps"],
    },
    requires_confirmation=True,
)
def save_workflow_tool(args: dict) -> str:
    from dela.workflows import save_workflow
    workflow = {
        "name": args["name"],
        "description": args["description"],
        "steps": args["steps"],
        "schedule": args.get("schedule", ""),
    }
    name = save_workflow(workflow)
    return f"Workflow '{name}' saved with {len(args['steps'])} step(s). Use run_workflow to execute it."


@register(
    name="run_workflow",
    description=(
        "Execute a saved workflow. Each step dispatches to its specified agent. "
        "Steps with dependencies wait; independent steps run in parallel. "
        "Returns a summary of results. Requires confirmation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "The workflow name to run."},
            "input_data": {
                "type": "object",
                "description": "Optional input data to pass to the workflow steps.",
            },
        },
        "required": ["name"],
    },
    requires_confirmation=True,
)
def run_workflow_tool(args: dict) -> str:
    from dela.workflows import execute_workflow
    result = execute_workflow(args["name"], args.get("input_data"))
    if "error" in result:
        return result["error"]

    lines = [
        f"Workflow '{result['workflow']}' complete: "
        f"{result['completed']}/{result['total']} steps done, {result['failed']} failed.",
    ]
    for step_id, step_result in result.get("results", {}).items():
        lines.append(f"  {step_id}: {step_result[:150]}")
    return "\n".join(lines)


@register(
    name="design_workflow",
    description=(
        "Dispatch the workflow designer sub-agent to help brainstorm and design "
        "a workflow. The designer will ask questions, propose steps, suggest agents, "
        "and help the user think through the process. Use this when the user says "
        "'help me design a workflow', 'brainstorm a process', 'figure out the steps', "
        "or describes a recurring task they want to automate."
    ),
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "What the user wants the workflow to accomplish."},
            "context": {"type": "string", "description": "Any additional context about the task."},
        },
        "required": ["goal"],
    },
)
def design_workflow_tool(args: dict) -> str:
    from dela.agents import get_agent
    from dela.brain import run_subagent

    soul = get_agent("workflow_designer")
    if soul is None:
        return "Workflow designer agent not available."

    prompt = soul.build_prompt()
    task = f"Help the user design a workflow for: {args['goal']}"
    if args.get("context"):
        task += f"\n\nContext: {args['context']}"

    result = run_subagent(
        agent_name="workflow_designer",
        task=task,
        system_prompt_text=prompt,
        tool_whitelist=soul.tool_whitelist,
    )
    return f"[Workflow designer result]:\n{result}"


@register(
    name="delete_workflow",
    description="Delete a saved workflow by name. Requires confirmation.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "The workflow name to delete."},
        },
        "required": ["name"],
    },
    requires_confirmation=True,
)
def delete_workflow_tool(args: dict) -> str:
    from dela.workflows import delete_workflow
    if delete_workflow(args["name"]):
        return f"Workflow '{args['name']}' deleted."
    return f"Workflow '{args['name']}' not found."