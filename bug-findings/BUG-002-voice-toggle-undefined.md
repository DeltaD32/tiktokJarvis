# BUG-2: Voice toggle fires two STT calls — first returns `undefined`

**Severity**: Low
**Found**: 2026-06-29, Playwright audit  
**Files**: `frontend/src/hooks/useVoiceRecorder.js`, `frontend/src/App.jsx`

## Reproduction

1. Open app at http://localhost:5173/
2. Click MIC button
3. Click STOP button
4. Check browser console

**Console output**:
```
[voice] STT result: undefined      ← first call (from start())
[voice] empty/error — not sending  
[voice] STT result: ""             ← second call (from stop())
[voice] empty/error — not sending  
```

Two `[voice] STT result:` logs appear, one with `undefined`.

## Root Cause

The `useVoiceRecorder` hook's `toggle()` function has asymmetric return types:

```javascript
// useVoiceRecorder.js
const toggle = useCallback(() => {
    if (recording) {
      return stop()   // Returns Promise<string>
    } else {
      return start()  // Returns undefined (no return statement)
    }
}, [recording, start, stop])
```

The caller in `App.jsx`:

```javascript
const handleVoiceToggle = async () => {
    const text = await toggleVoice()  // undefined when starting
    console.log('[voice] STT result:', JSON.stringify(text))
```

When the user clicks MIC to START recording, `toggle()` calls `start()` which has no return value, but `handleVoiceToggle` still `await`s it and logs `undefined`.

The SECOND call (when user clicks STOP) comes from the actual `stop()` promise resolving — but this may happen during StrictMode's unmount/remount cycle, causing the `toggle()` to be called twice with different `recording` state values.

## Impact

- No user-visible error (the `undefined` result is caught by the empty/error guard)
- Creates confusing console noise
- Potentially double-STT calls in certain timing scenarios

## Fix

### Option A: Only await when stopping

```javascript
// App.jsx - handleVoiceToggle
const handleVoiceToggle = async () => {
    if (recordingRef.current) {
      const text = await toggleVoice()
      console.log('[voice] STT result:', JSON.stringify(text))
      // ... rest of handler
    } else {
      toggleVoice()  // Don't await start()
    }
}
```

### Option B: Make start() return a Promise too

```javascript
// useVoiceRecorder.js
const start = useCallback(() => {
    return new Promise((resolve) => {
      // ... start recording
      resolve('')  // empty string for start (not an STT result)
    })
}, [])
```

### Option C: Separate start/stop into distinct functions

```javascript
const handleVoiceToggle = () => {
    if (recording) {
      stop().then(text => {
        console.log('[voice] STT result:', JSON.stringify(text))
        // handle result
      })
    } else {
      start()
    }
}
```

**Recommendation**: Option C — cleanest separation of concerns. Option A is simplest minimal fix.

## Verification

After fix:
1. Click MIC → console shows no `[voice]` log
2. Click STOP → console shows exactly one `[voice] STT result: "..."` 
3. No `undefined` logs
