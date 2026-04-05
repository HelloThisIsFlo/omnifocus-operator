---
phase: quick
plan: 260331-v9q
subsystem: contracts
tags: [schema, validation, pydantic, field-constraints]
dependency_graph:
  requires: []
  provides: [model-level-name-validation, explicit-flagged-default]
  affects: [add-task-pipeline, edit-task-pipeline, payload-builder]
tech_stack:
  added: []
  patterns: [field_validator-strip-before-min_length, bool-default-over-optional]
key_files:
  created:
    - tests/test_contracts_field_constraints.py
  modified:
    - src/omnifocus_operator/contracts/use_cases/add/tasks.py
    - src/omnifocus_operator/contracts/use_cases/edit/tasks.py
    - src/omnifocus_operator/service/payload.py
    - tests/test_service_payload.py
    - tests/test_models.py
    - tests/test_service.py
decisions:
  - Service-layer name validation kept as defense-in-depth alongside new model-level validators
metrics:
  duration: ~4min
  completed: 2026-03-31T21:37:37Z
  tasks: 2/2
  tests_total: 1383
---

# Quick Task 260331-v9q: Tighten Schema Field Constraints (flagged + name) Summary

Model-level min_length + whitespace strip on task name; flagged default changed from None to False with always-send payload semantics.

## Completed Tasks

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Add field constraint tests (TDD red) | a241857 | Created `tests/test_contracts_field_constraints.py` with 11 tests (6 failing) |
| 2 | Tighten models + update payload | 7eb64f3 | AddTaskCommand name/flagged, EditTaskCommand name validator, payload builder, test updates |

## Changes Made

### AddTaskCommand (`contracts/use_cases/add/tasks.py`)
- `name: str` -> `name: str = Field(min_length=1)` with `_strip_name` validator (mode="before")
- `flagged: bool | None = None` -> `flagged: bool = False`

### EditTaskCommand (`contracts/use_cases/edit/tasks.py`)
- Added `_validate_name` field_validator: strips whitespace, raises ValueError on empty string, passes `_Unset` through

### PayloadBuilder (`service/payload.py`)
- Removed `if command.flagged is not None` guard -- flagged is always bool, always sent to repo

### Test Updates
- `test_service_payload.py`: minimal add payload now asserts `flagged is False`
- `test_models.py`: minimal AddTaskCommand asserts `flagged is False`
- `test_service.py`: add/edit empty name tests now expect `ValidationError` at model level (not `ValueError` from service)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_models.py assertion**
- **Found during:** Task 2
- **Issue:** `test_add_task_command_minimal` asserted `flagged is None` -- now it's `False`
- **Fix:** Changed assertion to `flagged is False`
- **Files modified:** `tests/test_models.py`
- **Commit:** 7eb64f3

**2. [Rule 1 - Bug] Updated test_service.py edit name validation tests**
- **Found during:** Task 2
- **Issue:** Edit task empty/whitespace name tests expected `ValueError` from service layer; now caught at model level
- **Fix:** Changed to expect `ValidationError` from model construction
- **Files modified:** `tests/test_service.py`
- **Commit:** 7eb64f3

## Known Stubs

None.

## Verification

- 1383 tests passed, 0 failed
- Output schema tests: 23/23 passed
- Coverage: 98.11%

## Self-Check: PASSED
