"""Skill tools — let the model load capability guidance on demand.

The model calls `load_skill` when a task would benefit from structured guidance.
The skill's body is injected into the conversation as a tool result, so the
model reads it and adjusts its approach. Active skills also get appended to
the system prompt for the remainder of the session.
"""

from __future__ import annotations

from dela.skills import activate, get_skill, list_skills, skill_descriptions
from dela.tools import register


@register(
    name="load_skill",
    description=(
        "Load a skill to get structured guidance for a specific type of task. "
        "Skills provide best-practice workflows that shape how you approach "
        "the task. Use this when a task is complex enough to benefit from a "
        "structured approach. Available skills: " + skill_descriptions()
    ),
    parameters={
        "type": "object",
        "properties": {
            "skill": {
                "type": "string",
                "description": "The name of the skill to load.",
            },
        },
        "required": ["skill"],
    },
)
def load_skill(args: dict) -> str:
    name = args["skill"]
    skill = activate(name)
    if skill is None:
        return (
            f"No skill named '{name}'. Available skills:\n{skill_descriptions()}"
        )
    return f"[Skill '{skill.name}' loaded. Follow this guidance:]\n\n{skill.guidance()}"


@register(
    name="list_skills",
    description="List all available skills with their descriptions. Use this when the user asks what you can do or what skills you have. Read-only.",
    parameters={"type": "object", "properties": {}},
)
def list_skills_tool(args: dict) -> str:
    skills = list_skills()
    if not skills:
        return "No skills available."
    lines = [f"- {s.name}: {s.description}" for s in skills]
    return f"Available skills:\n" + "\n".join(lines)