---
phase: 54-batch-processing
plan: "01"
subsystem: contracts
tags: [batch-processing, models, migration, contracts]
dependency_graph:
  requires: []
  provides:
    - MAX_BATCH_SIZE config constant
    - AddTaskResult with status Literal field
    - EditTaskResult with status Literal field
  affects:
    - service/service.py (AddTaskResult/EditTaskResult constructors)
    - service/domain.py (EditTaskResult constructors)
    - server/handlers.py (debug log field reference)
    - all test files asserting on result shape
tech_stack:
  added: []
  patterns:
    - "status: Literal['success','error','skipped'] replacing success: bool"
    - "id/name/error all optional (None default) for batch error/skipped cases"
key_files:
  created: []
  modified:
    - src/omnifocus_operator/config.py
    - src/omnifocus_operator/contracts/use_cases/add/tasks.py
    - src/omnifocus_operator/contracts/use_cases/edit/tasks.py
    - src/omnifocus_operator/service/service.py
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/server/handlers.py
    - tests/test_service.py
    - tests/test_service_domain.py
    - tests/test_models.py
    - tests/test_preferences_warnings_surfacing.py
    - tests/test_server.py
    - tests/test_output_schema.py
decisions:
  - "Kept AddTaskResult and EditTaskResult as separate models (same shape) per existing naming convention — no shared BatchItemResult base"
  - "id/name made optional (None default) to support error/skipped results where no entity was created"
  - "error field added as optional str for error message in batch error cases"
metrics:
  duration_minutes: 15
  completed_date: "2026-04-15"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 12
---

# Phase 54 Plan 01: Model Foundation for Batch Processing Summary

Model migration from `success: bool` to `status: Literal["success", "error", "skipped"]` with optional id/name/error fields across AddTaskResult/EditTaskResult, MAX_BATCH_SIZE = 50 added to config, full codebase migration (5 production files + 6 test files), 2122 tests green.

## What Was Built

- `config.py`: `MAX_BATCH_SIZE: int = 50` added after `DEFAULT_LIST_LIMIT` block
- `contracts/use_cases/add/tasks.py`: `AddTaskResult` rewritten — `success: bool` removed, `status: Literal["success", "error", "skipped"]` added, `id`/`name` made optional, `error: str | None = None` added
- `contracts/use_cases/edit/tasks.py`: same changes as AddTaskResult
- `service/service.py`: 2 construction sites migrated to `status="success"`
- `service/domain.py`: 3 construction sites in `detect_early_return()` migrated to `status="success"`
- `server/handlers.py`: debug log updated from `results[0].success` to `results[0].status`
- 6 test files: ~120 assertion sites migrated from `.success is True` / `["success"] is True` / `"success" in props` / `success=True` constructors

## Decisions Made

- Kept `AddTaskResult` and `EditTaskResult` as separate models with identical shape — no merging into `BatchItemResult`. Consistent with existing naming convention and model-taxonomy.md.
- Made `id`, `name`, `error` all optional with `None` default — required for error/skipped batch items that have no associated entity.
- `status` uses `Literal["success", "error", "skipped"]` at the contract layer (not core model) — follows type constraint boundary rule from model-taxonomy.md.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two `success=True` occurrences in domain.py with different indentation not caught by `replace_all`**
- **Found during:** Task 2
- **Issue:** The `replace_all` edit only matched the 20-space indented pattern; two 16-space indented occurrences remained.
- **Fix:** Two separate targeted edits for the remaining constructors.
- **Files modified:** `src/omnifocus_operator/service/domain.py`
- **Commit:** e3a647e6

**2. [Rule 1 - Bug] test_models.py STRCT-02 strictness tests used `{"success": True, ...}` as the required field**
- **Found during:** Task 3, first test run
- **Issue:** `test_add_task_result_accepts_unknown_field` and `test_edit_task_result_accepts_unknown_field` used `success=True` as the required field to test model permissiveness — they failed after `success` was removed.
- **Fix:** Updated both to use `status="success"` as the required field while keeping `bogus="x"` as the unknown-field probe.
- **Files modified:** `tests/test_models.py`
- **Commit:** 0ff8d153

## Known Stubs

None — this plan is a mechanical migration with no new user-facing behavior.

## Threat Flags

None — outbound-only models, no new attack surface (per plan threat model T-54-01).

## Self-Check: PASSED

- All 12 modified files exist on disk
- All 3 task commits verified: 3995fe19, e3a647e6, 0ff8d153
- 2122 tests pass, zero failures
