"""Microsoft Teams Webhook channel.

Architecture:
  - Dela exposes a POST endpoint on the FastAPI server (e.g. /channels/teams/webhook)
  - A Teams Workflow / Power Automate / outgoing webhook sends messages to that endpoint
  - Dela runs the brain and posts the reply back to the Teams incoming webhook URL

This is the simplest Teams integration — no Bot Framework, no Azure AD app.
Set up a Teams incoming webhook (or Workflow webhook) and point a Flow at
Dela's endpoint. Messages flow in, replies flow back.

Config (channels_config.json):
  "teams_webhook": {
    "enabled": true,
    "incoming_webhook_url_env": "DELA_TEAMS_WEBHOOK_URL",
    "endpoint_path": "/channels/teams/webhook",
    "verify_token_env": "DELA_TEAMS_VERIFY_TOKEN"   // optional shared secret
  }

The endpoint accepts POST with JSON body:
  {"text": "user message", "conversation_id": "optional-id", "user": "optional-name"}

Dela replies by POSTing to the configured webhook URL.
"""

from __future__ import annotations

import json
import urllib.request

from dela import brain, gate, noticeboard
from dela.channels import register_channel
from dela.channels.config import get_channel, resolve_secret, is_enabled

# Per-conversation histories.
_histories: dict[str, list] = {}


class TeamsWebhookConfirmer:
    """Auto-deny in Teams webhook — no interactive dialog yet.
    Future: use Adaptive Cards with Yes/No buttons."""

    def confirm(self, description: str, timeout: float | None = None) -> bool:
        return False


def _post_to_teams(webhook_url: str, text: str) -> None:
    """Post a message to a Teams incoming webhook URL."""
    try:
        # Teams incoming webhooks accept plain text or Adaptive Card JSON.
        payload = json.dumps({"text": text}).encode()
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[Teams Webhook: send failed: {e}]")


def handle_message(body: dict) -> dict:
    """Handle an incoming Teams webhook POST. Called by the FastAPI server.

    Returns a JSON response for the HTTP caller (the Teams Workflow).
    The actual reply is posted asynchronously to the Teams webhook URL.
    """
    cfg = get_channel("teams_webhook")
    webhook_url = resolve_secret(cfg, "incoming_webhook_url")
    verify_token = resolve_secret(cfg, "verify_token")

    # Optional shared-secret verification.
    if verify_token:
        provided = body.get("verify_token", "")
        if provided != verify_token:
            return {"ok": False, "error": "invalid verify token"}

    text = body.get("text", "").strip()
    if not text:
        return {"ok": False, "error": "no text"}

    conversation_id = body.get("conversation_id", "default")
    if conversation_id not in _histories:
        _histories[conversation_id] = []

    # Surface pending notices on first contact in this conversation.
    pending = noticeboard.pending_on_return()
    if pending:
        notice_text = "\n".join(n["message"] for n in pending)
        _post_to_teams(webhook_url, f"While you were away:\n{notice_text}")
        for n in pending:
            noticeboard.dismiss(n["id"])

    # Run the brain.
    gate.set_confirmer(TeamsWebhookConfirmer())
    reply = brain.assemble_reply(_histories[conversation_id], text)

    # Post the reply back to Teams.
    _post_to_teams(webhook_url, reply)

    return {"ok": True, "reply": reply[:200]}


def register_endpoint(app) -> None:
    """Register the webhook endpoint on the FastAPI app."""
    if not is_enabled("teams_webhook"):
        return

    cfg = get_channel("teams_webhook")
    path = cfg.get("endpoint_path", "/channels/teams/webhook")

    @app.post(path)
    async def teams_webhook(body: dict):
        return handle_message(body)

    print(f"[Teams Webhook: endpoint registered at {path}]")


@register_channel("teams_webhook")
def start() -> None:
    """Standalone mode — runs the FastAPI server with the webhook endpoint.

    Typically the webhook endpoint is registered on the main FastAPI server
    (dela/server.py calls register_endpoint). This standalone function is for
    running just the channel without the full UI server.
    """
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI(title="Dela Teams Webhook")
    register_endpoint(app)
    print("[Teams Webhook: starting server on port 8001...]")
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    start()