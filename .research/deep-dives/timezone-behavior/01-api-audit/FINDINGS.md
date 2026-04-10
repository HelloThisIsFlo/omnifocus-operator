# Timezone API Audit — Findings

> `shouldUseFloatingTimeZone` is NOT cosmetic — it changes how OmniFocus interprets stored dates across timezone changes. Floating = wall clock preserved, Fixed = UTC moment preserved. 100% of real tasks are floating=true.

**Date:** 2026-04-10
**Scripts:** `01-tz-api-audit.js`, `01b-floating-probe.js`, `01c-cross-tz-inspect.js`

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

## Raw Output — Script 01b (Floating vs Fixed Baseline, BST)

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

### A: 100% floating — no exceptions
Every task (3341) and project (379) has `shouldUseFloatingTimeZone=true`. Zero `false` in the entire database.

### B: No hidden timezone properties
`shouldUseFloatingTimeZone` is the **only** timezone-related property on Task. No `timeZone`, `calendar`, or other TZ properties exist.

### C: OmniJS Dates are standard JS Dates in the system timezone
- March 25 date (GMT period): `getTimezoneOffset()=0`, "Greenwich Mean Time"
- July 15 date (BST period): `getTimezoneOffset()=-60`, "British Summer Time"
- OmniJS Dates are fully DST-aware in the system timezone
- `toISOString()` always outputs UTC — this is what the bridge's `d()` function uses

### D: TimeZone class quirks
- **IANA names don't work**: `new TimeZone("Europe/London")` returns null. Only abbreviations work.
- **Abbreviations reflect current DST**: `new TimeZone("EST")` → EDT in April
- **DateComponents.timeZone shows current system TZ**: Decomposing a March 25 date (GMT) shows GMT+1 because we ran it during BST

### E: No observable "database default" difference
All tasks floating=true regardless of whether they have dates.

### F: Same-timezone probe (01b)
From BST (the creation timezone), floating and fixed tasks are **identical** through the Date API. Toggling the flag changes nothing observable — same epoch ms, same ISO string, same offset.

UI difference only: "fixed" shows a GMT+1 label on notifications, "floating" hides it.

### G: Cross-timezone experiment (01b + 01c) — THE KEY FINDING

Two tasks with identical `dueDate = new Date("2026-07-15T10:00:00Z")`, created in BST:

| | BST (home, UTC+1) | EDT (New York, UTC-4) |
|---|---|---|
| **Floating** | 11:00 BST, getTime=1784109600000 | **11:00 EDT**, getTime=**1784127600000** (+5h) |
| **Fixed** | 11:00 BST, getTime=1784109600000 | **06:00 EDT**, getTime=**1784109600000** (unchanged) |

- **Floating = wall clock time**: "11:00" travels with the user. UTC moment recalculated for the new timezone.
- **Fixed = UTC moment**: 10:00 UTC stays 10:00 UTC. Wall clock shifts to whatever that means locally.
- **Delta = 300 min = 5h** — exactly BST(+1) to EDT(-4)
- **Notifications shift too**: floating task's fire dates shifted by 5h, fixed task's unchanged
- **`effectiveDueDate` follows the same pattern** as `dueDate`

### Codebase impact

- **Bridge `d()` calls `.toISOString()`** — for floating tasks, bridge output is timezone-dependent. A snapshot taken in New York would show different UTC strings than one taken in London for the same floating task.
- **`_parse_local_datetime()` in hybrid.py** interprets naive SQLite text as local time → correct for floating tasks (100% of real data). Fixed tasks may need different handling (script 02 will check SQLite storage).
- **In practice: 100% floating=true, so current code is correct.** But we now understand the boundary condition.

## Key Findings

- `shouldUseFloatingTimeZone` is NOT cosmetic — it fundamentally changes date interpretation across timezones
- **Floating** = wall clock preserved, UTC moment shifts with timezone changes
- **Fixed** = UTC moment preserved, wall clock shifts with timezone changes
- From the same timezone, both look identical — the difference only manifests when the system timezone changes
- 100% of 3341 tasks and 379 projects are floating=true
- OmniJS Dates are DST-aware JS Dates: offset=-60 in BST, offset=0 in GMT
- IANA timezone names can't be used with `new TimeZone()` — only abbreviations

## Surprises / Unexpected Results

- The floating flag having a real, measurable effect on `getTime()` and `toISOString()` — not just a display hint
- `new TimeZone("Europe/London")` returning null
- DateComponents reporting GMT+1 for a March 25 date (current system state, not the date's)
- Notification fire dates also shifting for floating tasks (even though `usesFloatingTimeZone=false` on the notification objects themselves)

## Questions Answered

| Question | Answer | Evidence |
|----------|--------|----------|
| Q1 | Only `shouldUseFloatingTimeZone` (bool, r/w). No other TZ properties on Task. | Section B: all probes returned `undefined` |
| Q2 | Setting floating=false works. From same TZ: no API difference. From different TZ: fixed preserves UTC moment, floating preserves wall clock. | 01b: 0ms delta same-TZ. 01c: 300min delta cross-TZ |
| Q3 (partial) | No hidden TZ properties on the API side. SQLite column scan pending (script 02). | Section B |
| Q7 | Toggling floating on an existing task is instant and persists. The reinterpretation happens when OmniFocus next evaluates the date in a different timezone context. | 01b: toggle confirmed. 01c: reinterpretation observed |
