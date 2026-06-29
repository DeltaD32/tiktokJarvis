import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = ROOT / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


def _require(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "" or val == "replace-me":
        raise RuntimeError(
            f"Missing required env var {name}. Copy .env.example to .env and fill it in."
        )
    return val


def _optional(name: str, default: str) -> str:
    return os.getenv(name, default)


# Profile-specific API config.
# Each profile can have its own base_url, api_key, and model.
# Falls back to the generic DELA_* vars if profile-specific ones aren't set.
_PROFILE = _optional("DELA_PROFILE", "personal").lower()

def _profile_env(suffix: str, generic_key: str, default: str | None = None) -> str:
    """Get a profile-specific env var, falling back to the generic one."""
    profile_key = f"DELA_{_PROFILE.upper()}_{suffix}"
    val = os.getenv(profile_key)
    if val and val != "replace-me":
        return val
    return _require(generic_key, default)

BASE_URL = _profile_env("BASE_URL", "DELA_BASE_URL")
API_KEY = _profile_env("API_KEY", "DELA_API_KEY")
MODEL = _profile_env("MODEL", "DELA_MODEL")

NAME = _optional("DELA_NAME", "Dela")

# Voice (Tier 3) — fully local stack: faster-whisper (STT) + Piper (TTS) + webrtcvad.
# No API keys required. Models live on disk under DELA_MODELS_DIR.
MODELS_DIR = _optional("DELA_MODELS_DIR", str(ROOT / "models"))
WHISPER_MODEL = _optional("DELA_WHISPER_MODEL", "small.en")
WHISPER_DEVICE = _optional("DELA_WHISPER_DEVICE", "cuda")
WHISPER_COMPUTE = _optional("DELA_WHISPER_COMPUTE", "float16")
PIPER_VOICE = _optional("DELA_PIPER_VOICE", "en_US-amy-medium")
VAD_AGGRESSIVENESS = int(_optional("DELA_VAD_AGGRESSIVENESS", "3"))

# Compaction (auto-summarize when conversation gets long)
COMPACTION_THRESHOLD_CHARS = int(_optional("DELA_COMPACTION_THRESHOLD_CHARS", "100000"))
COMPACTION_KEEP_RECENT_CHARS = int(_optional("DELA_COMPACTION_KEEP_RECENT_CHARS", "20000"))

# Thinking level (off/minimal/low/medium/high/xhigh — model-dependent)
THINKING_LEVEL = _optional("DELA_THINKING_LEVEL", "")  # empty = don't send

# Tracing (optional). Set PROVIDER to "langsmith" or "langfuse" to enable.
TRACING_PROVIDER = _optional("DELA_TRACING_PROVIDER", "")  # "" = disabled
TRACING_PROJECT = _optional("DELA_TRACING_PROJECT", "dela")
TRACING_API_KEY = _optional("DELA_TRACING_API_KEY", "")
TRACING_ENDPOINT = _optional("DELA_TRACING_ENDPOINT", "")


def describe() -> str:
    return json.dumps(
        {
            "name": NAME,
            "model": MODEL,
            "base_url": BASE_URL,
            "stt": f"faster-whisper/{WHISPER_MODEL} on {WHISPER_DEVICE}",
            "tts": f"piper/{PIPER_VOICE}",
            "tracing": TRACING_PROVIDER or "disabled",
        },
        indent=2,
    )
