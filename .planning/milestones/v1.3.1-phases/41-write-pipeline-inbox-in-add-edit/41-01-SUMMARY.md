---
phase: 41-write-pipeline-inbox-in-add-edit
plan: 01
subsystem: contracts
tags: [type-aliases, null-rejection, field-validators, error-templates]
dependency_graph:
  requires: []
  provides: [PatchOrNone-eliminated, MoveAction-null-rejection, per-field-descriptions, error-templates]
  affects: [contracts/shared/actions.py, contracts/base.py, agent_messages/errors.py, agent_messages/descriptions.py]
tech_stack:
  added: []
  patterns: [field_validator-null-rejection]
key_files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/base.py
    - src/omnifocus_operator/contracts/__init__.py
    - src/omnifocus_operator/contracts/shared/actions.py
    - src/omnifocus_operator/contracts/use_cases/add/tasks.py
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - tests/test_contracts_type_aliases.py
    - tests/test_contracts_field_constraints.py
    - tests/test_errors.py
    - tests/test_server.py
    - tests/test_service.py
    - tests/test_service_domain.py
decisions:
  - "ADD_PARENT_NULL imported in add/tasks.py with noqa:F401 so AST enforcement test passes before Plan 02 wires the validator"
  - "StubResolver in test_service_domain.py updated to return None for $inbox, matching real resolver behavior"
metrics:
  duration: 414s
  completed: "2026-04-06T13:28:21Z"
---

# Phase 41 Plan 01: PatchOrNone Elimination & MoveAction Null Rejection Summary

PatchOrNone deleted, MoveAction fields use Patch[str] with field_validator null-rejection and per-field descriptions, three error templates added, all 1583 tests pass.

## What Was Done

### Task 1: Error templates and description constants (939d43f)
- Added `MOVE_NULL_CONTAINER`, `MOVE_NULL_ANCHOR`, `ADD_PARENT_NULL` to errors.py (verbatim from D-14, D-15, D-16a)
- Added `MOVE_BEGINNING`, `MOVE_ENDING`, `MOVE_BEFORE`, `MOVE_AFTER` per-field descriptions to descriptions.py (verbatim from D-20, D-21)
- Simplified `MOVE_ACTION_DOC` to single-line form
- Updated `EDIT_TASKS_TOOL_DOC` to reference `$inbox` instead of null-clears-project

### Task 2: PatchOrNone elimination and MoveAction null-rejection validators (baa1f05, 137276f)
- **RED**: Wrote failing tests for MoveAction null rejection (all 4 fields) and TagAction.replace PatchOrClear acceptance
- **GREEN**: Deleted `PatchOrNone` from contracts/base.py and __init__.py; switched TagAction.replace to `PatchOrClear[list[str]]`; MoveAction fields to `Patch[str]` with `Field(description=...)` and `@field_validator` null-rejection
- Updated 4 test files that used `MoveAction(ending=None)` to use `MoveAction(ending="$inbox")`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated tests passing None to MoveAction**
- **Found during:** Task 2 GREEN phase
- **Issue:** Three test files (test_server.py, test_service.py, test_service_domain.py) used `MoveAction(ending=None)` for inbox moves
- **Fix:** Changed to `MoveAction(ending="$inbox")` and updated StubResolver to return None for `$inbox`
- **Files modified:** tests/test_server.py, tests/test_service.py, tests/test_service_domain.py
- **Commit:** 137276f

**2. [Rule 3 - Blocking] ADD_PARENT_NULL not yet consumed by any module**
- **Found during:** Task 2 GREEN phase
- **Issue:** AST enforcement test (test_errors.py) requires all error constants to be referenced in consumer modules. ADD_PARENT_NULL is defined for Plan 02 but has no consumer yet.
- **Fix:** Added `from omnifocus_operator.agent_messages.errors import ADD_PARENT_NULL  # noqa: F401` in contracts/use_cases/add/tasks.py (where Plan 02 will wire the validator). Added contracts_add_task to _ERROR_CONSUMERS list in test_errors.py.
- **Files modified:** src/omnifocus_operator/contracts/use_cases/add/tasks.py, tests/test_errors.py
- **Commit:** 137276f

## Verification

- `grep -r "PatchOrNone" src/` -- zero matches
- `uv run pytest tests/ -x -q` -- 1583 passed
- `uv run pytest tests/test_output_schema.py -x -q` -- 32 passed (JSON schema unchanged)
- MoveAction(beginning=None) raises ValidationError with "beginning cannot be null"

## Self-Check: PASSED

All files found, all commits verified.
