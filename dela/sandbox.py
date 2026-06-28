"""Sandbox execution seam — run code in an isolated environment.

Two backends:
  - Docker: runs code in an isolated container (safe, recommended)
  - Subprocess: runs code in a local subprocess (less safe, fallback)

The seam means the execution backend can swap without changing the tool.
Both backends are timeout-bounded and capture stdout/stderr.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

_DEFAULT_TIMEOUT = 30
_DOCKER_IMAGE = "python:3.12-slim"


class SandboxError(RuntimeError):
    pass


def _run_docker(code: str, timeout: int = _DEFAULT_TIMEOUT) -> str:
    """Run Python code in a Docker container. Returns stdout+stderr."""
    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", "512m",
                "--cpus", "1.0",
                _DOCKER_IMAGE,
                "python", "-c", code,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += ("\n--- stderr ---\n" + result.stderr) if output else result.stderr
        if result.returncode != 0 and not output:
            output = f"[exit code {result.returncode}]"
        return output.strip() or "(no output)"
    except FileNotFoundError:
        raise SandboxError("Docker is not installed. Use subprocess backend or install Docker.")
    except subprocess.TimeoutExpired:
        return f"[execution timed out after {timeout}s]"
    except Exception as e:
        raise SandboxError(f"Docker execution failed: {e}")


def _run_subprocess(code: str, timeout: int = _DEFAULT_TIMEOUT) -> str:
    """Run Python code in a local subprocess. Less isolated — fallback only."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        script_path = f.name

    try:
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += ("\n--- stderr ---\n" + result.stderr) if output else result.stderr
        if result.returncode != 0 and not output:
            output = f"[exit code {result.returncode}]"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"[execution timed out after {timeout}s]"
    except Exception as e:
        raise SandboxError(f"Subprocess execution failed: {e}")
    finally:
        Path(script_path).unlink(missing_ok=True)


def has_docker() -> bool:
    """Check if Docker is available."""
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def execute(code: str, timeout: int = _DEFAULT_TIMEOUT, backend: str = "auto") -> str:
    """Execute Python code and return the output.

    backend: "docker" (isolated), "subprocess" (local), or "auto" (docker if available).
    """
    if backend == "docker" or (backend == "auto" and has_docker()):
        try:
            return _run_docker(code, timeout)
        except SandboxError:
            if backend == "auto":
                return _run_subprocess(code, timeout)
            raise
    elif backend == "subprocess" or backend == "auto":
        return _run_subprocess(code, timeout)
    else:
        raise SandboxError(f"Unknown backend: {backend}")
