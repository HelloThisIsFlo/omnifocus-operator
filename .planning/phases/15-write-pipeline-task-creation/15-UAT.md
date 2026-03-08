---
status: complete
phase: 15-write-pipeline-task-creation
source: 15-01-SUMMARY.md, 15-02-SUMMARY.md, 15-03-SUMMARY.md
started: 2026-03-08T01:00:00Z
updated: 2026-03-08T01:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Create Task with Name Only
expected: `add_tasks` with name-only creates task in OmniFocus Inbox, returns ID and name.
result: pass
coverage: Report #1

### 2. Create Task with Optional Fields
expected: Setting note, dueDate, deferDate, plannedDate, flagged, estimatedMinutes all persist correctly.
result: pass
coverage: Report #2, #11, #12, #19 (dates, fractional estimates)

### 3. Create Task Under a Project
expected: parentId pointing to project nests task under that project, not Inbox.
result: pass
coverage: Report #3 (project), #4 (nested 3-level), #5 (50-task hierarchy)

### 4. Create Task with Tags
expected: tagNames associates tags with task. Tags appear in OmniFocus.
result: pass
coverage: Report #6 (single), #7 (multiple), #8 (by ID), #9 (nonexistent error), #10 (mutual exclusivity)

### 5. Post-Write Freshness
expected: After add_tasks, immediately calling get_all/get_task returns the new task. Cache invalidation works.
result: pass
coverage: Bridge mode via get_task + get_all, Hybrid mode via get_task (_mark_stale confirmed)

### 6. Validation Error — Empty Name
expected: name="" returns clear error, no task created.
result: pass
coverage: Report #21

### 7. Validation Error — Invalid Parent
expected: Fake parentId returns clear error, no task created.
result: pass
coverage: Report #22

## Additional Coverage (beyond planned tests)

### Dates & Scheduling
- #11 plannedDate only → Forecast view ✓
- #12 All three dates combined → round-tripped ✓
- #13 Naive datetime rejected → Pydantic validation ✓

### Status Model
- #14 Flagged inheritance (effectiveFlagged) ✓
- #15 Urgency: overdue ✓
- #16 Urgency: due_soon ✓
- #17 Availability: blocked by defer date ✓

### Edge Cases
- #18 Emoji, special chars, long names ✓
- #19 Fractional estimatedMinutes ✓
- #20 Unknown fields silently ignored ✓

### Parallel Performance
- #23 10 concurrent calls → 10/10 success, ~1s/task ✓
- #24 32 concurrent calls → 32/32 success ✓
- 50-task hierarchy in ~50 seconds ✓

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Observations

- 24 total test scenarios executed (7 planned + 17 additional)
- All 24 passed (20 clean pass, 4 with informational issues logged below)
- Parallel cancellation: Claude Code client cancels sibling calls on error — argues against lifting 1-item limit
- Single-item constraint validated as sufficient for real-world agent workflows

## Issues (informational — not phase 15 regressions)

### ISSUE-1: Note field encoding in hybrid/SQLite mode (medium)
- Notes via SQLite contain .AppleSystemUIFont artifacts, swallowed newlines, HTML-encoded & and >
- Bridge path returns clean plain text
- Action: Investigate alternative SQLite column or strip artifacts in hybrid layer

### ISSUE-2: Timezone discrepancy on deferDate vs effectiveDeferDate (low)
- Sent deferDate 09:00Z, got back 10:00Z (+1h DST shift) but effectiveDeferDate correct at 09:00Z
- Action: Investigate timezone handling difference between the two fields

### ISSUE-3: Mutually exclusive tags not enforced via API (low)
- OmniJS allows assigning multiple exclusive tags; UI-only enforcement
- Action: Consider service-layer validation in future version

### ISSUE-4: Tool description doesn't declare field boundaries (low, DX)
- Agent can't know which fields are unsupported without probing
- Action: Add "only these fields supported" line to tool description

## Gaps

[none — all tests passed]
