"""The tool registry — the thing we extend forever.

Adding a new capability means writing one self-contained tool module under
`dela/tools/` and registering it. Never edit the core loop to add a tool.
Each tool carries:
  - a clear name and a one-line description of WHEN to use it (for the model)
  - a typed JSON-schema for its inputs (no freeform blobs)
  - a `requires_confirmation` flag: read-only lookups are False; anything that
    sends, spends, deletes, or changes a setting is True. The gate lives in
    Tier 6; we flag now so it has teeth from the beginning.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# A tool's runner takes a dict of arguments and returns a plain-language string
# (success OR error). Returning an error as a result — not raising — lets the
# model reason over failures and recover.
ToolRunner = Callable[[dict[str, Any]], str]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    run: ToolRunner
    requires_confirmation: bool = False

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


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
            )
        )
        return fn

    return decorator


# Importing these modules registers their tools as a side effect.
from dela.tools import project, research, systems, memory, heartbeat_tools, ui_tools, subagent, skills, code_exec, presentation  # noqa: F401,E402

# Load MCP server tools (if configured). Safe no-op if no servers enabled.
try:
    from dela.mcp import load_mcp_tools
    load_mcp_tools()
except Exception:
    pass  # MCP is optional — never block startup if it fails

__all__ = ["registry", "register", "Tool", "Registry"]
