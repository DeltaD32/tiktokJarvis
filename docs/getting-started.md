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
- **An LLM endpoint** — one of:
  - **Cloud API** — any OpenAI-compatible endpoint (OpenAI, OpenCode GO, Anthropic, etc.)
  - **Ollama (fully offline)** — install from [ollama.com](https://ollama.com), pull a model, run `ollama serve`

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

### Option A: Cloud API

| Variable | Required | Description |
|---|---|---|
| `DELA_BASE_URL` | Yes | OpenAI-compatible endpoint |
| `DELA_API_KEY` | Yes | API key |
| `DELA_MODEL` | Yes | Model name |
| `DELA_PROFILE` | No | `personal` (default), `work`, or `offline` |

### Option B: Fully Offline with Ollama

1. Install [Ollama](https://ollama.com)
2. Pull a model: `ollama pull llama3.1` (or `qwen2.5`, `phi3`, `mistral`, etc.)
3. Start the server: `ollama serve`
4. Set in `.env`:

```env
DELA_PROFILE=offline
DELA_OFFLINE_BASE_URL=http://localhost:11434/v1
DELA_OFFLINE_API_KEY=ollama
DELA_OFFLINE_MODEL=llama3.1
```

Everything runs locally — LLM, STT (faster-whisper), TTS (Piper), VAD (webrtcvad). No internet required. The offline profile blocks `fetch_url` and `check_host` since there's no network.

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
