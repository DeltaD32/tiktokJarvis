"""The thin seam between the harness and the model provider.

Everything else calls into this module and never touches the provider's SDK
directly. Swap providers by changing config (BASE_URL / API_KEY / MODEL) or by
reimplementing this one module. Ollama is supported today because it exposes an
OpenAI-compatible endpoint at http://localhost:11434/v1.

Two entry points:
  - `reply()`          streams text tokens for a plain turn (no tools).
  - `reply_with_tools()` returns a non-streaming turn that may contain text,
                         one or more tool calls, or both. The brain handles the
                         tool-call loop and re-enters here as many times as
                         needed. Non-streaming here is deliberate: tool-call
                         deltas are fiddly to assemble mid-stream and voice
                         (Tier 3) will stream the *final* text turn anyway.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol, TypedDict

from openai import OpenAI, APIError

from dela import config


class ProviderError(RuntimeError):
    """Raised when the provider is slow, unreachable, or returns an error."""


class Message(TypedDict, total=False):
    role: str
    content: str | None
    tool_calls: list[dict[str, Any]]
    tool_call_id: str
    name: str


class _Streamer(Protocol):
    def stream(self) -> Iterator[str]: ...


def _active_connection() -> dict[str, Any]:
    """Resolve the active API connection (base_url, api_key, model, headers).

    Pulls from the connection registry (dela_state/connections.json), falling
    back to the config.py env defaults when no profile assignment exists. For
    OAuth connections the bearer token is fetched/refreshed here so every call
    always has a valid token.
    """
    from dela import connections
    try:
        return connections.get_active()
    except Exception:
        return {
            "base_url": config.BASE_URL,
            "api_key": config.API_KEY,
            "model": config.MODEL,
            "extra_headers": {},
        }


def _client() -> OpenAI:
    conn = _active_connection()
    headers = _tracing_headers() or {}
    extra = conn.get("extra_headers") or {}
    if extra:
        headers.update(extra)
    return OpenAI(
        base_url=conn.get("base_url", config.BASE_URL),
        api_key=conn.get("api_key", config.API_KEY) or "missing",
        default_headers=headers or None,
    )


def _thinking_kwargs() -> dict:
    """Build thinking-level kwargs if configured. Reads from live config."""
    from dela import live_config
    level = live_config.get("thinking_level", "").strip().lower() if live_config.get("thinking_level") else ""
    if not level:
        level = getattr(config, "THINKING_LEVEL", "").strip().lower()
    if not level:
        return {}
    return {"reasoning_effort": level} if level in ("low", "medium", "high") else {}


def _tracing_headers() -> dict[str, str] | None:
    """Build LangSmith/Langfuse trace headers for the OpenAI client.

    LangSmith reads these from the request headers to attribute calls to a
    project. Langfuse uses a proxy or the langfuse SDK, so we only inject
    LangSmith headers here. The key integration is at the audit/tracing seam;
    these headers give us server-side trace attribution when LangSmith is on.
    """
    from dela import tracing, config

    if not config.TRACING_PROVIDER:
        return None

    if config.TRACING_PROVIDER.lower() == "langsmith":
        headers = {}
        if config.TRACING_API_KEY:
            headers["langsmith-api-key"] = config.TRACING_API_KEY
        if config.TRACING_ENDPOINT:
            headers["langsmith-endpoint"] = config.TRACING_ENDPOINT
        headers["langsmith-project"] = config.TRACING_PROJECT
        return headers or None

    return None


def _wrap_error(prefix: str, e: Exception) -> ProviderError:
    if isinstance(e, APIError):
        return ProviderError(f"{prefix}: {e}")
    return ProviderError(f"{prefix}: {e}")


def _effective_model(override: str | None = None) -> str:
    """Resolve the model name to use for a call.

    Priority: explicit override > live_config override > active connection model
    > config.MODEL default.
    """
    if override:
        return override
    try:
        from dela import live_config
        live_model = live_config.get_override("model")
        if live_model and live_model != "default" and str(live_model).strip():
            return live_model
    except Exception:
        pass
    try:
        conn = _active_connection()
        conn_model = conn.get("model")
        if conn_model and str(conn_model).strip():
            return conn_model
    except Exception:
        pass
    return config.MODEL


def reply(system_prompt: str, history: list[Message], model: str | None = None) -> Iterator[str]:
    """Stream text tokens for a plain (tool-less) turn.

    If model is provided, overrides the configured model for this call only.
    """
    messages: list[Message] = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    use_model = _effective_model(model)

    try:
        stream = _client().chat.completions.create(
            model=use_model,
            messages=messages,
            stream=True,
            **_thinking_kwargs(),
        )
    except Exception as e:
        raise _wrap_error("The model provider rejected the request", e) from e

    try:
        for chunk in stream:
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            delta = choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        raise _wrap_error("The stream broke mid-reply", e) from e


def reply_with_tools(
    system_prompt: str,
    history: list[Message],
    tool_schemas: list[dict[str, Any]],
    model: str | None = None,
) -> Any:
    """Send a turn (with tools available) and return the raw completion.

    If model is provided, overrides the configured model for this call only.
    """
    messages: list[Message] = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    use_model = _effective_model(model)

    try:
        return _client().chat.completions.create(
            model=use_model,
            messages=messages,
            tools=tool_schemas,
            tool_choice="auto",
            **_thinking_kwargs(),
        )
    except Exception as e:
        raise _wrap_error("The model provider rejected the tool turn", e) from e
