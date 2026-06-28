"""
pptx_lib — Reusable python-pptx building blocks for BMW template presentations.

Import high-level helpers directly:
    from pptx_lib import add_card_row, add_hero_number, add_timeline

Or import from submodules:
    from .cards import add_card_with_accent
    from .text import add_bullet_paragraph
    from .infographics import add_progress_ring
"""

from .cards import (
    add_bottom_banner,
    add_card_with_accent,
    add_icon_circle,
    add_takeaway_box,
)
from .constants import (
    CARD_BG,
    CARD_BORDER,
    COLOR_ACCENT,
    COLOR_ACCENT2,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    DARK,
    FREE2_BOTTOM,
    FREE2_HEIGHT,
    FREE2_TOP,
    FREE_BOTTOM,
    FREE_HEIGHT,
    FREE_LEFT,
    FREE_TOP,
    FREE_WIDTH,
    PALETTE,
    WHITE,
    body_font_size,
    free_area,
)
from .credits import add_credits_slide
from .grid import ContentGrid
from .helpers import (
    bring_to_front,
    fix_dept_placeholder,
    remove_empty_placeholders,
    send_to_back,
    set_notes,
    set_ph_margins,
    suppress_bullet,
)
from .images import (
    add_background_image_with_overlay,
    add_image_preserved_ratio,
    add_text_shadow_box,
    fill_placeholder_image,
)
from .infographics import (
    add_callout,
    add_funnel,
    add_hero_number,
    add_hexagon_grid,
    add_progress_ring,
    add_pull_quote,
    add_rag_dashboard,
    add_rag_header,
    add_swimlane_timeline,
    add_timeline,
    add_venn,
)
from .layout import (
    add_key_value_pairs,
    add_mece_tiles,
    add_numbered_badge_list,
    add_pillars,
    add_pyramid_slide_content,
    add_sidebar_layout,
    add_tabbed_headers,
    add_zigzag_blocks,
)
from .shapes import (
    add_arrow_bar_steps,
    add_chevron_chain,
    add_divider_line,
    add_gap_chevron,
)
from .tables import (
    add_comparison_table,
    add_styled_table,
)
from .text import (
    add_accent_underline,
    add_bullet_paragraph,
    add_textbox,
)

__all__ = [
    # constants
    "body_font_size",
    "COLOR_PRIMARY",
    "COLOR_ACCENT",
    "COLOR_ACCENT2",
    "COLOR_SECONDARY",
    "CARD_BG",
    "CARD_BORDER",
    "WHITE",
    "DARK",
    "PALETTE",
    "FREE_LEFT",
    "FREE_TOP",
    "FREE_WIDTH",
    "FREE_HEIGHT",
    "FREE_BOTTOM",
    "FREE2_TOP",
    "FREE2_HEIGHT",
    "FREE2_BOTTOM",
    "free_area",
    # helpers
    "send_to_back",
    "bring_to_front",
    "remove_empty_placeholders",
    "suppress_bullet",
    "set_ph_margins",
    "set_notes",
    "fix_dept_placeholder",
    # text
    "add_textbox",
    "add_bullet_paragraph",
    "add_accent_underline",
    # images
    "fill_placeholder_image",
    "add_image_preserved_ratio",
    "add_text_shadow_box",
    "add_background_image_with_overlay",
    # cards
    "add_card_with_accent",
    "add_icon_circle",
    "add_bottom_banner",
    "add_takeaway_box",
    # shapes
    "add_chevron_chain",
    "add_arrow_bar_steps",
    "add_divider_line",
    "add_gap_chevron",
    # tables
    "add_styled_table",
    "add_comparison_table",
    # layout
    "add_pillars",
    "add_mece_tiles",
    "add_pyramid_slide_content",
    "add_sidebar_layout",
    "add_tabbed_headers",
    "add_zigzag_blocks",
    "add_numbered_badge_list",
    "add_key_value_pairs",
    # infographics
    "add_timeline",
    "add_swimlane_timeline",
    "add_rag_dashboard",
    "add_rag_header",
    "add_pull_quote",
    "add_progress_ring",
    "add_hexagon_grid",
    "add_venn",
    "add_funnel",
    "add_callout",
    "add_hero_number",
    # grid
    "ContentGrid",
    # credits
    "add_credits_slide",
]
