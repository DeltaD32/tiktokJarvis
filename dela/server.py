"""FastAPI/WebSocket server — thin bridge between the Dela backend and a web frontend.

Run:
    uvicorn dela.server:app --port 8000 --reload

The frontend connects to ws://localhost:8000/ws for real-time events and
calls REST endpoints under /api/ for state reads/writes.
"""
from __future__ import annotations

import asyncio
import json
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dela import audit, heartbeat, memory, noticeboard
from dela.brain import respond
from dela.gate import Confirmer, set_confirmer
from dela.tools import registry
from dela.channels.config import is_enabled, load as load_channels_config
from dela.profiles import get_current_profile

# ── Global state (single-user local app) ─────────────────────────────────────
_main_loop: asyncio.AbstractEventLoop | None = None

_profile = get_current_profile()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _main_loop
    _main_loop = asyncio.get_event_loop()
    set_confirmer(WebSocketConfirmer())
    heartbeat.start()
    try:
        from dela import oauth
        oauth.start_monitor()
    except Exception:
        pass
    # Register agent status → WebSocket broadcast
    from dela import agent_status
    def _on_agent_status(name, state, task):
        asyncio.run_coroutine_threadsafe(
            _broadcast({"type": "agent_status", "agent": name, "state": state, "task": task[:80] if task else ""}),
            _main_loop,
        )
    agent_status.on_change(_on_agent_status)
    yield
    heartbeat.stop()
    heartbeat.stop()
    try:
        from dela import oauth
        oauth.stop_monitor()
    except Exception:
        pass


app = FastAPI(title="Dela", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_profile.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

_clients: set[WebSocket] = set()
_history: list[dict] = []
_confirm_callbacks: dict[str, threading.Event] = {}
_confirm_results: dict[str, bool] = {}
_brain_lock = threading.Lock()
_oauth_refresh_times: dict[str, float] = {}

# ── Broadcast helpers ─────────────────────────────────────────────────────────

async def _broadcast(payload: dict) -> None:
    dead = set()
    for ws in _clients:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


def broadcast_sync(payload: dict) -> None:
    """Thread-safe broadcast from synchronous tool/gate code."""
    if _main_loop and _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast(payload), _main_loop)


# Register broadcast with ui_tools so show_panel can reach connected clients
from dela.tools import ui_tools as _ui_tools  # noqa: E402
_ui_tools._broadcast_fn = broadcast_sync

# Register notice hook so new heartbeat notices push to connected clients
def _on_notice(notice: dict) -> None:
    broadcast_sync({"type": "notice", "notice": notice})
    broadcast_sync({"type": "notices_refresh", "notices": noticeboard.active()})

noticeboard.set_on_file_hook(_on_notice)

# ── Confirmation bridge ───────────────────────────────────────────────────────

class WebSocketConfirmer:
    """Routes confirmation requests through the browser's confirmation dialog."""

    def confirm(self, description: str, timeout: float | None = None) -> bool:
        cid = str(uuid.uuid4())
        event = threading.Event()
        _confirm_callbacks[cid] = event
        _confirm_results[cid] = False

        broadcast_sync({"type": "confirmation_request", "id": cid, "description": description})

        granted = event.wait(timeout=timeout if timeout is not None else 30.0)
        _confirm_callbacks.pop(cid, None)
        result = _confirm_results.pop(cid, False)
        return granted and result


# Lifecycle handled by the `lifespan` context manager above (FastAPI ≥ 0.109).


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/api/memory")
def api_get_memory():
    return memory.load()


@app.post("/api/memory")
def api_add_memory(body: dict):
    text = body.get("text")
    if not text:
        return {"ok": False, "error": "Missing 'text' field"}
    return memory.add(text, body.get("category", "general"))


@app.delete("/api/memory/{fact_id}")
def api_del_memory(fact_id: int):
    return {"ok": memory.remove(fact_id)}


@app.get("/api/notices")
def api_get_notices():
    return noticeboard.active()


@app.delete("/api/notices/{notice_id}")
def api_dismiss_notice(notice_id: int):
    return {"ok": noticeboard.dismiss(notice_id)}


@app.get("/api/audit")
def api_get_audit(n: int = 60):
    return {"log": audit.tail(n), "cost": audit.cost_summary()}


@app.post("/api/heartbeat/kill")
def api_hb_kill():
    heartbeat.kill()
    broadcast_sync({"type": "heartbeat_state", "active": False})
    return {"ok": True}


@app.post("/api/heartbeat/resume")
def api_hb_resume():
    heartbeat.resume()
    broadcast_sync({"type": "heartbeat_state", "active": True})
    return {"ok": True}


@app.get("/api/tasks")
def api_get_tasks():
    from dela.tools.project import _load
    return _load()


@app.get("/api/tools")
def api_get_tools():
    return [
        {
            "name": t.name,
            "description": t.description,
            "requires_confirmation": t.requires_confirmation,
            "param_count": len(t.parameters.get("properties", {})),
        }
        for t in registry.all()
    ]


@app.get("/api/agents")
def api_get_agents():
    from dela.agents import list_agents
    from dela.agent_status import all_status, init_agents
    # Initialize status for all registered agents (sets them to "ready")
    init_agents([a.name for a in list_agents()])
    statuses = all_status()
    return [
        {
            "name": a.name,
            "description": a.description,
            "tool_count": len(a.tool_whitelist) if a.tool_whitelist else "all",
            "tools": sorted(a.tool_whitelist) if a.tool_whitelist else None,
            "status": statuses.get(a.name, {}).get("state", "ready"),
            "last_task": statuses.get(a.name, {}).get("last_task", ""),
            "last_dispatch_ago_s": statuses.get(a.name, {}).get("last_dispatch_ago_s"),
            "dispatch_count": statuses.get(a.name, {}).get("dispatch_count", 0),
        }
        for a in list_agents()
    ]

@app.get("/api/status")
def api_status():
    return {
        "heartbeat_active": not heartbeat.is_killed(),
        "cost": audit.cost_summary(),
        "notice_count": len(noticeboard.active()),
    }


@app.get("/api/analytics")
def api_analytics():
    """Return structured analytics: model calls, tool calls, gate decisions, per-tool usage."""
    return audit.analytics()


@app.get("/api/models")
def api_list_models_endpoint():
    """List available models from the current provider's models endpoint.

    Uses the active connection for the current profile (so OAuth/custom-header
    endpoints work too). Returns a list of model IDs. Useful for live model
    switching.
    """
    import time
    from dela import live_config
    from dela.profiles import get_current_profile_name
    from dela import connections
    from dela.provider import _effective_model

    conn = connections.get_active()
    base_url = conn.get("base_url", "")
    t0 = time.time()
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url=base_url,
            api_key=conn.get("api_key") or "missing",
            default_headers=conn.get("extra_headers") or None,
            timeout=10,
        )
        models = client.models.list()
        model_ids = sorted([m.id for m in models.data])
        current = _effective_model()
        latency = round((time.time() - t0) * 1000)
        return {
            "status": "ok",
            "profile": get_current_profile_name(),
            "connection": conn.get("name", ""),
            "base_url": base_url,
            "current": current,
            "count": len(model_ids),
            "models": model_ids,
            "latency_ms": latency,
        }
    except Exception as e:
        return {
            "status": "error",
            "profile": get_current_profile_name(),
            "connection": conn.get("name", ""),
            "base_url": base_url,
            "current": _effective_model(),
            "count": 0,
            "models": [],
            "error": str(e)[:200],
            "latency_ms": round((time.time() - t0) * 1000),
        }


@app.get("/api/uplink")
def api_uplink():
    """Check API connection + auth status for the active profile connection."""
    import time
    from dela import connections
    from dela.profiles import get_current_profile_name
    from dela.provider import _effective_model

    conn = connections.get_active()
    base_url = conn.get("base_url", "")
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url=base_url,
            api_key=conn.get("api_key") or "missing",
            default_headers=conn.get("extra_headers") or None,
            timeout=10,
        )
    except Exception as e:
        return {
            "status": "error",
            "profile": get_current_profile_name(),
            "connection": conn.get("name", ""),
            "model": _effective_model(),
            "base_url": base_url,
            "error": str(e)[:200],
            "latency_ms": 0,
        }

    t0 = time.time()
    try:
        client.models.list()
        latency = round((time.time() - t0) * 1000)
        return {
            "status": "connected",
            "profile": get_current_profile_name(),
            "connection": conn.get("name", ""),
            "model": _effective_model(),
            "base_url": base_url,
            "latency_ms": latency,
        }
    except Exception as e:
        latency = round((time.time() - t0) * 1000)
        err_str = str(e)
        if "401" in err_str or "auth" in err_str.lower() or "api key" in err_str.lower() or "token" in err_str.lower():
            status = "auth_error"
        elif "connection" in err_str.lower() or "timeout" in err_str.lower() or "unreachable" in err_str.lower():
            status = "unreachable"
        else:
            status = "error"
        return {
            "status": status,
            "profile": get_current_profile_name(),
            "connection": conn.get("name", ""),
            "model": _effective_model(),
            "base_url": base_url,
            "error": err_str[:200],
            "latency_ms": latency,
        }


@app.get("/api/ollama/status")
def api_ollama_status():
    """Check if Ollama is running locally and list available models."""
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            headers={"User-Agent": "Dela/0.1"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                import json as _json
                data = _json.loads(resp.read())
                models = []
                for m in data.get("models", []):
                    models.append({
                        "name": m.get("name", "?"),
                        "size_gb": round(m.get("size", 0) / 1e9, 1),
                        "modified": m.get("modified_at", ""),
                    })
                return {
                    "status": "running",
                    "url": "http://localhost:11434",
                    "models": models,
                    "model_count": len(models),
                }
    except urllib.error.URLError:
        return {
            "status": "not_running",
            "url": "http://localhost:11434",
            "models": [],
            "model_count": 0,
            "hint": "Install from https://ollama.com, then run: ollama serve",
        }
    except Exception as e:
        return {
            "status": "error",
            "url": "http://localhost:11434",
            "models": [],
            "model_count": 0,
            "error": str(e)[:200],
        }


# ── Voice endpoints (web STT/TTS) ─────────────────────────────────────────────

def _decode_with_pyav(audio_bytes: bytes) -> bytes | None:
    """Decode audio bytes (WebM/Opus, WAV, etc.) to raw 16-bit 16kHz mono PCM using PyAV.
    Returns None if PyAV is not available or decoding fails.
    """
    import io
    try:
        import av
        container = av.open(io.BytesIO(audio_bytes), "r")
        audio_stream = next((s for s in container.streams if s.type == "audio"), None)
        if audio_stream is None:
            return None

        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        chunks: list[bytes] = []
        for packet in container.demux(audio_stream):
            for frame in packet.decode():
                for resampled in resampler.resample(frame):
                    arr = resampled.to_ndarray()
                    if arr.ndim > 1:
                        arr = arr.ravel()
                    chunks.append(arr.tobytes())
        if not chunks:
            return None
        return b"".join(chunks)
    except Exception:
        return None


def _decode_with_ffmpeg(audio_bytes: bytes) -> bytes | None:
    """Decode audio bytes to raw 16-bit 16kHz mono PCM using system ffmpeg binary.
    Returns None if ffmpeg is not installed or decoding fails.
    """
    import subprocess, tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp_in:
        tmp_in.write(audio_bytes)
        tmp_in_path = tmp_in.name
    tmp_out_path = tmp_in_path.replace(".webm", ".wav")
    try:
        subprocess.run(
            ["ffmpeg", "-i", tmp_in_path, "-ar", "16000", "-ac", "1", "-f", "wav", tmp_out_path],
            capture_output=True, timeout=10, check=True,
        )
        from dela.stt import wav_to_pcm
        with open(tmp_out_path, "rb") as f:
            wav_bytes = f.read()
        return wav_to_pcm(wav_bytes)
    except Exception:
        return None
    finally:
        for p in (tmp_in_path, tmp_out_path):
            try:
                os.unlink(p)
            except Exception:
                pass


@app.post("/api/voice/stt")
async def api_voice_stt(request: Request):
    """Receive audio from the browser, transcribe with faster-whisper."""
    from dela.stt import transcribe, wav_to_pcm, STTError

    MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB — ~5 min of 16kHz mono
    file = await request.body()
    if not file:
        return {"text": "", "ok": False, "error": "No audio data received."}
    if len(file) > MAX_UPLOAD_BYTES:
        return {"text": "", "ok": False, "error": f"Audio too large (max {MAX_UPLOAD_BYTES // 1024 // 1024} MB)."}

    # Try to parse as WAV first; if that fails, try PyAV, then ffmpeg
    try:
        pcm = wav_to_pcm(file)
        print("  [stt] decoded as WAV")
    except Exception:
        pcm = _decode_with_pyav(file)
        if pcm is not None:
            print("  [stt] decoded with PyAV")
        if pcm is None:
            pcm = _decode_with_ffmpeg(file)
            if pcm is not None:
                print("  [stt] decoded with ffmpeg")
            if pcm is None:
                return {"text": "", "ok": False, "error": "Audio is not WAV and no decoder is available (install ffmpeg)."}

    try:
        text = transcribe(pcm)
        print(f"  [stt] transcribed: {text[:100]}")
        return {"text": text, "ok": True}
    except STTError as e:
        print(f"  [stt] error: {e}")
        return {"text": "", "ok": False, "error": str(e)}


@app.post("/api/voice/tts")
async def api_voice_tts(body: dict):
    """Synthesize text to WAV audio for browser playback."""
    from dela.tts import synthesize_wav as piper_synthesize, TTSError

    text = body.get("text", "")
    if not text.strip():
        return {"ok": False, "error": "No text provided."}

    MAX_TTS_CHARS = 5000
    if len(text) > MAX_TTS_CHARS:
        text = text[:MAX_TTS_CHARS]

    # Route to the selected TTS provider
    provider = live_config.get("tts_provider") or config.TTS_PROVIDER

    if provider == "kokoro":
        try:
            from dela.tts_kokoro import synthesize_wav as kokoro_synthesize
            voice = live_config.get("kokoro_voice") or config.KOKORO_VOICE
            wav_bytes = kokoro_synthesize(text, voice=voice)
            if not wav_bytes:
                return {"ok": False, "error": "Kokoro synthesis produced no audio."}
            return Response(content=wav_bytes, media_type="audio/wav")
        except Exception as e:
            # Fall back to Piper if Kokoro fails (not installed, model missing, etc.)
            print(f"  [tts] Kokoro failed ({e}), falling back to Piper")

    try:
        wav_bytes = piper_synthesize(text)
        if not wav_bytes:
            return {"ok": False, "error": "Synthesis produced no audio."}
        return Response(content=wav_bytes, media_type="audio/wav")
    except TTSError as e:
        return {"ok": False, "error": str(e)}


# ── State Browser endpoints ───────────────────────────────────────────────────

@app.get("/api/state/search")
def api_search_state(q: str, limit: int = 20):
    from dela.state_browser import search_state
    return search_state(q, limit=limit)

@app.get("/api/state")
def api_list_state_types():
    from dela.state_browser import list_state_types
    return list_state_types()

@app.get("/api/state/{stype}")
def api_read_state(stype: str, item_id: str | None = None, limit: int = 50):
    from dela.state_browser import read_state
    return read_state(stype, item_id=item_id, limit=limit)

@app.get("/api/state/{stype}/{item_id}")
def api_read_state_item(stype: str, item_id: str):
    from dela.state_browser import read_state
    return read_state(stype, item_id=item_id)

@app.put("/api/state/{stype}/{item_id}")
def api_edit_state(stype: str, item_id: str, body: dict):
    from dela.state_browser import edit_state
    return edit_state(stype, item_id, body)


# ── Security endpoints ────────────────────────────────────────────────────────

@app.get("/api/security")
def api_security_status():
    from dela.security import last_scan
    return last_scan()

@app.post("/api/security/scan")
def api_security_scan():
    from dela.security import run_full_scan
    return run_full_scan()

@app.get("/api/vuln-kb")
def api_vuln_kb():
    from dela.vuln_kb import get_kb_info
    return get_kb_info()

@app.post("/api/vuln-kb/refresh")
def api_vuln_kb_refresh():
    from dela.vuln_kb import refresh
    return refresh()

@app.post("/api/security/fix")
def api_security_fix(req: dict):
    """Dispatch the system_expert agent to analyze a security finding and recommend/implement a fix."""
    finding_title = req.get("finding_title", "")
    finding_detail = req.get("finding_detail", "")
    finding_category = req.get("finding_category", "")
    finding_priority = req.get("finding_priority", "")
    auto_apply = req.get("auto_apply", False)

    if not finding_title:
        return {"error": "finding_title is required"}

    from dela.agents import get_agent
    from dela.brain import run_subagent
    from dela.agent_status import mark_busy, mark_ready, mark_error

    soul = get_agent("system_expert")
    if soul is None:
        return {"error": "system_expert agent not available"}

    task = (
        f"SECURITY FINDING TO FIX:\n"
        f"  Title: {finding_title}\n"
        f"  Category: {finding_category}\n"
        f"  Priority: {finding_priority}\n"
        f"  Detail: {finding_detail}\n\n"
        f"Analyze this security finding in Dela's codebase. Use run_code to inspect the relevant files. "
        f"Then {'implement the fix directly' if auto_apply else 'recommend a specific fix with code changes'}. "
        f"Identify the exact file(s) and line(s) that need to change, explain the vulnerability, "
        f"and provide the patched code. Follow Dela's patterns: one module per capability, "
        f"errors as results, confirmation gate on consequential changes."
    )

    mark_busy("system_expert", f"Security fix: {finding_title[:60]}")
    try:
        prompt = soul.build_prompt()
        result = run_subagent(
            agent_name="system_expert",
            task=task,
            system_prompt_text=prompt,
            tool_whitelist=soul.tool_whitelist,
        )
        mark_ready("system_expert")
        return {"result": result, "finding": finding_title}
    except Exception as e:
        mark_error("system_expert", str(e))
        return {"error": str(e)}


# ── Workflow endpoints ────────────────────────────────────────────────────────

@app.get("/api/workflows")
def api_list_workflows():
    from dela.workflows import list_workflows
    return list_workflows()

@app.get("/api/workflows/{name}")
def api_get_workflow(name: str):
    from dela.workflows import load_workflow
    wf = load_workflow(name)
    if wf is None:
        return {"error": f"Workflow '{name}' not found"}
    return wf

@app.post("/api/workflows")
def api_save_workflow(req: dict):
    from dela.workflows import save_workflow
    name = save_workflow(req)
    return {"name": name, "steps": len(req.get("steps", []))}

@app.delete("/api/workflows/{name}")
def api_delete_workflow(name: str):
    from dela.workflows import delete_workflow
    if delete_workflow(name):
        return {"deleted": name}
    return {"error": f"Workflow '{name}' not found"}

@app.post("/api/workflows/{name}/run")
def api_run_workflow(name: str, req: dict = None):
    from dela.workflows import execute_workflow
    result = execute_workflow(name, req or {})
    return result

@app.get("/api/model-router/classify")
def api_model_router_classify(text: str = ""):
    from dela.model_router import get_routing_info
    from dela import live_config
    if not text:
        return {"error": "Provide 'text' query parameter"}
    info = get_routing_info(text)
    info["router_enabled"] = live_config.get("model_router_enabled", False)
    info["fast_model"] = live_config.get("model_fast", "")
    info["premium_model"] = live_config.get("model_premium", "")
    return info


# ── Settings endpoints ────────────────────────────────────────────────────────

@app.get("/api/settings")
def api_get_settings():
    from dela import config, hb_config
    from dela.channels.config import load as load_channels
    from dela.profiles import get_current_profile, list_profiles, get_current_profile_name
    from dela import connections
    return {
        "profile": {
            "current": get_current_profile_name(),
            "available": list_profiles(),
            "active_config": get_current_profile().to_dict(),
        },
        "model": {
            "name": config.NAME,
            "model": config.MODEL,
            "base_url": config.BASE_URL,
            "thinking_level": config.THINKING_LEVEL or "(off)",
        },
        "connection": connections.describe_active(),
        "voice": {
            "whisper_model": config.WHISPER_MODEL,
            "whisper_device": config.WHISPER_DEVICE,
            "whisper_compute": config.WHISPER_COMPUTE,
            "piper_voice": config.PIPER_VOICE,
            "vad_aggressiveness": config.VAD_AGGRESSIVENESS,
        },
        "compaction": {
            "threshold_chars": config.COMPACTION_THRESHOLD_CHARS,
            "keep_recent_chars": config.COMPACTION_KEEP_RECENT_CHARS,
        },
        "tracing": {
            "provider": config.TRACING_PROVIDER or "(disabled)",
            "project": config.TRACING_PROJECT,
        },
        "heartbeat": hb_config.load(),
        "channels": load_channels() if load_channels else {},
        "runtime": {
            "python_version": sys.version.split()[0],
            "tools_count": len(registry.all()),
            "agents_count": len(__import__('dela.agents', fromlist=['list_agents']).list_agents()),
        },
        "live": __import__('dela.live_config', fromlist=['all_live']).all_live(),
        "live_overrides": __import__('dela.live_config', fromlist=['all_overrides']).all_overrides(),
    }

@app.put("/api/settings/heartbeat")
def api_update_heartbeat_setting(body: dict):
    from dela import hb_config
    import json as _json
    ALLOWED = {"interval", "checks"}  # only allow known heartbeat config keys
    filtered = {k: v for k, v in body.items() if k in ALLOWED}
    path = hb_config.path()
    current = hb_config.load()
    current.update(filtered)
    path.write_text(_json.dumps(current, indent=2), encoding="utf-8")
    return {"ok": True, "config": current}

@app.put("/api/settings/env")
def api_update_env_setting(body: dict):
    """Update a .env variable. Requires server restart to take effect."""
    key = body.get("key", "")
    value = body.get("value", "").replace("\n", "").replace("\r", "")  # prevent env injection via newlines
    if not key or not key.startswith("DELA_"):
        return {"ok": False, "error": "Key must start with DELA_"}
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return {"ok": False, "error": ".env file not found"}
    lines = env_path.read_text(encoding="utf-8").splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return {"ok": True, "key": key, "note": "Restart required for changes to take effect."}


@app.put("/api/settings/profile")
def api_switch_profile(body: dict):
    """Switch the security profile. Requires restart."""
    from dela.profiles import set_profile, PROFILES
    name = body.get("profile", "")
    if name not in PROFILES:
        return {"ok": False, "error": f"Unknown profile: {name}. Available: {', '.join(PROFILES.keys())}"}
    success = set_profile(name)
    if success:
        return {"ok": True, "profile": name, "note": "Restart required to apply the new security profile."}
    return {"ok": False, "error": "Could not write to .env file."}


@app.get("/api/settings/live")
def api_get_live_settings():
    """Get all live settings with their current values and whether they're overridden."""
    from dela import live_config
    return {
        "live": live_config.all_live(),
        "overridden": live_config.all_overrides(),
        "available": list(live_config.LIVE_SETTINGS.keys()),
    }


@app.put("/api/settings/live")
def api_update_live_setting(body: dict):
    """Update a live setting. Takes effect immediately — no restart needed."""
    from dela import live_config
    key = body.get("key", "")
    value = body.get("value")
    if not key:
        return {"ok": False, "error": "Missing 'key' field."}
    if not live_config.is_live(key):
        return {"ok": False, "error": f"'{key}' is not a live setting. Live settings: {', '.join(live_config.LIVE_SETTINGS.keys())}"}
    success = live_config.set(key, value)
    if success:
        return {"ok": True, "key": key, "value": live_config.get(key), "note": "Applied immediately — no restart needed."}
    return {"ok": False, "error": f"Could not set '{key}' — check the value type."}


@app.delete("/api/settings/live/{key}")
def api_reset_live_setting(key: str):
    """Reset a live setting to its config.py default."""
    from dela import live_config
    if not live_config.is_live(key):
        return {"ok": False, "error": f"'{key}' is not a live setting."}
    live_config.reset(key)
    return {"ok": True, "key": key, "value": live_config.get(key), "note": "Reset to default."}


# ── API Connections + OAuth endpoints ──────────────────────────────────────────


@app.get("/api/connections")
def api_list_connections():
    """List all configured API connections (secrets masked) and profile assignments."""
    from dela import connections
    data = connections.load()
    return {
        "connections": connections.list_connections(masked=True),
        "assignments": data.get("assignments", {}),
        "active_profile": connections.active_profile_name(),
        "active": connections.describe_active(),
    }


@app.get("/api/connections/{name}")
def api_get_connection(name: str):
    from dela import connections
    conn = connections.get_connection(name)
    if conn is None:
        return {"error": f"Connection '{name}' not found"}
    masked = connections._mask(conn)
    return masked


@app.post("/api/connections")
def api_upsert_connection(body: dict):
    from dela import connections
    # If api_key/secret fields are blank or all-masked, preserve existing secret
    name = (body.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "Connection 'name' is required"}
    existing = connections.get_connection(name) or {}
    preserved = {}
    for secret_field in ("api_key", "oauth_client_secret"):
        v = body.get(secret_field, "")
        if v is None or v == "" or set(str(v)) <= {"*"}:
            preserved[secret_field] = existing.get(secret_field, "")
        else:
            preserved[secret_field] = v
    body.update(preserved)
    try:
        conn = connections.upsert_connection(body)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    # Drop cached oauth token if oauth config changed materially
    if conn.get("auth_type") == "oauth":
        try:
            from dela import oauth
            oauth.force_refresh(conn)
        except Exception:
            pass
    return {"ok": True, "connection": connections._mask(conn)}


@app.delete("/api/connections/{name}")
def api_delete_connection(name: str):
    from dela import connections
    existed = connections.delete_connection(name)
    # Also drop any cached oauth token
    try:
        from dela import oauth
        with oauth._lock:
            oauth._TOKENS.pop(name, None)
        oauth._persist()
    except Exception:
        pass
    return {"ok": existed, "deleted": name if existed else None}


@app.put("/api/connections/assign")
def api_assign_connection(body: dict):
    from dela import connections
    profile = body.get("profile", "")
    conn_name = body.get("connection", "")
    if not profile:
        return {"ok": False, "error": "'profile' is required"}
    ok = connections.assign_connection(profile, conn_name if conn_name else None)
    return {"ok": ok, "profile": profile, "connection": conn_name or None,
            "note": "Applied immediately — next model call uses the new connection."}


@app.post("/api/connections/{name}/test")
def api_test_connection(name: str):
    from dela import connections, oauth
    conn = connections.get_connection(name)
    if conn is None:
        return {"ok": False, "error": f"Connection '{name}' not found"}
    return oauth.test_connection(conn)


@app.get("/api/oauth/status")
def api_oauth_status():
    """OAuth monitor status + per-connection token info for oauth connections."""
    from dela import connections, oauth
    data = connections.load()
    tokens = {}
    for name, c in data.get("connections", {}).items():
        if c.get("auth_type") == "oauth":
            tokens[name] = oauth.token_info(c)
    return {
        "monitor_running": oauth.is_monitor_running(),
        "refresh_margin_s": oauth.REFRESH_MARGIN,
        "tokens": tokens,
    }


@app.post("/api/oauth/refresh")
def api_oauth_refresh(body: dict):
    from dela import connections, oauth
    name = body.get("name", "")
    conn = connections.get_connection(name)
    if conn is None:
        return {"ok": False, "error": f"Connection '{name}' not found"}
    if conn.get("auth_type") != "oauth":
        return {"ok": False, "error": f"Connection '{name}' is not an OAuth connection"}
    # Rate limit: 1 refresh per 60s per connection
    now = time.time()
    last = _oauth_refresh_times.get(name, 0)
    if now - last < 60:
        return {"ok": False, "error": "Rate limited — wait before refreshing again"}
    _oauth_refresh_times[name] = now
    try:
        tok = oauth.force_refresh(conn)
        return {"ok": True, "token_status": oauth.token_info(conn)}
    except Exception as e:
        return {"ok": False, "error": str(e), "token_status": oauth.token_info(conn)}


@app.put("/api/memory/{fact_id}")
def api_update_memory(fact_id: int, body: dict):
    text = body.get("text")
    if not text:
        return {"ok": False, "error": "Missing 'text' field"}
    result = memory.update(fact_id, text)
    if result is None:
        return {"ok": False, "error": f"No fact with id {fact_id}."}
    return {"ok": True, "fact": result}


@app.get("/api/config/heartbeat")
def api_get_hb_config():
    from dela import hb_config
    return hb_config.load()


@app.put("/api/config/heartbeat")
def api_update_hb_config(body: dict):
    from dela import hb_config
    import json as _json
    ALLOWED = {"interval", "checks"}
    filtered = {k: v for k, v in body.items() if k in ALLOWED}
    path = hb_config.path()
    path.write_text(_json.dumps(filtered, indent=2), encoding="utf-8")
    return {"ok": True, "config": filtered}


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    MAX_CLIENTS = 10
    if len(_clients) >= MAX_CLIENTS:
        await ws.accept()
        await ws.send_json({"type": "error", "message": "Too many connections"})
        await ws.close()
        return
    await ws.accept()
    try:
        await ws.send_json({
            "type": "init",
            "notices": noticeboard.active(),
            "heartbeat_active": not heartbeat.is_killed(),
            "cost": audit.cost_summary(),
        })
    except Exception:
        return  # client already gone, don't add to _clients
    _clients.add(ws)
    try:
        while True:
            data = await ws.receive_json()
            t = data.get("type")

            if t == "message":
                await _handle_message(data["content"])
            elif t == "confirm":
                cid = data.get("id", "")
                approved = bool(data.get("approved", False))
                _confirm_results[cid] = approved
                ev = _confirm_callbacks.get(cid)
                if ev:
                    ev.set()
            elif t == "dismiss_notice":
                noticeboard.dismiss(data["id"])
                await _broadcast({"type": "notices_refresh", "notices": noticeboard.active()})
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)


async def _handle_message(user_text: str) -> None:
    if not _brain_lock.acquire(blocking=False):
        await _broadcast({"type": "token", "content": "[Dela is still thinking — please wait]", "tool_blip": False})
        return

    await _broadcast({"type": "state_change", "state": "thinking"})
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    turn_timeout = 300  # 5-minute watchdog

    def _run() -> None:
        try:
            for token in respond(_history, user_text):
                asyncio.run_coroutine_threadsafe(queue.put(token), loop)
        except Exception as e:
            asyncio.run_coroutine_threadsafe(queue.put(f"[error: {e}]"), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)
            try:
                _brain_lock.release()
            except RuntimeError:
                pass  # lock already released by watchdog

    def _watchdog() -> None:
        time.sleep(turn_timeout)
        try:
            _brain_lock.release()
        except RuntimeError:
            pass  # already released normally

    threading.Thread(target=_run, daemon=True).start()
    threading.Thread(target=_watchdog, daemon=True).start()

    token_count = 0
    blip_count = 0
    while True:
        token = await queue.get()
        if token is None:
            break
        # Only tool status messages like "[ran fetch_url]" are tool blips.
        # Error messages like "[error: ...]" or "[I can't reach...]" are real content.
        is_blip = token.startswith("[") and token.endswith("]") and not token.startswith("[error") and not token.startswith("[I can't")
        if is_blip:
            blip_count += 1
        else:
            token_count += 1
        await _broadcast({
            "type": "token",
            "content": token,
            "tool_blip": is_blip,
        })
        if not is_blip:
            await _broadcast({"type": "state_change", "state": "speaking"})

    print(f"  [brain] turn complete: {token_count} text tokens, {blip_count} tool blips, reply_len={sum(len(t) for t in [_history[-1].get('content','')] if _history)}, history_msgs={len(_history)}")

    await _broadcast({"type": "reply_done"})
    await _broadcast({"type": "state_change", "state": "idle"})
    await _broadcast({"type": "cost_update", "cost": audit.cost_summary()})


# ── Static files (production build) ──────────────────────────────────────────

_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")

# ── Channel endpoints ─────────────────────────────────────────────────────────

if is_enabled("teams_webhook"):
    from dela.channels.teams_webhook import register_endpoint as _reg_teams
    _reg_teams(app)
