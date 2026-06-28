"""Project management tool — track tasks, list what's due, surface status.

Reads from / writes to a local JSON file so tasks survive restarts. Mutating
operations (add, complete, delete) require confirmation; reads don't.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from dela.tools import register

_STORE = Path(__file__).resolve().parent.parent.parent / "dela_state" / "tasks.json"


def _load() -> list[dict]:
    if not _STORE.exists():
        return []
    return json.loads(_STORE.read_text(encoding="utf-8"))


def _save(tasks: list[dict]) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")


@register(
    name="list_tasks",
    description="List my current tasks. Use this when I ask what's on my list, what's due, or what I should work on. Read-only.",
    parameters={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["open", "done", "all"],
                "description": "Filter by status. Default: open.",
            }
        },
    },
)
def list_tasks(args: dict) -> str:
    tasks = _load()
    status = args.get("status", "open")
    if status != "all":
        tasks = [t for t in tasks if t["status"] == status]
    if not tasks:
        return "Your task list is empty."
    lines = [f"- [{t['status']}] {t['title']} (due {t.get('due', 'n/a')}, id {t['id']})" for t in tasks]
    return f"You have {len(tasks)} task(s):\n" + "\n".join(lines)


@register(
    name="add_task",
    description="Add a new task to my list. Use this when I ask you to remember something to do, or to add a task. Always confirm the title and due date with me.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short description of the task."},
            "due": {"type": "string", "description": "Due date in YYYY-MM-DD format, or 'n/a'."},
        },
        "required": ["title"],
    },
    requires_confirmation=True,
)
def add_task(args: dict) -> str:
    tasks = _load()
    next_id = (max((t["id"] for t in tasks), default=0)) + 1
    task = {
        "id": next_id,
        "title": args["title"],
        "due": args.get("due", "n/a"),
        "status": "open",
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    tasks.append(task)
    _save(tasks)
    return f"Added task {next_id}: '{task['title']}' (due {task['due']})."


@register(
    name="complete_task",
    description="Mark a task as done by its id. Use this when I tell you I finished something. Confirm which task before completing.",
    parameters={
        "type": "object",
        "properties": {
            "id": {"type": "integer", "description": "The numeric id of the task to complete."},
        },
        "required": ["id"],
    },
    requires_confirmation=True,
)
def complete_task(args: dict) -> str:
    tasks = _load()
    for t in tasks:
        if t["id"] == args["id"]:
            t["status"] = "done"
            _save(tasks)
            return f"Marked task {t['id']} ('{t['title']}') as done."
    return f"No task with id {args['id']}."
