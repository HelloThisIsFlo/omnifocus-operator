---
status: complete
phase: 44-migrate-list-query-filters-to-patch-semantics-eliminate-null
source: [44-01-SUMMARY.md, 44-02-SUMMARY.md]
started: 2026-04-07T15:10:00Z
updated: 2026-04-07T15:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Null Filter Rejection
expected: Call `list_tasks` with a filter field set to null (e.g., `flagged: null`). Server returns an educational error message explaining to omit the field instead of sending null.
result: pass

### 2. Empty Tags Rejection
expected: Call `list_tasks` with `tags: []` (empty list). Server returns an error message explaining that an empty tag list is not a meaningful filter.
result: pass

### 3. Empty Availability Rejection
expected: Call `list_tasks` with `availability: []` (empty list). Server returns an error message explaining that an empty availability list is not valid.
result: pass

### 4. Filter Omission Works (UNSET Behavior)
expected: Call `list_tasks` with no filter fields (or only `limit`). Returns tasks normally — omitting fields means "no filter," not an error.
result: pass

### 5. AvailabilityFilter ALL Shorthand
expected: Call `list_tasks` with `availability: ["ALL"]`. Returns tasks across all availability statuses (available, remaining, completed). Equivalent to not filtering by availability at all.
result: pass

### 6. Mixed ALL Warning
expected: Call `list_tasks` with `availability: ["ALL", "available"]`. Request succeeds and returns results, but includes a warning about mixing ALL with specific values (redundant).
result: pass

### 7. Offset Defaults to Zero
expected: Call `list_tasks` with no `offset` field. Results start from the beginning (offset 0). No error about missing offset.
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
