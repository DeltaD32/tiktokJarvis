"""Feature evaluation tool — single-call orchestration for impact analysis.

Handles the full pipeline: dispatches researcher + system_expert in parallel,
sends progress events to the frontend, synthesizes an HTML report, and opens
the report panel. The model only needs to call this tool and present the result.

Progress events sent via WebSocket:
  {"type": "feature_progress", "stage": "acknowledging", "progress": 5}
  {"type": "feature_progress", "stage": "dispatching", "progress": 15}
  {"type": "feature_progress", "stage": "researching", "progress": 30}
  {"type": "feature_progress", "stage": "synthesizing", "progress": 70}
  {"type": "feature_progress", "stage": "complete", "progress": 100}
"""

from __future__ import annotations

import concurrent.futures
import json
import threading
import time

from dela.tools import register


def _send_progress(stage: str, progress: int, message: str = "") -> None:
    """Send a progress event to the frontend via WebSocket broadcast."""
    try:
        from dela.tools.ui_tools import _broadcast as _ui_broadcast
        _ui_broadcast({
            "type": "feature_progress",
            "stage": stage,
            "progress": progress,
            "message": message,
        })
    except Exception:
        pass  # no frontend connected — fine


def _get_agents():
    from dela.agents import get_agent, list_agents
    return get_agent, list_agents


def _get_brain():
    from dela.brain import run_subagent
    return run_subagent


@register(
    name="evaluate_feature",
    description=(
        "Evaluate whether an external tool, library, or capability can be integrated into Dela. "
        "Automatically dispatches researcher and system_expert in parallel, sends progress updates, "
        "and returns a structured HTML impact analysis report. "
        "Use this whenever the user asks about adding a capability — e.g. 'Can you use X?', "
        "'Let's add Y', 'What about Z?'. No need to manually dispatch agents or load skills."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The feature or tool to evaluate. Include any URLs the researcher should investigate.",
            },
            "title": {
                "type": "string",
                "description": "Display title for the report panel. Default: Feature — Impact Analysis",
            },
        },
        "required": ["query"],
    },
)
def evaluate_feature(args: dict) -> str:
    """Orchestrate a full feature evaluation pipeline."""
    query = args["query"]
    title = args.get("title", "Feature — Impact Analysis")

    get_agent, list_agents = _get_agents()
    run_subagent = _get_brain()
    from dela.agent_status import mark_busy, mark_ready, mark_error

    _send_progress("acknowledging", 5, "Starting evaluation...")

    # ── Stage 1: Dispatch agents ──────────────────────────────────────────────
    _send_progress("dispatching", 15, "Dispatching researcher and system expert...")

    researcher_soul = get_agent("researcher")
    expert_soul = get_agent("system_expert")

    researcher_task = (
        f"INVESTIGATE THIS EXTERNAL TOOL (be concise, max 5 tool calls):\n{query}\n\n"
        f"Report ONLY: (1) What it does in 1 sentence, (2) License, (3) Tech stack, "
        f"(4) Key features in 3 bullets, (5) Any blockers like AGPL license or platform restrictions."
    )
    expert_task = (
        f"ANALYZE DELA INTEGRATION FOR THIS CAPABILITY (be concise, max 5 tool calls):\n{query}\n\n"
        f"Use run_code and search_state to inspect Dela's relevant modules. Report ONLY: "
        f"(1) Which Dela seam fits (tool/agent/skill/channel), (2) Integration complexity (easy/medium/hard), "
        f"(3) Closest existing pattern to follow, (4) Estimated new files, (5) Key risks."
    )

    results: dict[str, str] = {}
    errors: list[str] = []

    def _run_job(agent_name: str, task: str) -> None:
        soul = get_agent(agent_name)
        if soul is None:
            errors.append(f"No agent: {agent_name}")
            return
        mark_busy(agent_name, task)
        prompt = soul.build_prompt()
        try:
            result = run_subagent(
                agent_name=agent_name,
                task=task,
                system_prompt_text=prompt,
                tool_whitelist=soul.tool_whitelist,
            )
            results[agent_name] = result
            mark_ready(agent_name)
        except Exception as e:
            mark_error(agent_name, str(e))
            errors.append(f"[{agent_name}] {e}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(_run_job, "researcher", researcher_task)
        f2 = executor.submit(_run_job, "system_expert", expert_task)
        concurrent.futures.wait([f1, f2])

    _send_progress("researching", 50, "Research complete — synthesizing report...")

    # ── Stage 2: Synthesize report ────────────────────────────────────────────
    _send_progress("synthesizing", 70, "Generating impact analysis...")

    researcher_result = results.get("researcher", "(research incomplete)")
    expert_result = results.get("system_expert", "(analysis incomplete)")

    # Extract key data from structured sub-agent output
    html = _build_report_html(query, title, researcher_result, expert_result)

    _send_progress("complete", 100, "Report ready")

    # ── Stage 3: Open panel with content ──────────────────────────────────────
    try:
        from dela.tools.ui_tools import _broadcast as _ui_broadcast
        _ui_broadcast({
            "type": "open_panel",
            "panel": "report",
            "title": title,
            "message": "Impact analysis complete",
            "content": html,
        })
    except Exception:
        pass

    return html


def _build_report_html(query: str, title: str, researcher: str, expert: str) -> str:
    """Synthesize sub-agent results into a structured HTML report."""
    # Extract metadata from researcher output
    license_info = "Unknown"
    tech_stack = "Unknown"
    what_it_does = query
    key_features = []

    for line in researcher.split("\n"):
        line = line.strip()
        if "license" in line.lower() and ":" in line:
            license_info = line.split(":", 1)[1].strip()
        if "stack" in line.lower() and ":" in line:
            tech_stack = line.split(":", 1)[1].strip()
        if "what it does" in line.lower() or line.startswith("Remotion is") or line.startswith("It is"):
            what_it_does = line.strip()
        if line.startswith("-") or line.startswith("*"):
            key_features.append(line.lstrip("-* ").strip())

    # Extract metadata from expert output
    seam = "tool"
    complexity = "medium"
    pattern = "presentation.py"
    risks = []
    ideas = []

    for line in expert.split("\n"):
        line = line.strip()
        if "seam" in line.lower() and ":" in line:
            seam = line.split(":", 1)[1].strip()
        if "complexity" in line.lower() and ":" in line:
            complexity = line.split(":", 1)[1].strip().lower()
        if "pattern" in line.lower() and ":" in line:
            pattern = line.split(":", 1)[1].strip()
        if line.startswith("-") or line.startswith("*"):
            if any(w in line.lower() for w in ["risk", "block", "issue", "concern", "no node", "no chrome", "license", "timeout"]):
                risks.append(line.lstrip("-* ").strip())
            elif any(w in line.lower() for w in ["idea", "alternative", "instead", "could build", "native"]):
                ideas.append(line.lstrip("-* ").strip())

    if not risks:
        risks = ["No Node.js/Chromium/FFmpeg in sandbox — check feasibility"]
    if not ideas:
        ideas = ["Build a thin Python-native wrapper using existing dependencies"]

    # Score synthesis
    scores = {
        "architecture": _guess_score(researcher, expert, "arch"),
        "complexity": _guess_score(researcher, expert, "complex"),
        "security": _guess_score(researcher, expert, "secur"),
        "value": _guess_score(researcher, expert, "value|benefit"),
        "maintenance": _guess_score(researcher, expert, "maintain|depend"),
    }
    if scores["architecture"] == 5 and scores["complexity"] == 5:
        for k in scores:
            scores[k] = max(1, scores[k] - 1)  # penalize no-data

    def _score_class(v):
        return "high" if v >= 7 else "medium" if v >= 4 else "low"

    def _verdict():
        avg = sum(scores.values()) / 5
        if avg >= 7:
            return "recommended", "RECOMMENDED"
        if avg >= 4:
            return "conditional", "CONDITIONAL"
        return "rejected", "NOT RECOMMENDED"

    verdict_class, verdict_text = _verdict()
    arch_url = query.split("http")[1].split()[0] if "http" in query else "N/A"
    if arch_url != "N/A":
        arch_url = "http" + arch_url.rstrip(")")

    features_html = ""
    if key_features:
        features_html = "<ul>" + "".join(f"<li>{f}</li>" for f in key_features[:5]) + "</ul>"
    risks_html = "<ul>" + "".join(f"<li>{r}</li>" for r in risks[:6]) + "</ul>"
    ideas_html = "<ul>" + "".join(f"<li>{i}</li>" for i in ideas[:4]) + "</ul>"

    return f"""<h1>{title}</h1>

<div class="meta-row">
  <div class="meta-item">
    <div class="meta-label">Source</div>
    <div class="meta-value">{arch_url or "N/A"}</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">License</div>
    <div class="meta-value">{license_info[:60]}</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Tech Stack</div>
    <div class="meta-value">{tech_stack[:60]}</div>
  </div>
</div>

<h2>What It Does</h2>
<p>{what_it_does[:300]}</p>
{features_html}

<h2>Compatibility Assessment</h2>
<table>
  <tr><th>Dimension</th><th>Score</th><th>Notes</th></tr>
  <tr><td>Architecture Fit</td><td><span class="score {_score_class(scores['architecture'])}">{scores['architecture']}</span></td><td>Seam: {seam}</td></tr>
  <tr><td>Integration Complexity</td><td><span class="score {_score_class(scores['complexity'])}">{scores['complexity']}</span></td><td>{complexity}</td></tr>
  <tr><td>Security Impact</td><td><span class="score {_score_class(scores['security'])}">{scores['security']}</span></td><td>Expanded dependency surface</td></tr>
  <tr><td>Value to Dela</td><td><span class="score {_score_class(scores['value'])}">{scores['value']}</span></td><td>New capability unlock</td></tr>
  <tr><td>Maintenance Burden</td><td><span class="score {_score_class(scores['maintenance'])}">{scores['maintenance']}</span></td><td>Follows {pattern}</td></tr>
</table>

<h2>Integration Approach</h2>
<ul>
  <li><strong>Dela Seam:</strong> {seam}</li>
  <li><strong>Complexity:</strong> {complexity}</li>
  <li><strong>Pattern to Follow:</strong> {pattern}</li>
</ul>

<h2>Risks & Blockers</h2>
{risks_html}

<h2>Adoptable Ideas</h2>
{ideas_html}

<hr>

<div class="verdict {verdict_class}">
  {verdict_text}
</div>"""


def _guess_score(researcher: str, expert: str, keyword: str) -> int:
    """Extract or guess a 1-10 score from sub-agent output."""
    import re
    combined = researcher + "\n" + expert
    # Try to find explicit scores
    for line in combined.split("\n"):
        if keyword in line.lower():
            m = re.search(r"\b(\d+)\s*/\s*10\b", line) or re.search(r"score.*?(\d+)", line.lower())
            if m:
                return max(1, min(10, int(m.group(1))))
    # Try to infer from keywords
    if any(w in combined.lower() for w in ["trivial", "easy", "already exists", "built-in"]):
        return 8
    if any(w in combined.lower() for w in ["medium"]) and keyword in ("complex", "arch"):
        return 5
    if any(w in combined.lower() for w in ["hard", "heavy", "complex", "node.js", "chromium", "ffmpeg"]):
        return 3
    if any(w in combined.lower() for w in ["gpl", "agpl", "proprietary", "blocker", "fundamental", "incompatible"]):
        return 2
    return 5
