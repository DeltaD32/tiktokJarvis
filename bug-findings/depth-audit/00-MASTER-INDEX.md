# Dela Deep Audit — Master Index

**Date**: 2026-06-29  
**Scope**: 10 files, ~4500 lines of code across frontend and backend  
**Method**: Static code analysis (line-by-line) + Playwright stress tests + Python standalone tests  

---

## Audit Documents

| # | Document | Scope | Issues Found |
|---|----------|-------|-------------|
| 01 | [useDelaWS.js Deep Audit](01-useDelaWS-deep-audit.md) | WebSocket hook (229 lines) | **25** (5 critical, 2 high, 10 medium, 8 low) |
| 02 | [App.jsx Deep Audit](02-App-jsx-deep-audit.md) | Main app component (509 lines) | **30** (2 high, 6 medium, 20 low, 2 info) |
| 03 | [Voice Hooks Deep Audit](03-voice-hooks-deep-audit.md) | Recorder + TTS + HUD (247 lines) | **20** (2 critical, 5 high, 6 medium, 7 low) |
| 04 | [Python Backend Deep Audit](04-python-backend-deep-audit.md) | 6 files, ~2000 lines | **62** (2 critical, 24 high, 28 medium, 8 low) |
| 05 | [Perf, Accessibility, Security](05-perf-accessibility-security.md) | Cross-cutting concerns | **23** findings |

**Total: 160 issues**

---

## Severity Breakdown

| Severity | Frontend | Backend | Total |
|----------|----------|---------|-------|
| CRITICAL | 5 | 2 | **7** |
| HIGH | 7 | 24 | **31** |
| MEDIUM | 22 | 28 | **50** |
| LOW | 36 | 8 | **44** |
| INFO | 2 | 0 | **2** |

---

## Top 10 Critical/High Issues to Fix First

### 1. CRITICAL — `_processingTurn` permanent deadlock (useDelaWS.js)
If WebSocket drops mid-turn, send is locked forever. No timeout, no watchdog, no reconnection reset. Affects every user session.

### 2. CRITICAL — Brain lock without timeout (server.py)
`threading.Lock` on asyncio thread, released on worker thread. If worker dies, all message processing deadlocks permanently.

### 3. CRITICAL — Dead FormData / wrong Content-Type (useVoiceRecorder.js)  
formData constructed but blob sent directly with wrong MIME type. STT endpoint gets mismatched content.

### 4. HIGH — No upload size limits on STT/TTS (server.py)
500MB audio upload or 100KB text OOMs the server. Add `MAX_UPLOAD_SIZE` / `MAX_TEXT_LENGTH`.

### 5. HIGH — Env-file injection via newline (server.py)
`value` written to `.env` unsanitized. Attacker injects new env vars. `.env` contains real API keys.

### 6. HIGH — Thread-unsafe model singletons (stt.py, tts.py)
Concurrent whisper/Piper calls create duplicate models, leaking GPU memory. Add `threading.Lock()`.

### 7. HIGH — Runtime theme switching broken (App.jsx + themes.js)
`ACCENT_RGB` holds stale colors after theme switch. Orb state changes revert accent to old theme. Requires page reload.

### 8. HIGH — Pipe drain thread death deadlocks subprocess (start_dela.py)
If pipe_output thread crashes, stdout stops draining, subprocess blocks, whole app hangs. Thread is daemon=True.

### 9. HIGH — Orphaned processes on shutdown (start_dela.py)
`terminate()` without `CREATE_NEW_PROCESS_GROUP` orphans uvicorn child workers. Ports remain held.

### 10. HIGH — `signal_speaking_done()` is no-op stub (voice_duplex.py)
Barge-in detection for duplex voice mode is completely non-functional. TTS/detection sync broken.

---

## File-by-File Health Score

| File | Health | Key Weakness |
|------|--------|-------------|
| `useDelaWS.js` | ⚠️ Fair | `_processingTurn` deadlock risk; no state reset on disconnect |
| `App.jsx` | ✅ Good | Missing memoization; theme switch bug; fetch race condition |
| `useVoiceRecorder.js` | ❌ Poor | Dead FormData; no MediaRecorder check; stream leaks; Safari unsupported |
| `useVoiceTTS.js` | ⚠️ Fair | Stale audio after stop; no cleanup on unmount; no queue limit |
| `VoiceHud.jsx` | ⚠️ Fair | Math.random() in render causes jank; truncated label |
| `server.py` | ⚠️ Fair | No input limits; lock timeout risk; env injection; WebSocket leaks |
| `stt.py` | ✅ Good | Thread-unsafe singleton; memory for large files |
| `tts.py` | ⚠️ Fair | Thread-unsafe singleton; no integrity verification; path traversal |
| `vad.py` | ✅ Good | Blocking read without timeout |
| `voice_duplex.py` | ❌ Poor | Barge-in stub; synchronous transcribe blocks capture; unbounded queue |
| `eot.py` | ⚠️ Fair | Speech duration calculation broken; wall-clock dependency |
| `start_dela.py` | ⚠️ Fair | Pipe deadlock risk; orphaned processes; TOCTOU races |

---

## Patterns & Anti-patterns Found

### Systemic Issues
1. **No timeouts anywhere** — WebSocket messages, STT transcription, TTS synthesis, model downloads, brain turns, mic reads, pipe drains. Any of these hanging blocks the entire system.
2. **Thread safety ignored** — Model singletons (whisper, Piper), dict mutations, lock ownership across threads. All rely on "only one user" assumption.
3. **Unbounded growth** — streamBuffer, audio_queue, chunks list, all_audio list, _clients set. No caps anywhere.
4. **Silent error swallowing** — `.catch(() => {})` everywhere, empty try/catch blocks, no error logging. Debugging requires adding print statements.
5. **Cleanup gaps** — useEffect without return, blob URLs not revoked, WebSocket listeners not removed, subprocesses not killed.

### Good Patterns
1. `connIdRef` stale-connection guard in useDelaWS — correct pattern for StrictMode safety
2. `msgIdRef` counter instead of Date.now() — avoids duplicate keys
3. FFT-based resampling in stt.py — better quality than linear (modulo the time-domain interpolation)
4. `_bytes_to_float` normalization — correct PCM→float conversion
5. Canvas DPR cap at 2 — prevents GPU overwork on high-DPI screens

---

## Related Documents

- `../AUDIT-SUMMARY.md` — Original functional audit (74 tests)
- `../GUI-VISUAL-AUDIT.md` — Visual/theme/responsive audit
- `../BUG-001*.md` through `../GUI-BUG-003*.md` — Individual bug reports (7 fixed)
- `../TEST-CASES.md` — All 42 functional test cases
- `../WARNINGS.md` — 3 cosmetic warnings
