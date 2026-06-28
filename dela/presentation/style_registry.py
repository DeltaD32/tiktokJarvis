"""Style registry — index of all cloned PPT styles.

Each style is a folder under dela_state/styles/<slug>/ containing:
  ├── style.json      Full machine-readable profile (theme, fonts, txStyles, layouts)
  ├── brand-guide.md  Human-readable guide (agents read this for color/font rules)
  ├── source.pptx     Copy of the original file (template base for generation)
  └── title-bg.jpeg   Extracted title background (if present)

The registry index (registry.json) holds summary metadata for quick listing.
Styles are resolved by slug, name, or fuzzy match.

This module is the read side — clone_style.py handles the write side.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_STYLES_ROOT = Path(__file__).resolve().parent.parent.parent / "dela_state" / "styles"
_REGISTRY = _STYLES_ROOT / "registry.json"


def style_dir(slug: str) -> Path:
    """Return the directory path for a style by slug."""
    return _STYLES_ROOT / slug


def registry_path() -> Path:
    return _REGISTRY


def _load_registry() -> dict[str, Any]:
    if not _REGISTRY.exists():
        return {"version": 1, "styles": {}}
    try:
        return json.loads(_REGISTRY.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "styles": {}}


def _save_registry(data: dict[str, Any]) -> None:
    _STYLES_ROOT.mkdir(parents=True, exist_ok=True)
    _REGISTRY.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def list_styles() -> list[dict[str, Any]]:
    """Return all registered styles as a list of summary dicts."""
    reg = _load_registry()
    return list(reg.get("styles", {}).values())


def get_style(slug: str) -> dict[str, Any] | None:
    """Get a single style's registry entry by slug (exact match)."""
    reg = _load_registry()
    return reg.get("styles", {}).get(slug)


def resolve_style(query: str) -> dict[str, Any] | None:
    """Resolve a style by slug, name, or fuzzy match.

    Accepts: slug, style name, "default", empty string, or partial match.
    Returns the registry entry or None if no match.
    """
    if not query or query.lower() in ("default", "none"):
        # Return the first style if any exist (or None).
        styles = list_styles()
        return styles[0] if styles else None

    query_lower = query.lower().strip()

    # Exact slug match.
    entry = get_style(query_lower)
    if entry:
        return entry

    # Exact name match (case-insensitive).
    reg = _load_registry()
    for slug, entry in reg.get("styles", {}).items():
        if entry.get("name", "").lower() == query_lower:
            return entry

    # Fuzzy: slug or name contains the query.
    for slug, entry in reg.get("styles", {}).items():
        name = entry.get("name", "").lower()
        if query_lower in slug or query_lower in name:
            return entry

    return None


def style_profile_path(slug: str) -> Path:
    """Return the path to a style's style.json."""
    return style_dir(slug) / "style.json"


def style_guide_path(slug: str) -> Path:
    """Return the path to a style's brand-guide.md."""
    return style_dir(slug) / "brand-guide.md"


def style_template_path(slug: str) -> Path:
    """Return the path to a style's source.pptx (template base for generation)."""
    return style_dir(slug) / "source.pptx"


def load_style_profile(slug: str) -> dict[str, Any] | None:
    """Load the full style.json for a style."""
    path = style_profile_path(slug)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def upsert_style(entry: dict[str, Any]) -> None:
    """Add or update a style in the registry (called by clone_style.py)."""
    reg = _load_registry()
    slug = entry["slug"]
    reg.setdefault("styles", {})[slug] = entry
    _save_registry(reg)


def styles_summary() -> str:
    """Human-readable one-line-per-style summary for the model."""
    styles = list_styles()
    if not styles:
        return "No styles registered. Use clone_pptx_style to add one from a .pptx file."
    lines = []
    for s in styles:
        typo = s.get("typography_summary", {})
        color = typo.get("primary_color", "?")
        font = typo.get("primary_font", "?")
        name = s.get("name", s["slug"])
        lines.append(f"- {s['slug']} ({name}): {color}, {font}")
    return "\n".join(lines)