---
title: Configuration
nav_order: 3
---

# Configuration

## Environment Variables (`.env`)

All secrets and runtime settings live in `.env` (git-ignored). Copy `.env.example` to start.

### Core API

| Variable | Default | Description |
|---|---|---|
| `DELA_BASE_URL` | *(required)* | OpenAI-compatible model endpoint (fallback) |
| `DELA_API_KEY` | *(required)* | API key (fallback) |
| `DELA_MODEL` | *(required)* | Model name (fallback) |
| `DELA_NAME` | `Dela` | Assistant name |
| `DELA_PROFILE` | `personal` | `personal` or `work` |

### Profile-Specific API

Each profile can have its own API connection. When a profile-specific var is set, it overrides the generic `DELA_*` var for that profile.

| Variable | Description |
|---|---|
| `DELA_PERSONAL_BASE_URL` | Personal profile API endpoint |
| `DELA_PERSONAL_API_KEY` | Personal profile API key |
| `DELA_PERSONAL_MODEL` | Personal profile model (e.g. `glm-5.2`) |
| `DELA_WORK_BASE_URL` | Work profile API endpoint |
| `DELA_WORK_API_KEY` | Work profile API key |
| `DELA_WORK_MODEL` | Work profile model (e.g. `claude-sonnet-4-6`) |

### Voice

| Variable | Default | Description |
|---|---|---|
| `DELA_MODELS_DIR` | `models/` | Where to cache Whisper and Piper models |
| `DELA_WHISPER_MODEL` | `small.en` | Whisper model size |
| `DELA_WHISPER_DEVICE` | `cuda` | `cuda` or `cpu` |
| `DELA_WHISPER_COMPUTE` | `float16` | `float16` (CUDA) or `int8` (CPU) |
| `DELA_PIPER_VOICE` | `en_US-amy-medium` | Piper voice ID |
| `DELA_VAD_AGGRESSIVENESS` | `3` | VAD sensitivity (0=least, 3=most) |

### Thinking & Compaction

| Variable | Default | Description |
|---|---|---|
| `DELA_THINKING_LEVEL` | *(empty)* | `off`/`minimal`/`low`/`medium`/`high`/`xhigh` |
| `DELA_COMPACTION_THRESHOLD_CHARS` | `100000` | Auto-summarize threshold |
| `DELA_COMPACTION_KEEP_RECENT_CHARS` | `20000` | Recent context to keep |

### Tracing

| Variable | Default | Description |
|---|---|---|
| `DELA_TRACING_PROVIDER` | *(empty)* | `langsmith` or `langfuse` |
| `DELA_TRACING_PROJECT` | `dela` | Tracing project name |
| `DELA_TRACING_API_KEY` | *(empty)* | Tracing API key |
| `DELA_TRACING_ENDPOINT` | *(empty)* | Tracing endpoint |

---

## Profile System

Three profiles for different contexts. Stored in `.env` as `DELA_PROFILE`. Switchable via the Settings panel (requires restart).

| Feature | Personal | Work | Offline |
|---|---|---|---|
| **Description** | Full access, standard security | Enterprise-grade, restricted | Fully local, no internet |
| **CORS** | Wildcard (local dev) | Approved origins only | Wildcard (local dev) |
| **Tools blocked** | None | `fetch_url` | `fetch_url`, `check_host` |
| **Extra confirmation** | None | `run_security_scan`, `dispatch_subagent`, `dispatch_system_expert`, `create_project`, `create_blackboard` | None |
| **Injection defense** | Standard | Maximum (8 absolute rules) | Standard |
| **Audit level** | Normal | Verbose | Normal |
| **WIZ integration** | Off | On (hook ready) | Off |
| **Web fetch** | Allowed | Blocked | Blocked |
| **API connection** | `DELA_PERSONAL_*` vars | `DELA_WORK_*` vars | `DELA_OFFLINE_*` vars |

- **File:** `dela/profiles.py`
- **Switch:** Settings panel → Profile tab, or edit `.env` and restart
- **Ollama status:** Settings panel → Profile tab shows live Ollama server status + available models

### Offline Mode with Ollama

Dela runs fully offline with [Ollama](https://ollama.com) as the LLM provider:

1. Install Ollama: `https://ollama.com`
2. Pull a model: `ollama pull llama3.1` (or `qwen2.5`, `phi3`, `mistral`, etc.)
3. Start the server: `ollama serve`
4. Set in `.env`:

```env
DELA_PROFILE=offline
DELA_OFFLINE_BASE_URL=http://localhost:11434/v1
DELA_OFFLINE_API_KEY=ollama
DELA_OFFLINE_MODEL=llama3.1
```

Everything runs locally:
- **LLM**: Ollama (OpenAI-compatible endpoint at `localhost:11434/v1`)
- **STT**: faster-whisper on your GPU
- **TTS**: Piper on CPU
- **VAD**: webrtcvad

The `start_dela.py` preflight checks detect Ollama automatically and list available models. The Settings panel shows Ollama status and model list.

### Profile-Specific API

Each profile can have its own API connection. When a profile-specific var is set, it overrides the generic `DELA_*` var for that profile.

| Variable | Description |
|---|---|
| `DELA_PERSONAL_BASE_URL` | Personal profile API endpoint |
| `DELA_PERSONAL_API_KEY` | Personal profile API key |
| `DELA_PERSONAL_MODEL` | Personal profile model (e.g. `glm-5.2`) |
| `DELA_WORK_BASE_URL` | Work profile API endpoint |
| `DELA_WORK_API_KEY` | Work profile API key |
| `DELA_WORK_MODEL` | Work profile model (e.g. `claude-sonnet-4-6`) |
| `DELA_OFFLINE_BASE_URL` | Offline profile API endpoint (default: `http://localhost:11434/v1`) |
| `DELA_OFFLINE_API_KEY` | Offline profile API key (default: `ollama`) |
| `DELA_OFFLINE_MODEL` | Offline profile model (default: `llama3.1`) |

---

## Live Settings (Hot-Reload)

11 settings can be changed at runtime without restarting Dela. They persist to `dela_state/live_settings.json` and survive restarts.

| Setting | Type | How it applies | Default |
|---|---|---|---|
| `thinking_level` | str | Next model call reads live value | from `.env` |
| `compaction_threshold_chars` | int | Next compaction check | `100000` |
| `compaction_keep_recent_chars` | int | Next compaction check | `20000` |
| `voice_mode` | str | Voice loop checks on next session (`ptt` or `duplex`) | `ptt` |
| `whisper_model` | str | Reloaded on next STT call | `small.en` |
| `whisper_device` | str | Reloaded on next STT call | `cuda` |
| `piper_voice` | str | Reloaded on next TTS call | `en_US-amy-medium` |
| `vad_aggressiveness` | int | Applied to next VAD instance | `3` |
| `model_router_enabled` | str | Enable model routing (`true`/`false`) | `false` |
| `model_fast` | str | Model for trivial tasks | from `.env` |
| `model_premium` | str | Model for complex tasks | from `.env` |

**Still require restart:** `base_url`, `api_key`, `model`, `profile`, tracing config. These are baked into the OpenAI client or CORS middleware at startup.

- **File:** `dela/live_config.py`
- **REST:** `GET/PUT/DELETE /api/settings/live`
- **UI:** Settings panel shows a green **LIVE** badge on hot-reloadable fields with a reset button

---

## Heartbeat Config (`heartbeat_config.json`)

6 checks with independent intervals, targets, and quiet hours. Edit the JSON — no code changes.

```json
{
  "heartbeat_interval_seconds": 30,
  "quiet_hours": { "enabled": true, "start": "22:00", "end": "08:00" },
  "checks": { ... }
}
```

→ **[Full heartbeat details](security#heartbeat)**

---

## Model Router

The model router auto-selects the best model for each task based on complexity. Configurable via live settings:

| Setting | Description |
|---|---|
| `model_router_enabled` | `true` to enable auto-routing, `false` to use default model for all |
| `model_fast` | Model name for trivial tasks (math, formatting, lookups) |
| `model_premium` | Model name for complex tasks (coding, architecture, analysis) |

When enabled, the router classifies each request using signals like input length, code blocks, keywords, and tool usage. Trivial tasks route to the fast model, complex tasks to premium, everything else uses the default.

- **File:** `dela/model_router.py`
- **REST:** `GET /api/model-router/classify?text=...` — see routing decision for any text
- **UI:** Settings panel → Router tab
