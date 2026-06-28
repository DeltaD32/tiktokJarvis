"""Presentation package — PPT style cloner, style registry, and slide generator.

Three capabilities:
  1. Clone: parse any .pptx, extract its visual DNA, store as a reusable style.
  2. Registry: index stored styles, list/get/resolve by name.
  3. Generate: build a .pptx deck from content using a stored style.

Adding a style = clone a .pptx (or drop one in dela_state/styles/).
Adding a building block = one function in pptx_lib/.
"""

from dela.presentation.style_registry import (
    list_styles,
    get_style,
    resolve_style,
    style_dir,
    registry_path,
    styles_summary,
    load_style_profile,
    style_template_path,
    style_guide_path,
)

__all__ = [
    "list_styles",
    "get_style",
    "resolve_style",
    "style_dir",
    "registry_path",
    "styles_summary",
    "load_style_profile",
    "style_template_path",
    "style_guide_path",
]