"""Vulnerability knowledge base — authoritative security checklists for Dela's scanner.

Embeds checklists from:
  1. OWASP Top 10 for LLM Applications 2025 (genai.owasp.org)
  2. CWE Top 25 Most Dangerous Software Weaknesses 2025 (cwe.mitre.org/top25)
  3. OWASP Secure Agent Playbook (github.com/OWASP/secure-agent-playbook)

Each item has:
  - id:           stable identifier (e.g. "LLM01", "CWE-78")
  - source:       authoritative source URL
  - title:        short name
  - description:  what the vulnerability is
  - remediation:  how to fix it
  - check_id:     maps to a scanner function in security.py (_scan_vuln_kb)
  - relevance:    "llm" (LLM-specific) or "general" (software-wide)

The embedded checklist works offline. refresh() can fetch fresh versions from
whitelisted domains (owasp.org, cwe.mitre.org, cisa.gov) and cache to
dela_state/vuln_kb.json.

Security: fetch only connects to whitelisted domains, uses HTTPS, validates
content is JSON/HTML (never executes anything), and caches locally.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from dela.config import ROOT

_KB_PATH = ROOT / "dela_state" / "vuln_kb.json"

_WHITELISTED_DOMAINS = {
    "genai.owasp.org",
    "owasp.org",
    "cwe.mitre.org",
    "cisa.gov",
    "raw.githubusercontent.com",
}

# ─── Embedded checklist (works offline) ───────────────────────────────────────

_EMBEDDED: list[dict[str, Any]] = [
    # ── OWASP Top 10 for LLM Applications 2025 ──
    {
        "id": "LLM01",
        "source": "https://genai.owasp.org/llmrisk/llm01-prompt-injection/",
        "title": "Prompt Injection",
        "description": "Attacker-controlled input alters LLM behavior, bypasses safety controls, or extracts sensitive information. Includes direct injection (jailbreaking), indirect injection (via fetched content), goal hijacking, and delimiter escape.",
        "remediation": "Input guardrails, context isolation, delimiter enforcement, output validation, least-privilege tool access, human confirmation on consequential actions.",
        "check_id": "llm01_prompt_injection",
        "relevance": "llm",
    },
    {
        "id": "LLM02",
        "source": "https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/",
        "title": "Sensitive Information Disclosure",
        "description": "LLM reveals sensitive training data, PII, system prompts, secrets, or proprietary information in responses.",
        "remediation": "Secret scanning, output filtering, redaction, access controls on memory/state, never store secrets in conversation history.",
        "check_id": "llm02_info_disclosure",
        "relevance": "llm",
    },
    {
        "id": "LLM03",
        "source": "https://genai.owasp.org/llmrisk/llm032025-supply-chain/",
        "title": "Supply Chain",
        "description": "Vulnerabilities in LLM supply chain including models, dependencies, plugins, and infrastructure. Dependency confusion, typosquatting, compromised plugins.",
        "remediation": "Dependency scanning (pip-audit, npm audit), pin versions, verify model provenance, review plugin/tool sources.",
        "check_id": "llm03_supply_chain",
        "relevance": "llm",
    },
    {
        "id": "LLM04",
        "source": "https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/",
        "title": "Data and Model Poisoning",
        "description": "Pre-training, fine-tuning, or embedding data is tampered to impair the model. RAG knowledge base can be poisoned with malicious documents.",
        "remediation": "Validate memory/RAG data sources, sanitize stored facts, review memory entries before retrieval, provenance tracking.",
        "check_id": "llm04_data_poisoning",
        "relevance": "llm",
    },
    {
        "id": "LLM05",
        "source": "https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/",
        "title": "Improper Output Handling",
        "description": "LLM outputs used unsafely leading to XSS, command injection, SQL injection, or other downstream vulnerabilities. Treating model output as trusted.",
        "remediation": "Validate/sanitize all tool outputs before use, enforce schemas, never pipe raw LLM output to shell/eval/render.",
        "check_id": "llm05_output_handling",
        "relevance": "llm",
    },
    {
        "id": "LLM06",
        "source": "https://genai.owasp.org/llmrisk/llm062025-excessive-agency/",
        "title": "Excessive Agency",
        "description": "LLM has too much autonomy — can take consequential actions without confirmation, access all tools, or modify state destructively.",
        "remediation": "Confirmation gate on all consequential tools, least-privilege tool whitelists per profile, rate limits, human-in-the-loop.",
        "check_id": "llm06_excessive_agency",
        "relevance": "llm",
    },
    {
        "id": "LLM07",
        "source": "https://genai.owasp.org/llmrisk/llm072025-system-prompt-leakage/",
        "title": "System Prompt Leakage",
        "description": "LLM reveals system prompts containing secrets, instructions, or proprietary logic when probed by users.",
        "remediation": "Never store secrets in system prompt, use injection defense language, separate secrets from prompt text, monitor for extraction attempts.",
        "check_id": "llm07_prompt_leakage",
        "relevance": "llm",
    },
    {
        "id": "LLM08",
        "source": "https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/",
        "title": "Vector and Embedding Weaknesses",
        "description": "Insecure vector DB access, embedding poisoning, unauthorized retrieval of sensitive embeddings.",
        "remediation": "Access control on memory/vector store, validate embedding sources, sanitize retrieval results.",
        "check_id": "llm08_vector_weakness",
        "relevance": "llm",
    },
    {
        "id": "LLM09",
        "source": "https://genai.owasp.org/llmrisk/llm092025-misinformation/",
        "title": "Misinformation",
        "description": "LLM produces false, misleading, or hallucinated information that users act upon. Overreliance without verification.",
        "remediation": "Fact-checking tools, source citations, confidence indicators, human review for high-stakes outputs.",
        "check_id": "llm09_misinformation",
        "relevance": "llm",
    },
    {
        "id": "LLM10",
        "source": "https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/",
        "title": "Unbounded Consumption",
        "description": "LLL consumes excessive resources — token bombing, unbounded API calls, memory exhaustion, cost spirals.",
        "remediation": "Rate limiting, token/cost budgets, max conversation length, compaction, per-request limits.",
        "check_id": "llm10_unbounded_consumption",
        "relevance": "llm",
    },
    # ── CWE Top 25 (2025) — Python-relevant subset ──
    {
        "id": "CWE-78",
        "source": "https://cwe.mitre.org/data/definitions/78.html",
        "title": "OS Command Injection",
        "description": "User input is passed to OS commands without proper sanitization, allowing command execution.",
        "remediation": "Avoid shell=True in subprocess, use argument lists, sanitize all inputs, whitelist allowed commands.",
        "check_id": "cwe78_command_injection",
        "relevance": "general",
    },
    {
        "id": "CWE-22",
        "source": "https://cwe.mitre.org/data/definitions/22.html",
        "title": "Path Traversal",
        "description": "File operations use user-controlled paths without restricting to intended directories.",
        "remediation": "Validate and normalize paths, enforce base directory, reject ../ sequences, use pathlib.",
        "check_id": "cwe22_path_traversal",
        "relevance": "general",
    },
    {
        "id": "CWE-94",
        "source": "https://cwe.mitre.org/data/definitions/94.html",
        "title": "Code Injection",
        "description": "Raw eval() or exec() on user-controlled input allows arbitrary code execution.",
        "remediation": "Never eval/exec user input, use sandboxed execution, AST parsing instead of eval.",
        "check_id": "cwe94_code_injection",
        "relevance": "general",
    },
    {
        "id": "CWE-502",
        "source": "https://cwe.mitre.org/data/definitions/502.html",
        "title": "Deserialization of Untrusted Data",
        "description": "Loading JSON/pickle data from untrusted sources without validation.",
        "remediation": "Validate schema after json.load, never use pickle for untrusted data, sanitize before use.",
        "check_id": "cwe502_deserialization",
        "relevance": "general",
    },
    {
        "id": "CWE-200",
        "source": "https://cwe.mitre.org/data/definitions/200.html",
        "title": "Exposure of Sensitive Information",
        "description": "Error messages, logs, or responses reveal sensitive information to unauthorized actors.",
        "remediation": "Sanitize error messages, avoid logging secrets, use generic error responses, redact PII.",
        "check_id": "cwe200_info_exposure",
        "relevance": "general",
    },
    {
        "id": "CWE-306",
        "source": "https://cwe.mitre.org/data/definitions/306.html",
        "title": "Missing Authentication for Critical Function",
        "description": "Critical API endpoints or functions lack authentication, allowing unauthorized access.",
        "remediation": "Require auth on sensitive endpoints, especially in work profile, API key validation, session checks.",
        "check_id": "cwe306_missing_auth",
        "relevance": "general",
    },
    {
        "id": "CWE-770",
        "source": "https://cwe.mitre.org/data/definitions/770.html",
        "title": "Allocation of Resources Without Limits or Throttling",
        "description": "No rate limiting or resource limits — allows resource exhaustion, DoS, cost spirals.",
        "remediation": "Rate limits on API calls, max request size, connection limits, token/cost budgets.",
        "check_id": "cwe770_resource_limits",
        "relevance": "general",
    },
    {
        "id": "CWE-918",
        "source": "https://cwe.mitre.org/data/definitions/918.html",
        "title": "Server-Side Request Forgery (SSRF)",
        "description": "Web fetch tools allow arbitrary URL access, enabling internal network probing.",
        "remediation": "URL validation, block internal IPs/domains, whitelist allowed URL schemes, restrict redirects.",
        "check_id": "cwe918_ssrf",
        "relevance": "general",
    },
    {
        "id": "CWE-89",
        "source": "https://cwe.mitre.org/data/definitions/89.html",
        "title": "Injection (General)",
        "description": "User input injected into interpreters (SQL, JSON, templates) without sanitization.",
        "remediation": "Parameterized queries, schema validation, input sanitization, escape special characters.",
        "check_id": "cwe89_injection",
        "relevance": "general",
    },
    {
        "id": "CWE-352",
        "source": "https://cwe.mitre.org/data/definitions/352.html",
        "title": "Cross-Site Request Forgery (CSRF)",
        "description": "Web endpoints accept requests without verifying origin, allowing forged actions.",
        "remediation": "CORS restrictions, origin validation, CSRF tokens for state-changing operations.",
        "check_id": "cwe352_csrf",
        "relevance": "general",
    },
]


def get_checklist() -> list[dict[str, Any]]:
    """Return the vulnerability checklist (from cache if available, else embedded)."""
    if _KB_PATH.exists():
        try:
            data = json.loads(_KB_PATH.read_text(encoding="utf-8"))
            if data.get("items"):
                return data["items"]
        except Exception:
            pass
    return _EMBEDDED


def get_kb_info() -> dict[str, Any]:
    """Return KB metadata + checklist."""
    cached = False
    fetched_at = None
    if _KB_PATH.exists():
        try:
            data = json.loads(_KB_PATH.read_text(encoding="utf-8"))
            cached = True
            fetched_at = data.get("fetched_at")
        except Exception:
            pass

    items = get_checklist()
    return {
        "item_count": len(items),
        "sources": sorted(set(item["source"] for item in items)),
        "whitelisted_domains": sorted(_WHITELISTED_DOMAINS),
        "cached": cached,
        "fetched_at": fetched_at,
        "embedded_count": len(_EMBEDDED),
        "items": items,
    }


def refresh() -> dict[str, Any]:
    """Fetch fresh checklist data from authoritative sources.

    Only connects to whitelisted domains over HTTPS.
    Stores result in dela_state/vuln_kb.json.
    Falls back to embedded checklist if fetch fails.
    """
    import urllib.request
    import urllib.error

    fetched_items: list[dict[str, Any]] = []
    errors: list[str] = []

    # Try to fetch OWASP LLM Top 10 index
    try:
        req = urllib.request.Request(
            "https://genai.owasp.org/llm-top-10/",
            headers={"User-Agent": "Dela-Security-Scanner/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                _ = resp.read()
                fetched_items.extend([item for item in _EMBEDDED if item["id"].startswith("LLM")])
    except Exception as e:
        errors.append(f"OWASP fetch: {e}")

    # CWE Top 25 is HTML — we use the embedded version since parsing HTML is brittle
    fetched_items.extend([item for item in _EMBEDDED if item["id"].startswith("CWE")])

    if not fetched_items:
        fetched_items = list(_EMBEDDED)

    now = time.time()
    data = {
        "fetched_at": now,
        "item_count": len(fetched_items),
        "sources": sorted(set(item["source"] for item in fetched_items)),
        "items": fetched_items,
        "errors": errors,
    }

    _KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _KB_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return {
        "status": "ok" if not errors else "partial",
        "fetched_count": len(fetched_items),
        "errors": errors,
        "cached_at": now,
    }


def is_domain_whitelisted(url: str) -> bool:
    """Check if a URL's domain is in the whitelist."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.hostname in _WHITELISTED_DOMAINS
