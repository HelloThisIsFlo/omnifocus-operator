---
phase: 45-date-models-resolution
plan: 02
subsystem: contracts
tags: [date-filtering, query-models, config]
dependency_graph:
  requires: [45-01]
  provides: [ListTasksQuery-date-fields, ListTasksRepoQuery-datetime-fields, OPERATOR_WEEK_START]
  affects: [service-resolution, sql-query-builder, bridge-filter]
tech_stack:
  added: []
  patterns: [union-discrimination, Literal-type-shortcuts, env-var-config]
key_files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/use_cases/list/tasks.py
    - src/omnifocus_operator/config.py
    - tests/test_date_filter_contracts.py
    - tests/test_list_contracts.py
decisions:
  - Union ordering (StrEnum/Literal before DateFilter) ensures Pydantic tries string match first
  - get_week_start() uses inline os import to avoid module-level side effect
  - Date fields placed after search and before limit/offset in ListTasksQuery
metrics:
  duration: 289s
  completed: "2026-04-07T22:30:28Z"
  tasks: 1
  files_modified: 4
---

# Phase 45 Plan 02: Date Filter Query Fields Summary

Extended ListTasksQuery with 7 date filter fields using per-field shortcut unions, ListTasksRepoQuery with 14 resolved datetime bounds, and OPERATOR_WEEK_START env var config.

## Completed Tasks

| # | Name | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | OPERATOR_WEEK_START config and ListTasksQuery/RepoQuery date field extensions | 1ea4666 (test), 1e20e12 (feat) | 7 date fields on ListTasksQuery, 14 datetime fields on ListTasksRepoQuery, get_week_start() config |

## Key Implementation Details

- **ListTasksQuery date fields**: `due` (DueDateShortcut | DateFilter), `defer`/`planned`/`added`/`modified` (Literal["today"] | DateFilter), `completed`/`dropped` (LifecycleDateShortcut | DateFilter)
- **Union ordering**: StrEnum/Literal always left of DateFilter -- Pydantic v2 tries left-to-right, so string shortcuts resolve before dict-based DateFilter
- **Null rejection**: All 7 date field names added to `_PATCH_FIELDS` for the existing `reject_null_filters` model validator
- **ListTasksRepoQuery**: 14 flat `datetime | None` fields (`due_after`, `due_before`, etc.) -- service layer will resolve shortcuts/DateFilter to these
- **OPERATOR_WEEK_START**: Reads env var with monday default, validates against whitelist (monday/sunday), returns Python weekday int

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated field parity test in test_list_contracts.py**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** `TestRepoQueryFieldParity::test_tasks_shared_fields_match` expected identical field sets between ListTasksQuery and ListTasksRepoQuery. Date fields intentionally diverge (7 query fields -> 14 repo fields).
- **Fix:** Added date field exclusion sets to the parity test assertion.
- **Files modified:** tests/test_list_contracts.py
- **Commit:** 1e20e12

## Verification

- `uv run pytest tests/test_date_filter_contracts.py -x -q` -- 64 passed
- `uv run pytest -x -q` -- 1763 passed, 98% coverage
- `uv run pytest tests/test_output_schema.py -x -q` -- 32 passed
- Union discrimination verified: `ListTasksQuery(due="overdue")` -> DueDateShortcut, `ListTasksQuery(due={"this":"w"})` -> DateFilter

## Self-Check: PASSED
