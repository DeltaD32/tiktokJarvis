"""Tracing seam — optional LangSmith or Langfuse observability.

If DELA_TRACING_PROVIDER is set, this module builds the appropriate callback
handlers and the provider attaches them to model calls. If not set, everything
is a no-op — tracing is purely additive and never breaks the core loop.

Tracing gives you token-level visibility: which prompt was sent, which tools
were called, how many tokens each call used, and how long it took. Our audit
log is for humans; tracing is for dashboards.
"""

from __future__ import annotations

from typing import Any

from dela import config

_callbacks: list[Any] | None = None
_enabled = False


def _init() -> None:
    """Build tracing callbacks based on config. Called once on first use."""
    global _callbacks, _enabled

    provider = config.TRACING_PROVIDER.lower().strip()

    if provider == "langsmith":
        _callbacks = _init_langsmith()
    elif provider == "langfuse":
        _callbacks = _init_langfuse()
    else:
        _callbacks = []

    _enabled = bool(_callbacks)


def _init_langsmith() -> list[Any]:
    """Initialize LangSmith tracing callbacks."""
    import os

    if config.TRACING_API_KEY:
        os.environ["LANGCHAIN_API_KEY"] = config.TRACING_API_KEY
    if config.TRACING_ENDPOINT:
        os.environ["LANGCHAIN_ENDPOINT"] = config.TRACING_ENDPOINT
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = config.TRACING_PROJECT

    try:
        from langchain.callbacks.tracing.langchain import LangChainTracer
        return [LangChainTracer(project_name=config.TRACING_PROJECT)]
    except ImportError:
        # langchain not installed — tracing silently disabled
        return []


def _init_langfuse() -> list[Any]:
    """Initialize Langfuse tracing callbacks."""
    import os

    if config.TRACING_API_KEY:
        os.environ["LANGFUSE_PUBLIC_KEY"] = config.TRACING_API_KEY
    if config.TRACING_ENDPOINT:
        os.environ["LANGFUSE_BASE_URL"] = config.TRACING_ENDPOINT

    try:
        from langfuse.callback import CallbackHandler
        return [CallbackHandler()]
    except ImportError:
        return []


def enabled() -> bool:
    """True if tracing callbacks are active."""
    if not _enabled:
        return False
    return len(_callbacks or []) > 0


def callbacks() -> list[Any]:
    """Return the list of tracing callbacks (empty if disabled or not yet init)."""
    if _callbacks is None:
        _init()
    return _callbacks or []


def trace_model_call(model: str, messages: list[dict], response_summary: str = "") -> None:
    """Record a model call to the tracing backend.

    This is a lightweight hook — the provider calls it after each completion.
    For full token-level tracing, we'd need the langchain integration; this
    gives us session-level visibility via the audit log + optional callbacks.
    """
    from dela import audit
    # Always log to audit (our own trail).
    audit.model_call(model)
    # If tracing callbacks are active, they're attached at the provider level.


def trace_tool_call(tool_name: str, args: dict, result: str) -> None:
    """Record a tool call to the tracing backend."""
    from dela import audit
    audit.tool_call(tool_name, args, result)


def trace_subagent_dispatch(agent_name: str, task: str) -> None:
    """Record that a sub-agent was dispatched (used in Step 2)."""
    from dela import audit
    audit._write_event(f"SUBAGENT dispatch {agent_name}: {task}")


def trace_subagent_return(agent_name: str, result_summary: str) -> None:
    """Record that a sub-agent returned (used in Step 2)."""
    from dela import audit
    audit._write_event(f"SUBAGENT return {agent_name}: {result_summary}")


def describe() -> str:
    """Human-readable status for config display."""
    if not config.TRACING_PROVIDER:
        return "tracing: disabled"
    return f"tracing: {config.TRACING_PROVIDER} (project: {config.TRACING_PROJECT})"