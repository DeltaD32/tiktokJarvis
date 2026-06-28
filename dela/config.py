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


BASE_URL = _require("DELA_BASE_URL")
API_KEY = _require("DELA_API_KEY")
MODEL = _require("DELA_MODEL")

NAME = _optional("DELA_NAME", "Dela")

# Voice (Tier 3) — fully local stack: faster-whisper (STT) + Piper (TTS) + webrtcvad.
# No API keys required. Models live on disk under DELA_MODELS_DIR.
MODELS_DIR = _optional("DELA_MODELS_DIR", str(ROOT / "models"))
WHISPER_MODEL = _optional("DELA_WHISPER_MODEL", "small.en")
WHISPER_DEVICE = _optional("DELA_WHISPER_DEVICE", "cuda")
WHISPER_COMPUTE = _optional("DELA_WHISPER_COMPUTE", "float16")
PIPER_VOICE = _optional("DELA_PIPER_VOICE", "en_US-amy-medium")
VAD_AGGRESSIVENESS = int(_optional("DELA_VAD_AGGRESSIVENESS", "3"))


def describe() -> str:
    return json.dumps(
        {
            "name": NAME,
            "model": MODEL,
            "base_url": BASE_URL,
            "stt": f"faster-whisper/{WHISPER_MODEL} on {WHISPER_DEVICE}",
            "tts": f"piper/{PIPER_VOICE}",
        },
        indent=2,
    )
