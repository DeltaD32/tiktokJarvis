---
title: Agents & Orchestration
nav_order: 6
---

# Agents & Orchestration

## Sub-Agents

5 sub-agents, each with its own SOUL (system prompt + tool whitelist):

| Agent | File | Tools | Role |
|---|---|---|---|
| `researcher` | `dela/agents/researcher.py` | fetch_url, check_host | Web research and summarization |
| `presenter` | `dela/agents/presenter.py` | clone_pptx_style, list_ppt_styles, generate_presentation, list_notices | Presentation design and generation |
| `secretary` | `dela/agents/secretary.py` | All project_mgmt tools | Multi-agent project coordinator |
| `workflow_designer` | `dela/agents/workflow_designer.py` | Workflow + memory tools | Workflow brainstorming, design, refinement |
| `system_expert` | `dela/agents/system_expert.py` | run_code, search_state, list_skills, list_workflows | Architecture expert — advises on and implements new features |

Adding a sub-agent = one file in `dela/agents/` with `@register_agent(...)`.

## Agent Status Tracking

Each sub-agent's status is tracked in real time:

| State | Meaning | UI Color |
|---|---|---|
| `ready` | Idle and available for dispatch | Green |
| `busy` | Currently executing a task | Amber (pulsing) |
| `error` | Last run failed | Red |

- `dela/agent_status.py` tracks status in-memory
- `dispatch_subagent` marks busy before run, ready/error after
- `/api/agents` returns live status + dispatch count + last task
- HiveWindow polls every 3s and shows colored badges
- Idle view shows agent roster — each agent name with status dot and dispatch count

## Agent Self-Learning Memory

Each sub-agent has its own memory namespace with three learning types: `WORKED`, `AVOID`, `PATTERN`. Learnings are injected into the sub-agent's prompt at task start and decay over time.

---

## Blackboard Architecture

Dela has a full multi-agent orchestration system adapted from the blackboard architecture pattern. It enables complex, multi-step tasks that require input from multiple specialist agents working on a shared workspace.

| Component | File | Role |
|---|---|---|
| **Blackboard** | `dela/blackboard.py` | Shared workspace — sections, status state machine |
| **Project store** | `dela/projects.py` | Persistent state — specialist queues, decisions, conflicts |
| **Handoff protocol** | `dela/handoff.py` | Structured task envelopes with traceability |
| **Secretary agent** | `dela/agents/secretary.py` | Coordinator — manages state, never does domain work |
| **Blackboard memory** | `dela/blackboard_memory.py` | Auto-distillation + cleanup of completed blackboards |
| **DAG scheduler** | `dela/scheduler.py` | Parallel task execution with dependency resolution |
| **Status events** | `dela/status_events.py` | Append-only lifecycle event log (JSONL) |

### Multi-Agent Workflow

```
1. create_project → create_blackboard
2. dispatch_to_blackboard (specialist writes a section)
3. Repeat for each specialist
4. set_execution_plan (orchestrator assembles all sections)
5. approve_blackboard (governance gate — user confirms)
6. Worker executes
7. distill_blackboard → learnings stored → archived
```

---

## Semantic Routing Cache

Dela learns from past routing decisions. When a request is similar to a past one (Jaccard token similarity >= 0.65), the cached routing is used — skipping deliberation.

---

## Model Router

The model router auto-selects the best model for each task based on complexity, saving tokens and cost.

### How it works

The router classifies each request using:
- **Input length** (short = simple, long = complex)
- **Code blocks** (``` present = complex)
- **Keywords** ("calculate/format" = trivial, "implement/design" = complex)
- **URLs, multi-line content, tool usage history**

### Tiers

| Tier | Score | Use case |
|---|---|---|
| `fast` | ≤ -2 | Trivial: math, formatting, yes/no, simple lookups |
| `default` | -1 to +2 | Standard: normal conversation, questions |
| `premium` | ≥ +3 | Complex: coding, architecture, multi-step analysis |

### Configuration

Via live settings (hot-reloadable):

| Setting | Description |
|---|---|
| `model_router_enabled` | `true`/`false` — enable auto-routing |
| `model_fast` | Model name for fast tier |
| `model_premium` | Model name for premium tier |

- **File:** `dela/model_router.py`
- **Wired into:** `brain.py` — `respond()` calls `route_model()` when enabled
- **REST:** `GET /api/model-router/classify?text=...` — see routing decision for any text
- **UI:** Settings panel → Router tab
