"""Voice Activity Detection (VAD) for duplex interaction.

Two jobs:
  1. `wait_for_speech()` — block until the user starts speaking (open mic,
     VAD-triggered). Used while Dela is idle or speaking so you can barge in.
  2. `record_speech()` — record until the user stops speaking, return PCM.

Both use webrtcvad on a live mic stream. This is what gives the *experience*
of full-duplex (listen-while-speaking, barge-in) without a giant speech model:
the mic stays open, VAD decides when a real turn starts, and a speaking-stop
event can be set instantly to cut off TTS.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

import numpy as np
import sounddevice as sd
import webrtcvad

from dela import config

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000  # 480 samples per 30ms frame
FRAME_BYTES = FRAME_SAMPLES * 2  # 16-bit mono


def _vad() -> webrtcvad.Vad:
    return webrtcvad.Vad(config.VAD_AGGRESSIVENESS)


def _is_speech(vad: webrtcvad.Vad, frame: bytes) -> bool:
    if len(frame) < FRAME_BYTES:
        return False
    try:
        return vad.is_speech(frame[:FRAME_BYTES], SAMPLE_RATE)
    except Exception:
        return False


def wait_for_speech(
    stop_event: threading.Event | None = None,
    on_speech: Callable[[], None] | None = None,
) -> None:
    """Block on the mic until speech is detected, then return.

    If `stop_event` is set, returns immediately (used to stop listening).
    `on_speech` is called the moment speech is detected — e.g. to interrupt TTS.
    """
    vad = _vad()
    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=FRAME_SAMPLES
    ) as stream:
        while True:
            if stop_event is not None and stop_event.is_set():
                return
            frame, _ = stream.read(FRAME_SAMPLES)
            pcm = frame.tobytes()
            if _is_speech(vad, pcm):
                if on_speech is not None:
                    on_speech()
                return


def record_speech(
    max_duration: float = 15.0,
    silence_pad: float = 0.8,
    stop_event: threading.Event | None = None,
    leading_frame: bytes | None = None,
) -> bytes:
    """Record until the user stops speaking. Returns 16-bit mono PCM.

    Starts recording immediately (speech has already been detected). Records
    until `silence_pad` seconds of continuous silence after speech, or until
    `max_duration`, or until `stop_event` is set.
    `leading_frame` is the first speech frame from wait_for_speech, if any.
    """
    vad = _vad()
    frames: list[np.ndarray] = []
    silence_frames_needed = int(silence_pad * 1000 / FRAME_MS)
    silence_count = 0
    start = time.monotonic()

    if leading_frame is not None:
        frames.append(np.frombuffer(leading_frame, dtype=np.int16))

    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=FRAME_SAMPLES
    ) as stream:
        while True:
            if stop_event is not None and stop_event.is_set():
                break
            if time.monotonic() - start > max_duration:
                break
            frame, _ = stream.read(FRAME_SAMPLES)
            pcm = frame.tobytes()
            frames.append(frame.copy())
            if _is_speech(vad, pcm):
                silence_count = 0
            else:
                silence_count += 1
                if silence_count >= silence_frames_needed and len(frames) > silence_count:
                    break

    if not frames:
        return b""
    return np.concatenate(frames).tobytes()
