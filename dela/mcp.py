"""MCP server support — bridge external tool ecosystems into Dela's tool registry.

Model Context Protocol (MCP) servers expose tools via a standard protocol. This
module connects to configured servers (stdio or SSE), discovers their tools,
and wraps each as a Dela `Tool` with a generated `run()` function that proxies
to the server. MCP tools respect the same confirmation gate as native tools.

Config: mcp_config.json at the project root.
  {
    "servers": {
      "server-name": {
        "enabled": true,
        "transport": "stdio",      // or "sse"
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
        "env": {}
      }
    }
  }

Adding an MCP server = add an entry to mcp_config.json. No code changes.
MCP tools are loaded on startup and registered alongside native tools.
"""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from typing import Any

from dela.tools import Tool, registry

_CFG_PATH = Path(__file__).resolve().parent.parent / "mcp_config.json"

# Persistent event loop for MCP sessions — the stdio streams are tied to
# the loop they were created on, so we need one shared loop for all MCP calls.
_mcp_loop: asyncio.AbstractEventLoop | None = None
_mcp_thread: threading.Thread | None = None


def _ensure_loop() -> asyncio.AbstractEventLoop:
    """Get (or create) a persistent event loop running in a background thread."""
    global _mcp_loop, _mcp_thread
    if _mcp_loop is not None and not _mcp_loop.is_closed():
        return _mcp_loop

    _mcp_loop = asyncio.new_event_loop()
    _mcp_thread = threading.Thread(
        target=_mcp_loop.run_forever, daemon=True, name="mcp-loop"
    )
    _mcp_thread.start()
    return _mcp_loop


def _run_async(coro: Any) -> Any:
    """Run a coroutine on the persistent MCP loop and return the result."""
    loop = _ensure_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)


# Keep session contexts alive so streams don't close.
_session_ctxs: dict[str, Any] = {}


def _load_config() -> dict[str, Any]:
    if not _CFG_PATH.exists():
        return {"servers": {}}
    try:
        return json.loads(_CFG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"servers": {}}


def _mcp_tool_name(server_name: str, tool_name: str) -> str:
    """Namespaced tool name to avoid collisions: server__tool."""
    return f"{server_name}__{tool_name}"


async def _connect_stdio(server_name: str, params: dict[str, Any]) -> Any:
    """Connect to an MCP server over stdio and return the session."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    command = params.get("command", "")
    args = params.get("args", [])
    env = params.get("env", {})

    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=env if env else None,
    )

    # stdio_client is an async context manager yielding (read, write)
    ctx = stdio_client(server_params)
    read, write = await ctx.__aenter__()
    session = ClientSession(read, write)
    await session.__aenter__()
    await session.initialize()
    # Keep the ctx alive so the streams don't close.
    _session_ctxs[server_name] = ctx
    return session


async def _discover_tools(session: Any, server_name: str) -> list[dict]:
    """List tools from a connected MCP session."""
    result = await session.list_tools()
    return [
        {
            "name": _mcp_tool_name(server_name, t.name),
            "original_name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema or {"type": "object", "properties": {}},
            "server_name": server_name,
        }
        for t in result.tools
    ]


async def _call_tool(session: Any, tool_name: str, args: dict) -> str:
    """Call a tool on an MCP session and return the result as a string."""
    result = await session.call_tool(tool_name, args)
    # MCP results have a list of content items (text, image, etc.)
    parts = []
    for item in result.content:
        if hasattr(item, "text"):
            parts.append(item.text)
        else:
            parts.append(str(item))
    return "\n".join(parts) if parts else "(no output)"


def _make_runner(server_name: str, original_name: str, session: Any) -> Any:
    """Create a sync runner that proxies to the async MCP session.

    Uses the persistent MCP event loop so session streams stay alive.
    """

    def run(args: dict) -> str:
        try:
            return _run_async(_call_tool(session, original_name, args))
        except Exception as e:
            return f"MCP tool '{original_name}' on server '{server_name}' failed: {e}"

    return run


def _guess_confirmation(description: str, original_name: str) -> bool:
    """Heuristic: if the tool name or description suggests a destructive action,
    flag it as requiring confirmation. MCP doesn't have a standard confirmation
    flag, so we guess based on keywords."""
    text = (description + " " + original_name).lower()
    risky = ("delete", "remove", "drop", "write", "create", "update", "move",
             "rename", "send", "post", "put", "execute", "run", "kill", "stop")
    return any(w in text for w in risky)


def load_mcp_tools() -> None:
    """Connect to all enabled MCP servers and register their tools.

    Called on startup. If a server can't connect, it's skipped with a warning —
    Dela still works with its native tools. MCP tools are added alongside them.
    """
    cfg = _load_config()
    servers = cfg.get("servers", {})
    if not servers:
        return

    loop = _ensure_loop()

    for server_name, params in servers.items():
            if not params.get("enabled", False):
                continue

            transport = params.get("transport", "stdio")
            try:
                if transport == "stdio":
                    session = _run_async(_connect_stdio(server_name, params))
                else:
                    print(f"[MCP: skipping '{server_name}' — transport '{transport}' not yet supported]")
                    continue
            except Exception as e:
                print(f"[MCP: couldn't connect to '{server_name}': {e}]")
                continue

            try:
                tools = _run_async(_discover_tools(session, server_name))
            except Exception as e:
                print(f"[MCP: couldn't list tools from '{server_name}': {e}]")
                continue

            for t in tools:
                name = t["name"]
                if registry.get(name) is not None:
                    continue

                runner = _make_runner(server_name, t["original_name"], session)
                registry.add(Tool(
                    name=name,
                    description=f"[MCP:{server_name}] {t['description']}",
                    parameters=t["input_schema"],
                    run=runner,
                    requires_confirmation=_guess_confirmation(t["description"], t["original_name"]),
                ))

            print(f"[MCP: loaded {len(tools)} tool(s) from '{server_name}']")


def mcp_status() -> dict[str, Any]:
    """Return a summary of MCP config for display."""
    cfg = _load_config()
    servers = cfg.get("servers", {})
    return {
        name: {"enabled": p.get("enabled", False), "transport": p.get("transport", "stdio")}
        for name, p in servers.items()
    }