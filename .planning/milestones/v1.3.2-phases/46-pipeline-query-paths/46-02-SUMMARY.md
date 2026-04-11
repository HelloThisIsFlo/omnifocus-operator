---
phase: 46-pipeline-query-paths
plan: 02
subsystem: repository
tags: [sqlite, query-builder, bridge-only, date-filtering, cf-epoch]

# Dependency graph
requires:
  - phase: 45-date-models-resolution
    provides: "ListTasksRepoQuery with 14 _after/_before datetime fields"
provides:
  - "SQL date predicate generation for all 7 date dimensions"
  - "In-memory bridge date filtering with matching semantics"
  - "_DATE_COLUMN_MAP and _BRIDGE_FIELD_MAP constants"
affects: [46-03, 46-04, cross-path-equivalence]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mapping dict + loop pattern for date predicates (avoids 14 separate if-blocks)"
    - "CF epoch conversion via (datetime - _CF_EPOCH).total_seconds()"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/repository/hybrid/query_builder.py
    - src/omnifocus_operator/repository/bridge_only/bridge_only.py
    - tests/test_query_builder.py
    - tests/test_list_pipelines.py

key-decisions:
  - "Mapping dict + loop pattern for both SQL and bridge paths -- avoids 14 separate if-blocks per path"
  - ">= for after (inclusive), < for before (exclusive) -- mirrors RESOLVE-10 boundary semantics"

patterns-established:
  - "_DATE_COLUMN_MAP pattern: dict mapping query field prefix to SQL column name"
  - "_BRIDGE_FIELD_MAP pattern: dict mapping query field prefix to Task model attribute"

requirements-completed: [EXEC-01, EXEC-02, EXEC-07, EXEC-09]

# Metrics
duration: 5min
completed: 2026-04-08
---

# Phase 46 Plan 02: Query Paths Summary

**SQL and bridge date predicates for all 7 date dimensions using mapping dict + loop pattern with CF epoch conversion**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-08T11:11:53Z
- **Completed:** 2026-04-08T11:16:48Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- SQL query builder generates parameterized CF-epoch date predicates for all 7 dimensions (due, defer, planned, completed, dropped, added, modified)
- Bridge path filters in-memory with identical semantics (>= after, < before, NULL excluded)
- Date predicates compose with AND among themselves and with existing base filters
- 18 new tests (13 SQL + 5 bridge), full suite green at 1842 tests

## Task Commits

Each task was committed atomically (TDD: test then feat):

1. **Task 1: Add date predicates to build_list_tasks_sql()** - `2d82231` (test) + `3fa4f41` (feat)
2. **Task 2: Add date filtering to BridgeOnlyRepository.list_tasks()** - `5e2b47e` (test) + `e889428` (feat)

## Files Created/Modified
- `src/omnifocus_operator/repository/hybrid/query_builder.py` - Added `_DATE_COLUMN_MAP`, `_add_date_conditions()`, and call in `build_list_tasks_sql()`
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` - Added `_BRIDGE_FIELD_MAP` and date filtering loop in `list_tasks()`
- `tests/test_query_builder.py` - 13 new tests in `TestDatePredicates` class
- `tests/test_list_pipelines.py` - 5 new tests in `TestListTasksDateFiltering` class

## Decisions Made
- Used mapping dict + loop pattern for both paths -- clean, DRY, extensible
- `>=` for after (inclusive lower bound), `<` for before (exclusive upper bound) -- consistent with RESOLVE-10 which shifts date-only `before` values to start-of-next-day
- All SQL values use `?` placeholders (T-46-04 mitigation, no string interpolation)
- Column names come from static dict (T-46-05 accepted, no external input affects column names)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed backward compatibility test checking column names in availability clauses**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** `test_no_date_fields_no_date_predicates` asserted column names were absent from SQL, but availability clauses also reference `effectiveDateCompleted`/`effectiveDateHidden` with IS NULL checks
- **Fix:** Changed assertions to check for specific date predicate patterns (`t.{col} >= ?` and `t.{col} < ?`) rather than bare column names
- **Files modified:** tests/test_query_builder.py
- **Verification:** All 68 query builder tests pass
- **Committed in:** 3fa4f41 (part of Task 1 feat commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test)
**Impact on plan:** Test refinement for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SQL and bridge date predicates ready for service pipeline (Plan 03) to populate
- Both paths use identical semantics, ready for cross-path equivalence testing (Plan 04)

---
## Self-Check: PASSED

All 4 modified files confirmed on disk. All 4 task commit hashes verified in git log.

---
*Phase: 46-pipeline-query-paths*
*Completed: 2026-04-08*
