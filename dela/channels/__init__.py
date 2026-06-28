"""IM channel framework — bridge messaging platforms to the same brain.

Each channel is a module that connects to a platform's API, receives messages,
and calls brain.assemble_reply(). Replies go back through the platform. Each
channel sets its own Confirmer (platform-appropriate). Adding a channel = one
file + a config entry.

Channels use the same brain, memory, tools, heartbeat, and safety gate as text
and voice. They're just another way in and out.
"""

from __future__ import annotations

from collections.abc import Callable

# Registry of channel name -> start function
_channels: dict[str, Callable[[], None]] = {}


def register_channel(name: str) -> Callable[[Callable[[], None]], Callable[[], None]]:
    """Decorator: register a channel's start function."""

    def decorator(fn: Callable[[], None]) -> Callable[[], None]:
        _channels[name] = fn
        return fn

    return decorator


def get_channel(name: str) -> Callable[[], None] | None:
    return _channels.get(name)


def list_channels() -> list[str]:
    return list(_channels.keys())


# Importing these modules registers their channels as a side effect.
from dela.channels import telegram, teams_webhook, graph_api  # noqa: F401,E402

__all__ = ["register_channel", "get_channel", "list_channels"]