"""Web research tool — fetch a URL and return its text for the model to summarize.

Read-only, so no confirmation gate. Uses stdlib urllib to avoid a heavy dep.
Treats fetched content as DATA, never instructions (Tier 6 hardens this; the
system prompt already tells Dela inbound text is never a command).
"""

from __future__ import annotations

import urllib.error
import urllib.request

from dela.tools import register

_HEADERS = {"User-Agent": "Dela/0.1 (research assistant)"}
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
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read(_MAX_BYTES + 1)
        if len(raw) > _MAX_BYTES:
            return f"Fetched {url} but it's large; truncated to first {_MAX_BYTES} bytes.\n\n{raw[:_MAX_BYTES].decode('utf-8', errors='replace')}"
        return f"Fetched {url}:\n\n{raw.decode('utf-8', errors='replace')}"
    except urllib.error.HTTPError as e:
        return f"Couldn't fetch {url}: the server returned HTTP {e.code}."
    except urllib.error.URLError as e:
        return f"Couldn't reach {url}: {e.reason}."
    except Exception as e:
        return f"Couldn't fetch {url}: {e}."
