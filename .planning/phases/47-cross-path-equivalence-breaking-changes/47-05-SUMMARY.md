---
phase: 47-cross-path-equivalence-breaking-changes
plan: 05
subsystem: contracts
tags: [pydantic, strenum, date-filtering, type-coercion]

# Dependency graph
requires:
  - phase: 45-date-models-resolution
    provides: DateFilter model, StrEnum shortcuts, resolve_date_filter
provides:
  - DateFieldShortcut(StrEnum) for non-due date fields (defer, planned, added, modified)
  - Pydantic coercion of raw "today" string to DateFieldShortcut.TODAY on 4 fields
affects: [47-cross-path-equivalence-breaking-changes]

# Tech tracking
tech-stack:
  added: []
  patterns: [StrEnum shortcut pattern extended to general date fields]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/use_cases/list/_enums.py
    - src/omnifocus_operator/contracts/use_cases/list/tasks.py
    - src/omnifocus_operator/contracts/use_cases/list/__init__.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - tests/test_date_filter_contracts.py
    - tests/test_resolve_dates.py

key-decisions:
  - "DateFieldShortcut as separate StrEnum (not merged into DueDateShortcut) -- only 'today' applies to general date fields, not 'overdue'/'soon'"

patterns-established:
  - "StrEnum shortcut for each date field category: DueDateShortcut (due), LifecycleDateShortcut (completed/dropped), DateFieldShortcut (defer/planned/added/modified)"

requirements-completed: [EXEC-10]

# Metrics
duration: 4min
completed: 2026-04-09
---

# Phase 47 Plan 05: DateFieldShortcut enum fixing "today" shortcut crash on non-due fields

**DateFieldShortcut(StrEnum) replaces Literal["today"] on defer/planned/added/modified -- Pydantic coerces raw string to enum, resolve_date_filter StrEnum path handles it**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-09T13:58:03Z
- **Completed:** 2026-04-09T14:02:54Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created DateFieldShortcut(StrEnum) with TODAY="today" in _enums.py
- Replaced Literal["today"] with DateFieldShortcut on 4 contract fields (defer, planned, added, modified)
- Pydantic now coerces raw "today" string to DateFieldShortcut.TODAY, which isinstance(value, StrEnum) catches in resolve_date_filter
- Added explicit resolve_date_filter test proving DateFieldShortcut.TODAY resolves to today's midnight bounds
- Full suite passes: 1916 tests, 97.80% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Create DateFieldShortcut enum and update contract annotations** - `52c29dd` (test) + `fe46c0c` (feat)
2. **Task 2: Add resolve_date_filter test for DateFieldShortcut** - `145b078` (test)

_Note: Task 1 used TDD with separate RED and GREEN commits_

## Files Created/Modified
- `src/omnifocus_operator/contracts/use_cases/list/_enums.py` - Added DateFieldShortcut(StrEnum) with TODAY="today"
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` - Changed 4 fields from Literal["today"] to DateFieldShortcut
- `src/omnifocus_operator/contracts/use_cases/list/__init__.py` - Export DateFieldShortcut
- `src/omnifocus_operator/agent_messages/descriptions.py` - Added DATE_FIELD_SHORTCUT_DOC constant
- `tests/test_date_filter_contracts.py` - Updated 4 tests to assert isinstance(DateFieldShortcut), added 4 DateFilter object tests
- `tests/test_resolve_dates.py` - Added test_date_field_shortcut_today proving StrEnum resolution path

## Decisions Made
- DateFieldShortcut is a separate StrEnum (not merged into DueDateShortcut) because only "today" applies to general date fields -- "overdue" and "soon" are due-specific semantics

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The "today" shortcut now works on all 7 date filter fields without errors
- UAT gaps 13/14 ("'str' object has no attribute 'this'") are closed
- resolve_date_filter handles DateFieldShortcut via existing isinstance(value, StrEnum) gate

## Self-Check: PASSED

All 6 modified files verified present. All 3 task commits verified in git log. SUMMARY.md exists.

---
*Phase: 47-cross-path-equivalence-breaking-changes*
*Completed: 2026-04-09*
