"""The tool registry — the thing we extend forever.

Adding a new capability means writing one self-contained tool module under
`dela/tools/` and registering it. Never edit the core loop to add a tool.
Each tool carries:
  - a clear name and a one-line description of WHEN to use it (for the model)
  - a typed JSON-schema for its inputs (no freeform blobs)
  - a `requires_confirmation` flag: read-only lookups are False; anything that
    sends, spends, deletes, or changes a setting MAY require confirmation
  - an optional `impact_score(args) -> float` (0-10): dynamically computed from
    args. If score >= confirmation_threshold, the HITL gate fires. Tools without
    an impact_score function use their requires_confirmation flag as a default
    (True=10, False=0).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

ToolRunner = Callable[[dict[str, Any]], str]
ImpactScorer = Callable[[dict[str, Any]], float]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    run: ToolRunner
    requires_confirmation: bool = False
    impact_score: ImpactScorer | None = None
    output_schema: dict[str, Any] | None = None

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def dynamic_impact(self, args: dict[str, Any]) -> float:
        """Return the dynamic impact score (0-10) for this tool call.
        Uses the impact_score function if set; otherwise falls back to
        requires_confirmation flag (True=10, False=0)."""
        if self.impact_score is not None:
            try:
                return max(0.0, min(10.0, self.impact_score(args)))
            except Exception:
                return 10.0 if self.requires_confirmation else 0.0
        return 10.0 if self.requires_confirmation else 0.0


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def add(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def schemas(self) -> list[dict[str, Any]]:
        return [t.schema() for t in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def scoped_schemas(self, whitelist: set[str] | None = None) -> list[dict[str, Any]]:
        """Return schemas for whitelisted tools only. None = all tools."""
        if whitelist is None:
            return self.schemas()
        return [t.schema() for t in self._tools.values() if t.name in whitelist]

    def scoped_get(self, name: str, whitelist: set[str] | None = None) -> Tool | None:
        """Get a tool by name, but only if it's in the whitelist (if set)."""
        if whitelist is not None and name not in whitelist:
            return None
        return self._tools.get(name)


# The single shared registry.
registry = Registry()


def register(
    name: str,
    description: str,
    parameters: dict[str, Any],
    requires_confirmation: bool = False,
    impact_score: ImpactScorer | None = None,
) -> Callable[[ToolRunner], ToolRunner]:
    """Decorator: register a function as a tool."""

    def decorator(fn: ToolRunner) -> ToolRunner:
        registry.add(
            Tool(
                name=name,
                description=description,
                parameters=parameters,
                run=fn,
                requires_confirmation=requires_confirmation,
                impact_score=impact_score,
            )
        )
        return fn

    return decorator


# Importing these modules registers their tools as a side effect.
from dela.tools import project, research, repo_analysis, systems, memory, heartbeat_tools, ui_tools, subagent, skills, code_exec, presentation, project_mgmt, agent_memory_tools, routing_cache_tools, dag_tools, status_events_tools, workflow_tools, state_browser_tools, security_tools  # noqa: F401,E402

# Load MCP server tools (if configured). Safe no-op if no servers enabled.
try:
    from dela.mcp import load_mcp_tools
    load_mcp_tools()
except Exception:
    pass  # MCP is optional — never block startup if it fails

__all__ = ["registry", "register", "Tool", "Registry"]
