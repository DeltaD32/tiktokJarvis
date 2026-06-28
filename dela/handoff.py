"""Handoff protocol — structured task envelopes for inter-agent communication.

The HANDOFF/RESPONSE pattern ensures that when one agent delegates to another:
  - The task is fully specified (no thin delegations)
  - The context is traceable (handoff_id, context echo)
  - The output is worker-executable (not prose)
  - Prior decisions are enforced (cross-task consistency)

Adapted from opencode-galaxy's HANDOFF v1 / RESPONSE v1, simplified for Dela:
JSON dicts instead of text envelopes, integrated with the blackboard.

[HANDOFF] — orchestrator → specialist (one complete message):
  {
    "handoff_id": "unique-id",
    "blackboard_id": "bb-...",
    "project_id": "proj-...",
    "task": "clear description of what to do",
    "scope": {"files_to_inspect": [], "files_to_change": [], "out_of_scope": []},
    "prior_decisions": [{"decision": "...", "rationale": "..."}],
    "acceptance_criteria": ["criterion 1", "criterion 2"],
    "response_format": "response"  # always "response"
  }

[RESPONSE] — specialist → orchestrator (via blackboard section):
  {
    "handoff_id": "must match",
    "agent": "specialist-name",
    "context_echo": {"project_id": "...", "blackboard_id": "..."},
    "summary": "what was found / decided",
    "proposed_changes": "exact code/steps (not prose)",
    "validation": "how to verify the changes work",
    "blockers": ["any blockers encountered"],
    "memory_to_persist": {"worked": [], "avoided": [], "patterns": []}
  }
"""

from __future__ import annotations

import uuid
from typing import Any


def create_handoff(
    blackboard_id: str,
    project_id: str,
    task: str,
    scope: dict[str, list[str]] | None = None,
    prior_decisions: list[dict[str, str]] | None = None,
    acceptance_criteria: list[str] | None = None,
) -> dict[str, Any]:
    """Create a structured handoff envelope for delegating to a specialist."""
    return {
        "handoff_id": str(uuid.uuid4())[:8],
        "blackboard_id": blackboard_id,
        "project_id": project_id,
        "task": task,
        "scope": scope or {"files_to_inspect": [], "files_to_change": [], "out_of_scope": []},
        "prior_decisions": prior_decisions or [],
        "acceptance_criteria": acceptance_criteria or [],
        "response_format": "response",
    }


def create_response(
    handoff_id: str,
    agent: str,
    blackboard_id: str,
    project_id: str,
    summary: str,
    proposed_changes: str,
    validation: str = "",
    blockers: list[str] | None = None,
    memory_to_persist: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Create a structured response envelope from a specialist."""
    return {
        "handoff_id": handoff_id,
        "agent": agent,
        "context_echo": {"project_id": project_id, "blackboard_id": blackboard_id},
        "summary": summary,
        "proposed_changes": proposed_changes,
        "validation": validation,
        "blockers": blockers or [],
        "memory_to_persist": memory_to_persist or {"worked": [], "avoided": [], "patterns": []},
    }


def validate_handoff(handoff: dict[str, Any]) -> list[str]:
    """Validate a handoff envelope. Returns a list of errors (empty = valid)."""
    errors = []
    required = ["handoff_id", "blackboard_id", "task", "response_format"]
    for field in required:
        if field not in handoff:
            errors.append(f"Missing required field: {field}")
    if handoff.get("response_format") != "response":
        errors.append("response_format must be 'response'")
    if not handoff.get("task", "").strip():
        errors.append("task must not be empty")
    return errors


def validate_response(response: dict[str, Any], expected_handoff_id: str) -> list[str]:
    """Validate a response envelope. Returns a list of errors (empty = valid)."""
    errors = []
    if response.get("handoff_id") != expected_handoff_id:
        errors.append(f"handoff_id mismatch: expected {expected_handoff_id}, got {response.get('handoff_id')}")
    if not response.get("agent"):
        errors.append("Missing agent name")
    if not response.get("summary"):
        errors.append("Missing summary")
    if not response.get("proposed_changes"):
        errors.append("Missing proposed_changes (must be exact code/steps, not prose)")
    return errors


def handoff_to_prompt(handoff: dict[str, Any]) -> str:
    """Render a handoff as a text prompt for the specialist sub-agent."""
    lines = [
        f"[HANDOFF] Task: {handoff['task']}",
        f"Blackboard: {handoff['blackboard_id']}",
        f"Project: {handoff.get('project_id', '—')}",
        f"Handoff ID: {handoff['handoff_id']}",
        "",
    ]
    if handoff.get("scope", {}).get("files_to_inspect"):
        lines.append(f"Files to inspect: {', '.join(handoff['scope']['files_to_inspect'])}")
    if handoff.get("scope", {}).get("files_to_change"):
        lines.append(f"Files to change: {', '.join(handoff['scope']['files_to_change'])}")
    if handoff.get("prior_decisions"):
        lines.append("Prior decisions (must respect):")
        for d in handoff["prior_decisions"]:
            lines.append(f"  - {d.get('decision', '?')}: {d.get('rationale', '?')}")
    if handoff.get("acceptance_criteria"):
        lines.append("Acceptance criteria:")
        for c in handoff["acceptance_criteria"]:
            lines.append(f"  - {c}")
    lines.append("")
    lines.append("Write your analysis and proposed changes to the blackboard using the appropriate section.")
    lines.append(f"Respond with a [RESPONSE] envelope referencing handoff_id {handoff['handoff_id']}.")
    return "\n".join(lines)


def response_from_text(text: str, agent: str, blackboard_id: str, project_id: str, handoff_id: str) -> dict[str, Any]:
    """Create a response from a sub-agent's text output (best-effort parsing)."""
    return create_response(
        handoff_id=handoff_id,
        agent=agent,
        blackboard_id=blackboard_id,
        project_id=project_id,
        summary=text[:500],
        proposed_changes=text,
    )