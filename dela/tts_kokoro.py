"""Kokoro TTS provider — high-fidelity local neural TTS (82M params, 24kHz).

Kokoro-82M is an open-weight StyleTTS2-based model that produces near-studio-quality
speech. It's local, offline, and runs on CPU at interactive speed (~2x real-time).

Usage is identical to the Piper TTS seam:
    from dela.tts_kokoro import synthesize_wav
    wav_bytes = synthesize_wav("Hello world")
    # Returns 24kHz 16-bit mono WAV bytes

Voices (American English):
    af_heart, af_bella, af_nicole, af_sarah, af_sky  (female)
    am_adam, am_michael, am_eric                       (male)

The model (~330MB) is auto-downloaded from HuggingFace on first use and cached
under DELA_MODELS_DIR/kokoro/.
"""

from __future__ import annotations

import io
import threading
import urllib.request
import wave
from pathlib import Path

import numpy as np

from dela import config

_pipeline = None
_pipeline_lock = threading.Lock()
_KOKORO_SAMPLE_RATE = 24000

# Voice names from hexgrad/Kokoro-82M
_VOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky",
    "am_adam", "am_michael", "am_eric",
]


def _model_dir() -> Path:
    d = Path(config.MODELS_DIR) / "kokoro"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ensure_kokoro():
    """Lazy-load the Kokoro pipeline. Downloads model files on first use."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    with _pipeline_lock:
        if _pipeline is not None:  # double-check
            return _pipeline

        try:
            from kokoro import KPipeline
        except ImportError:
            raise RuntimeError(
                "Kokoro is not installed. Run: pip install kokoro"
            )

        # Set cache dir so model files go to our models directory
        import os
        os.environ.setdefault("KOKORO_CACHE_DIR", str(_model_dir()))

        _pipeline = KPipeline(lang_code="a")  # American English
        return _pipeline


def synthesize_wav(text: str, voice: str = "af_heart") -> bytes:
    """Synthesize text to WAV bytes (16-bit PCM, 24kHz, mono).

    Args:
        text: The text to synthesize.
        voice: Kokoro voice name (default: af_heart).
               See _VOICES for available options.

    Returns:
        WAV file as bytes, or empty bytes if text is empty.
    """
    if not text.strip():
        return b""

    if voice not in _VOICES:
        voice = "af_heart"  # fallback

    pipeline = _ensure_kokoro()

    # Collect all audio chunks into one array
    chunks: list[np.ndarray] = []
    try:
        for _gs, _ps, audio in pipeline(text, voice=voice, speed=1):
            chunks.append(audio)
    except Exception as e:
        raise RuntimeError(f"Kokoro synthesis failed: {e}") from e

    if not chunks:
        return b""

    combined = np.concatenate(chunks)
    # Convert float32 [-1,1] to int16 PCM
    pcm = (combined * 32767).clip(-32768, 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(_KOKORO_SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())
    return buf.getvalue()


def available_voices() -> list[str]:
    """Return the list of available Kokoro voice names."""
    return list(_VOICES)
