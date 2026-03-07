---
status: complete
phase: 10-model-overhaul
source: [10-01-SUMMARY.md, 10-02-SUMMARY.md, 10-03-SUMMARY.md]
started: 2026-03-07T03:30:00Z
updated: 2026-03-07T03:50:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Two-Axis Status on Tasks
expected: Query tasks via the MCP `list_all` tool. Each task should have `urgency` (one of: overdue, due_soon, none) and `availability` (one of: available, blocked, completed, dropped) fields. There should be NO `status` field on tasks.
result: pass

### 2. Two-Axis Status on Projects
expected: In the same `list_all` output, each project should have `urgency` and `availability` fields instead of a `status` field. Same enum values as tasks.
result: pass

### 3. Snake Case Enum Values + Unified Availability
expected: All enum values in the output should be snake_case. Tags/folders should use availability (not status) with unified vocabulary matching tasks/projects.
result: issue
reported: "TagStatus and FolderStatus should be renamed to TagAvailability and FolderAvailability. Values unified: active->available, on_hold->blocked. All entity types use 'availability' with consistent vocabulary (available/blocked/dropped)."
severity: minor

### 4. Deprecated Fields Removed
expected: Tasks and projects should NOT have any of these fields: `active`, `effectiveActive`, `completed`, `completedByChildren`, `sequential`, `shouldUseFloatingTimeZone`. Tags should NOT have `allowsNextAction`. Projects should NOT have `containsSingletonActions`.
result: issue
reported: "effectiveCompletionDate on projects is always null (370 projects checked). OmniFocus never populates it for projects because projects can't inherit completion from a parent. The regular completionDate is what gets set. It's structurally dead on projects."
severity: minor

### 5. UAT Script Runs Against Live OmniFocus
expected: Run `python uat/test_model_overhaul.py` manually. The script should connect to OmniFocus, pull a snapshot, run it through the adapter and Pydantic validation, and report success with counts of entities validated.
result: pass

### 6. ScheduleType.none Should Not Exist
expected: The ScheduleType enum should not contain a `none` value. When there's no repetition rule, OmniFocus omits the repetitionRule object entirely rather than emitting one with scheduleType "none".
result: issue
reported: "ScheduleType.none is defined in the enum but never appears in the database. When there's no repetition rule, OmniFocus omits the repetitionRule object entirely. The bridge already throws on unknown values, so if none ever came through it should surface as an error, not be silently accepted. Remove none from ScheduleType."
severity: minor

## Summary

total: 6
passed: 3
issues: 3
pending: 0
skipped: 0

## Gaps

- truth: "Deprecated/dead fields should be removed from models"
  status: failed
  reason: "User reported: effectiveCompletionDate on projects is always null (370 projects checked). OmniFocus never populates it for projects because projects can't inherit completion from a parent. The regular completionDate is what gets set. It's structurally dead on projects."
  severity: minor
  test: 4
  fix: "Remove effectiveCompletionDate from Project model only (keep on Task where it's meaningful). Override or exclude in Project class."
  artifacts:
    - path: "src/omnifocus_operator/models/base.py"
      issue: "ActionableEntity defines effectiveCompletionDate, inherited by both Task and Project"
    - path: "src/omnifocus_operator/models/project.py"
      issue: "Needs to exclude effectiveCompletionDate"
  missing: []

- truth: "ScheduleType enum should only contain values that actually appear in OmniFocus data"
  status: failed
  reason: "User reported: ScheduleType.none is defined in the enum but never appears in the database. When there's no repetition rule, OmniFocus omits the repetitionRule object entirely. Remove none from ScheduleType."
  severity: minor
  test: 6
  fix: "Remove ScheduleType.none from enum. Add adapter guardrail: if scheduleType is 'None'/'none', replace the entire repetitionRule with null instead of crashing. Cover with unit test (can't e2e test since no real data has this)."
  artifacts:
    - path: "src/omnifocus_operator/models/enums.py"
      issue: "ScheduleType has unused 'none' value"
    - path: "src/omnifocus_operator/bridge/adapter.py"
      issue: "Needs guardrail for scheduleType=none -> repetitionRule=null"
  missing:
    - "Unit test: adapter receives scheduleType 'None', returns entity with repetitionRule=null"
    - "Integration test: full pipeline (bridge output -> adapter -> Pydantic) handles scheduleType 'None' gracefully"

- truth: "Tag and folder status should use unified availability concept"
  status: failed
  reason: "User decided: TagStatus/FolderStatus should be renamed to TagAvailability/FolderAvailability to unify under one concept. Values unified: active->available, on_hold->blocked. All entity types now use 'availability' with consistent vocabulary."
  severity: minor
  test: 3
  fix: |
    Rename TagStatus -> TagAvailability (values: available, blocked, dropped).
    Rename FolderStatus -> FolderAvailability (values: available, dropped).
    Update adapter mappings: OnHold->blocked (was on_hold), Active->available (was active).
    Update Tag.status field -> Tag.availability, Folder.status field -> Folder.availability.
    Update all references: models/__init__.py exports, adapter mapping tables, tests, simulator data, InMemoryBridge seed data.
  artifacts:
    - path: "src/omnifocus_operator/models/enums.py"
      issue: "TagStatus and FolderStatus need rename + value changes"
    - path: "src/omnifocus_operator/models/tag.py"
      issue: "status field -> availability field"
    - path: "src/omnifocus_operator/models/folder.py"
      issue: "status field -> availability field"
    - path: "src/omnifocus_operator/bridge/adapter.py"
      issue: "Mapping tables need updated target values"
    - path: "src/omnifocus_operator/models/__init__.py"
      issue: "Export renames"
  missing: []
