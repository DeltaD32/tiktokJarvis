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


def _client() -> OpenAI:
    return OpenAI(base_url=config.BASE_URL, api_key=config.API_KEY)


def _wrap_error(prefix: str, e: Exception) -> ProviderError:
    if isinstance(e, APIError):
        return ProviderError(f"{prefix}: {e}")
    return ProviderError(f"{prefix}: {e}")


def reply(system_prompt: str, history: list[Message]) -> Iterator[str]:
    """Stream text tokens for a plain (tool-less) turn."""
    messages: list[Message] = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    try:
        stream = _client().chat.completions.create(
            model=config.MODEL,
            messages=messages,
            stream=True,
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
) -> Any:
    """Send a turn (with tools available) and return the raw completion.

    Returns the chat completion object so the brain can inspect both
    `.choices[0].message.content` and `.choices[0].message.tool_calls`.
    Raises ProviderError on any provider failure.
    """
    messages: list[Message] = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    try:
        return _client().chat.completions.create(
            model=config.MODEL,
            messages=messages,
            tools=tool_schemas,
            tool_choice="auto",
        )
    except Exception as e:
        raise _wrap_error("The model provider rejected the tool turn", e) from e
