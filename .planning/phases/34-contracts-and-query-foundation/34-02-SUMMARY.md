---
phase: 34-contracts-and-query-foundation
plan: 02
subsystem: repository
tags: [sql, query-builder, parameterized-sql, sqlite, tdd]

requires:
  - phase: 34-contracts-and-query-foundation
    provides: ListTasksQuery, ListProjectsQuery validated query models with typed Availability enums

provides:
  - build_list_tasks_sql: pure function producing parameterized SQL for 8 task filter fields
  - build_list_projects_sql: pure function producing parameterized SQL for 4 project filter fields
  - SqlQuery NamedTuple (sql, params) for type-safe SQL transport
  - Availability compound OR clause builders matching hybrid.py mapper logic

affects: [35-sql-query-engine, 36-bridge-fallback, 37-service-list-orchestration]

tech-stack:
  added: []
  patterns: [pure-function SQL builder with conditions list + params list accumulation, availability clause lookup tables]

key-files:
  created:
    - src/omnifocus_operator/repository/query_builder.py
    - tests/test_query_builder.py
  modified: []

key-decisions:
  - "Availability clauses use static lookup dicts (no user params) -- column-only conditions avoid injection surface entirely"
  - "Tasks base SQL includes WHERE pi.task IS NULL (appends with AND); projects base has no WHERE (prepends WHERE) -- mirrors hybrid.py structure"
  - "No refactor needed -- two builders are under 50 lines each with clear structure; LIMIT/OFFSET duplication is 4 lines, not worth extracting"

patterns-established:
  - "SqlQuery NamedTuple: standard return type for all parameterized SQL in repository layer"
  - "Availability clause lookup tables: dict[Availability, str] mapping enum values to SQL fragments"
  - "Conditions accumulator pattern: list[str] conditions + list[Any] params built incrementally"

requirements-completed: [INFRA-01]

duration: 4min
completed: 2026-03-29
---

# Phase 34 Plan 02: Query Builder Summary

**Pure-function parameterized SQL builder for task (8 filters) and project (4 filters) queries with compound availability clauses, dynamic tag IN expansion, and LIKE search -- all via ? placeholders (INFRA-01)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-29T22:49:59Z
- **Completed:** 2026-03-29T22:54:00Z
- **Tasks:** 3 (TDD red-green-refactor)
- **Files modified:** 2

## Accomplishments

- Built `build_list_tasks_sql` handling 8 filter fields: in_inbox, flagged, project (subquery), tags (IN expansion), estimated_minutes_max, availability (compound OR), search (LIKE on name+note), limit/offset
- Built `build_list_projects_sql` handling 4 filter fields: availability (compound OR with effectiveStatus), folder (subquery), review_due_within (date comparison), flagged, limit/offset
- Both return `(data_query, count_query)` tuples -- count uses SELECT COUNT(*) without LIMIT/OFFSET
- 47 TDD tests covering every filter field in isolation, combinations, edge cases (limit=0, offset without limit), and parameterization safety

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for query builder** - `6cd0bfe` (test)
2. **Task 2 (GREEN): Implement query builder** - `57609e3` (feat)
3. **Task 3 (REFACTOR): No changes needed** - skipped (code already clean)

## Files Created/Modified

- `src/omnifocus_operator/repository/query_builder.py` - Pure functions producing parameterized SQL for task and project queries (250 lines)
- `tests/test_query_builder.py` - 47 TDD tests covering all filter fields, combinations, and edge cases (449 lines)

## Decisions Made

- Availability clauses use static lookup dicts mapping Availability enum values to SQL fragments -- no user params in availability conditions at all, eliminating injection surface
- Tasks base SQL already has `WHERE pi.task IS NULL` so filters append with `AND`; projects base has no WHERE so filters prepend `WHERE` -- mirrors hybrid.py's existing structure exactly
- No refactor phase needed -- both builder functions are under 50 lines, well-structured, and the 4-line LIMIT/OFFSET duplication doesn't justify a shared helper
- Tags filter uses `IN (?,?,?)` with dynamic placeholder expansion from `",".join("?" * len(tags))` -- safe because only `?` characters are interpolated
- f-strings used only for param values (`%search%` LIKE patterns) and `?` placeholder counts, never for user data in SQL strings

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Query builder functions ready for Phase 35 (SQL query engine) to call from HybridRepository
- SqlQuery NamedTuple provides clean interface for repository to execute with `cursor.execute(sq.sql, sq.params)`
- Availability clause logic precisely matches hybrid.py's `_map_task_availability` and `_map_project_availability` -- SQL conditions are the inverse of the Python mapper logic
- Full test suite green (1189 tests)

## Self-Check: PASSED

All files verified present on disk. All task commits verified in git log. No stubs found.

---
*Phase: 34-contracts-and-query-foundation*
*Completed: 2026-03-29*
