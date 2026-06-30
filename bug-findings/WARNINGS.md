# Warnings (Non-Functional)

## WARN-1: WebSocket initial connection transient failure

**Severity**: Info (no impact)
**Console**: `WebSocket connection to 'ws://localhost:5173/ws' failed: WebSocket is closed before the connection is established.`
**Location**: `frontend/src/hooks/useDelaWS.js` — initial `connect()` call

**Cause**: React StrictMode mounts the component → `connect()` creates WebSocket → backend not fully ready → connection fails → browser logs warning. Reconnect fires after 3.5s and succeeds.

**Why not a bug**: The `connIdRef` pattern correctly handles StrictMode double-mount. The reconnect successfully establishes a WebSocket connection within 3.5 seconds. Application functions normally after this.

**Mitigation**: Add a 500ms delay before first connection attempt:
```javascript
const connect = useCallback(() => {
    // ...
    setTimeout(() => {
        const ws = new WebSocket(WS_URL)
        // ...
    }, 500)
}, [])
```

---

## WARN-2: Dock.jsx CSS animation/animationDelay React warning

**Severity**: Info (no impact)
**Console**: 
```
Warning: Updating animation animationDelay ... don't mix shorthand and non-shorthand 
properties for the same value
    at div
    at div
    at div  
    at div
    at Dock (Dock.jsx:17:24)
```

**Location**: `frontend/src/components/Dock.jsx` — heartbeart mic bars animation

**Cause**: Dock.jsx applies `animation` (CSS shorthand) in one render and `animationDelay` (longhand) in another, or vice versa. React 18 detects the conflict during reconciliation.

**Fix**: Use consistent CSS property approach:
```jsx
style={{
    animationName: 'jeq',
    animationDuration: '...',
    animationDelay: '...',
    // ... instead of mixing animation shorthand with animationDelay
}}
```

---

## WARN-3: Favicon 404

**Observed**: `GET /favicon.ico` returns 404
**Fix**: Add a `favicon.ico` to `frontend/public/`
