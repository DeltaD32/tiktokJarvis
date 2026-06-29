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
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dela import audit, heartbeat, memory, noticeboard
from dela.brain import respond
from dela.gate import Confirmer, set_confirmer
from dela.tools import registry
from dela.channels.config import is_enabled, load as load_channels_config

# ── Global state (single-user local app) ─────────────────────────────────────
_main_loop: asyncio.AbstractEventLoop | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _main_loop
    _main_loop = asyncio.get_event_loop()
    set_confirmer(WebSocketConfirmer())
    heartbeat.start()
    yield
    heartbeat.stop()


app = FastAPI(title="Dela", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_clients: set[WebSocket] = set()
_history: list[dict] = []
_confirm_callbacks: dict[str, threading.Event] = {}
_confirm_results: dict[str, bool] = {}
_brain_lock = threading.Lock()

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
    return memory.add(body["text"], body.get("category", "general"))


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
    return [
        {
            "name": a.name,
            "description": a.description,
            "tool_count": len(a.tool_whitelist) if a.tool_whitelist else "all",
            "tools": sorted(a.tool_whitelist) if a.tool_whitelist else None,
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


# ── Settings endpoints ────────────────────────────────────────────────────────

@app.get("/api/settings")
def api_get_settings():
    from dela import config, hb_config
    from dela.channels.config import load as load_channels
    return {
        "model": {
            "name": config.NAME,
            "model": config.MODEL,
            "base_url": config.BASE_URL,
            "thinking_level": config.THINKING_LEVEL or "(off)",
        },
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
    }

@app.put("/api/settings/heartbeat")
def api_update_heartbeat_setting(body: dict):
    from dela import hb_config
    import json as _json
    path = hb_config.path()
    current = hb_config.load()
    current.update(body)
    path.write_text(_json.dumps(current, indent=2), encoding="utf-8")
    return {"ok": True, "config": current}

@app.put("/api/settings/env")
def api_update_env_setting(body: dict):
    """Update a .env variable. Requires server restart to take effect."""
    key = body.get("key", "")
    value = body.get("value", "")
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


@app.put("/api/memory/{fact_id}")
def api_update_memory(fact_id: int, body: dict):
    result = memory.update(fact_id, body["text"])
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
    path = hb_config.path()
    path.write_text(_json.dumps(body, indent=2), encoding="utf-8")
    return {"ok": True, "config": body}


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    await ws.send_json({
        "type": "init",
        "notices": noticeboard.active(),
        "heartbeat_active": not heartbeat.is_killed(),
        "cost": audit.cost_summary(),
    })
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
        _clients.discard(ws)


async def _handle_message(user_text: str) -> None:
    if not _brain_lock.acquire(blocking=False):
        await _broadcast({"type": "token", "content": "[Dela is still thinking — please wait]", "tool_blip": True})
        return

    await _broadcast({"type": "state_change", "state": "thinking"})
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def _run() -> None:
        try:
            for token in respond(_history, user_text):
                asyncio.run_coroutine_threadsafe(queue.put(token), loop)
        except Exception as e:
            asyncio.run_coroutine_threadsafe(queue.put(f"[error: {e}]"), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)
            _brain_lock.release()

    threading.Thread(target=_run, daemon=True).start()

    while True:
        token = await queue.get()
        if token is None:
            break
        is_blip = token.startswith("[") and token.endswith("]")
        await _broadcast({
            "type": "token",
            "content": token,
            "tool_blip": is_blip,
        })
        if not is_blip:
            await _broadcast({"type": "state_change", "state": "speaking"})

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
