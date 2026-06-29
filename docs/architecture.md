---
title: Architecture
nav_order: 2
---

# Architecture

Dela is built as concentric layers, each wrapping the last. The core discipline: **voice is a layer on top of a working agent, never the foundation.** The brain was built and verified in plain text before a single line of audio was added.

```
            ┌──────────────────────────────────────────┐
            │              Entry Points                │
            │  (web UI · text CLI · voice · heartbeat) │
            └──────────────┬───────────────────────────┘
                           │
            ┌──────────────▼───────────────────────────┐
            │              The Brain                    │
            │  (conversation loop + tool-call loop)    │
            │  brain.py — respond() / assemble_reply() │
            └──┬────────┬────────┬────────┬───────────┘
               │        │        │        │
        ┌──────▼──┐ ┌───▼──┐ ┌──▼───┐ ┌──▼──────────┐
        │ Provider │ │ Tools│ │ Gate │ │   Audit     │
        │  (seam)  │ │ (reg)│ │(conf)│ │  (log+cost) │
        └──────────┘ └──┬───┘ └──────┘ └─────────────┘
                        │
              ┌─────────┼─────────┐
              │         │         │
         ┌────▼───┐ ┌──▼────┐ ┌─▼──────┐
         │ Project│ │Research│ │Systems │  ... (+ 47 tools,
         │ (tasks)│ │(fetch) │ │(check) │      5 sub-agents,
         └────────┘ └───────┘ └────────┘      3 skills)
```

## Key Design Principles

1. **One shared agent core.** `brain.respond()` / `brain.assemble_reply()` is the single entry point. Text, voice, web UI, and heartbeat turns all flow through it.

2. **Seams everywhere.** The provider (`provider.py`), STT (`stt.py`), TTS (`tts.py`), and live config (`live_config.py`) are each behind a thin module. Swap any of them by rewriting one file.

3. **Tools are the extension point.** Adding a capability means writing one self-contained module under `dela/tools/` and decorating a function with `@register(...)`. Never edit the core loop.

4. **Errors as results, not exceptions.** Tool failures return a plain-language string to the model so it can reason and recover.

5. **Secrets never in code.** All credentials live in `.env` (git-ignored). Profile-specific credentials are loaded per profile.

6. **Profile-aware.** Security posture, API connection, tool access, and injection defense level all change based on the active profile.

## The Six Tiers

Each tier was built and verified before the next started. Each ends with something runnable.

### Tier 1 — The Brain

A text conversation loop: read input → append to history → send to model → stream the reply → append → repeat. The provider is behind a seam so swapping models is a config change.

- **File:** `dela/brain.py`
- **Provider seam:** `dela/provider.py` — `reply()` (streaming, no tools) and `reply_with_tools()` (non-streaming, with tool schemas). Reads `thinking_level` from live config.
- **System prompt:** `dela/system_prompt.py` — profile-aware, carries identity, personality, safety rules, injection defense, and loaded memory facts

### Tier 2 — The Hands (Tools)

A tool registry where each tool has a name, a description (written for the model), typed JSON-schema inputs, and a `requires_confirmation` flag. 47 tools across 18 modules.

- **Registry:** `dela/tools/__init__.py` — `Tool` dataclass, `Registry` class, `@register` decorator

### Tier 3 — The Ears and Mouth (Voice)

Voice wraps the exact same brain. Input comes from transcribed speech, output gets spoken aloud. The brain in the middle is untouched.

- **STT seam:** `dela/stt.py` — `transcribe(audio_bytes) -> str` via faster-whisper
- **TTS seam:** `dela/tts.py` — `speak(text, stop_event)` via Piper
- **VAD:** `dela/vad.py` — `wait_for_speech()` and `record_speech()` via webrtcvad
- **EoT detector:** `dela/eot.py` — state machine for smart turn-taking
- **Duplex mode:** `dela/voice_duplex.py` — full-duplex with barge-in
- **Voice entry:** `dela/voice.py` — duplex mode and PTT mode

→ **[Full voice documentation](voice)**

### Tier 4 — The Memory

A durable, human-readable JSON store of small named facts. Loaded into the system prompt at the start of every conversation.

- **Store:** `dela/memory.py`
- **Store file:** `dela_state/memory.json` — editable by hand

### Tier 5 — The Heartbeat

A background loop that wakes on an interval, runs scheduled checks, and files noteworthy results to a noticeboard.

- **Loop:** `dela/heartbeat.py`
- **Checks (6):** `systems_health`, `tasks_due`, `blackboard_cleanup`, `scheduled_workflows`, `security_scan`, `vuln_kb_refresh`
- **Config:** `heartbeat_config.json` — intervals, targets, quiet hours

### Tier 6 — The Rails (Safety)

- **Confirmation gate:** `dela/gate.py` — pluggable `Confirmer` (text, voice, WebSocket, silent, timeout)
- **Prompt injection defense:** Profile-aware — `standard` (8 rules) or `maximum` (8 absolute rules, work profile)
- **Audit trail:** `dela/audit.py` — every tool call, model call, heartbeat notice, gate decision
- **Kill switch:** `heartbeat.kill()` / `heartbeat.resume()`
- **Security self-audit:** `dela/security.py` — 9 check categories, score 0-100

→ **[Full security documentation](security)**

## Project Structure

```
tiktokJarvis/
├── .env                        # Secrets (git-ignored)
├── .env.example                # Template for .env
├── start_dela.py               # One-command startup with preflight
├── requirements.txt            # Python dependencies
├── heartbeat_config.json       # 6 heartbeat checks
│
├── dela/                       # The assistant package
│   ├── brain.py                # Shared conversation loop + tool-call loop
│   ├── provider.py             # Model provider seam (reads live_config)
│   ├── system_prompt.py        # Profile-aware system prompt + injection defense
│   ├── config.py               # Env loading, profile-specific API config
│   ├── live_config.py          # Hot-reloadable settings layer
│   ├── profiles.py             # Personal + work profile definitions
│   ├── security.py             # Security self-audit engine (9 categories)
│   ├── vuln_kb.py              # Vulnerability knowledge base (OWASP + CWE)
│   ├── model_router.py         # Auto-selects model by task complexity
│   ├── agent_status.py         # Agent ready/busy/error tracker
│   ├── gate.py                 # Confirmation gate
│   ├── audit.py                # Audit trail + cost tally
│   ├── memory.py               # Long-term memory store
│   ├── heartbeat.py            # Heartbeat background loop
│   ├── checks.py               # 6 scheduled checks
│   ├── stt.py / tts.py / vad.py / eot.py / voice*.py  # Voice stack
│   ├── server.py               # FastAPI + WebSocket server (40 endpoints)
│   ├── workflows.py            # Workflow system
│   ├── blackboard.py           # Multi-agent shared workspace
│   ├── scheduler.py            # DAG scheduler
│   ├── sandbox.py              # Code execution seam
│   ├── agents/                 # 5 sub-agents
│   ├── tools/                  # 47 tools across 18 modules
│   ├── skills/                 # 3 skills (markdown guidance)
│   ├── channels/               # IM channels (Telegram, Teams, Graph API)
│   └── presentation/           # PPT style cloner + generator
│
├── frontend/                   # Jarvis Hub web UI
├── dela_state/                 # Durable state (git-ignored)
└── models/                     # Cached ML models (git-ignored)
```
