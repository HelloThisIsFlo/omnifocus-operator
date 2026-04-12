---
phase: 51-task-ordering
plan: 01
subsystem: models
tags: [pydantic, task-model, bridge-adapter, agent-descriptions]

# Dependency graph
requires: []
provides:
  - "Task model with order: str | None field (dotted notation)"
  - "ORDER_FIELD description constant in agent_messages/descriptions.py"
  - "Bridge adapter sets order=None for degraded mode (D-03)"
  - "Cross-path equivalence tests exclude order from comparison (D-05)"
  - "All three tool descriptions mention order field (D-04)"
affects: [51-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "order field uses Field(default=None) for optional read-only fields populated by specific repo paths"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/models/task.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - src/omnifocus_operator/repository/bridge_only/adapter.py
    - tests/conftest.py
    - tests/test_cross_path_equivalence.py
    - tests/test_models.py

key-decisions:
  - "Moved order=None inside _adapt_task() instead of adapt_snapshot() loop to preserve adapter idempotency"

patterns-established:
  - "Read-only repo-specific fields use Field(default=None) on core model, set by adapter for degraded paths"

requirements-completed: [ORDER-01, ORDER-03]

# Metrics
duration: 6min
completed: 2026-04-12
---

# Phase 51 Plan 01: Task Model Order Field Summary

**Added order: str | None field to Task model with dotted notation description, bridge degraded-mode handling, and cross-path test exclusion**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-12T12:59:16Z
- **Completed:** 2026-04-12T13:05:51Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Task model has `order: str | None` field with agent-facing description constant
- All three tool descriptions (get_task, list_tasks, get_all) updated per D-04
- Bridge adapter sets `order=None` on all adapted tasks (D-03 degraded mode)
- Cross-path equivalence tests exclude `order` from comparison (D-05)
- Full test suite (2020 tests) passes

## Task Commits

Each task was committed atomically:

1. **Task 1: Add order field to Task model and bridge adapter** - `fda05692` (feat)
2. **Task 2: Update test factories and cross-path equivalence** - `7b683749` (feat)

## Files Created/Modified
- `src/omnifocus_operator/models/task.py` - Added `order: str | None` field with ORDER_FIELD description
- `src/omnifocus_operator/agent_messages/descriptions.py` - Added ORDER_FIELD constant, updated GET_TASK_TOOL_DOC, LIST_TASKS_TOOL_DOC, GET_ALL_TOOL_DOC
- `src/omnifocus_operator/repository/bridge_only/adapter.py` - Added `raw["order"] = None` inside `_adapt_task()` for bridge degradation
- `tests/conftest.py` - Added `"order": None` to `make_model_task_dict()` defaults
- `tests/test_cross_path_equivalence.py` - Updated `assert_equivalent()` to use `model_dump(exclude={"order"})` with `strict=True` zip
- `tests/test_models.py` - Updated Task model field count assertions from 26 to 27

## Decisions Made
- Moved `order=None` assignment inside `_adapt_task()` (after status mapping) rather than in `adapt_snapshot()` loop -- preserves adapter idempotency (already-adapted tasks without status key are untouched)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed adapter idempotency violation**
- **Found during:** Task 2 (full test suite run)
- **Issue:** Plan specified adding `task["order"] = None` in the `adapt_snapshot()` task loop after `_adapt_task(task)`. This unconditionally modifies already-adapted tasks (no `status` key), breaking the idempotency contract tested by `test_task_without_status_key_is_noop`.
- **Fix:** Moved `raw["order"] = None` inside `_adapt_task()` after `_adapt_parent_ref(raw)`, so it only runs during actual adaptation (when `status` key is present).
- **Files modified:** `src/omnifocus_operator/repository/bridge_only/adapter.py`
- **Verification:** `test_adapter.py::TestAdapterIdempotency::test_task_without_status_key_is_noop` passes
- **Committed in:** `7b683749` (Task 2 commit)

**2. [Rule 3 - Blocking] Updated Task model field count assertions**
- **Found during:** Task 2 (full test suite run)
- **Issue:** Two tests in `test_models.py` assert exact field counts on the Task model and `make_model_task_dict()`. Adding `order` field increased count from 26 to 27.
- **Fix:** Updated both assertions from 26 to 27 with updated docstrings.
- **Files modified:** `tests/test_models.py`
- **Verification:** Both field count tests pass
- **Committed in:** `7b683749` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None.

## Known Stubs
None -- `order` field defaults to `None` which is the correct degraded-mode value. Plan 02 will wire the CTE to populate actual dotted-path values.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Task model ready for Plan 02 to populate `order` from CTE in HybridRepository
- Bridge path correctly returns `None` -- no further changes needed there
- Cross-path tests ready -- `order` excluded from comparison so HybridRepository can return dotted paths while BridgeOnly returns None

## Self-Check: PASSED

- All 6 modified files exist on disk
- Commit fda05692 found in git log
- Commit 7b683749 found in git log
- Full test suite: 2020 passed

---
*Phase: 51-task-ordering*
*Completed: 2026-04-12*
