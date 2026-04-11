---
status: complete
phase: 49-implement-naive-local-datetime-contract-for-all-date-inputs
source: 49-01-SUMMARY.md, 49-02-SUMMARY.md, 49-03-SUMMARY.md
started: 2026-04-11T08:00:00Z
updated: 2026-04-11T08:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Test suite passes
expected: Run `uv run pytest` — all 1951+ tests pass, no failures related to date types.
result: skipped
reason: Covered by CI

### 2. Add task with naive datetime (no timezone)
expected: Call `add_tasks` with a naive datetime like `"dueDate": "2026-07-15T17:00:00"` (no Z, no +offset). Task is created successfully in OmniFocus with the correct due date.
result: pass

### 3. Add task with date-only string
expected: Call `add_tasks` with a date-only value like `"dueDate": "2026-07-15"`. Task is created successfully — the date is treated as start-of-day (midnight local time).
result: pass

### 4. Add task with timezone (backward compat)
expected: Call `add_tasks` with an aware datetime like `"dueDate": "2026-07-15T17:00:00Z"`. Task is created successfully — the UTC time is converted to local time before storing.
result: pass

### 5. Invalid date rejection
expected: Call `add_tasks` with `"dueDate": "not-a-date"`. Server returns a clear validation error mentioning the expected format (ISO 8601), not a crash or generic error.
result: pass

### 6. Edit task dates with naive string
expected: Call `edit_tasks` on an existing task with `"dueDate": "2026-08-01T09:00:00"` (naive). The task's due date updates correctly in OmniFocus.
result: pass

### 7. Tool descriptions show local time guidance
expected: Inspect the `add_tasks` or `edit_tasks` tool description (via MCP client or schema). DATE_EXAMPLE shows `"2026-03-15T17:00:00"` (no Z). Description mentions dates are in local time.
result: pass

### 8. JSON Schema has no format: date-time on date inputs
expected: Inspect the JSON Schema for `add_tasks` inputSchema. Date fields (dueDate, deferDate, completionDate) should NOT have `"format": "date-time"` — they should be plain `string` type.
result: pass

### 9. Date filter with naive datetime bounds
expected: Call `list_tasks` with `due: {after: "2026-07-01T00:00:00", before: "2026-08-15T23:59:59"}` (naive bounds). Tasks with due dates in that range are returned correctly.
result: pass

## Summary

total: 9
passed: 8
issues: 0
pending: 0
skipped: 1
blocked: 0

## Gaps

[none yet]
