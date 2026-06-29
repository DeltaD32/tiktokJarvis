---
title: Voice
nav_order: 5
---

# Voice Stack

Fully local, no API keys, no per-call cost.

| Component | Technology | Role |
|---|---|---|
| Speech-to-text | faster-whisper (Whisper on CTranslate2) | `stt.py` — transcribe audio to text |
| Text-to-speech | Piper (neural, ONNX) | `tts.py` — synthesize and play text aloud |
| Voice activity detection | webrtcvad | `vad.py` — detect speech for duplex/barge-in |
| EoT detector | State machine (custom) | `eot.py` — smart turn-taking |
| Audio I/O | sounddevice + numpy | mic capture and speaker playback |
| Web audio | MediaRecorder + WAV | `useVoiceRecorder.js` / `useVoiceTTS.js` |

## GPU Notes

- **STT (faster-whisper):** Runs on CUDA (float16) if NVIDIA CUDA Toolkit DLLs are available. The pip wheels provide them. If unavailable, set `DELA_WHISPER_DEVICE=cpu`.
- **TTS (Piper):** Runs on CPU via ONNX Runtime. Piper is lightweight enough that GPU isn't needed.
- **Model downloads:** Whisper `small.en` (~244 MB) and Piper voice (~60 MB) are downloaded automatically on first use and cached under `models/`.

## Web Voice I/O

The web UI supports voice through REST endpoints (no WebSocket needed for audio):

- **Recording:** `MediaRecorder` captures mic audio → `POST /api/voice/stt` (audio/webm or WAV) → `wav_to_pcm()` resamples to 16kHz → faster-whisper transcribes → returns text
- **Playback:** Text → `POST /api/voice/tts` → Piper synthesizes → WAV bytes → browser `Audio` element plays
- **Sentence streaming:** TTS splits text into sentences and plays them sequentially for lower latency
- **ffmpeg fallback:** If the browser sends non-WAV audio (webm/opus), ffmpeg converts it

---

## EoT Detector & Duplex Voice

Borrowed concepts from FireRedChat (pVAD, EoT detection, barge-in) — implemented locally without LiveKit, Redis, or Docker.

### EoT Detector (`dela/eot.py`)

A state machine that detects when the user has finished speaking:

```
IDLE → SPEAKING → PAUSED → DONE
```

- **Adaptive silence threshold:** Longer speech = shorter wait. Someone who talked for 5s probably finished if they pause for 400ms; someone who talked for 300ms needs 700ms silence.
- **Min speech filter:** Ignores sounds shorter than 300ms (coughs, clicks).
- **Barge-in detection:** If user speaks while Dela speaks → interrupt signal.
- **Max utterance safety:** 30s cap.
- Not a neural model — pure heuristic state machine, no dependency.

### Duplex Voice Mode (`dela/voice_duplex.py`)

Full-duplex without LiveKit:

- Concurrent mic capture + TTS playback via threading
- EoT detector for smart turn-taking (no fixed silence timeout)
- Barge-in: user can interrupt Dela mid-sentence
- Uses same `sounddevice` stack as existing voice module
- Controlled by `voice_mode` live setting: `"ptt"` or `"duplex"`
- Switchable in Settings → Voice without restart

### What we kept (vs. FireRedChat)

- **faster-whisper** (lighter than FireRedASR)
- **Piper** (lighter than FireRedTTS)
- **webrtcvad** (EoT detector adds the intelligence layer on top)

The key insight: turn detection and barge-in are what make duplex feel natural — not the specific infrastructure. Those are solved with a state machine + threading, not LiveKit + Redis.
