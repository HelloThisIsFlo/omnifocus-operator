# Cross-Timezone Experiment — Quick Guide

> Creates two identical tasks (one floating, one fixed), then compares how OmniFocus reports them from a different timezone.

## Step 1: Clean up any previous probe tasks

1. Open OmniFocus → Automation → Console
2. Open `cleanup.js`, copy, paste into console, run
3. This deletes any leftover `TZ-DD-*` or `TZ-PROBE-*` tasks

## Step 2: Create the two probe tasks (in your normal BST timezone)

1. Open `01b-floating-probe.js` in a text editor, copy the entire contents
2. Paste into the Automation Console and run
3. Save the output — this is your **BST baseline**
4. Confirm **two tasks** appear in your inbox:
   - `TZ-PROBE-Floating` (shouldUseFloatingTimeZone = true)
   - `TZ-PROBE-Fixed` (shouldUseFloatingTimeZone = false)
5. Both have the same dueDate: `new Date("2026-07-15T10:00:00Z")`

**BST baseline — both tasks should be identical:**

```
getTime():           1784109600000
toISOString():       2026-07-15T10:00:00.000Z
getTimezoneOffset(): -60 (BST, UTC+1)
toString():          Wed Jul 15 2026 11:00:00 GMT+0100 (British Summer Time)
```

## Step 3: Switch system timezone

1. Open **System Settings → General → Date & Time**
2. Uncheck **"Set time zone automatically"**
3. Pick a city far from London — e.g. **New York** (EDT, UTC-4) or **Tokyo** (JST, UTC+9)
4. Confirm the menu bar clock changes to the new timezone

## Step 4: Restart OmniFocus

1. **Quit** OmniFocus completely (Cmd+Q — not just close the window)
2. **Reopen** OmniFocus
3. Wait for it to fully load

## Step 5: Run the inspection script

1. Open OmniFocus → Automation → Console
2. Open `01c-cross-tz-inspect.js` in a text editor, copy the entire contents
3. Paste into the console and run
4. Save the output

## Step 6: Read the results

The script compares both tasks against each other AND against the BST baseline.

**What to look for — floating vs fixed task:**

| Result | Meaning |
|--------|---------|
| Both `getTime()` identical | The flag has no effect on the Date API |
| `getTime()` differs between them | The flag changes how OmniFocus interprets the stored date |

**What to look for — comparison with BST baseline:**

| Task | `getTime()` unchanged | `getTime()` changed |
|------|----------------------|---------------------|
| Floating | UTC moment preserved (unexpected) | Wall clock preserved, UTC shifted (= floating behavior) |
| Fixed | UTC moment preserved (= fixed behavior) | Wall clock preserved (unexpected for fixed) |

## Step 7: Check the OmniFocus UI

While still in the new timezone, look at both tasks in OmniFocus:

- `TZ-PROBE-Floating`: does it show **11:00** (wall clock preserved) or a shifted time?
- `TZ-PROBE-Fixed`: does it show the **same** as floating, or a **different time**?

If floating shows 11:00 and fixed shows a different local time — that's the flag in action.

## Step 8: Switch back to normal

1. Open **System Settings → General → Date & Time**
2. Re-check **"Set time zone automatically"** (or manually select London)
3. Confirm the menu bar clock shows BST again
4. **Quit and reopen OmniFocus**
5. Optionally run `01c` again to confirm values match the baseline

## Cleanup

Paste `cleanup.js` in the Automation Console — it catches both `TZ-DD-*` and `TZ-PROBE-*` tasks.
