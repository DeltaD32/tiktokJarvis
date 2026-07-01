# Dela Backend Roadmap — Post-Baseline Enhancements

Borrowed ideas from DeerFlow 2.0, implemented Dela's way: one module at a time,
behind existing seams, verified before the next. No framework swap.

Each step is independently testable. None require rewriting the brain, the
provider seam, or the entry points. They all extend the existing architecture.

---

## Step 1 — Enhanced Tracing (LangSmith + Langfuse callbacks)

**What:** Add optional LangSmith and/or Langfuse tracing to our audit seam so
every LLM call, tool call, and sub-agent run is visible in a dashboard.

**Why:** Our `audit.log` is great for humans, but token-level tracing (which
prompt, which tools, how many tokens, how long) needs a proper observability
backend. LangSmith/Langfuse are free and lightweight.

**How:** Add a `dela/tracing.py` module behind a seam (like `provider.py`).
If `DELA_TRACING_PROVIDER` is set in `.env`, attach callbacks to the OpenAI
client. If not set, no-op. The audit trail stays as-is; tracing is additive.

**Files:** `dela/tracing.py` (new), `dela/config.py` (add tracing env vars),
`dela/provider.py` (attach callbacks), `.env.example` (document vars)

**Verify:** Enable tracing, run a turn with a tool call, see it in the dashboard.

---

## Step 2 — Sub-Agents (Specialist agents with own prompt + tools)

**What:** Let Dela spawn a sub-agent mid-conversation — a child brain with its
own system prompt, its own tool subset, and a focused task. The sub-agent runs,
reports back a structured result, and the lead agent weaves it into the reply.

**Why:** Complex tasks don't fit in a single pass. "Research X and write a
report" should fan out to a research sub-agent and a writing sub-agent. This
is the spec's "specialist sub-agents" next step.

**How:** A new tool `dispatch_subagent` that the lead agent can call. It takes
a task description, an optional agent name (maps to a predefined SOUL), and an
optional tool whitelist. The sub-agent runs the same `brain.respond()` loop
with a scoped system prompt, scoped tools, and its own history. When done, the
result string goes back to the lead agent as the tool result.

Sub-agent SOULs are defined in a `dela/agents/` directory — each is a Python
file with a system prompt builder and a tool whitelist. Adding a new agent =
one file, no code changes to the brain.

**Files:** `dela/agents/` (new dir), `dela/agents/__init__.py` (agent registry),
`dela/agents/researcher.py` (first sub-agent), `dela/tools/subagent.py`
(the dispatch tool), `dela/brain.py` (minor: support scoped tool registries)

**Verify:** Ask Dela "research X thoroughly" → it dispatches a research
sub-agent → sub-agent uses fetch_url multiple times → reports back → Dela
synthesizes the result.

---

## Step 3 — Skills System (Progressive tool descriptions, loaded on demand)

**What:** A skill is a Markdown file that defines a workflow, best practices,
and tool usage guidance. Skills are loaded progressively — only when the task
needs them — keeping the context window lean.

**Why:** As we add more tools, the system prompt grows. Skills let the model
discover capability on demand without loading every tool description up front.

**How:** A `dela/skills/` directory. Each skill is a `.md` file with optional
frontmatter (name, description, tools) and a body (guidance injected into the
context when the skill is activated). A `load_skill` tool lets the model pull
in a skill's guidance mid-conversation. The model can also activate a skill
explicitly: "use the data-analysis skill." Slash activation (`/skill-name`)
works in text mode.

**Files:** `dela/skills/` (new dir), `dela/skills/__init__.py` (skill loader),
`dela/skills/research.md` (first skill), `dela/tools/skills.py`
(the load_skill tool), `dela/system_prompt.py` (inject active skills)

**Verify:** Ask Dela a question that benefits from a skill → it loads the skill
mid-conversation → the skill's guidance shapes the reply.

---

## Step 4 — MCP Server Support (Bridge external tool ecosystems)

**What:** Support Model Context Protocol (MCP) servers as tool sources. An MCP
server exposes tools via a standard protocol; Dela bridges them into the tool
registry as if they were native tools.

**Why:** MCP is the emerging standard for LLM tool interoperability. Supporting
it opens up hundreds of existing tools (filesystem, database, browser, etc.)
without writing each one as a Dela tool.

**How:** A `dela/mcp.py` module that connects to configured MCP servers
(stdio or HTTP/SSE), discovers their tools, and wraps each as a Dela `Tool`
with a generated `run()` function that proxies to the MCP server. Config in
`heartbeat_config.json` or a new `mcp_config.json`. MCP tools respect the
same confirmation gate as native tools (schema inspection determines
`requires_confirmation`).

**Files:** `dela/mcp.py` (new), `mcp_config.json` (new), `dela/tools/__init__.py`
(load MCP tools on startup), `requirements.txt` (add `mcp` SDK)

**Verify:** Configure an MCP server (e.g. filesystem) → Dela discovers its
tools → calls one mid-conversation → result flows back through the brain.

---

## Step 5 — Sandboxed Code Execution (A `run_code` tool)

**What:** A tool that lets Dela execute Python (or shell) code in an isolated
Docker container and return the output. Read-only by default; file writes
require confirmation.

**Why:** Data analysis, file processing, quick calculations — the things that
make Dela genuinely useful for real work instead of just conversation.

**How:** A `run_code` tool that spawns a Docker container (using the official
Python image), mounts a scratch directory, executes the code, captures stdout/
stderr, and returns it. Timeout-bounded. Container is killed after execution.
The tool is confirmation-gated (running arbitrary code is consequential).

For environments without Docker, fall back to a `subprocess`-based executor
with a warning that it's less isolated. The seam means the execution backend
can swap without changing the tool.

**Files:** `dela/tools/code_exec.py` (new), `dela/sandbox.py` (execution
backend seam — Docker or subprocess), `requirements.txt` (add `docker` if
Docker mode)

**Verify:** Ask Dela "calculate the factorial of 20 in Python" → it calls
run_code → gets the result → replies with the answer.

---

## Step 6 — IM Channels (Slack, Telegram, Discord entry points)

**What:** New entry points that bridge IM platforms to the same brain. Messages
from Slack/Telegram/Discord flow through `brain.assemble_reply()` exactly like
text and voice do.

**Why:** Dela should be reachable where the team already works. The
architecture is already shaped for this — "one shared agent core, many ways in
and out."

**How:** A `dela/channels/` package. Each channel is a module that connects
to the platform's API (bot token, socket mode, etc.), receives messages, and
calls `brain.assemble_reply()`. Replies go back through the platform API.
Each channel sets its own `Confirmer` (platform-appropriate — Slack uses
reactions or buttons, Telegram uses inline keyboards).

**Files:** `dela/channels/` (new dir), `dela/channels/__init__.py` (channel
registry), `dela/channels/telegram.py` (first channel), `dela/channels/slack.py`,
`channels_config.json` (tokens + per-channel settings), `requirements.txt`
(add `python-telegram-bot`, `slack-sdk`)

**Verify:** Send a message to Dela's Telegram bot → it responds using the same
brain + tools + memory.

---

## Step 7 — Content Sandbox

**What:** A 6-layer security pipeline for all internet-facing content. Every byte from
external URLs passes through SSRF protection, content-type validation, HTML sanitization,
malicious pattern scanning, encrypted quarantine, and integrity verification before
reaching the model.

**Why:** `fetch_url` previously fetched arbitrary URLs with only a basic scheme check.
No protection against SSRF attacks, malicious scripts in HTML, prompt injection payloads,
or binary content. As Dela gains more internet-facing tools (repo analysis, multi-platform
research), a centralized security layer prevents accidental compromise.

**How:** `dela/content_sandbox.py` — a seam that wraps `urllib.request`. Existing tools
import `secure_fetch()` instead of calling `urlopen()` directly. Six layers applied in
order; any layer can reject content before it reaches the brain.

**Files:** `dela/content_sandbox.py` (new), `dela/tools/research.py` (rewired to sandbox),
`dela/tools/repo_analysis.py` (rewired to sandbox), `dela/brain.py` (added
`analyze_external_repo` to `_EXTERNAL_TOOLS`), `docs/security.md` (content sandbox
section).

**New deps:** None (stdlib-only: `hashlib`, `ipaddress`, `re`, `json`, `urllib`).

**Verify:** SSRF blocks `127.0.0.1`, `169.254.169.254`; HTML sanitizer strips
`<script>`, `<iframe>`, event handlers; pattern scanner detects "ignore previous
instructions" and `eval()` calls; quarantined content is encrypted at rest.

---

## Step 8 — Multi-User Auth & Access Control ✅ (done)

**What:** Transform Dela from a single-user laptop assistant to a multi-user
server with role-based access control, per-user state isolation, JWT
authentication, and a login flow on the frontend. Three roles: admin (full
system access), user (own state only), viewer (read-only, future).

**Why:** Dela currently runs as a single user with all state global. The
backend can run on a server and the frontend can be used by multiple users
simultaneously — but there's no auth, no state isolation, and no user concept.
Every WebSocket client shares one conversation. For team use, this is a blocker.

**How:** Five implementation phases, extending at the edges:

**Phase 1 — Auth core (new modules, no breaking changes):**
- `dela/users.py` — User model, CRUD, SQLite-backed (stdlib, zero new deps)
- `dela/auth.py` — JWT encode/decode (PyJWT already installed), bcrypt password hashing
- `dela/auth_middleware.py` — FastAPI middleware, extracts user from Bearer token
- `dela/server.py` — `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/refresh`
- Admin seeder: creates default admin on first run

**Phase 2 — State isolation (per-user directories):**
- Per-user state under `dela_state/users/{user_id}/` (memory, sessions, audit, notices, settings, blackboards, projects)
- System state under `dela_state/system/` (heartbeat config, vuln KB, schedule)
- Migration: existing `dela_state/*` moves to `global/` on first multi-user startup

**Phase 3 — Server multi-user wiring:**
- Per-user `_clients` dict (user_id → WebSocket), `_histories`, `_confirm_callbacks`
- WebSocket auth via `?token=<jwt>` query param
- `WebSocketConfirmer` scoped to user (confirmation dialogs route to correct user)
- Auth middleware on all `/api/*` routes; role checks on admin endpoints

**Phase 4 — Frontend auth:**
- `AuthContext.jsx` — login state, token storage, auth helpers
- `LoginPage.jsx` — login form
- `AdminPanel.jsx` — user management (admin only)
- Token in WebSocket URL and all `fetch()` Authorization headers
- Role-based UI: admin sees system config + user management; user sees own state only

**Phase 5 — Polish:**
- Rate limiting on auth endpoints (5 attempts / 15 min)
- Token refresh flow
- Audit log includes `[user:xxx]` prefix
- Per-user cost tracking
- Password change flow

**Files:** `dela/users.py` (new), `dela/auth.py` (new), `dela/auth_middleware.py` (new),
`dela/server.py` (major: per-user state, auth middleware, new endpoints),
`dela/gate.py` (minor: `ask()` accepts `user_id`), `dela/brain.py` (minor:
`respond()` accepts `user_id`), `dela/memory.py` (add `user_id` to all functions),
`dela/sessions.py` (per-user session dirs), `dela/audit.py` (per-user log),
`frontend/src/contexts/AuthContext.jsx` (new), `frontend/src/components/LoginPage.jsx`
(new), `frontend/src/components/AdminPanel.jsx` (new), `frontend/src/App.jsx`
(auth guard), `frontend/src/hooks/useDelaWS.js` (token in WS URL),
`frontend/src/components/TopStrip.jsx` (user info + logout)

**New deps:** `bcrypt` only (pure Python, ~30KB)

**Detailed plan:** `docs/multi-user-auth-plan.md`

**Verify:** Two users log in from separate browsers → chat simultaneously with
isolated conversation histories → admin sees user management panel → user does
not → confirmation dialogs route to correct user → audit log shows per-user
entries.

**Implementation notes:**
- `dela/users.py` — SQLite user store, `dela/auth.py` — JWT + bcrypt, `dela/auth_middleware.py` — FastAPI middleware
- `dela/user_context.py` — thread-local per-user path resolution
- 12 state modules updated for per-user paths (memory, audit, noticeboard, sessions, live_config, blackboard, projects, agent_memory, routing_cache, status_events, workflows, tasks)
- System-level files (hb_config, connections, oauth, vuln_kb, schedule) stay system-level
- Migration: single-user state moves to `dela_state/global/` on first multi-user startup
- Per-user `_clients`, `_histories`, `_confirm_callbacks` in server; WebSocket auth via `?token=<jwt>`
- `UserSocketConfirmer` routes confirmations to correct user
- 11 admin-only endpoints guarded by role check
- Frontend: `AuthContext.jsx`, `LoginPage.jsx`, `AdminPanel.jsx`; token in WS + all fetch calls
- Rate limiting: 5 failed attempts / 15 min per IP
- Password change: `PUT /api/auth/password`
- New dep: `bcrypt>=4.0.0` (PyJWT already installed)

---

## Implementation Order

1. **Tracing** ✅ (done — LangSmith + Langfuse callbacks)
2. **Sub-agents** ✅ (done — 5 specialist agents)
3. **Skills** ✅ (done — 3 skills, progressive loading)
4. **MCP support** ✅ (done — MCP server bridging)
5. **Sandboxed execution** ✅ (done — Docker/subprocess sandbox)
6. **IM channels** ✅ (done — Telegram, Teams, Graph API)
7. **Content sandbox** ✅ (done — 6-layer internet content security)
8. **Multi-user auth** ✅ (done — JWT + bcrypt + SQLite users + per-user state + frontend login)

Each step ends with something runnable and a verification test. Don't start
a step until the previous one works on its own.

---

## Perfection Roadmap (post-baseline polish)

These items are ordered by impact × effort — smallest fixes first (snowball method).

### Tier 1 — Snowball (quick wins, under 30 min each)

| # | Item | Effort | Impact | Status |
|---|---|---|---|---|
| 1 | **Exponential WS backoff** — 1s → 3s → 10s → 30s instead of fixed 3.5s reconnect | 5 min | Reduces log noise | ✅ done |
| 2 | **Conversation persistence** — save/restore to localStorage, survives page reload | 10 min | UX: history survives refresh | ✅ done |
| 3 | **Per-user brain lock** — `_brain_locks[user_id]` instead of global lock, multi-user simultaneous chat | 5 min | Unblocks multi-user concurrency | ✅ done |
| 4 | **Sub-agent JSON output** — structured `{section, data}` format from agents instead of free text | 15 min | Enables reliable HTML synthesis |
| 5 | **WebSocket reconnect state** — show "Reconnecting in Xs..." in top strip during backoff | 10 min | Visual feedback on connection loss |
| 6 | **Error boundary** — React `<ErrorBoundary>` wrapping app, catches render crashes | 10 min | Graceful crash recovery |

### Tier 2 — Solidify (foundational quality)

| # | Item | Effort | Impact | Status |
|---|---|---|---|---|
| 7 | **Feature registry** — `dela_state/features.json`, lifecycle states (evaluated → shelved → in_progress → done), prevents double-research | 1h | Foundation for feature management |
| 8 | **Token refresh UI** — auto-refresh token before expiry, "Session expiring" warning | 30 min | Seamless auth experience |
| 9 | **Sub-agent result streaming** — stream sub-agent output tokens into panel overlay in real-time | 1h | Rich visibility into agent work |
| 10 | **Voice selection UI** — dropdown for kokoro/piper voices, TTS provider toggle | 30 min | Voice customization |
| 11 | **Audit search/filter** — `GET /api/audit?q=keyword&type=tool&since=...` | 45 min | Debuggability |
| 12 | **Heartbeat per-user** — each user can configure their own heartbeat checks | 1h | Personalization |

### Tier 3 — Expand (new capabilities)

| # | Item | Effort | Impact | Status |
|---|---|---|---|---|
| 13 | **Acceptance wizard** — Accept → questionnaire → implementation plan → progress tracking | 2h | Completes feature pipeline |
| 14 | **Feature idea Gantt** — timeline view of all evaluated/in-progress features | 1.5h | Strategic overview |
| 15 | **Mobile responsive layout** — breakpoints for tablet/phone, collapsible panels | 3h | Ubiquity |
| 16 | **Multi-provider fallback** — primary → secondary provider on failure | 1h | Resilience |
| 17 | **Sandbox runtime expansion** — add Node.js/FFmpeg to Docker sandbox for video/media tools | 2h | Unblocks Remotion-class tools |
| 18 | **User-custom themes** — per-user theme via settings panel, stored per-user | 45 min | Personalization |

### Tier 4 — Polish (delight)

| # | Item | Effort | Impact | Status |
|---|---|---|---|---|
| 19 | **Benchmark dashboard** — cost per feature, token trends, model routing stats | 2h | Operational visibility |
| 20 | **Pipeline resume** — interrupted evaluations recover from last stage after restart | 2h | Reliability |
| 21 | **Collaborative workflow** — two users on same project via shared blackboard | 3h | Team capability |
| 22 | **Plugin system** — third-party tool/agent/skill packages via a manifest | 4h | Ecosystem |

---

See `docs/feature-pipeline.md` for the full feature evaluation architecture.