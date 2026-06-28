"""Code execution tool — lets Dela run Python code and get the result.

This is a consequential tool (requires confirmation) — running arbitrary code
is powerful and potentially dangerous. The sandbox seam handles isolation:
Docker by default (isolated container, no network, memory/CPU limited),
subprocess as a fallback (less isolated but works without Docker).

The tool is also available to sub-agents via the tool whitelist, so a
sub-agent could run code to analyze data and report results.
"""

from __future__ import annotations

from dela.sandbox import execute, has_docker
from dela.tools import register


@register(
    name="run_code",
    description=(
        "Execute Python code and return the output (stdout + stderr). "
        "Use this for calculations, data analysis, file processing, or any "
        "task that needs actual computation. The code runs in an isolated "
        "sandbox (Docker if available, subprocess fallback). "
        "Timeout is 30 seconds. Requires confirmation before running."
    ),
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute. Write complete, runnable code.",
            },
            "timeout": {
                "type": "integer",
                "description": "Max execution time in seconds. Default 30. Max 60.",
            },
        },
        "required": ["code"],
    },
    requires_confirmation=True,
)
def run_code(args: dict) -> str:
    code = args["code"]
    timeout = min(int(args.get("timeout", 30)), 60)

    if not code.strip():
        return "No code provided."

    backend = "docker" if has_docker() else "subprocess"
    try:
        output = execute(code, timeout=timeout, backend="auto")
        backend_note = f"[ran in {backend} sandbox]" if backend == "subprocess" else "[ran in Docker sandbox]"
        return f"{backend_note}\n{output}"
    except Exception as e:
        return f"Code execution failed: {e}"
