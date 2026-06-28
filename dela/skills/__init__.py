"""Skills system — progressive capability guidance, loaded on demand.

A skill is a Markdown file in dela/skills/ with optional frontmatter and a body.
The body is guidance injected into the conversation when the skill is activated.
Skills are loaded progressively — only when the task needs them — so the system
prompt stays lean as the toolset grows.

Adding a skill = drop a .md file in dela/skills/. No code changes.
A `load_skill` tool lets the model pull in a skill mid-conversation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_SKILLS_DIR = Path(__file__).resolve().parent
_skills: dict[str, "Skill"] = {}
_active: set[str] = set()  # skills activated in the current session


@dataclass
class Skill:
    name: str
    description: str
    body: str
    tools: set[str] = field(default_factory=set)  # optional: tools this skill guides

    def guidance(self) -> str:
        """The text injected into the conversation when this skill is active."""
        return self.body


def _parse_skill(path: Path) -> Skill | None:
    """Parse a skill .md file: optional frontmatter + body."""
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Optional frontmatter (--- key: value ---)
    front = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    front[key.strip()] = val.strip()
            body = parts[2].strip()

    name = front.get("name", path.stem)
    description = front.get("description", "")
    tools_str = front.get("tools", "")
    tools = {t.strip() for t in tools_str.split(",") if t.strip()} if tools_str else set()

    return Skill(name=name, description=description, body=body, tools=tools)


def _load_all() -> None:
    """Discover and parse all .md files in the skills directory."""
    if _skills:
        return
    for path in sorted(_SKILLS_DIR.glob("*.md")):
        skill = _parse_skill(path)
        if skill is not None:
            _skills[skill.name] = skill


def list_skills() -> list[Skill]:
    _load_all()
    return list(_skills.values())


def get_skill(name: str) -> Skill | None:
    _load_all()
    # case-insensitive match
    return _skills.get(name) or _skills.get(name.lower())


def activate(name: str) -> Skill | None:
    """Activate a skill for the current session and return it."""
    skill = get_skill(name)
    if skill is not None:
        _active.add(skill.name)
    return skill


def active_skills() -> list[Skill]:
    """Return all skills activated in the current session."""
    _load_all()
    return [_skills[n] for n in _active if n in _skills]


def clear_active() -> None:
    """Deactivate all skills (e.g., on session restart)."""
    _active.clear()


def active_guidance_block() -> str:
    """Render the active skills' guidance as a block for the system prompt.

    Returns empty string if no skills are active (so the prompt stays clean).
    """
    skills = active_skills()
    if not skills:
        return ""
    parts = []
    for s in skills:
        parts.append(f"### Active Skill: {s.name}\n{s.guidance()}")
    return "\n\n" + "\n\n".join(parts)


def skill_descriptions() -> str:
    """One-line descriptions of all available skills, for the load_skill tool."""
    _load_all()
    if not _skills:
        return "No skills available."
    return "\n".join(f"- {s.name}: {s.description}" for s in _skills.values())


__all__ = [
    "Skill",
    "list_skills",
    "get_skill",
    "activate",
    "active_skills",
    "active_guidance_block",
    "skill_descriptions",
    "clear_active",
]