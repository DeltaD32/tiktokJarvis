"""Load channels_config.json — all IM channel settings in one file.

Each channel has its own config block with secrets referenced by env var name
(not the secret itself). Editing a setting = a one-line JSON edit, no code change.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_CFG_PATH = Path(__file__).resolve().parent.parent.parent / "channels_config.json"


def load() -> dict[str, Any]:
    if not _CFG_PATH.exists():
        return {"channels": {}}
    try:
        return json.loads(_CFG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"channels": {}}


def get_channel(name: str) -> dict[str, Any]:
    return load().get("channels", {}).get(name, {})


def is_enabled(name: str) -> bool:
    return get_channel(name).get("enabled", False)


def resolve_env(value: str | None, env_key: str | None) -> str:
    """If env_key is set, read from environment; else return value directly."""
    if env_key:
        return os.getenv(env_key, "")
    return value or ""


def resolve_secret(config: dict[str, Any], key: str) -> str:
    """Resolve a secret: try {key}_env first, then the key itself."""
    env_key = config.get(f"{key}_env")
    if env_key:
        return os.getenv(env_key, "")
    return config.get(key, "")


def path() -> Path:
    return _CFG_PATH