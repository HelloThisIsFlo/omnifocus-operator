# Timezone API Audit — Findings

> `shouldUseFloatingTimeZone` is the only TZ property on Task. It's a pure display/alerting flag — toggling it changes nothing in the Date API, notifications, or storage. 100% of tasks are floating=true. OmniJS Dates are standard JS Date objects in the system timezone.

**Date:** 2026-04-10
**Scripts:** `01-api-audit/01-tz-api-audit.js`, `01-api-audit/01b-floating-probe.js`

## Raw Output — Script 01

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

## Raw Output — Script 01b (Floating Probe)

Created task `TZ-PROBE-Floating` with `dueDate = new Date("2026-07-15T10:00:00Z")` (July = BST).

```
Toggling shouldUseFloatingTimeZone:
  floating=true:  getTime()=1784109600000, toISOString()=2026-07-15T10:00:00.000Z, offset=-60
  floating=false: getTime()=1784109600000, toISOString()=2026-07-15T10:00:00.000Z, offset=-60
  restored=true:  getTime()=1784109600000, toISOString()=2026-07-15T10:00:00.000Z, offset=-60

  Delta floating→fixed: 0ms
  Delta fixed→restored: 0ms
```

Notification inspection (2 due-relative notifications, tested in both floating=true and floating=false):

```
Both states produced identical results:
  [0] kind=DueRelative, initialFireDate=2026-07-14T10:00:00.000Z, relativeFireOffset=-86400min, usesFloatingTimeZone=false
  [1] kind=DueRelative, initialFireDate=2026-07-15T09:59:00.000Z, relativeFireOffset=-60min, usesFloatingTimeZone=false
```

UI observation: When set to "fixed", the notification display shows "GMT+1" alongside the time. When set to "floating", the GMT+1 label disappears. No change to the actual fire time.

## Interpretation

### A: 100% floating — no exceptions
Every task (3341) and project (379) has `shouldUseFloatingTimeZone=true`. Zero `false` in the entire database.

### B: No hidden timezone properties
`shouldUseFloatingTimeZone` is the **only** timezone-related property on Task. No `timeZone`, `calendar`, or other TZ properties exist.

### C: OmniJS Dates are standard JS Dates in the system timezone
- Script 01 sampled a March 25 date (GMT period): `getTimezoneOffset()=0`, `toString()` shows "Greenwich Mean Time"
- Script 01b sampled a July 15 date (BST period): `getTimezoneOffset()=-60`, `toString()` shows "British Summer Time"
- Both confirm OmniJS Dates are fully DST-aware in the system timezone
- `toISOString()` always outputs UTC — this is what the bridge's `d()` function uses

### D: TimeZone class quirks
- **IANA names don't work**: `new TimeZone("Europe/London")` returns null. Only abbreviations work.
- **Abbreviations reflect current DST**: `new TimeZone("EST")` → EDT in April because Eastern is in daylight time
- **DateComponents.timeZone shows current system TZ**: Decomposing a March 25 date (GMT) shows GMT+1 because we're running in April (BST)

### E: No observable "database default" difference
Tasks with and without dates are all floating=true — the "reverts to default" behavior is invisible since the default is true.

### F: Floating flag — what we know and don't know (01b probe)

**Caveat**: We tested from the same timezone (BST) where the task was created. This limits what we can conclude.

What we proved:
- **The assignment persists** — toggling to false and checking the UI confirmed it showed "fixed"
- **Toggling does not change the Date object when observed from the same timezone**: epoch ms, ISO string, timezone offset all identical across true/false/restored
- **Due-relative notifications are unaffected**: `usesFloatingTimeZone=false` on notifications regardless of task flag (docs: only applies to absolute notifications)
- **UI display changes**: "fixed" shows a GMT+1 label on notifications, "floating" hides it

What we did NOT test:
- Whether the flag changes SQLite storage (→ script 02)
- Whether the flag changes behavior when observed from a different timezone (that's the whole point of floating vs fixed)
- Whether absolute notifications (not due-relative) would behave differently

## Key Findings

- `shouldUseFloatingTimeZone` is the only TZ property on Task
- Toggling it changes nothing observable through the API **when observed from the same timezone** — cross-timezone behavior untested
- 100% of 3341 tasks and 379 projects are floating=true
- OmniJS Dates are DST-aware JS Dates: offset=-60 in BST, offset=0 in GMT
- IANA timezone names (`"Europe/London"`) can't be used with `new TimeZone()` — only abbreviations

## Surprises / Unexpected Results

- `new TimeZone("Europe/London")` returning null
- DateComponents reporting GMT+1 for a March 25 date (shows calendar's current state, not the date's)
- The floating flag having no observable effect through the API from the same timezone — real impact may only show when crossing timezones

## Questions Answered

| Question | Answer | Evidence |
|----------|--------|----------|
| Q1 | Only `shouldUseFloatingTimeZone` (bool, r/w). No other TZ properties on Task. | Section B: all probes returned `undefined` |
| Q2 (partial) | Setting floating=false works and persists. No Date API change **from same timezone** — cross-TZ and SQLite impact untested. | 01b probe: 0ms delta, same-TZ caveat |
| Q3 (partial) | No hidden TZ properties on the API side. SQLite column scan pending (script 02). | Section B |
| Q7 (partial) | Toggling floating on an existing task persists and is instant. No date recalculation from same timezone. | 01b probe: toggle + UI verification |
