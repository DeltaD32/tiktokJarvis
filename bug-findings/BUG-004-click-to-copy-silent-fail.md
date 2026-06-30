# BUG-4: Click-to-copy silently fails when clipboard permission denied

**Severity**: Low
**Found**: 2026-06-29, Playwright audit
**File**: `frontend/src/App.jsx`, ~line 383

## Reproduction

1. In a browser without clipboard permissions (incognito, Playwright, HTTP origin)
2. Click a conversation message
3. Nothing happens — no visual feedback, no copy

**Expected**: Message copied to clipboard OR user sees an error
**Actual**: Silent failure — `.catch(() => {})` swallows the error

## Root Cause

```jsx
// App.jsx ~line 383
onClick={() => {
    navigator.clipboard.writeText(msg.content).catch(() => {})
}}
```

The Clipboard API requires:
- Secure context (HTTPS or localhost)
- User permission (some browsers)

When denied, the error is silently caught with no user feedback.

## Impact

- User clicks thinking they copied but nothing happened
- No way for user to know copy failed
- Particularly affects: Playwright, incognito mode, browsers with strict clipboard policies, HTTP origins (non-localhost)

## Fix

### Option A: Fallback to execCommand

```jsx
onClick={() => {
    navigator.clipboard.writeText(msg.content).catch(() => {
        // Fallback for non-secure contexts
        const textarea = document.createElement('textarea')
        textarea.value = msg.content
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.select()
        try {
            document.execCommand('copy')
        } catch(e) {}
        document.body.removeChild(textarea)
    })
}}
```

### Option B: Show toast on failure

```jsx
onClick={() => {
    navigator.clipboard.writeText(msg.content).catch(() => {
        setToast('Copy failed — check browser permissions')
    })
}}
```

### Option C: Visual feedback on success, silent on failure

```jsx
onClick={() => {
    navigator.clipboard.writeText(msg.content)
        .then(() => setToast('Copied!'))
        .catch(() => {})
}}
```

**Recommendation**: Option A + C combined — try clipboard API first, fall back to execCommand, always show visual feedback.

## Verification

1. Open in Playwright or incognito browser
2. Click a conversation message
3. Should see brief "Copied!" feedback (or fallback copy works)
4. If both fail, should see "Copy failed" message
