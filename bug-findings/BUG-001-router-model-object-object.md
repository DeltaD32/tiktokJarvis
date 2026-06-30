# BUG-1: Settings ROUTER model textboxes show `[object Object]`

**Severity**: Medium
**Found**: 2026-06-29, Playwright audit
**File**: `frontend/src/components/panels/SettingsPanel.jsx`
**Lines**: 671-682

## Reproduction

1. Open app at http://localhost:5173/
2. Click SETTINGS in top navigation
3. Click ROUTER section tab
4. Observe FAST MODEL and PREMIUM MODEL text inputs

**Expected**: Model name strings (e.g. "glm-5.2")
**Actual**: `[object Object]`

## Root Cause

The Settings API (`GET /api/settings`) returns `settings.model` as an object:

```json
{
  "model": {
    "name": "Dela",
    "model": "glm-5.2",
    "base_url": "https://opencode.ai/zen/go/v1",
    "thinking_level": "off"
  }
}
```

The LiveField component passes `value` to a text `<input value={value || ''}>` which calls `.toString()` on the object.

**Offending code** (lines 674, 680):

```jsx
<LiveField
  label="FAST MODEL"
  settingKey="model_fast"
  value={settings.live?.model_fast || settings.model}  // ← OBJECT, not string
/>

<LiveField  
  label="PREMIUM MODEL"
  settingKey="model_premium"
  value={settings.live?.model_premium || settings.model}  // ← OBJECT, not string
/>
```

The `||` fallback is `settings.model` (object), not `settings.model.model` (string "glm-5.2").

## Fix

```jsx
// Line 674 (FAST MODEL):
value={settings.live?.model_fast || settings.model?.model}

// Line 680 (PREMIUM MODEL):
value={settings.live?.model_premium || settings.model?.model}
```

Or alternatively, destructure the model name at the top of the router section:

```jsx
const defaultModel = settings.model?.model || ''
```

Then use `defaultModel` in both LiveField value props.

## Verification

After fix:
1. Navigate to Settings → ROUTER
2. FAST MODEL textbox shows "glm-5.2" 
3. PREMIUM MODEL textbox shows "glm-5.2"
4. Both fields are editable and values save correctly
