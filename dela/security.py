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
    priority: str = ""  # "P0" | "P1" | "P2" | "P3" | "P4" — set by _prioritize_findings

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "detail": self.detail,
            "priority": self.priority or "P4",
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
        from dela.profiles import get_current_profile
        profile = get_current_profile()

        unconfirmed = []
        confirmed = 0
        blocked = 0
        # Use word-boundary matching to avoid false positives like "kill" in "skills"
        consequential_keywords = [
            "delete", "remove", "destroy", "drop", "send", "deploy",
            "execute", "kill", "reset", "wipe", "purge",
        ]
        for tool in registry.all():
            if not profile.is_tool_allowed(tool.name):
                blocked += 1
                continue
            effective_confirm = profile.requires_confirmation(tool.name, tool.requires_confirmation)
            if effective_confirm:
                confirmed += 1
            else:
                name_lower = tool.name.lower()
                # Check word boundaries: split on _ and -
                words = re.split(r'[-_]', name_lower)
                if any(kw in words for kw in consequential_keywords):
                    unconfirmed.append(tool.name)

        findings.append(Finding(
            "ok" if not unconfirmed else "warning",
            "gate",
            f"Confirmation gate: {confirmed} confirmed, {blocked} blocked by profile",
            f"All consequential tools have confirmation gate." if not unconfirmed
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
    """Check server network exposure based on current profile."""
    findings: list[Finding] = []
    try:
        from dela.profiles import get_current_profile
        profile = get_current_profile()

        # Check CORS config
        if profile.cors_origins == ["*"]:
            findings.append(Finding("warning", "network", "CORS allows all origins",
                'Profile uses allow_origins=["*"]. Acceptable for local dev; switch to work profile for restricted origins.'))
        else:
            findings.append(Finding("ok", "network", f"CORS restricted to {len(profile.cors_origins)} origin(s)",
                f"Allowed: {', '.join(profile.cors_origins)}"))

        # Check bind host
        if profile.bind_host == "127.0.0.1":
            findings.append(Finding("ok", "network", "Server binds to localhost", "Not exposed to external networks."))
        else:
            findings.append(Finding("warning", "network", f"Server binds to {profile.bind_host}", "External networks can reach the server."))
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


def _scan_profile() -> list[Finding]:
    """Check that the security profile is properly configured."""
    findings: list[Finding] = []
    try:
        from dela.profiles import get_current_profile, get_current_profile_name
        profile = get_current_profile()
        name = get_current_profile_name()

        findings.append(Finding(
            "ok", "profile", f"Active profile: {name.upper()}",
            profile.description,
        ))

        if profile.tools_blocked:
            findings.append(Finding(
                "ok", "profile", f"{len(profile.tools_blocked)} tool(s) blocked by profile",
                f"Blocked: {', '.join(sorted(profile.tools_blocked))}",
            ))

        if profile.injection_level == "maximum":
            findings.append(Finding("ok", "profile", "Maximum injection defense active", "8 absolute rules enforced."))
        else:
            findings.append(Finding("ok", "profile", "Standard injection defense active", ""))

        if profile.wiz_enabled:
            findings.append(Finding("ok", "profile", "WIZ enterprise integration enabled", "Cloud resources monitored by WIZ."))
        else:
            findings.append(Finding("info", "profile", "WIZ integration disabled", "Enable work profile for WIZ support."))

    except Exception as e:
        findings.append(Finding("warning", "profile", "Could not check profile", str(e)[:100]))

    return findings


# ─── Vulnerability KB checks (OWASP LLM Top 10 + CWE Top 25) ──────────────────

def _check_shell_injection() -> Finding:
    """CWE-78: Check for subprocess usage with shell=True on user input."""
    skip_dirs = {".venv", "node_modules", "__pycache__", ".git", "models", "dela_state", "frontend/dist"}
    skip_files = {"dela\\security.py", "dela\\vuln_kb.py", "start_dela.py"}
    issues = []
    for py_file in ROOT.rglob("*.py"):
        if any(part in skip_dirs for part in py_file.parts):
            continue
        rel_str = str(py_file.relative_to(ROOT)).replace("/", "\\")
        if rel_str in skip_files:
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in re.finditer(r'shell\s*=\s*True', text):
            line_num = text[:m.start()].count('\n') + 1
            rel = py_file.relative_to(ROOT)
            issues.append(f"{rel}:{line_num}")
    if issues:
        return Finding("warning", "vuln_kb", "CWE-78: shell=True found",
                       f"Locations: {', '.join(issues[:5])}. Avoid shell=True with user input.")
    return Finding("ok", "vuln_kb", "CWE-78: No shell=True usage", "")


def _check_path_traversal() -> Finding:
    """CWE-22: Check file operations for path validation."""
    skip_dirs = {".venv", "node_modules", "__pycache__", ".git", "models", "dela_state", "frontend/dist"}
    risky = []
    for py_file in ROOT.glob("dela/**/*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if re.search(r'open\s*\(\s*[^)]*f["\']', text) and not re.search(r'resolve|normalize|is_relative_to|check_path', text, re.I):
            risky.append(str(py_file.relative_to(ROOT)))
    if risky:
        return Finding("info", "vuln_kb", "CWE-22: File opens with f-strings",
                       f"Review path validation in: {', '.join(risky[:5])}")
    return Finding("ok", "vuln_kb", "CWE-22: Path operations look safe", "")


def _check_code_injection() -> Finding:
    """CWE-94: Check for eval()/exec() on user input."""
    skip_dirs = {".venv", "node_modules", "__pycache__", ".git", "models", "dela_state", "frontend/dist"}
    skip_files = {"dela\\security.py", "dela\\vuln_kb.py"}
    issues = []
    for py_file in ROOT.rglob("*.py"):
        if any(part in skip_dirs for part in py_file.parts):
            continue
        rel_str = str(py_file.relative_to(ROOT)).replace("/", "\\")
        if rel_str in skip_files:
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in re.finditer(r'\b(?:eval|exec)\s*\(', text):
            line_num = text[:m.start()].count('\n') + 1
            rel = py_file.relative_to(ROOT)
            issues.append(f"{rel}:{line_num}")
    if issues:
        return Finding("warning", "vuln_kb", "CWE-94: eval()/exec() found",
                       f"Locations: {', '.join(issues[:5])}. Ensure not used on user input.")
    return Finding("ok", "vuln_kb", "CWE-94: No eval()/exec() usage", "")


def _check_deserialization() -> Finding:
    """CWE-502: Check for unsafe deserialization."""
    skip_dirs = {".venv", "node_modules", "__pycache__", ".git", "models", "dela_state", "frontend/dist"}
    issues = []
    for py_file in ROOT.rglob("*.py"):
        if any(part in skip_dirs for part in py_file.parts):
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if re.search(r'\bpickle\.(load|loads)\b', text):
            rel = py_file.relative_to(ROOT)
            issues.append(f"{rel} (pickle)")
        if re.search(r'\byaml\.(load|unsafe_load)\b', text) and not re.search(r'SafeLoader', text):
            rel = py_file.relative_to(ROOT)
            issues.append(f"{rel} (yaml.unsafe_load)")
    if issues:
        return Finding("warning", "vuln_kb", "CWE-502: Unsafe deserialization",
                       f"Use json or SafeLoader. Found: {', '.join(issues[:5])}")
    return Finding("ok", "vuln_kb", "CWE-502: No unsafe deserialization", "")


def _check_info_exposure() -> Finding:
    """CWE-200: Check error messages don't leak secrets."""
    try:
        server_text = (ROOT / "dela" / "server.py").read_text(encoding="utf-8")
        has_debug = "debug=True" in server_text or "DEBUG.*True" in server_text
        if has_debug:
            return Finding("warning", "vuln_kb", "CWE-200: Debug mode may leak info",
                           "Disable debug=True in production.")
        return Finding("ok", "vuln_kb", "CWE-200: Debug mode disabled", "")
    except Exception:
        return Finding("info", "vuln_kb", "CWE-200: Could not check debug mode", "")


def _check_missing_auth() -> Finding:
    """CWE-306: Check API auth in work profile."""
    try:
        from dela.profiles import get_current_profile, get_current_profile_name
        name = get_current_profile_name()
        profile = get_current_profile()
        if name == "work":
            if profile.cors_origins == ["*"]:
                return Finding("warning", "vuln_kb", "CWE-306: Work profile has wildcard CORS",
                               "Restrict CORS origins in work profile.")
            return Finding("ok", "vuln_kb", "CWE-306: Work profile has restricted access", "")
        return Finding("info", "vuln_kb", "CWE-306: Personal profile (auth optional)", "")
    except Exception:
        return Finding("info", "vuln_kb", "CWE-306: Could not check auth", "")


def _check_resource_limits() -> Finding:
    """CWE-770: Check for rate limiting / resource limits."""
    try:
        server_text = (ROOT / "dela" / "server.py").read_text(encoding="utf-8")
        has_limits = any(kw in server_text.lower() for kw in ["ratelimit", "rate_limit", "throttle", "max_tokens", "timeout"])
        has_compaction = "compact" in server_text.lower()
        if has_limits or has_compaction:
            return Finding("ok", "vuln_kb", "CWE-770: Resource limits present",
                           f"Found: {', '.join(k for k in ['rate_limit', 'timeout', 'compaction'] if k in server_text.lower())}")
        return Finding("warning", "vuln_kb", "CWE-770: No resource limits detected",
                       "Add rate limiting, timeouts, and token budgets.")
    except Exception:
        return Finding("info", "vuln_kb", "CWE-770: Could not check resource limits", "")


def _check_ssrf() -> Finding:
    """CWE-918: Check web fetch URL validation."""
    try:
        fetch_files = list(ROOT.glob("dela/tools/*.py"))
        has_url_validation = False
        for f in fetch_files:
            text = f.read_text(encoding="utf-8", errors="replace")
            if any(kw in text.lower() for kw in ["urlparse", "validate_url", "whitelist", "allowed_domain", "is_domain_whitelisted"]):
                has_url_validation = True
                break
        if has_url_validation:
            return Finding("ok", "vuln_kb", "CWE-918: URL validation present", "")
        return Finding("info", "vuln_kb", "CWE-918: No URL validation in fetch tools",
                       "Consider validating URLs in web fetch tools.")
    except Exception:
        return Finding("info", "vuln_kb", "CWE-918: Could not check SSRF", "")


def _check_data_poisoning() -> Finding:
    """LLM04: Check memory/RAG data validation."""
    try:
        memory_text = (ROOT / "dela" / "memory.py").read_text(encoding="utf-8")
        has_validation = any(kw in memory_text.lower() for kw in ["validate", "sanitize", "check", "limit", "max_"])
        if has_validation:
            return Finding("ok", "vuln_kb", "LLM04: Memory has validation", "")
        return Finding("info", "vuln_kb", "LLM04: Memory lacks data validation",
                       "Consider validating memory entries before storage.")
    except Exception:
        return Finding("info", "vuln_kb", "LLM04: Could not check memory validation", "")


def _check_output_handling() -> Finding:
    """LLM05: Check tool output validation."""
    try:
        brain_text = (ROOT / "dela" / "brain.py").read_text(encoding="utf-8")
        has_truncation = "truncate" in brain_text.lower() or "max_length" in brain_text.lower() or "[:1000]" in brain_text
        if has_truncation:
            return Finding("ok", "vuln_kb", "LLM05: Tool output truncated/validated", "")
        return Finding("info", "vuln_kb", "LLM05: Tool output not truncated",
                       "Consider truncating tool outputs before feeding to LLM.")
    except Exception:
        return Finding("info", "vuln_kb", "LLM05: Could not check output handling", "")


def _check_prompt_leakage() -> Finding:
    """LLM07: Check system prompt doesn't contain secrets."""
    try:
        from dela.system_prompt import build_system_prompt
        prompt = build_system_prompt()
        secret_patterns = [r"sk-[a-zA-Z0-9]{20,}", r"ghp_[a-zA-Z0-9]{36}", r"password\s*=\s*['\"][^'\"]+['\"]"]
        for pat in secret_patterns:
            if re.search(pat, prompt):
                return Finding("critical", "vuln_kb", "LLM07: Secrets found in system prompt!",
                               "Remove all secrets from system prompt text.")
        return Finding("ok", "vuln_kb", "LLM07: No secrets in system prompt", "")
    except Exception:
        return Finding("info", "vuln_kb", "LLM07: Could not check prompt for secrets", "")


def _check_unbounded_consumption() -> Finding:
    """LLM10: Check for token/cost limits and compaction."""
    try:
        from dela.live_config import get as lc_get
        has_compaction = "compact" in (ROOT / "dela" / "compaction.py").read_text(encoding="utf-8", errors="replace").lower()
        max_tokens = lc_get("max_tokens", 0) if hasattr(lc_get, '__call__') else 0
        if has_compaction:
            return Finding("ok", "vuln_kb", "LLM10: Compaction + token limits active", "")
        return Finding("info", "vuln_kb", "LLM10: No compaction detected",
                       "Enable conversation compaction to limit token usage.")
    except Exception:
        return Finding("info", "vuln_kb", "LLM10: Could not check consumption limits", "")


def _scan_vuln_kb() -> list[Finding]:
    """Run vulnerability KB checks against the codebase."""
    from dela.vuln_kb import get_checklist

    findings: list[Finding] = []

    # Map check_id -> function
    check_map = {
        "cwe78_command_injection": _check_shell_injection,
        "cwe22_path_traversal": _check_path_traversal,
        "cwe94_code_injection": _check_code_injection,
        "cwe502_deserialization": _check_deserialization,
        "cwe200_info_exposure": _check_info_exposure,
        "cwe306_missing_auth": _check_missing_auth,
        "cwe770_resource_limits": _check_resource_limits,
        "cwe918_ssrf": _check_ssrf,
        "llm04_data_poisoning": _check_data_poisoning,
        "llm05_output_handling": _check_output_handling,
        "llm07_prompt_leakage": _check_prompt_leakage,
        "llm10_unbounded_consumption": _check_unbounded_consumption,
    }

    checklist = get_checklist()
    checked_ids: set[str] = set()

    for item in checklist:
        check_id = item.get("check_id", "")
        if check_id in check_map and check_id not in checked_ids:
            try:
                finding = check_map[check_id]()
                finding.category = "vuln_kb"
                findings.append(finding)
                checked_ids.add(check_id)
            except Exception as e:
                findings.append(Finding("info", "vuln_kb", f"{item['id']}: check failed", str(e)[:100]))

    # Summary finding
    kb_count = len(checklist)
    checked = len(checked_ids)
    findings.append(Finding(
        "ok", "vuln_kb", f"Vuln KB: {checked}/{kb_count} checks run",
        f"Sources: OWASP LLM Top 10 2025, CWE Top 25 2025",
    ))

    return findings


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
    all_findings += _scan_profile()
    all_findings += _scan_vuln_kb()

    # Prioritize findings
    prioritized = _prioritize_findings(all_findings)

    findings_dict = [f.to_dict() for f in prioritized]
    critical = sum(1 for f in prioritized if f.severity == "critical")
    warning = sum(1 for f in prioritized if f.severity == "warning")
    ok = sum(1 for f in prioritized if f.severity == "ok")
    info = sum(1 for f in prioritized if f.severity == "info")

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
            "total": len(prioritized),
        },
        "findings": findings_dict,
        "status": "critical" if critical > 0 else "warning" if warning > 0 else "secure",
    }


# Priority levels for findings
_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4, None: 5}

# Categories that are more dangerous if they have findings
_HIGH_IMPACT_CATEGORIES = {"secrets", "gate", "injection", "sandbox", "vuln_kb"}
_MEDIUM_IMPACT_CATEGORIES = {"network", "deps", "profile"}


def _prioritize_findings(findings: list[Finding]) -> list[Finding]:
    """Sort findings by priority: P0 (critical+exploitable) → P4 (info).

    Priority assignment:
      P0: Critical + high-impact category (secrets, injection, sandbox)
      P1: Critical + other category
      P2: Warning + high-impact category
      P3: Warning + other category
      P4: Info / OK
    """
    def get_priority(f: Finding) -> str:
        if f.severity == "critical":
            return "P0" if f.category in _HIGH_IMPACT_CATEGORIES else "P1"
        elif f.severity == "warning":
            return "P2" if f.category in _HIGH_IMPACT_CATEGORIES else "P3"
        else:
            return "P4"

    def sort_key(f: Finding) -> tuple:
        priority = get_priority(f)
        f.priority = priority
        return (_PRIORITY_ORDER[priority], f.severity != "critical", f.severity != "warning")

    return sorted(findings, key=sort_key)


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
