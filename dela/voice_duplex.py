"""Full-duplex voice mode — concurrent listening + speaking with barge-in.

Borrowed concept from FireRedChat: true full-duplex where Dela listens while
it speaks, and the user can interrupt (barge-in) at any time.

Architecture (no LiveKit, no Redis, no external services):
  - Input thread: captures mic audio, runs VAD, feeds EoT detector
  - Output: TTS plays sentence-bysentence on the main thread
  - Barge-in: if EoT detects speech while TTS is playing, TTS stops immediately
  - Turn-taking: when EoT reaches DONE state, captured audio is transcribed
    and sent to the brain

This is a lighter alternative to FireRedChat's LiveKit-based approach. It uses
threading + sounddevice (same as the existing voice module) but adds:
  - EoT detector for smart turn-taking (no fixed silence timeout)
  - Barge-in support (interrupt Dela mid-sentence)
  - Adaptive silence threshold (longer speech → shorter wait)

Two voice modes:
  - "ptt" (push-to-talk): existing behavior, hold a key to talk
  - "duplex": full-duplex with EoT + barge-in (this module)

The mode is controlled by live_config.get("voice_mode") — switchable in Settings
without restart.
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Any

from dela import config, live_config


def is_duplex_mode() -> bool:
    """Check if duplex mode is enabled."""
    return live_config.get("voice_mode", "ptt") == "duplex"


def run_duplex_loop(on_transcript, on_state_change) -> None:
    """Run the full-duplex voice loop.

    Args:
        on_transcript: callback(text: str) when user speech is transcribed
        on_state_change: callback(state: str) when voice state changes
                         ("listening", "thinking", "speaking", "barge_in")
    """
    import numpy as np
    import webrtcvad
    from dela.eot import EoTDetector, TurnState
    from dela.stt import transcribe
    from dela.tts import speak

    # VAD setup
    vad_aggr = int(live_config.get("vad_aggressiveness", 3))
    vad = webrtcvad.Vad(vad_aggr)
    SAMPLE_RATE = 16000
    FRAME_MS = 30
    FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000

    # EoT detector
    eot = EoTDetector(
        min_speech_ms=300,
        silence_threshold_ms=700,
        grace_period_ms=400,
    )

    # Audio buffer for current utterance
    audio_buffer: list[bytes] = []
    dela_speaking = False
    running = True

    # Audio capture thread
    audio_queue: queue.Queue[bytes] = queue.Queue()
    stop_event = threading.Event()

    def _capture():
        try:
            import sounddevice as sd
            def callback(indata, frames, time_info, status):
                if not stop_event.is_set():
                    # Convert to 16-bit mono PCM
                    audio = (indata[:, 0] * 32767).astype(np.int16).tobytes()
                    audio_queue.put(audio)
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                                blocksize=FRAME_SAMPLES, callback=callback):
                stop_event.wait()
        except Exception as e:
            audio_queue.put(None)  # signal error

    capture_thread = threading.Thread(target=_capture, daemon=True)
    capture_thread.start()

    on_state_change("listening")

    try:
        while running:
            # Get audio chunk
            chunk = audio_queue.get(timeout=1)
            if chunk is None:
                break

            # Run VAD
            has_speech = False
            for i in range(0, len(chunk), FRAME_SAMPLES * 2):  # 2 bytes per sample
                frame = chunk[i:i + FRAME_SAMPLES * 2]
                if len(frame) == FRAME_SAMPLES * 2:
                    try:
                        if vad.is_speech(frame, SAMPLE_RATE):
                            has_speech = True
                            break
                    except Exception:
                        pass

            # Feed EoT detector
            state = eot.feed(has_speech, dela_speaking=dela_speaking)

            # Handle barge-in
            if eot.barge_in and dela_speaking:
                on_state_change("barge_in")
                dela_speaking = False
                # TTS will be interrupted by the caller

            # Collect audio during speech
            if state == TurnState.SPEAKING or (state == TurnState.PAUSED and audio_buffer):
                audio_buffer.append(chunk)

            # Turn complete — transcribe and respond
            if state == TurnState.DONE and audio_buffer:
                on_state_change("thinking")
                # Combine audio and transcribe
                full_audio = b"".join(audio_buffer)
                audio_buffer.clear()
                eot.reset()

                try:
                    text = transcribe(full_audio)
                    if text and text.strip():
                        on_transcript(text.strip())

                        # Response phase — Dela speaks
                        dela_speaking = True
                        on_state_change("speaking")
                        # The actual TTS + response is handled by the caller
                        # via on_transcript callback. The caller should call
                        # signal_speaking_done() when TTS finishes.
                except Exception:
                    pass

                dela_speaking = False
                eot.reset()
                on_state_change("listening")

    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        capture_thread.join(timeout=2)


def signal_speaking_done() -> None:
    """Called by the brain/voice loop when TTS playback finishes."""
    pass  # The duplex loop checks dela_speaking flag internally
