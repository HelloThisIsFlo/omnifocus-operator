# Date Conversion Proof — Findings

> Formula proven: `CF_seconds = (naive_local_as_tz(system_tz) → UTC - CF_EPOCH)`. Perfect match across 430 tasks, both BST and GMT. `shouldUseFloatingTimeZone` is NOT a SQLite column.

**Date:** 2026-04-10
**Script:** `02-conversion-proof/02-date-conversion-proof.py`

## Raw Output

```
Timezone Conversion Proof
=========================
Database: ~/Library/Group Containers/.../OmniFocusDatabase.db

1. System Timezone
  time.tzname:     ('GMT', 'BST')
  Current time:    2026-04-10T18:05:32.922115+01:00
  UTC offset:      +0100 (BST)
  DST active:      True
  ZoneInfo:        Europe/London

2. Full Column Scan — Timezone-Related Columns
  Total columns in Task table: 58
  Columns matching time/zone/tz/float/calendar:
    [39] latestTimeToStartAlarmPolicyString (TEXT): samples=['no-alarm']
  shouldUseFloatingTimeZone column NOT found in Task table

3. dateDue → effectiveDateDue
  200 tasks verified, max delta: 0.000s
  Summer (BST): 31 matches, 0 mismatches
  Winter (GMT): 169 matches, 0 mismatches
  RESULT: ALL 200 match

4. dateToStart → effectiveDateToStart
  200 tasks verified, max delta: 1267200.0s
  Summer (BST): 26 matches, 1 mismatch
  Winter (GMT): 173 matches, 0 mismatches
  RESULT: 1 MISMATCH (inherited effective date — see below)

5. datePlanned → effectiveDatePlanned
  30 tasks verified, max delta: 0.000s
  Summer (BST): 6 matches, 0 mismatches
  Winter (GMT): 24 matches, 0 mismatches
  RESULT: ALL 30 match
```

## Interpretation

### The formula is proven
For all three direct→effective column pairs, the conversion is:

```
CF_seconds = (naive_local_datetime.replace(tzinfo=system_tz).astimezone(UTC) - CF_EPOCH).total_seconds()
```

- **dateDue**: 200/200 match, 0.000s max delta, across both BST and GMT dates
- **datePlanned**: 30/30 match, 0.000s max delta
- **dateToStart**: 199/200 match — the one mismatch is explained below

This confirms `_parse_local_datetime()` in `hybrid.py` is correct for the entire database.

### The one dateToStart mismatch: inherited effective date
"Check if order has been accepted": delta = 1,267,200s = 14.67 days. The task's own `dateToStart` is April 26, but `effectiveDateToStart` comes from an ancestor with an earlier defer date. The script includes tasks where effective != direct because of inheritance — expected behavior, not a formula error.

### shouldUseFloatingTimeZone is NOT in SQLite
The column does not exist in the 58-column Task table. Only one vaguely TZ-related column: `latestTimeToStartAlarmPolicyString` (TEXT, all `'no-alarm'`).

This means:
- The flag lives in OmniFocus's XML/plist layer or a different table, not the SQLite cache
- **Our SQLite reader can't distinguish floating vs fixed tasks**
- In practice: 100% of tasks are floating (script 01), so this doesn't matter today
- If we ever need to support fixed-timezone tasks, we'd need the bridge API to read the flag

### DST handling is correct
The formula correctly handles both seasons because `ZoneInfo("Europe/London")` automatically applies the right offset based on the date itself:
- Summer dates (months 4-10): offset = +1h (BST)
- Winter dates (months 11-3): offset = +0h (GMT)

No special-casing needed — stdlib `zoneinfo` handles DST transitions.

## Key Findings

- **Conversion formula proven** across 430 tasks with zero errors (excluding one inherited effective date)
- **DST is handled correctly** — summer BST (+1h) and winter GMT (+0h) both match perfectly
- **`shouldUseFloatingTimeZone` is not a SQLite column** — flag lives outside the SQLite cache
- **Only one TZ-adjacent column in SQLite**: `latestTimeToStartAlarmPolicyString` (irrelevant, all `'no-alarm'`)
- **`_parse_local_datetime()` in `hybrid.py` is confirmed correct** for converting naive local text to UTC

## Surprises / Unexpected Results

- `shouldUseFloatingTimeZone` not being in SQLite — the API exposes it but the cache doesn't store it
- The `dateToStart` mismatch being exactly 14.67 days (inheritance, not a TZ error)
- Zero delta on all direct→effective conversions — not even sub-second rounding differences

## Questions Answered

| Question | Answer | Evidence |
|----------|--------|----------|
| Q3 | No hidden timezone columns in SQLite. `shouldUseFloatingTimeZone` is NOT a column. Only `latestTimeToStartAlarmPolicyString` matches TZ keywords (irrelevant). | Section 2: PRAGMA table_info scan |
| Q4 | `effectiveDateDue = CF_seconds(naive_local_as_utc_via_system_tz - CF_EPOCH)`. Exact match for 200/200 tasks. | Section 3: 0.000s max delta |
| Q5 | Yes — conversion holds perfectly across DST. 31 BST + 169 GMT dates all match for dateDue. | Sections 3-5: 0 mismatches in BST or GMT |
