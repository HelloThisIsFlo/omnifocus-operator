# Timezone API Audit — Findings

> `shouldUseFloatingTimeZone` is NOT cosmetic — it changes how OmniFocus interprets stored dates across timezone changes. 🌊 Floating = wall clock preserved, 📌 Fixed = UTC moment preserved. 100% of real tasks are 🌊.

**Date:** 2026-04-10
**Scripts:** `01-tz-api-audit.js`, `01b-floating-probe.js`, `01c-cross-tz-inspect.js`, `01d-sqlite-floating-inspect.py`

## Raw Output — Script 01 (API Audit)

```
=== 01: Timezone API Audit ===
Total tasks: 3341
Total projects: 379

--- A: shouldUseFloatingTimeZone Distribution ---

  Tasks:
    true:  3341
    false: 0
    null:  0
    other: 0
  Projects (via .task):
    true:  379
    false: 0
    null:  0
    other: 0

--- B: Timezone Property Probe ---

  Sample task: "Test task for edit experiment" (id: bXgOaDOm02N)

  Properties matching time/zone/tz/float/calendar:
    shouldUseFloatingTimeZone: [boolean] true

  Specific property probes:
    task.timeZone: undefined
    task.calendar: undefined
    task.timezone: undefined
    task.floatingTimeZone: undefined
    task.shouldUseFloatingTimeZone: [boolean] true
    task.taskTimeZone: undefined

--- C: Date Object Inspection ---

  Task: "Test task for edit experiment"

  dueDate:
    typeof:           object
    instanceof Date:  true
    toISOString():    2026-03-25T17:00:00.000Z
    getTime():        1774458000000 (epoch ms)
    getTimezoneOffset(): 0 (minutes from UTC)
    toString():       Wed Mar 25 2026 17:00:00 GMT+0000 (Greenwich Mean Time)
    toLocaleString(): 3/25/2026, 5:00:00 PM

  effectiveDueDate:
    typeof:           object
    instanceof Date:  true
    toISOString():    2026-03-25T17:00:00.000Z
    getTime():        1774458000000 (epoch ms)
    getTimezoneOffset(): 0 (minutes from UTC)

  dueDate vs effectiveDueDate:
    Same epoch ms: true
    Delta ms:      0

--- D: TimeZone + DateComponents Probe ---

  TimeZone.abbreviations: 51 entries
    Sample: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9

  TimeZone construction:
    new TimeZone("EST"): abbreviation=EDT, secondsFromGMT=-14400, daylightSavingTime=true
    new TimeZone("UTC"): abbreviation=GMT, secondsFromGMT=0, daylightSavingTime=false
    new TimeZone("PST"): abbreviation=PDT, secondsFromGMT=-25200, daylightSavingTime=true
    new TimeZone("BST"): abbreviation=GMT+1, secondsFromGMT=3600, daylightSavingTime=true
    new TimeZone("GMT"): abbreviation=GMT, secondsFromGMT=0, daylightSavingTime=false
    new TimeZone("Europe/London"): [ERROR] null is not an object (evaluating 'tz.abbreviation')

  DateComponents from sample dueDate:
    year:     2026
    month:    3
    day:      25
    hour:     17
    minute:   0
    second:   0
    timeZone: [object TimeZone: Europe/London]
    timeZone.abbreviation: GMT+1
    timeZone.secondsFromGMT: 3600

--- E: Floating TZ — Tasks With vs Without Dates ---

  Tasks WITH dates (due or defer):
    total:  630
    floating=true:  630
    floating=false: 0
  Tasks WITHOUT dates:
    total:  2711
    floating=true:  2711
    floating=false: 0
```

## Raw Output — Script 01b (🌊 vs 📌 Baseline, BST)

Created two tasks with identical `dueDate = new Date("2026-07-15T10:00:00Z")` (July = BST).

```
  --- FLOATING (shouldUseFloatingTimeZone = true) ---
  id:       mgFcYratJYj
  dueDate:
    toISOString():       2026-07-15T10:00:00.000Z
    getTime():           1784109600000 (epoch ms)
    getTimezoneOffset(): -60 (min from UTC)
    toString():          Wed Jul 15 2026 11:00:00 GMT+0100 (British Summer Time)

  --- FIXED (shouldUseFloatingTimeZone = false) ---
  id:       nHoYo0OQOmL
  dueDate:
    toISOString():       2026-07-15T10:00:00.000Z
    getTime():           1784109600000 (epoch ms)
    getTimezoneOffset(): -60 (min from UTC)
    toString():          Wed Jul 15 2026 11:00:00 GMT+0100 (British Summer Time)

  Both identical in home timezone. Delta: 0ms.
```

## Raw Output — Script 01c (Cross-TZ Inspection, EDT/New York)

System timezone switched to America/New_York (EDT, UTC-4), OmniFocus restarted.

```
Current environment:
  now.toString():          Fri Apr 10 2026 12:51:50 GMT-0400 (Eastern Daylight Time)
  now.getTimezoneOffset(): 240 min from UTC

  --- FLOATING TASK ---
  dueDate:
    toISOString():       2026-07-15T15:00:00.000Z
    getTime():           1784127600000 (epoch ms)
    getTimezoneOffset(): 240 (min from UTC)
    toString():          Wed Jul 15 2026 11:00:00 GMT-0400 (Eastern Daylight Time)
  effectiveDueDate:
    toISOString():       2026-07-15T15:00:00.000Z
    getTime():           1784127600000 (epoch ms)
  Notifications:
    [0] DueRelative, initialFireDate=2026-07-15T14:59:00.000Z, offset=-60min
    [1] DueRelative, initialFireDate=2026-07-14T15:00:00.000Z, offset=-86400min

  --- FIXED TASK ---
  dueDate:
    toISOString():       2026-07-15T10:00:00.000Z
    getTime():           1784109600000 (epoch ms)
    getTimezoneOffset(): 240 (min from UTC)
    toString():          Wed Jul 15 2026 06:00:00 GMT-0400 (Eastern Daylight Time)
  effectiveDueDate:
    toISOString():       2026-07-15T10:00:00.000Z
    getTime():           1784109600000 (epoch ms)
  Notifications:
    [0] DueRelative, initialFireDate=2026-07-15T09:59:00.000Z, offset=-60min
    [1] DueRelative, initialFireDate=2026-07-14T10:00:00.000Z, offset=-86400min

  Floating vs Fixed delta: 18000000 ms (300 min = 5h)
  Floating vs BST baseline: CHANGED by +300 min (wall clock preserved, UTC shifted)
  Fixed vs BST baseline: UNCHANGED (UTC moment preserved, wall clock shifted)
```

## Interpretation

### A: 100% 🌊 floating — no exceptions

Every task (3341) and project (379) has `shouldUseFloatingTimeZone=true`. Zero `false` in the entire database.

### B: No hidden timezone properties

`shouldUseFloatingTimeZone` is the **only** timezone-related property on Task:
- `task.timeZone` → `undefined`
- `task.calendar` → `undefined`
- `task.timezone` → `undefined`
- `task.floatingTimeZone` → `undefined`
- `task.taskTimeZone` → `undefined`

### C: OmniJS Dates are standard JS Dates in the system timezone

- March 25 (GMT period) → `getTimezoneOffset()=0`, "Greenwich Mean Time"
- July 15 (BST period) → `getTimezoneOffset()=-60`, "British Summer Time"
- Fully DST-aware
- `toISOString()` always outputs UTC — this is what the bridge's `d()` uses

### D: TimeZone class quirks

> [!warning] IANA names don't work
>
> - `new TimeZone("Europe/London")` → **null** (throws on property access)
> - Only abbreviations work: `"EST"`, `"UTC"`, `"PST"`, `"BST"`, `"GMT"`
> - Abbreviations reflect **current DST**: `new TimeZone("EST")` → EDT in April
> - `DateComponents.timeZone` shows **current system TZ** (not the date's own period)

### E: No observable "database default" difference

All tasks `floating=true` regardless of whether they have dates — 630 with dates, 2711 without, all floating.

### F: Same-timezone probe (01b)

> [!important] Same-TZ invisibility
>
> - 🌊 and 📌 are **identical** through the Date API from the creation timezone
> - Same epoch ms, same ISO string, same offset
> - Only UI difference: 📌 shows a GMT+1 label on notifications, 🌊 hides it

### G: Cross-timezone experiment (01b + 01c) — 🔑 THE KEY FINDING

Two tasks with identical `dueDate = new Date("2026-07-15T10:00:00Z")`, created in BST:

| | BST (home, UTC+1) | EDT (New York, UTC-4) |
|---|---|---|
| 🌊 **Floating** | 11:00 BST, `getTime=1784109600000` | **11:00 EDT**, `getTime=1784127600000` (+5h) |
| 📌 **Fixed** | 11:00 BST, `getTime=1784109600000` | **06:00 EDT**, `getTime=1784109600000` (unchanged) |

- 🌊 **Floating = wall clock** — "11:00" travels with you, UTC moment recalculated
- 📌 **Fixed = UTC moment** — 10:00 UTC stays 10:00 UTC, wall clock shifts
- **Delta = 300 min = 5h** — exactly BST(+1) to EDT(-4)
- Notifications shift too — 🌊 fire dates shifted by 5h, 📌 unchanged
- `effectiveDueDate` follows the same pattern

### Codebase impact

- **Bridge `d()` calls `.toISOString()`** — for 🌊 tasks, output is timezone-dependent
  - Snapshot in New York ≠ snapshot in London for the same task
- **`_parse_local_datetime()` in `hybrid.py`** — interprets naive SQLite text as local time
  - ✅ Correct for 🌊 tasks (100% of real data)
  - 📌 tasks would need different handling — but none exist in practice

### H: SQLite storage of 🌊 vs 📌 (01d)

> [!important] The encoding rule
>
> - 🌊 Floating → **no Z suffix** — naive local time (e.g., `2026-07-15T11:00:00.000`)
> - 📌 Fixed → **Z suffix** — UTC-anchored (e.g., `2026-07-15T10:00:00.000Z`)
> - Both have identical `effectiveDateDue` — same UTC moment, different text encoding
> - **Detection**: `dateDue.endswith('Z')` → 📌 fixed. No separate column needed.

Broader scan: 465 `dateDue` values → only 1 Z-suffix (our test task). Zero Z in `dateToStart` (0/510) and `datePlanned` (0/30). Confirms 100% 🌊 in real data.

## 🤯 Surprises

- The floating flag having a **real, measurable effect** on `getTime()` and `toISOString()` — not just a display hint
- `new TimeZone("Europe/London")` returning null
- `DateComponents.timeZone` reporting GMT+1 for a March 25 date — current system state, not the date's own period
- Notification fire dates shifting for 🌊 tasks — even though `usesFloatingTimeZone=false` on the notification objects themselves

## Questions Answered

| Question | Answer | Evidence |
|----------|--------|----------|
| Q1 | Only `shouldUseFloatingTimeZone` (bool, r/w). No other TZ properties on Task. | Section B: all probes → `undefined` |
| Q2 | Setting `floating=false` works. Same TZ: no API difference. Different TZ: 📌 preserves UTC, 🌊 preserves wall clock. | 01b: 0ms delta same-TZ. 01c: 300min delta cross-TZ |
| Q3 | No hidden TZ columns in SQLite. Floating encoded as Z-suffix on date text strings. | 01d: side-by-side + broader scan |
| Q7 | Toggling is instant and persists. Reinterpretation happens on next TZ change. | 01b: toggle confirmed. 01c: reinterpretation observed |
