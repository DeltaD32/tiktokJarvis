"""Text entry point for Dela.

This is the Tier 1 interface and stays forever as the debug/fallback path.
Run:  python -m dela  (after `pip install -r requirements.txt` and a filled .env)

Also starts the heartbeat (Tier 5) in the background, surfaces pending notices,
and wires in the confirmation gate (Tier 6) so consequential actions ask first.

Commands:
  notices          — list pending notices
  dismiss <id>     — dismiss one notice
  clear notices    — dismiss all notices
  pause heartbeat  — kill switch (stop all proactive behavior)
  resume heartbeat — clear the kill switch
  audit            — show the last lines of the audit log
  cost             — show the running model cost tally
"""

from dela import audit, brain, config, gate, heartbeat, noticeboard
from dela.brain import assemble_reply


def _surface_notices() -> None:
    pending = noticeboard.pending_on_return()
    if not pending:
        return
    print(f"\n--- {config.NAME} noticed {len(pending)} thing(s) while you were away ---")
    for n in pending:
        flag = {"urgent": "URGENT", "attention": "attention", "info": "info"}[n["severity"]]
        print(f"  [{flag}] {n['message']}")
    print(f"  (dismiss with: clear notices, or dismiss {pending[0]['id']})\n")


def _handle_commands(text: str) -> bool:
    """Return True if the input was a built-in command (already handled)."""
    t = text.lower().strip()

    if t in ("clear notices", "dismiss all", "clear"):
        count = noticeboard.dismiss_all()
        print(f"[dismissed {count} notice(s).]")
        return True
    if t.startswith("dismiss "):
        try:
            nid = int(t.split()[1])
        except (IndexError, ValueError):
            return False
        if noticeboard.dismiss(nid):
            print(f"[dismissed notice {nid}.]")
        else:
            print(f"[no notice with id {nid}.]")
        return True
    if t == "notices":
        active = noticeboard.active()
        if not active:
            print("[no pending notices.]")
        else:
            for n in active:
                flag = {"urgent": "URGENT", "attention": "attention", "info": "info"}[n["severity"]]
                print(f"  [{n['id']}|{flag}] {n['message']}")
        return True
    if t in ("pause heartbeat", "pause", "kill switch"):
        heartbeat.kill()
        audit.kill_switch("paused")
        print("[heartbeat paused — all proactive behavior stopped. "
              "Say 'resume heartbeat' to restart.]")
        return True
    if t in ("resume heartbeat", "resume"):
        heartbeat.resume()
        audit.kill_switch("resumed")
        print("[heartbeat resumed.]")
        return True
    if t == "audit":
        print(audit.tail(20))
        return True
    if t == "cost":
        print(f"[{audit.cost_summary()}]")
        return True
    return False


def main() -> None:
    # Wire in the confirmation gate for text mode.
    gate.set_confirmer(gate.TextConfirmer())

    # Recover any interrupted sessions from a previous run
    from dela import sessions
    recovered = sessions.recover_interrupted()
    for r in recovered:
        print(f"[session recovery] {r['id']}: {r['action']}")

    # Start the heartbeat in the background.
    heartbeat.start()
    print(f"{config.NAME} is ready. Heartbeat is running. Type a message and press Enter. Ctrl+C to quit.")
    print("Commands: notices, dismiss <id>, clear notices, pause/resume heartbeat, audit, cost\n")

    _surface_notices()

    history: list = []
    try:
        while True:
            try:
                user_text = input("you > ").strip()
            except EOFError:
                break
            if not user_text:
                continue

            if _handle_commands(user_text):
                continue

            reply = assemble_reply(history, user_text)
            print(f"{config.NAME} > {reply}")
            print()

            _surface_notices()
    except KeyboardInterrupt:
        print("\n(quit)")
    finally:
        heartbeat.stop()


if __name__ == "__main__":
    main()
