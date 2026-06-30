---
title: Roadmap
nav_order: 12
---

# Roadmap

## Completed

The baseline (Tiers 0-6) and all roadmap steps are complete:

- [x] **Tracing seam** — LangSmith/Langfuse headers injected into provider calls
- [x] **Sub-agent system** — 5 specialist agents with tool whitelists
- [x] **Skills system** — markdown guidance files loaded on demand
- [x] **MCP server support** — external tool integration
- [x] **Sandboxed code execution** — Docker + subprocess fallback
- [x] **IM channels** — Telegram, Teams, Graph API
- [x] **Blackboard orchestration** — multi-agent shared workspace
- [x] **8 Flue-inspired features** — compaction, thinking levels, durable execution, model override, instance IDs, workflows, scheduled workflows, structured output
- [x] **State browser** — unified read/search/edit across 13 state types
- [x] **System Expert agent** — self-aware architecture advisor
- [x] **Security audit system** — 9 check categories, score 0-100
- [x] **Profile system** — personal + work with profile-specific API config
- [x] **Live settings** — 11 hot-reloadable settings without restart
- [x] **EoT detector + duplex voice** — smart turn-taking with barge-in
- [x] **Jarvis Hub UI** — holographic web UI with 5 themes, floating windows, live stats
- [x] **One-command startup** — `python start_dela.py` with preflight checks
- [x] **Voice I/O via web** — mic button + TTS playback in the browser
- [x] **Agent status tracking** — live ready/busy/error in the Hive panel + idle roster
- [x] **Vulnerability knowledge base** — OWASP LLM Top 10 + CWE Top 25 (20 checks)
- [x] **Security fix button** — dispatch system_expert to recommend/implement fixes
- [x] **Vuln KB auto-refresh** — heartbeat check syncs from OWASP/CWE/CISA daily
- [x] **Security prioritization** — findings sorted P0-P4 by severity + impact
- [x] **Model router** — auto-routes trivial tasks to cheap model, complex to premium
- [x] **Workflow designer UI** — visual editor with all 5 agents, run button, results
- [x] **Analytics dashboard** — model calls, cost, tool usage, gate decisions
- [x] **GitHub Pages docs** — full documentation site with search and navigation
- [x] **Kokoro TTS** — second TTS provider, 12 US/UK voices at 24kHz (default)
- [x] **Piper voice auto-detection** — 25 voices auto-download from HuggingFace on first use
- [x] **Personality matrix** — 7 presets (Friendly, Professional, Energetic, Calm, British, Technical, Creative) injected into system prompt
- [x] **Dynamic HITL gate** — impact-based confirmation scoring (0-10), configurable threshold
- [x] **RichMessage component** — markdown rendering with code copy, tables, headings, iframe previews
- [x] **Slash commands** — /help /clear /voice /theme /memory /scan /tasks /cost
- [x] **Sub-agent overlay** — animated draggable overlay with live tool blips during agent execution
- [x] **Idle chat redesign** — ultra-compact 3-icon bar (💬🎤●), smooth expand with cubic-bezier animation
- [x] **Panel chips redesign** — floating emoji icon buttons without boxes, grouped with spacers
- [x] **Conversation transitions** — smooth fade on TopStrip, Dock, and conv-overlay appearance
- [x] **Multi-tab audio coordination** — BroadcastChannel to ensure only one tab speaks
- [x] **Pulse-audio sync** — particle canvas reads real RMS amplitude from AnalyserNode
- [x] **Model router defaults on** — FAST/PREMIUM MODEL dropdowns populated from `/api/models`
- [x] **Thread-safe memory** — locking, atomic writes (temp+rename), dedup, list_facts/search_facts tools
- [x] **Memory search UI** — search bar + category filter in MemoryPanel
- [x] **Project panels** — collapsible projects with status tabs, agent steps, usefulness audit
- [x] **Browser-based STT/TTS** — MediaRecorder + AudioBuffer.decodeAudioData via Web Audio API

## Future Ideas

- **Ollama integration** — local model support (already compatible via OpenAI endpoint)
- **Wake word** — open-mic wake word detection on top of VAD
- **Always-on host** — move heartbeat to a machine that never sleeps
- **Multi-user** — formalize per-user state
- **True duplex speech model** — when a runnable client ships, swap STT+TTS for a single seam
- **WIZ integration** — full cloud security monitoring for work profile
- **More vuln KB sources** — NVD, BSI, additional security frameworks
- **Workflow templates** — pre-built workflow library for common tasks
- **Multi-language voice** — Whisper multilingual model + Piper voices for other languages
