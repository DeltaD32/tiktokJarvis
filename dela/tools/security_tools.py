"""Security tools — let the model run security scans and review findings."""

from __future__ import annotations

from dela.tools import register


@register(
    name="run_security_scan",
    description=(
        "Run a full security audit of Dela's codebase, dependencies, and configuration. "
        "Checks for: hardcoded secrets, missing confirmation gates, prompt injection "
        "defense gaps, vulnerable npm/pip packages, network exposure, sandbox safety, "
        "and audit trail health. Returns a structured report with severity levels. "
        "Use this when the user asks about security, wants a vulnerability check, "
        "or says 'audit my system'."
    ),
    parameters={"type": "object", "properties": {}},
)
def run_security_scan_tool(args: dict) -> str:
    from dela.security import run_full_scan
    report = run_full_scan()
    lines = [
        f"Security Scan Results — Score: {report['score']}/100 — Status: {report['status'].upper()}",
        f"Critical: {report['summary']['critical']} | Warning: {report['summary']['warning']} | OK: {report['summary']['ok']} | Info: {report['summary']['info']}",
        "",
    ]
    for f in report["findings"]:
        icon = {"critical": "[!]", "warning": "[/]", "ok": "[+]", "info": "[i]"}[f["severity"]]
        lines.append(f"{icon} [{f['category']}] {f['title']}")
        if f["detail"]:
            lines.append(f"    {f['detail']}")
    return "\n".join(lines)


@register(
    name="get_security_status",
    description=(
        "Get the last security scan results without running a new scan. "
        "Use this for a quick status check. Returns the security score, "
        "summary counts, and any critical findings."
    ),
    parameters={"type": "object", "properties": {}},
)
def get_security_status_tool(args: dict) -> str:
    from dela.security import last_scan
    report = last_scan()
    lines = [
        f"Security Status — Score: {report['score']}/100 — {report['status'].upper()}",
        f"Critical: {report['summary']['critical']} | Warning: {report['summary']['warning']} | OK: {report['summary']['ok']}",
    ]
    criticals = [f for f in report["findings"] if f["severity"] == "critical"]
    if criticals:
        lines.append("\nCRITICAL FINDINGS:")
        for f in criticals:
            lines.append(f"  [{f['category']}] {f['title']}: {f['detail']}")
    return "\n".join(lines)
