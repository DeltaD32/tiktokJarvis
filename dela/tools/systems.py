"""Systems checks tool — check whether a host or URL is reachable and report status.

Read-only health checks. Mutating operations (restart a service, change a
config) would go here later and would be flagged requires_confirmation=True.
"""

from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request

from dela.tools import register


@register(
    name="check_host",
    description="Check whether a host or URL is reachable and measure response time. Use this when I ask if a service is up, to check system health, or to ping a host. Read-only.",
    parameters={
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "A URL (http/https) or a bare host:port like example.com:443.",
            },
            "timeout": {
                "type": "number",
                "description": "Seconds to wait before giving up. Default 5.",
            },
        },
        "required": ["target"],
    },
)
def check_host(args: dict) -> str:
    target = args["target"]
    timeout = float(args.get("timeout", 5))

    if target.startswith(("http://", "https://")):
        try:
            req = urllib.request.Request(target, method="HEAD", headers={"User-Agent": "Dela/0.1"})
            start = time.monotonic()
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ms = (time.monotonic() - start) * 1000
            return f"{target} is UP — HTTP {resp.status}, responded in {ms:.0f}ms."
        except urllib.error.HTTPError as e:
            return f"{target} responded but with HTTP {e.code} — reachable but not healthy."
        except Exception as e:
            return f"{target} is DOWN: {e}."

    # bare host:port -> TCP connect check
    if ":" not in target:
        target = f"{target}:80"
    host, _, port = target.partition(":")
    try:
        port_i = int(port)
    except ValueError:
        return f"Bad target '{target}'. Use host:port or a full URL."

    start = time.monotonic()
    try:
        with socket.create_connection((host, port_i), timeout=timeout):
            ms = (time.monotonic() - start) * 1000
        return f"{host}:{port_i} is UP — TCP connect succeeded in {ms:.0f}ms."
    except Exception as e:
        return f"{host}:{port_i} is DOWN: {e}."
