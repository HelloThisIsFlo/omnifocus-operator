---
phase: 49-implement-naive-local-datetime-contract-for-all-date-inputs
plan: 01
subsystem: contracts
tags: [pydantic, datetime, naive-local, json-schema, validation]

# Dependency graph
requires:
  - phase: 48-refactor-datefilter-into-discriminated-union-with-typed-date
    provides: discriminated union DateFilter structure (kept intact, only bound types changed)
provides:
  - str-typed date fields on AddTaskCommand, EditTaskCommand, and _DateBound
  - _validate_date_string syntax validator for all date inputs
  - local_now() helper in config.py returning tz-aware local datetime
  - DATE_EXAMPLE as naive local format
  - Tool descriptions framing dates as local time
affects: [49-02, 49-03, service-layer-date-normalization, query-builder-date-resolution]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "str-typed date fields with fromisoformat syntax validation (no format: date-time in JSON Schema)"
    - "local_now() as centralized local timezone helper"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/config.py
    - src/omnifocus_operator/contracts/use_cases/add/tasks.py
    - src/omnifocus_operator/contracts/use_cases/edit/tasks.py
    - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - src/omnifocus_operator/agent_messages/errors.py

key-decisions:
  - "str type over AwareDatetime/NaiveDatetime -- drops format: date-time from JSON Schema entirely"
  - "fromisoformat for syntax validation -- accepts naive, aware, and date-only strings"
  - "Duplicate _validate_date_string in add/edit rather than shared import -- small function, avoids cross-package dependency"
  - "Separate _validate_date_bound_string for filter bounds -- handles 'now' literal pass-through"

patterns-established:
  - "Date syntax validation: fromisoformat as the single validation gate for all date string inputs"
  - "local_now() in config.py: canonical way to get current local time throughout the codebase"

requirements-completed: [LOCAL-01, LOCAL-02, LOCAL-07]

# Metrics
duration: 4min
completed: 2026-04-10
---

# Phase 49 Plan 01: Contract Date Types Summary

**All date inputs changed from AwareDatetime to str with fromisoformat syntax validation, local_now() helper created, DATE_EXAMPLE switched to naive local, dead Phase 48 timezone rejection code removed**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-10T21:36:50Z
- **Completed:** 2026-04-10T21:40:24Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- All 8 date input fields across the API (3 on AddTaskCommand, 3 on EditTaskCommand, 2 on AbsoluteRangeFilter) now accept naive datetime strings
- JSON Schema no longer emits `format: "date-time"` on any date input field -- agents no longer receive a signal to include timezone
- `local_now()` helper in config.py returns tz-aware local datetime for use by service layer (Plan 02)
- DATE_EXAMPLE changed to "2026-03-15T17:00:00" (no Z suffix) -- agents copy this pattern
- Dead code removed: `_reject_naive_datetime`, `_to_naive`, `DATE_FILTER_NAIVE_DATETIME`

## Task Commits

Each task was committed atomically:

1. **Task 1: Change contract types to str + add syntax validator + create local_now()** - `9ab5a3c` (feat)
2. **Task 2: Update DATE_EXAMPLE + bound descriptions + tool doc notes + remove error constant** - `ab41fbb` (feat)

## Files Created/Modified
- `src/omnifocus_operator/config.py` - Added local_now() helper function, datetime import
- `src/omnifocus_operator/contracts/use_cases/add/tasks.py` - AwareDatetime -> str on 3 date fields, added _validate_date_string + field_validator
- `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` - PatchOrClear[AwareDatetime] -> PatchOrClear[str] on 3 date fields, added _validate_date_string + field_validator
- `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py` - _DateBound changed to Literal["now"] | str, _reject_naive_datetime and _to_naive removed, _validate_bounds updated to parse strings
- `src/omnifocus_operator/agent_messages/descriptions.py` - DATE_EXAMPLE naive local, tool docs add "local time" note, bound descriptions updated
- `src/omnifocus_operator/agent_messages/errors.py` - DATE_FILTER_NAIVE_DATETIME removed, DATE_FILTER_RANGE_EMPTY updated

## Decisions Made
- Used `datetime.fromisoformat()` as the syntax validator -- it accepts all three formats (naive, aware, date-only) that the API supports, making it the exact right gate
- Duplicated `_validate_date_string` in both add/tasks.py and edit/tasks.py rather than creating a shared import -- the function is 8 lines; sharing would create a cross-package import for minimal DRY benefit
- Created a separate `_validate_date_bound_string` for filter bounds that also handles the "now" literal pass-through
- `_validate_bounds` strips tzinfo before comparing so mixed naive/aware bounds don't raise TypeError

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Contract layer complete: all date inputs accept str, syntax validated, no format: "date-time" in schema
- Plan 02 can implement service-layer normalization (domain.py) using these str inputs
- Plan 02 can use local_now() for datetime.now(UTC) replacement in service pipelines
- Plan 03 can update tests to exercise the new contract

## Self-Check: PASSED

- All 6 modified files exist on disk
- Commit 9ab5a3c (Task 1) found in git log
- Commit ab41fbb (Task 2) found in git log

---
*Phase: 49-implement-naive-local-datetime-contract-for-all-date-inputs*
*Completed: 2026-04-10*
