---
phase: 47-cross-path-equivalence-breaking-changes
plan: 03
subsystem: repository
tags: [availability, filtering, sql, bridge, cross-path-equivalence]

# Dependency graph
requires:
  - phase: 47-01
    provides: cross-path date filter equivalence tests and SQL date predicates
  - phase: 47-02
    provides: bridge in-memory date filtering and service pipeline integration
provides:
  - "Fixed availability=[] semantics: empty list returns 0 items on both repo paths"
  - "Cross-path equivalence test for empty availability"
  - "Repo-level date filter tests use list(Availability) instead of []"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "availability=[] means 'match nothing' not 'skip filter' at repo layer"
    - "SQL impossible clause '1=0' for empty availability lists"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/repository/bridge_only/bridge_only.py
    - src/omnifocus_operator/repository/hybrid/query_builder.py
    - tests/test_cross_path_equivalence.py
    - tests/test_list_pipelines.py

key-decisions:
  - "Always apply availability filter in bridge path (remove truthiness guard) -- field is list[Availability], never None"
  - "Return '1=0' impossible clause in SQL for empty availability -- zero rows match"
  - "Replace availability=[] with list(Availability) in date tests -- expands to all 4 values"

patterns-established:
  - "Empty list filters match nothing: availability=[] at repo layer returns 0 results"

requirements-completed: [EXEC-10]

# Metrics
duration: 3min
completed: 2026-04-09
---

# Phase 47 Plan 03: Fix availability=[] Semantics Summary

**Fixed availability=[] to return zero items on both bridge and SQL paths, closing UAT gap 2 where empty list bypassed the filter returning all remaining tasks**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-09T12:24:02Z
- **Completed:** 2026-04-09T12:27:29Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Fixed bridge path: removed truthiness guard `if query.availability:` for both task and project listing -- always apply the availability filter
- Fixed SQL path: `_build_availability_clause` returns `"1=0"` for empty list instead of `""` -- impossible WHERE clause matches zero rows
- Added 2 cross-path equivalence tests proving availability=[] returns 0 items on both paths
- Updated 5 repo-level date filter tests from `availability=[]` to `list(Availability)` to express "include all states"

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix both repo paths and add cross-path empty-availability test** (TDD)
   - `f8769ad` (test: failing tests for empty availability)
   - `5d74b65` (feat: fix availability=[] on both repo paths)
2. **Task 2: Update repo-level date filter tests** - `dea33c7` (fix)

_TDD Task 1 had RED and GREEN commits._

## Files Created/Modified
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` - Remove truthiness guard on availability filter for tasks and projects
- `src/omnifocus_operator/repository/hybrid/query_builder.py` - Return '1=0' for empty availability list in SQL builder
- `tests/test_cross_path_equivalence.py` - Add TestEmptyAvailabilityCrossPath with 2 tests (x2 paths = 4)
- `tests/test_list_pipelines.py` - Replace availability=[] with list(Availability) in 5 date filter tests, add Availability import

## Decisions Made
- Always apply availability filter in bridge path -- `list[Availability]` is never None, so truthiness guard is wrong for empty lists
- SQL '1=0' impossible clause is the standard pattern for "match nothing" in parameterized queries
- `list(Availability)` is the correct way to express "all availability states" since StrEnum iteration returns all members

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Formatter removed Availability import on first edit (before usage existed in file) -- re-added after subsequent edits

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All availability=[] semantics fixed and tested across both repo paths
- Full suite green (1911 tests)
- Service-level test `test_completed_all_with_empty_availability_only_completed` passes unchanged (service layer expands [] via lifecycle additions)

---
*Phase: 47-cross-path-equivalence-breaking-changes*
*Completed: 2026-04-09*
