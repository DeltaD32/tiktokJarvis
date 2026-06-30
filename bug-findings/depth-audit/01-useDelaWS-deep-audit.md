# Deep Audit: useDelaWS.js — WebSocket Hook

**File**: `frontend/src/hooks/useDelaWS.js` (229 lines)
**Audit scope**: Race conditions, stale closures, memory leaks, error handling, message ordering, buffer management, connection lifecycle, state machine correctness, edge cases

---

## Summary

| Severity | Count | Key themes |
|----------|-------|------------|
| CRITICAL | 5 | `_processingTurn` permanent deadlock; unrecoverable after disconnect, reconnect, or server-idle |
| HIGH | 2 | No state reset on disconnect; stale state surfaced to UI after reconnect |
| MEDIUM | 10 | setState-after-unmount; unbounded buffer; silent send failures; idleTimer leaks; per-token re-render |
| LOW | 8 | Missing diagnostics; binary frame handling; edge-case gaps; cosmetic state flickers |

**Total: 25 issues**

---

## CRITICAL Issues

### C1. `_processingTurn` stuck permanently after WebSocket drops mid-turn
**Line**: 172 set, 92 reset only
**Problem**: `_processingTurn.current = true` is set in `sendMessage` and reset ONLY in `reply_done` (:92). If connection dies after send but before `reply_done`, `_processingTurn` stays `true` **forever**. All future `sendMessage` calls silently rejected (:164-166). No timeout, no watchdog, no reset in `onclose` or `init`.

### C2. `_processingTurn` not reset on reconnect / `init`
**Lines**: 48-53 (init handler), 172 (set), 92 (reset)
**Problem**: After reconnect, server sends `init`, but `_processingTurn.current` is never cleared. Since prior connection likely dropped mid-turn, user permanently locked out.

### C3. `state_change: idle` from server does not reset `_processingTurn`
**Lines**: 55-68 (state_change handler), 92 (reset only in reply_done)
**Problem**: Server can emit `state_change: idle` to transition orb. Client handles this (:60-65) but does NOT set `_processingTurn.current = false`. Only `reply_done` resets it. If server sends idle without reply_done (error, cancellation), sendMessage permanently blocked.

### C4. `_processingTurn` guard destroys message ordering across reconnections
**Lines**: 164-166, 172, 92
**Problem**: When `_processingTurn` gets stuck, user's message is already in conversation state (:174) with no assurance server received it. On reconnect, no replay, no sync, no recovery. Conversation has "ghost" user message with no reply.

### C5. Only two reset paths exist for `_processingTurn`
**Lines**: 92 (reply_done) and 26 (initial value)
**Problem**: Not reset in `onclose`, `init`, `state_change`, or `sendConfirm` denial. No timeout/watchdog. Any path that activates `_processingTurn` but doesn't reach `reply_done` leaves hook permanently broken until remount.

---

## HIGH Issues

### H1. No `_processingTurn` / `toolStatus` / `orbState` / `currentStream` reset on disconnect
**Lines**: 135-140 (onclose handler)
**Problem**: `onclose` sets `connected = false` but doesn't reset `toolStatus` (:14), `currentStream` (:13), or `_processingTurn` (:26). UI shows stale tool status, frozen stream, or locked send button indefinitely after disconnect.

### H2. No state reset on reconnect — stale state from old connection surfacing
**Lines**: 48-53 (init)
**Problem**: On reconnect, `init` only sets `notices`, `noticeCount`, `heartbeatActive`, `cost`. All stream, tool, and processing state from old connection remains.

---

## MEDIUM Issues

### M1. setState calls in WebSocket handlers fire after unmount
**Lines**: 41, 49-128, 136, 149
**Problem**: When cleanup closes WebSocket (:149), queued `onmessage` and `onclose` handlers still fire and call React state setters. Cleanup increments `connIdRef` (:148) to suppress reconnect but doesn't prevent stale state calls.

### M2. `streamBuffer` has no size limit — unbounded growth
**Line**: 75
**Problem**: `streamBuffer.current += data.content` grows without bound. Runaway/malicious server streaming gigabytes exhausts browser memory. No cap, truncation, or back-pressure.

### M3. `setCurrentStream` called on every token — 10,000 re-renders
**Line**: 76
**Problem**: Every `token` message triggers `setCurrentStream(streamBuffer.current)`. A 10,000-token reply = 10,000 React state updates and re-renders. Performance bottleneck for long streams.

### M4. `send()` does not guard against CONNECTING readyState
**Line**: 156
**Problem**: `wsRef.current?.readyState === WebSocket.OPEN` drops messages when socket is CONNECTING. During reconnection, sendMessage between `connect()` and `onopen` is silently lost.

### M5. `JSON.stringify` in `send` can throw on non-serializable payloads
**Line**: 157
**Problem**: No try/catch. Circular object or BigInt crashes send synchronously with no error boundary.

### M6. `idleTimer` not cleared in `onclose` handler
**Lines**: 135-140, 62-64, 95-97
**Problem**: If connection drops while 60s idle timer pending, callback fires later calling `setOrbState('idle')` on component with new connection in different state. SendMessage (:168) and state_change (:56) clear it, but not onclose.

### M7. `idleTimer` callback fires after reconnect sets new state
**Lines**: 62-64, 95-97
**Problem**: setTimeout callback sets orbState to 'idle' unconditionally. If reconnect happens and server sends `state_change: thinking` before stale 60s timer fires, timer overrides to idle. Not cleared by onclose (see M6).

### M8. `streamBuffer` retains stale content across reconnections
**Lines**: 24, 75, 177
**Problem**: When `connect()` reconnects, `streamBuffer.current` not cleared. Old stream text persists. Next `sendMessage` clears it (:177), but if `reply_done` fires for old stream on new connection, stale text committed to conversation.

### M9. Empty assistant reply silently dropped
**Line**: 84
**Problem**: `if (reply)` is falsy for empty string `""`. Legitimate empty reply (error, tool-only turn) never added to conversation. User sees no response and no error.

### M10. Reconnect timer conflict if onclose fires during manual connect()
**Lines**: 30-33, 138
**Problem**: Old WebSocket not explicitly closed before overwriting `wsRef.current` (:39). If still in OPEN/CONNECTING, becomes orphaned. connId guard suppresses double-reconnect but doesn't close old socket.

---

## LOW Issues

### L1. `ws.onerror` swallows all diagnostics
**Line**: 142
No logging, no error state exposed to UI, no distinction between transient and permanent failures.

### L2. `sendConfirm` does not validate `id` or `approved`
**Lines**: 181-182
Malformed object sent to server if called with null id or non-boolean approved.

### L3. No sequence numbering — no replay/dedup protocol
**Lines**: 43-133
`msgIdRef` is local increment (:173, :85), never sent to server. If server resends or deduplicates, no protocol exists.

### L4. `data.content` could be null/undefined — "null" string injected
**Line**: 75
`streamBuffer.current += data.content` concatenates "null" or "undefined" string if data.content is null/undefined.

### L5. Binary WebSocket frames silently dropped
**Line**: 45
JSON.parse on binary data throws, caught by empty catch, returning silently.

### L6. `connected` state doesn't distinguish CONNECTING from OPEN
**Lines**: 10, 41, 136
Consumers can't show "connecting..." vs "disconnected" indicator.

### L7. `connIdRef` not checked in `onmessage` handler
**Line**: 43
Unlike onclose/onerror, onmessage doesn't guard against stale connections. Stale reply_done could add duplicate conversation entry.

### L8. `state_change` into idle always delays 60 seconds
**Lines**: 60-65
Even when server says "idle now" (error, timeout), client forces 60s delay. Orb stuck in current state, misaligned with server intent.

---

## Areas With Zero Issues
- **Stale closures**: All useCallback hooks reference stable setters and refs. No issues.
- **Missing useEffect deps**: All useCallback/useEffect satisfy exhaustive-deps.
- **Type coercion**: All comparisons use `===`. No implicit coercion risks.
