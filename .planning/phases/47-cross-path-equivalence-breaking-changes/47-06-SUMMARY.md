---
phase: 47-cross-path-equivalence-breaking-changes
plan: 06
subsystem: repository
tags: [sqlite, bridge, date-filter, lifecycle, cross-path-equivalence]

# Dependency graph
requires:
  - phase: 47-02
    provides: Cross-path equivalence test infrastructure with lifecycle task data
  - phase: 46
    provides: Date filtering SQL and bridge implementation
provides:
  - Additive lifecycle date filter semantics on both SQL and bridge paths
  - Cross-path equivalence tests for lifecycle date filter remaining task preservation
affects: [list-tasks, date-filtering, UAT-gaps]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_LIFECYCLE_DATE_FIELDS set pattern for field-specific filter semantics"
    - "IS NULL OR pattern for additive SQL predicates"
    - "is None or pattern for additive Python in-memory filtering"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/repository/hybrid/query_builder.py
    - src/omnifocus_operator/repository/bridge_only/bridge_only.py
    - tests/test_cross_path_equivalence.py
    - tests/test_list_pipelines.py

key-decisions:
  - "Lifecycle fields (completed, dropped) use additive IS NULL OR semantics; all other date fields remain restrictive"

patterns-established:
  - "_LIFECYCLE_DATE_FIELDS: module-level set distinguishing additive vs restrictive date filter semantics"

requirements-completed: [EXEC-10, EXEC-11]

# Metrics
duration: 4min
completed: 2026-04-09
---

# Phase 47 Plan 06: Lifecycle Date Filter Additive Fix Summary

**Fixed lifecycle date filters (completed/dropped) to additive IS NULL OR semantics, preserving remaining tasks alongside date-scoped lifecycle items on both SQL and bridge paths**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-09T13:58:03Z
- **Completed:** 2026-04-09T14:02:20Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 4

## Accomplishments
- SQL path uses `(column IS NULL OR column >= ?)` pattern for completed/dropped date predicates
- Bridge path uses `is None or` pattern for completed/dropped in-memory date filtering
- 2 new cross-path equivalence tests prove remaining tasks survive lifecycle date filters (6 items each: 5 remaining + 1 lifecycle)
- 3 existing tests updated from restrictive to additive assertions
- Full suite passes: 1915 tests, 97.8% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing lifecycle tests** - `c5d8447` (test)
2. **Task 1 GREEN: Fix lifecycle date filters + update existing tests** - `f913183` (feat)

## Files Created/Modified
- `src/omnifocus_operator/repository/hybrid/query_builder.py` - Added `_LIFECYCLE_DATE_FIELDS` set, split `_add_date_conditions` loop for IS NULL OR pattern on lifecycle fields
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` - Added `_LIFECYCLE_DATE_FIELDS` set, split date filter loop for `is None or` pattern on lifecycle fields
- `tests/test_cross_path_equivalence.py` - Added `test_completed_date_filter_preserves_remaining_lifecycle` and `test_dropped_date_filter_preserves_remaining_lifecycle`
- `tests/test_list_pipelines.py` - Updated 3 tests to match additive lifecycle filter semantics

## Decisions Made
- Lifecycle fields (completed, dropped) use additive semantics because these filters mean "also show lifecycle items in this date range" -- remaining tasks (NULL completion/drop dates) must pass through. All other date fields (due, defer, planned, added, modified) remain restrictive because NULL means "no value" and should be excluded from date range queries.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated 3 existing tests asserting old restrictive behavior**
- **Found during:** Task 1 GREEN (full suite run)
- **Issue:** `test_completed_after_in_range_excludes_null`, `test_multiple_date_filters_and_composition`, `test_completed_today_auto_includes_completed_availability`, and `test_dropped_last_1w_auto_includes_dropped_availability` in test_list_pipelines.py asserted that NULL lifecycle dates excluded tasks -- the exact bug being fixed
- **Fix:** Updated assertions to expect remaining tasks to be included (additive semantics)
- **Files modified:** tests/test_list_pipelines.py
- **Verification:** Full test suite passes (1915 tests)
- **Committed in:** f913183 (part of GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug -- tests encoding the buggy behavior)
**Impact on plan:** Essential fix. The existing tests were asserting the bug, not the correct behavior.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Lifecycle date filters now work correctly for UAT gaps 6 and 7
- Remaining plans (04, 05) address other UAT gaps independently

---
*Phase: 47-cross-path-equivalence-breaking-changes*
*Completed: 2026-04-09*
