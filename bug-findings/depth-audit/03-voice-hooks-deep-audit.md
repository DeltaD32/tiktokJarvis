# Deep Audit: Voice Hooks — Recorder, TTS, and HUD

**Files**: 
- `frontend/src/hooks/useVoiceRecorder.js` (131 lines)
- `frontend/src/hooks/useVoiceTTS.js` (81 lines)
- `frontend/src/components/VoiceHud.jsx` (33 lines)

**Audit scope**: MediaRecorder lifecycle, TTS queue management, visual rendering, error paths, cleanup, memory leaks

---

## Summary

| Severity | Count | Key issues |
|----------|-------|------------|
| CRITICAL | 2 | Dead FormData (wrong body sent); No MediaRecorder existence check |
| HIGH | 4 | Stream leak on constructor throw; Double-start leaks; Stale audio plays after stop; Blob URL leak on stop; Math.random in render causes jank |
| MEDIUM | 5 | Shared chunks across recordings; No AbortController; Safari unsupported; Queue unbounded; Missing cleanup on unmount |
| LOW | 9 | Dead ref, misleading comments, sentence regex bugs, missing aria-labels |

**Total: 20 issues**

---

## CRITICAL Issues

### C1. Dead FormData — raw Blob sent with wrong Content-Type
**File**: `useVoiceRecorder.js:86-92`
**Problem**: `formData` is constructed (lines 86-87) but **never used**. Line 91 sends `blob` directly. The `Content-Type` is hardcoded to `'audio/webm'` on line 92, which mismatches when `audio/webm;codecs=opus` was the actual MIME (line 43). Backend receives either wrong Content-Type or wrong body format.

### C2. No `typeof MediaRecorder !== 'undefined'` check — throws on unsupported browsers
**File**: `useVoiceRecorder.js:42-46`
**Problem**: `MediaRecorder.isTypeSupported(...)` and `new MediaRecorder(...)` called without checking MediaRecorder exists. Older Safari, some mobile browsers throw ReferenceError. Acquired stream is leaked (see H1).

---

## HIGH Issues

### H1. Stream leak when MediaRecorder constructor throws
**File**: `useVoiceRecorder.js:39-46`
**Problem**: `streamRef.current = stream` (line 39) happens BEFORE `new MediaRecorder(stream, ...)` (line 46). If constructor throws, catch block at line 56 never stops stream tracks. Microphone held open indefinitely until unmount.

### H2. Double `start()` leaks stream and recorder
**File**: `useVoiceRecorder.js:28-59`
**Problem**: No guard at top of `start()` checks if already recording. Calling `start()` twice:
1. Acquires second getUserMedia stream
2. Creates second MediaRecorder
3. Overwrites refs
4. First stream and recorder leaked without stopping tracks

### H3. `stop()` does not cancel in-flight fetch — stale audio plays after stop
**File**: `useVoiceTTS.js:70-78, 33-58`
**Problem**: `stop()` clears queue and pauses `audioRef.current`, but any `fetch('/api/voice/tts', ...)` started before `stop()` still completes. Its `.then()` creates new `Audio` element and calls `.play()`, causing audio playback after user explicitly stopped. No AbortController or cancellation flag in `.then()` chain.

### H4. Blob URL leaked on `stop()`
**File**: `useVoiceTTS.js:70-78`
**Problem**: `stop()` calls `audioRef.current.pause()` and sets to null, but never calls `URL.revokeObjectURL()`. The blob URL created at line 43 for currently playing audio is leaked. (URL IS revoked in `onended`/`onerror`, but `stop()` prevents those from firing by pausing.)

### H5. `Math.random()` in render — continuous animation jank
**File**: `VoiceHud.jsx:5-7`
**Problem**: New random `dur` and `delay` values generated on EVERY render. Every parent re-render resets all 20 bar animations, causing visible jitter/flashing even when props haven't changed.

---

## MEDIUM Issues

### M1. `chunksRef` shared across recorder instances — data corruption
**File**: `useVoiceRecorder.js:47, 49-51`
**Problem**: When double-`start()` occurs, `chunksRef.current = []` resets array that OLD recorder's `ondataavailable` handler still references. Old recorder's chunks get pushed into new recording's array.

### M2. No AbortController — in-flight transcription not cancellable
**File**: `useVoiceRecorder.js:85-107`
**Problem**: If `stop()` called while first call's `fetch('/api/voice/stt', ...)` is still in-flight, promise resolves immediately but fetch continues. Its `.then()` later calls `setTranscript(...)` and `setTranscribing(false)`, overwriting newer state.

### M3. Safari / iOS unsupported — no WAV fallback
**File**: `useVoiceRecorder.js:42-44`
**Problem**: Safari supports neither `audio/webm;codecs=opus` nor `audio/webm`. Fallback ends at `'audio/webm'`, which Safari's MediaRecorder rejects. Comment says "package as WAV" but code never produces WAV. Recording silently fails on all iOS browsers.

### M4. No queue size limit — unbounded growth
**File**: `useVoiceTTS.js:62-64`
**Problem**: `queueRef.current.push(...sentences)` has no upper bound. Rapid repeated `speak()` calls grow queue without limit, consuming memory and delaying playback arbitrarily.

### M5. No cleanup on component unmount — orphaned audio and fetches
**File**: `useVoiceTTS.js:1` (missing useEffect)
**Problem**: No `useEffect` return cleanup. If component unmounts mid-playback, all blob URLs remain un-revoked, in-flight fetches never aborted, Audio element may continue playing orphaned.

### M6. Truncated label 'DELA' — likely incomplete word
**File**: `VoiceHud.jsx:9`
**Problem**: Fallback label is string `'DELA'`. When `speaking` is true but neither `recording` nor `transcribing`, HUD displays "DELA" — almost certainly meant to be "DELAYING", "SPEAKING", or "PLAYING".

---

## LOW Issues

### L1. Errors silently swallowed — no user feedback
**File**: `useVoiceTTS.js:50-52, 56-58`
Fetch `.catch()` and `audio.onerror` silently call `playNext()` with no `setError` or callback. Consumer has no way to know synthesis/playback failed.

### L2. Sentence regex splits on abbreviation periods
**File**: `useVoiceTTS.js:63`
`/[^.!?]+[.!?]*/g` treats every `.` as sentence boundary. "Mr. Smith went to D.C." splits into `["Mr.", " Smith went to D.", "C."]` — three garbled TTS requests.

### L3. Unpunctuated text sent as single chunk
**File**: `useVoiceTTS.js:63`
If text has no `.!?`, entire string sent as one TTS request, defeating sentence-splitting optimization.

### L4. `speaking` state has no distinct bar color
**File**: `VoiceHud.jsx:9-10, 22`
When speaking, bars use CSS default color. Unlike `--red` for recording or `--amber` for transcribing, no distinct color for speaking state.

### L5. Hardcoded bar count magic number
**File**: `VoiceHud.jsx:4`
`20` is magic number. If CSS keyframes or layout expect different count, visual breakage occurs.

### L6. Unused `audioCtxRef` — dead code
**File**: `useVoiceRecorder.js:23`
Declared but never assigned or read. Header comment says "Uses the Web Audio API" but code uses MediaRecorder exclusively.

### L7. Misleading JSDoc comment: "package as WAV"
**File**: `useVoiceRecorder.js:6-7`
Says recording is packaged as WAV but code produces WebM. Misleads maintainers.

### L8. `error` state has no dismiss mechanism in hook
**File**: `useVoiceRecorder.js`
`error` setter exposed via `clearError` (added in BUG-3 fix), but only called on App mount. No in-session clear.

---

## Areas With Zero Issues
- **Web Audio API integration**: Clean MediaRecorder API usage (modulo missing existence check)
- **Blob URL revocation**: Properly handled in `onended`/`onerror` (except `stop()` bypass)
- **TTS sentence queueing**: Sequential play ordering is correct
