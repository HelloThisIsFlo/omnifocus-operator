---
phase: 51-task-ordering
plan: 02
subsystem: repository
tags: [sqlite, cte, recursive-query, ordering, hybrid-repository]

# Dependency graph
requires:
  - "51-01: Task model order field, bridge adapter, cross-path exclusion"
provides:
  - "Recursive CTE (_TASK_ORDER_CTE) producing sort_path for outline ordering"
  - "_TASKS_DATA_BASE constant with CTE-joined data query"
  - "_compute_dotted_orders() for Python-side sequential ordinal computation"
  - "_build_full_dotted_orders() for full-DB order lookup (sparse ordinals in filtered results)"
  - "list_tasks returns tasks in outline order with dotted order field"
  - "get_all returns tasks in outline order with dotted order field"
  - "get_task returns correct dotted order via scoped CTE"
  - "Inbox tasks sort before projects via 0000000000/ prefix"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Recursive CTE with three anchors (project roots, inbox roots, recursive children) for outline ordering"
    - "Python-side dotted ordinal computation from CTE-sorted results (avoids ROW_NUMBER() in recursive CTE)"
    - "Full unfiltered CTE for order lookup, filtered query for results (preserves sparse ordinals)"
    - "ID tiebreaker in ORDER BY for deterministic pagination with equal ranks"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/repository/hybrid/query_builder.py
    - src/omnifocus_operator/repository/hybrid/hybrid.py
    - tests/test_hybrid_repository.py
    - tests/test_query_builder.py
    - tests/test_cross_path_equivalence.py

key-decisions:
  - "Compute dotted orders from full unfiltered CTE (not filtered result set) to preserve sparse ordinals when filters remove siblings"
  - "Add t.persistentIdentifier tiebreaker to ORDER BY o.sort_path for deterministic pagination when tasks share same rank"
  - "Use _build_full_dotted_orders helper for list_tasks (runs full CTE separately), inline CTE for _read_all (already has all rows)"

patterns-established:
  - "CTE ordering: three-anchor recursive CTE for task outline order, reused across all read paths"
  - "Dotted order: Python-side computation from sorted rows avoids SQLite ROW_NUMBER() limitation in recursive CTEs"

requirements-completed: [ORDER-02, ORDER-04, ORDER-05]

# Metrics
duration: 12min
completed: 2026-04-12
---

# Phase 51 Plan 02: CTE Outline Ordering Summary

**Recursive CTE with three-anchor sort_path produces exact OmniFocus outline order; Python computes dotted ordinals (1.2.3) for all read paths**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-12T13:09:26Z
- **Completed:** 2026-04-12T13:21:18Z
- **Tasks:** 1
- **Files modified:** 5

## Accomplishments
- Recursive CTE (`_TASK_ORDER_CTE`) with project-root, inbox-root, and recursive-child anchors produces correct outline ordering
- Python-side `_compute_dotted_orders()` generates sequential 1-based ordinals with dotted notation (1, 1.1, 1.2, 2)
- All three read paths wired: `list_tasks` (via `_build_full_dotted_orders`), `get_all` (inline CTE), `get_task` (scoped `_compute_task_order`)
- Inbox tasks sort before all project tasks via `0000000000/` sort_path prefix
- Filtered results preserve original ordinals (sparse values like 1, 3 when sibling 2 is filtered out)
- Full test suite: 2029 passed, 98% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Add recursive CTE to query_builder and integrate outline ordering in list_tasks** - `576113d9` (feat)

## Files Created/Modified
- `src/omnifocus_operator/repository/hybrid/query_builder.py` - Added `_TASK_ORDER_CTE`, `_TASKS_DATA_BASE`, changed ORDER BY to `o.sort_path, t.persistentIdentifier`
- `src/omnifocus_operator/repository/hybrid/hybrid.py` - Added `_compute_dotted_orders()`, `_build_full_dotted_orders()`, `_compute_task_order()`, modified `_map_task_row()` with order param, wired into `_read_all`, `_read_task`, `_list_tasks_sync`
- `tests/test_hybrid_repository.py` - Added `rank` column to test DB schema, 9 ordering tests in `TestTaskOrdering` class
- `tests/test_query_builder.py` - Updated ORDER BY assertions from `t.persistentIdentifier` to `o.sort_path, t.persistentIdentifier`
- `tests/test_cross_path_equivalence.py` - Added `rank` column to test DB schema

## Decisions Made
- **Full CTE for order lookup**: `_list_tasks_sync` runs the full unfiltered CTE via `_build_full_dotted_orders()` to compute orders, then applies the filtered query for results. This preserves sparse ordinals (1, 3) when filters remove middle siblings. Cost: one extra CTE query (~5ms) per list_tasks call.
- **ID tiebreaker**: Added `t.persistentIdentifier` as secondary sort key after `o.sort_path` to ensure deterministic pagination when tasks share the same rank (e.g., all rank=0 inbox tasks).
- **Scoped CTE for get_task**: `_compute_task_order` scopes the CTE to the task's project or inbox namespace, then looks up the single task's order. Avoids running the full DB CTE for single-entity reads.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Sparse ordinals in filtered results**
- **Found during:** Task 1 (GREEN phase, test_filtered_results_preserve_outline_order)
- **Issue:** Initial implementation computed dotted orders from filtered result set, producing sequential (1, 2) instead of sparse (1, 3) when a middle sibling was filtered out
- **Fix:** Added `_build_full_dotted_orders()` helper that computes orders from the full unfiltered CTE, used as lookup when mapping filtered rows
- **Files modified:** `src/omnifocus_operator/repository/hybrid/hybrid.py`
- **Verification:** test_filtered_results_preserve_outline_order passes with expected sparse values
- **Committed in:** `576113d9`

**2. [Rule 3 - Blocking] Deterministic pagination tiebreaker**
- **Found during:** Task 1 (GREEN phase, existing test_list_tasks_paginated_sorted_by_id)
- **Issue:** Inbox tasks with same rank=0 had undefined order with `ORDER BY o.sort_path` alone, breaking existing deterministic ordering test
- **Fix:** Added `t.persistentIdentifier` tiebreaker to all ORDER BY clauses (query_builder, _read_all, _build_full_dotted_orders, _compute_task_order)
- **Files modified:** `query_builder.py`, `hybrid.py`
- **Verification:** test_list_tasks_paginated_sorted_by_id passes, 2029 tests green
- **Committed in:** `576113d9`

**3. [Rule 3 - Blocking] Updated ORDER BY assertions in query builder tests**
- **Found during:** Task 1 (GREEN phase, test_order_by_before_limit)
- **Issue:** Two tests in test_query_builder.py asserted `ORDER BY t.persistentIdentifier` which no longer matches
- **Fix:** Updated assertions to `ORDER BY o.sort_path, t.persistentIdentifier`
- **Files modified:** `tests/test_query_builder.py`
- **Verification:** Both tests pass
- **Committed in:** `576113d9`

**4. [Rule 3 - Blocking] Added rank column to test DB schemas**
- **Found during:** Task 1 (prerequisite for CTE to function)
- **Issue:** Test database schemas lacked `rank` column needed by the CTE's `printf('%010d', t.rank + 2147483648)`
- **Fix:** Added `rank INTEGER DEFAULT 0` to Task CREATE TABLE in both test_hybrid_repository.py and test_cross_path_equivalence.py
- **Files modified:** `tests/test_hybrid_repository.py`, `tests/test_cross_path_equivalence.py`
- **Verification:** CTE executes without error, all tests pass
- **Committed in:** `576113d9`

---

**Total deviations:** 4 auto-fixed (1 bug, 3 blocking)
**Impact on plan:** All fixes necessary for correctness and test compatibility. No scope creep.

## Issues Encountered
None.

## Known Stubs
None -- all read paths produce real dotted order values from the CTE.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 51 complete: all ORDER requirements (ORDER-01 through ORDER-05) implemented
- Task model has `order` field populated by HybridRepository, `None` for BridgeOnlyRepository
- All 2029 tests pass, 98% coverage, strict mypy clean

## Self-Check: PASSED

- All 5 modified files exist on disk
- Commit 576113d9 found in git log
- Full test suite: 2029 passed

---
*Phase: 51-task-ordering*
*Completed: 2026-04-12*
