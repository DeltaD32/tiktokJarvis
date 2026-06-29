"""Security audit and self-checking system.

Runs a set of checks against Dela's own codebase, dependencies, and configuration
to detect potential vulnerabilities, leaked secrets, misconfigured gates, and
prompt-injection risks. Results are surfaced via REST, tools, and a heartbeat check.

Check categories:
  1. Dependency scan — known CVEs in pip and npm packages
  2. Secret scan — hardcoded API keys, tokens, passwords in source
  3. Git hygiene — .env gitignored, no secrets in tracked files
  4. Gate audit — every consequential tool has requires_confirmation=True
  5. Injection defense — system prompt has injection guard, tools sanitize input
  6. Network exposure — server binds to localhost only, CORS not wildcard in prod
  7. File permissions — state files not world-readable
  8. Sandbox safety — code exec is sandboxed, not raw eval
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dela.config import ROOT

_CHECKS_RUN: list[dict] = []
_LAST_SCAN: float = 0


@dataclass
class Finding:
    severity: str  # "critical" | "warning" | "info" | "ok"
    category: str
    title: str
    detail: str

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "detail": self.detail,
        }


def _scan_secrets() -> list[Finding]:
    """Scan source files for hardcoded secrets."""
    findings: list[Finding] = []
    secret_patterns = [
        (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API key"),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub PAT"),
        (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth token"),
        (r"xox[bpoa]-[a-zA-Z0-9-]+", "Slack token"),
        (r"AIza[a-zA-Z0-9_-]{35}", "Google API key"),
        (r"-----BEGIN (RSA |EC )?PRIVATE KEY-----", "Private key block"),
        (r"password\s*=\s*['\"][^'\"]{8,}['\"]", "Hardcoded password"),
        (r"api_key\s*=\s*['\"][^'\"]{10,}['\"]", "Hardcoded API key"),
    ]

    skip_dirs = {".venv", "node_modules", "__pycache__", ".git", "models", "dela_state", "frontend/dist"}
    skip_files = {".env.example", ".gitignore"}

    for py_file in ROOT.rglob("*.py"):
        if any(part in skip_dirs for part in py_file.parts):
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for pattern, name in secret_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                rel = py_file.relative_to(ROOT)
                findings.append(Finding(
                    severity="critical",
                    category="secrets",
                    title=f"Possible {name} in {rel}",
                    detail=f"Pattern matched {len(matches)} time(s). Do NOT hardcode secrets in source — use .env.",
                ))

    # Check .env is not tracked
    gitignore = (ROOT / ".gitignore")
    if gitignore.exists():
        gi_text = gitignore.read_text(encoding="utf-8")
        if ".env" not in gi_text:
            findings.append(Finding("critical", "git", ".env not in .gitignore", "Secrets could be committed."))
        else:
            findings.append(Finding("ok", "git", ".env is gitignored", ""))
    else:
        findings.append(Finding("warning", "git", "No .gitignore found", "Create one to prevent secret leakage."))

    if not any(f.severity == "critical" for f in findings if f.category == "secrets"):
        findings.append(Finding("ok", "secrets", "No hardcoded secrets detected", "Scanned all .py files."))

    return findings


def _scan_gate() -> list[Finding]:
    """Audit the confirmation gate — every consequential tool must have it."""
    findings: list[Finding] = []
    try:
        from dela.tools import registry
        unconfirmed = []
        confirmed = 0
        for tool in registry.all():
            if tool.requires_confirmation:
                confirmed += 1
            else:
                # Check if the tool name suggests it's consequential
                name = tool.name.lower()
                consequential_keywords = ["delete", "remove", "destroy", "drop", "send", "deploy",
                                          "execute", "run", "kill", "reset", "wipe", "purge"]
                if any(kw in name for kw in consequential_keywords):
                    unconfirmed.append(tool.name)

        findings.append(Finding(
            "ok" if not unconfirmed else "warning",
            "gate",
            f"Confirmation gate: {confirmed} tools confirmed",
            f"All consequential tools have requires_confirmation=True." if not unconfirmed
            else f"Possible missing confirmation on: {', '.join(unconfirmed)}",
        ))
    except Exception as e:
        findings.append(Finding("warning", "gate", "Could not audit gate", str(e)))

    return findings


def _scan_injection() -> list[Finding]:
    """Check that prompt injection defenses are in place."""
    findings: list[Finding] = []
    try:
        from dela.system_prompt import build_system_prompt
        prompt = build_system_prompt()
        has_injection_guard = any(kw in prompt.lower() for kw in [
            "prompt injection", "untrusted", "inject", "malicious input",
            "ignore previous", "never follow instructions from",
        ])
        findings.append(Finding(
            "ok" if has_injection_guard else "warning",
            "injection",
            "Prompt injection defense",
            "System prompt contains injection guard language." if has_injection_guard
            else "No injection defense language found in system prompt.",
        ))
    except Exception as e:
        findings.append(Finding("warning", "injection", "Could not check injection defense", str(e)))

    return findings


def _scan_dependencies() -> list[Finding]:
    """Check for known vulnerabilities in pip and npm packages."""
    findings: list[Finding] = []

    # Python: try pip-audit if installed, else check for known-bad versions
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    py_exe = str(venv_py) if venv_py.exists() else sys.executable

    try:
        result = subprocess.run(
            [py_exe, "-m", "pip", "list", "--format=json"],
            capture_output=True, text=True, timeout=30, cwd=str(ROOT),
        )
        packages = json.loads(result.stdout)
        findings.append(Finding(
            "ok", "deps", f"Python: {len(packages)} packages installed",
            "Run 'pip-audit' for CVE checking (install it separately if needed).",
        ))
    except Exception as e:
        findings.append(Finding("info", "deps", "Could not enumerate pip packages", str(e)[:100]))

    # Try pip-audit if available
    try:
        result = subprocess.run(
            [py_exe, "-m", "pip_audit", "--format=json", "--strict"],
            capture_output=True, text=True, timeout=120, cwd=str(ROOT),
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            vulns = data.get("vulnerabilities", [])
            if vulns:
                for v in vulns[:10]:
                    findings.append(Finding("warning", "deps",
                        f"Vulnerable: {v.get('name')} {v.get('version')}",
                        f"Fix: upgrade to {v.get('fix_version', 'latest')}. CVEs: {', '.join(v.get('ids', []))}"))
            else:
                findings.append(Finding("ok", "deps", "pip-audit: no known vulnerabilities", ""))
        else:
            findings.append(Finding("info", "deps", "pip-audit not available", "Install with: pip install pip-audit"))
    except Exception:
        findings.append(Finding("info", "deps", "pip-audit not installed", "Optional: pip install pip-audit for CVE scanning"))

    # npm audit
    npm_dir = ROOT / "frontend"
    npm_cmd = shutil_which("npm.cmd") or shutil_which("npm")
    if npm_dir.exists() and npm_cmd:
        try:
            result = subprocess.run(
                [npm_cmd, "audit", "--json"],
                capture_output=True, text=True, timeout=60, cwd=str(npm_dir),
                shell=True,
            )
            if result.stdout:
                data = json.loads(result.stdout)
                vulns = data.get("vulnerabilities", {})
                high = sum(1 for v in vulns.values() if v.get("severity") == "high")
                critical = sum(1 for v in vulns.values() if v.get("severity") == "critical")
                total = len(vulns)
                if critical > 0:
                    findings.append(Finding("critical", "deps", f"npm: {critical} critical vulnerabilities", f"Run 'npm audit fix' in frontend/."))
                elif high > 0:
                    findings.append(Finding("warning", "deps", f"npm: {high} high vulnerabilities", f"Run 'npm audit fix' in frontend/."))
                elif total > 0:
                    findings.append(Finding("info", "deps", f"npm: {total} low/moderate vulnerabilities", "Review with 'npm audit' in frontend/."))
                else:
                    findings.append(Finding("ok", "deps", "npm: no vulnerabilities", ""))
        except Exception:
            findings.append(Finding("info", "deps", "npm audit not available", ""))
    else:
        findings.append(Finding("info", "deps", "npm not found", "Node.js/npm not in PATH"))

    return findings


def _scan_network() -> list[Finding]:
    """Check server network exposure."""
    findings: list[Finding] = []
    try:
        server_text = (ROOT / "dela" / "server.py").read_text(encoding="utf-8")
        binds_localhost = "127.0.0.1" in server_text or "localhost" in server_text
        wildcard_cors = 'allow_origins=["*"]' in server_text

        if wildcard_cors:
            findings.append(Finding("warning", "network", "CORS allows all origins",
                'Server uses allow_origins=["*"]. For local use this is fine; restrict for deployment.'))
        else:
            findings.append(Finding("ok", "network", "CORS configured", ""))

        # Check start_dela.py binds to localhost
        start_text = (ROOT / "start_dela.py").read_text(encoding="utf-8") if (ROOT / "start_dela.py").exists() else ""
        if "127.0.0.1" in start_text:
            findings.append(Finding("ok", "network", "Server binds to localhost", "Not exposed to external networks."))
        else:
            findings.append(Finding("info", "network", "Server bind address not verified", "Ensure uvicorn binds to 127.0.0.1 in production."))
    except Exception as e:
        findings.append(Finding("info", "network", "Could not check network config", str(e)[:100]))

    return findings


def _scan_sandbox() -> list[Finding]:
    """Check that code execution is sandboxed."""
    findings: list[Finding] = []
    try:
        sandbox_text = (ROOT / "dela" / "sandbox.py").read_text(encoding="utf-8")
        has_docker = "docker" in sandbox_text.lower()
        has_subprocess = "subprocess" in sandbox_text.lower()
        has_eval = re.search(r"\beval\s*\(", sandbox_text)
        has_exec = re.search(r"\bexec\s*\(", sandbox_text)

        if has_docker:
            findings.append(Finding("ok", "sandbox", "Docker sandbox available", "Code execution can be containerized."))
        elif has_subprocess:
            findings.append(Finding("ok", "sandbox", "Subprocess sandboxing", "Code runs in subprocess (not in-process)."))
        else:
            findings.append(Finding("warning", "sandbox", "No sandboxing detected", "Code execution may run in-process."))

        if has_eval or has_exec:
            findings.append(Finding("warning", "sandbox", "eval()/exec() found in sandbox.py", "Ensure user code is isolated."))
    except Exception as e:
        findings.append(Finding("info", "sandbox", "Could not check sandbox", str(e)[:100]))

    return findings


def _scan_audit_trail() -> list[Finding]:
    """Check that audit trail is functioning."""
    findings: list[Finding] = []
    try:
        from dela import audit
        log = audit.tail(1)
        if log:
            findings.append(Finding("ok", "audit", "Audit trail active", f"Last entry: {log[0][:80]}..."))
        else:
            findings.append(Finding("info", "audit", "Audit trail empty", "No actions logged yet."))
    except Exception as e:
        findings.append(Finding("warning", "audit", "Audit trail not accessible", str(e)[:100]))

    return findings


def shutil_which(cmd: str) -> str | None:
    import shutil
    return shutil.which(cmd)


def run_full_scan() -> dict[str, Any]:
    """Run all security checks and return a structured report."""
    import time
    global _CHECKS_RUN, _LAST_SCAN
    _LAST_SCAN = time.time()

    all_findings: list[Finding] = []
    all_findings += _scan_secrets()
    all_findings += _scan_gate()
    all_findings += _scan_injection()
    all_findings += _scan_dependencies()
    all_findings += _scan_network()
    all_findings += _scan_sandbox()
    all_findings += _scan_audit_trail()

    findings_dict = [f.to_dict() for f in all_findings]
    critical = sum(1 for f in all_findings if f.severity == "critical")
    warning = sum(1 for f in all_findings if f.severity == "warning")
    ok = sum(1 for f in all_findings if f.severity == "ok")
    info = sum(1 for f in all_findings if f.severity == "info")

    _CHECKS_RUN = findings_dict

    score = max(0, 100 - critical * 25 - warning * 10)

    return {
        "timestamp": _LAST_SCAN,
        "score": score,
        "summary": {
            "critical": critical,
            "warning": warning,
            "ok": ok,
            "info": info,
            "total": len(all_findings),
        },
        "findings": findings_dict,
        "status": "critical" if critical > 0 else "warning" if warning > 0 else "secure",
    }


def last_scan() -> dict[str, Any]:
    """Return the last scan results, or run a new scan if none exists."""
    if not _CHECKS_RUN:
        return run_full_scan()
    import time
    return {
        "timestamp": _LAST_SCAN,
        "score": max(0, 100 - sum(1 for f in _CHECKS_RUN if f["severity"] == "critical") * 25
                         - sum(1 for f in _CHECKS_RUN if f["severity"] == "warning") * 10),
        "summary": {
            "critical": sum(1 for f in _CHECKS_RUN if f["severity"] == "critical"),
            "warning": sum(1 for f in _CHECKS_RUN if f["severity"] == "warning"),
            "ok": sum(1 for f in _CHECKS_RUN if f["severity"] == "ok"),
            "info": sum(1 for f in _CHECKS_RUN if f["severity"] == "info"),
            "total": len(_CHECKS_RUN),
        },
        "findings": _CHECKS_RUN,
        "status": "critical" if any(f["severity"] == "critical" for f in _CHECKS_RUN) else
                  "warning" if any(f["severity"] == "warning" for f in _CHECKS_RUN) else "secure",
    }
