---
status: resolved
trigger: "Investigate ISSUE-2: Timezone discrepancy on deferDate vs effectiveDeferDate"
created: 2026-03-08T00:00:00Z
updated: 2026-03-08T02:00:00Z
---

## Current Focus

hypothesis: CONFIRMED -- _parse_timestamp treats local-time text as UTC
test: verified with real SQLite data and CF epoch cross-reference
expecting: n/a (root cause found)
next_action: report diagnosis

## Symptoms

expected: deferDate should match the sent value "2026-04-01T09:00:00Z"
actual: deferDate returned as "2026-04-01T10:00:00Z" (+1h), effectiveDeferDate correct at "2026-04-01T09:00:00Z"
errors: no error, silent data transformation
reproduction: send add_tasks with deferDate "2026-04-01T09:00:00Z", observe response via get_all/get_task
started: discovered during UAT of add_tasks (test 17)

## Eliminated

- hypothesis: bug in bridge.js write path (date set incorrectly)
  evidence: bridge uses `new Date(params.deferDate)` which correctly parses UTC ISO strings; OmniFocus stores the correct moment internally (effectiveDateToStart CF epoch is correct)
  timestamp: 2026-03-08

- hypothesis: Pydantic serialization alters the date
  evidence: `model_dump(mode="json")` produces exact ISO string "2026-04-01T09:00:00Z" (verified)
  timestamp: 2026-03-08

## Evidence

- timestamp: 2026-03-08
  checked: OmniFocus SQLite schema (PRAGMA table_info(Task))
  found: Two distinct column type conventions -- `datetime` for user-set dates, `timestamp` for computed/effective dates
  implication: OmniFocus stores these differently

- timestamp: 2026-03-08
  checked: Actual stored values for dateToStart vs effectiveDateToStart
  found: dateToStart is stored as TEXT (ISO 8601, local time, no timezone): e.g. "2026-08-03T08:00:00.000". effectiveDateToStart is stored as INTEGER (CF epoch seconds, UTC): e.g. 807433200
  implication: The two columns use completely different storage formats

- timestamp: 2026-03-08
  checked: Cross-referenced 3 rows converting CF epoch to London local time
  found: In ALL cases, dateToStart TEXT matches the London local time of the UTC moment stored in effectiveDateToStart. Summer dates (BST, UTC+1) show +1h offset. Winter dates (GMT, UTC+0) show 0 offset.
  implication: dateToStart TEXT is local time (system timezone), NOT UTC

- timestamp: 2026-03-08
  checked: _parse_timestamp() in hybrid.py (lines 74-98)
  found: For text values without timezone suffix, line 95 appends "+00:00" (assumes UTC). This is WRONG for `datetime`-type columns which store local time.
  implication: All three user-settable date fields are misinterpreted as UTC

- timestamp: 2026-03-08
  checked: System timezone
  found: GMT/BST (Europe/London). April 1 2026 = BST (UTC+1). 09:00 UTC = 10:00 BST.
  implication: Explains exactly the +1h shift: "10:00" local stored as text, read as "10:00 UTC"

- timestamp: 2026-03-08
  checked: Which columns are affected (datetime vs timestamp type)
  found: THREE columns use `datetime` type (local-time text): dateDue, datePlanned, dateToStart. ALL `effective*` and lifecycle columns use `timestamp` type (CF epoch integer).
  implication: Bug affects dueDate and plannedDate too, not just deferDate

## Resolution

root_cause: |
  OmniFocus SQLite stores user-settable dates (dateToStart, dateDue, datePlanned) as
  LOCAL TIME ISO 8601 text strings WITHOUT timezone info (column type: `datetime`).
  Computed/effective dates (effectiveDateToStart, etc.) are stored as CF epoch integers
  in UTC (column type: `timestamp`).

  `_parse_timestamp()` in hybrid.py treats ALL timezone-naive ISO strings as UTC
  (appends "+00:00" on line 95). This is correct for timestamp columns (which are
  numeric, not strings) but WRONG for datetime columns (which are local-time strings).

  Result: during DST periods (BST=UTC+1), deferDate/dueDate/plannedDate are shifted
  +1h. During GMT periods (UTC+0), values happen to be correct by coincidence.

fix:
verification:
files_changed: []
