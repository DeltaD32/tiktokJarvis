"""User model — SQLite-backed user store with CRUD operations.

Stored in dela_state/users.db alongside other state files.
Thread-safe via module-level lock.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "dela_state" / "users.db"
_lock = threading.Lock()

ROLES = ("admin", "user", "viewer")
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    email       TEXT UNIQUE,
    password    TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'user',
    display_name TEXT,
    created_at  TEXT NOT NULL,
    last_login  TEXT,
    active      INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id),
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    revoked     INTEGER DEFAULT 0
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    d.pop("password", None)
    return d


# ── User CRUD ──────────────────────────────────────────────────────────────────


def create_user(
    username: str,
    password_hash: str,
    *,
    role: str = "user",
    email: str | None = None,
    display_name: str | None = None,
) -> dict:
    if role not in ROLES:
        return {"ok": False, "error": f"Invalid role '{role}'. Must be one of: {', '.join(ROLES)}"}
    user_id = str(uuid.uuid4())
    now = _now()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO users (id, username, email, password, role, display_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, username, email, password_hash, role, display_name, now),
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            msg = str(e).lower()
            if "username" in msg:
                return {"ok": False, "error": f"Username '{username}' already exists"}
            if "email" in msg:
                return {"ok": False, "error": f"Email '{email}' already exists"}
            return {"ok": False, "error": str(e)}
        finally:
            conn.close()
    return {
        "ok": True,
        "user": {"id": user_id, "username": username, "email": email, "role": role, "display_name": display_name, "created_at": now, "active": 1},
    }


def get_user(user_id: str) -> dict | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT * FROM users WHERE id = ? AND active = 1", (user_id,)).fetchone()
        finally:
            conn.close()
    return _row_to_dict(row)


def get_user_by_username(username: str) -> dict | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT * FROM users WHERE username = ? AND active = 1", (username,)).fetchone()
        finally:
            conn.close()
    return _row_to_dict(row)


def get_user_with_password(username: str) -> dict | None:
    """Return user dict INCLUDING password hash — for login validation only."""
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT * FROM users WHERE username = ? AND active = 1", (username,)).fetchone()
        finally:
            conn.close()
    if row is None:
        return None
    return dict(row)


def list_users() -> list[dict]:
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute("SELECT * FROM users WHERE active = 1 ORDER BY created_at").fetchall()
        finally:
            conn.close()
    return [d for row in rows if (d := _row_to_dict(row)) is not None]


def update_user(user_id: str, **fields) -> dict | None:
    allowed = {"username", "email", "role", "display_name", "password", "active"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_user(user_id)
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    with _lock:
        conn = _connect()
        try:
            conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        except sqlite3.IntegrityError as e:
            return {"ok": False, "error": str(e)}
        finally:
            conn.close()
    return _row_to_dict(row)


def delete_user(user_id: str) -> bool:
    """Soft-delete: set active=0."""
    with _lock:
        conn = _connect()
        try:
            conn.execute("UPDATE users SET active = 0 WHERE id = ?", (user_id,))
            conn.commit()
            affected = conn.total_changes > 0
        finally:
            conn.close()
    return affected


def record_login(user_id: str) -> None:
    with _lock:
        conn = _connect()
        try:
            conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (_now(), user_id))
            conn.commit()
        finally:
            conn.close()


def count_users() -> int:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT COUNT(*) FROM users WHERE active = 1").fetchone()
        finally:
            conn.close()
    return row[0] if row else 0


# ── Session tracking ───────────────────────────────────────────────────────────


def create_session(user_id: str, token: str, expires_at: str) -> None:
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, user_id, _now(), expires_at),
            )
            conn.commit()
        finally:
            conn.close()


def revoke_session(token: str) -> None:
    with _lock:
        conn = _connect()
        try:
            conn.execute("UPDATE sessions SET revoked = 1 WHERE token = ?", (token,))
            conn.commit()
        finally:
            conn.close()


def is_session_revoked(token: str) -> bool:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT revoked FROM sessions WHERE token = ?", (token,)).fetchone()
        finally:
            conn.close()
    if row is None:
        return False
    return bool(row["revoked"])


def prune_expired_sessions() -> int:
    with _lock:
        conn = _connect()
        try:
            conn.execute("DELETE FROM sessions WHERE expires_at < ? OR revoked = 1", (_now(),))
            conn.commit()
            count = conn.total_changes
        finally:
            conn.close()
    return count
