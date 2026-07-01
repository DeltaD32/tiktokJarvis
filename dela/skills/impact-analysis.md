# Impact Analysis & Feature Evaluation

When the user asks about adding a capability, integrating an external tool,
or evaluating a feature, follow this structured process. Output the final
assessment as a rich HTML snippet using the template below.

## Process

1. **Dispatch in parallel**: researcher (investigate the external tool/repo)
   and system_expert (inspect Dela's architecture for integration seams).
2. **Synthesize findings** into the template below.
3. **Open in panel** using `show_panel` with `panel='report'`, the template
   HTML as `content`, and a descriptive `title`.
4. **Ask the user**: "Should I proceed with implementation, or shelve this
   for later?" Wait for their answer before implementing.

## HTML Template

Use this EXACT HTML structure for the report. Fill in all [bracketed]
placeholders with actual data. Keep the structure intact — the frontend
panel styles will render headings, tables, scores, and verdicts correctly.

```html
<h1>[Feature / Tool Name] — Impact Analysis</h1>

<div class="meta-row">
  <div class="meta-item">
    <div class="meta-label">Source</div>
    <div class="meta-value">[URL or repo name]</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">License</div>
    <div class="meta-value">[MIT / Apache 2.0 / GPL / etc.]</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Tech Stack</div>
    <div class="meta-value">[React / Python / Node / etc.]</div>
  </div>
</div>

<h2>What It Does</h2>
<p>[2-3 sentence summary of what the tool/repo does]</p>

<h2>Compatibility Assessment</h2>
<table>
  <tr><th>Dimension</th><th>Score</th><th>Notes</th></tr>
  <tr>
    <td>Architecture Fit</td>
    <td><span class="score [high/medium/low]">[0-10]</span></td>
    <td>[How well it maps to Dela's seams]</td>
  </tr>
  <tr>
    <td>Integration Complexity</td>
    <td><span class="score [high/medium/low]">[0-10]</span></td>
    <td>[Effort: easy / medium / hard — 10 means trivial]</td>
  </tr>
  <tr>
    <td>Security Impact</td>
    <td><span class="score [high/medium/low]">[0-10]</span></td>
    <td>[New attack surface? Data exposure?]</td>
  </tr>
  <tr>
    <td>Value to Dela</td>
    <td><span class="score [high/medium/low]">[0-10]</span></td>
    <td>[What new capability does this unlock?]</td>
  </tr>
  <tr>
    <td>Maintenance Burden</td>
    <td><span class="score [high/medium/low]">[0-10]</span></td>
    <td>[Ongoing dependency cost]</td>
  </tr>
</table>

<h2>Integration Approach</h2>
<ul>
  <li><strong>Dela Seam:</strong> [tool / agent / skill / channel / check]</li>
  <li><strong>New Files:</strong> [list estimated files]</li>
  <li><strong>New Dependencies:</strong> [list npm/pip packages needed]</li>
  <li><strong>Pattern to Follow:</strong> [which existing module is the closest model]</li>
</ul>

<h2>Risks & Blockers</h2>
<ul>
  <li>[Risk or blocker]</li>
  <li>[Risk or blocker — say "None identified" if clean]</li>
</ul>

<h2>Adoptable Ideas (built from scratch)</h2>
<p>Even if direct integration is rejected, these ideas can be built natively:</p>
<ul>
  <li><strong>[Feature name]:</strong> [one-sentence approach]. Complexity: [easy/medium/hard].</li>
</ul>

<hr>

<div class="verdict [recommended/conditional/rejected]">
  [RECOMMENDED / CONDITIONAL / NOT RECOMMENDED]
</div>

<h2>Next Steps (if proceeding)</h2>
<ol>
  <li>[Step 1]</li>
  <li>[Step 2]</li>
  <li>[Step 3]</li>
</ol>
```

## Scoring Guide

- Use `class="score high"` for 8-10, `class="score medium"` for 5-7, `class="score low"` for 0-4.
- Use `class="verdict recommended"` for RECOMMENDED, `class="verdict conditional"` for CONDITIONAL, `class="verdict rejected"` for NOT RECOMMENDED.

## Rules

- Never claim implementation was done if you only advised.
- If implementation requires changes to brain.py or provider.py, mark as CONDITIONAL (core changes need careful review).
- Always flag GPL/AGPL licenses as a blocker (NOT RECOMMENDED).
- Always identify which existing Dela module is the closest pattern to follow.
- Propose clean-room implementations for valuable ideas even if direct integration is rejected.
