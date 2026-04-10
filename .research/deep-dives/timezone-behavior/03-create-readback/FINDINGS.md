# Create & Readback — Findings

> OmniFocus normalizes ALL date inputs to 🌊 naive local time. UTC, offsets, naive, date-only — everything becomes local wall clock time with no Z suffix. UI displays exactly what's in `dateDue`.

**Date:** 2026-04-10
**Script:** `03-create-readback/03-create-and-readback.py`
**System timezone:** Europe/London, BST (UTC+1)

## Raw Output

```
Timezone Create & Readback Experiment
========================================

System time:  2026-04-10T18:16:52.102131+01:00
UTC offset:   +0100 (BST)

======================================================================
7. Side-by-Side Comparison
======================================================================

  Label  Input                          SQLite dateDue               SQLite effDue (UTC)      Bridge dueDate
  ------ ------------------------------ ---------------------------- ------------------------ ------------------------------
  A      2026-07-15T09:00:00Z           2026-07-15T10:00:00.000      2026-07-15T09:00:00 UTC  2026-07-15T09:00:00.000Z
  B      2026-12-15T09:00:00Z           2026-12-15T09:00:00.000      2026-12-15T09:00:00 UTC  2026-12-15T09:00:00.000Z
  C      2026-07-15T09:00:00            2026-07-15T09:00:00.000      2026-07-15T08:00:00 UTC  2026-07-15T08:00:00.000Z
  D      2026-07-15                     2026-07-15T01:00:00.000      2026-07-15T00:00:00 UTC  2026-07-15T00:00:00.000Z
  E      2026-07-15T09:00:00+05:30      2026-07-15T04:30:00.000      2026-07-15T03:30:00 UTC  2026-07-15T03:30:00.000Z
  F      2026-07-15T09:00:00Z→+05:30    2026-07-15T04:30:00.000      2026-07-15T03:30:00 UTC  2026-07-15T03:30:00.000Z
```

## UI Spot Check

| Task | UI shows | SQLite `dateDue` | Match? |
|------|----------|-----------------|--------|
| A | 10:00 AM Jul 15 | `10:00:00.000` | ✅ |
| B | 9:00 AM Dec 15 | `09:00:00.000` | ✅ |
| C | 9:00 AM Jul 15 | `09:00:00.000` | ✅ |
| D | 1:00 AM Jul 15 | `01:00:00.000` | ✅ |
| E | 4:30 AM Jul 15 | `04:30:00.000` | ✅ |
| F | 4:30 AM Jul 15 | `04:30:00.000` | ✅ |

UI displays exactly what's in `dateDue` — naive local time.

## Interpretation

### The normalization pipeline

Every date input: `bridge JS` → `new Date(input)` → OmniFocus stores as 🌊 naive local time.

1. **JS `new Date()` parses the string** — UTC, offsets, naive, date-only per ECMA-262
2. **OmniFocus receives a Date object** — UTC moment internally
3. **OmniFocus stores as naive local** — converts UTC → system timezone, strips TZ info, writes text to `dateDue`
4. **All tasks are 🌊** — no Z suffix on any stored date

### Per-format behavior

- **Explicit UTC (`Z`)** — correctly converted to local
  - Task A: `09:00Z` → `10:00` local (BST +1h)
  - Task B: `09:00Z` → `09:00` local (December = GMT, no shift)
- **Naive (no Z)** — JS treats as **local time**
  - Task C: `09:00` → stored as `09:00`, effective = `08:00 UTC`
  - ⚠️ Same "09:00" in input but **different UTC** than Task A's `09:00Z`
- **Explicit offset** — correctly normalized
  - Task E: `09:00+05:30` → `03:30 UTC` → `04:30 BST`
- **Edit re-normalizes** — Task F created as `09:00Z` (= 10:00 local), edited to `09:00+05:30` (= 04:30 local)
  - Edit completely replaces the stored value

> [!warning] Date-only input quirk
>
> - `new Date("2026-07-15")` parses as **UTC midnight** (`00:00Z`), not local midnight
> - OmniFocus converts to local → `01:00 BST`
> - Users sending date-only strings get **1am**, not midnight
>
> This is a JS `new Date()` behavior, not an OmniFocus decision => **use `DefaultDueTime`/`DefaultStartTime` from settings instead**

### Bridge readback vs SQLite

- **Bridge** (`d()` → `.toISOString()`) — always returns UTC with Z suffix
- **SQLite** (`dateDue` text) — always stores naive local time without Z
- Both are correct representations of the same moment — just different timezones
- `effectiveDateDue` (CF epoch float) = the UTC moment, matches bridge output

## 🤯 Surprises

- ⚠️ **Date-only quirk is significant** — `"2026-07-15"` → 1:00 AM, not midnight
- **No fixed dates ever** — even explicit UTC (`Z`) input stores as 🌊 floating. Bridge `new Date()` + assignment always produces 🌊

## Questions Answered

| Question | Answer | Evidence |
|----------|--------|----------|
| Q6 | All formats normalized to 🌊 naive local time. UTC→local shift. Naive=local. Date-only=UTC midnight→local. Offset→UTC→local. | Side-by-side table |
| Q2 (partial) | Creating via bridge always produces 🌊 tasks. Bridge doesn't set `floating=false`. | All 6 tasks stored without Z suffix |

> [!tip] Settings API
>
> The date-only quirk led to discovering the OmniFocus settings API — full details in [script 05 findings](../05-settings-api/FINDINGS.md)
