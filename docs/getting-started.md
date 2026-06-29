---
title: Getting Started
nav_order: 1
---

# Getting Started

## Prerequisites

- **Python 3.12+** (developed on 3.12.10, Windows)
- **Node.js 18+** (for the frontend; developed on v24.18.0)
- **An NVIDIA GPU** (recommended for real-time STT; CPU works but is slower)
- **A working microphone and speakers** (for voice mode)
- **An OpenAI-compatible model endpoint** (any provider that speaks the OpenAI chat completions API)

## Install

```bash
cd D:\projects\tiktokJarvis

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate         # Windows PowerShell: & ".venv\Scripts\Activate.ps1"

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..
```

## Configure

```bash
# Copy the env template and fill in your model provider credentials
copy .env.example .env
```

Edit `.env` and set at minimum:

| Variable | Required | Description |
|---|---|---|
| `DELA_BASE_URL` | Yes | OpenAI-compatible endpoint (fallback for all profiles) |
| `DELA_API_KEY` | Yes | API key for the model provider (fallback for all profiles) |
| `DELA_MODEL` | Yes | Model name (fallback for all profiles) |
| `DELA_PROFILE` | No | `personal` (default) or `work` — selects security posture + API config |
| `DELA_PERSONAL_BASE_URL` | No | Personal profile API endpoint (overrides `DELA_BASE_URL`) |
| `DELA_PERSONAL_API_KEY` | No | Personal profile API key |
| `DELA_PERSONAL_MODEL` | No | Personal profile model (e.g. `glm-5.2` at home) |
| `DELA_WORK_BASE_URL` | No | Work profile API endpoint |
| `DELA_WORK_API_KEY` | No | Work profile API key |
| `DELA_WORK_MODEL` | No | Work profile model (e.g. `claude-sonnet-4-6` at work) |
| `DELA_NAME` | No | Assistant name (default: `Dela`) |
| `DELA_WHISPER_DEVICE` | No | `cuda` (default) or `cpu` |
| `DELA_WHISPER_COMPUTE` | No | `float16` (default for CUDA) or `int8` (for CPU) |
| `DELA_PIPER_VOICE` | No | Piper voice ID (default: `en_US-amy-medium`) |
| `DELA_VAD_AGGRESSIVENESS` | No | VAD sensitivity 0–3 (default: 3, most aggressive) |
| `DELA_THINKING_LEVEL` | No | `off`/`minimal`/`low`/`medium`/`high`/`xhigh` (empty = don't send) |
| `DELA_TRACING_PROVIDER` | No | `langsmith` or `langfuse` (empty = disabled) |

See [`.env.example`](../.env.example) for the full list including voice, compaction, tracing, and IM channel vars.

→ **[Full configuration reference](configuration)**

## Run — One Command

```bash
python start_dela.py
```

This runs preflight checks (Python, .env, pip deps, Node.js, npm, ports), launches the backend (port 8000) and frontend (port 5173), and opens the browser. Ctrl+C shuts everything down gracefully.

## Run — Manual

```bash
# Backend only (FastAPI + WebSocket server)
python -m dela.server  # or: uvicorn dela.server:app --port 8000

# Frontend (in another terminal)
cd frontend && npm run dev

# Text mode CLI (no web UI)
python -m dela

# Voice mode CLI (open mic, just talk, barge in any time)
python -m dela.voice

# Push-to-talk CLI (hold Space to talk, release to send)
python -m dela.voice --ptt
```

On first run, voice mode downloads the Whisper model (~244 MB) and Piper voice (~60 MB) automatically. These are cached under `models/` and never re-downloaded.

## Entry Points

All entry points share the same brain — `brain.respond()` / `brain.assemble_reply()`:

| Entry Point | Command | Description |
|---|---|---|
| **Web UI** | `python start_dela.py` | Holographic web UI at `http://localhost:5173` |
| **Text CLI** | `python -m dela` | Text chat with built-in commands |
| **Voice (duplex)** | `python -m dela.voice` | Open mic with barge-in |
| **Voice (PTT)** | `python -m dela.voice --ptt` | Hold Space to talk |

### Text CLI Commands

Built-in commands available in text mode: `notices`, `dismiss <id>`, `clear notices`, `pause heartbeat`, `resume heartbeat`, `audit`, `cost`.
