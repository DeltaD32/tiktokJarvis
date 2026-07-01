"""State browser — unified read/search API across all Dela state.

Lets the model and the UI inspect, search, and edit every piece of state
Dela manages. No more black box — everything is visible and controllable.

State types:
  memory       — durable user facts (memory.json)
  agent_memory — per-agent learnings (agent_memory.json)
  notices      — proactive notices (notices.json)
  tasks        — project management tasks (tasks.json)
  projects     — multi-agent projects (projects/*.json)
  blackboards  — shared workspaces (blackboards/*.json)
  sessions     — conversation histories (sessions/*.json)
  workflows    — workflow definitions (workflows/*.json)
  routing      — routing cache (routing_cache.json)
  audit        — audit log (audit.log)
  events       — status events (status_events.jsonl)
  cost         — cost tally (cost_tally.json)
  styles       — PPT style registry (styles/)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dela import user_context


def _state_root() -> Path:
    uid = user_context.current_user_id()
    if uid:
        return user_context.resolve_state_path(".")
    return Path(__file__).resolve().parent.parent / "dela_state"

# Map state type → (file or dir, format, description)
_STATE_MAP = {
    "memory": ("memory.json", "json", "Durable user facts"),
    "agent_memory": ("agent_memory.json", "json", "Per-agent self-learning memory"),
    "notices": ("notices.json", "json", "Proactive notices"),
    "tasks": ("tasks.json", "json", "Project management tasks"),
    "routing": ("routing_cache.json", "json", "Semantic routing cache"),
    "cost": ("cost_tally.json", "json", "Model cost tally"),
    "audit": ("audit.log", "text", "Audit trail (append-only)"),
    "events": ("status_events.jsonl", "jsonl", "Lifecycle event log"),
    "projects": ("projects", "dir_json", "Multi-agent projects"),
    "blackboards": ("blackboards", "dir_json", "Shared workspaces"),
    "sessions": ("sessions", "dir_json", "Conversation histories"),
    "workflows": ("workflows", "dir_json", "Workflow definitions"),
    "styles": ("styles", "dir_registry", "PPT style registry"),
}


def list_state_types() -> list[dict[str, str]]:
    """Return all state types with descriptions and item counts."""
    results = []
    for stype, (path, fmt, desc) in _STATE_MAP.items():
        count = _count_items(stype)
        results.append({
            "type": stype,
            "description": desc,
            "items": count,
            "format": fmt,
        })
    return results


def _count_items(stype: str) -> int:
    """Count items in a state type."""
    path_str, fmt, _ = _STATE_MAP.get(stype, ("", "", ""))
    full = _state_root() / path_str
    if not full.exists():
        return 0
    if fmt == "dir_json":
        return len(list(full.glob("*.json")))
    elif fmt == "dir_registry":
        # styles has subdirectories
        registry = full / "registry.json"
        if registry.exists():
            try:
                data = json.loads(registry.read_text(encoding="utf-8"))
                return len(data.get("styles", {}))
            except Exception:
                pass
        return len([d for d in full.iterdir() if d.is_dir()])
    elif fmt == "json":
        try:
            data = json.loads(full.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return len(data)
            elif isinstance(data, dict):
                return len(data)
            return 1
        except Exception:
            return 0
    elif fmt == "jsonl":
        return sum(1 for _ in full.open(encoding="utf-8"))
    elif fmt == "text":
        return sum(1 for _ in full.open(encoding="utf-8"))
    return 0


def read_state(stype: str, item_id: str | None = None, limit: int = 50) -> dict[str, Any]:
    """Read a state type, or a specific item within it.

    For dir-based types, item_id selects a specific file (by ID/slug).
    For json types, item_id selects a specific entry by index or key.
    For text/jsonl, returns the last N lines.
    """
    if stype not in _STATE_MAP:
        return {"error": f"Unknown state type: {stype}. Available: {list(_STATE_MAP.keys())}"}

    path_str, fmt, _ = _STATE_MAP[stype]
    full = _state_root() / path_str

    if not full.exists():
        return {"type": stype, "items": [], "note": "No state file found yet."}

    if fmt == "json":
        try:
            data = json.loads(full.read_text(encoding="utf-8"))
            if item_id is not None:
                # Try to find by id field or index
                if isinstance(data, list):
                    for item in data:
                        if str(item.get("id", "")) == item_id:
                            return {"type": stype, "item": item}
                    return {"error": f"Item '{item_id}' not found in {stype}"}
                elif isinstance(data, dict):
                    if item_id in data:
                        return {"type": stype, "item": data[item_id]}
                    return {"error": f"Key '{item_id}' not found in {stype}"}
            return {"type": stype, "data": data}
        except Exception as e:
            return {"error": f"Failed to read {stype}: {e}"}

    elif fmt == "dir_json":
        if item_id:
            # Find the file — try exact match, then glob
            for f in full.glob("*.json"):
                if item_id in f.name:
                    try:
                        return {"type": stype, "item": json.loads(f.read_text(encoding="utf-8"))}
                    except Exception as e:
                        return {"error": f"Failed to read {f.name}: {e}"}
            return {"error": f"Item '{item_id}' not found in {stype}"}
        else:
            items = []
            for f in sorted(full.glob("*.json")):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    # Summary only (don't return full content for list view)
                    summary = {
                        "id": data.get("id", f.stem),
                        "name": data.get("name", data.get("task_description", f.stem))[:80],
                        "status": data.get("status", ""),
                    }
                    items.append(summary)
                except Exception:
                    pass
            return {"type": stype, "items": items[:limit]}

    elif fmt == "jsonl":
        lines = full.read_text(encoding="utf-8").splitlines()
        if item_id:
            for line in lines:
                try:
                    event = json.loads(line)
                    if str(event.get("entity_id", "")) == item_id:
                        return {"type": stype, "item": event}
                except Exception:
                    pass
        return {"type": stype, "lines": lines[-limit:]}

    elif fmt == "text":
        lines = full.read_text(encoding="utf-8").splitlines()
        return {"type": stype, "lines": lines[-limit:]}

    elif fmt == "dir_registry":
        registry = full / "registry.json"
        if registry.exists():
            try:
                data = json.loads(registry.read_text(encoding="utf-8"))
                if item_id:
                    styles = data.get("styles", {})
                    if item_id in styles:
                        return {"type": stype, "item": styles[item_id]}
                return {"type": stype, "data": data.get("styles", {})}
            except Exception as e:
                return {"error": f"Failed to read styles: {e}"}
        return {"type": stype, "items": []}

    return {"error": f"Unsupported format: {fmt}"}


def search_state(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Search across ALL state types for a query string.

    Searches text content in all state files. Returns matching items with
    their type, id, and a snippet of the matching content.
    """
    query_lower = query.lower()
    results = []

    for stype, (path_str, fmt, _) in _STATE_MAP.items():
        full = _state_root() / path_str
        if not full.exists():
            continue

        if fmt in ("json", "jsonl"):
            _search_file(full, stype, query_lower, results)
        elif fmt == "dir_json":
            for f in full.glob("*.json"):
                _search_file(f, stype, query_lower, results, file_id=f.stem)
        elif fmt == "text":
            try:
                for i, line in enumerate(full.read_text(encoding="utf-8").splitlines()):
                    if query_lower in line.lower():
                        results.append({
                            "type": stype,
                            "line": i,
                            "snippet": line[:200],
                        })
                        if len(results) >= limit:
                            return results
            except Exception:
                pass

    return results[:limit]


def _search_file(path: Path, stype: str, query: str, results: list, file_id: str = "") -> None:
    """Search a single JSON/JSONL file for the query."""
    try:
        content = path.read_text(encoding="utf-8")
        if query not in content.lower():
            return

        data = json.loads(content)
        if isinstance(data, list):
            for item in data:
                item_str = json.dumps(item, ensure_ascii=False).lower()
                if query in item_str:
                    snippet = _extract_snippet(item, query)
                    results.append({
                        "type": stype,
                        "id": str(item.get("id", file_id or "?")),
                        "snippet": snippet[:200],
                    })
        elif isinstance(data, dict):
            for key, val in data.items():
                val_str = json.dumps(val, ensure_ascii=False).lower()
                if query in val_str:
                    snippet = _extract_snippet(val, query)
                    results.append({
                        "type": stype,
                        "id": str(key),
                        "snippet": snippet[:200],
                    })
    except Exception:
        pass


def _extract_snippet(data: Any, query: str) -> str:
    """Extract a snippet around the matching query from data."""
    text = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    idx = text.lower().find(query)
    if idx < 0:
        return text[:200]
    start = max(0, idx - 50)
    end = min(len(text), idx + len(query) + 50)
    return ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")


def edit_state(stype: str, item_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    """Edit a specific item in state. Only supports types with item-level editing.

    Currently supports: memory (update/delete facts), notices (dismiss),
    tasks (update status), agent_memory (not directly—use the tools).
    """
    if stype == "memory":
        from dela import memory
        if "text" in changes:
            result = memory.update(int(item_id), changes["text"])
            if result:
                return {"ok": True, "item": result}
            return {"error": f"Fact {item_id} not found."}
        if changes.get("delete"):
            return {"ok": memory.remove(int(item_id))}
        return {"error": "Provide 'text' to update or 'delete': true to remove."}

    elif stype == "notices":
        from dela import noticeboard
        if changes.get("dismiss"):
            return {"ok": noticeboard.dismiss(int(item_id))}
        return {"error": "Provide 'dismiss': true to dismiss a notice."}

    elif stype == "tasks":
        from dela.tools.project import _load, _save
        tasks = _load()
        for t in tasks:
            if str(t["id"]) == item_id:
                if "status" in changes:
                    t["status"] = changes["status"]
                if "title" in changes:
                    t["title"] = changes["title"]
                _save(tasks)
                return {"ok": True, "item": t}
        return {"error": f"Task {item_id} not found."}

    return {"error": f"Editing {stype} is not supported via state browser. Use the appropriate tool."}