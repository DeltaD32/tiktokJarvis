# Feature Evaluation Pipeline — Architecture

## Overview

When a user asks "Can Dela use X?" or "Let's add Y", the system runs a single
`evaluate_feature` tool call that orchestrates the full pipeline:

```
User says "Let's see if you can use Remotion"
  → Model acknowledges ("Got it — let me evaluate Remotion")
  → Model calls evaluate_feature(query="...", title="Remotion — Impact Analysis")
  → Tool dispatches researcher + system_expert in parallel (ThreadPoolExecutor)
  → Progress events sent to frontend via WebSocket at each stage
  → HTML report synthesized from sub-agent results
  → show_panel(panel='report') opens the report with Shelve/Reject/Accept buttons
  → User clicks an action → stored in memory
```

## Files

| File | Role |
|---|---|
| `dela/tools/feature_eval.py` | Orchestration tool — dispatches agents, sends progress, builds HTML |
| `dela/tools/subagent.py` | Low-level dispatch tools (dispatch_subagent, dispatch_parallel) |
| `dela/brain.py` | Sub-agent execution (run_subagent, _run_one_tool_scoped) |
| `dela/system_prompt.py` | Instructions for the model on when/how to use evaluate_feature |
| `dela/skills/impact-analysis.md` | Reference template (loaded by skill loader if needed) |
| `dela/server.py` | `/api/report/action` endpoint for Shelve/Reject/Accept |
| `dela/agent_status.py` | Tracks sub-agent state for frontend overlay |
| `frontend/src/components/ReportProgressBar.jsx` | Progress bar driven by feature_progress WebSocket events |
| `frontend/src/components/panels/ReportPanel.jsx` | Report panel with action buttons |
| `frontend/src/components/SubAgentOverlay.jsx` | Sub-agent activity panels with completion countdown |
| `frontend/src/hooks/useDelaWS.js` | WebSocket handler for feature_progress events |

## Progress Events

The tool sends these WebSocket events during execution:

```json
{"type": "feature_progress", "stage": "acknowledging", "progress": 5}
{"type": "feature_progress", "stage": "dispatching",   "progress": 15}
{"type": "feature_progress", "stage": "researching",   "progress": 50}
{"type": "feature_progress", "stage": "synthesizing",  "progress": 70}
{"type": "feature_progress", "stage": "complete",      "progress": 100}
```

The frontend renders a progress bar that:
- Appears on first feature_progress event
- Advances smoothly with each stage
- Shows a green "complete" bar with glow at 100%
- Auto-dismisses after 2.5 seconds when complete

## Sub-Agent Optimization

Sub-agents are limited to **5 tool rounds** (down from 12). Each agent receives
a focused, directive task with explicit output format requirements:

**Researcher:** "Report ONLY: (1) What it does, (2) License, (3) Tech stack, (4) Key features, (5) Blockers"
**System Expert:** "Report ONLY: (1) Dela seam, (2) Complexity, (3) Pattern, (4) Files, (5) Risks"

This ensures fast, targeted research instead of unbounded exploration.

## Report Actions

The report panel provides three buttons backed by `POST /api/report/action`:

| Action | Effect | Memory category |
|---|---|---|
| **Shelve** | Store analysis for later recall | `feature-shelve` |
| **Reject** | Archive as not viable | `feature-reject` |
| **Accept** | Mark for implementation | `feature-accept` |

## Future Enhancements (not yet built)

1. **Feature memory with recall** — `list_shelved_features` tool so Dela can
   say "You shelved Remotion — resume that analysis?"
2. **Acceptance wizard** — after Accept, questionnaire panel asks for feature
   name, preferred seam, constraints before dispatching implementation agent
3. **Server-side state machine** — resume interrupted pipelines after restart
4. **Feature registry** — deduplicated store of all evaluated features with
   status lifecycle (evaluated → shelved/in_progress/completed/rejected)
