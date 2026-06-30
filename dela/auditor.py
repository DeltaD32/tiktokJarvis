"""Shared asset auditor — security, usability, impact, and efficiency analysis.

Every new tool, agent, skill, or workflow passes through this auditor before
deployment. It produces a structured report with scores and actionable findings.

Usage:
    from dela.auditor import audit_tool, audit_agent, audit_workflow
    report = audit_tool(name="delete_all", description="...", parameters={...})
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuditFinding:
    category: str       # security, usability, impact, efficiency
    severity: str       # critical, high, medium, low, info
    message: str
    suggestion: str = ""


@dataclass
class AuditReport:
    asset_type: str     # tool, agent, workflow
    asset_name: str
    scores: dict[str, float] = field(default_factory=lambda: {"security": 0, "usability": 0, "impact": 0, "efficiency": 0})
    findings: list[AuditFinding] = field(default_factory=list)
    passed: bool = False

    @property
    def overall(self) -> float:
        weights = {"security": 0.35, "usability": 0.25, "impact": 0.25, "efficiency": 0.15}
        return round(sum(self.scores[k] * v for k, v in weights.items()), 1)

    @property
    def grade(self) -> str:
        s = self.overall
        if s >= 9.0: return "A+"
        if s >= 8.0: return "A"
        if s >= 7.0: return "B"
        if s >= 6.0: return "C"
        if s >= 5.0: return "D"
        return "F"


# ── Security checks ──────────────────────────────────────────────────────────

_DANGEROUS_KEYWORDS = [
    "delete", "drop", "truncate", "destroy", "purge", "wipe", "nuke",
    "execute", "exec", "eval", "system", "shell", "os.", "subprocess",
    "sudo", "root", "admin", "unrestricted", "bypass", "override",
    "rm ", "rmdir", "format", "partition", "mkfs",
]

_DANGEROUS_PARAM_PATTERNS = [
    (r"(?i)\b(command|cmd|shell|script|code|exec|eval)\b", "Accepts arbitrary code/command input — high injection risk"),
    (r"(?i)\b(path|file|dir|folder|filename)\b", "File path parameter — validate against traversal attacks"),
    (r"(?i)\b(url|uri|link|endpoint)\b", "URL parameter — validate scheme and domain allowlist"),
    (r"(?i)\b(sql|query|database|db)\b", "Database query parameter — use parameterized queries"),
    (r"(?i)\b(password|secret|token|key|credential)\b", "Credentials parameter — must never be logged or stored in plaintext"),
]


def _check_security(name: str, description: str, parameters: dict | None, requires_confirmation: bool) -> list[AuditFinding]:
    findings = []
    name_lower = name.lower()
    desc_lower = (description or "").lower()
    score = 10.0

    # Check name for dangerous keywords
    for kw in _DANGEROUS_KEYWORDS:
        if kw in name_lower:
            findings.append(AuditFinding("security", "high",
                f"Tool name contains dangerous keyword '{kw}' — may indicate destructive operation",
                "Consider a softer verb (e.g. 'remove' instead of 'delete')"))
            score -= 2.0
            break

    # Check description for dangerous patterns
    for kw in _DANGEROUS_KEYWORDS:
        if kw in desc_lower:
            findings.append(AuditFinding("security", "medium",
                f"Description references '{kw}' — ensure proper safeguards",
                "Add input validation and confirmation requirements"))
            score -= 1.0
            break

    # Check parameters for dangerous patterns
    if parameters and "properties" in parameters:
        for param_name, param_info in parameters["properties"].items():
            for pattern, warning in _DANGEROUS_PARAM_PATTERNS:
                if re.search(pattern, param_name) or re.search(pattern, param_info.get("description", "")):
                    findings.append(AuditFinding("security", "medium", f"Parameter '{param_name}': {warning}",
                        f"Add validation, sanitization, and allowlist for '{param_name}'"))
                    score -= 1.5
                    break

    # Confirmation gate check
    if not requires_confirmation and any(kw in name_lower for kw in ["delete", "remove", "forget", "destroy", "purge"]):
        findings.append(AuditFinding("security", "high",
            "Destructive operation lacks confirmation requirement",
            "Set requires_confirmation=True or add impact_score function"))
        score -= 3.0

    if requires_confirmation:
        findings.append(AuditFinding("security", "info",
            "Confirmation gate is enabled — user must approve before execution", ""))
        score = min(10.0, score + 0.5)  # bonus for having confirmation

    return findings, max(0.0, score)


# ── Usability checks ─────────────────────────────────────────────────────────

def _check_usability(name: str, description: str, parameters: dict | None) -> list[AuditFinding]:
    findings = []
    score = 10.0

    # Name quality
    if not name:
        findings.append(AuditFinding("usability", "critical", "Asset has no name", "Provide a descriptive snake_case name"))
        score -= 10.0
    elif "_" not in name and len(name) > 15:
        findings.append(AuditFinding("usability", "low", "Name uses CamelCase — prefer snake_case", f"Rename to {_to_snake(name)}"))
        score -= 0.5
    elif len(name) < 5:
        findings.append(AuditFinding("usability", "low", "Name is very short — may be ambiguous", "Use a more descriptive name"))
        score -= 1.0
    elif len(name) > 40:
        findings.append(AuditFinding("usability", "low", "Name is very long — may be hard to type", "Shorten to under 40 characters"))
        score -= 0.5

    # Description quality
    if not description or len(description) < 20:
        findings.append(AuditFinding("usability", "medium",
            "Description is too short (< 20 chars) — model may misuse the tool",
            "Write a clear one-sentence description of WHEN to use this tool"))
        score -= 3.0
    elif len(description) > 500:
        findings.append(AuditFinding("usability", "low",
            "Description is very long (> 500 chars) — model may ignore details",
            "Keep description under 300 characters for optimal model comprehension"))
        score -= 1.0

    # Parameter count
    param_count = len(parameters.get("properties", {})) if parameters else 0
    if param_count == 0 and name not in ("list_facts",):
        findings.append(AuditFinding("usability", "low", "No parameters defined", "Consider if the tool needs any input"))
    elif param_count > 5:
        findings.append(AuditFinding("usability", "medium",
            f"High parameter count ({param_count}) — increases cognitive load",
            "Split into multiple focused tools or make non-essential params optional"))
        score -= 2.0

    # Check for required params that should be optional
    if parameters and "required" in parameters and "properties" in parameters:
        required = set(parameters["required"])
        optional_count = len(parameters["properties"]) - len(required)
        if len(required) > 3:
            findings.append(AuditFinding("usability", "low",
                f"{len(required)} required parameters — consider making some optional with defaults",
                "Reduce required params to 3 or fewer for better usability"))
            score -= 1.0

    return findings, max(0.0, score)


# ── Impact analysis ──────────────────────────────────────────────────────────

def _check_impact(name: str, description: str, requires_confirmation: bool) -> list[AuditFinding]:
    findings = []
    score = 0.0
    name_lower = name.lower()
    desc_lower = (description or "").lower()

    # Destructive operations
    if any(kw in name_lower for kw in ["delete", "remove", "destroy", "purge", "forget", "wipe"]):
        score += 8.0
        findings.append(AuditFinding("impact", "high", "Destructive operation — data will be permanently lost",
            "Ensure confirmation is required and consider soft-delete with undo"))
    elif any(kw in name_lower for kw in ["update", "change", "modify", "edit", "set", "write", "save"]):
        score += 4.0
        findings.append(AuditFinding("impact", "medium", "Mutating operation — changes existing data",
            "Consider logging changes for audit trail"))
    elif any(kw in name_lower for kw in ["create", "add", "new", "generate", "build"]):
        score += 2.0
        findings.append(AuditFinding("impact", "low", "Creation operation — adds new data only",
            "Low risk but may consume resources"))
    else:
        score += 1.0
        findings.append(AuditFinding("impact", "info", "Read-only or query operation — no side effects", ""))

    # External interaction
    if any(kw in desc_lower for kw in ["api", "http", "fetch", "url", "web", "network", "remote"]):
        score += 2.0
        findings.append(AuditFinding("impact", "medium", "Interacts with external services — network risk",
            "Add timeout, retry logic, and error handling"))

    # Confirmation provides impact mitigation
    if requires_confirmation:
        score = max(0.0, score - 2.0)

    return findings, min(10.0, score)


# ── Efficiency checks ────────────────────────────────────────────────────────

def _check_efficiency(name: str, description: str, parameters: dict | None) -> list[AuditFinding]:
    findings = []
    score = 10.0
    desc_lower = (description or "").lower()

    # Suggest batching for list operations
    if "list" in name.lower() and parameters and "properties" in parameters:
        has_limit = any("limit" in p.lower() or "max" in p.lower() for p in parameters["properties"])
        if not has_limit:
            findings.append(AuditFinding("efficiency", "low",
                "List operation without limit parameter — may return excessive data",
                "Add a 'limit' parameter with a sensible default (e.g. 50)"))
            score -= 1.0

    # Suggest caching for read operations
    if all(kw not in name.lower() for kw in ["create", "add", "update", "delete", "remove", "set", "write"]):
        if not any(kw in desc_lower for kw in ["cache", "cached", "memoize"]):
            findings.append(AuditFinding("efficiency", "low",
                "Read-only tool — consider caching results for repeated calls",
                "Add a short-lived cache (e.g. 30s TTL) for frequently-queried data"))
            score -= 0.5

    # Large parameter sets
    if parameters and "properties" in parameters:
        large_props = [k for k, v in parameters["properties"].items()
                       if v.get("type") == "string" and not v.get("maxLength")]
        if large_props:
            findings.append(AuditFinding("efficiency", "low",
                f"Unbounded string parameters: {', '.join(large_props[:3])}",
                "Add maxLength constraints to prevent memory exhaustion"))
            score -= 1.0

    # Sequential operations suggestion
    if any(kw in name.lower() for kw in ["batch", "bulk", "all", "every"]):
        findings.append(AuditFinding("efficiency", "info",
            "Bulk operation — ensure it processes items concurrently where possible",
            "Use ThreadPoolExecutor or asyncio.gather for parallel execution"))
        score = min(10.0, score + 0.5)

    return findings, max(0.0, score)


# ── Public API ───────────────────────────────────────────────────────────────

def _to_snake(name: str) -> str:
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


_MAX_NAME_LEN = 200
_MAX_DESC_LEN = 2000


def audit_tool(name: str, description: str = "", parameters: dict | None = None,
               requires_confirmation: bool = False) -> AuditReport:
    """Audit a tool before deployment. Returns structured report with scores."""
    name = (name or "")[:_MAX_NAME_LEN]
    description = (description or "")[:_MAX_DESC_LEN]
    report = AuditReport(asset_type="tool", asset_name=name)
    all_findings = []

    sec_findings, report.scores["security"] = _check_security(name, description, parameters, requires_confirmation)
    all_findings.extend(sec_findings)

    use_findings, report.scores["usability"] = _check_usability(name, description, parameters)
    all_findings.extend(use_findings)

    imp_findings, report.scores["impact"] = _check_impact(name, description, requires_confirmation)
    all_findings.extend(imp_findings)

    eff_findings, report.scores["efficiency"] = _check_efficiency(name, description, parameters)
    all_findings.extend(eff_findings)

    report.findings = all_findings
    report.passed = report.overall >= 5.0
    return report


def audit_agent(name: str, description: str = "", tools: list[str] | None = None) -> AuditReport:
    """Audit an agent before deployment."""
    name = (name or "")[:_MAX_NAME_LEN]
    description = (description or "")[:_MAX_DESC_LEN]
    report = AuditReport(asset_type="agent", asset_name=name)
    all_findings = []

    sec_findings, report.scores["security"] = _check_security(name, description, None, True)
    all_findings.extend(sec_findings)

    use_findings, report.scores["usability"] = _check_usability(name, description, None)
    all_findings.extend(use_findings)

    # Agent-specific: check tool whitelist
    if tools and len(tools) > 10:
        all_findings.append(AuditFinding("usability", "medium",
            f"Agent has {len(tools)} tools — consider narrowing the whitelist for focus",
            "Limit to 5-8 core tools for better agent reliability"))
        report.scores["usability"] = max(0.0, report.scores["usability"] - 2.0)

    if tools and all(t in ["run_code", "fetch_url"] for t in tools):
        all_findings.append(AuditFinding("security", "high",
            "Agent has code execution AND web access — double-check safety",
            "Consider restricting to one high-risk capability per agent"))
        report.scores["security"] = max(0.0, report.scores["security"] - 3.0)

    imp_findings, report.scores["impact"] = _check_impact(name, description, True)
    all_findings.extend(imp_findings)

    eff_findings, report.scores["efficiency"] = _check_efficiency(name, description, None)
    all_findings.extend(eff_findings)

    report.findings = all_findings
    report.passed = report.overall >= 5.0
    return report


def audit_workflow(name: str, description: str = "", steps: list[dict] | None = None) -> AuditReport:
    """Audit a workflow before deployment."""
    name = (name or "")[:_MAX_NAME_LEN]
    description = (description or "")[:_MAX_DESC_LEN]
    report = AuditReport(asset_type="workflow", asset_name=name)
    all_findings = []

    sec_findings, report.scores["security"] = _check_security(name, description, None, True)
    all_findings.extend(sec_findings)

    use_findings, report.scores["usability"] = _check_usability(name, description, None)
    all_findings.extend(use_findings)

    # Workflow-specific: step analysis
    if steps:
        if len(steps) == 1:
            all_findings.append(AuditFinding("efficiency", "info",
                "Single-step workflow — consider using a direct tool call instead",
                "Workflows are best for 2+ coordinated steps"))
        if len(steps) > 10:
            all_findings.append(AuditFinding("usability", "medium",
                f"Workflow has {len(steps)} steps — consider splitting into sub-workflows",
                "Break into smaller workflows for maintainability"))
            report.scores["usability"] = max(0.0, report.scores["usability"] - 1.5)

        # Check for parallelizable steps
        step_names = [s.get("agent") for s in steps if s.get("agent")]
        if len(step_names) > len(set(step_names)):
            all_findings.append(AuditFinding("efficiency", "info",
                "Same agent used multiple times — steps may be parallelizable",
                "Consider grouping sequential steps under a single agent dispatch"))

    imp_findings, report.scores["impact"] = _check_impact(name, description, True)
    all_findings.extend(imp_findings)

    eff_findings, report.scores["efficiency"] = _check_efficiency(name, description, None)
    all_findings.extend(eff_findings)

    report.findings = all_findings
    report.passed = report.overall >= 5.0
    return report


# ── Repository compatibility audit ─────────────────────────────────────────────

def audit_repository(
    repo_name: str,
    repo_description: str = "",
    tech_stack: list[str] | None = None,
    features: list[str] | None = None,
    new_dependencies: list[str] | None = None,
    integration_points: list[str] | None = None,
    security_notes: str = "",
) -> AuditReport:
    """Audit an external repository for compatibility with Dela.

    Scores across four dimensions:
      - security: dependency safety, credential handling, network exposure
      - usability: feature overlap, fit with Dela's patterns
      - impact: how much it would change Dela (low = better)
      - efficiency: integration effort, runtime cost, dependency weight

    Returns an AuditReport with scores, findings, and a pass/fail verdict.
    """
    name = (repo_name or "")[:_MAX_NAME_LEN]
    description = (repo_description or "")[:_MAX_DESC_LEN]
    report = AuditReport(asset_type="repository", asset_name=name)
    all_findings = []

    tech_stack = tech_stack or []
    features = features or []
    new_deps = new_dependencies or []
    integration_pts = integration_points or []

    # ── Security scoring ──────────────────────────────────────────────────
    sec_score = 8.0

    for dep in new_deps:
        dep_lower = dep.lower()
        if any(kw in dep_lower for kw in ["exec", "subprocess", "docker", "shell"]):
            all_findings.append(AuditFinding(
                "security", "high",
                f"New dependency '{dep}' introduces code execution capability",
                "Ensure sandboxing before integrating"))
            sec_score = max(0.0, sec_score - 3.0)
        elif any(kw in dep_lower for kw in ["transformers", "torch", "onnx", "cuda"]):
            all_findings.append(AuditFinding(
                "security", "medium",
                f"New dependency '{dep}' is large and may introduce supply-chain risk",
                "Pin versions and review SBOM"))
            sec_score = max(0.0, sec_score - 1.5)
        elif any(kw in dep_lower for kw in ["http", "request", "fetch", "socket"]):
            all_findings.append(AuditFinding(
                "security", "medium",
                f"New dependency '{dep}' involves network access",
                "Ensure proper URL validation and timeout handling"))
            sec_score = max(0.0, sec_score - 1.0)

    seclower = security_notes.lower()
    if any(kw in seclower for kw in ["injection", "secret", "credential", "token leak"]):
        all_findings.append(AuditFinding(
            "security", "critical",
            "Analysis flagged potential credential/injection risk",
            "Requires full security review before integration"))
        sec_score = max(0.0, sec_score - 5.0)
    elif any(kw in seclower for kw in ["network", "exposed", "public"]):
        all_findings.append(AuditFinding(
            "security", "medium",
            "Repository involves network-exposed features",
            "Confirm it works offline and behind firewall"))
        sec_score = max(0.0, sec_score - 2.0)

    report.scores["security"] = max(0.0, sec_score)

    # ── Usability scoring ─────────────────────────────────────────────────
    use_score = 7.0

    overlap_keywords = {
        "memory": "Dela already has a memory system",
        "voice": "Dela already has a full voice stack",
        "web search": "Dela already has fetch_url + researcher agent",
        "ppt": "Dela already has presentation generation",
        "security scan": "Dela already has security self-audit",
        "heartbeat": "Dela already has heartbeat checks",
        "compaction": "Dela already has compaction.py",
        "tools": "May overlap with Dela's tool system",
    }
    feature_text = " ".join(features + [description]).lower()
    for keyword, msg in overlap_keywords.items():
        if keyword in feature_text:
            all_findings.append(AuditFinding(
                "usability", "info",
                msg,
                "Evaluate if the external implementation adds value beyond Dela's built-in"))
            use_score = max(0.0, use_score - 1.0)

    if len(features) > 0 and any(
        kw not in feature_text
        for kw in ["memory", "voice", "speech", "web search", "ppt", "security", "heartbeat"]
    ):
        use_score = min(10.0, use_score + 1.0)

    ts_text = " ".join(tech_stack).lower()
    if "python" in ts_text:
        use_score = min(10.0, use_score + 1.0)
    if "rust" in ts_text:
        all_findings.append(AuditFinding(
            "usability", "medium",
            "Rust dependency requires C/C++ build toolchain",
            "Dela is pure Python — Rust adds compilation complexity"))
        use_score = max(0.0, use_score - 1.0)
    if "typescript" in ts_text or "javascript" in ts_text:
        all_findings.append(AuditFinding(
            "usability", "low",
            "JS/TS presence may add Node.js dependency",
            "Consider if the Python API is sufficient"))

    report.scores["usability"] = max(0.0, min(10.0, use_score))

    # ── Impact scoring ────────────────────────────────────────────────────
    impact_score = 10.0

    for pt in integration_pts:
        pt_lower = pt.lower()
        if any(kw in pt_lower for kw in ["brain", "core", "provider"]):
            all_findings.append(AuditFinding(
                "impact", "high",
                f"Integration touches core module: {pt}",
                "Core changes risk regression across all entry points"))
            impact_score = max(0.0, impact_score - 4.0)
        elif any(kw in pt_lower for kw in ["tool", "agent", "skill", "channel"]):
            all_findings.append(AuditFinding(
                "impact", "low",
                f"Integration at edge seam: {pt}",
                "Extension seams are designed for this — low risk"))
            impact_score = min(10.0, impact_score + 0.5)
        elif "proxy" in pt_lower or "mcp" in pt_lower:
            all_findings.append(AuditFinding(
                "impact", "medium",
                f"Integration via proxy/intermediary: {pt}",
                "Adds a runtime dependency process"))
            impact_score = max(0.0, impact_score - 2.0)

    if len(new_deps) > 5:
        all_findings.append(AuditFinding(
            "impact", "medium",
            f"Adds {len(new_deps)} new dependencies",
            "Each new dependency increases maintenance surface"))
        impact_score = max(0.0, impact_score - len(new_deps) * 0.5)

    report.scores["impact"] = max(0.0, min(10.0, impact_score))

    # ── Efficiency scoring ────────────────────────────────────────────────
    eff_score = 7.0

    if len(new_deps) > 3:
        eff_score = max(0.0, eff_score - (len(new_deps) - 3) * 0.5)

    for dep in new_deps:
        dep_lower = dep.lower()
        if any(kw in dep_lower for kw in ["transformers", "torch", "onnx", "cuda"]):
            all_findings.append(AuditFinding(
                "efficiency", "low",
                f"Heavyweight dependency: {dep}",
                "Consider if runtime cost is acceptable"))
            eff_score = max(0.0, eff_score - 1.0)

    if len(new_deps) == 0:
        all_findings.append(AuditFinding(
            "efficiency", "info",
            "No new dependencies required",
            "Can be implemented with existing Dela stack"))
        eff_score = min(10.0, eff_score + 2.0)

    num_int_points = len(integration_pts)
    if num_int_points == 1:
        eff_score = min(10.0, eff_score + 1.0)
    elif num_int_points > 3:
        all_findings.append(AuditFinding(
            "efficiency", "medium",
            f"Requires {num_int_points} integration points",
            "Multi-point integration increases testing surface"))
        eff_score = max(0.0, eff_score - (num_int_points - 3) * 0.5)

    report.scores["efficiency"] = max(0.0, min(10.0, eff_score))

    report.findings = all_findings
    report.passed = report.overall >= 5.0
    return report
