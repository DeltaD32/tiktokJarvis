# Deep Audit: App.jsx — Main Application Component

**File**: `frontend/src/App.jsx` (509 lines)
**Audit scope**: State management, stale closures, rendering inefficiencies, panel state, data fetching races, theme bugs, voice integration, accessibility

---

## Summary

| Severity | Count | Key Issues |
|----------|-------|------------|
| HIGH | 2 | Data fetch race condition (stale overwrites fresh); Runtime theme switching broken |
| MEDIUM | 6 | Voice double-send race; Missing useCallback; Input not reset; Stream not cleared on server-idle; Panel crash on undefined id; Copy keyboard-inaccessible |
| LOW | 20 | Missing memoization; index-as-key; DOM patterns; accessibility gaps |
| INFO | 2 | Style observations |

**Total: 30 issues**

---

## HIGH Issues

### H1. Data fetch race condition — stale data permanently overwrites fresh
**Lines**: 114-122 (periodic interval)
**Problem**: Interval fires every 15,000ms. If `/api/uplink` takes >15s to respond, two requests are in-flight simultaneously. Older response can arrive after newer, overwriting fresh data with stale. No request sequencing, versioning, or AbortController. Same applies to `/api/agents`.

### H2. Runtime theme switching broken — ACCENT_RGB holds stale colors
**Lines**: 37-44, 126-130 + `themes.js:54-63`
**Problem**: `ACCENT_RGB` is mutated at module load via `Object.assign(ACCENT_RGB, {..._theme.colors})`. `applyTheme(newTheme)` updates CSS custom properties (`--idle-rgb`, etc.) but `ACCENT_RGB` object still holds **old theme's colors**. On next `orbState` change, `useEffect` (line 126-130) overwrites `--accent-rgb`/`--accent` with stale theme colors. Theme appears to switch, then partially reverts. Requires page reload for full effect.

---

## MEDIUM Issues

### M1. Voice double-send race: stale transcript injected during new recording
**Lines**: 187-201 (handleVoiceToggle)
**Problem**: `handleVoiceToggle` not memoized — recreated every render. After `await toggleVoice()`, if user clicked again during await, new recording starts but STT result from OLD recording is still processed (sendMessage, setInput). Injects stale text into conversation mid-recording.

### M2. Missing useCallback on handleSend — unnecessary TopStrip re-renders
**Lines**: 173-178
**Problem**: `handleSend` not wrapped in `useCallback`. Passed as `onSend` prop to TopStrip and `onClick` on EXECUTE button. New function reference every render forces child re-renders.

### M3. `input` state never cleared on idle transitions
**Line**: 63
**Problem**: If user types, transitions to non-idle externally (server state_change), then returns to idle, old input value reappears. Not catastrophic but inconsistent UX.

### M4. `currentStream` not cleared on server-initiated `state_change: idle`
**Lines**: 55-57 (from useDelaWS)
**Problem**: If server sends `state_change: {state:'idle'}` while stream is mid-flight, `currentStream` is NOT cleared. Stream text lingers until 60s timer fires or new message arrives.

### M5. `togglePanel` crashes on undefined panel id
**Lines**: 142-147
**Problem**: `prev[id]` — if id is typo'd or undefined, accessing `.open` throws TypeError. Current code only passes 'hive'/'stream'/'sandbox' from initial state, so safe for now, but fragile.

### M6. Click-to-copy is keyboard-inaccessible
**Lines**: 388-395
**Problem**: Conversation messages have `onClick` for copy but no `onKeyDown`. They are `<div>` elements — not focusable, not in tab order, not activatable via Enter/Space. Keyboard-only users cannot copy messages. `title="Click to copy"` reinforces mouse-only assumption.

### M7. `clearVoiceError` used in useEffect but absent from deps array (bypassed)
**Line**: 83-86
**Problem**: `clearVoiceError` used inside effect but not in deps. Technically violates Rules of Hooks (exhaustive-deps). Practically harmless (runs once on mount) but would fail strict linting.

---

## LOW Issues — State Management

### L1-L7. Missing useCallback on callbacks causing unnecessary re-renders
- `handleKey` (line 180) — not memoized
- `handleVoiceToggle` (line 187) — not memoized
- `openLocalPanel` (line 169) — not memoized, used in 10+ inline onClick handlers
- `handleClose` (line 170) — not memoized, passed to 10 panels
Each creates new function reference every render.

### L8. Panels/localPanel not reset on idle transitions
**Lines**: 68-69
Panel opened during active mode stays open when returning to idle. Only cleared on explicit close.

### L9. `confirmRequest` never reset on idle transitions
**Line**: 57
If HITL confirmation active and conversation ends, HitlGate shows stale confirmation indefinitely.

### L10. Sandbox/Stream panel overlap on narrow viewports
**Lines**: 133-140
Sandbox at `x: Math.max(28, W - 458)` collides with Hive at x=28 below ~486px width. Stream at midpoint also collapses below ~588px. No minimum viewport guard.

### L11. zRef initialized to 1; first togglePanel skips to z=2
**Lines**: 142-147
`++zRef.current` pre-increments. Initial z:1 is dead after first toggle. Minor inconsistency.

### L12. index-as-key on IDLE_STATS map
**Line**: 300
Static array, acceptable now, fragile if made dynamic.

### L13. agent name as React key — collision possible
**Line**: 363
Two agents with same name would recycle DOM nodes incorrectly.

### L14. zRef reset inconsistency on StrictMode remount
**Lines**: 70, 143-146, 153-154
On remount, zRef starts fresh but state may have stale z values from prior mount.

---

## LOW Issues — Data Fetching

### L15. No AbortController or mounted guard on fetches
**Lines**: 89-122
If component unmounts during fetch, setState on unmounted component.

### L16. Silent error swallowing — no user feedback
**Lines**: 96-104, 111
`.catch(() => {})` on agent/tool fetches drops all errors. User never knows data is stale.

### L17. `dismissNotice` optimistic update without rollback
useDelaWS.js:195 — local state removed before server confirms DELETE. If server fails, notice reappears on next refresh.

---

## LOW Issues — Voice Integration

### L18. Two `recording` values from different render batches
**Lines**: 187-201 vs useVoiceRecorder.js:114-120
`handleVoiceToggle` checks `recording` from App's render, then calls `toggleVoice()` which checks from useVoiceRecorder's render. Could desync in concurrent mode.

### L19. `voiceEnabled` not persisted — lost on refresh
**Line**: 76
Defaults to OFF every session. User must re-enable.

### L20. Barge-in only triggers on `orbState === 'thinking'`
**Lines**: 215-219
Other non-idle states (busy, alert) don't stop TTS.

### L21. Voice errors lack dismiss/retry UI
**Lines**: 338-341
Only cleared via `clearVoiceError()` on mount (page refresh). No in-session dismiss.

---

## LOW Issues — Rendering / Patterns

### L22. Direct DOM style manipulation bypassing React
**Lines**: 128-129
`document.documentElement.style.setProperty()` — correct as side effect in useEffect, but bypasses virtual DOM.

### L23. Clipboard fallback uses deprecated execCommand
**Lines**: 393-399
Creates textarea, appends to body, calls deprecated `execCommand('copy')`. No keyboard equivalent.

### L24. AnimatePresence flicker on rapid panel switching
**Line**: 466
Exit animation may be interrupted by next panel mounting during rapid clicks.

---

## Accessibility Issues

### A1. MIC button lacks `aria-label`
**Line**: 329-335
When label is "...", accessible name is meaningless.

### A2. Idle input not re-focused on idle transition
**Line**: 327
`autoFocus` only fires on initial mount, not on active→idle transitions.

### A3. Data panel buttons lack contextual aria-labels
**Lines**: 254-263
10 buttons with only visible text (e.g. "ANALYTICS"). Screen readers get minimal context.

---

## Areas With Zero Issues
- **Conditional hooks**: All hooks called unconditionally at top level
- **Ref vs State sync**: No critical inconsistencies beyond noted zRef behavior
- **Animation timing**: No infinite loops or timing-dependent state bugs
