---
phase: 41-write-pipeline-inbox-in-add-edit
plan: 02
subsystem: service, contracts
tags: [patch-semantics, null-rejection, inbox-pipeline, field-validator]
dependency_graph:
  requires: [PatchOrNone-eliminated, MoveAction-null-rejection, error-templates]
  provides: [AddTaskCommand-Patch-parent, inbox-pipeline-wired, WRIT-01-through-WRIT-05]
  affects: [contracts/use_cases/add/tasks.py, service/service.py]
tech_stack:
  added: []
  patterns: [is_set-guard-in-add-pipeline]
key_files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/use_cases/add/tasks.py
    - src/omnifocus_operator/service/service.py
    - tests/test_contracts_field_constraints.py
    - tests/test_service.py
    - tests/test_models.py
decisions:
  - "WRIT-03 wording already updated in REQUIREMENTS.md during discuss phase -- no change needed"
metrics:
  duration: 263s
  completed: "2026-04-06T13:34:23Z"
---

# Phase 41 Plan 02: $inbox Pipeline Wiring & AddTaskCommand Patch[str] Summary

AddTaskCommand.parent converted to Patch[str] with UNSET default and null-rejection validator; service pipeline uses is_set() guard for inbox dispatch; 10 new integration tests confirm all WRIT requirements; 1593 tests pass.

## What Was Done

### Task 1: AddTaskCommand.parent Patch[str] conversion and pipeline wiring (1dccec7, 7c8faa5)
- **RED**: Wrote 10 failing/new tests across test_contracts_field_constraints.py and test_service.py
  - Contract: null rejected, UNSET on omit, $inbox accepted, string accepted
  - Service add: parent omitted -> inbox, parent=$inbox -> inbox, parent=project -> resolves
  - Service edit: ending/beginning=$inbox -> inbox, before=$inbox -> cross-type error
- **GREEN**: Converted `AddTaskCommand.parent` from `str | None = None` to `Patch[str] = UNSET`
  - Added `@field_validator("parent", mode="before")` with `ADD_PARENT_NULL` error
  - Changed `_resolve_parent()` from `if self._command.parent is None` to `if not is_set(self._command.parent)`
  - Updated `_validate()` debug log to display "UNSET" for omitted parent
  - Wired `ADD_PARENT_NULL` import (removed noqa:F401 placeholder from Plan 01)

### Task 2: REQUIREMENTS.md WRIT-03 wording (no change needed)
- Verified WRIT-03 already contains revised wording: "returns error (null not accepted; omit field for inbox or use `$inbox`)"
- Updated during discuss phase -- no file modification required

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_models assertion for parent default**
- **Found during:** Task 1 GREEN phase
- **Issue:** `test_add_task_command_minimal` asserted `command.parent is None` but parent is now UNSET
- **Fix:** Changed to `not is_set(command.parent)` and added `is_set` import
- **Files modified:** tests/test_models.py
- **Commit:** 7c8faa5

## Verification

- `uv run pytest tests/test_contracts_field_constraints.py` -- 17 passed (4 new AddTaskCommand null-rejection tests)
- `uv run pytest tests/test_service.py` -- all passed (6 new inbox pipeline integration tests)
- `uv run pytest tests/test_output_schema.py -x -q` -- 32 passed (schema valid, parent is string-only)
- `uv run pytest tests/ -x -q` -- 1593 passed
- AddTaskCommand(parent=None) raises ValidationError with "parent cannot be null"
- AddTaskCommand() omitted parent is UNSET (inbox)
- AddTaskCommand(parent="$inbox") resolves to inbox via resolve_container
- MoveAction ending/beginning="$inbox" moves task to inbox
- MoveAction before="$inbox" raises cross-type error

## Self-Check: PASSED

All files found, all commits verified.
