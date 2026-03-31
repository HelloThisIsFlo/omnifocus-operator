---
phase: 36-service-orchestration-cross-path-equivalence-merged-from-old-phases-36-37
plan: 01
subsystem: api
tags: [pydantic, validation, datetime, cf-epoch, educational-errors]

requires:
  - phase: 35.2-uniform-name-id-resolution
    provides: ListProjectsQuery, ListProjectsRepoQuery, _ListProjectsPipeline, _ReadPipeline base class
provides:
  - ReviewDueFilter value object and DurationUnit enum
  - validate_offset_requires_limit and parse_review_due_within helpers
  - Educational error constants for list query validation
  - Pipeline expansion of ReviewDueFilter to datetime
  - CF epoch conversion in query builder for review_due_before
  - BridgeRepository review_due_before filter (cross-path equivalence)
affects: [36-02, service-orchestration, list-projects]

tech-stack:
  added: []
  patterns:
    - "<noun>Filter as read-side value object pattern in contracts/"
    - "Field validator calling shared helper for string-to-value-object parsing"
    - "Pipeline static method for context-dependent computation (datetime expansion)"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/service/validate.py
    - src/omnifocus_operator/contracts/use_cases/list/projects.py
    - src/omnifocus_operator/contracts/use_cases/list/tasks.py
    - src/omnifocus_operator/contracts/use_cases/list/__init__.py
    - src/omnifocus_operator/service/service.py
    - src/omnifocus_operator/repository/query_builder.py
    - src/omnifocus_operator/repository/bridge.py
    - tests/test_list_contracts.py
    - tests/test_list_pipelines.py
    - tests/test_query_builder.py
    - tests/test_hybrid_repository.py
    - tests/test_output_schema.py

key-decisions:
  - "ReviewDueFilter uses QueryModel base (not standalone dataclass) -- consistent with model taxonomy Filter pattern"
  - "Calendar arithmetic for months/years avoids dateutil dependency -- manual month/year overflow handling"
  - "CF epoch conversion in query builder (not pipeline) -- keeps datetime in Python types as long as possible"
  - "Filter suffix added to naming convention allowed suffixes -- first <noun>Filter in the codebase"

patterns-established:
  - "<noun>Filter pattern: read-side value object for complex query dimensions, parsed via @field_validator"
  - "Offset-requires-limit validation via shared helper called from @model_validator"

requirements-completed: [INFRA-06]

duration: 8min
completed: 2026-03-31
---

# Phase 36 Plan 01: Input Validation, ReviewDueFilter, and Educational Error Messages Summary

**Offset-requires-limit validation, ReviewDueFilter value object with full parsing pipeline from string to CF epoch, educational error messages for agents**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-31T13:09:41Z
- **Completed:** 2026-03-31T13:18:10Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Educational error messages for offset-without-limit and invalid review_due_within format
- ReviewDueFilter + DurationUnit value objects parse "1w", "2m", "30d", "1y", "now" and reject invalid inputs
- Full pipeline: string -> ReviewDueFilter -> datetime -> CF epoch float through all three layers
- BridgeRepository cross-path equivalence for review_due_before filter

## Task Commits

Each task was committed atomically:

1. **Task 1: Error constants, validation helpers, ReviewDueFilter, and query model validators**
   - `d6e03b7` (test: failing tests for offset-requires-limit and ReviewDueFilter)
   - `dab79df` (feat: error constants, ReviewDueFilter, offset-requires-limit validators)
2. **Task 2: Pipeline expansion, query builder datetime, and bridge review_due_before filter** - `6f3c6b2` (feat)

## Files Created/Modified
- `src/omnifocus_operator/agent_messages/errors.py` - OFFSET_REQUIRES_LIMIT and REVIEW_DUE_WITHIN_INVALID constants
- `src/omnifocus_operator/service/validate.py` - validate_offset_requires_limit and parse_review_due_within helpers
- `src/omnifocus_operator/contracts/use_cases/list/projects.py` - DurationUnit, ReviewDueFilter, validators on ListProjectsQuery, review_due_before on ListProjectsRepoQuery
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` - offset-requires-limit model validator
- `src/omnifocus_operator/contracts/use_cases/list/__init__.py` - Re-exports for ReviewDueFilter and DurationUnit
- `src/omnifocus_operator/service/service.py` - _expand_review_due static method on _ListProjectsPipeline
- `src/omnifocus_operator/repository/query_builder.py` - CF epoch conversion for review_due_before
- `src/omnifocus_operator/repository/bridge.py` - review_due_before filter in list_projects
- `tests/test_list_contracts.py` - 16 new tests for offset and review_due validation
- `tests/test_list_pipelines.py` - 7 new tests for pipeline expansion
- `tests/test_query_builder.py` - Updated review_due test to use datetime + CF epoch assertion
- `tests/test_hybrid_repository.py` - Fixed review_due test to use CF epoch floats in fixture data
- `tests/test_output_schema.py` - Added Filter to naming convention allowed suffixes

## Decisions Made
- ReviewDueFilter uses QueryModel base for consistency with model taxonomy
- Calendar arithmetic for months/years without dateutil dependency
- CF epoch conversion stays in query builder (not pipeline) to keep datetime types in Python as long as possible
- Added "Filter" to CONTRACT_SUFFIXES as first instance of the <noun>Filter pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed hybrid repo test data using ISO strings instead of CF epoch floats**
- **Found during:** Task 2 (full test suite run)
- **Issue:** test_list_projects_review_due_within used ISO string "2026-03-15T00:00:00+00:00" for nextReviewDate in fixture data, but SQLite column is REAL type expecting CF epoch floats
- **Fix:** Converted fixture nextReviewDate values to use _cf_epoch() helper
- **Files modified:** tests/test_hybrid_repository.py
- **Committed in:** 6f3c6b2

**2. [Rule 3 - Blocking] Added "Filter" to naming convention suffix whitelist**
- **Found during:** Task 2 (full test suite run)
- **Issue:** test_output_schema.py naming convention test rejected ReviewDueFilter because "Filter" wasn't in CONTRACT_SUFFIXES
- **Fix:** Added "Filter" to the tuple, consistent with model-taxonomy.md which documents <noun>Filter as valid
- **Files modified:** tests/test_output_schema.py
- **Committed in:** 6f3c6b2

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for test suite to pass. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data flows are fully wired.

## Next Phase Readiness
- ReviewDueFilter and validation infrastructure ready for use by 36-02 (cross-path equivalence tests)
- All three layers (contracts, service, repository) updated consistently

---
*Phase: 36-service-orchestration-cross-path-equivalence-merged-from-old-phases-36-37*
*Completed: 2026-03-31*
