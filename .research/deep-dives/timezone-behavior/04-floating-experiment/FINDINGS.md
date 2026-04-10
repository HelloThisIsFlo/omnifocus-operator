# Floating Timezone Experiment — Findings

> Toggling 🌊↔📌 is instant but invisible from the same TZ. Order matters: date must exist before `floating=false`. `new TimeZone("EST")` gives EDT in summer. SQLite re-encodes on toggle (naive local ↔ UTC+Z).

**Date:** 2026-04-10
**Script:** `04-floating-experiment/04-floating-tz-experiment.js`

## Raw Output

```
=== 04: Floating Timezone Experiment ===

Found TZ-DD-A: id=j5TckkeVYMg

--- Part 1: Toggle Floating on Task A ---

  BEFORE:
    shouldUseFloatingTimeZone: true
    dueDate.toISOString():     2026-07-15T09:00:00.000Z
    dueDate.getTime():         1784106000000 (epoch ms)
    dueDate.toString():        Wed Jul 15 2026 10:00:00 GMT+0100 (British Summer Time)

  AFTER (set to false):
    shouldUseFloatingTimeZone: false
    dueDate.toISOString():     2026-07-15T09:00:00.000Z
    dueDate.getTime():         1784106000000 (epoch ms)
    dueDate.toString():        Wed Jul 15 2026 10:00:00 GMT+0100 (British Summer Time)

  KEY QUESTION: Did getTime() change? Compare BEFORE and AFTER getTime() values above.

  RESTORED: shouldUseFloatingTimeZone = true
    dueDate.getTime(): 1784106000000

--- Part 2: TZ-DD-G — DateComponents with EST ---

  DateComponents created:
    year=2026, month=7, day=15, hour=9
    timeZone=[object TimeZone: America/New_York], abbreviation=EDT
    secondsFromGMT=-14400

  Date from DateComponents:
    toISOString(): 2026-07-15T13:00:00.000Z
    getTime():     1784120400000
    Expected:      09:00 EST = 14:00 UTC = 2026-07-15T14:00:00.000Z

  Task created:
    id:       opxuahmZtlT
    dueDate:  2026-07-15T13:00:00.000Z
    floating: false

--- Part 3: TZ-DD-H — Non-floating from start ---

  ERROR creating TZ-DD-H: Set due or defer date to edit the time zone

--- Part 4: TZ-DD-I — Set date then toggle floating ---

  After setting dueDate (floating still true):
    dueDate:  2026-07-15T09:00:00.000Z
    getTime(): 1784106000000
    floating: true

  After toggling floating to false:
    dueDate:  2026-07-15T09:00:00.000Z
    getTime(): 1784106000000
    floating: false

  Task:
    id: cwIl1rVBAmG

--- Part 5: H vs I Comparison ---

  Both got dueDate = new Date("2026-07-15T09:00:00Z")
  H: set floating=false BEFORE dueDate
  I: set dueDate BEFORE floating=false
  Compare their getTime() values above — are they identical?

--- Part 6: SQLite Verification Query ---

  Run this after the script completes:

  sqlite3 -readonly -header -column \
    ~/Library/Group\ Containers/34YW5XSRB7.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel/OmniFocusDatabase.db \
    "SELECT persistentIdentifier, name, dateDue, effectiveDateDue, shouldUseFloatingTimeZone FROM Task WHERE name LIKE 'TZ-DD-%'"

--- New Task IDs ---

  TZ-DD-A: UTC summer: id=j5TckkeVYMg, floating=true
  TZ-DD-B: UTC winter: id=cIlCdvQY0db, floating=true
  TZ-DD-C: Naive no-Z: id=mKgFOOIohDA, floating=true
  TZ-DD-D: Date-only: id=f8JwucOfA1X, floating=true
  TZ-DD-E: Offset +0530: id=gXDfwfPAUSf, floating=true
  TZ-DD-F: Edit tz change: id=fH8OD3x1yWM, floating=true

=== END ===
```

### SQLite verification

```
persistentIdentifier  name                              dateDue                   effectiveDateDue
--------------------  --------------------------------  ------------------------  ----------------
j5TckkeVYMg           TZ-DD-A: UTC summer               2026-07-15T10:00:00.000   805798800
cIlCdvQY0db           TZ-DD-B: UTC winter               2026-12-15T09:00:00.000   819018000
mKgFOOIohDA           TZ-DD-C: Naive no-Z               2026-07-15T09:00:00.000   805795200
f8JwucOfA1X           TZ-DD-D: Date-only                2026-07-15T01:00:00.000   805766400
gXDfwfPAUSf           TZ-DD-E: Offset +0530             2026-07-15T04:30:00.000   805779000
fH8OD3x1yWM           TZ-DD-F: Edit tz change           2026-07-15T04:30:00.000   805779000
opxuahmZtlT           TZ-DD-G: DateComponents EST       2026-07-15T13:00:00.000Z  805813200
eZT-VuI2R4t           TZ-DD-H: Non-floating from start
cwIl1rVBAmG           TZ-DD-I: Date then toggle         2026-07-15T09:00:00.000Z  805798800
```

## Interpretation

### Part 1: Toggle is instant, invisible from same TZ

`getTime()` = `1784106000000` before, during (`false`), and after (restored to `true`). From the same timezone, toggling changes nothing in the Date API. Reinterpretation only manifests on TZ change (proven by script 01c).

### Part 2: DateComponents with "EST" — DST resolution

> [!warning] Abbreviations are DST-aware
>
> - `new TimeZone("EST")` resolved to **EDT** (America/New_York in summer)
> - `secondsFromGMT=-14400` (UTC-4), not UTC-5
> - `09:00 EDT = 13:00 UTC` — **not** `14:00 UTC` as EST would give
>
> OmniJS applies current DST rules when resolving abbreviations => **"EST" in July gives EDT**

Task created as 📌 non-floating — stored with Z suffix in SQLite.

### Part 3: Order enforced

> [!warning] Date before flag
>
> - OmniFocus throws `"Set due or defer date to edit the time zone"` on `floating=false` for a dateless task
> - The task was still created (`new Task()` succeeded), just dateless
> - Only valid sequence: **set date first, then toggle floating**

### Part 4: Date-then-toggle works

Set `dueDate` first → toggle `floating=false` → no error. `getTime()` unchanged from same TZ (consistent with Part 1).

### Part 5: H vs I

H failed => no direct comparison. The error itself is the finding.

### SQLite verification — re-encoding on toggle

| Task | `dateDue` | Z? | Notes |
|------|-----------|-----|-------|
| A-F (🌊) | naive local time | No | Standard floating encoding |
| G (📌, DateComponents) | `13:00:00.000Z` | Yes | UTC-anchored, matches 09:00 EDT |
| H (error) | *(empty)* | — | Created but dateless |
| I (📌, toggled) | `09:00:00.000Z` | Yes | Was `10:00:00.000` local when 🌊, re-encoded to UTC |

> [!important] Active re-encoding
>
> - TZ-DD-I was stored as `10:00:00.000` (naive BST local) when 🌊
> - Toggled to 📌 → re-encoded to `09:00:00.000Z` (UTC)
> - Same moment, different encoding — OmniFocus **rewrites the date text** on flag change
> - `effectiveDateDue` (805798800) matches TZ-DD-A — same UTC moment

## 🤯 Surprises

- **Order enforcement** — didn't expect OmniFocus to throw on `floating=false` for a dateless task
  - The flag conceptually applies to the task, not the date
- **TZ-DD-H still exists** as a dateless task despite the error — `new Task()` succeeded, only the floating assignment failed
- **Active re-encoding** — OmniFocus doesn't just flip a boolean, it rewrites the date text representation
- **EST → EDT** — script expected fixed UTC-5, got DST-aware UTC-4

## Questions Answered

| Question | Answer | Evidence |
|----------|--------|----------|
| Q2 | `floating=false` works but **only after a date exists**. Same TZ: no difference. Different TZ: 📌 preserves UTC (01c). SQLite stores 📌 with Z suffix. | Part 1: identical `getTime()`. Part 3: error. SQLite: Z on G, I. |
| Q7 | Toggle is instant, persists, triggers SQLite re-encoding (naive local ↔ UTC+Z). No `getTime()` change from same TZ. | Part 1: toggle + restore. SQLite: I re-encoded. |
| Q8 | `new TimeZone("EST")` works but gives EDT in summer (DST-aware). IANA names → null (script 01). Abbreviations map to IANA zones internally. | Part 2: EST → EDT, `-14400`. |
