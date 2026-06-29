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

| Capability | Status |
|---|---|
| Text, voice, and web UI turns through one shared brain | ✅ |
| 47 tools across 18 modules — add new ones in one file | ✅ |
| Fully local voice: faster-whisper STT + Piper TTS + webrtcvad | ✅ |
| Open-mic duplex with barge-in (no LiveKit, no Redis) | ✅ |
| Voice I/O through the web UI — mic button + TTS playback | ✅ |
| 5 sub-agents with scoped tools and live status tracking | ✅ |
| Multi-agent orchestration via blackboard architecture | ✅ |
| Workflow system with visual designer, scheduling, DAG execution | ✅ |
| Proactive heartbeat — 6 checks running on intervals | ✅ |
| Durable memory that survives restarts | ✅ |
| Security self-audit — OWASP LLM Top 10 + CWE Top 25 (20 checks) | ✅ |
| Prioritized findings (P0–P4) + agent-powered fix button | ✅ |
| Model router — auto-saves tokens by routing simple tasks to cheap models | ✅ |
| Profile system — personal (full access) vs work (enterprise-grade) | ✅ |
| 11 hot-reloadable live settings — no restart to change them | ✅ |
| Holographic web UI with 5 themes, floating windows, live agent roster | ✅ |
| One-command startup with preflight checks | ✅ |

---

## By the Numbers

```
  47 tools     5 sub-agents     6 heartbeat checks     40 REST endpoints
  20 vuln checks   13 state types   3 skills    5 themes    2 profiles
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

### Self-Auditing Security
Dela scans its own codebase against the OWASP Top 10 for LLM Applications 2025 and the CWE Top 25 (2025). 20 checks covering prompt injection, secrets, command injection, path traversal, code injection, deserialization, SSRF, and more. Findings are prioritized P0–P4. A heartbeat check refreshes the checklist from authoritative sources daily. And when you find a vulnerability, the **FIX** button dispatches the system_expert agent to analyze the code and recommend or implement a patch.

### Multi-Agent Orchestration
Five specialist agents (researcher, presenter, secretary, workflow_designer, system_expert) each with their own SOUL — a system prompt + tool whitelist. They collaborate via a blackboard architecture with a DAG scheduler for parallel execution. The secretary coordinates, specialists write sections, a governance gate requires user approval before execution. Agent status is tracked live: ready (green), busy (amber, pulsing), error (red).

### Token-Smart Model Routing
"Why burn premium tokens on 'what is 2+2'?" The model router classifies each request by complexity — input length, code blocks, keywords, tool usage — and routes trivial tasks to a cheap model, complex tasks to a premium model. Configurable via live settings. Off by default, opt-in with one toggle.

### Holographic Web UI
A 2D canvas galaxy engine — no WebGL dependency. Particles swirl around a central core, color shifts with system state. Floating draggable windows. Glassmorphism panels. Five themes. Live stats in every corner: heartbeat status, tool count, API uplink health, agent roster with status dots. Slide-in panels for security, analytics, workflows, settings, memory, state browser, audit trail, tasks.

### Seams Everywhere
The provider, STT, TTS, live config, and tracing are each behind a thin module. Swap any of them by rewriting one file. Ollama works today because it exposes an OpenAI-compatible endpoint. New tools, agents, skills, channels, and heartbeat checks are each one file — the brain never changes.

### Profile-Aware
Two security postures stored in `.env`:
- **Personal** — full access, standard security, wildcard CORS, all tools
- **Work** — enterprise-grade, maximum injection defense, restricted CORS, blocked tools, extra confirmation on sensitive operations, WIZ integration hook

Each profile can have its own API connection — GLM-5.2 at home, Sonnet at work.

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
