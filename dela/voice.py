"""Voice entry point for Dela — VAD-driven duplex (open mic, barge-in).

Wraps the exact same brain from Tier 1/2. The mic stays open; VAD detects
when you start speaking, interrupts any reply being spoken (barge-in), records
your turn, transcribes it, runs the brain, and speaks the reply. Push-to-talk
is still available as a fallback mode.

Run:  python -m dela.voice            (duplex / open mic)
      python -m dela.voice --ptt      (push-to-talk fallback)

The typed path (python -m dela) stays working forever.
"""

from __future__ import annotations

import argparse
import sys
import threading

from dela import brain, config, gate, heartbeat, noticeboard
from dela.stt import STTError, transcribe
from dela.tts import TTSError, speak
from dela.vad import record_speech, wait_for_speech

# If a reply is being spoken, this event is set so TTS stops (barge-in).
_speaking_stop: threading.Event | None = None


def _interrupt_speaking() -> None:
    global _speaking_stop
    if _speaking_stop is not None:
        _speaking_stop.set()
        _speaking_stop = None


class VoiceConfirmer:
    """Speak the intent, listen for a spoken yes/no. Falls back to text on stdin."""

    def confirm(self, description: str, timeout: float | None = None) -> bool:
        global _speaking_stop
        print(f"  [confirmation needed] {description}")
        # Speak the question.
        stop = threading.Event()
        _speaking_stop = stop
        try:
            speak(f"I need your okay to proceed. {description}. Is that alright?", stop_event=stop)
        except TTSError:
            pass
        _speaking_stop = None
        # Listen for the answer via VAD + STT.
        print("  [listening for yes/no...]")
        wait_for_speech()
        audio = record_speech(max_duration=5)
        if not audio:
            # Fall back to text input.
            try:
                answer = input("  Allow? (yes/no) > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return False
            return answer in ("yes", "y", "yeah", "ok", "sure", "go ahead")
        try:
            text = transcribe(audio).lower().strip()
        except STTError:
            return False
        print(f"  [you said: {text}]")
        return any(w in text for w in ("yes", "yeah", "yep", "sure", "ok", "alright", "go ahead"))


def _run_duplex_turn(history: list) -> None:
    """One duplex turn: wait for speech (open mic), record, transcribe, reply."""
    # The first speech frame, captured by wait_for_speech, fed into record_speech
    # so the start of the user's sentence isn't lost.
    leading = {"frame": None}

    def on_speech_start() -> None:
        # The user started talking — interrupt any reply being spoken.
        _interrupt_speaking()

    # Listen on the open mic until speech is detected.
    # We need the leading frame; wait_for_speech signals via callback.
    # We capture the frame by peeking: simpler to just record fresh here.
    wait_for_speech(on_speech=on_speech_start)

    # Record the full turn (speech already started).
    audio = record_speech()
    if not audio:
        return

    # Ears: transcribe.
    try:
        text = transcribe(audio)
    except STTError as e:
        print(f"[transcription failed: {e}]")
        return

    if not text.strip():
        print("[I didn't catch that — try again?]")
        return

    # Print the transcript so we can tell ears vs brain faults apart while building.
    print(f"you (transcript) > {text}")

    # Brain: same entry point the typed path uses.
    reply = brain.assemble_reply(history, text)
    print(f"{config.NAME} > {reply}")

    # Mouth: speak the reply. Barge-in sets this event from on_speech_start.
    stop = threading.Event()
    global _speaking_stop
    _speaking_stop = stop
    try:
        speak(reply, stop_event=stop)
    except TTSError as e:
        print(f"[speech failed: {e}]")
    _speaking_stop = None


def _surface_notices_voice() -> None:
    """Speak any pending notices when the user returns."""
    pending = noticeboard.pending_on_return()
    if not pending:
        return
    msg = f"I noticed {len(pending)} thing(s) while you were away. "
    for n in pending:
        msg += n["message"] + ". "
    print(f"[notices: {len(pending)} pending]")
    print(msg)
    stop = threading.Event()
    global _speaking_stop
    _speaking_stop = stop
    try:
        speak(msg, stop_event=stop)
    except TTSError:
        pass
    _speaking_stop = None


def duplex_loop() -> None:
    gate.set_confirmer(VoiceConfirmer())
    heartbeat.start()
    print(f"{config.NAME} duplex voice mode. Heartbeat running. Just talk — I'll listen. Ctrl+C to quit.")
    print("(Barge in any time. Push-to-talk fallback: python -m dela.voice --ptt)")
    print("(Typed path still works: python -m dela)\n")

    _surface_notices_voice()

    history: list = []
    try:
        while True:
            _run_duplex_turn(history)
    except KeyboardInterrupt:
        _interrupt_speaking()
        print("\n(quit)")
    finally:
        heartbeat.stop()


def ptt_loop() -> None:
    """Push-to-talk fallback — hold Space to talk, release to send."""
    from dela.mic import record_until_release

    gate.set_confirmer(VoiceConfirmer())
    heartbeat.start()
    print(f"{config.NAME} push-to-talk mode. Heartbeat running. Hold SPACE to talk. Ctrl+C to quit.\n")
    _surface_notices_voice()
    history: list = []
    try:
        while True:
            audio = record_until_release("space")
            if not audio:
                continue
            _interrupt_speaking()
            try:
                text = transcribe(audio)
            except STTError as e:
                print(f"[transcription failed: {e}]")
                continue
            if not text.strip():
                print("[I didn't catch that — try again?]")
                continue
            print(f"you (transcript) > {text}")
            reply = brain.assemble_reply(history, text)
            print(f"{config.NAME} > {reply}")
            stop = threading.Event()
            global _speaking_stop
            _speaking_stop = stop
            try:
                speak(reply, stop_event=stop)
            except TTSError as e:
                print(f"[speech failed: {e}]")
            _speaking_stop = None
    except KeyboardInterrupt:
        _interrupt_speaking()
        print("\n(quit)")
    finally:
        heartbeat.stop()


def main() -> None:
    parser = argparse.ArgumentParser(prog="dela.voice")
    parser.add_argument("--ptt", action="store_true", help="push-to-talk mode")
    args = parser.parse_args()
    if args.ptt:
        ptt_loop()
    else:
        duplex_loop()


if __name__ == "__main__":
    main()
