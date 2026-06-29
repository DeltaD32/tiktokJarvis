---
title: Workflows
nav_order: 7
---

# Workflows

A workflow is a reusable, named sequence of steps that Dela can execute. Each step specifies an agent, a task description, optional dependencies, and optional tools.

## Workflow Designer

The web UI includes a full workflow designer panel (`WorkflowDesignerPanel.jsx`) with three views:

- **List** — all saved workflows with step count and schedule
- **Detail** — visual step flow with agent-colored dots and dependency arrows; run button with execution results
- **Editor** — create/edit workflows with a full step editor

### Available Agents

All 5 agents are available as step targets:

| Agent | Best for |
|---|---|
| `researcher` | Web research, URL fetching, host checking |
| `presenter` | Presentation design, PPT generation |
| `secretary` | Coordination, blackboard management, conflict resolution |
| `workflow_designer` | Workflow brainstorming, design, refinement |
| `system_expert` | Codebase inspection, architecture advice, code implementation |

### Workflow Definition Format

```json
{
  "name": "daily-standup-prep",
  "description": "Prepare a daily standup summary",
  "steps": [
    {
      "id": "s1",
      "name": "Check project status",
      "agent": "researcher",
      "task": "Research the current status of all active projects",
      "depends_on": []
    },
    {
      "id": "s2",
      "name": "Generate summary",
      "agent": "presenter",
      "task": "Create a standup summary from the research findings",
      "depends_on": ["s1"]
    }
  ],
  "schedule": "0 9 * * *",
  "created_at": "2026-06-28T19:00:00",
  "created_by": "user"
}
```

## Execution

Workflows are executed via the DAG scheduler — steps with dependencies wait, independent steps run in parallel (bounded by concurrency cap of 3).

Each step dispatches to the specified sub-agent. The agent runs with its own SOUL (system prompt + tool whitelist) and isolated history. Results are collected and returned as a summary.

## Scheduling

Workflows can have an optional cron schedule. The heartbeat's `scheduled_workflows` check (runs every 300s) checks if any workflow is due and executes it.

## REST Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/workflows` | GET | List all saved workflows |
| `/api/workflows` | POST | Save a new workflow |
| `/api/workflows/{name}` | GET | Get a workflow's full definition |
| `/api/workflows/{name}` | DELETE | Delete a workflow |
| `/api/workflows/{name}/run` | POST | Execute a workflow |

## Workflow Tools

| Tool | Description | Confirmation |
|---|---|---|
| `design_workflow` | Dispatch the workflow designer sub-agent to brainstorm | No |
| `save_workflow` | Save a workflow definition to disk | Yes |
| `list_workflows` | List all saved workflows | No |
| `get_workflow` | Get a specific workflow's full definition | No |
| `run_workflow` | Execute a workflow via DAG scheduler | Yes |
| `delete_workflow` | Delete a saved workflow | Yes |

---

## Skills

Skills are markdown guidance files loaded on demand. The model can load a skill when it needs workflow guidance for a specific domain.

| Skill | File | Guidance |
|---|---|---|
| `research` | `dela/skills/research.md` | Multi-step web research workflow |
| `task-management` | `dela/skills/task-management.md` | Task management best practices |
| `presentation` | `dela/skills/presentation.md` | Presentation design principles |

Adding a skill = drop a `.md` file in `dela/skills/`. The model loads it on demand via the `load_skill` tool.

---

## Presentation System

Dela can clone the visual style of any PowerPoint file and generate new presentations using that style.

### Style Cloner

Parse any `.pptx` and extract its complete visual DNA at the XML level: theme colors, fonts, master text styles, layout backgrounds, placeholder positions, shape fills, typography, title background images.

### Slide Generator

Builds `.pptx` files from a storyline using a stored style. Layout types: `bullets`, `title_only`, `hero_number`, `pillars`, `mece_tiles`, `table`, `chevron`, `cards`, `key_message`.

| Tool | Confirmation | Description |
|---|---|---|
| `clone_pptx_style` | Yes | Parse a .pptx, extract its style, store it |
| `list_ppt_styles` | No | List all stored styles |
| `generate_presentation` | Yes | Generate a .pptx from a storyline |
