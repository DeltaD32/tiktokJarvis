"""Text-to-speech seam: give it text, play it aloud.

One function — `speak()` — synthesizes audio via Piper (local, offline, neural)
and plays it through the default output device, sentence by sentence so playback
starts before the full reply is synthesized. Swap voices or providers by
rewriting this module. The voice model is auto-downloaded to DELA_MODELS_DIR
on first use and cached thereafter.
"""

from __future__ import annotations

import threading
import urllib.request
from pathlib import Path

import numpy as np
import sounddevice as sd

from dela import config

_voice = None
_VOICE_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
_VOICE_PATHS = {
    "en_US-amy-medium": "en/en_US/amy/medium/en_US-amy-medium",
    "en_US-ryan-medium": "en/en_US/ryan/medium/en_US-ryan-medium",
}


def _voice_dir() -> Path:
    d = Path(config.MODELS_DIR) / "piper"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ensure_voice() -> Path:
    """Download the .onnx + .json for the configured voice if missing."""
    name = config.PIPER_VOICE
    rel = _VOICE_PATHS.get(name, name)
    onnx = _voice_dir() / f"{name}.onnx"
    cfg = _voice_dir() / f"{name}.onnx.json"
    if not onnx.exists():
        print(f"[downloading Piper voice: {name} (~60MB, one-time)]")
        urllib.request.urlretrieve(f"{_VOICE_BASE}/{rel}.onnx", onnx)
    if not cfg.exists():
        urllib.request.urlretrieve(f"{_VOICE_BASE}/{rel}.onnx.json", cfg)
    return onnx


def _piper():
    global _voice
    if _voice is None:
        from piper import PiperVoice

        onnx = _ensure_voice()
        # use_cuda only if onnxruntime has the CUDA provider; else CPU (still fast).
        try:
            import onnxruntime as ort
            has_cuda = "CUDAExecutionProvider" in ort.get_available_providers()
        except Exception:
            has_cuda = False
        _voice = PiperVoice.load(onnx, use_cuda=has_cuda)
    return _voice


class TTSError(RuntimeError):
    """Raised when synthesis fails — the loop shows a clean message."""


def speak(text: str, stop_event: threading.Event | None = None) -> None:
    """Synthesize `text` and play it aloud, sentence by sentence.

    Streaming by sentence means Dela starts speaking the first sentence while
    the rest is still being synthesized. If `stop_event` is set (by a barge-in
    turn), playback stops promptly at the next sentence boundary.
    """
    if not text.strip():
        return

    try:
        voice = _piper()
        # Open the output stream on the first chunk so we know the sample rate.
        stream = None
        try:
            for chunk in voice.synthesize(text):
                if stop_event is not None and stop_event.is_set():
                    break
                if stream is None:
                    stream = sd.RawOutputStream(
                        samplerate=chunk.sample_rate,
                        channels=chunk.sample_channels,
                        dtype="int16",
                        blocksize=2048,
                    )
                    stream.start()
                audio_int16 = (chunk.audio_float_array * 32767).astype(np.int16)
                stream.write(audio_int16.tobytes())
        finally:
            if stream is not None:
                stream.stop()
                stream.close()
    except Exception as e:
        raise TTSError(f"Piper synthesis failed: {e}") from e
