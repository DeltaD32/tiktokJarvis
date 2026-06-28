"""DAG scheduler — decompose complex tasks into a dependency graph and run in parallel.

The scheduler takes a task decomposition (list of sub-tasks with dependencies)
and runs them concurrently where possible, respecting:
  - Dependencies: a task only runs when all its depends_on tasks are done
  - File leases: two tasks with overlapping file scopes can't run simultaneously
  - Concurrency cap: at most N tasks running at once
  - Governance: the blackboard must be in 'executing' status

This enables true parallel multi-agent work — e.g. "fix the API and write the
docs" can run the code fix and the docs update concurrently if they touch
different files, but serialize if they both modify the same file.

The decomposition is provided by the caller (the model or the secretary).
The scheduler validates the DAG (acyclic check via Kahn's algorithm) and
executes it using ThreadPoolExecutor.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Any, Callable

from dela import audit


@dataclass
class TaskSpec:
    """A single task in the DAG."""
    id: str
    agent: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    file_scope: list[str] = field(default_factory=list)
    status: str = "pending"  # pending → ready → running → done | failed
    result: str = ""
    attempts: int = 0
    max_attempts: int = 3
    lease_owner: str = ""
    lease_expires: float = 0.0


LEASE_TTL = 120  # seconds before a file lease is considered stale


class Scheduler:
    """Run a DAG of tasks with dependency resolution and file-lease safety."""

    def __init__(self, tasks: list[TaskSpec], concurrency: int = 3, blackboard_id: str = ""):
        self.tasks: dict[str, TaskSpec] = {t.id: t for t in tasks}
        self.concurrency = concurrency
        self.blackboard_id = blackboard_id
        self._lock = threading.Lock()
        self._file_leases: dict[str, str] = {}  # file_path → task_id
        self._completed: set[str] = set()
        self._failed: set[str] = set()
        self._events: list[dict[str, Any]] = []
        self._runner: Callable[[TaskSpec], str] | None = None

    def validate(self) -> list[str]:
        """Validate the DAG. Returns list of errors (empty = valid)."""
        errors = []

        # Check all task IDs are unique
        ids = [t.id for t in self.tasks.values()]
        if len(ids) != len(set(ids)):
            errors.append("Duplicate task IDs")

        # Check all depends_on references exist
        for task in self.tasks.values():
            for dep in task.depends_on:
                if dep not in self.tasks:
                    errors.append(f"Task '{task.id}' depends on unknown task '{dep}'")

        # Check acyclic (Kahn's algorithm)
        if not errors:
            in_degree: dict[str, int] = {tid: 0 for tid in self.tasks}
            adj: dict[str, list[str]] = defaultdict(list)
            for task in self.tasks.values():
                for dep in task.depends_on:
                    adj[dep].append(task.id)
                    in_degree[task.id] += 1

            queue = [tid for tid, d in in_degree.items() if d == 0]
            visited = 0
            while queue:
                node = queue.pop(0)
                visited += 1
                for neighbor in adj[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            if visited != len(self.tasks):
                errors.append("Cycle detected in task dependencies (not a DAG)")

        return errors

    def _log_event(self, event: str, task_id: str = "", detail: str = "") -> None:
        self._events.append({
            "event": event,
            "task_id": task_id,
            "detail": detail,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    def _is_ready(self, task: TaskSpec) -> bool:
        """Check if a task's dependencies are all completed."""
        return all(dep in self._completed for dep in task.depends_on)

    def _acquire_leases(self, task: TaskSpec) -> bool:
        """Try to acquire file leases for a task. Returns True if all acquired."""
        now = time.time()
        with self._lock:
            for path in task.file_scope:
                owner = self._file_leases.get(path)
                if owner and owner != task.id:
                    # Check if lease is stale
                    owner_task = self.tasks.get(owner)
                    if owner_task and owner_task.lease_expires > now:
                        return False  # lease held by another active task
                    # Stale lease — reclaim
                    self._file_leases.pop(path, None)

                self._file_leases[path] = task.id
                task.lease_owner = task.id
                task.lease_expires = now + LEASE_TTL
            return True

    def _release_leases(self, task: TaskSpec) -> None:
        """Release file leases held by a task."""
        with self._lock:
            for path in task.file_scope:
                if self._file_leases.get(path) == task.id:
                    del self._file_leases[path]

    def _check_blackboard_gate(self) -> bool:
        """Check if the blackboard is in executing status (governance gate)."""
        if not self.blackboard_id:
            return True  # no blackboard = no gate
        from dela.blackboard import is_gate_open
        return is_gate_open(self.blackboard_id)

    def run(self, runner: Callable[[TaskSpec], str]) -> dict[str, Any]:
        """Run the DAG to completion. Returns a summary dict.

        runner: a function that takes a TaskSpec and returns a result string.
        The runner is responsible for actually executing the task (e.g.
        dispatching a sub-agent, running code, etc.).
        """
        self._runner = runner
        errors = self.validate()
        if errors:
            return {"error": "DAG validation failed", "details": errors}

        self._log_event("scheduler_started", detail=f"{len(self.tasks)} tasks, concurrency={self.concurrency}")

        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures: dict[str, Future] = {}

            while True:
                # Check if all tasks are done or failed
                remaining = [t for t in self.tasks.values() if t.status not in ("done", "failed")]
                if not remaining:
                    break

                # Check governance gate
                if not self._check_blackboard_gate():
                    self._log_event("gate_blocked", detail="Blackboard not in executing status")
                    break

                # Find ready tasks that can acquire leases
                for task in remaining:
                    if task.status == "pending" and self._is_ready(task):
                        if self._acquire_leases(task):
                            task.status = "running"
                            task.attempts += 1
                            self._log_event("task_started", task.id)
                            futures[task.id] = pool.submit(self._run_task, task)

                # Wait for at least one future to complete
                if futures:
                    done_ids = []
                    for tid, fut in list(futures.items()):
                        if fut.done():
                            done_ids.append(tid)

                    if not done_ids:
                        time.sleep(0.1)
                        continue

                    for tid in done_ids:
                        fut = futures.pop(tid)
                        task = self.tasks[tid]
                        try:
                            result = fut.result()
                            task.result = result
                            task.status = "done"
                            self._completed.add(tid)
                            self._log_event("task_done", tid, result[:100])
                        except Exception as e:
                            task.status = "failed"
                            self._failed.add(tid)
                            self._log_event("task_failed", tid, str(e)[:100])
                            audit._write_event(f"DAG task '{tid}' failed: {e}")
                        finally:
                            self._release_leases(task)
                else:
                    # No futures running but tasks remain — check for deadlocks
                    ready = [t for t in remaining if t.status == "pending" and self._is_ready(t)]
                    if not ready:
                        # Could be waiting on leases — wait a bit
                        blocked_by_lease = [t for t in remaining if t.status == "pending" and self._is_ready(t)]
                        if not blocked_by_lease:
                            # Deadlock — no ready tasks and none running
                            self._log_event("deadlock_detected", detail=f"Remaining: {[t.id for t in remaining]}")
                            break
                    time.sleep(0.2)

        self._log_event("scheduler_finished")
        return {
            "completed": len(self._completed),
            "failed": len(self._failed),
            "total": len(self.tasks),
            "events": self._events,
            "results": {tid: t.result for tid, t in self.tasks.items() if t.status == "done"},
        }

    def _run_task(self, task: TaskSpec) -> str:
        """Run a single task using the runner function."""
        if self._runner is None:
            return "No runner configured"
        return self._runner(task)

    def get_events(self) -> list[dict[str, Any]]:
        """Return the event log (for the status events feature)."""
        return self._events

    def get_status(self) -> dict[str, Any]:
        """Return current scheduler status."""
        return {
            "total": len(self.tasks),
            "completed": len(self._completed),
            "failed": len(self._failed),
            "running": sum(1 for t in self.tasks.values() if t.status == "running"),
            "pending": sum(1 for t in self.tasks.values() if t.status == "pending"),
        }


def decompose_from_json(plan: dict[str, Any]) -> list[TaskSpec]:
    """Build TaskSpecs from a JSON decomposition (from the model).

    Expected format:
      {
        "tasks": [
          {"id": "t1", "agent": "researcher", "description": "...", "depends_on": [], "file_scope": []},
          {"id": "t2", "agent": "presenter", "description": "...", "depends_on": ["t1"], "file_scope": ["slides.pptx"]}
        ]
      }
    """
    tasks = []
    for t in plan.get("tasks", []):
        tasks.append(TaskSpec(
            id=t["id"],
            agent=t.get("agent", "worker"),
            description=t["description"],
            depends_on=t.get("depends_on", []),
            file_scope=t.get("file_scope", []),
        ))
    return tasks