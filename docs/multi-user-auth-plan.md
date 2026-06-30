# Multi-User Auth System — Architecture Plan

## Overview

Dela currently runs as a single-user laptop assistant. All state is global,
the server has no auth, and every WebSocket client shares one conversation.
This plan transforms Dela into a **multi-user server** with role-based access
control, per-user state isolation, and a login flow on the frontend.

**Design principles:**
- Extend at the edges, never rewrite the core. Brain/brain loop stays unchanged.
- One new module per concern. Auth, users, permissions are each a thin seam.
- State isolation by user directory, not by database migration.
- JWT for stateless auth (works across multiple server instances if needed).

---

## 1. User Model

### Roles

| Role | Capabilities |
|---|---|
| `admin` | Full access — manage users, view all state, configure system, kill/resume heartbeat, run security scans, view all audit logs |
| `user` | Own state only — chat, memory, tasks, workflows, sessions, gate confirmations. Cannot manage other users or change system config. |
| `viewer` | Read-only access to own state. Can chat but no gate approvals, no tool execution. (Future: optional lowest tier) |

### User schema (stored in `dela_state/users.db` — SQLite)

```
users:
  id          TEXT PRIMARY KEY (UUID)
  username    TEXT UNIQUE NOT NULL
  email       TEXT UNIQUE
  password    TEXT NOT NULL (bcrypt hashed)
  role        TEXT NOT NULL DEFAULT 'user'
  display_name TEXT
  created_at  TEXT NOT NULL (ISO 8601)
  last_login  TEXT
  active      INTEGER DEFAULT 1

sessions:
  token       TEXT PRIMARY KEY (JWT jti or UUID)
  user_id     TEXT NOT NULL REFERENCES users(id)
  created_at  TEXT NOT NULL
  expires_at  TEXT NOT NULL
  revoked     INTEGER DEFAULT 0
```

### Why SQLite for users

- Zero new dependencies (sqlite3 is in Python stdlib)
- Single file, easy to back up
- Fast enough for user lookups (cached in memory after first load)
- No separate database server needed

---

## 2. Auth Layer

### Token flow (JWT)

```
1. POST /api/auth/login  {username, password}
   → validates bcrypt hash
   → returns {access_token, refresh_token, user: {id, username, role}}

2. All subsequent requests include:
   Authorization: Bearer <access_token>

3. WebSocket connection:
   ws://host/ws?token=<access_token>
   → server validates on connect, extracts user context
   → connection is scoped to that user

4. POST /api/auth/refresh  {refresh_token}
   → returns new access_token

5. POST /api/auth/logout
   → revokes token (adds to revoked list)
```

### Token config

```
JWT_SECRET:        from DELA_JWT_SECRET env var (required)
ACCESS_EXPIRY:     24 hours
REFRESH_EXPIRY:    30 days
ALGORITHM:         HS256
```

### New files

| File | Purpose |
|---|---|
| `dela/auth.py` | JWT encode/decode, password hashing, token validation |
| `dela/auth_middleware.py` | FastAPI middleware — extracts user from Bearer token, attaches to request |
| `dela/users.py` | User CRUD (create, get, list, update, delete), role checks |
| `dela/server.py` | Added auth endpoints, middleware wiring, per-user state |

### Dependencies added

- `PyJWT` — already installed (MCP uses it)
- `bcrypt` — new, pure Python, ~30KB

---

## 3. State Isolation

### Directory structure

```
dela_state/
├── users.db                    # Auth + user records
├── system/                     # Shared system config (not per-user)
│   ├── heartbeat_config.json
│   ├── vuln_kb.json
│   ├── routing_cache.json      # Shared across users (or per-user)
│   └── schedule.json
├── users/{user_id}/            # Per-user state
│   ├── memory.json
│   ├── notices.json
│   ├── agent_memory.json
│   ├── audit.log
│   ├── cost_tally.json
│   ├── live_settings.json
│   ├── sessions/
│   ├── blackboards/
│   └── projects/
└── global/                     # Legacy: migrated on first multi-user run
```

### Migration path

On first startup with `DELA_MULTI_USER=1`:
1. If `users.db` doesn't exist, create it with a default admin user
2. Move existing state files to `global/` for reference
3. New users get clean isolated state directories

### Module changes for state isolation

| Module | Change |
|---|---|
| `memory.py` | `_STORE` path becomes `dela_state/users/{user_id}/memory.json` |
| `noticeboard.py` | `_STORE` becomes per-user path |
| `audit.py` | Log to `dela_state/users/{user_id}/audit.log`; `[user:xxx]` prefix in log lines |
| `audit.py` cost tracking | Per-user counters |
| `sessions.py` | `session_id` scoped within user directory |
| `agent_memory.py` | Per-user path — agents learn per user |
| `live_config.py` | Per-user settings file |
| `blackboard.py` | Blackboards stored per-user |
| `projects.py` | Projects stored per-user |
| `config.py` | `get_user_config(user_id)` — resolves profile per-user |
| `provider.py` | `_active_connection(user_id)` — per-user API connections |

---

## 4. Server Changes (`server.py`)

### Auth middleware

```python
# Added to app startup:
app.add_middleware(AuthMiddleware)  # After CORS, before routes

class AuthMiddleware:
    """Extracts JWT from Authorization header, attaches user to request."""
    - Skips /api/auth/login, /api/auth/register, /health, /docs
    - Validates token on all other /api/* routes
    - Injects request.state.user = {"id": ..., "username": ..., "role": ...}
    - Returns 401 if missing/invalid/expired token
```

### WebSocket auth

```python
# ws_endpoint now:
async def ws_endpoint(ws: WebSocket):
    token = ws.query_params.get("token")
    user = auth.validate_token(token)  # 4001 close code if invalid
    
    # Register client per-user
    _clients[user.id] = ws
    _histories[user.id] = sessions.get_or_create_history(f"user_{user.id}")
    
    # Send initial state scoped to user
    await ws.send_json({"type": "init", "user": user, ...})
```

### Per-user state in server

| Old (global) | New (per-user) |
|---|---|
| `_clients: set[WebSocket]` | `_clients: dict[str, WebSocket]` (keyed by user_id) |
| `_history: list[dict]` | `_histories: dict[str, list[dict]]` |
| `_confirm_callbacks: dict[str, Event]` | `_confirm_callbacks: dict[str, dict[str, Event]]` (user_id → cid → Event) |
| `_brain_lock` | Per-user lock or remain global (serialize all brain calls) |

### Confirmation gate per-user

```python
class WebSocketConfirmer:
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def confirm(self, description: str, timeout=None) -> bool:
        # Send confirmation_request ONLY to this user's WebSocket
        ws = _clients.get(self.user_id)
        if ws:
            asyncio.run(ws.send_json({
                "type": "confirmation_request",
                "cid": cid,
                "description": description
            }))
```

### New REST endpoints

| Endpoint | Method | Role | Purpose |
|---|---|---|---|
| `/api/auth/login` | POST | public | Login, returns JWT |
| `/api/auth/refresh` | POST | public | Refresh access token |
| `/api/auth/logout` | POST | any | Revoke token |
| `/api/auth/me` | GET | any | Get current user profile |
| `/api/users` | GET | admin | List all users |
| `/api/users` | POST | admin | Create user |
| `/api/users/{id}` | GET | admin/self | Get user details |
| `/api/users/{id}` | PUT | admin/self | Update user (role change = admin only) |
| `/api/users/{id}` | DELETE | admin | Delete/deactivate user |
| `/api/users/{id}/password` | PUT | admin/self | Change password |

### Existing endpoint auth requirements

| Group | Auth | Notes |
|---|---|---|
| Memory, Notices, Tasks, Sessions | user | Scoped to own data |
| Audit, Analytics | admin | Admin sees all; user sees own if `?scope=self` |
| Heartbeat, Settings, Connections, OAuth | admin | System-level config |
| Tools, Agents, Status, Voices, Models | user | Read-only for all |
| Security scan, Vuln KB | admin | System-level security |
| Workflows | user | Own workflows only |
| State browser | user | Own state only; admin sees all |
| Uplink, Ollama | admin | System health |

---

## 5. Brain Changes

### User context threading

```python
# brain.py — minimal change: optional user_id for audit/gate
def respond(
    history: list[Message],
    user_text: str,
    model: str | None = None,
    user_id: str | None = None,  # NEW
) -> Iterator[str]:
    # Pass user_id through to _run_one_tool for gate + audit
```

### Gate call updated

```python
# In _run_one_tool():
if score >= threshold:
    granted = gate.ask(name, description, user_id=user_id)  # user_id added
    audit.confirmation_request(name, description, granted, user_id=user_id)
```

### Sub-agents

Sub-agents inherit the parent user's context. They don't need their own user_id — they run as the parent user. This means blackboard/project operations are already user-scoped if the parent carries user_id.

---

## 6. Frontend Changes

### New files

| File | Purpose |
|---|---|
| `frontend/src/contexts/AuthContext.jsx` | React context — user, token, login/logout |
| `frontend/src/components/LoginPage.jsx` | Login form (username + password) |
| `frontend/src/components/AdminPanel.jsx` | User management (admin only) |

### Modified files

| File | Change |
|---|---|
| `main.jsx` | Wrap app in `<AuthProvider>` |
| `App.jsx` | Show LoginPage if not authenticated; show AdminPanel tab if admin role |
| `useDelaWS.js` | Pass token in WebSocket URL; handle 4001 close (token expired → redirect to login) |
| All `fetch()` calls | Include `Authorization: Bearer <token>` header |
| `SettingsPanel.jsx` | Add profile/account section; add user management tab (admin) |
| `TopStrip.jsx` | Add user avatar/name, logout button |

### Auth flow

```
1. User opens Dela → LoginPage
2. POST /api/auth/login → receive JWT
3. Store JWT in AuthContext (localStorage for persistence)
4. Connect WebSocket with ?token=<jwt>
5. All REST calls include Authorization header
6. On 401/403 response → redirect to LoginPage
7. On logout → revoke token, clear context, redirect to LoginPage
```

### Role-based UI

| Element | admin | user |
|---|---|---|
| Chat input | Yes | Yes |
| Memory panel | Yes (own) | Yes (own) |
| Notices panel | Yes (own) | Yes (own) |
| Audit panel | Yes (all) | Yes (own) |
| Settings panel | Yes (system) | Yes (profile only) |
| Admin panel (user mgmt) | Yes | No |
| Heartbeat control | Yes | No |
| Security scan | Yes | No |
| Connections config | Yes | No |

---

## 7. Security Considerations

### Password policy
- Minimum 8 characters, no maximum
- bcrypt cost factor: 12 (industry standard)
- Rate limit: 5 failed login attempts per IP per 15 minutes
- Password reset: admin-only for now (email-based reset = future)

### Token security
- Access tokens: 24h expiry, stored in memory (not localStorage ideally, but localStorage is acceptable for a self-hosted tool)
- Refresh tokens: stored in httpOnly cookie (future) or in secure storage
- Token revocation: on logout, add jti to revoked list in users.db; prune expired revoked tokens daily

### Multi-user isolation
- Brain lock: serialize brain calls to prevent interleaved conversations
- History: each user has isolated conversation history
- File system: each user has isolated directory, no cross-user file access
- API: middleware enforces user scope; admin endpoints check role

### Threat model
| Threat | Mitigation |
|---|---|
| Token theft (XSS) | HttpOnly cookie for refresh token (future); short access token life |
| Privilege escalation | Role check in middleware, not just UI |
| Cross-user data access | State isolation by directory; user_id filter on all queries |
| Brute force login | Rate limiting on /api/auth/login |
| Session fixation | New JWT on each login; refresh rotation |
| WebSocket hijacking | Token validated on connect; 4001 on invalid |

---

## 8. Implementation Order

### Phase 1 — Auth core (new modules, no breaking changes)
1. `dela/users.py` — User model, CRUD, SQLite setup
2. `dela/auth.py` — JWT encode/decode, password hashing
3. `dela/auth_middleware.py` — FastAPI middleware
4. `dela/server.py` — Add auth endpoints (`/api/auth/login`, `/api/auth/me`)
5. Admin seeder: create default admin on first run

**Verify:** POST /api/auth/login returns JWT; GET /api/auth/me works with token

### Phase 2 — State isolation (per-user directories)
1. `dela/memory.py` — Per-user memory store
2. `dela/sessions.py` — Per-user session directories
3. `dela/audit.py` — Per-user audit log + cost tracking
4. `dela/noticeboard.py` — Per-user notices
5. `dela/live_config.py` — Per-user settings
6. `dela/blackboard.py`, `dela/projects.py` — Per-user ownership
7. Migration script: move existing state to `global/`

**Verify:** Two users can connect, each sees only their own memory/conversations

### Phase 3 — Server multi-user wiring
1. `server.py` — Per-user `_clients`, `_histories`, `_confirm_callbacks`
2. `server.py` — WebSocket auth via query param
3. `server.py` — `_handle_message` accepts user context
4. `server.py` — `WebSocketConfirmer` scoped to user
5. `server.py` — Auth middleware on all `/api/*` routes
6. `server.py` — Role-based endpoint access (admin/user)

**Verify:** Two users chat simultaneously in separate browser tabs

### Phase 4 — Frontend
1. `AuthContext.jsx` — Login state, token storage, auth helpers
2. `LoginPage.jsx` — Login form
3. `App.jsx` — Auth guard, login redirect
4. `TopStrip.jsx` — User info, logout
5. `useDelaWS.js` — Token in WebSocket URL
6. All fetch calls — Authorization header
7. `AdminPanel.jsx` — User management (admin only)

**Verify:** Login flow works; admin sees user management; user doesn't

### Phase 5 — Polish
1. Rate limiting on auth endpoints
2. Token refresh flow
3. Role-based UI hiding (admin-only panels)
4. Audit log includes `[user:xxx]` prefix
5. Cost tracking per user
6. Password change flow
7. Documentation updates

---

## 9. Environment Variables (additions to .env)

```
# Multi-user auth (required for multi-user mode)
DELA_MULTI_USER=1                    # Enable multi-user mode
DELA_JWT_SECRET=<random-64-char>     # JWT signing secret (generate with: openssl rand -hex 32)
DELA_ADMIN_EMAIL=admin@dela.local    # Default admin email (first run only)
DELA_ADMIN_PASSWORD=changeme         # Default admin password (first run only)

# Optional
DELA_ACCESS_TOKEN_EXPIRY=24          # Hours until access token expires
DELA_REFRESH_TOKEN_EXPIRY=30         # Days until refresh token expires
DELA_MAX_LOGIN_ATTEMPTS=5            # Rate limit threshold
DELA_LOGIN_LOCKOUT_MINUTES=15        # Lockout duration
```

---

## 10. Impact Summary

| Area | What Changes |
|---|---|
| Brain (`brain.py`) | 3 lines: add optional `user_id` to `respond()`, pass to gate, pass to audit |
| Provider (`provider.py`) | `_active_connection()` accepts `user_id` |
| Gate (`gate.py`) | `ask()` accepts `user_id`; Confirmer protocol adds `user_id` |
| Memory | `_STORE` path changes; all functions accept `user_id` |
| Audit | Per-user log; `[user:xxx]` prefix |
| Server | Major: auth middleware, per-user state dicts, WebSocket auth, new endpoints |
| Frontend | New: LoginPage, AuthContext, AdminPanel. Modified: App, TopStrip, useDelaWS |
| Config | `get_user_config(user_id)` added |
| New deps | `bcrypt` only (PyJWT already installed) |
| Breaking | Yes — first multi-user startup requires state migration |
