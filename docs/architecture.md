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
- **Content sandbox:** `dela/content_sandbox.py` — 6-layer security for all internet-facing content (SSRF protection, content-type validation, HTML sanitization, pattern scanning, encrypted quarantine, integrity verification)

→ **[Full security documentation](security)**

## Design Decisions

### Why no external compression layer (e.g. Headroom)

Headroom (`headroomlabs-ai/headroom`) was evaluated as a drop-in proxy compression
layer. It routes each LLM request through a local proxy that compresses tool
outputs, conversation history, and RAG results before they reach the model.

**Why we rejected it:**

1. **Dela's workloads are too small to benefit.** Headroom targets enterprise
   agents processing 10K–65K token workloads (SRE incidents, codebase
   exploration). Dela's laptop-first tool outputs are typically <1K tokens.
   In testing, **80% of Dela requests were skipped** as "too short to compress."

2. **Added failure point.** The proxy sits between Dela and the LLM provider.
   If the proxy process dies, Dela loses connectivity. Dela's existing
   architecture avoids inter-process dependencies by design.

3. **Dependency weight.** Headroom pulls in ~50MB of packages (transformers,
   litellm, huggingface-hub, ONNX models) for marginal benefit. Dela already
   uses two of these for voice (transformers, onnxruntime) — adding them for
   compression alone isn't justified.

4. **Dela already compacts.** The built-in `dela/compaction.py` auto-summarizes
   conversation history when it exceeds `COMPACTION_THRESHOLD_CHARS` (default
   100K), keeping recent turns with `COMPACTION_KEEP_RECENT_CHARS` (default
   20K). This is simpler, involves no extra processes, and matches Dela's
   actual workload patterns.

5. **Evaluated, not guessed.** The prototype was fully integrated — proxy
   started, `.env` redirected, 5 requests sent end-to-end. The 42% compression
   rate on the one compressible request sounds impressive until you see the
   absolute numbers: 994 tokens saved on a request that was artificially large.
   Real Dela tool outputs are much smaller and rarely trigger compression.

**Verdict:** Stick with `compaction.py`. If Dela ever grows to handle enterprise-
scale agentic workloads with 50K+ token tool outputs, revisit.

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
│   ├── content_sandbox.py       # Content sandbox — 6-layer internet content security
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
│   ├── auditor.py              # Shared asset auditor (tools, agents, repos)
│   ├── tools/                  # 48 tools across 19 modules
│   │   ├── repo_analysis.py    # External repo analyzer (fetches, scores, verdict)
│   │   ...
│   ├── skills/                 # 3 skills (markdown guidance)
│   ├── channels/               # IM channels (Telegram, Teams, Graph API)
│   └── presentation/           # PPT style cloner + generator
│
├── frontend/                   # Jarvis Hub web UI
├── dela_state/                 # Durable state (git-ignored)
└── models/                     # Cached ML models (git-ignored)
```
