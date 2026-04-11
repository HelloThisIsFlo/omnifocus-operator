---
phase: 46-pipeline-query-paths
plan: 03
subsystem: service
tags: [pipeline, date-filtering, lifecycle-availability, resolve-dates, method-object]

# Dependency graph
requires:
  - phase: 45-date-models-resolution
    provides: "DateFilter model, resolve_date_filter(), DueSoonSetting enum"
  - plan: 46-01
    provides: "get_due_soon_setting() on Repository protocol"
  - plan: 46-02
    provides: "SQL and bridge date predicates for all 7 dimensions"
provides:
  - "_resolve_date_filters() pipeline step in _ListTasksPipeline"
  - "Lifecycle availability auto-include for completed/dropped date filters"
  - "End-to-end date filtering through service layer"
affects: [46-04, cross-path-equivalence, MCP-tool-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inline imports in async method to avoid linter stripping unused top-level imports with from __future__ import annotations"
    - "Lifecycle availability set-union merge: set(expanded) | set(additions) for duplicate-free merge"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/service/service.py
    - src/omnifocus_operator/service/resolve_dates.py
    - tests/test_list_pipelines.py

key-decisions:
  - "Inline imports inside _resolve_date_filters: StrEnum, get_week_start, DueSoonSetting, resolve_date_filter imported inside method body -- required because from __future__ import annotations makes top-level imports appear unused to linter"
  - "completed/dropped 'any' does NOT exclude non-lifecycle tasks: 'any' adds lifecycle availability but sets no date bounds, so existing availability (available/blocked) still applies -- result includes both available and completed/dropped tasks"

patterns-established:
  - "Date field iteration with lifecycle association: list of (field_name, query_value, lifecycle_avail) tuples processed in a single loop"

requirements-completed: [RESOLVE-11, EXEC-03, EXEC-04, EXEC-05, EXEC-06, EXEC-09]

# Metrics
duration: 8min
completed: 2026-04-08
---

# Phase 46 Plan 03: Pipeline Date Filter Integration Summary

**_resolve_date_filters() wires Phase 45 date resolver into _ListTasksPipeline with lifecycle auto-include and single-now capture, 11 integration tests verify all EXEC requirements**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-08T11:21:04Z
- **Completed:** 2026-04-08T11:29:45Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `_resolve_date_filters()` async method to `_ListTasksPipeline` with single `datetime.now(UTC)` capture
- Pipeline resolves all 7 date fields (due/defer/planned/completed/dropped/added/modified) to 14 _after/_before bounds
- Lifecycle availability auto-include: completed/dropped date filters add `Availability.COMPLETED`/`DROPPED` via set-union merge
- "any" shortcut bypass: adds lifecycle availability without date bounds (no resolver call)
- Conditional `get_due_soon_setting()` call: only when `due="soon"` detected
- 11 new integration tests covering RESOLVE-11, EXEC-03 through EXEC-09
- Full suite green: 1,853 tests, 97.78% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _resolve_date_filters() and update _build_repo_query()** - `ba5c84c`
2. **Task 2: Pipeline date filter integration tests** - `e732092`

## Files Created/Modified
- `src/omnifocus_operator/service/service.py` -- Added `_resolve_date_filters()` method, updated `execute()` call order, updated `_build_repo_query()` with lifecycle merge and 14 date bound fields
- `src/omnifocus_operator/service/resolve_dates.py` -- Fixed `_parse_absolute_after`/`_parse_absolute_before` to inherit tzinfo from `now` parameter (prevents naive/aware datetime mismatch)
- `tests/test_list_pipelines.py` -- Added `TestListTasksDateFilterPipeline` class with 11 tests

## Decisions Made
- Inline imports inside `_resolve_date_filters`: `from __future__ import annotations` makes all type annotations lazy, causing the linter to strip top-level imports that are only used in the new method. Inline imports with `# noqa: PLC0415` solve this cleanly
- `completed="any"` / `dropped="any"` adds lifecycle availability to the existing filter set but does NOT exclude non-lifecycle tasks. The "any" shortcut is purely additive -- it makes completed/dropped tasks visible alongside regular available/blocked tasks

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed timezone-naive datetime in absolute date parser**
- **Found during:** Task 2 (test `test_due_absolute_range_returns_tasks_in_range`)
- **Issue:** `_parse_absolute_after`/`_parse_absolute_before` in `resolve_dates.py` created naive `datetime(year, month, day)` for date-only input, but bridge path compares against Task model `AwareDatetime` fields (UTC), causing `TypeError: can't compare offset-naive and offset-aware datetimes`
- **Fix:** Added `tzinfo=now.tzinfo` to datetime construction in both functions, inheriting timezone from the caller-provided `now` parameter
- **Files modified:** `src/omnifocus_operator/service/resolve_dates.py`
- **Committed in:** `e732092` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in upstream resolver)
**Impact on plan:** Bug fix for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation.

## User Setup Required
None -- no external service configuration required.

## Next Phase Readiness
- Pipeline date filtering fully wired end-to-end for bridge path
- Ready for cross-path equivalence testing (Plan 04) to verify SQL and bridge paths match
- Ready for MCP tool wiring to expose date filters through list_tasks

## Self-Check: PASSED

All 3 modified files verified present. Both commit hashes verified in git log.

---
*Phase: 46-pipeline-query-paths*
*Completed: 2026-04-08*
