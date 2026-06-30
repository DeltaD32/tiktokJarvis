# Deep Audit: Performance, Accessibility & Security

**Audit scope**: Render profiling, memory analysis, accessibility tree, keyboard navigation, XSS surface, unsafe patterns

---

## Performance Audit

### P1. `setCurrentStream` called on every token — mass re-renders
**File**: `useDelaWS.js:76`
Each `token` WebSocket message triggers `setCurrentStream(streamBuffer.current)`. A 10,000-token reply = 10,000 React state updates + re-renders of the entire App component. For long streams this becomes a significant performance bottleneck. Should batch/rate-limit: throttled to 60fps (16ms) or use `requestAnimationFrame`.

### P2. `handleSend`, `openLocalPanel`, `handleClose` not memoized
**File**: `App.jsx:169-178`
These callbacks are passed as props to child components. New function reference every render forces children to re-render (even if they use React.memo). Missing `useCallback`.

### P3. `_bytes_to_float` + FFT doubles peak memory during resampling
**File**: `stt.py:89-92, 131-141`
PCM bytes → float32 (4x memory) → FFT (2x more for complex) → irFFT → np.arange(len(audio)) (another 8 bytes per sample). Peak memory ~12x input size.

### P4. `synthesize_wav` accumulates all audio — no streaming
**File**: `tts.py:118-129`
All Piper chunks stored in `all_audio: list[np.ndarray]`, then `np.concatenate()`. Long text → memory spike. Should write directly to `io.BytesIO` buffer per chunk.

### P5. Canvas particle count: 460 galaxy + 70 cloud + 150 corona = 680 particles
**File**: `ParticleCanvas.jsx`
Each particle rendered per frame via `requestAnimationFrame`. Acceptable for 2D canvas at 60fps on modern hardware. DPR capped at 2. No perf issue.

### P6. VoiceHud: 20 bars with inline styles recalculated per render
**File**: `VoiceHud.jsx`
Each bar has `style={{ width, height, animationDuration, animationDelay }}` computed inline. Combined with `Math.random()` per render, this causes layout thrashing. Should use CSS classes or `useMemo` for bar configs.

### P7. No virtualization for conversation
**File**: `App.jsx:384`
`.slice(-6)` limits to 6 messages, so no need for virtualization. OK for current design.

### P8. Periodic data fetching: 15s interval, no debounce/batching
**File**: `App.jsx:114`
Three separate intervals (uplink, agents, tools starting at staggered times). Inefficient but low-cost (HTTP GET with small payloads).

---

## Accessibility Audit

### A1. Click-to-copy is keyboard-inaccessible
**File**: `App.jsx:388-395`
Conversation messages use `<div onClick>` — not focusable (no tabIndex), not activatable via Enter/Space. `title="Click to copy"` reinforces mouse-only assumption. **Severity: Medium**

### A2. Idle input not re-focused on active→idle transition
**File**: `App.jsx:327`
`autoFocus` only on initial mount. After 60s idle returns, user must click to type. Should use ref + `useEffect` on `isIdle`. **Severity: Low**

### A3. MIC button accessible name is "..." during transcribing
**File**: `App.jsx:329-335`
Screen readers hear "..." when button shows transcribing state. Should use `aria-label={recording ? 'Stop recording' : transcribing ? 'Transcribing...' : 'Start recording'}`. **Severity: Low**

### A4. Data panel buttons lack contextual aria-labels
**File**: `App.jsx:254-263`
10 buttons with only visible text (e.g. "ANALYTICS"). Screen readers get minimal context. Should have `aria-label="Open Analytics panel"`. **Severity: Low**

### A5. Settings form controls lack labels
**File**: `SettingsPanel.jsx` (869 lines)
LiveField text inputs and selects lack `<label>` association. Relies on adjacent `<span>` text which isn't semantically linked. **Severity: Low**

### A6. No skip-navigation link
No "Skip to main content" link at top of page. Keyboard users must tab through 10 data buttons to reach input. **Severity: Low**

### A7. Float windows: drag-only, no keyboard positioning
FloatWindow.jsx implements drag (onMouseDown/onMouseMove/onMouseUp) but has no keyboard (arrow keys) repositioning. **Severity: Low**

### A8. Color-only state indicators
Corner stats (HEARTBEAT ACTIVE/PAUSED) show state via color only (green/dim). No text alternative for color-blind users. **Severity: Low**

### A9. Focus trap in HitlGate
**File**: `HitlGate.jsx`
Full-screen overlay for confirmations doesn't trap focus. Tab can escape behind overlay. **Severity: Low**

---

## Security Audit

### S1. No Content Security Policy
No CSP headers set. XSS via inline script injection would succeed if an injection vector exists. (React's JSX escaping prevents most, but CSP would be defense-in-depth.)

### S2. Env-file injection via newline (HIGH — see backend audit H3)
**File**: `server.py:697-717`
Sanitized `value` written to `.env`. Newline injection creates arbitrary env vars. `.env` contains API keys.

### S3. Path traversal via PIPER_VOICE config (HIGH — see backend audit H11)
**File**: `tts.py:37-48`
`f"{name}.onnx"` without path sanitization allows `../../target` traversal.

### S4. Model download without integrity verification (HIGH — see backend audit H10)
**File**: `tts.py:45,47`
`urlretrieve()` downloads ONNX model files with no hash check. MITM → malicious model → code execution via ONNX Runtime.

### S5. No auth on any API endpoint
All /api/* endpoints are unauthenticated. Any network-accessible client can enumerate connections (masked API keys), modify settings, delete memory, kill heartbeat. **Severity: Medium** (acceptable for local-only, unacceptable for network-exposed deployments).

### S6. XSS via conversation content — SAFE
React's JSX auto-escaping prevents HTML injection. Tested: `<script>alert(1)</script>` rendered as text. **No issue.**

### S7. eval() / new Function() — NONE FOUND
No dynamic code execution in frontend codebase. **No issue.**

### S8. innerHTML / dangerouslySetInnerHTML — NONE FOUND  
Frontend uses only React JSX and textContent patterns. **No issue.**

### S9. localStorage: theme only, no sensitive data
Only `dela-theme` key stored. No tokens, passwords, or API keys. **No issue.**

### S10. Websocket: no origin validation
**File**: `server.py:917`
`ws_endpoint` accepts any WebSocket connection. No `Origin` header check. Any webpage can open a WebSocket to the backend. Combined with S5, allows full remote control if network-exposed.

---

## Areas With Zero Issues
- **No eval/Function** usage
- **No innerHTML** usage in frontend
- **No credentials in localStorage** beyond theme
- **No prototype pollution** vectors
- **React XSS protection** effective against conversation content injection
- **Canvas** uses 2D context only (no WebGL shader injection surface)
