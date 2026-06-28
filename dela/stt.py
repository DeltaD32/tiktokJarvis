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

import os
import sys
from pathlib import Path

import numpy as np

from dela import config

_model = None


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
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE,
            download_root=config.MODELS_DIR,
        )
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
