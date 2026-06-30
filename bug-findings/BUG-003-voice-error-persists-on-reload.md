# BUG-3: Voice error persists across page reloads

**Severity**: Low
**Found**: 2026-06-29, Playwright audit
**File**: `frontend/src/App.jsx`

## Reproduction

1. Click MIC to start recording
2. Click STOP (with no real mic input — STT returns error)
3. Observe: "Voice error: Transcription failed" shown below input
4. Refresh the page (F5 or Ctrl+R)
5. Observe: error message still visible

**Expected**: Error clears on fresh page load
**Actual**: Error persists

## Root Cause

`voiceError` state in App.jsx is initialized to `null` but once set, is never cleared on component mount/remount. If React preserves state across HMR refreshes (Vite dev server behavior), the error persists. Also, if the state is stored in sessionStorage or a parent component, it survives navigation.

## Impact

- Cosmetic: stale error message displayed until next voice interaction
- Confusing: user sees "Transcription failed" on a fresh page load when no voice interaction has occurred

## Fix

Add a `useEffect` to clear `voiceError` on mount:

```jsx
// App.jsx
useEffect(() => {
    setVoiceError(null)
}, [])
```

Or reset it in the component initializer:
```jsx
const [voiceError, setVoiceError] = useState(null)  // already null by default
```

If the issue is Vite HMR state preservation, this may be a Vite config issue rather than application code.

## Verification

1. Trigger a voice error
2. Refresh page
3. Error message should be gone
