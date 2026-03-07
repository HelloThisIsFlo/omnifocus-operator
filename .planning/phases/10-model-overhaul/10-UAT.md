---
status: complete
phase: 10-model-overhaul
source: [10-01-SUMMARY.md, 10-02-SUMMARY.md, 10-03-SUMMARY.md, 10-04-SUMMARY.md]
started: 2026-03-07T14:00:00Z
updated: 2026-03-07T14:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Two-Axis Status on Tasks
expected: Query tasks via the MCP `list_all` tool. Each task should have `urgency` (one of: overdue, due_soon, none) and `availability` (one of: available, blocked, completed, dropped) fields. There should be NO `status` field on tasks.
result: pass

### 2. Two-Axis Status on Projects
expected: In the same `list_all` output, each project should have `urgency` and `availability` fields (same enum values as tasks) instead of a `status` field.
result: pass

### 3. Unified Availability on Tags
expected: Each tag should have an `availability` field (NOT `status`) with values from: available, blocked, dropped. The field name is `availability`, not `status`. The enum type is `TagAvailability`.
result: pass

### 4. Unified Availability on Folders
expected: Each folder should have an `availability` field (NOT `status`) with values from: available, dropped. Same naming convention as tags.
result: pass

### 5. Snake Case Enum Values
expected: All enum values in the output should be snake_case (e.g., `due_soon`, `available`, `on_hold` should NOT appear as `DueSoon`, `Available`, `OnHold`).
result: pass

### 6. Deprecated Fields Removed from Tasks
expected: Tasks should NOT have any of these fields: `active`, `effectiveActive`, `completed`, `completedByChildren`, `sequential`, `shouldUseFloatingTimeZone`.
result: pass

### 7. Deprecated Fields Removed from Projects
expected: Projects should NOT have: `status`, `taskStatus`, `containsSingletonActions`, `effectiveCompletionDate`. Projects should still have `completionDate` (that one is real).
result: pass

### 8. Tags Missing allowsNextAction
expected: Tags should NOT have an `allowsNextAction` field (it was removed as deprecated).
result: pass

### 9. ScheduleType Has No "none" Value
expected: If any tasks have a `repetitionRule`, the `scheduleType` should be either `regularly` or `from_completion`. There should be no `none` value. Tasks without repetition should have `repetitionRule: null` (the field omitted or null, not a rule with scheduleType "none").
result: pass

### 10. UAT Script Validates Full Pipeline
expected: Run `python uat/test_model_overhaul.py` manually. The script should connect to OmniFocus, pull a snapshot, run it through the adapter and Pydantic validation, and report success with counts of entities validated.
result: pass (initially failed — script had stale 'status' checks for tags/folders, user fixed it, retest passed with 10,272 checks / 0 failures)

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
