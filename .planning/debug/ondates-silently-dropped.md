---
status: diagnosed
trigger: "monthly_day_in_month with onDates=[1, 15, -1] loses 15 and -1 on round-trip"
created: 2026-03-28T00:00:00Z
updated: 2026-03-28T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — two independent bugs both drop multi-value onDates
test: traced full write and read paths
expecting: n/a — root cause found
next_action: return diagnosis

## Symptoms

expected: get_task round-trip returns onDates [1, 15, -1]
actual: get_task returns onDates [1] — values 15 and -1 silently dropped
errors: none (silent data loss)
reproduction: add_tasks with monthly_day_in_month frequency and onDates=[1, 15, -1], then get_task
started: unknown

## Eliminated

## Evidence

- timestamp: 2026-03-28T00:01:00Z
  checked: builder.py line 99 — build_rrule() BYMONTHDAY construction
  found: `parts.append(f"BYMONTHDAY={frequency.on_dates[0]}")` — hardcoded [0] index, only emits first value
  implication: WRITE PATH BUG — onDates=[1,15,-1] produces "BYMONTHDAY=1" instead of "BYMONTHDAY=1,15,-1"

- timestamp: 2026-03-28T00:02:00Z
  checked: parser.py lines 255-264 — _parse_monthly_bymonthday()
  found: `day = int(bymonthday_value)` — calls int() on the raw string, which would fail on "1,15,-1" (comma-separated)
  implication: READ PATH BUG — parser treats BYMONTHDAY value as single integer, cannot parse comma-separated values

- timestamp: 2026-03-28T00:03:00Z
  checked: bridge.js handleAddTask and handleEditTask
  found: Bridge passes ruleString directly to OmniJS Task.RepetitionRule constructor — no onDates transformation at bridge level
  implication: Bridge is a pass-through for ruleString; the bug is entirely in Python rrule builder + parser

- timestamp: 2026-03-28T00:04:00Z
  checked: payload.py _build_repetition_rule_payload()
  found: Calls build_rrule(frequency, end) which returns the already-truncated ruleString
  implication: Payload layer is fine; it delegates to build_rrule which is where the write-side truncation happens

- timestamp: 2026-03-28T00:05:00Z
  checked: Existing tests in test_rrule.py and golden master snapshots
  found: All existing BYMONTHDAY tests use single values (15, -1). No test for multi-value onDates.
  implication: Bug was never caught because multi-value scenario was never tested

## Resolution

root_cause: Two independent bugs silently drop multi-value onDates. (1) WRITE: builder.py line 99 hardcodes `on_dates[0]`, emitting only the first value. (2) READ: parser.py line 261 calls `int(bymonthday_value)` which cannot parse comma-separated values like "1,15,-1".
fix: (1) Builder: emit comma-joined values `",".join(str(d) for d in frequency.on_dates)`. (2) Parser: split on comma and parse each value `[int(d) for d in bymonthday_value.split(",")]`.
verification:
files_changed: []
