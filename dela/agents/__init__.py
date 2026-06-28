"""Sub-agent registry — specialist agents, each with its own SOUL.

A SOUL is a system prompt builder + a tool whitelist. The lead agent dispatches
a sub-agent by name; the sub-agent runs the same brain loop with its scoped
prompt and tools, reports back a result string, and the lead agent weaves it
into the reply.

Adding a new sub-agent = one file in dela/agents/. No brain changes.
Each SOUL module exports:
  - build_prompt() -> str       : the sub-agent's system prompt
  - TOOL_WHITELIST -> set[str]  : which tool names this agent may use (None = all)
  - DESCRIPTION -> str          : one-line description for the dispatch tool
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from dela.tools import registry as tool_registry


@dataclass
class Soul:
    name: str
    description: str
    build_prompt: Callable[[], str]
    tool_whitelist: set[str] | None  # None = all tools; set = only these


_agents: dict[str, Soul] = {}


def register_agent(
    name: str,
    description: str,
    tool_whitelist: set[str] | None = None,
) -> Callable[[Callable[[], str]], Callable[[], str]]:
    """Decorator: register a sub-agent SOUL. The decorated function builds the prompt."""

    def decorator(fn: Callable[[], str]) -> Callable[[], str]:
        _agents[name] = Soul(
            name=name,
            description=description,
            build_prompt=fn,
            tool_whitelist=tool_whitelist,
        )
        return fn

    return decorator


def get_agent(name: str) -> Soul | None:
    return _agents.get(name)


def list_agents() -> list[Soul]:
    return list(_agents.values())


def agent_descriptions() -> list[dict[str, str]]:
    """Return agent names + descriptions for the dispatch tool's schema."""
    return [{"name": a.name, "description": a.description} for a in _agents.values()]


# Importing these modules registers their agents as a side effect.
from dela.agents import researcher  # noqa: F401,E402

__all__ = ["Soul", "register_agent", "get_agent", "list_agents", "agent_descriptions"]