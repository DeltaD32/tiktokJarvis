"""Profile system — security postures for different contexts.

Two profiles:
  - PERSONAL: less restrictive but still secure. Localhost-only, full tool
    access, standard confirmation gate. For solo use on your own machine.
  - WORK: enterprise-grade. Restricted tools, extended confirmation gate,
    WIZ integration hook, verbose audit, strict injection defense, approved
    origins only. For use in corporate environments.

Switching profiles changes the security posture. The profile is stored in
.env as DELA_PROFILE and loaded at startup. It can be switched via the
Settings panel (requires restart).

Each profile defines:
  - cors_origins: list of allowed origins (or ["localhost"])
  - bind_host: what host uvicorn binds to
  - tools_blocked: tools that are NOT available in this profile
  - tools_extra_confirm: tools that require confirmation in this profile
    (but not in personal)
  - injection_level: "standard" or "maximum"
  - audit_level: "normal" or "verbose"
  - wiz_enabled: whether WIZ integration hooks are active
  - allow_web_fetch: whether fetch_url is allowed
  - allow_code_exec: whether run_code is allowed
  - description: human-readable summary
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from dela.config import _optional


@dataclass
class Profile:
    name: str
    description: str
    cors_origins: list[str]
    bind_host: str
    tools_blocked: set[str] = field(default_factory=set)
    tools_extra_confirm: set[str] = field(default_factory=set)
    injection_level: str = "standard"
    audit_level: str = "normal"
    wiz_enabled: bool = False
    allow_web_fetch: bool = True
    allow_code_exec: bool = True
    max_conversation_chars: int = 100_000

    def is_tool_allowed(self, tool_name: str) -> bool:
        return tool_name not in self.tools_blocked

    def requires_confirmation(self, tool_name: str, base_confirm: bool) -> bool:
        return base_confirm or tool_name in self.tools_extra_confirm

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "cors_origins": self.cors_origins,
            "bind_host": self.bind_host,
            "tools_blocked": sorted(self.tools_blocked),
            "tools_extra_confirm": sorted(self.tools_extra_confirm),
            "injection_level": self.injection_level,
            "audit_level": self.audit_level,
            "wiz_enabled": self.wiz_enabled,
            "allow_web_fetch": self.allow_web_fetch,
            "allow_code_exec": self.allow_code_exec,
            "max_conversation_chars": self.max_conversation_chars,
        }


PROFILES: dict[str, Profile] = {
    "personal": Profile(
        name="personal",
        description="Full access, standard security. Localhost-only, all tools available, standard confirmation gate.",
        cors_origins=["*"],  # local dev — vite proxy handles it
        bind_host="127.0.0.1",
        tools_blocked=set(),
        tools_extra_confirm=set(),
        injection_level="standard",
        audit_level="normal",
        wiz_enabled=False,
        allow_web_fetch=True,
        allow_code_exec=True,
    ),
    "work": Profile(
        name="work",
        description="Enterprise-grade. Restricted tools, extended confirmation, WIZ integration, verbose audit, strict injection defense.",
        cors_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        bind_host="127.0.0.1",
        tools_blocked={
            # Block tools that exfiltrate data in work profile
            "fetch_url",       # no uncontrolled web fetch
        },
        tools_extra_confirm={
            # Extra confirmation for tools that are auto in personal
            "run_security_scan",  # scans filesystem — confirm in work mode
            "dispatch_subagent",  # spawning agents — confirm in work mode
            "dispatch_system_expert",  # can read/write code — confirm
            "create_project",    # already confirmed, keep
            "create_blackboard", # already confirmed, keep
        },
        injection_level="maximum",
        audit_level="verbose",
        wiz_enabled=True,
        allow_web_fetch=False,
        allow_code_exec=True,  # still allow but with extra logging
        max_conversation_chars=50_000,  # shorter context in work mode
    ),
}


def get_current_profile_name() -> str:
    return _optional("DELA_PROFILE", "personal").lower()


def get_current_profile() -> Profile:
    name = get_current_profile_name()
    return PROFILES.get(name, PROFILES["personal"])


def list_profiles() -> list[dict[str, Any]]:
    return [p.to_dict() for p in PROFILES.values()]


def set_profile(name: str) -> bool:
    """Write the profile to .env. Returns True if successful."""
    if name not in PROFILES:
        return False
    from pathlib import Path
    from dela.config import ROOT
    env_path = ROOT / ".env"
    if not env_path.exists():
        return False
    lines = env_path.read_text(encoding="utf-8").splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith("DELA_PROFILE="):
            new_lines.append(f"DELA_PROFILE={name}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"DELA_PROFILE={name}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return True
