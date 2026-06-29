---
title: API Reference
nav_order: 10
---

# REST API Reference

The FastAPI server (`dela/server.py`) exposes 40 REST endpoints + 1 WebSocket.

## Conversation & State

| Endpoint | Method | Description |
|---|---|---|
| `/ws` | WS | Streaming replies, confirmation requests, notice push |
| `/api/memory` | GET | Get all memory facts |
| `/api/memory` | POST | Add a memory fact |
| `/api/memory/{id}` | PUT | Update a fact |
| `/api/memory/{id}` | DELETE | Delete a fact |
| `/api/notices` | GET | Active notices |
| `/api/notices/{id}` | DELETE | Dismiss a notice |
| `/api/audit` | GET | Audit trail + cost |
| `/api/tasks` | GET | Project tasks |

## Heartbeat

| Endpoint | Method | Description |
|---|---|---|
| `/api/heartbeat/kill` | POST | Kill switch — pause proactive behavior |
| `/api/heartbeat/resume` | POST | Resume proactive behavior |
| `/api/config/heartbeat` | GET | Heartbeat config |
| `/api/config/heartbeat` | PUT | Update heartbeat config |

## Uplink & Status

| Endpoint | Method | Description |
|---|---|---|
| `/api/uplink` | GET | API connection + auth status for active profile |
| `/api/status` | GET | Heartbeat active, cost, notice count |

## Voice I/O

| Endpoint | Method | Description |
|---|---|---|
| `/api/voice/stt` | POST | Transcribe audio (webm/WAV) via faster-whisper |
| `/api/voice/tts` | POST | Synthesize text to WAV via Piper |

## Tools & Agents

| Endpoint | Method | Description |
|---|---|---|
| `/api/tools` | GET | List all 47 tools |
| `/api/agents` | GET | List all 5 agents with live status |

## State Browser

| Endpoint | Method | Description |
|---|---|---|
| `/api/state` | GET | List all 13 state types |
| `/api/state/search` | GET | Search across all state types |
| `/api/state/{type}` | GET | Read a state type |
| `/api/state/{type}/{id}` | GET | Read a specific item |
| `/api/state/{type}/{id}` | PUT | Edit an item |

## Analytics

| Endpoint | Method | Description |
|---|---|---|
| `/api/analytics` | GET | Usage stats: model calls, cost, tool calls, gate decisions |

## Security

| Endpoint | Method | Description |
|---|---|---|
| `/api/security` | GET | Last scan results (with priority P0-P4) |
| `/api/security/scan` | POST | Run a new security scan |
| `/api/security/fix` | POST | Dispatch system_expert agent to analyze/fix a finding |
| `/api/vuln-kb` | GET | Vulnerability KB checklist + metadata |
| `/api/vuln-kb/refresh` | POST | Fetch fresh checklist from whitelisted sources |

## Settings

| Endpoint | Method | Description |
|---|---|---|
| `/api/settings` | GET | All settings (profile, model, voice, live, etc.) |
| `/api/settings/heartbeat` | PUT | Update heartbeat config |
| `/api/settings/env` | PUT | Update a .env var (restart required) |
| `/api/settings/profile` | PUT | Switch profile (restart required) |
| `/api/settings/live` | GET | All live settings |
| `/api/settings/live` | PUT | Update a live setting (no restart) |
| `/api/settings/live/{key}` | DELETE | Reset a live setting to default |

## Workflows

| Endpoint | Method | Description |
|---|---|---|
| `/api/workflows` | GET | List all saved workflows |
| `/api/workflows` | POST | Save a new workflow definition |
| `/api/workflows/{name}` | GET | Get a workflow's full definition |
| `/api/workflows/{name}` | DELETE | Delete a workflow |
| `/api/workflows/{name}/run` | POST | Execute a workflow (dispatches agents via DAG scheduler) |

## Model Router

| Endpoint | Method | Description |
|---|---|---|
| `/api/model-router/classify` | GET | Classify text complexity and show routing decision |
