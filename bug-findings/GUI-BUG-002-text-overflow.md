# GUI-BUG-2: Long unbroken text overflows conversation container

**Severity**: Low
**Found**: 2026-06-29, GUI visual audit
**File**: `frontend/src/App.jsx` — conversation overlay inline styles

## Reproduction

1. Send a message consisting of 500+ characters with no spaces (e.g. "AAAAA...")
2. Observe conversation display: message extends beyond viewport width
3. No wrapping or overflow:hidden clipping

## Root Cause

The conversation message container lacks `overflow-wrap: break-word` or `word-break: break-all` CSS properties. Long unbroken strings (no whitespace) are not broken across lines and overflow the container.

## Fix

Add to the conversation message inline style or CSS:

```css
overflow-wrap: break-word;
word-break: break-all;
max-width: 100%;
overflow: hidden;
```

In `App.jsx`, add to the message display div's style:
```jsx
style={{
    maxWidth: '100%',
    overflowWrap: 'break-word',
    wordBreak: 'break-all',
    // ... existing styles
}}
```

## Verification

1. Send a 500-character string with no spaces
2. Message should wrap within container
3. No horizontal scroll or overflow
