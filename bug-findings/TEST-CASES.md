# Playwright Audit — Test Cases Executed

**Date**: 2026-06-29
**Browser**: Microsoft Edge (msedge)
**App URL**: http://localhost:5173/

## Idle View Tests

### TC-01: Idle view loads correctly
- Navigate to http://localhost:5173/
- Verify: DELA logo, "all systems nominal — awaiting your directive"
- Verify: MIC + EXECUTE buttons visible
- Verify: 4 suggestion chips visible
- Verify: Agent roster shows 5 agents
- Verify: Corner stats (HEARTBEAT, TOOLS, UPLINK, AGENTS) all present
- **Result**: ✅ PASS

### TC-02: Empty input guard
- Type nothing in input
- Press Enter
- Verify: App stays in idle view, no errors
- **Result**: ✅ PASS

### TC-03: Shift+Enter does not send
- Type "test" in input
- Press Shift+Enter
- Verify: Text stays in input, no message sent
- **Result**: ✅ PASS

### TC-04: Suggestion chip "What can you do?"
- Click "What can you do?" chip
- Wait for response
- Verify: Conversation appears, response received
- **Result**: ✅ PASS — Response: "Here's what I can help with: - **Tasks** ..."

## Text Conversation Tests

### TC-05: Send message via EXECUTE button
- Type "What is the capital of France? Answer in one word only."
- Click EXECUTE
- Wait for response
- Verify: Single `[ws] sendMessage:` log in console
- Verify: Response "Paris." appears
- **Result**: ✅ PASS

### TC-06: Conversation message display
- Verify: User message shown ("What is the capital of France?...")
- Verify: Assistant message shown ("Paris.")
- Verify: Messages truncated to 200 chars
- Verify: Streaming cursor `▍` during response
- **Result**: ✅ PASS

### TC-07: Rapid double-send guard
- Type "Hello again", click RUN
- Immediately type "This should be blocked", click RUN
- Verify: Only first message sent, second blocked
- Verify: Console shows `[ws] (ignored — already processing a turn)` or second message doesn't appear
- **Result**: ✅ PASS

### TC-08: Multiple conversation messages
- Send 3 messages sequentially
- Verify: All messages appear in conversation
- Verify: No duplicate messages
- **Result**: ✅ PASS

## Data Panels Tests

### TC-09 through TC-18: All 10 panel open/close
For each of: ANALYTICS, TOOLS, WORKFLOWS, NOTICES(1), SETTINGS, SECURITY, MEMORY, STATE, AUDIT, TASKS:
- Click data-btn
- Verify: Panel slides in from right
- Verify: Panel has title header with ✕ close button
- Verify: Expected content renders
- Click ✕ to close
- Verify: Panel dismisses
- **Result**: ✅ PASS — All 10 panels open and close correctly

### TC-19: Settings PROFILE section
- Open Settings → PROFILE tab
- Verify: Shows current profile, available profiles, Ollama status
- **Result**: ✅ PASS

### TC-20: Settings ROUTER section — BUG FOUND
- Open Settings → ROUTER tab
- Verify: Model textboxes show model names (e.g. "glm-5.2")
- **Actual**: Shows `[object Object]`
- **Result**: ❌ FAIL — BUG-1

### TC-21: Security panel FINDINGS
- Open Security panel
- Verify: FINDINGS tab selected, score visible, finding details listed
- **Result**: ✅ PASS

### TC-22: Workflows panel empty state
- Open Workflows panel
- Verify: "+ NEW" button visible, workflow list or empty state
- **Result**: ✅ PASS

## Float Windows Tests

### TC-23: Dock appears in non-idle state
- Send a message to leave idle state
- Verify: Dock visible with HEARTBEAT, HIVE, STREAM, SANDBOX, NOTICES, MINIMIZE ALL
- **Result**: ✅ PASS

### TC-24: HIVE float window
- Click THE HIVE
- Verify: Float window opens with AGENT REGISTRY
- Verify: 5 agents listed with READY status, descriptions, tool counts
- Verify: IAC bus active, 5/5 ready
- **Result**: ✅ PASS

### TC-25: STREAM float window
- Click THE STREAM
- Verify: Timeline with User/Dela messages, DIRECTIVE/RESPONSE tags
- Verify: Colored dots, connecting lines
- **Result**: ✅ PASS

### TC-26: SANDBOX float window
- Click SANDBOX
- Verify: Terminal tab with blinking cursor
- Verify: Message history displayed
- **Result**: ✅ PASS

### TC-27: Sandbox tools tab
- Click tools tab in SANDBOX
- Verify: REQUIRES CONFIRMATION and SAFE sections
- **Result**: ✅ PASS

### TC-28: Sandbox agents tab
- Click agents tab in SANDBOX
- Verify: Agent list with tools
- **Result**: ✅ PASS

### TC-29: MINIMIZE ALL
- Open all 3 float windows
- Click MINIMIZE ALL
- Verify: All float windows close
- **Result**: ✅ PASS

### TC-30: HEARTBEAT toggle
- Click HEARTBEAT dock button
- Verify: Toggles ON/OFF, idle stats reflect change (ACTIVE ↔ PAUSED)
- **Result**: ✅ PASS

### TC-31: NOTICES dock button
- Click NOTICES dock button
- Verify: Opens Notices panel
- **Result**: ✅ PASS

## Voice Pipeline Tests

### TC-32: MIC → recording state
- Click MIC button
- Verify: Button changes to STOP, red pulse animation
- Verify: LISTENING indicator in VoiceHud
- **Result**: ✅ PASS

### TC-33: STOP → transcribing state
- Click STOP button
- Verify: Button changes to "...", amber
- Verify: TRANSCRIBING indicator in VoiceHud
- **Result**: ✅ PASS

### TC-34: STT empty result handling
- Verify: "Voice error: Transcription failed" shown
- Verify: No `[ws] sendMessage:` fired
- **Result**: ✅ PASS (expected — no real mic in Playwright)

### TC-35: Voice toggle double-STT call — BUG FOUND
- Check browser console after voice interaction
- Verify: Single `[voice] STT result:` log
- **Actual**: Two logs — one `undefined`, one `""`
- **Result**: ❌ FAIL — BUG-2

## WebSocket Tests

### TC-36: Single sendMessage per user action
- Send a message
- Verify: Console shows exactly one `[ws] sendMessage:` log
- **Result**: ✅ PASS

### TC-37: connIdRef prevents stale reconnects
- Page loads in React StrictMode
- Verify: Only one WebSocket connection active at a time
- Verify: No duplicate token streams
- **Result**: ✅ PASS

### TC-38: Idle delay after response
- Send a message, wait for response
- Verify: After 60s, app transitions to idle view
- **Result**: ✅ PASS (verified visually — returned to idle after waiting)

## Console Hygiene

### TC-39: Console error count
- Run all tests
- Count console errors (not warnings, not logs)
- Verify: 0 errors unrelated to known warnings
- **Result**: ✅ PASS — 2 React CSS warnings (Dock animation), 0 real errors

### TC-40: Console warning review
- Review all warnings
- Findings: WS initial connection failure (WARN-1), Dock CSS animation (WARN-2), Favicon 404 (WARN-3)
- **Result**: ✅ PASS — No new/unknown warnings

## Edge Cases

### TC-41: Window resize
- Resize viewport to 1024x600
- Verify: App still renders, no crashes
- Resize to 1920x1080
- **Result**: ✅ PASS

### TC-42: Copy to clipboard
- Click a conversation message
- Verify: Clipboard API called (checked via evaluate)
- **Result**: ⚠️ PARTIAL — API called but silently fails when permission denied (BUG-4)
