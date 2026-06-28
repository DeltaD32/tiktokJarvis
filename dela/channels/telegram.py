"""Telegram channel — bridge Telegram messages to Dela's brain.

Connects via the Telegram Bot API (long-polling). Each incoming message runs
through brain.assemble_reply() with the same tools, memory, and heartbeat.
Confirmation-gated actions auto-deny in this channel (no interactive dialog
yet — a future enhancement could use Telegram inline keyboards for yes/no).

Config: set DELA_TELEGRAM_BOT_TOKEN in .env.
Run:    python -m dela.channels.telegram
"""

from __future__ import annotations

import threading

from dela import brain, config, gate, heartbeat, noticeboard
from dela.channels import register_channel
from dela.channels.config import get_channel, resolve_secret, is_enabled

# Per-chat conversation histories (single-user assumption; multi-user later).
_histories: dict[int, list] = {}


class TelegramConfirmer:
    """Auto-deny in Telegram — no interactive confirmation dialog yet.
    A future enhancement could use inline keyboards for yes/no."""

    def confirm(self, description: str, timeout: float | None = None) -> bool:
        return False


def _start_telegram() -> None:
    import urllib.request
    import json

    cfg = get_channel("telegram")
    token = resolve_secret(cfg, "bot_token")
    if not token:
        print("[Telegram: no bot token configured — channel disabled]")
        return

    # Set the Telegram confirmer for this session.
    gate.set_confirmer(TelegramConfirmer())
    heartbeat.start()

    api = f"https://api.telegram.org/bot{token}"
    offset = 0

    print("[Telegram: polling for messages...]")
    while True:
        try:
            url = f"{api}/getUpdates?offset={offset}&timeout=30"
            with urllib.request.urlopen(url, timeout=35) as resp:
                data = json.loads(resp.read())

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg or "text" not in msg:
                    continue

                chat_id = msg["chat"]["id"]
                text = msg["text"].strip()

                # Skip commands for now (future: /notices, /pause, etc.)
                if text.startswith("/"):
                    if text == "/start":
                        _send(api, chat_id, f"Hi, I'm {config.NAME}. Just send me a message.")
                    continue

                # Get or create per-chat history.
                if chat_id not in _histories:
                    _histories[chat_id] = []

                # Surface pending notices on first contact.
                pending = noticeboard.pending_on_return()
                if pending:
                    notice_text = "\n".join(n["message"] for n in pending)
                    _send(api, chat_id, f"While you were away:\n{notice_text}")
                    for n in pending:
                        noticeboard.dismiss(n["id"])

                # Run the brain.
                reply = brain.assemble_reply(_histories[chat_id], text)

                # Telegram has a 4096 char limit — split if needed.
                for i in range(0, len(reply), 4000):
                    _send(api, chat_id, reply[i:i + 4000])

        except Exception as e:
            print(f"[Telegram: error: {e}]")
            import time
            time.sleep(5)


def _send(api: str, chat_id: int, text: str) -> None:
    import urllib.request
    import json

    try:
        data = json.dumps({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(
            f"{api}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[Telegram: send failed: {e}]")


@register_channel("telegram")
def start() -> None:
    if not is_enabled("telegram"):
        print("[Telegram: disabled in config]")
        return
    _start_telegram()


if __name__ == "__main__":
    _start_telegram()