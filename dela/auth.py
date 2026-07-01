"""Authentication — JWT encode/decode + bcrypt password hashing.

Environment variables:
    DELA_JWT_SECRET          — HS256 signing secret (required, generated on first run if missing)
    DELA_ACCESS_TOKEN_EXPIRY — hours (default 24)
    DELA_REFRESH_TOKEN_EXPIRY — days (default 30)
"""

from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt as pyjwt

from dela import config

_JWT_SECRET: str | None = None

ACCESS_EXPIRY_HOURS = int(os.getenv("DELA_ACCESS_TOKEN_EXPIRY", "24"))
REFRESH_EXPIRY_DAYS = int(os.getenv("DELA_REFRESH_TOKEN_EXPIRY", "30"))
ALGORITHM = "HS256"
BCRYPT_COST = 12


def _get_secret() -> str:
    global _JWT_SECRET
    if _JWT_SECRET is not None:
        return _JWT_SECRET

    env_secret = os.getenv("DELA_JWT_SECRET", "")
    if env_secret and env_secret != "replace-me":
        _JWT_SECRET = env_secret
        return _JWT_SECRET

    # Auto-generate a secret and persist it to .env so it survives restarts
    generated = secrets.token_hex(32)
    _JWT_SECRET = generated

    env_path = config.ROOT / ".env"
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        found = False
        new_lines = []
        for line in lines:
            if line.startswith("DELA_JWT_SECRET="):
                new_lines.append(f"DELA_JWT_SECRET={generated}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append("")
            new_lines.append(f"# Multi-user auth — auto-generated on first run")
            new_lines.append(f"DELA_JWT_SECRET={generated}")
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return _JWT_SECRET


# ── Password hashing ───────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_COST)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def validate_password_policy(password: str) -> str | None:
    """Return error string if password fails policy, else None."""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    return None


# ── JWT tokens ─────────────────────────────────────────────────────────────────


def create_access_token(user_id: str, username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "jti": str(uuid.uuid4()),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(hours=ACCESS_EXPIRY_HOURS),
    }
    return pyjwt.encode(payload, _get_secret(), algorithm=ALGORITHM)


def create_refresh_token(user_id: str, username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=REFRESH_EXPIRY_DAYS),
    }
    return pyjwt.encode(payload, _get_secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises pyjwt.PyJWTError on invalid/expired."""
    return pyjwt.decode(token, _get_secret(), algorithms=[ALGORITHM])


def get_token_expiry(token: str) -> str:
    """Return ISO expiry string from a token (without full validation)."""
    try:
        payload = pyjwt.decode(token, _get_secret(), algorithms=[ALGORITHM], options={"verify_exp": False})
        exp = payload.get("exp", 0)
        return datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def refresh_access_token(refresh_token: str) -> dict:
    """Validate refresh token and return a new access_token dict or error."""
    from dela import users

    try:
        payload = decode_token(refresh_token)
    except pyjwt.PyJWTError as e:
        return {"ok": False, "error": f"Invalid or expired refresh token: {e}"}

    if payload.get("type") != "refresh":
        return {"ok": False, "error": "Token is not a refresh token"}

    if users.is_session_revoked(payload["jti"]):
        return {"ok": False, "error": "Refresh token has been revoked"}

    user_id = payload["sub"]
    username = payload["username"]
    role = payload["role"]

    new_access = create_access_token(user_id, username, role)

    return {
        "ok": True,
        "access_token": new_access,
        "expires_at": get_token_expiry(new_access),
        "user": {"id": user_id, "username": username, "role": role},
    }
