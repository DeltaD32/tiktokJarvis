# GUI-BUG-1: STT returns empty for real speech audio

**Severity**: Medium
**Found**: 2026-06-29, GUI visual audit
**Files**: `dela/stt.py`, `dela/server.py:441-471`

## Reproduction

1. POST any real speech WAV to `/api/voice/stt`
2. Response is `{"text":"","ok":true}` — empty transcription

Tested with:
- TTS-synthesized "hello" (Piper `en_US-amy-medium`, 22050Hz, 16-bit, mono) → empty
- TTS-synthesized "the quick brown fox jumps over the lazy dog" → empty
- Sine tone → empty (expected — not speech)

## Root Cause Hypothesis

The `faster-whisper small.en` model with `vad_filter=True` is returning 0 segments for Piper TTS audio. Possible reasons:

1. **VAD filter**: The Voice Activity Detection filter may be too aggressive for synthetic speech, filtering all audio as non-speech.
2. **Resampling quality**: Linear interpolation from 22050→16000Hz may introduce artifacts that confuse whisper.
3. **Piper voice quality**: The `en_US-amy-medium` model at 22050Hz produces audio outside whisper's training distribution (whisper was trained on 16kHz natural speech).

## Suggested Fixes

### Fix 1: Disable VAD for TTS audio
In `dela/stt.py:81-83`:
```python
segments, _ = _whisper().transcribe(
    audio, language="en", beam_size=5, vad_filter=False  # Changed from True
)
```

### Fix 2: Improve resampling
Replace linear interpolation with proper resampling:
```python
from scipy.signal import resample_poly
if framerate != target_rate:
    audio = resample_poly(audio, target_rate, framerate)
```

### Fix 3: Change Piper sample rate
Configure Piper to output at 16000Hz natively (check if the model supports it).

### Fix 4: Add transcription debug logs
```python
segments, info = _whisper().transcribe(audio, ...)
print(f"  [stt] segments: {len(list(segments))}, info: {info}")
```

## Verification

1. Apply fix
2. POST TTS audio ("hello") to `/api/voice/stt`
3. Should return `{"text":"hello","ok":true}`
4. Test with browser voice recorder (real mic)
