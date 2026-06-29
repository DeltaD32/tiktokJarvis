---
title: Frontend
nav_order: 9
---

# Frontend — Jarvis Hub UI

Dela has a holographic web UI with a 2D canvas galaxy engine, floating draggable windows, 5 themes, and live data overlays.

## One-Command Startup

```bash
python start_dela.py
```

Runs preflight checks (Python, .env, pip deps, Node.js, npm, ports), launches backend + frontend, opens browser.

## Visual Design

- **ParticleCanvas** — 2D canvas galaxy engine (no WebGL dependency). Particles swirl around a central core, color shifts with system state (idle, thinking, speaking, busy, alert, complete).
- **Inter + JetBrains Mono** — clean, modern typography. No Orbitron.
- **Glassmorphism** — frosted glass panels with backdrop blur.
- **State-based accent colors** — the entire UI shifts color based on what Dela is doing.

## Idle View (Home)

The home screen shows live data in the corners surrounding the particle galaxy:

| Stat | Source | Shows |
|---|---|---|
| **HEARTBEAT** | WebSocket | `ACTIVE` (green) / `PAUSED` (gray) — live from WS |
| **TOOLS** | `/api/tools` | Live tool count |
| **UPLINK** | `/api/uplink` | `LINKED` (green) / `AUTH FAIL` (red) / `OFFLINE` (amber) + model name, latency, profile |
| **AGENTS** | `/api/agents` | Live count + ready count + **agent roster** (each agent name with status dot + dispatch count) |

Stats auto-refresh every 15 seconds. The UPLINK stat does a real API connection check (calls `models.list()`) and reports auth status and latency. The agent roster shows each agent with a colored status dot (green=ready, amber=busy, red=error) and dispatch count.

## Voice Input (Home)

- **MIC button** on the idle input bar — click to start recording, click again to stop + transcribe
- Uses `MediaRecorder` → `POST /api/voice/stt` → faster-whisper → text
- Transcript auto-sends as a message
- **VOICE ON/OFF chip** toggles TTS playback — when ON, Dela's replies are spoken via `POST /api/voice/tts` → Piper → WAV → browser audio
- VoiceHud shows 3 states: `LISTENING` (red bars), `TRANSCRIBING` (amber bars), `DELA` (accent bars)
- Barge-in: TTS stops when you send a new message

## Floating Windows

Draggable, focusable windows that float over the galaxy:

| Window | Content |
|---|---|
| **THE HIVE** | Agent registry — shows all 5 sub-agents with live status (ready/busy/error), dispatch counts, current task. Polls every 3s. |
| **STREAM** | Conversation view — running chat with tool-call indicators |
| **SANDBOX** | Code execution output |

## Slide-in Panels

Opened via buttons in the top-right:

| Panel | Content |
|---|---|
| **ANALYTICS** | Usage dashboard — model calls, cost, tool calls, gate decisions, tool usage breakdown, recent activity |
| **TOOLS** | Browse all 47 tools + 5 agents with whitelists |
| **WORKFLOWS** | Workflow designer — list, detail, editor with all 5 agents |
| **NOTICES** | Proactive notice board |
| **SETTINGS** | 7 sections: Profile, General, Router, Voice, Theme, Heartbeat, Env Vars. Live editing of hot-reloadable settings. |
| **SECURITY** | Security audit score gauge + findings by priority + OWASP/CWE checklist + fix buttons |
| **MEMORY** | Durable facts viewer/editor — add, update, delete facts |
| **STATE** | Unified state browser — search across all 13 state types, view items, edit |
| **AUDIT** | Audit trail viewer — last N lines, cost summary |
| **TASKS** | Project management tasks |

## Themes

5 themes selectable in Settings → Theme tab. Persisted in localStorage. ParticleCanvas reads theme colors from CSS variables.

| Theme | Accent | Vibe |
|---|---|---|
| **JARVIS** | Cyan | Classic AI assistant |
| **ULTRAVIOLET** | Purple | 科幻 |
| **SOLAR** | Amber | Warm, energetic |
| **FOREST** | Green | Calm, organic |
| **CRIMSON** | Red | Alert, intense |

## Frontend Files

| File | Role |
|---|---|
| `frontend/src/App.jsx` | Main app — wires all components, fetches live stats, voice hooks |
| `frontend/src/components/ParticleCanvas.jsx` | 2D canvas galaxy engine |
| `frontend/src/components/TopStrip.jsx` | Top bar with state label, input, stats |
| `frontend/src/components/Dock.jsx` | Bottom dock for floating windows |
| `frontend/src/components/VoiceHud.jsx` | Voice visualization (recording/transcribing/speaking) |
| `frontend/src/components/HitlGate.jsx` | Human-in-the-loop confirmation dialog |
| `frontend/src/components/FloatWindow.jsx` | Draggable window wrapper |
| `frontend/src/components/HiveWindow.jsx` | Agent registry with live status |
| `frontend/src/components/StreamWindow.jsx` | Conversation view |
| `frontend/src/components/SandboxWindow.jsx` | Code execution output |
| `frontend/src/components/panels/SecurityPanel.jsx` | Security audit UI with fix buttons |
| `frontend/src/components/panels/SettingsPanel.jsx` | 7-section settings with live editing |
| `frontend/src/components/panels/WorkflowDesignerPanel.jsx` | Workflow designer with all 5 agents |
| `frontend/src/components/panels/AnalyticsPanel.jsx` | Usage dashboard |
| `frontend/src/components/panels/MemoryPanel.jsx` | Memory viewer/editor |
| `frontend/src/components/panels/StateBrowserPanel.jsx` | State browser |
| `frontend/src/components/panels/ToolBrowserPanel.jsx` | Tool + agent browser |
| `frontend/src/components/panels/AuditPanel.jsx` | Audit trail viewer |
| `frontend/src/components/panels/NoticesPanel.jsx` | Notice board |
| `frontend/src/components/panels/TasksPanel.jsx` | Task viewer |
| `frontend/src/hooks/useDelaWS.js` | WebSocket hook |
| `frontend/src/hooks/useVoiceRecorder.js` | Mic recording → STT |
| `frontend/src/hooks/useVoiceTTS.js` | Text → TTS → audio playback |
| `frontend/src/themes.js` | 5 theme palettes with localStorage persistence |
| `frontend/src/styles/globals.css` | Complete style system |
