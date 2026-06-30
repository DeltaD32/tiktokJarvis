"""End-of-Turn (EoT) detector — borrowed concept from FireRedChat.

FireRedChat uses a trained turn-detector model. We use a simpler heuristic
approach that's good enough for single-user local use:

1. **Silence duration**: VAD reports no speech for N ms (configurable)
2. **Minimum speech**: user spoke for at least M ms (filters coughs/noises)
3. **Natural pause**: after a sufficient speech segment, a shorter silence
   counts as end-of-turn (adaptive based on speech length)

This is NOT a neural model — it's a state machine that tracks speech/silence
transitions and decides when the user has finished talking. It runs alongside
VAD and provides barge-in support for full-duplex mode.

States:
  IDLE     → waiting for speech
  SPEAKING → user is talking
  PAUSED   → user stopped, but might continue (grace period)
  DONE     → user finished — trigger response

Barge-in:
  When Dela is speaking (TTS active) and the EoT detector sees SPEAKING,
  it signals the voice loop to stop TTS and listen.
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Any


class TurnState(Enum):
    IDLE = "idle"
    SPEAKING = "speaking"
    PAUSED = "paused"
    DONE = "done"

FRAME_MS = 30  # VAD frame duration in ms — must match vad.py


class EoTDetector:
    """State machine that detects when the user has finished speaking."""

    def __init__(
        self,
        min_speech_ms: int = 300,
        silence_threshold_ms: int = 700,
        grace_period_ms: int = 400,
        max_utterance_ms: int = 30_000,
    ):
        self.min_speech_ms = min_speech_ms
        self.silence_threshold_ms = silence_threshold_ms
        self.grace_period_ms = grace_period_ms
        self.max_utterance_ms = max_utterance_ms

        self._state = TurnState.IDLE
        self._last_speech_frame: float = 0
        self._speech_duration_ms: float = 0
        self._silence_start: float = 0
        self._last_vad_speech: bool = False
        self._barge_in_triggered: bool = False

    @property
    def state(self) -> TurnState:
        return self._state

    @property
    def barge_in(self) -> bool:
        """True if the user started speaking while Dela was speaking (interrupt)."""
        return self._barge_in_triggered

    def reset(self) -> None:
        self._state = TurnState.IDLE
        self._last_speech_frame = 0
        self._speech_duration_ms = 0
        self._silence_start = 0
        self._last_vad_speech = False
        self._barge_in_triggered = False

    def feed(self, vad_speech: bool, dela_speaking: bool = False, timestamp: float | None = None) -> TurnState:
        """Feed a VAD frame. Returns the current state.

        Args:
            vad_speech: True if VAD detected speech in this frame
            dela_speaking: True if Dela's TTS is currently playing
            timestamp: current time (defaults to time.monotonic())
        """
        now = timestamp or time.monotonic()

        # Detect barge-in: user speaks while Dela is speaking
        if dela_speaking and vad_speech and not self._last_vad_speech:
            self._barge_in_triggered = True
            self._state = TurnState.SPEAKING
            self._last_speech_frame = now
            self._speech_duration_ms = 0
            return self._state

        # State machine
        if self._state == TurnState.IDLE:
            if vad_speech:
                self._state = TurnState.SPEAKING
                self._last_speech_frame = now
                self._speech_duration_ms = 0

        elif self._state == TurnState.SPEAKING:
            if vad_speech:
                self._speech_duration_ms += FRAME_MS  # each VAD frame is FRAME_MS
                self._last_speech_frame = now
                if self._speech_duration_ms > self.max_utterance_ms:
                    self._state = TurnState.DONE
            else:
                self._state = TurnState.PAUSED
                self._silence_start = now

        elif self._state == TurnState.PAUSED:
            if vad_speech:
                self._state = TurnState.SPEAKING
                self._last_speech_frame = now
            else:
                silence_ms = (now - self._silence_start) * 1000
                adaptive_threshold = self.silence_threshold_ms
                if self._speech_duration_ms > 5000:
                    adaptive_threshold = self.grace_period_ms

                if silence_ms >= adaptive_threshold:
                    if self._speech_duration_ms >= self.min_speech_ms:
                        self._state = TurnState.DONE
                    else:
                        self._state = TurnState.IDLE

        elif self._state == TurnState.DONE:
            # Stay done until reset() is called
            pass

        self._last_vad_speech = vad_speech
        return self._state

    def status(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "speech_duration_ms": round(self._speech_duration_ms, 0),
            "barge_in": self._barge_in_triggered,
            "min_speech_ms": self.min_speech_ms,
            "silence_threshold_ms": self.silence_threshold_ms,
        }
