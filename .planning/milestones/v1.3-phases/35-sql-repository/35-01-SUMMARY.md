---
phase: 35-sql-repository
plan: 01
subsystem: database
tags: [sqlite, sql, filtering, pagination, repository]

requires:
  - phase: 34-contracts-and-query-foundation
    provides: "ListTasksQuery, ListProjectsQuery, ListResult, build_list_tasks_sql, build_list_projects_sql"
provides:
  - "HybridRepository.list_tasks() -- filtered, paginated task queries from SQLite"
  - "HybridRepository.list_projects() -- filtered, paginated project queries from SQLite"
  - "4 shared lookup helpers extracted from _read_all for reuse"
affects: [35-02-plan, service-layer, mcp-tools]

tech-stack:
  added: []
  patterns:
    - "Shared lookup builder functions (_build_tag_name_lookup, _build_task_tag_map, _build_project_info_lookup, _build_task_name_lookup)"
    - "List methods follow async-wraps-sync pattern with fresh read-only connections"
    - "Query builder integration: build_list_*_sql returns (data_q, count_q) SqlQuery pairs"

key-files:
  created: []
  modified:
    - "src/omnifocus_operator/repository/hybrid.py"
    - "tests/test_hybrid_repository.py"
    - "src/omnifocus_operator/repository/query_builder.py"

key-decisions:
  - "Extracted 4 lookup helpers as module-level functions (not class methods) for reuse by both _read_all and list methods"
  - "list_projects builds only tag lookups (not project_info/task_name) since _map_project_row takes 2 params"

patterns-established:
  - "List method pattern: _list_*_sync builds lookups + executes query builder SQL + maps rows + computes pagination"
  - "Lookup extraction: shared lookup builders avoid code duplication between _read_all and list methods"

requirements-completed: [TASK-01, TASK-02, TASK-03, TASK-04, TASK-06, TASK-07, TASK-08, TASK-09, TASK-10, TASK-11, PROJ-01, PROJ-02, PROJ-03, PROJ-04, PROJ-05, PROJ-06, PROJ-07, INFRA-02]

duration: 6min
completed: 2026-03-30
---

# Phase 35 Plan 01: SQL Repository list_tasks/list_projects Summary

**Filtered SQL list methods on HybridRepository with 22 new tests covering all task/project filters, pagination, and performance comparison**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-29T23:55:20Z
- **Completed:** 2026-03-30T00:01:33Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `list_tasks` on HybridRepository with 10 filter parameters, pagination, and ListResult construction
- `list_projects` on HybridRepository with 4 filter parameters, pagination, and ListResult construction
- 4 shared lookup helpers extracted from `_read_all`, eliminating code duplication
- 22 new tests covering every filter, pagination edge case, and filtered-vs-full performance comparison
- Full suite: 1216 tests, 98.17% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract shared lookup helpers and implement list_tasks + list_projects** - TDD
   - `55e98c6` (test: RED -- failing tests for list_tasks/list_projects)
   - `a046bb5` (feat: GREEN -- implementation with extracted helpers)

2. **Task 2: Comprehensive tests for all filters, pagination, and performance** - `e1a5399` (test)

## Files Created/Modified
- `src/omnifocus_operator/repository/hybrid.py` -- Added 4 shared lookup helpers, list_tasks, list_projects, refactored _read_all
- `tests/test_hybrid_repository.py` -- Added TestListTasks (15 tests), TestListProjects (6 tests), TestListPerformance (1 test)
- `src/omnifocus_operator/repository/query_builder.py` -- Fixed project subquery (pi2.pk not pi2.task)

## Decisions Made
- Extracted lookup builders as module-level functions (not class methods) since they take a connection parameter and have no class state dependency
- list_projects only builds tag lookups (not project_info_lookup or task_name_lookup) because `_map_project_row` takes only 2 params (row, tag_lookup)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed query_builder project subquery column reference**
- **Found during:** Task 2 (writing project filter integration test)
- **Issue:** `build_list_tasks_sql` project subquery used `SELECT pi2.task` but `t.containingProjectInfo` references the ProjectInfo PK, not the task identifier. The join `t.containingProjectInfo IN (SELECT pi2.task ...)` would never match because PK values (e.g., "pi-proj-001") differ from task IDs (e.g., "proj-001").
- **Fix:** Changed `SELECT pi2.task` to `SELECT pi2.pk` in the project filter subquery
- **Files modified:** `src/omnifocus_operator/repository/query_builder.py`
- **Verification:** `test_list_tasks_project_filter` passes with real SQLite execution
- **Committed in:** `e1a5399` (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking -- query correctness)
**Impact on plan:** Essential fix for project filter to work at all. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- list_tasks and list_projects ready for Plan 02 (list_tags, list_folders, list_perspectives, count methods)
- Shared lookup helpers available for reuse in Plan 02's simpler list methods
- Query builder integration pattern established for future list operations

## Self-Check: PASSED

- All 3 modified files exist on disk
- All 3 task commits verified in git log
- SUMMARY.md created

---
*Phase: 35-sql-repository*
*Completed: 2026-03-30*
