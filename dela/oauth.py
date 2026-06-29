"""OAuth client-credentials token manager for api connections.

Some work APIs use a client_id / client_secret pair to mint a bearer token from
an OAuth token endpoint. That token is then sent to the OpenAI-compatible
endpoint as `Authorization: Bearer <token>` along with a clientid header. Tokens
expire after a short lifetime (commonly 7199s). This module:

  - fetches tokens via the client-credentials grant,
  - caches them per connection in dela_state/oauth_tokens.json,
  - lazily refreshes when a token is within REFRESH_MARGIN of expiry,
  - runs a background thread that proactively re-ups auth before expiry.

Two safety nets:
  1. `get_valid_token(conn)` refreshes on demand if the cached token is
     expiring soon — so every provider call always has a usable token.
  2. `start_monitor()` spawns a daemon thread that periodically checks all known
     oauth connections and refreshes any token that is near expiry, even if
     nothing is calling the model.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from typing import Any

# Refresh when fewer than this many seconds remain before expiry.
REFRESH_MARGIN = 600  # 10 minutes
_CHECK_INTERVAL = 60   # background thread poll period (seconds)

_lock = threading.Lock()
_STATE_PATH = _tp = None
_TOKENS: dict[str, dict[str, Any]] = {}

_MONITOR_THREAD: threading.Thread | None = None
_MONITOR_STOP = threading.Event()


def _path():
    global _tp
    if _tp is None:
        from pathlib import Path
        _tp = Path(__file__).resolve().parent.parent / "dela_state" / "oauth_tokens.json"
    return _tp


def _now() -> float:
    return time.time()


def _load() -> None:
    global _TOKENS
    try:
        if _path().exists():
            with _lock:
                _TOKENS = json.loads(_path().read_text(encoding="utf-8"))
    except Exception:
        _TOKENS = {}


def _persist() -> None:
    try:
        _path().parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            _path().write_text(json.dumps(_TOKENS, indent=2), encoding="utf-8")
    except Exception:
        pass


_load()


def _key(conn: dict[str, Any]) -> str:
    return conn.get("name") or conn.get("oauth_token_url") or "default"


def fetch_token(conn: dict[str, Any]) -> dict[str, Any]:
    """Mint a new token from the OAuth token endpoint.

    Returns: {"access_token", "expires_in", "expires_at", "fetched_at", "client_id"?}
    Raises RuntimeError on failure.
    """
    token_url = conn.get("oauth_token_url", "")
    client_id = conn.get("oauth_client_id", "")
    client_secret = conn.get("oauth_client_secret", "")
    scopes = conn.get("oauth_scopes", "")
    if not token_url or not client_id or not client_secret:
        raise RuntimeError("OAuth connection is missing token_url/client_id/client_secret")

    params = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if scopes:
        params["scope"] = scopes
    body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(
        token_url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "Dela/0.1",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
    try:
        data = json.loads(raw)
    except Exception:
        raise RuntimeError(f"OAuth token endpoint returned non-JSON: {raw[:200]!r}")
    if "access_token" not in data:
        raise RuntimeError(f"OAuth token response had no access_token: {data}")

    expires_in = int(data.get("expires_in", 7199) or 7199)
    # Cap to 7199s — many providers advertise longer but revoke earlier.
    expires_in = min(expires_in, 7199)
    fetched = _now()
    token = {
        "access_token": data["access_token"],
        "expires_in": expires_in,
        "expires_at": fetched + expires_in,
        "fetched_at": fetched,
    }
    if data.get("client_id"):
        token["client_id"] = data["client_id"]
    if data.get("token_type"):
        token["token_type"] = data["token_type"]
    with _lock:
        _TOKENS[_key(conn)] = token
    _persist()
    return token


def get_cached(conn: dict[str, Any]) -> dict[str, Any] | None:
    with _lock:
        return _TOKENS.get(_key(conn))


def get_valid_token(conn: dict[str, Any], refresh_margin: int = REFRESH_MARGIN) -> str | None:
    """Return a still-valid bearer token, refreshing if within margin of expiry.

    Returns the token string, or None if refresh failed and there is no token.
    """
    cached = get_cached(conn)
    if cached:
        seconds_left = cached.get("expires_at", 0) - _now()
        if seconds_left > refresh_margin:
            return cached["access_token"]
    try:
        token = fetch_token(conn)
        return token["access_token"]
    except Exception:
        # Last resort: return the stale token if we still have one — better than nothing.
        if cached:
            return cached.get("access_token")
        return None


def force_refresh(conn: dict[str, Any]) -> dict[str, Any]:
    return fetch_token(conn)


def token_info(conn: dict[str, Any]) -> dict[str, Any]:
    """Return a status descriptor for a connection's token."""
    cached = get_cached(conn)
    if not cached:
        return {"status": "none", "has_token": False, "seconds_left": 0, "expires_at": None}
    seconds_left = int(cached.get("expires_at", 0) - _now())
    if seconds_left <= 0:
        status = "expired"
    elif seconds_left <= REFRESH_MARGIN:
        status = "expiring"
    else:
        status = "valid"
    return {
        "status": status,
        "has_token": True,
        "seconds_left": seconds_left,
        "expires_at": cached.get("expires_at"),
        "fetched_at": cached.get("fetched_at"),
    }


def _all_oauth_connections() -> list[dict[str, Any]]:
    """Return all registered oauth connections (assigned or not)."""
    try:
        from dela import connections
        data = connections.load()
        return [c for c in data.get("connections", {}).values() if c.get("auth_type") == "oauth"]
    except Exception:
        return []


def _monitor_loop() -> None:
    while not _MONITOR_STOP.wait(_CHECK_INTERVAL):
        for conn in _all_oauth_connections():
            info = token_info(conn)
            if info["status"] in ("none", "expired", "expiring"):
                try:
                    fetch_token(conn)
                except Exception:
                    pass


def start_monitor() -> None:
    """Start the background refresh thread (idempotent)."""
    global _MONITOR_THREAD
    if _MONITOR_THREAD is not None and _MONITOR_THREAD.is_alive():
        return
    _MONITOR_STOP.clear()
    _MONITOR_THREAD = threading.Thread(target=_monitor_loop, name="oauth-monitor", daemon=True)
    _MONITOR_THREAD.start()


def stop_monitor() -> None:
    _MONITOR_STOP.set()


def is_monitor_running() -> bool:
    return _MONITOR_THREAD is not None and _MONITOR_THREAD.is_alive()


def test_simple_connection(conn: dict[str, Any]) -> dict[str, Any]:
    """Verify a simple (api-key) connection with a lightweight models.list()."""
    from openai import OpenAI
    base_url = conn.get("base_url", "")
    api_key = conn.get("api_key", "")
    extra = dict(conn.get("extra_headers") or {})
    try:
        client = OpenAI(base_url=base_url, api_key=api_key, default_headers=extra or None, timeout=15)
        models = client.models.list()
        ids = sorted([m.id for m in models.data])
        return {"ok": True, "message": f"Connected — {len(ids)} models available", "models": ids}
    except Exception as e:
        return {"ok": False, "message": f"Endpoint call failed: {e}"}


def test_oauth_connection(conn: dict[str, Any]) -> dict[str, Any]:
    """Fetch a fresh token and do a lightweight models.list() to verify the endpoint.

    Returns {"ok": bool, "message": str, "token_status": ..., "models": [...]?}
    """
    from openai import OpenAI
    info_before = token_info(conn)
    try:
        tok = force_refresh(conn)
    except Exception as e:
        return {"ok": False, "message": f"Token fetch failed: {e}", "token_status": info_before}

    base_url = conn.get("base_url", "")
    header_name = conn.get("oauth_header_name", "x-client-id")
    headers = {header_name: conn.get("oauth_client_id", "")}
    try:
        client = OpenAI(base_url=base_url, api_key=tok["access_token"], default_headers=headers, timeout=15)
        models = client.models.list()
        ids = sorted([m.id for m in models.data])
        return {
            "ok": True,
            "message": f"Connected — {len(ids)} models available",
            "token_status": token_info(conn),
            "models": ids,
        }
    except Exception as e:
        return {"ok": False, "message": f"Endpoint call failed: {e}", "token_status": token_info(conn)}


def test_connection(conn: dict[str, Any]) -> dict[str, Any]:
    """Dispatch to the right tester based on auth_type."""
    if conn.get("auth_type") == "oauth":
        return test_oauth_connection(conn)
    return test_simple_connection(conn)