"""API connection registry — multiple LLM endpoints, assignable to profiles.

This module lets the user define several API connections (base_url + api_key +
model + optional OAuth) and assign one to each security profile. The active
connection for the current profile is resolved at call time (not import time)
so changes take effect without a restart.

Connection shape:
    {
      "name": "my-cloud",
      "base_url": "https://api.example.com/v1",
      "api_key": "sk-...",
      "model": "glm-5.2",
      "auth_type": "simple" | "oauth",
      # oauth-only fields:
      "oauth_client_id": "...",       # used to request the token
      "oauth_client_secret": "...",
      "oauth_token_url": "https://.../oauth/token",
      "oauth_scopes": "",             # optional
      "oauth_header_name": "x-client-id",  # header carrying clientid to OpenAI endpoint
      # generic:
      "extra_headers": {}             # merged into every request
    }

State lives in dela_state/connections.json. If the file is absent or a profile
has no assignment, we fall back to the config.py defaults (BASE_URL/API_KEY/
MODEL) so existing single-connection setups keep working unchanged.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from dela import config

_lock = threading.Lock()
_STATE_PATH = Path(__file__).resolve().parent.parent / "dela_state" / "connections.json"


def _seed_default() -> dict[str, Any]:
    """Build the default connection from config.py env values."""
    return {
        "name": "(env default)",
        "base_url": config.BASE_URL,
        "api_key": config.API_KEY,
        "model": config.MODEL,
        "auth_type": "simple",
        "extra_headers": {},
    }


def load() -> dict[str, Any]:
    """Load the full registry from disk."""
    try:
        if _STATE_PATH.exists():
            with _lock:
                data = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
            if "connections" not in data:
                data["connections"] = {}
            if "assignments" not in data:
                data["assignments"] = {}
            return data
    except Exception:
        pass
    return {"connections": {}, "assignments": {}}


def save(data: dict[str, Any]) -> None:
    try:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            _STATE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _mask(conn: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a connection with secrets masked, for the API/UI."""
    c = dict(conn)
    if c.get("api_key"):
        c["api_key"] = _mask_secret(c["api_key"])
    if c.get("oauth_client_secret"):
        c["oauth_client_secret"] = _mask_secret(c["oauth_client_secret"])
    return c


def _mask_secret(s: str) -> str:
    if not s:
        return ""
    if len(s) <= 8:
        return "*" * len(s)
    return s[:3] + "*" * (len(s) - 6) + s[-3:]


def list_connections(masked: bool = True) -> list[dict[str, Any]]:
    data = load()
    conns = []
    for name, c in data.get("connections", {}).items():
        conns.append(c if not masked else _mask(c))
    return conns


def get_connection(name: str) -> dict[str, Any] | None:
    data = load()
    return data.get("connections", {}).get(name)


def upsert_connection(conn: dict[str, Any]) -> dict[str, Any]:
    """Create or update a connection by name."""
    name = (conn.get("name") or "").strip()
    if not name:
        raise ValueError("Connection must have a 'name'")
    conn["name"] = name
    conn.setdefault("auth_type", "simple")
    conn.setdefault("extra_headers", {})
    if conn["auth_type"] == "oauth":
        conn.setdefault("oauth_header_name", "x-client-id")
        conn.setdefault("oauth_scopes", "")
    data = load()
    data.setdefault("connections", {})[name] = conn
    save(data)
    return conn


def delete_connection(name: str) -> bool:
    data = load()
    conns = data.get("connections", {})
    existed = name in conns
    conns.pop(name, None)
    # Clear any assignments pointing at it
    for p, c in list(data.get("assignments", {}).items()):
        if c == name:
            data["assignments"].pop(p, None)
    save(data)
    return existed


def get_assignment(profile: str) -> str | None:
    data = load()
    return data.get("assignments", {}).get(profile)


def assign_connection(profile: str, conn_name: str | None) -> bool:
    data = load()
    assignments = data.setdefault("assignments", {})
    if conn_name is None or conn_name == "":
        assignments.pop(profile, None)
    else:
        if conn_name not in data.get("connections", {}):
            return False
        assignments[profile] = conn_name
    save(data)
    return True


def active_profile_name() -> str:
    from dela.profiles import get_current_profile_name
    return get_current_profile_name()


def get_active_for_profile(profile: str) -> dict[str, Any]:
    """Resolve the full connection for a profile, falling back to env defaults."""
    name = get_assignment(profile)
    if name:
        conn = get_connection(name)
        if conn:
            return _resolve(conn)
    return _seed_default()


def get_active() -> dict[str, Any]:
    """Resolve the full connection for the CURRENT profile (used by provider)."""
    return get_active_for_profile(active_profile_name())


def _resolve(conn: dict[str, Any]) -> dict[str, Any]:
    """Fill in derived fields (bearer token for oauth) ready for the OpenAI client."""
    resolved = {
        "name": conn.get("name", ""),
        "base_url": conn.get("base_url", config.BASE_URL),
        "model": conn.get("model", config.MODEL),
        "extra_headers": dict(conn.get("extra_headers") or {}),
        "auth_type": conn.get("auth_type", "simple"),
    }
    if resolved["auth_type"] == "oauth":
        from dela import oauth
        token = oauth.get_valid_token(conn)
        resolved["api_key"] = token or ""
        header_name = conn.get("oauth_header_name", "x-client-id")
        client_id = resolved["extra_headers"].get(header_name)
        if not client_id:
            resolved["extra_headers"][header_name] = conn.get("oauth_client_id", "")
    else:
        resolved["api_key"] = conn.get("api_key", config.API_KEY)
    return resolved


def describe_active() -> dict[str, Any]:
    """Return a masked summary of the active connection (for /api/settings)."""
    profile = active_profile_name()
    name = get_assignment(profile)
    if name:
        conn = get_connection(name)
        if conn:
            d = _mask(conn)
            d["assigned"] = True
            d["profile"] = profile
            if d.get("auth_type") == "oauth":
                from dela import oauth
                d["oauth_status"] = oauth.token_info(conn)
            return d
    d = _seed_default()
    d["name"] = "(env default)"
    d["assigned"] = False
    d["profile"] = profile
    d["api_key"] = _mask_secret(d["api_key"])
    return d