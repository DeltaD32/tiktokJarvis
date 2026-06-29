"""Speech-to-text seam: give it audio bytes, get back text.

One function — `transcribe()` — is the only thing the rest of the harness
calls. Swap transcribers by rewriting this module; nothing else changes.
Uses faster-whisper (Whisper on CTranslate2) — local, offline.
The model is downloaded to DELA_MODELS_DIR on first use and cached thereafter.

Note: GPU (CUDA) requires the CUDA Toolkit (cuBLAS/cuDNN DLLs), not just the
driver. If unavailable, set DELA_WHISPER_DEVICE=cpu — small.en on CPU int8 is
fast enough for real-time push-to-talk and duplex.
"""

from __future__ import annotations

import io
import os
import sys
import wave
from pathlib import Path

import numpy as np

from dela import config

_model = None
_model_key: tuple[str, str, str] | None = None


def _ensure_cuda_dlls() -> None:
    """Add pip-installed NVIDIA CUDA DLLs (cublas/cudnn) to the DLL search path.

    CTranslate2 loads cublas64_12.dll / cudnn64_9.dll at inference time. The
    pip wheels ship them under nvidia/*/bin but don't put them on PATH. We add
    those dirs to os.environ["PATH"] before importing faster-whisper so Windows
    can find them. No-op if the wheels aren't installed (CPU fallback handles it).
    """
    sp = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if not sp.exists():
        return
    dll_dirs = [
        sp / "cublas" / "bin",
        sp / "cudnn" / "bin",
        sp / "cuda_nvrtc" / "bin",
    ]
    for d in dll_dirs:
        if d.exists():
            os.add_dll_directory(str(d))
            os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")


def _whisper():
    global _model, _model_key
    from dela import live_config
    model_name = live_config.get("whisper_model") or config.WHISPER_MODEL
    device = live_config.get("whisper_device") or config.WHISPER_DEVICE
    compute = config.WHISPER_COMPUTE
    key = (model_name, device, compute)
    if _model is None or _model_key != key:
        from faster_whisper import WhisperModel
        _model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute,
            download_root=config.MODELS_DIR,
        )
        _model_key = key
    return _model


class STTError(RuntimeError):
    """Raised when transcription fails — the loop shows a clean message."""


_ensure_cuda_dlls()


def transcribe(audio_bytes: bytes, *, sample_rate: int = 16000) -> str:
    """Transcribe recorded audio (16-bit PCM mono) and return the text."""
    audio = _bytes_to_float(audio_bytes)
    try:
        segments, _ = _whisper().transcribe(
            audio, language="en", beam_size=5, vad_filter=True
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
    except Exception as e:
        raise STTError(f"Transcription failed: {e}") from e


def _bytes_to_float(pcm: bytes) -> np.ndarray:
    """16-bit mono PCM -> float32 normalized to [-1, 1] for faster-whisper."""
    arr = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    return arr


def wav_to_pcm(wav_bytes: bytes, target_rate: int = 16000) -> bytes:
    """Parse a WAV file and return raw 16-bit PCM mono at target_rate.

    Handles any sample rate / channel count from the browser's MediaRecorder.
    Resamples using linear interpolation (good enough for speech).
    """
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        n_channels = wav.getnchannels()
        sampwidth = wav.getsampwidth()
        framerate = wav.getframerate()
        n_frames = wav.getnframes()
        raw = wav.readframes(n_frames)

    if sampwidth != 2:
        raise STTError(f"Expected 16-bit WAV, got {sampwidth * 8}-bit")

    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)

    # Mix to mono if needed
    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)

    # Resample to target_rate if needed
    if framerate != target_rate:
        old_len = len(audio)
        new_len = int(old_len * target_rate / framerate)
        indices = np.linspace(0, old_len - 1, new_len)
        audio = np.interp(indices, np.arange(old_len), audio)

    # Back to 16-bit PCM bytes
    return (audio * 32767).astype(np.int16).tobytes()
