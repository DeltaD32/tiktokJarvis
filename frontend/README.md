# Dela — Holographic UI

A Jarvis-style web frontend for the Dela voice assistant. Built with React, Three.js, and WebSockets.

---

## What it looks like

A full-screen holographic display centered on a 3D animated orb — glowing orbital rings, a particle cloud, and bloom lighting — all reacting in real-time to what Dela is doing. Conversation text overlays the bottom of the scene as cinematic subtitles. Modal panels slide in from the right when Dela opens them (or when you trigger them manually from the top bar).

**Orb states and their colors:**

| State | Color | When |
|---|---|---|
| Idle | Cyan `#00c8ff` | Waiting |
| Thinking | Amber `#ffaa00` | Processing a request, calling tools |
| Speaking | Green `#00ff88` | Reply arriving |
| Listening | Bright cyan `#00f0ff` | (reserved for future mic integration) |
| Alert | Red `#ff4400` | Confirmation dialog awaiting yes/no |

---

## Quick start

### 1. Start the backend

```bash
# from the repo root
pip install -r requirements.txt
uvicorn dela.server:app --port 8000 --reload
```

The server starts the Dela heartbeat, wires the WebSocket confirmation gate, and serves `/api/*` REST endpoints.

### 2. Start the frontend dev server

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api` and `/ws` to `localhost:8000`.

### 3. Production build

```bash
cd frontend
npm run build
```

The built `dist/` is picked up automatically by the FastAPI server and served at `http://localhost:8000`. A single `uvicorn dela.server:app --port 8000` command serves everything.

---

## Architecture

```
Browser (React)
  │  WebSocket ws://localhost:8000/ws      — streaming replies, tool blips,
  │                                          confirmation requests, panel commands
  │  HTTP /api/*                           — memory CRUD, notices, tasks, audit, status
  ▼
FastAPI  (dela/server.py)
  │  imports from dela.*
  ▼
Dela backend  (existing — no changes to core)
```

### WebSocket event protocol

**Server → client:**

| Event | Fields | Meaning |
|---|---|---|
| `init` | `notices`, `heartbeat_active`, `cost` | Sent on connect |
| `state_change` | `state` | Orb visual state update |
| `token` | `content`, `tool_blip` | Streaming reply or tool status |
| `reply_done` | — | Full reply complete |
| `confirmation_request` | `id`, `description` | Dela needs a yes/no |
| `open_panel` | `panel`, `message` | Dela wants to show a panel |
| `notice` | `notice` | New heartbeat notice |
| `notices_refresh` | `notices` | Full notice list refresh |
| `heartbeat_state` | `active` | Heartbeat kill/resume |
| `cost_update` | `cost` | Updated cost string |

**Client → server:**

| Event | Fields | Meaning |
|---|---|---|
| `message` | `content` | User sent a message |
| `confirm` | `id`, `approved` | Response to confirmation dialog |
| `dismiss_notice` | `id` | Dismiss a notice by ID |

---

## Panels

Panels slide in from the right edge. They can be opened two ways:

1. **By Dela** — Dela calls the `show_panel` tool mid-conversation:
   ```
   You: "show me my tasks"
   Dela: [calls show_panel(panel="tasks", message="Here are your open items")]
         → Tasks panel slides in automatically
   ```

2. **By you** — click **AUDIT** or **NOTICES** in the top bar, or ask Dela to open one.

Available panels: `tasks`, `notices`, `audit`. (The `memory` panel is wired in the server but the frontend doesn't render it yet — easy to add following the `TasksPanel` pattern.)

---

## Adding a new panel

1. Create `src/components/panels/MyPanel.jsx` — wrap content in `<HoloPanel title="..." onClose={onClose}>`.
2. Import it in `App.jsx` and add a branch in the `<AnimatePresence>` block for `panel === 'my_panel'`.
3. Add `"my_panel"` to the `show_panel` tool's `enum` in `dela/tools/ui_tools.py`.

---

## Tech stack

| Layer | Library |
|---|---|
| 3D rendering | [React Three Fiber](https://docs.pmnd.rs/react-three-fiber) + [Three.js](https://threejs.org) |
| 3D helpers | [@react-three/drei](https://github.com/pmndrs/drei) — `MeshDistortMaterial` |
| Post-processing | [@react-three/postprocessing](https://github.com/pmndrs/react-postprocessing) — `Bloom` |
| Panel animations | [Framer Motion](https://www.framer.com/motion/) |
| Icons | [Lucide React](https://lucide.dev) |
| Build | [Vite](https://vitejs.dev) |
| Fonts | Orbitron (headings), Share Tech Mono (body) — Google Fonts |

---

## Files

```
frontend/
├── index.html                     — Google Fonts link, root div
├── package.json
├── vite.config.js                 — dev proxy: /api and /ws → localhost:8000
└── src/
    ├── main.jsx                   — React root
    ├── App.jsx                    — Layout: canvas + overlay UI + panels
    ├── hooks/
    │   └── useDelaWS.js           — WebSocket connection, all app state
    ├── components/
    │   ├── JarvisOrb.jsx          — 3D orb: sphere, rings, particles, bloom
    │   ├── HoloPanel.jsx          — Shared panel wrapper (slide-in animation)
    │   ├── ConversationOverlay.jsx — Chat transcript overlay with typewriter
    │   ├── ConfirmationDialog.jsx  — Yes/no gate dialog
    │   ├── TopBar.jsx             — Status, cost, heartbeat controls
    │   └── panels/
    │       ├── TasksPanel.jsx     — Task list from /api/tasks
    │       ├── NoticesPanel.jsx   — Heartbeat notices
    │       └── AuditPanel.jsx     — Live-polling audit log
    └── styles/
        └── globals.css            — Full design system (colors, layout, components)
```

---

## GUI tests (Playwright)

The frontend has a full Playwright test suite covering the idle view, conversation/WebSocket flow, top strip + dock, all three floating windows, all ten slide-in panels, the HITL confirmation gate, themes/settings, and the notices/connection-banner flow.

### Run the mocked suite (no backend needed)

```bash
cd frontend
npm test
```

This runs the `mocked` project: Playwright intercepts every `/api/**` REST call and replaces `window.WebSocket` with a controllable mock, so the tests are self-contained and deterministic. A Vite dev server is started automatically by `playwright.config.js`.

Useful flags:

```bash
npm run test:ui        # interactive UI mode — watch + time-travel debug
npx playwright test --project=mocked --headed
npx playwright test tests/panels.spec.js
npx playwright show-report   # open the HTML report
```

### Run the real-backend E2E suite (optional)

```bash
# terminal 1 — start Dela backend on :8000
python start_dela.py        # or: uvicorn dela.server:app --port 8000

# terminal 2 — run the e2e project
npm run test:e2e
```

The `e2e` project runs a small smoke suite against the live backend. It auto-skips when the backend isn't reachable, so `npm test` always works even with no Python running.

### First-time setup

```bash
cd frontend
npm install
npx playwright install chromium
```

### Test layout

```
frontend/tests/
├── fixtures/
│   ├── delaTest.js     — custom test fixture that wires REST + WS mocks onto `page`
│   ├── mockApi.js      — canned responses for every /api/* endpoint
│   └── mockWS.js       — addInitScript that swaps in a controllable WebSocket
├── pages/
│   └── AppPage.js      — page object with selectors + helpers
├── idle-view.spec.js          conversation.spec.js
├── topstrip-dock.spec.js      floating-windows.spec.js
├── panels.spec.js             hitl-gate.spec.js
├── themes-settings.spec.js    connection-notices.spec.js
└── e2e/
    ├── globalSetup.js   — pings :8000 and skips the e2e suite if down
    └── smoke.spec.js    — real-backend smoke tests
```

### Notes

- The app uses `className`-based markup (no `data-testid`), so selectors target stable classes (`.idle-input`, `.holo-panel`, `.dock-pill`, `.hitl-overlay`, …). If you rename a class in `src/`, update the matching selector in `tests/pages/AppPage.js`.
- To push a fake server message into a mocked test, use `pushWS(page, { type: 'state_change', state: 'thinking' })` from `tests/fixtures/delaTest.js`.
- To override a canned REST response for a single test, register a more specific `page.route(...)` after the fixture installs mocks — later registrations run first.
