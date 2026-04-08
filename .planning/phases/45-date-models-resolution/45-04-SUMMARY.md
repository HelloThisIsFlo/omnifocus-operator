---
phase: 45-date-models-resolution
plan: 04
subsystem: contracts, service
tags: [date-filter, error-messages, due-soon, enum, gap-closure]
dependency_graph:
  requires:
    - phase: 45-01
      provides: DateFilter model, error constants, _validate_this_unit
    - phase: 45-03
      provides: resolve_date_filter pure function
  provides:
    - DATE_FILTER_INVALID_THIS_UNIT error constant
    - DueSoonSetting enum with 7 OmniFocus due-soon settings
    - DueSoonSetting-based resolve_date_filter signature
  affects: [service.resolve_dates, contracts.use_cases.list._enums, agent_messages.errors]
tech_stack:
  added: []
  patterns: [tuple-valued-enum-with-properties]
key_files:
  created:
    - tests/test_date_filter_constants.py
  modified:
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
    - src/omnifocus_operator/contracts/use_cases/list/_enums.py
    - src/omnifocus_operator/contracts/use_cases/list/__init__.py
    - src/omnifocus_operator/service/resolve_dates.py
    - tests/test_date_filter_contracts.py
    - tests/test_resolve_dates.py
    - tests/test_descriptions.py
key_decisions:
  - "DueSoonSetting uses tuple-valued Enum (not StrEnum) with domain properties -- internal config, not agent-facing"
  - "DATE_FILTER_INVALID_THIS_UNIT mentions only bare unit chars (d/w/m/y), never count+unit examples"
  - "_compute_soon_threshold refactored to accept (days, calendar_aligned) instead of (interval, granularity)"
patterns_established:
  - "Tuple-valued Enum with __init__ and @property for domain semantics over raw storage values"
requirements_completed: [DATE-05, RESOLVE-06]
metrics:
  duration: 10m
  completed: 2026-04-08
  tasks_completed: 2
  tasks_total: 2
  test_count: 1808
  test_pass: 1808
---

# Phase 45 Plan 04: Gap Closure -- Error Message and DueSoonSetting Summary

**Fixed 'this' field error message to mention only bare unit chars, replaced raw interval/granularity ints with DueSoonSetting domain enum on resolve_date_filter**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-08T10:28:25Z
- **Completed:** 2026-04-08T10:38:45Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- DateFilter(this="2w") now raises error mentioning only bare unit chars (d/w/m/y), not duration format with counts
- DueSoonSetting enum with exactly 7 members matching OmniFocus discrete settings, each with domain properties (days, calendar_aligned)
- resolve_date_filter signature uses DueSoonSetting enum instead of raw ints
- Full test suite passes: 1808 tests, 97.80% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Add DATE_FILTER_INVALID_THIS_UNIT constant and fix _validate_this_unit** - `7456e06` (fix)
2. **Task 2: Create DueSoonSetting enum and refactor resolve_date_filter signature** - `77f053e` (feat)

## Files Created/Modified
- `src/omnifocus_operator/agent_messages/errors.py` - New DATE_FILTER_INVALID_THIS_UNIT constant
- `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py` - _validate_this_unit uses new constant
- `src/omnifocus_operator/contracts/use_cases/list/_enums.py` - DueSoonSetting enum with 7 members
- `src/omnifocus_operator/contracts/use_cases/list/__init__.py` - DueSoonSetting exported
- `src/omnifocus_operator/service/resolve_dates.py` - due_soon_setting param, domain-term threshold
- `tests/test_date_filter_contracts.py` - Updated match pattern for 'this' validation
- `tests/test_date_filter_constants.py` - New constant importability and placeholder tests
- `tests/test_resolve_dates.py` - DueSoonSetting-based tests, enum property tests
- `tests/test_descriptions.py` - DueSoonSetting added to _INTERNAL_CLASSES

## Decisions Made
- DueSoonSetting uses tuple-valued Enum (not StrEnum) because it's an internal config type, not agent-facing input. Each member's value is `(days, calendar_aligned)` with `@property` accessors.
- _compute_soon_threshold refactored from `(interval_seconds, granularity_int)` to `(days, calendar_aligned)` -- domain semantics replace storage format. Rolling mode uses `timedelta(days=N)` instead of `timedelta(seconds=interval)`.
- test_date_filter_constants.py recreated (was previously deleted as redundant) specifically for the new DATE_FILTER_INVALID_THIS_UNIT constant tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added DueSoonSetting to _INTERNAL_CLASSES in test_descriptions.py**
- **Found during:** Task 2 verification
- **Issue:** `test_no_inline_class_docstrings_on_agent_classes` flagged DueSoonSetting's inline docstring as a violation. DueSoonSetting is internal (not agent-facing), so it should be in the exception list.
- **Fix:** Added `"DueSoonSetting"` to `_INTERNAL_CLASSES` set with comment explaining it's an internal config enum.
- **Files modified:** tests/test_descriptions.py
- **Verification:** Full suite passes (1808 tests)
- **Committed in:** 77f053e (Task 2 commit)

**2. [Rule 3 - Blocking] Recreated test_date_filter_constants.py**
- **Found during:** Task 1 setup
- **Issue:** Plan references test_date_filter_constants.py for adding tests, but the file was deleted in dc9b531 (lint cleanup). File needed to exist for the new constant tests.
- **Fix:** Created new test_date_filter_constants.py with tests for DATE_FILTER_INVALID_THIS_UNIT.
- **Files modified:** tests/test_date_filter_constants.py (created)
- **Verification:** 4 tests pass
- **Committed in:** 7456e06 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for test infrastructure correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Error constant and DueSoonSetting enum ready for Phase 46 pipeline integration
- Phase 46 will read DueSoonInterval/DueSoonGranularity from Settings table, map to DueSoonSetting, pass to resolver

## Self-Check: PASSED

- All 10 key files verified present on disk
- Both task commits (7456e06, 77f053e) found in git log
- DateFilter(this="2w") error message mentions only bare unit chars -- PASS
- DueSoonSetting has exactly 7 members with correct properties -- PASS
- resolve_date_filter signature uses due_soon_setting, not raw ints -- PASS
- Full suite: 1808 passed, 97.80% coverage -- PASS

---
*Phase: 45-date-models-resolution*
*Completed: 2026-04-08*
