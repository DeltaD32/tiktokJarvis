"""User context — thread-local user ID for per-user state isolation.

State modules (memory, audit, noticeboard, etc.) call `current_user_id()`
to resolve their store path. In single-user mode (DELA_MULTI_USER != "1"),
it always returns None and paths stay at `dela_state/`. In multi-user mode,
the server sets the context before processing each request/turn.

Usage:
    from dela import user_context
    user_context.set_current_user_id("user-uuid-here")
    # ... state operations now scoped to that user ...
    user_context.clear_current_user_id()
"""

from __future__ import annotations

import os
import threading

_user_id: threading.local = threading.local()


def is_multi_user() -> bool:
    return os.getenv("DELA_MULTI_USER", "0") == "1"


def set_current_user_id(user_id: str | None) -> None:
    _user_id.value = user_id


def clear_current_user_id() -> None:
    _user_id.value = None


def current_user_id() -> str | None:
    if not is_multi_user():
        return None
    return getattr(_user_id, "value", None)


def resolve_state_path(filename: str) -> "Path":
    """Resolve a state file path.
    
    In single-user mode: dela_state/{filename}
    In multi-user mode with context: dela_state/users/{user_id}/{filename}
    In multi-user mode without context (system-level): dela_state/system/{filename}
    
    System-level files (heartbeat config, vuln KB, schedule, routing cache) 
    should use get_system_path() instead.
    """
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent / "dela_state"
    uid = current_user_id()
    if uid:
        return root / "users" / uid / filename
    return root / filename


def resolve_state_dir(dirname: str) -> "Path":
    """Resolve a state directory path. Same logic as resolve_state_path."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent / "dela_state"
    uid = current_user_id()
    if uid:
        return root / "users" / uid / dirname
    return root / dirname


def get_system_path(filename: str) -> "Path":
    """Get a system-level (non-user-scoped) state file path."""
    from pathlib import Path
    return Path(__file__).resolve().parent.parent / "dela_state" / "system" / filename


def get_global_path(filename: str = "") -> "Path":
    """Get a legacy/global (non-user-scoped) state file path."""
    from pathlib import Path
    base = Path(__file__).resolve().parent.parent / "dela_state"
    if filename:
        return base / filename
    return base


def migrate_to_multi_user() -> bool:
    """Move existing single-user state files to global/ on first multi-user startup.

    Returns True if migration was performed, False if already migrated or
    multi-user mode is not enabled.
    """
    from pathlib import Path
    import shutil

    if not is_multi_user():
        return False

    root = Path(__file__).resolve().parent.parent / "dela_state"
    global_dir = root / "global"
    marker = global_dir / ".migrated"

    if marker.exists():
        return False

    # Files/dirs that are per-user state (will be migrated to global/)
    PER_USER_FILES = {
        "memory.json", "notices.json", "audit.log", "cost_tally.json",
        "agent_memory.json", "routing_cache.json", "tasks.json",
        "live_settings.json", "status_events.jsonl",
    }
    PER_USER_DIRS = {
        "sessions", "blackboards", "projects", "workflows",
    }

    # Files that stay system-level (don't migrate)
    SYSTEM_FILES = {
        "users.db", "connections.json", "oauth_tokens.json",
        "vuln_kb.json", "schedule.json",
    }

    if not any((root / f).exists() for f in PER_USER_FILES):
        if not any((root / d).exists() for d in PER_USER_DIRS):
            # Nothing to migrate
            global_dir.mkdir(parents=True, exist_ok=True)
            marker.touch()
            return False

    global_dir.mkdir(parents=True, exist_ok=True)

    for fname in PER_USER_FILES:
        src = root / fname
        if src.exists():
            dst = global_dir / fname
            shutil.move(str(src), str(dst))

    for dname in PER_USER_DIRS:
        src = root / dname
        if src.exists() and src.is_dir():
            dst = global_dir / dname
            if dst.exists():
                shutil.rmtree(str(dst))
            shutil.move(str(src), str(dst))

    marker.touch()
    print("  [migrate] Moved existing state to dela_state/global/ — multi-user mode active")
    return True
