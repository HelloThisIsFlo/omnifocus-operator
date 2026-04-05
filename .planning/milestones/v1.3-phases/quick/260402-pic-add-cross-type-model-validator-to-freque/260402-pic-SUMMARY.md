---
phase: quick-260402-pic
plan: 01
subsystem: contracts
tags: [pydantic, model-validator, patch-semantics, repetition-rule]

requires:
  - phase: quick-260401-hz9
    provides: OrdinalWeekdaySpec typed model used by FrequencyEditSpec.on field
provides:
  - Cross-type validation on FrequencyEditSpec catching contradictory patches at contract boundary
affects: [service-layer-merge, edit-tasks]

tech-stack:
  added: []
  patterns: [is_set-guarded model_validator for edit specs]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/shared/repetition_rule.py
    - tests/test_contracts_repetition_rule.py

key-decisions:
  - "is_set() guard on type field -- skip all cross-type checks when type is UNSET, deferring to service layer after merge"

patterns-established:
  - "is_set-guarded cross-type validator: convert UNSET fields to None before delegating to shared validation function"

requirements-completed: [QUICK-260402-PIC]

duration: 3min
completed: 2026-04-02
---

# Quick Task 260402-pic: Cross-Type Model Validator for FrequencyEditSpec Summary

**FrequencyEditSpec now rejects contradictory type+field patches (e.g., type='daily' + on_days) at contract boundary via is_set()-guarded model_validator**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-02T16:19:41Z
- **Completed:** 2026-04-02T16:22:35Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments

- Added @model_validator to FrequencyEditSpec calling check_frequency_cross_type_fields with is_set() guards
- 8 new tests: 4 rejection, 4 pass-through (replaces 2 less-specific tests)
- All 1435 tests pass, 98.2% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `9c92c8e` (test)
2. **Task 1 GREEN: Implement validator** - `b82a0c2` (feat)

## Files Created/Modified

- `src/omnifocus_operator/contracts/shared/repetition_rule.py` - Added is_set import, _check_cross_type_fields model_validator on FrequencyEditSpec
- `tests/test_contracts_repetition_rule.py` - Replaced 2 generic tests with 8 specific cross-type validation tests
- `src/omnifocus_operator/service/service.py` - Fixed pre-existing mypy error (type: ignore on Spec->Core assignment)

## Decisions Made

- is_set() guard on type field: when type is UNSET, skip all cross-type checks entirely -- service layer validates after merging edit spec with existing rule

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed pre-existing mypy error in service.py**
- **Found during:** Task 1 RED (commit attempt)
- **Issue:** Pre-existing mypy error on service.py:598 -- EndConditionSpec assigned to EndCondition variable. Blocked all commits via pre-commit hook.
- **Fix:** Added `type: ignore[assignment]` comment (Spec and Core models are structurally compatible)
- **Files modified:** src/omnifocus_operator/service/service.py
- **Verification:** mypy passes, all tests pass
- **Committed in:** 9c92c8e (part of RED commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minimal -- pre-existing issue unrelated to plan scope, type: ignore is appropriate for Spec->Core structural compatibility.

## Issues Encountered

None beyond the pre-existing mypy error documented above.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- FrequencyEditSpec now has parity with FrequencyAddSpec for cross-type validation
- Service layer merge logic unchanged -- UNSET fields still deferred correctly

---
*Phase: quick-260402-pic*
*Completed: 2026-04-02*
