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

## Implementation Order

1. **Tracing** (smallest, gives visibility for everything after)
2. **Sub-agents** (highest architectural value, on the spec roadmap)
3. **Skills** (builds on sub-agents, enhances context management)
4. **MCP support** (opens up the external tool ecosystem)
5. **Sandboxed execution** (high-value tool, usable by sub-agents)
6. **IM channels** (new entry points, uses everything above)

Each step ends with something runnable and a verification test. Don't start
a step until the previous one works on its own.