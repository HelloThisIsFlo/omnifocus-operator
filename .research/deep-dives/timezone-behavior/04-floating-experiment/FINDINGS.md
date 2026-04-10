# Floating Timezone Experiment — Findings

> Toggling floating is instant but invisible from the same TZ. Order matters: date must exist before setting floating=false. `new TimeZone("EST")` gives EDT in summer. SQLite re-encodes on toggle (naive local ↔ UTC+Z).

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

### Part 1: Toggle is instant but invisible from the same TZ

`getTime()` = `1784106000000` before, during (false), and after (restored to true). From the same timezone, toggling floating changes nothing observable in the Date API. The reinterpretation only manifests when the system timezone changes (proven by script 01c's cross-TZ experiment).

### Part 2: DateComponents with EST — DST resolution quirk

- `new TimeZone("EST")` resolved to **EDT** (America/New_York in summer), `secondsFromGMT=-14400` (UTC-4)
- Result: `09:00 EDT = 13:00 UTC`, not `14:00 UTC` as EST (UTC-5) would give
- OmniJS applies current DST rules when resolving abbreviations — "EST" in July gives EDT
- Task created as non-floating with `floating=false` — stored with Z suffix in SQLite

### Part 3: Order enforced — date must exist before toggling floating

OmniFocus throws `"Set due or defer date to edit the time zone"` when setting `shouldUseFloatingTimeZone=false` on a dateless task. The task was still created (via `new Task()`), just dateless.

### Part 4: Date-then-toggle works

Setting dueDate first, then toggling floating=false — no error. `getTime()` unchanged from the same TZ (consistent with Part 1).

### Part 5: H vs I — can't compare, but the error is the finding

H failed, so no direct comparison. The takeaway: the only valid sequence is date first, then toggle floating.

### SQLite verification — re-encoding on toggle

| Task | dateDue | Z? | Notes |
|------|---------|-----|-------|
| A-F (floating) | naive local time | No Z | Standard floating encoding |
| G (fixed, DateComponents) | `13:00:00.000Z` | Z | UTC-anchored, matches 09:00 EDT |
| H (error case) | *(empty)* | — | Task created but dateless |
| I (date then toggle) | `09:00:00.000Z` | Z | Was `10:00:00.000` local when floating, re-encoded to UTC on toggle |

TZ-DD-I is the most interesting: originally stored as `10:00:00.000` (naive BST local) when floating, then re-encoded to `09:00:00.000Z` (UTC) when toggled to fixed. Same moment, different encoding. OmniFocus actively re-encodes the SQLite text when the floating flag changes.

TZ-DD-I's `effectiveDateDue` (805798800) matches TZ-DD-A's — both represent the same UTC moment (2026-07-15T09:00:00Z).

## Key Findings

- **Toggle is instant, invisible from same TZ.** `getTime()` unchanged across toggle. Reinterpretation only on TZ change.
- **Order enforced**: must set a date before `shouldUseFloatingTimeZone=false`. OmniFocus throws if you try otherwise.
- **`new TimeZone("EST")` gives EDT in summer.** Abbreviations resolve through current DST rules, not literal fixed offsets.
- **SQLite re-encodes on floating toggle.** Floating = naive local (no Z), fixed = UTC (Z suffix). OmniFocus converts between them when the flag changes.
- **IANA names still don't work** for `new TimeZone()` — but abbreviations resolve to the right IANA zone internally (EST → America/New_York).

## Surprises / Unexpected Results

- **The order enforcement** — didn't expect OmniFocus to throw on `floating=false` for a dateless task. The flag conceptually applies to the task, not the date.
- **TZ-DD-H still exists** as a dateless task despite the error — `new Task()` succeeded, only the floating assignment failed.
- **Active re-encoding** in SQLite when toggling the flag — OmniFocus doesn't just flip a boolean, it rewrites the date text representation.
- **EST → EDT resolution** — the script expected fixed UTC-5, got DST-aware UTC-4. OmniJS abbreviations are DST-aware.

## Questions Answered

| Question | Answer | Evidence |
|----------|--------|----------|
| Q2 | Setting floating=false works but only after a date exists. From same TZ: no observable difference. From different TZ: fixed preserves UTC (01c). SQLite stores fixed dates with Z suffix. | Part 1: identical getTime(). Part 3: error without date. SQLite: Z suffix on G, I. |
| Q7 | Toggle is instant, persists, and triggers SQLite re-encoding (naive local ↔ UTC+Z). No getTime() change from same TZ. | Part 1: toggle + restore. SQLite: I re-encoded from local to UTC. |
| Q8 | `new TimeZone("EST")` works but resolves to EDT in summer (DST-aware). IANA names (`Europe/London`) return null (script 01). Abbreviations map to IANA zones internally. | Part 2: EST → EDT, secondsFromGMT=-14400. Script 01d: Europe/London → null. |
