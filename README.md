<div align="center">

# DELA

### Voice-First AI Assistant with Tools, Memory, Multi-Agent Orchestration, and a Holographic Web UI

**One shared agent core. Many ways in and out. All on your laptop.**

[Getting Started](docs/getting-started.md) · [Architecture](docs/architecture.md) · [Full Docs](docs/)

</div>

---

## What Dela Does

Dela is a voice-first AI assistant that runs entirely on your laptop. It talks, it listens, it remembers, it acts — and it does it all through a single shared brain that text, voice, the web UI, and the proactive heartbeat all share.

No per-call API charges for speech. No cloud dependency for audio. No heavy frameworks. Just Python, seams, and a discipline: **extend at the edges, never rewrite the core.**

**Works fully offline with Ollama** — LLM, STT, TTS, and VAD all run locally. No internet required.

| Capability | Status |
|---|---|---|
| Text, voice, and web UI turns through one shared brain | ✅ |
| 47 tools across 18 modules — add new ones in one file | ✅ |
| Fully local voice: faster-whisper STT + Piper (25 voices) + Kokoro (12 voices) TTS + webrtcvad | ✅ |
| Open-mic duplex with barge-in (no LiveKit, no Redis) | ✅ |
| Voice I/O through the web UI — mic button + TTS playback + 🔊 toggle | ✅ |
| 5 sub-agents with scoped tools and live status tracking | ✅ |
| Multi-agent orchestration via blackboard architecture | ✅ |
| Workflow system with visual designer, scheduling, DAG execution | ✅ |
| Proactive heartbeat — 6 checks running on intervals | ✅ |
| Durable memory that survives restarts (thread-safe, dedup, search) | ✅ |
| Security self-audit — OWASP LLM Top 10 + CWE Top 25 (20 checks) | ✅ |
| Prioritized findings (P0–P4) + agent-powered fix button | ✅ |
| Model router — auto-saves tokens by routing simple tasks to cheap models (default on) | ✅ |
| Profile system — personal, work, or fully offline (Ollama) | ✅ |
| 11 hot-reloadable live settings — no restart to change them | ✅ |
| Personality matrix — 7 presets (Friendly, Professional, Energetic, Calm, British, Technical, Creative) | ✅ |
| Dynamic HITL gate — impact-based confirmation scoring (0–10 threshold) | ✅ |
| Kokoro TTS provider — 12 US/UK voices at 24kHz (default, auto-download) | ✅ |
| Multi-tab audio coordination via BroadcastChannel | ✅ |
| Markdown-rich responses — code blocks w/ copy, tables, links, headings | ✅ |
| Analytics dashboard — 6 KPI cards, full tool/agent/memory breakdowns | ✅ |
| Slash commands — /help /clear /voice /theme /memory /scan /tasks /cost | ✅ |
| Animated sub-agent overlay — live tool blips, expand/collapse, draggable | ✅ |
| Holographic web UI with 5 themes, floating windows, live agent roster, smooth transitions | ✅ |
| One-command startup with preflight checks | ✅ |

---

## By the Numbers

```
  47 tools     5 sub-agents     6 heartbeat checks     40 REST endpoints
  20 vuln checks   13 state types   3 skills    5 themes    2 profiles
  25 Piper voices   12 Kokoro voices   7 personalities   11 live settings
```

---

## Quick Start

```bash
# 1. Install
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Configure
copy .env.example .env
# Edit .env — set DELA_BASE_URL, DELA_API_KEY, DELA_MODEL

# 3. Run
python start_dela.py
```

That's it. Preflight checks run, backend launches on `:8000`, frontend on `:5173`, browser opens. Ctrl+C shuts everything down gracefully.

**Prerequisites:** Python 3.12+, Node.js 18+, an OpenAI-compatible model endpoint, a mic + speakers for voice.

---

## Why Dela?

### Voice-First, Cloud-Free
faster-whisper runs on your GPU. Piper runs on CPU. webrtcvad handles silence detection. No API keys for speech, no per-call charges, no latency to a cloud STT endpoint. The EoT detector is a pure state machine — no neural model needed for turn-taking. Barge-in works because threading + VAD is all you need, not LiveKit + Redis.

### Fully Offline with Ollama
Set `DELA_PROFILE=offline`, point Dela at `http://localhost:11434/v1`, and everything runs locally — LLM, STT, TTS, VAD. No internet required. The offline profile blocks web-dependent tools (`fetch_url`, `check_host`) and the preflight checks detect Ollama automatically, listing available models. The Settings panel shows live Ollama status. Works with any Ollama model: llama3.1, qwen2.5, phi3, mistral, etc.

### Self-Auditing Security
Dela scans its own codebase against the OWASP Top 10 for LLM Applications 2025 and the CWE Top 25 (2025). 20 checks covering prompt injection, secrets, command injection, path traversal, code injection, deserialization, SSRF, and more. Findings are prioritized P0–P4. A heartbeat check refreshes the checklist from authoritative sources daily. And when you find a vulnerability, the **FIX** button dispatches the system_expert agent to analyze the code and recommend or implement a patch.

### Multi-Agent Orchestration
Five specialist agents (researcher, presenter, secretary, workflow_designer, system_expert) each with their own SOUL — a system prompt + tool whitelist. They collaborate via a blackboard architecture with a DAG scheduler for parallel execution. The secretary coordinates, specialists write sections, a governance gate requires user approval before execution. Agent status is tracked live: ready (green), busy (amber, pulsing), error (red).

### Token-Smart Model Routing
"Why burn premium tokens on 'what is 2+2'?" The model router classifies each request by complexity — input length, code blocks, keywords, tool usage — and routes trivial tasks to a fast model, complex tasks to a premium model. Each tier is a dropdown populated from `/api/models`. Enabled by default, disable with one toggle.

### Holographic Web UI
A 2D canvas particle galaxy — particles swirl and pulse with real audio amplitude via Web Audio API. Color shifts with system state. Idle mode: ultra-compact 3-icon bar (💬 chat · 🎤 voice · ● heartbeat) that smoothly expands into a full input panel. Floating draggable windows. Glassmorphism panels. Floating icon buttons for all 12 panels. RichMessage markdown rendering: code blocks with copy, tables, headings, iframes. Animated sub-agent overlay with live tool blips. Five themes. Slash commands in the input bar. Smooth fade transitions between idle and conversation states.

### Seams Everywhere
The provider, STT, TTS, live config, and tracing are each behind a thin module. Swap any of them by rewriting one file. Ollama works today because it exposes an OpenAI-compatible endpoint. New tools, agents, skills, channels, and heartbeat checks are each one file — the brain never changes.

### Profile-Aware
Three security postures stored in `.env`:
- **Personal** — full access, standard security, wildcard CORS, all tools
- **Work** — enterprise-grade, maximum injection defense, restricted CORS, blocked tools, extra confirmation on sensitive operations, WIZ integration hook
- **Offline** — fully local, pairs with Ollama, blocks web-dependent tools, no internet needed

Each profile can have its own API connection — GLM-5.2 at home, Sonnet at work, llama3.1 offline.

---

## Architecture

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

→ **[Read the full architecture docs](docs/architecture.md)**

---

## Documentation

All docs live in the [`docs/`](docs/) directory and are served as a beautiful docs site via GitHub Pages.

| Doc | What's in it |
|---|---|
| [Getting Started](docs/getting-started.md) | Install, configure, run, entry points |
| [Architecture](docs/architecture.md) | Design principles, the six tiers, project structure |
| [Configuration](docs/configuration.md) | Env vars, profiles, live settings, heartbeat config |
| [Tools](docs/tools.md) | Tool registry, adding tools, complete 47-tool reference |
| [Voice](docs/voice.md) | Voice stack, EoT detector, duplex mode, web voice I/O |
| [Agents & Orchestration](docs/agents.md) | Sub-agents, blackboard, agent memory, model router |
| [Workflows](docs/workflows.md) | Workflow system, designer, DAG scheduler, skills |
| [Security](docs/security.md) | Audit system, vuln KB, prioritization, fix button, gate |
| [Frontend](docs/frontend.md) | Jarvis Hub UI, panels, themes, floating windows |
| [API Reference](docs/api-reference.md) | All 40 REST endpoints + WebSocket |
| [State & Audit](docs/state-and-audit.md) | State files, audit trail, cost tally |
| [Roadmap](docs/roadmap.md) | Completed features, future ideas |

---

## Personality

Warm, plain-spoken, and brief. Friendly without being chatty. Gets to the point.

## License

Private project. See the GitHub repo for licensing decisions.
