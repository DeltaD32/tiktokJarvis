"""Text-to-speech seam: give it text, play it aloud.

One function — `speak()` — synthesizes audio via Piper (local, offline, neural)
and plays it through the default output device, sentence by sentence so playback
starts before the full reply is synthesized. Swap voices or providers by
rewriting this module. The voice model is auto-downloaded to DELA_MODELS_DIR
on first use and cached thereafter.
"""

from __future__ import annotations

import io
import threading
import urllib.request
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from dela import config

_voice = None
_voice_name: str | None = None
_voice_lock = threading.Lock()
_VOICE_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def _voice_path(name: str) -> str:
    """Auto-generate the HuggingFace path from a Piper voice name.
    Format: {lang_code}-{voice}-{quality} → {lang_family}/{lang_code}/{voice}/{quality}/{full_name}
    e.g. en_US-amy-medium → en/en_US/amy/medium/en_US-amy-medium
    """
    # Sanitize: only allow alphanumeric, dash, underscore — prevent traversal
    safe = "".join(c for c in name if c.isalnum() or c in "-_.")
    if safe != name or ".." in name:
        raise ValueError(f"Invalid Piper voice name: {name}")
    parts = safe.rsplit("-", 1)
    if len(parts) != 2:
        raise ValueError(f"Cannot parse Piper voice name: {name}")
    voice_quality = parts[1].lower()
    voice_name = parts[0]
    name_parts = voice_name.split("-", 1)
    if len(name_parts) != 2:
        raise ValueError(f"Cannot parse Piper voice name: {name}")
    lang_code = name_parts[0]
    voice_short = name_parts[1].lower()
    lang_family = lang_code.split("_")[0].lower()
    # Validate quality is a known value
    if voice_quality not in ("low", "medium", "high"):
        raise ValueError(f"Unknown Piper voice quality: {voice_quality}")
    return f"{lang_family}/{lang_code}/{voice_short}/{voice_quality}/{safe}"


def _voice_dir() -> Path:
    d = Path(config.MODELS_DIR) / "piper"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ensure_voice() -> Path:
    """Download the .onnx + .json for the configured voice if missing."""
    from dela import live_config
    name = live_config.get("piper_voice") or config.PIPER_VOICE
    rel = _voice_path(name)
    onnx_path = _voice_dir() / f"{name}.onnx"
    cfg_path = _voice_dir() / f"{name}.onnx.json"

    def _download(url: str, dest: Path, label: str, expected_min_bytes: int = 1000) -> None:
        if dest.exists():
            size = dest.stat().st_size
            if size < expected_min_bytes:
                print(f"[removing truncated {label}: {size} bytes]")
                dest.unlink()
            else:
                return  # already downloaded
        print(f"[downloading Piper {label}: {name} (~60MB, one-time)]")
        # Download with timeout; verify file starts with valid header
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        # ONNX files start with protobuf magic; JSON with '{'
        if label == "voice":
            if len(data) < 4 or data[:4] != b'\x08\x08\x12\x08':
                raise RuntimeError(f"Downloaded ONNX file has invalid header — possible corruption")
        elif label == "config":
            if len(data) < 2 or data[0:1] != b'{':
                raise RuntimeError(f"Downloaded config is not JSON — possible corruption")
        dest.write_bytes(data)

    _download(f"{_VOICE_BASE}/{rel}.onnx", onnx_path, "voice", expected_min_bytes=50_000_000)
    _download(f"{_VOICE_BASE}/{rel}.onnx.json", cfg_path, "config", expected_min_bytes=100)
    return onnx_path


def _piper():
    global _voice, _voice_name
    from dela import live_config
    current_name = live_config.get("piper_voice") or config.PIPER_VOICE
    if _voice is None or _voice_name != current_name:
        with _voice_lock:
            if _voice is None or _voice_name != current_name:  # double-check
                from piper import PiperVoice
                onnx = _ensure_voice()
                try:
                    import onnxruntime as ort
                    has_cuda = "CUDAExecutionProvider" in ort.get_available_providers()
                except Exception:
                    has_cuda = False
                _voice = PiperVoice.load(onnx, use_cuda=has_cuda)
                _voice_name = current_name
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


def synthesize_wav(text: str) -> bytes:
    """Synthesize text to WAV bytes (16-bit PCM, mono) for web playback.

    Unlike speak() which plays through sounddevice, this returns the audio
    as a WAV file suitable for HTTP response / browser playback.
    """
    if not text.strip():
        return b""

    try:
        voice = _piper()
        all_audio: list[np.ndarray] = []
        sample_rate = 22050  # piper default, updated from first chunk

        for chunk in voice.synthesize(text):
            sample_rate = chunk.sample_rate
            audio_int16 = (chunk.audio_float_array * 32767).astype(np.int16)
            all_audio.append(audio_int16)

        if not all_audio:
            return b""

        combined = np.concatenate(all_audio)

        # Write to WAV in memory
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(sample_rate)
            wav.writeframes(combined.tobytes())
        return buf.getvalue()

    except Exception as e:
        raise TTSError(f"Piper synthesis failed: {e}") from e
