"""Microsoft Graph API channel — send and poll Teams messages via Graph.

Uses the OAuth2 client credentials flow (no user interaction) to get an
access token, then sends messages to a Teams chat or channel and polls
for incoming messages.

Setup (one-time):
  1. Register an Azure AD app (App Registrations in Azure Portal)
  2. Add client secret, note the client_id and tenant_id
  3. Grant API permissions:
     - ChannelMessage.Read.All (for channel polling)
     - ChannelMessage.Send (for channel sending)
     - Chat.Read (for chat polling)
     - ChatMessage.Send (for chat sending)
     - Or Mail.Send / Mail.Read for email mode
  4. Set env vars and enable in channels_config.json

Config (channels_config.json):
  "graph_api": {
    "enabled": true,
    "client_id_env": "DELA_GRAPH_CLIENT_ID",
    "client_secret_env": "DELA_GRAPH_CLIENT_SECRET",
    "tenant_id_env": "DELA_GRAPH_TENANT_ID",
    "target_type": "chat",        // "chat" or "channel"
    "target_id_env": "DELA_GRAPH_TARGET_ID",
    "poll_interval_seconds": 10
  }

Run:  python -m dela.channels.graph_api
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.parse

from dela import brain, config, gate, heartbeat, noticeboard
from dela.channels import register_channel
from dela.channels.config import get_channel, resolve_secret, is_enabled

# Token cache.
_token: str = ""
_token_expiry: float = 0

# Per-target conversation histories.
_histories: dict[str, list] = {}

# Track the last seen message ID to avoid reprocessing.
_last_message_id: str = ""

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphApiConfirmer:
    """Auto-deny in Graph API channel — no interactive dialog yet.
    Future: use Adaptive Cards with Yes/No buttons in Teams."""

    def confirm(self, description: str, timeout: float | None = None) -> bool:
        return False


def _get_token() -> str:
    """Get (or refresh) an OAuth2 access token via client credentials flow."""
    global _token, _token_expiry

    if _token and time.time() < _token_expiry - 60:
        return _token

    cfg = get_channel("graph_api")
    client_id = resolve_secret(cfg, "client_id")
    client_secret = resolve_secret(cfg, "client_secret")
    tenant_id = resolve_secret(cfg, "tenant_id")

    if not all([client_id, client_secret, tenant_id]):
        raise RuntimeError("Graph API: missing client_id, client_secret, or tenant_id")

    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }).encode()

    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
    })

    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())

    _token = result["access_token"]
    _token_expiry = time.time() + result.get("expires_in", 3600)
    return _token


def _graph_request(method: str, path: str, body: dict | None = None) -> dict:
    """Make an authenticated Graph API request."""
    token = _get_token()
    url = f"{_GRAPH_BASE}{path}"
    data = json.dumps(body).encode() if body else None

    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })

    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _send_chat_message(chat_id: str, text: str) -> None:
    """Send a message to a Teams chat."""
    _graph_request("POST", f"/chats/{chat_id}/messages", {
        "body": {"content": text},
    })


def _send_channel_message(team_id: str, channel_id: str, text: str) -> None:
    """Send a message to a Teams channel."""
    _graph_request("POST", f"/teams/{team_id}/channels/{channel_id}/messages", {
        "body": {"content": text},
    })


def _poll_chat_messages(chat_id: str) -> list[dict]:
    """Get recent messages from a chat, newest first."""
    result = _graph_request("GET", f"/chats/{chat_id}/messages?$top=10")
    return result.get("value", [])


def _poll_channel_messages(team_id: str, channel_id: str) -> list[dict]:
    """Get recent messages from a channel, newest first."""
    result = _graph_request("GET", f"/teams/{team_id}/channels/{channel_id}/messages?$top=10")
    return result.get("value", [])


def _is_my_message(msg: dict) -> bool:
    """Check if a message was sent by the app (skip our own replies)."""
    return msg.get("from", {}).get("application", {}) is not None


def _process_incoming(text: str, target_id: str) -> None:
    """Run the brain on an incoming message and send the reply."""
    if target_id not in _histories:
        _histories[target_id] = []

    # Surface pending notices on first contact.
    pending = noticeboard.pending_on_return()
    if pending:
        notice_text = "\n".join(n["message"] for n in pending)
        _send_to_target(target_id, f"While you were away:\n{notice_text}")
        for n in pending:
            noticeboard.dismiss(n["id"])

    gate.set_confirmer(GraphApiConfirmer())
    reply = brain.assemble_reply(_histories[target_id], text)
    _send_to_target(target_id, reply)


def _send_to_target(target_id: str, text: str) -> None:
    """Send a message to the configured target (chat or channel)."""
    cfg = get_channel("graph_api")
    target_type = cfg.get("target_type", "chat")

    if target_type == "chat":
        _send_chat_message(target_id, text)
    elif target_type == "channel":
        # target_id format for channels: "team_id/channel_id"
        if "/" in target_id:
            team_id, channel_id = target_id.split("/", 1)
            _send_channel_message(team_id, channel_id, text)
        else:
            print(f"[Graph API: channel target_id should be 'team_id/channel_id', got '{target_id}']")
    else:
        print(f"[Graph API: unknown target_type '{target_type}']")


def _poll_loop() -> None:
    """Poll for incoming messages and process them."""
    global _last_message_id

    cfg = get_channel("graph_api")
    target_id = resolve_secret(cfg, "target_id")
    target_type = cfg.get("target_type", "chat")
    poll_interval = int(cfg.get("poll_interval_seconds", 10))

    if not target_id:
        print("[Graph API: no target_id configured]")
        return

    print(f"[Graph API: polling {target_type} '{target_id}' every {poll_interval}s...]")

    # On first run, grab the latest message ID without processing it
    # (so we don't replay old messages).
    if not _last_message_id:
        msgs = _poll_chat_messages(target_id) if target_type == "chat" else (
            _poll_channel_messages(*target_id.split("/", 1)) if "/" in target_id else []
        )
        if msgs:
            _last_message_id = msgs[0]["id"]
        print(f"[Graph API: caught up — last message id: {_last_message_id[:20]}...]")

    while True:
        try:
            if target_type == "chat":
                msgs = _poll_chat_messages(target_id)
            elif target_type == "channel" and "/" in target_id:
                team_id, channel_id = target_id.split("/", 1)
                msgs = _poll_channel_messages(team_id, channel_id)
            else:
                msgs = []

            # Process new messages (they come newest-first; process oldest new first).
            new_msgs = []
            for msg in msgs:
                if msg["id"] == _last_message_id:
                    break
                if not _is_my_message(msg):
                    new_msgs.append(msg)

            new_msgs.reverse()  # process in chronological order
            for msg in new_msgs:
                text = msg.get("body", {}).get("content", "").strip()
                # Strip HTML tags (Teams messages are HTML).
                import re
                text = re.sub(r"<[^>]+>", "", text).strip()
                if text:
                    print(f"[Graph API: incoming: {text[:80]}]")
                    _process_incoming(text, target_id)

            if msgs:
                _last_message_id = msgs[0]["id"]

        except Exception as e:
            print(f"[Graph API: poll error: {e}]")

        time.sleep(poll_interval)


@register_channel("graph_api")
def start() -> None:
    """Start the Graph API channel — polls for messages and replies."""
    if not is_enabled("graph_api"):
        print("[Graph API: disabled in config]")
        return

    heartbeat.start()
    _poll_loop()


if __name__ == "__main__":
    start()