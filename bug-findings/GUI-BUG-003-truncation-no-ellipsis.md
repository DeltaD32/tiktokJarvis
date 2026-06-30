# GUI-BUG-3: Message truncation missing ellipsis for user messages

**Severity**: Low
**Found**: 2026-06-29, GUI visual audit
**File**: `frontend/src/App.jsx` — conversation rendering

## Reproduction

1. Send a message longer than 200 characters
2. User message shown as 250 chars without "..." suffix
3. Assistant message correctly shows 200 chars with "..."

## Root Cause

There are two different truncation points in App.jsx:
1. Inline conversation overlay: `.slice(-6)` messages, each truncated to 200 chars with `+ "..."` — this correctly shows ellipsis for assistant messages
2. Some other rendering path: user message is truncated at 250 chars without adding "..." 

The inconsistency comes from different rendering paths or different `.slice()` lengths.

## Fix

Ensure all message truncation paths consistently add "..." suffix when text is truncated:
```jsx
const truncate = (text, max) => 
    text.length > max ? text.slice(0, max) + '...' : text
```

## Verification

1. Send message > 200 chars
2. Both user and assistant messages should show "..."
3. Full messages accessible via click-to-copy
