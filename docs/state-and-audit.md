---
title: State & Audit
nav_order: 11
---

# State Files & Audit Trail

## State Files

All durable state lives under `dela_state/` (git-ignored). Each file is human-readable and editable.

| File/Dir | Purpose |
|---|---|
| `dela_state/memory.json` | Long-term user memory (durable facts) |
| `dela_state/notices.json` | Noticeboard (proactive notices) |
| `dela_state/schedule.json` | Heartbeat schedule (next-due times) |
| `dela_state/audit.log` | Audit trail (append-only) |
| `dela_state/cost_tally.json` | Running model cost tally |
| `dela_state/tasks.json` | Project management tasks |
| `dela_state/agent_memory.json` | Per-agent self-learning memory |
| `dela_state/routing_cache.json` | Semantic routing cache |
| `dela_state/status_events.jsonl` | Lifecycle event log (JSONL) |
| `dela_state/blackboards/` | Blackboard files (one JSON per blackboard) |
| `dela_state/projects/` | Project store (one JSON per project) |
| `dela_state/styles/` | Cloned PPT styles (one folder per style) |
| `dela_state/sessions/` | Durable session histories |
| `dela_state/workflows/` | Saved workflow definitions |
| `dela_state/output/` | Generated presentations |
| `dela_state/live_settings.json` | Live config overrides (hot-reloadable) |
| `dela_state/vuln_kb.json` | Vulnerability KB cache (refreshed daily) |

Models (Whisper, Piper voices) are cached under `models/` (git-ignored).

## Memory

Long-term memory is a JSON file at `dela_state/memory.json`:

```json
[
  {"id": 1, "text": "The user's name is Bruce.", "category": "identity"},
  {"id": 2, "text": "Bruce prefers email over phone.", "category": "preference"}
]
```

- **Loaded into the system prompt** at the start of every turn.
- **Model-managed** via `remember_fact`, `update_fact`, `forget_fact` tools (all confirmation-gated).
- **Human-editable** — open the JSON in any text editor. Dela respects the edit on the next turn.
- **Data, not instructions** — stored facts are framed as background knowledge, never as commands.

---

## Audit Trail

A plain-text, append-only log at `dela_state/audit.log`:

```
[2026-06-28 14:16:40] HEARTBEAT [urgent] systems_health: Systems check: ...
[2026-06-28 14:16:45] MODEL glm-5.2 call #13 (in~0 out~0) est_cost~$0.0260
[2026-06-28 14:16:45] TOOL list_notices({}) -> 2 notice(s): ...
[2026-06-28 14:16:48] GATE dismiss_notice: ... -> GRANTED
[2026-06-28 14:16:48] KILL_SWITCH paused
```

- Tool calls, model calls, heartbeat notices, gate decisions, kill switch events
- Running cost tally at `dela_state/cost_tally.json`
- Viewable via the Audit panel in the web UI or `python -m dela` then type `audit`
- Analytics dashboard (`/api/analytics`) parses the audit log for structured usage data

### Audit Entry Types

| Type | Example | Description |
|---|---|---|
| `MODEL` | `MODEL glm-5.2 call #13` | Model API call with token estimate and cost |
| `TOOL` | `TOOL list_notices({}) -> 2 notice(s)` | Tool call with args and result summary |
| `GATE` | `GATE dismiss_notice -> GRANTED` | Confirmation gate decision |
| `HEARTBEAT` | `HEARTBEAT [urgent] systems_health: ...` | Heartbeat check result with severity |
| `KILL_SWITCH` | `KILL_SWITCH paused` | Heartbeat kill/resume events |
