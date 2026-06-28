---
name: presentation
description: Guidance for designing and generating professional presentations — storyline design, layout selection, and visual principles.
tools: clone_pptx_style, list_ppt_styles, generate_presentation, dispatch_subagent
---

## Presentation Skill

When creating a presentation, follow this workflow:

1. **Check for styles.** Call `list_ppt_styles` to see what's available. If none, ask the user for a .pptx template to clone.

2. **Design the storyline.** Don't just map content 1:1 onto slides. Think like a presentation designer:
   - How many slides? (Usually 5-15 for a standard deck)
   - What's the narrative arc? (Title → context → data → insights → recommendations → summary)
   - What layout type per slide? (Vary them — don't use bullets for every slide)

3. **Choose layouts wisely:**
   - `title_only`: Title slide, section dividers
   - `bullets`: Standard content with 3-5 bullet points
   - `hero_number`: When there's one impactful number (revenue, growth %, count)
   - `pillars`: 2-4 equal-weight concepts with sub-points
   - `mece_tiles`: 3-5 mutually exclusive categories
   - `table`: Structured data comparison
   - `chevron`: Sequential steps or process flow
   - `cards`: 2-4 items each with a title and body
   - `key_message`: Single powerful statement, centered

4. **Generate.** Call `generate_presentation` with the storyline and style.

5. **Design rules:**
   - One message per slide. If a slide has too much content, split it.
   - Less text, more impact. Put details in speaker notes, not on the slide.
   - Visualize numbers. One large number > a table of numbers.
   - Vary layout types. Don't use the same layout for 3 consecutive slides.
   - Start with a title slide. End with key takeaways or next steps.

6. **For complex decks** (10+ slides), consider dispatching the `presenter` sub-agent to handle the storyline design and generation in one focused pass.