"""Push-to-talk audio capture: hold Spacebar to record, release to stop.

Returns 16-bit mono PCM at 16 kHz — the format Deepgram expects. Push-to-talk
removes a whole class of "is it listening?" bugs: we never guess when the user
started or finished.
"""

from __future__ import annotations

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHUNK = 1024


def record_until_release(key: str = "space") -> bytes:
    """Block until `key` is pressed, record while it's held, return PCM on release."""
    import keyboard

    # Wait for press, then capture until release.
    keyboard.wait(key)
    frames: list[np.ndarray] = []

    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=CHUNK
    ) as stream:
        while keyboard.is_pressed(key):
            chunk, _ = stream.read(CHUNK)
            frames.append(chunk.copy())

    if not frames:
        return b""
    audio = np.concatenate(frames)
    return audio.tobytes()
