"""Workflow system — define, store, design, and execute multi-step workflows.

A workflow is a reusable, named sequence of steps that Dela can execute.
Each step specifies an agent, a task description, optional dependencies on
other steps, and optional tools. Workflows are stored as JSON and can be:
  - Designed interactively (brainstorm with the workflow designer sub-agent)
  - Recorded from steps the user describes
  - Created manually via the create_workflow tool
  - Executed via the run_workflow tool (uses the DAG scheduler for parallelism)
  - Scheduled via the heartbeat (Feature 7)

Workflow definition format (JSON):
  {
    "name": "daily-standup-prep",
    "description": "Prepare a daily standup summary from project status",
    "steps": [
      {
        "id": "s1",
        "name": "Check project status",
        "agent": "researcher",
        "task": "Research the current status of all active projects",
        "depends_on": [],
        "tools": ["fetch_url", "check_host"]
      },
      {
        "id": "s2",
        "name": "Generate summary",
        "agent": "presenter",
        "task": "Create a standup summary from the research findings",
        "depends_on": ["s1"],
        "tools": ["generate_presentation"]
      }
    ],
    "schedule": "0 9 * * *",  // optional cron expression
    "created_at": "2026-06-28T19:00:00",
    "created_by": "user"
  }
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "dela_state" / "workflows"


def _wf_path(name: str) -> Path:
    """Slugify a workflow name to a filename."""
    slug = name.lower().replace(" ", "-").replace("/", "-")[:60]
    return _WORKFLOWS_DIR / f"{slug}.json"


def save_workflow(workflow: dict[str, Any]) -> str:
    """Save a workflow definition. Returns the workflow name."""
    _WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    name = workflow["name"]
    workflow.setdefault("created_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
    workflow.setdefault("created_by", "user")
    workflow.setdefault("steps", [])
    _wf_path(name).write_text(
        json.dumps(workflow, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return name


def load_workflow(name: str) -> dict[str, Any] | None:
    """Load a workflow by name (exact or slug match)."""
    path = _wf_path(name)
    if not path.exists():
        # Try fuzzy match
        for p in _WORKFLOWS_DIR.glob("*.json"):
            try:
                wf = json.loads(p.read_text(encoding="utf-8"))
                if wf.get("name", "").lower() == name.lower():
                    return wf
            except (json.JSONDecodeError, OSError):
                pass
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_workflows() -> list[dict[str, Any]]:
    """List all saved workflows."""
    if not _WORKFLOWS_DIR.exists():
        return []
    results = []
    for path in _WORKFLOWS_DIR.glob("*.json"):
        try:
            wf = json.loads(path.read_text(encoding="utf-8"))
            results.append({
                "name": wf.get("name", path.stem),
                "description": wf.get("description", ""),
                "steps": len(wf.get("steps", [])),
                "schedule": wf.get("schedule", ""),
                "created_at": wf.get("created_at", ""),
            })
        except (json.JSONDecodeError, OSError):
            pass
    return results


def delete_workflow(name: str) -> bool:
    """Delete a workflow."""
    path = _wf_path(name)
    if path.exists():
        path.unlink()
        return True
    return False


def execute_workflow(name: str, input_data: dict | None = None) -> dict[str, Any]:
    """Execute a workflow using the DAG scheduler.

    Each step dispatches to the specified sub-agent. Steps with dependencies
    wait for their dependencies to complete. Independent steps run in parallel
    (bounded by the scheduler's concurrency cap).

    Returns a summary of the execution results.
    """
    from dela.scheduler import Scheduler, TaskSpec

    wf = load_workflow(name)
    if wf is None:
        return {"error": f"Workflow '{name}' not found."}

    steps = wf.get("steps", [])
    if not steps:
        return {"error": "Workflow has no steps."}

    # Build TaskSpecs from workflow steps
    task_specs = []
    for step in steps:
        task_specs.append(TaskSpec(
            id=step["id"],
            agent=step.get("agent", "researcher"),
            description=step.get("task", step.get("name", step["id"])),
            depends_on=step.get("depends_on", []),
            file_scope=step.get("file_scope", []),
        ))

    # Create and validate the scheduler
    sched = Scheduler(task_specs, concurrency=3)
    errors = sched.validate()
    if errors:
        return {"error": "Workflow validation failed", "details": errors}

    # Define the runner — dispatch each step as a sub-agent
    from dela.agents import get_agent
    from dela.brain import run_subagent

    def _runner(task: TaskSpec) -> str:
        soul = get_agent(task.agent)
        if soul is None:
            return f"No agent named '{task.agent}'. Available agents: researcher, presenter, secretary, workflow_designer, system_expert."

        # Inject input data into the task description if provided
        task_desc = task.description
        if input_data:
            task_desc += f"\n\nInput data: {json.dumps(input_data)}"

        prompt = soul.build_prompt()
        return run_subagent(
            agent_name=task.agent,
            task=task_desc,
            system_prompt_text=prompt,
            tool_whitelist=soul.tool_whitelist,
        )

    # Run
    result = sched.run(_runner)

    return {
        "workflow": name,
        "completed": result["completed"],
        "failed": result["failed"],
        "total": result["total"],
        "results": result.get("results", {}),
    }


def workflow_to_text(workflow: dict[str, Any]) -> str:
    """Render a workflow as human-readable text for the model or user."""
    lines = [
        f"Workflow: {workflow.get('name', '?')}",
        f"Description: {workflow.get('description', '—')}",
        f"Steps ({len(workflow.get('steps', []))}):",
    ]
    for step in workflow.get("steps", []):
        deps = ", ".join(step.get("depends_on", [])) or "none"
        lines.append(
            f"  {step['id']}. {step.get('name', step['id'])} "
            f"[agent: {step.get('agent', '?')}, depends on: {deps}]"
        )
        lines.append(f"     Task: {step.get('task', '—')}")
    if workflow.get("schedule"):
        lines.append(f"Schedule: {workflow['schedule']}")
    return "\n".join(lines)