"""pptx_lib.constants — Style-driven color palette and free-area geometry.

Unlike the original BMW-hardcoded version, colors and fonts here are loaded
from the active style's style.json at runtime. This makes the library
style-agnostic: the same building blocks work with any cloned PPT style.

Call `load_style_constants(slug)` once before using any helper that references
COLOR_PRIMARY, COLOR_ACCENT, etc. Until then, sensible defaults are used.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pptx.dml.color import RGBColor
from pptx.util import Cm, Pt


# ── Defaults (used until load_style_constants is called) ─────────────────────
# These are generic, non-brand-specific values.
COLOR_PRIMARY = RGBColor(0x33, 0x66, 0x99)   # muted blue
COLOR_ACCENT = RGBColor(0xF0, 0xA8, 0x30)    # amber
COLOR_ACCENT2 = RGBColor(0x66, 0x99, 0xCC)   # lighter blue
COLOR_SECONDARY = RGBColor(0xCC, 0x55, 0x33) # muted orange
CARD_BG = RGBColor(0xFA, 0xFA, 0xFA)
CARD_BORDER = RGBColor(0xDD, 0xDD, 0xDD)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK = RGBColor(0x22, 0x22, 0x22)
PALETTE = [COLOR_PRIMARY, COLOR_ACCENT, COLOR_SECONDARY, COLOR_ACCENT2]

# Font names — overridden by style profile
TITLE_FONT = "Arial"
BODY_FONT = "Arial"

# ── Free area geometry (16:9 standard, overridden by style if available) ──────
FREE_LEFT = Cm(1.36)
FREE_TOP = Cm(3.93)
FREE_WIDTH = Cm(31.18)
FREE_HEIGHT = Cm(13.6)
FREE_BOTTOM = FREE_TOP + FREE_HEIGHT

FREE2_TOP = Cm(2.07)
FREE2_HEIGHT = Cm(15.46)
FREE2_BOTTOM = FREE2_TOP + FREE2_HEIGHT


def _hex_to_rgb(hex_str: str) -> RGBColor:
    """Convert '#RRGGBB' to RGBColor."""
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def load_style_constants(slug: str, styles_root: Path | None = None) -> None:
    """Load colors, fonts, and geometry from a style's style.json.

    Call this once before generating slides with a specific style.
    Overrides the module-level constants above.
    """
    global COLOR_PRIMARY, COLOR_ACCENT, COLOR_ACCENT2, COLOR_SECONDARY
    global CARD_BG, CARD_BORDER, PALETTE, TITLE_FONT, BODY_FONT
    global FREE_LEFT, FREE_TOP, FREE_WIDTH, FREE_HEIGHT, FREE_BOTTOM
    global FREE2_TOP, FREE2_HEIGHT, FREE2_BOTTOM

    if styles_root is None:
        styles_root = Path(__file__).resolve().parent.parent.parent.parent / "dela_state" / "styles"

    profile_path = styles_root / slug / "style.json"
    if not profile_path.exists():
        return

    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    # Colors from theme color scheme
    clr = profile.get("theme", {}).get("color_scheme", {})

    # Primary color from typography summary or dk2
    typo = profile.get("typography", {})
    primary_hex = typo.get("primary_color") or clr.get("dk2", {}).get("hex", "#336699")
    COLOR_PRIMARY = _hex_to_rgb(primary_hex)

    # Accent colors from accent1-6
    accent1_hex = clr.get("accent1", {}).get("hex", "#F0A830")
    COLOR_ACCENT = _hex_to_rgb(accent1_hex)

    accent2_hex = clr.get("accent2", {}).get("hex", "#6699CC")
    COLOR_ACCENT2 = _hex_to_rgb(accent2_hex)

    # Secondary: use accent3 or a computed contrast
    accent3_hex = clr.get("accent3", {}).get("hex", "#CC5533")
    COLOR_SECONDARY = _hex_to_rgb(accent3_hex)

    # Card colors from accent5/accent6 (light variants) or defaults
    accent5_hex = clr.get("accent5", {}).get("hex", "#FAFAFA")
    CARD_BG = _hex_to_rgb(accent5_hex)
    accent6_hex = clr.get("accent6", {}).get("hex", "#DDDDDD")
    CARD_BORDER = _hex_to_rgb(accent6_hex)

    PALETTE = [COLOR_PRIMARY, COLOR_ACCENT, COLOR_SECONDARY, COLOR_ACCENT2]

    # Fonts
    fonts = profile.get("theme", {}).get("font_scheme", {})
    TITLE_FONT = fonts.get("major_latin", "Arial")
    BODY_FONT = fonts.get("minor_latin", "Arial")

    # Slide geometry
    dims = profile.get("slide_dimensions", {})
    if dims:
        from pptx.util import Emu
        FREE_LEFT = Cm(1.36)   # standard left margin
        FREE_TOP = Cm(3.93)    # standard content top
        FREE_WIDTH = Cm(31.18) # standard content width
        FREE_HEIGHT = Cm(13.6) # standard content height
        FREE_BOTTOM = FREE_TOP + FREE_HEIGHT


def body_font_size(height_per_item_cm: float) -> "Pt":
    """Return a body font size scaled to the available height per item.

    Uses fixed tiers so similar slides share the same font size.
    """
    if height_per_item_cm >= 4.0:
        return Pt(20)
    if height_per_item_cm >= 3.0:
        return Pt(18)
    if height_per_item_cm >= 2.2:
        return Pt(16)
    if height_per_item_cm >= 1.6:
        return Pt(14)
    if height_per_item_cm >= 1.1:
        return Pt(12)
    return Pt(10)


def free_area(layout_idx: int = 12) -> tuple:
    """Return (left, top, width, height) for the free content area of a layout."""
    if layout_idx == 2:
        return FREE_LEFT, FREE2_TOP, FREE_WIDTH, FREE2_HEIGHT
    return FREE_LEFT, FREE_TOP, FREE_WIDTH, FREE_HEIGHT