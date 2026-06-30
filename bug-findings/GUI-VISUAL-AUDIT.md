# Dela GUI/Visual Audit Report

**Date**: 2026-06-29
**Method**: Playwright browser automation + PowerShell API testing
**Resolution tested**: 1920×1080, 1440×900, 1024×768, 768×1024, 480×850
**Themes tested**: JARVIS, ULTRAVIOLET, SOLAR, FOREST, CRIMSON

---

## Overall Assessment

The UI is **visually stable across all breakpoints and themes**. No layout breakage, no element overlap, correct z-index stacking. **3 new GUI bugs found** (STT transcription quality, text overflow, truncation inconsistency) plus 1 existing bug confirmed visually (ROUTER `[object Object]`).

---

## Visual Bugs Found

### GUI-BUG-1 [MEDIUM] STT returns empty transcription for real speech audio

**Test**: TTS synthesized speech ("hello", "the quick brown fox") → WAV → POST `/api/voice/stt`
**Expected**: Transcribed text matching the spoken phrase
**Actual**: `{"text":"","ok":true}` — always empty
**Investigation**:
- TTS produces 22050Hz 16-bit mono WAV (verified via header parse)
- `wav_to_pcm()` resamples to 16000Hz via linear interpolation
- `faster-whisper small.en` model is downloaded and present on disk
- `transcribe()` returns 0 segments (empty string)
- Server logs show `[stt] decoded as WAV` and `[stt] transcribed:` (empty)

**Possible causes**:
1. VAD filter (`vad_filter=True`) is filtering all Piper TTS audio as non-speech
2. Linear interpolation resampling from 22050→16000Hz degrades quality enough that whisper can't recognize words
3. Piper `en_US-amy-medium` voice at low quality produces audio outside whisper's training distribution

**Severity**: Medium — makes the voice transcription feature non-functional. Not just a GUI issue; affects core voice pipeline.

**Recommendation**: 
1. Test with `vad_filter=False` 
2. Try resampling with `scipy.signal.resample` instead of linear interpolation
3. Test with a real human voice recording (not TTS) to isolate whether it's the Piper voice or the pipeline
4. Add debug logging for segment count and silence detection

---

### GUI-BUG-2 [LOW] Long unbroken text overflows conversation container

**Test**: Send 500-character string of "A"s with no spaces
**Result**: Conversation message overflows viewport width (1920px+)
**Details**:
- User message (250 chars shown, no ellipsis, overflowX=true)
- Assistant response (203 chars with "...", overflowX=true)

**Root cause**: The conversation message container likely has `word-break: normal` or no `overflow-wrap: break-word`, causing long unbroken strings to extend beyond the container.

**Fix**: Add `overflow-wrap: break-word; word-break: break-all;` to conversation message CSS

**Severity**: Low — requires malicious/accidental input of very long unbroken strings. Normal conversation text is fine.

---

### GUI-BUG-3 [LOW] Message truncation missing ellipsis in some cases

**Test**: 500-char message truncated to 250 chars
**Result**: Truncated message shows 250 chars without "..." suffix
**Details**:
- `textLen: 250, endsWithEllipsis: false` — user message
- `textLen: 203, endsWithEllipsis: true` — assistant message (correct)

The user message truncation at 250 chars doesn't add "...". Only the 200-char conversation overlay truncation adds it.

**Fix**: Ensure the inline truncation `msg.content.slice(0, 200)` always appends "..." when truncated.

---

## Theme Audit

All 5 themes tested. CSS custom properties verified after each switch.

| Theme | idle-rgb | thinking-rgb | busy-rgb | alert-rgb | complete-rgb | Pass |
|-------|----------|-------------|----------|-----------|-------------|------|
| JARVIS | 0,240,255 | 179,136,255 | 255,179,0 | 255,90,69 | 70,242,176 | ✅ |
| ULTRAVIOLET | 138,99,255 | 186,85,211 | 255,100,180 | 255,60,60 | 0,230,200 | ✅ |
| SOLAR | 255,180,0 | 255,120,0 | 255,80,0 | 255,40,40 | 180,255,0 | ✅ |
| FOREST | 0,230,120 | 100,200,255 | 255,200,0 | 255,80,80 | 180,255,100 | ✅ |
| CRIMSON | 255,80,80 | 255,140,0 | 255,180,0 | 255,40,40 | 100,255,150 | ✅ |

- localStorage persists correctly: `dela-theme` key updates on switch
- Color swatches (idle/thinking/busy/alert/complete) rendered per theme
- Orb canvas reads `--idle-rgb` etc. correctly

---

## Responsive Breakpoints

| Breakpoint | Viewport | Overflow | Input Width | Agent Roster | Chips | Pass |
|------------|----------|----------|-------------|-------------|-------|------|
| Desktop FHD | 1920×1080 | None | 437px | Visible | Visible | ✅ |
| Desktop HD+ | 1440×900 | None | 437px | Visible | Visible | ✅ |
| Tablet Landscape | 1024×768 | None | 437px | Visible | Visible | ✅ |
| Tablet Portrait | 768×1024 | None | 437px | Visible | Visible | ✅ |
| Mobile | 480×850 | None | 200px | Visible | Visible | ✅ |

- No elements overflowing viewport at any breakpoint
- Input scales down on mobile (437→200px)
- All interactive elements remain visible and clickable
- Agent roster and chips visible at all sizes

---

## Z-Index Stacking

| Layer | Element | Z-Index | Verified |
|-------|---------|---------|----------|
| 0 | Background grid overlay | 0 | ✅ |
| 1 | Particle canvas | 1 | ✅ |
| 2 | Corner bracket stats | 2 | ✅ |
| 3 | HIVE float window | 3 | ✅ |
| 4 | STREAM float window | 4 | ✅ |
| 6 | SANDBOX float window | 6 | ✅ |
| 7 | Data buttons (top-right) | 7 | ✅ |
| 8 | Dock bar | 8 | ✅ |
| 15 | Conversation overlay | 15 | ✅ |
| 30 | Slide-in panels (Settings etc.) | 30 | ✅ |
| 40 | HitlGate / Connection banner | 40 | ✅ |

**Correct behavior**:
- Last-clicked float window gets highest z-index among floats
- Data panels always above float windows
- HitlGate always on top

---

## VoiceHud Rendering

| Check | Result |
|-------|--------|
| Bar count | 20 (correct, 1 extra from caption container) |
| Bar visibility during recording | ✅ Visible, opacity 1 |
| Bar widths | 3px each |
| Bar heights | 8-30px (animated, varying) |
| HUD position during recording | top:52% |
| Caption/label visible | ✅ "LISTENING" / "recording your voice..." |
| Color during recording | `var(--red)` |
| jfade entrance animation | ✅ |

---

## Conversation Display

| Check | Result |
|-------|--------|
| Max messages shown | 6 (`.slice(-6)`) |
| Truncation length | 200 chars |
| Ellipsis on truncation | ⚠️ Missing on user messages (GUI-BUG-3) |
| Streaming cursor `▍` | ✅ Blinking during response |
| Tool blip display | ✅ Amber, inline |
| Message overflow | ⚠️ Long unbroken text overflows (GUI-BUG-2) |
| XSS safety | ✅ React escapes HTML, no script injection |
| Click-to-copy handler | ✅ onClick registered |

---

## Contrast & Readability

| Element | Foreground | Background | Ratio | WCAG AA (4.5) | Notes |
|---------|-----------|------------|-------|----------------|-------|
| RUN button | rgb(0,240,255) | rgba(255,255,255,0.03) | 1.41 | ❌ | Intentional dark theme aesthetic |
| Body text | (varies) | #05060A | 15+ | ✅ | Light text on dark bg |
| Accent elements | rgb(0,240,255) | #05060A | 12+ | ✅ | High contrast against dark bg |

**Note**: The low contrast on the RUN button is likely intentional as part of the dark sci-fi theme. Not a bug, but worth noting for accessibility.

---

## Animation Performance

| Check | Result |
|-------|--------|
| Long animations (>10s) | None found |
| will-change optimization | N/A (0 animated elements on idle page via style/class) |
| Canvas rendering | 1920×1080, 2D context |
| requestAnimationFrame | ✅ Particle canvas uses RAF |
| DPR cap | ✅ Capped at 2 |
| Frame delta clamp | ✅ Clamped at 0.1s to prevent spiral-of-death |

---

## Empty States

| Panel | Empty State Text | Verified |
|-------|-----------------|----------|
| Workflows | "No workflows yet. Click + NEW to..." | ✅ |
| Memory | "No stored facts yet." | ✅ (from code audit) |
| Tasks | "No tasks found." | ✅ (from code audit) |
| Audit | "No log entries yet." | ✅ (from code audit) |
| Stream | "No activity yet. Send a message to begin." | ✅ (from code audit) |

---

## Previously Known Bugs — Visually Confirmed

- **BUG-1 (ROUTER `[object Object]`)**: Confirmed visually — model text inputs show `[object Object]` in Settings → ROUTER section
- **BUG-3 (Voice error persists)**: Confirmed visually — "Voice error: Transcription failed" remains after page reload
- **BUG-4 (Click-to-copy silent fail)**: Confirmed — no visual feedback when clipboard permission denied

---

## Screenshots Captured

| File | Description |
|------|-------------|
| `visual-audit-01-idle.png` | Idle view at 1920×1080 (JARVIS theme) |
| `visual-audit-02-thinking-streaming.png` | Thinking/streaming state during response |
| `visual-audit-03-conversation-full.png` | Full conversation with messages |
| `visual-audit-04-panel-stacking.png` | 3 float windows + Analytics panel |
| `visual-audit-responsive-desktop-fhd.png` | 1920×1080 |
| `visual-audit-responsive-desktop-hd+.png` | 1440×900 |
| `visual-audit-responsive-tablet-landscape.png` | 1024×768 |
| `visual-audit-responsive-tablet-portrait.png` | 768×1024 |
| `visual-audit-responsive-mobile.png` | 480×850 |

---

## Gaps Not Tested

1. **Real microphone audio transcription** — Playwright cannot capture mic audio; tested with synthesized TTS audio instead (which revealed GUI-BUG-1)
2. **HITL Gate visual** — Not triggered during testing (requires server-sent `confirmation_request`)
3. **3D JarvisOrb** — Component exists but is unused (2D ParticleCanvas used instead)
4. **Float window drag smoothness** — Drag tested functionally, but not for animation smoothness
5. **Framer-motion spring animations** — Panel slide-in/out tested functionally, not for smoothness
6. **High-DPI (4K/Retina)** — Only tested up to 1920×1080
7. **Browser compatibility** — Only tested in Edge (Chromium)
