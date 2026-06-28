# Dela — Voice-First AI Assistant

The single source of truth for what we're building and why. Future sessions read this first.

## Identity
- **Name:** Dela
- **One-line purpose:** A voice-first assistant that manages projects, researches the web, and checks on systems — and reaches out to me first when something matters.
- **For:** A small team eventually. Start single-user, but keep per-user state in mind from the beginning (memory, preferences, and confirmation gates should be user-scoped in design, even if only one user exists today).
- **Personality & tone:** Warm, plain-spoken, and brief. Friendly without being chatty; gets to the point. Consistent everywhere — system prompt, logs, spoken replies.

## First three capabilities (Tier 2 tools + first test cases)
1. **Project Management** — track tasks, remind me of what's due, surface project status.
2. **Web Research** — look things up on the web and summarize findings.
3. **Systems Checks** — run health checks against services/endpoints and report status.

## Stack
- **Language & runtime:** Python. Mainstream, great audio + HTTP libraries, no heavy framework. Keep the harness small and readable.
- **Model provider:** OpenCode GO / Zen via an **OpenAI-compatible** endpoint (kept behind a thin seam so it's swappable). **Ollama** is the planned future provider for local/self-hosted runs — same seam, no rewrite.
- **Where it runs:** Laptop-first. Tier 5 (heartbeat) is built so it *can* move to an always-on host later without a rewrite, but no server required to start.

## How I talk to it
- **Build text first** regardless (Tier 1), then **push-to-talk** in Tier 3 (most reliable, cheapest to get right).
- **Wake word / open mic** comes later — design the audio layer so this is an add-on, not a fork.

## Safety posture (never without asking me first)
The default list, baked into the confirmation gate from Tier 2 onward and hardened in Tier 6:
- **Send a message**
- **Spend money**
- **Delete data**
- **Change a setting**

Read-only actions flow freely; irreversible ones never act on assumed permission. Confirmation is per-action and never generalizes.

## Proactivity
- **Proactive, but quiet by default.** Dela earns interruptions; it doesn't assume them.
- Most checks produce nothing most of the time; a calm log accumulates the rest.
- Notices are held for me if I'm away, not fired into the void.
- Quiet hours are a setting. Only truly critical things earn a late-night interruption.

## Build discipline
- **Tier by tier.** Each tier ends with something runnable and a verification step. Don't start a tier until the previous one works on its own.
- **One shared agent core, many ways in and out.** Typed, spoken, and heartbeat-initiated turns all flow through the same brain. If the agent logic gets written twice, stop and unify.
- **Get the brain working in plain text before adding a single line of audio.** Voice is a layer on top of a working agent, never the foundation.
- **Secrets never in code.** API keys live in environment variables or a git-ignored local secrets file from the very first commit.

## Tier map
0. Interview → this spec file (done)
1. The brain — text conversation loop, streamed replies, provider behind a seam (done)
2. The hands — tool registry; first tools = project mgmt, web research, systems checks (done)
3. The ears and mouth — local voice: faster-whisper STT + Piper TTS + webrtcvad duplex, all behind seams (done)
4. The memory — durable, human-readable, model-managed, data-not-instructions (done)
5. The heartbeat — quiet-by-default proactive loop, scheduled checks, hold-for-return, kill switch (done)
6. The rails — confirmation gate, treat inbound content as data, config file, audit log, cost tally, kill switch (done)

## How to run
- Text: `python -m dela`
- Voice (duplex/open mic): `python -m dela.voice`
- Voice (push-to-talk): `python -m dela.voice --ptt`
- Commands: `notices`, `dismiss <id>`, `clear notices`, `pause/resume heartbeat`, `audit`, `cost`
