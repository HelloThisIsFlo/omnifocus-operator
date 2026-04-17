---
phase: 54-batch-processing
plan: "02"
subsystem: server-handlers
tags: [batch-processing, handlers, descriptions, best-effort, fail-fast]
dependency_graph:
  requires: [54-01]
  provides: [batch-handler-loops, batch-tool-descriptions]
  affects: [server/handlers.py, agent_messages/descriptions.py, agent_messages/errors.py]
tech_stack:
  added: []
  patterns: [best-effort-batch, fail-fast-batch, parameterized-description-fragments]
key_files:
  created: []
  modified:
    - src/omnifocus_operator/server/handlers.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - src/omnifocus_operator/agent_messages/errors.py
    - tests/test_server.py
decisions:
  - "[54-02-01] _MAX_BATCH_SIZE=50 mirrored in descriptions.py to avoid circular import (descriptions <- config <- models.enums <- models.common <- descriptions)"
  - "[54-02-02] Dead ADD_TASKS_BATCH_LIMIT/EDIT_TASKS_BATCH_LIMIT constants removed from errors.py — Pydantic max_length now enforces the limit, and AST enforcement test would fail with unreferenced constants"
  - "[54-02-03] Service-layer errors in add_tasks/edit_tasks return per-item status=error, not ToolError — tests updated to assert on result array, not ToolError"
metrics:
  duration_seconds: 300
  completed_date: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 4
requirements-completed: [BATCH-09]
---

# Phase 54 Plan 02: Batch Handler Loops and Updated Descriptions Summary

Rewrote add_tasks and edit_tasks handlers with best-effort and fail-fast batch loops using Pydantic max_length enforcement, and updated tool descriptions with parameterized batch semantic fragments.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rewrite add_tasks and edit_tasks handlers with batch loops | 58ba21c7 | handlers.py, errors.py |
| 2 | Update tool descriptions with batch semantics and fragments | 31ab1342 | descriptions.py, errors.py, test_server.py |

## What Was Built

### handlers.py — Batch Loops

**add_tasks (best-effort):**
- `Annotated[list[AddTaskCommand], Field(min_length=1, max_length=MAX_BATCH_SIZE)]` parameter
- try/except per item catches `ToolError` and `ValueError`
- Errors produce `AddTaskResult(status="error", error=f"Task {i+1}: {e}")`
- All items always processed; progress reported per-item

**edit_tasks (fail-fast):**
- `Annotated[list[EditTaskCommand], Field(min_length=1, max_length=MAX_BATCH_SIZE)]` parameter
- `failed_idx: int | None` tracks first failure
- Items after failure get `EditTaskResult(status="skipped", id=command.id, warnings=[f"Skipped: task {failed_idx + 1} failed"])`
- Only `ToolError` and `ValueError` caught — unexpected exceptions propagate (systemic failure)

### descriptions.py — Batch Fragments

Four new shared fragments:
- `_BATCH_RETURNS` — per-item result shape (status/id/name/error/warnings)
- `_BATCH_LIMIT_NOTE` — "Up to 50 items per call."
- `_BATCH_CROSS_ITEM_NOTE` — cross-item reference limitation (use sequential calls for hierarchies)
- `_BATCH_CONCURRENCY_NOTE` — concurrent calls not serialized caveat

`_WRITE_RETURNS` aliased to `_BATCH_RETURNS` for backward compatibility with any internal references.

Both `ADD_TASKS_TOOL_DOC` and `EDIT_TASKS_TOOL_DOC` updated:
- Removed "Limited to 1 item" / "Max 1 item per call" language
- Added failure mode explanation (Best-effort vs Fail-fast)
- Cross-item and concurrency notes appended

### errors.py — Dead Code Removal

`ADD_TASKS_BATCH_LIMIT` and `EDIT_TASKS_BATCH_LIMIT` constants removed. The limit is now enforced at schema level by Pydantic's `max_length` constraint. The AST enforcement test (`test_all_error_constants_referenced_in_consumers`) would flag them as unreferenced dead code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Circular import: descriptions.py cannot import from config.py**
- **Found during:** Task 2 verification
- **Issue:** `descriptions.py` importing `MAX_BATCH_SIZE` from `config.py` created a circular import chain: `descriptions → config → models.enums → models.__init__ → models.common → descriptions`
- **Fix:** Defined `_MAX_BATCH_SIZE = 50` directly in `descriptions.py` with a comment noting it mirrors `config.MAX_BATCH_SIZE`. If the config value changes, this must be updated too.
- **Files modified:** `src/omnifocus_operator/agent_messages/descriptions.py`
- **Commit:** 31ab1342

**2. [Rule 1 - Bug] Dead error constants fail AST enforcement test**
- **Found during:** Task 2 test run
- **Issue:** Removing the `ADD_TASKS_BATCH_LIMIT`/`EDIT_TASKS_BATCH_LIMIT` imports from handlers.py made these constants unreferenced, triggering `test_all_error_constants_referenced_in_consumers`
- **Fix:** Removed the constants from errors.py entirely — they're dead code now that Pydantic enforces the limit
- **Files modified:** `src/omnifocus_operator/agent_messages/errors.py`
- **Commit:** 31ab1342

**3. [Rule 1 - Bug] Existing tests expected ToolError for service-layer failures**
- **Found during:** Task 2 test run (3 cascading failures)
- **Issue:** Tests for invalid parent, invalid tag, and not-found task used `pytest.raises(ToolError)`. With best-effort/fail-fast semantics, service-layer failures now produce per-item `status="error"` results, not ToolErrors.
- **Fix:** Updated 4 tests in `test_server.py`:
  - `test_add_tasks_single_item_constraint` → `test_add_tasks_two_items_best_effort` (verifies 2 items succeed)
  - `test_add_tasks_invalid_parent` → checks `items[0]["status"] == "error"` and error message
  - `test_add_tasks_invalid_tag` → checks `items[0]["status"] == "error"` and error message
  - `test_edit_tasks_rejects_multi_item_array` → removed (multi-item now accepted)
  - `test_edit_tasks_not_found` → checks `items[0]["status"] == "error"` and error message
- **Files modified:** `tests/test_server.py`
- **Commit:** 31ab1342

Note: Schema validation errors (missing name, empty array, unknown fields) still raise ToolError — this is correct because they represent malformed input caught at the Pydantic level, not per-item service failures.

## Known Stubs

None — all batch behavior is fully wired through service layer.

## Threat Flags

All threat mitigations from the plan's threat model are implemented:
- **T-54-03 (DoS):** `max_length=50` on Pydantic parameter enforces hard upper bound
- **T-54-04 (Info Disclosure):** Only `str(e)` from ToolError/ValueError in error messages; no stack traces; unexpected exceptions re-raise without catch-all

## Self-Check: PASSED

- handlers.py: FOUND
- descriptions.py: FOUND
- errors.py: FOUND
- 54-02-SUMMARY.md: FOUND
- Commit 58ba21c7 (Task 1): FOUND
- Commit 31ab1342 (Task 2): FOUND
- All 2121 tests pass, 97% coverage
