"""Presentation tools — clone styles, list styles, generate presentations.

Three tools that let Dela parse PPT files, manage styles, and generate decks:
  - clone_pptx_style: parse a .pptx, extract its visual DNA, store it
  - list_ppt_styles: list all stored styles
  - generate_presentation: build a .pptx from a storyline using a stored style

Cloning and generating are consequential (they write files), so they require
confirmation. Listing is read-only.
"""

from __future__ import annotations

from dela.presentation import styles_summary, resolve_style
from dela.presentation.style_registry import load_style_profile, style_template_path
from dela.tools import register


@register(
    name="clone_pptx_style",
    description=(
        "Clone the visual style of a PowerPoint (.pptx) file. Extracts its colors, "
        "fonts, layouts, and typography into a reusable style profile stored in "
        "the registry. Use this when the user provides a .pptx template they want "
        "to replicate the look of, or when they say 'parse this presentation' or "
        "'clone this style'. The style can then be used to generate new presentations "
        "with the same look. Requires confirmation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the .pptx file to clone.",
            },
            "name": {
                "type": "string",
                "description": "A human-readable name for this style (e.g. 'Company Template').",
            },
            "description": {
                "type": "string",
                "description": "Optional one-line description of the style.",
            },
        },
        "required": ["file_path", "name"],
    },
    requires_confirmation=True,
)
def clone_pptx_style(args: dict) -> str:
    import os
    from pathlib import Path
    from dela.presentation.clone_style import extract_full_style, register_style, slugify, generate_brand_guide_md
    from dela.presentation.style_registry import style_dir as get_style_dir, upsert_style

    file_path = args["file_path"]
    name = args["name"]
    description = args.get("description", "")

    if not os.path.exists(file_path):
        return f"File not found: {file_path}"

    slug = slugify(name)

    # Extract the full style profile
    try:
        style = extract_full_style(file_path)
    except Exception as e:
        return f"Failed to extract style: {e}"

    # Create the style directory and copy the source file
    sdir = get_style_dir(slug)
    sdir.mkdir(parents=True, exist_ok=True)

    import shutil
    shutil.copy2(file_path, str(sdir / "source.pptx"))

    # Save style.json
    import json
    (sdir / "style.json").write_text(json.dumps(style, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate and save brand guide
    brand_guide = generate_brand_guide_md(style, name, file_path, is_builtin=False)
    (sdir / "brand-guide.md").write_text(brand_guide, encoding="utf-8")

    # Register in the registry
    register_style(slug, name, description, Path(file_path), sdir, style)

    # Extract typography summary for the response
    typo = style.get("typography", {})
    primary_color = typo.get("primary_color", "?")
    primary_font = typo.get("primary_font", "?")
    n_layouts = len(style.get("layouts", []))

    return (
        f"Style '{name}' (slug: {slug}) cloned successfully.\n"
        f"  Primary color: {primary_color}\n"
        f"  Primary font: {primary_font}\n"
        f"  Layouts: {n_layouts}\n"
        f"  Stored at: {sdir}\n"
        f"Use this style with generate_presentation by passing style='{slug}'."
    )


@register(
    name="list_ppt_styles",
    description=(
        "List all registered presentation styles with their colors, fonts, and "
        "layout counts. Use this when the user asks what styles are available, "
        "or before generating a presentation to help them choose. Read-only."
    ),
    parameters={"type": "object", "properties": {}},
)
def list_ppt_styles(args: dict) -> str:
    return styles_summary()


@register(
    name="generate_presentation",
    description=(
        "Generate a PowerPoint (.pptx) presentation from a storyline using a "
        "stored style. The storyline is a list of slide specs, each with a "
        "layout type, title, and content. Use this when the user wants to "
        "create slides, build a deck, or make a presentation. Requires confirmation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "style": {
                "type": "string",
                "description": "The style slug or name to use (e.g. 'company-template'). Use list_ppt_styles to see available styles.",
            },
            "storyline": {
                "type": "array",
                "description": "List of slide specifications.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Slide title."},
                        "layout_type": {
                            "type": "string",
                            "description": "Type of slide layout.",
                            "enum": ["bullets", "title_only", "hero_number", "pillars",
                                     "mece_tiles", "table", "chevron", "cards", "key_message"],
                        },
                        "content": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Bullet content (for bullets layout).",
                        },
                        "hero_number": {"type": "string", "description": "Large number (for hero_number layout)."},
                        "hero_subtitle": {"type": "string", "description": "Subtitle below the number."},
                        "layout": {"type": "integer", "description": "Layout index in the template (default 12)."},
                        "notes": {"type": "string", "description": "Speaker notes for this slide."},
                    },
                    "required": ["title", "layout_type"],
                },
            },
            "output_path": {
                "type": "string",
                "description": "Where to save the .pptx file. Defaults to dela_state/output/.",
            },
            "footer": {
                "type": "string",
                "description": "Footer text for all slides (e.g. 'Company | Date | Author').",
            },
        },
        "required": ["style", "storyline"],
    },
    requires_confirmation=True,
)
def generate_presentation(args: dict) -> str:
    from pathlib import Path
    from dela.presentation.generator import generate

    style_query = args["style"]
    storyline = args["storyline"]
    output_path = args.get("output_path", "")
    footer = args.get("footer", "")

    # Resolve the style
    entry = resolve_style(style_query)
    if entry is None:
        return f"Style '{style_query}' not found. Available styles:\n{styles_summary()}"

    slug = entry["slug"]

    # Default output path
    if not output_path:
        output_path = str(Path("dela_state/output") / f"presentation-{slug}.pptx")

    # Generate
    try:
        result = generate(
            style_slug=slug,
            storyline=storyline,
            output_path=output_path,
            footer=footer,
        )
        return f"Presentation generated: {result}\nUsed style: {entry['name']} ({slug})\nSlides: {len(storyline)}"
    except Exception as e:
        return f"Generation failed: {e}"