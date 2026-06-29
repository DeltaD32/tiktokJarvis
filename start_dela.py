"""Dela startup script — preflight checks + dual-server launch.

Run:
    python start_dela.py

Checks:
  1. Python version >= 3.11
  2. .env exists and has required keys (DELA_BASE_URL, DELA_API_KEY, DELA_MODEL)
  3. Virtual environment exists
  4. Key Python dependencies importable (fastapi, uvicorn, openai)
  5. Node.js installed
  6. frontend/node_modules exists (runs npm install if not)
  7. Ports 8000 and 5173 are available

Then launches:
  - Backend:  uvicorn dela.server:app --port 8000
  - Frontend: vite dev server --port 5173 (with proxy to backend)

Ctrl+C shuts down both gracefully.
"""
from __future__ import annotations

import os
import sys
import time
import socket
import shutil
import subprocess
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
NODE = shutil.which("node")
NPM = shutil.which("npm.cmd") or shutil.which("npm")
FRONTEND = ROOT / "frontend"
ENV_FILE = ROOT / ".env"

# ── Colors ────────────────────────────────────────────────────────────────────
class C:
    R = "\033[0m"
    B = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    AMBER = "\033[93m"
    RED = "\033[91m"
    GRAY = "\033[90m"

def banner():
    print(f"""{C.CYAN}{C.B}
  ╔═══════════════════════════════════════════════════╗
  ║          D E L A   —   S T A R T U P             ║
  ║          voice-first AI assistant                 ║
  ╚═══════════════════════════════════════════════════╝{C.R}
""")

def ok(msg):   print(f"  {C.GREEN}✓{C.R} {msg}")
def warn(msg): print(f"  {C.AMBER}⚠{C.R} {msg}")
def fail(msg): print(f"  {C.RED}✗{C.R} {msg}")
def info(msg): print(f"  {C.GRAY}→{C.R} {msg}")

def check_port(host: str, port: int) -> bool:
    """Return True if port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False

def preflight() -> bool:
    """Run all preflight checks. Return True if all pass."""
    print(f"\n{C.B}PREFLIGHT CHECKS{C.R}\n")
    all_ok = True

    # 1. Python version
    pyver = sys.version_info
    if pyver >= (3, 11):
        ok(f"Python {pyver.major}.{pyver.minor}.{pyver.micro}")
    else:
        fail(f"Python {pyver.major}.{pyver.minor} — need >= 3.11")
        all_ok = False

    # 2. Virtual environment
    if VENV_PY.exists():
        ok(f"Virtual environment: {VENV_PY.relative_to(ROOT)}")
    else:
        fail("No .venv found — run: python -m venv .venv && .venv\\Scripts\\pip install -r requirements.txt")
        all_ok = False

    # 3. .env file
    if ENV_FILE.exists():
        ok(".env file found")
        # Check required keys
        missing = []
        for key in ("DELA_BASE_URL", "DELA_API_KEY", "DELA_MODEL"):
            val = ""
            for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                if line.startswith(f"{key}="):
                    val = line.split("=", 1)[1].strip()
                    break
            if not val or val == "replace-me":
                missing.append(key)
        if missing:
            fail(f".env missing required values: {', '.join(missing)}")
            all_ok = False
        else:
            ok(".env has all required keys")

        # Show current security profile
        profile = ""
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("DELA_PROFILE="):
                profile = line.split("=", 1)[1].strip()
                break
        if profile:
            ok(f"Security profile: {profile.upper()}")
        else:
            info("No DELA_PROFILE set — defaulting to PERSONAL")
    else:
        fail("No .env file — copy .env.example to .env and fill in your API keys")
        all_ok = False

    # 4. Key Python deps
    dep_check = subprocess.run(
        [str(VENV_PY), "-c", "import fastapi, uvicorn, openai, dotenv; print('ok')"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if "ok" in dep_check.stdout:
        ok("Python dependencies (fastapi, uvicorn, openai, dotenv)")
    else:
        fail(f"Python dependencies missing — run: .venv\\Scripts\\pip install -r requirements.txt")
        info(dep_check.stderr.strip()[:200])
        all_ok = False

    # 5. Node.js
    node_paths = [NODE, "C:\\Program Files\\nodejs\\node.exe", "C:\\Program Files (x86)\\nodejs\\node.exe"]
    node_exe = next((p for p in node_paths if p and Path(p).exists()), None)
    if node_exe:
        node_ver = subprocess.run([node_exe, "--version"], capture_output=True, text=True)
        ok(f"Node.js {node_ver.stdout.strip()}")
    else:
        fail("Node.js not found — install from https://nodejs.org/")
        all_ok = False

    # 6. Frontend node_modules
    if (FRONTEND / "node_modules").exists():
        ok("Frontend dependencies installed")
    else:
        warn("Frontend node_modules missing — running npm install...")
        if NPM:
            result = subprocess.run(
                [NPM, "install"],
                cwd=str(FRONTEND),
                capture_output=True, text=True,
                shell=True,
            )
            if result.returncode == 0:
                ok("npm install completed")
            else:
                fail(f"npm install failed: {result.stderr[:200]}")
                all_ok = False
        else:
            fail("npm not found — install Node.js first")
            all_ok = False

    # 7. Ports
    for port in (8000, 5173):
        if check_port("127.0.0.1", port):
            ok(f"Port {port} available")
        else:
            fail(f"Port {port} is in use — close the process using it or change the port")
            all_ok = False

    print()
    return all_ok

def start_backend() -> subprocess.Popen:
    """Start the FastAPI backend server."""
    info("Starting backend on port 8000...")
    proc = subprocess.Popen(
        [
            str(VENV_PY), "-m", "uvicorn", "dela.server:app",
            "--port", "8000",
            "--app-dir", str(ROOT),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(ROOT),
        encoding="utf-8",
        errors="replace",
    )

    # Wait for server to be ready
    for _ in range(30):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("127.0.0.1", 8000))
                ok("Backend ready at http://localhost:8000")
                return proc
        except OSError:
            time.sleep(0.5)
    fail("Backend failed to start within 15s")
    return proc

def start_frontend() -> subprocess.Popen:
    """Start the Vite dev server."""
    info("Starting frontend on port 5173...")
    vite = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
    node_exe = NODE or "C:\\Program Files\\nodejs\\node.exe"
    proc = subprocess.Popen(
        [node_exe, str(vite), "--port", "5173", "--strictPort"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(FRONTEND),
        encoding="utf-8",
        errors="replace",
    )

    # Wait for server to be ready
    for _ in range(30):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("127.0.0.1", 5173))
                ok("Frontend ready at http://localhost:5173")
                return proc
        except OSError:
            time.sleep(0.5)
    fail("Frontend failed to start within 15s")
    return proc

def pipe_output(proc: subprocess.Popen, label: str, color: str):
    """Thread: pipe subprocess output to console with a label."""
    prefix = f"{color}[{label}]{C.R} "
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            print(f"  {prefix}{line}")

def main():
    banner()

    if not preflight():
        print(f"\n{C.RED}{C.B}Preflight checks failed. Fix the issues above and try again.{C.R}\n")
        sys.exit(1)

    print(f"{C.GREEN}{C.B}All checks passed. Launching Dela...{C.R}\n")

    # Start both servers
    backend = start_backend()
    frontend = start_frontend()

    # Pipe output in threads
    bt = threading.Thread(target=pipe_output, args=(backend, "backend", C.CYAN), daemon=True)
    ft = threading.Thread(target=pipe_output, args=(frontend, "frontend", C.AMBER), daemon=True)
    bt.start()
    ft.start()

    # Open browser after a short delay
    time.sleep(1.5)
    webbrowser.open("http://localhost:5173")
    ok("Browser opened")

    print(f"\n{C.B}Dela is running.{C.R}")
    print(f"  {C.GRAY}Frontend: http://localhost:5173{C.R}")
    print(f"  {C.GRAY}Backend:  http://localhost:8000{C.R}")
    print(f"  {C.GRAY}Press Ctrl+C to stop both servers.{C.R}\n")

    # Wait for either to exit
    try:
        while True:
            if backend.poll() is not None:
                warn("Backend exited.")
                break
            if frontend.poll() is not None:
                warn("Frontend exited.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{C.AMBER}Shutting down...{C.R}")

    # Graceful shutdown
    for proc, name in [(frontend, "frontend"), (backend, "backend")]:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
                ok(f"{name} stopped")
            except subprocess.TimeoutExpired:
                proc.kill()
                warn(f"{name} killed (did not terminate gracefully)")

    print(f"\n{C.GREEN}Dela stopped. Goodbye.{C.R}\n")

if __name__ == "__main__":
    main()
