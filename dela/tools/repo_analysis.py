"""External repository analysis tool — dissect features, score fit, surface adoptable ideas.

Given a GitHub repo URL, this tool:
  1. Fetches the README via raw GitHub URLs (through content sandbox)
  2. Constructs a structured analysis brief from the fetched content
  3. Dispatches the system_expert sub-agent to perform impact analysis
  4. Separates "direct integration" from "clean-room feature adoption"
  5. Returns a scored report with two verdicts:
     - Integration verdict (RECOMMENDED/REJECTED/CONDITIONAL) — for code adoption
     - Per-feature adoptable ideas — what Dela could build from scratch, inspired by this repo

The system_expert knows Dela's architecture intimately and determines:
  - Whether direct code integration is architecturally sound
  - Which features could be reverse-engineered and built from scratch using Dela's patterns
  - Security considerations for both approaches
  - Concrete implementation plans for adoptable features

Reverse-engineering is always preferred over copy/paste. The tool surfaces ideas
worth building natively, not dependencies worth installing.
"""

from __future__ import annotations

import re

from dela.content_sandbox import secure_fetch, SandboxError
from dela.tools import register

_MAX_BYTES = 80_000
_TIMEOUT = 20


def _fetch_raw(url: str) -> str:
    """Fetch a URL through the content sandbox, returning clean text."""
    try:
        result = secure_fetch(url, max_bytes=_MAX_BYTES, timeout=_TIMEOUT,
                              allow_html=False)  # READMEs are markdown, not HTML
    except SandboxError as e:
        return f"Sandbox blocked: {e}"
    except ValueError as e:
        return f"URL error: {e}"
    except Exception as e:
        return f"Fetch error: {e}"

    return result["text"]


def _github_raw_urls(gh_url: str) -> dict[str, str]:
    """Derive raw.githubusercontent.com URLs from a GitHub repo URL.

    Supports:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - https://github.com/owner/repo/tree/branch/path
    """
    # Normalize: strip trailing .git, slashes, and tree/ paths to get owner/repo
    url = gh_url.rstrip("/").replace(".git", "")

    # Match github.com/owner/repo
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)", url)
    if not m:
        return {}

    owner, repo = m.group(1), m.group(2)
    base = f"https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/main"

    return {
        "readme": f"{base}/README.md",
        "contributing": f"{base}/CONTRIBUTING.md",
        "architecture": f"{base}/docs/architecture.md",
        "roadmap": f"{base}/ROADMAP.md",
        "readme_alt": f"https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/master/README.md",
    }


def _dispatch_system_expert(task: str, max_attempts: int = 2) -> str:
    """Dispatch the system_expert sub-agent and return its result.
    
    Retries once on empty result (LLMs are non-deterministic).
    """
    from dela.agents import get_agent
    from dela.brain import run_subagent
    from dela.agent_status import mark_busy, mark_ready, mark_error

    soul = get_agent("system_expert")
    if soul is None:
        return "ERROR: system_expert agent not found"

    prompt = soul.build_prompt()
    # Strip fetch_url from whitelist — we pre-fetch content so the sub-agent
    # shouldn't fetch more and risk context overflow
    safe_whitelist = (soul.tool_whitelist - {"fetch_url"}) if soul.tool_whitelist else None
    for attempt in range(max_attempts):
        mark_busy("system_expert", task[:80])
        try:
            result = run_subagent(
                agent_name="system_expert",
                task=task,
                system_prompt_text=prompt,
                tool_whitelist=safe_whitelist,
            )
            mark_ready("system_expert")
            if result and result.strip():
                return result
        except Exception as e:
            mark_error("system_expert", str(e))
            if attempt < max_attempts - 1:
                continue
            return f"ERROR: system_expert dispatch failed: {e}"

    return "ERROR: system_expert returned empty result after retries"


def _audit_repo_fit(repo_name: str, features_summary: str, analysis_text: str) -> dict:
    """Score the repo's fit for DIRECT CODE INTEGRATION with Dela."""
    compat = _extract_score(analysis_text, "compatibility", 5.0)
    benefit = _extract_score(analysis_text, "benefit", 5.0)
    complexity = _extract_score(analysis_text, "complexity", 5.0)
    safety = _extract_score(analysis_text, "safety", 7.0)

    text_lower = (features_summary + analysis_text).lower()

    # Penalize if the analysis mentions core rewrites
    if any(phrase in text_lower for phrase in ["rewrite brain", "edit brain", "core change", "edit provider"]):
        complexity = min(complexity, 4.0)

    # License blocker detection
    if any(lic in text_lower for lic in ["agpl", "gpl-3", "gplv3"]):
        compatibility = min(compatibility, 3.0)
        safety = max(safety - 3.0, 0.0)

    # Architecture mismatch
    if "monolith" in text_lower or "docker-compose" in text_lower:
        complexity = min(complexity, 5.0)
        compatibility = max(compatibility - 1.5, 0.0)

    overall = compat * 0.30 + benefit * 0.35 + complexity * 0.20 + safety * 0.15

    if benefit >= 7.0 and complexity >= 6.0 and overall >= 6.5:
        verdict = "RECOMMENDED"
    elif benefit < 4.0 or overall < 4.0:
        verdict = "REJECTED"
    else:
        verdict = "CONDITIONAL"

    return {
        "compatibility": round(compat, 1),
        "benefit": round(benefit, 1),
        "complexity": round(complexity, 1),
        "safety": round(safety, 1),
        "overall": round(overall, 1),
        "verdict": verdict,
    }


def _extract_adoptable_features(analysis_text: str) -> list[dict]:
    """Parse PART 2 of analysis: extract features Dela could build from scratch."""
    # Find the PART 2 section
    part2_match = re.search(
        r"PART\s*2.*?ADOPTABLE\s*IDEAS?(.*?)(?:$)",
        analysis_text, re.IGNORECASE | re.DOTALL
    )
    if not part2_match:
        # Try alternative patterns
        part2_match = re.search(
            r"(?:adoptable|from scratch|clean.room)(?:.*?\n)+(.*?)(?:$)",
            analysis_text, re.IGNORECASE | re.DOTALL
        )
    if not part2_match:
        return []

    section = part2_match.group(1) if part2_match else analysis_text

    # Parse feature entries: each line or bullet describing a feature
    features = []
    # Look for patterns like "- Feature name: description" or "Feature name: seam: ..."
    lines = [l.strip(" *-•\t") for l in section.split("\n") if l.strip()]

    for line in lines:
        if len(line) < 10:
            continue
        # Skip lines that are headers, scores, or verdicts
        if any(kw in line.lower()[:15] for kw in ["score", "verdict", "part", "compat"]):
            continue

        feature = {
            "raw": line[:300],
        }

        # Extract complexity keyword
        for level in ["easy", "medium", "hard"]:
            if level in line.lower():
                feature["complexity"] = level
                break

        # Extract seam
        for seam in ["tool", "agent", "skill", "channel", "heartbeat check", "workflow", "none"]:
            if seam in line.lower():
                feature["seam"] = seam
                break

        if "complexity" in feature or "seam" in feature:
            features.append(feature)

    return features[:8]  # Cap at 8 to avoid noise


def _extract_score(text: str, dimension: str, default: float) -> float:
    """Try to extract a score from analysis text. Handles multiple formats."""
    # Map dimension names to possible aliases in model output
    aliases = {
        "compatibility": [r"compat", r"compatibility", r"fit"],
        "benefit": [r"benefit", r"value", r"usefulness"],
        "complexity": [r"complexity", r"effort", r"ease", r"difficulty"],
        "safety": [r"safety", r"security", r"risk"],
    }
    names = aliases.get(dimension.lower(), [dimension])

    for name in names:
        # Match "Name: X/10" or "Name=X/10" or "Name X/10"
        pattern = rf"{name}\s*[:=]\s*(\d+\.?\d*)\s*/?\s*10"
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return min(10.0, max(0.0, float(m.group(1))))
            except ValueError:
                pass

    return default


def _build_analysis_task(repo_url: str, readme_snippet: str) -> str:
    """Construct analysis task — direct integration + feature inspiration."""
    return f"""Analyze this external repo for Dela.

**Repo:** {repo_url}

**README (already fetched; DO NOT call tools):**

{readme_snippet}

Start with: Scores: Compat=X/10, Benefit=X/10, Complexity=X/10, Safety=X/10

PART 1 — DIRECT INTEGRATION: What is this repo? Tech stack/license? Does Dela already do this? Blocker? Verdict: RECOMMENDED/REJECTED/CONDITIONAL. One sentence why.

PART 2 — ADOPTABLE IDEAS (clean-room, from scratch): For each feature Dela lacks, output: "FEATURE: name | SEAM: tool/agent/skill/channel/check/workflow | COMPLEXITY: easy/medium/hard | APPROACH: one sentence". Skip features Dela already has."""


@register(
    name="analyze_external_repo",
    description=(
        "Analyze an external GitHub repository for Dela. Produces a two-part report: "
        "(1) Direct integration analysis — should Dela adopt this code? Scores fit, "
        "flags license/architecture blockers, gives a verdict. "
        "(2) Adoptable ideas — features Dela could build from scratch in its own style, "
        "mapped to the right seam (tool/agent/skill/channel/check/workflow). "
        "Use this when a user provides a repo URL and wants to know what's worth adopting."
    ),
    parameters={
        "type": "object",
        "properties": {
            "repo_url": {
                "type": "string",
                "description": (
                    "The GitHub repository URL to analyze. "
                    "E.g. 'https://github.com/owner/repo'"
                ),
            },
        },
        "required": ["repo_url"],
    },
)
def analyze_external_repo(args: dict) -> str:
    repo_url = args["repo_url"].strip()

    # Validate URL
    if "github.com" not in repo_url:
        return f"Not a GitHub URL: {repo_url}. Please provide a full GitHub repository URL."

    # Derive owner/repo name
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)", repo_url.rstrip("/").replace(".git", ""))
    if not m:
        return f"Could not parse GitHub URL: {repo_url}. Use the format 'https://github.com/owner/repo'."

    owner, repo_name = m.group(1), m.group(2)

    # Derive raw URLs and fetch README for context and scoring
    urls = _github_raw_urls(repo_url)
    readme = _fetch_raw(urls["readme"])
    if readme.startswith(("HTTP", "URL error", "Fetch error")):
        readme = _fetch_raw(urls["readme_alt"])
    readme_ok = not readme.startswith(("HTTP", "URL error", "Fetch error"))

    if not readme_ok:
        return f"Could not fetch README from {repo_url}. Error: {readme}"

    # Truncate README aggressively — system prompt is already ~9K chars
    readme_snippet = readme[:2000]
    if len(readme) > 2000:
        readme_snippet += "\n...[truncated]"

    # Dispatch system_expert (told not to call tools — read from pre-fetched content)
    task = _build_analysis_task(repo_url, readme_snippet)

    analysis = _dispatch_system_expert(task)
    if analysis.startswith("ERROR:"):
        # Fall back to heuristic scoring without LLM analysis
        features_summary = readme[:1500] if readme_ok else ""
        scores = _audit_repo_fit(f"{owner}/{repo_name}", features_summary, analysis)
        return f"""# External Repo Analysis Report

**Repo:** {repo_url}
**Analyzed by:** Dela system_expert (heuristic fallback — LLM dispatch failed)
**Verdict:** {scores['verdict']}

## Scores

| Dimension | Score |
|---|---|
| Compatibility | {scores['compatibility']}/10 |
| Benefit | {scores['benefit']}/10 |
| Complexity | {scores['complexity']}/10 (higher = easier) |
| Safety | {scores['safety']}/10 |
| **Overall** | **{scores['overall']}/10** |

---

## System Expert Analysis

{analysis}
"""

    # Score the fit for direct integration
    features_summary = readme[:1500]
    scores = _audit_repo_fit(f"{owner}/{repo_name}", features_summary, analysis)
    adoptable = _extract_adoptable_features(analysis)

    # Build adoptable ideas table
    adoptable_section = ""
    if adoptable:
        rows = []
        for i, f in enumerate(adoptable, 1):
            seam = f.get("seam", "?")
            complexity = f.get("complexity", "?")
            desc = f.get("raw", "")[:120]
            rows.append(f"| {i} | {seam} | {complexity} | {desc} |")
        adoptable_section = f"""## Adoptable Ideas ({len(adoptable)} features Dela could build from scratch)

| # | Seam | Complexity | Description |
|---|---|---|---|
{chr(10).join(rows)}

*These features would be implemented clean-room using Dela's own patterns — no external code adopted.*
"""

    # Build report
    report = f"""# External Repo Analysis Report

**Repo:** {repo_url}
**Analyzed by:** Dela system_expert

## Direct Integration Verdict: **{scores['verdict']}**

| Dimension | Score |
|---|---|
| Compatibility | {scores['compatibility']}/10 |
| Benefit | {scores['benefit']}/10 |
| Complexity | {scores['complexity']}/10 (higher = easier) |
| Safety | {scores['safety']}/10 |
| **Overall** | **{scores['overall']}/10** |

---

## System Expert Analysis

{analysis}

---

{adoptable_section}"""

    return report
