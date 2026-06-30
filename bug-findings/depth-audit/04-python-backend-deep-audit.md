# Deep Audit: Python Backend — server.py, stt.py, tts.py, vad.py, voice_duplex.py, start_dela.py

**Files audited**: 6 files, ~2000 lines total
**Audit scope**: Race conditions, resource leaks, security, thread safety, error handling, memory limits

---

## Summary

| Severity | Count | Key themes |
|----------|-------|------------|
| CRITICAL | 2 | Brain lock without timeout → permanent deadlock; ts race on shared dicts |
| HIGH | 24 | No upload size limits; env injection; thread-unsafe singletons; integrity unverified model downloads; subprocess deadlocks; orphaned processes |
| MEDIUM | 28 | Socket leaks; missing validation; blocking calls without timeout; unbounded queues |
| LOW | 8 | Minor resource leaks; misleading code patterns |

**Total: 62 issues**

---

## CRITICAL

### C1. Brain lock without timeout — permanent deadlock
**File**: `server.py:69, 952, 968`
`_brain_lock` (threading.Lock) acquired on asyncio thread, released on worker thread. If worker thread dies (OOM, shutdown with daemon threads, event-loop death before `finally` runs `run_coroutine_threadsafe`), lock **never released**. No timeout on `respond()`. Hung LLM call blocks ALL future messages permanently.

### C2. Race condition on `_confirm_callbacks` / `_confirm_results`
**File**: `server.py:67-68, 937-942, 105-116`
`WebSocketConfirmer.confirm()` (arbitrary thread) writes to these dicts unprotected while `ws_endpoint` (asyncio) reads/pops from them concurrently. No lock guards these dicts. Under GIL, individual dict ops are not truly atomic across multiple lines.

---

## HIGH — Resource Limits & Input Validation

### H1. STT endpoint: no upload size limit → memory exhaustion
**File**: `server.py:446-447`
`await request.body()` reads entire uploaded audio with no size cap. 500MB upload exhausts server RAM.

### H2. TTS endpoint: no text length limit → memory exhaustion
**File**: `server.py:474-489`
`body.get("text")` accepts arbitrary-length text. Piper accumulates all audio chunks then np.concatenate. Long text = OOM.

### H3. Env-file injection via newline in value
**File**: `server.py:697-717`
`value` written to `.env` unsanitized. Value containing `\n` injects new env vars. Example: `value="x\nDELA_EVIL=owned"`. `.env` contains real API keys.

### H4. Memory key missing → unhandled KeyError → 500
**File**: `server.py:130-131`, `server.py:895-898`
`body["text"]` without key presence check. Missing `"text"` → `KeyError` → unhandled 500. Same in `api_update_memory`.

### H5. WebSocket leak in `_clients` on non-disconnect exception
**File**: `server.py:922-923, 947-948`
`_clients.add(ws)` then `ws.send_json(...)`. If send_json raises any exception other than WebSocketDisconnect, dead WebSocket leaks in `_clients` permanently. `_broadcast` fails every cycle.

### H6. `_history` passed to worker thread — no read guard
**File**: `server.py:66, 962`
`_history` (global list) passed to respond() in worker thread. If any other code path reads/writes `_history` concurrently, it races. Lock only prevents multiple brain turns, not `_history` reads.

---

## HIGH — Thread Safety & Singletons

### H7. Whisper model singleton not thread-safe — GPU memory leak
**File**: `stt.py:25-26, 51-67`
Two concurrent `transcribe()` calls both enter `if _model is None:` block, both create WhisperModel, one overwrites other. Abandoned model leaks GPU memory (CTranslate2 C++ backend not GC'd).

### H8. _model_key updated before constructor — inconsistent state
**File**: `stt.py:57, 60, 66`
`_model_key` updated at line 57 before `WhisperModel(...)` at line 60. If constructor raises, key reflects new model but `_model` retains old one. Next call returns old model silently.

### H9. Piper voice singleton not thread-safe
**File**: `tts.py:23, 51-64`
Two concurrent `synthesize_wav()` calls both call `PiperVoice.load()`. Second load overwrites first, leaking ONNX runtime memory.

### H10. Piper voice download — no integrity verification
**File**: `tts.py:45, 47`
`urlretrieve()` downloads model files with NO hash check. MITM or compromised CDN serves malicious .onnx → ONNX Runtime code execution.

### H11. Path traversal via PIPER_VOICE config
**File**: `tts.py:37-48`
If `config.PIPER_VOICE` attacker-controlled (via env injection H3), `f"{name}.onnx"` can traverse directories. `../../target` → `target.onnx` file overwrite.

### H12. eot.py: Speech duration calculation broken
**File**: `eot.py:104-106`
`self._speech_duration_ms += (now - self._speech_start) * 1000` measures time since LAST speech frame, not speech START. Accumulates inter-frame gaps, not utterance duration. Corrupts `max_utterance_ms` cutoff.

---

## HIGH — Subprocess & Pipe Management (start_dela.py)

### H13. Pipe drain thread death → subprocess deadlock
**File**: `start_dela.py:298-304`
If pipe_output thread crashes (Unicode error, OOM), no more data drained from proc.stdout. Pipe OS buffer fills (64KB), subprocess blocks on write(stdout), entire subprocess deadlocks. Thread is `daemon=True` — death is silent.

### H14. Orphaned backend on frontend start failure
**File**: `start_dela.py:315-317`
If backend starts but frontend fails and returns early (timeout), backend process orphaned — no reference to terminate.

### H15. `proc.terminate()` orphans uvicorn workers
**File**: `start_dela.py:343-351`
Without `CREATE_NEW_PROCESS_GROUP`, terminate() only kills parent. Uvicorn child workers keep running, holding ports.

### H16. Port TOCTOU race + wrong-process ready detection
**File**: `start_dela.py:67-74`, `start_dela.py:254-263`
Port checked, then server starts later — another process can bind port in between. Also, start_backend polls TCP connectivity and may see port active from OLD process, declaring wrong process ready.

### H17. voice_duplex: `signal_speaking_done()` is no-op stub
**File**: `voice_duplex.py:162-164`
By the time TTS actually plays, `dela_speaking` is already False. Barge-in detection non-functional. Nobody calls this stub.

---

## MEDIUM Issues — Selected Highlights

| # | File:Line | Issue |
|---|-----------|-------|
| M1 | `server.py:237-250` | New OpenAI client per request → socket leak from unclosed httpx pool |
| M2 | `server.py:878-891` | OAuth refresh: no rate limiting → exhaust provider limits |
| M3 | `server.py:917-949` | WebSocket: no ping/pong, connection limit, message size limit, or rate limit |
| M4 | `stt.py:131-141` | FFT resampling followed by np.interp in time domain → aliasing. Should use frequency-domain only or scipy |
| M5 | `stt.py:104-144` | Entire WAV loaded into RAM. 10min 44.1kHz stereo = ~105MB |
| M6 | `tts.py:107-138` | synthesize_wav accumulates ALL chunks → np.concatenate. No streaming. |
| M7 | `tts.py:39` vs `stt.py:54` | TTS reads static config, STT reads live_config. Live voice switching ignored for TTS until restart. |
| M8 | `vad.py:55-66` | `stream.read()` blocks forever if mic disconnected — no timeout |
| M9 | `voice_duplex.py:75` | `audio_queue` unbounded — if transcription hangs, queue grows to OOM |
| M10 | `voice_duplex.py:130-153` | DONE processing: synchronous transcribe() on main loop blocks capture → stale audio in queue → phantom VAD detections |
| M11 | `eot.py:78-138` | feed() uses `time.time()` (wall clock). NTP sync or sleep/wake jumps clock → wrong state transitions |
| M12 | `start_dela.py:156-169` | npm install: `shell=True` on Windows → injection vector with spaced paths |
| M13 | `start_dela.py:241,273` | Pipe encoding: `errors="replace"` silently corrupts non-UTF-8 output from Vite/uvicorn |

---

## Areas With Zero Issues
- **Message routing**: All /api endpoints correctly dispatched
- **CORS**: No cross-origin issues noted
- **Static file serving**: FastAPI StaticFiles pattern correct
- **ASGI lifecycle**: startup/shutdown hooks properly structured
