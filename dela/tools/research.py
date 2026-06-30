"""Web research tool — fetch a URL and return its text for the model to summarize.

Read-only, so no confirmation gate. All fetches pass through the content sandbox
(dela/content_sandbox.py) which applies SSRF protection, content-type validation,
HTML sanitization, and malicious pattern scanning before content reaches the model.
"""

from __future__ import annotations

from dela.content_sandbox import secure_fetch, SandboxError
from dela.tools import register

_MAX_BYTES = 20_000


@register(
    name="fetch_url",
    description="Fetch the text content of a web URL for me to read and summarize. Use this when I ask you to look something up online or check a specific page. Read-only.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The full http(s) URL to fetch."},
        },
        "required": ["url"],
    },
)
def fetch_url(args: dict) -> str:
    url = args["url"]
    if not url.startswith(("http://", "https://")):
        return f"That doesn't look like a URL: {url}"

    try:
        result = secure_fetch(url, max_bytes=_MAX_BYTES, timeout=15, allow_html=True)
    except SandboxError as e:
        return f"Content sandbox blocked {url}: {e}"
    except ValueError as e:
        return f"Invalid URL {url}: {e}"

    if result["findings"]:
        warnings = "; ".join(f["type"] for f in result["findings"])
        return f"Fetched {url} (sandbox flagged: {warnings}):\n\n{result['text']}"

    return f"Fetched {url}:\n\n{result['text']}"
