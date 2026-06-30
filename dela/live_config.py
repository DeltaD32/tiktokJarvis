"""Live runtime config — settings that can change without a restart.

config.py loads .env at import time and freezes values as module-level constants.
This module provides a mutable runtime layer on top of those constants. Settings
that are safe to hot-reload are stored here and read by the rest of the system
at call time (not import time).

Categories:
  LIVE (no restart needed):
    - thinking_level     → read by provider on each call
    - compaction_threshold → read by compaction on each check
    - compaction_keep_recent → same
    - voice_mode          → "ptt" or "duplex" (read by voice loop)
    - whisper_model       → reloaded on next STT call
    - whisper_device      → reloaded on next STT call
    - piper_voice         → reloaded on next TTS call
    - vad_aggressiveness  → read by VAD on each frame batch
    - heartbeat interval  → already live via hb_config
    - security scan interval → already live via heartbeat config

  RESTART REQUIRED (can't hot-reload safely):
    - base_url, api_key, model → OpenAI client is constructed per-call, but
      changing these mid-session would break in-flight requests
    - profile → changes CORS middleware (already initialized), tool blocking,
      system prompt structure
    - tracing config → headers are baked into client construction
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from dela import config

_lock = threading.Lock()

# Live overrides — keyed by setting name, value is the live value
# None means "use config.py default"
_overrides: dict[str, Any] = {}

# Which settings can be changed live
LIVE_SETTINGS = {
    "thinking_level": str,
    "compaction_threshold_chars": int,
    "compaction_keep_recent_chars": int,
    "voice_mode": str,  # "ptt" or "duplex"
    "whisper_model": str,
    "whisper_device": str,
    "piper_voice": str,
    "vad_aggressiveness": int,
    "tts_provider": str,         # "piper" or "kokoro"
    "kokoro_voice": str,         # voice name for Kokoro (e.g. "af_heart")
    "personality": str,          # personality preset key (e.g. "friendly", "professional")
    "model_router_enabled": str,  # "true"/"false" stored as string
    "model_fast": str,            # model name for fast tier
    "model_premium": str,         # model name for premium tier
    "model": str,                 # primary model — hot-reloadable (read by provider on each call)
    "confirmation_threshold": float,  # 0-10, tools with score >= this need HITL approval
    "max_tokens": int,           # max output tokens per turn (default 2048, 0 = unlimited)
}

# Settings that require restart
RESTART_SETTINGS = {
    "base_url", "api_key", "model", "profile",
    "tracing_provider", "tracing_project", "tracing_api_key", "tracing_endpoint",
}

_PERSIST_PATH = Path(__file__).resolve().parent.parent / "dela_state" / "live_settings.json"


def get(key: str, default: Any = None) -> Any:
    """Get a live setting value, falling back to config.py default."""
    with _lock:
        if key in _overrides and _overrides[key] is not None:
            return _overrides[key]
    # Fall back to config.py
    return getattr(config, key.upper(), default)


def set(key: str, value: Any) -> bool:
    """Set a live setting. Returns True if the key is a live setting."""
    if key not in LIVE_SETTINGS:
        return False
    expected_type = LIVE_SETTINGS[key]
    try:
        if expected_type is int:
            value = int(value)
        elif expected_type is str:
            value = str(value)
    except (ValueError, TypeError):
        return False
    with _lock:
        _overrides[key] = value
    _persist()
    return True


def reset(key: str) -> None:
    """Reset a live setting to its config.py default."""
    with _lock:
        _overrides.pop(key, None)
    _persist()


def all_live() -> dict[str, Any]:
    """Return all live settings with their current effective values."""
    result = {}
    for key in LIVE_SETTINGS:
        result[key] = get(key)
    return result


def all_overrides() -> dict[str, Any]:
    """Return only the settings that have been overridden (not defaults)."""
    with _lock:
        return dict(_overrides)


def get_override(key: str) -> Any:
    """Return the live override value for a key, or None if not overridden.

    Unlike `get()`, this does NOT fall back to config.py defaults — it only
    returns a value when the user has explicitly set a live override.
    """
    with _lock:
        return _overrides.get(key)


def is_live(key: str) -> bool:
    return key in LIVE_SETTINGS


def _persist() -> None:
    """Save overrides to disk so they survive restarts."""
    try:
        _PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            data = dict(_overrides)
        _PERSIST_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load() -> None:
    """Load persisted overrides on startup."""
    try:
        if _PERSIST_PATH.exists():
            data = json.loads(_PERSIST_PATH.read_text(encoding="utf-8"))
            with _lock:
                for k, v in data.items():
                    if k in LIVE_SETTINGS:
                        _overrides[k] = v
    except Exception:
        pass


# Load on import
_load()
