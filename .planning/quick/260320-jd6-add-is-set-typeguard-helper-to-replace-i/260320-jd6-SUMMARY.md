---
phase: quick-260320-jd6
plan: 01
subsystem: contracts
tags: [typeguard, sentinel, type-narrowing, pydantic]

requires:
  - phase: 22-service-decomposition
    provides: "service layer with _Unset sentinel checks"
provides:
  - "is_set() TypeGuard helper in contracts/base.py"
  - "Cleaner sentinel checks across 5 consumer files"
affects: [contracts, service]

tech-stack:
  added: []
  patterns: ["is_set() TypeGuard for sentinel checks instead of isinstance(_Unset)"]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/base.py
    - src/omnifocus_operator/contracts/common.py
    - src/omnifocus_operator/service/service.py
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/service/payload.py
    - src/omnifocus_operator/service/validate.py

key-decisions:
  - "PEP 695 type parameter syntax (def is_set[T]) per ruff UP047"
  - "Added 3 type: ignore[union-attr] on is_set compound checks in service.py (mypy bool-var narrowing limitation)"
  - "Keep _Unset import in common.py where used for field type annotations"

patterns-established:
  - "is_set(value) replaces not isinstance(value, _Unset) everywhere"
  - "not is_set(value) replaces isinstance(value, _Unset) everywhere"

requirements-completed: [TODO-is-set-typeguard]

duration: 4min
completed: 2026-03-20
---

# Quick Task 260320-jd6: is_set TypeGuard Helper Summary

**Added is_set() TypeGuard helper to contracts/base.py and replaced all 22 isinstance(_Unset) checks across 5 consumer files**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T14:14:44Z
- **Completed:** 2026-03-20T14:19:18Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `is_set[T](value: T | _Unset) -> TypeGuard[T]` helper with PEP 695 syntax
- Replaced all 22 `isinstance(..., _Unset)` checks with `is_set()` / `not is_set()` across 5 files
- Zero remaining isinstance _Unset patterns in consumer code
- All 588 tests pass, mypy clean, ruff clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Add is_set TypeGuard helper to contracts/base.py** - `a4b8e3c` (feat)
2. **Task 2: Replace all isinstance _Unset checks with is_set across 5 files** - `2661e2e` (refactor)

## Files Created/Modified

- `src/omnifocus_operator/contracts/base.py` - Added is_set() TypeGuard helper function, exported in __all__
- `src/omnifocus_operator/contracts/common.py` - TagAction + MoveAction validators use is_set() (4 replacements)
- `src/omnifocus_operator/service/service.py` - edit_task orchestration uses is_set() (8 replacements)
- `src/omnifocus_operator/service/domain.py` - normalize, tag diff, move extract use is_set() (7 replacements)
- `src/omnifocus_operator/service/payload.py` - _add_if_set + _add_dates_if_set use is_set() (2 replacements)
- `src/omnifocus_operator/service/validate.py` - validate_task_name_if_set uses not is_set() (1 replacement)

## Decisions Made

- **PEP 695 syntax**: Ruff UP047 required `def is_set[T](...)` instead of `TypeVar("T")` -- Python 3.12+ project, so no compatibility concern
- **3 new type: ignore[union-attr]**: Lines 150-152 in service.py need type: ignore because mypy doesn't propagate TypeGuard narrowing through boolean variables (`has_actions = is_set(command.actions)` then `has_actions and is_set(command.actions.lifecycle)` -- mypy doesn't know `command.actions` is narrowed in the second operand). This is a known mypy limitation, not a regression
- **_Unset import retained in common.py**: Still used for field type annotations (`add: list[str] | _Unset = UNSET`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff UP047 required PEP 695 type parameter syntax**
- **Found during:** Task 1 (is_set helper creation)
- **Issue:** Ruff rejected `T = TypeVar("T")` + `def is_set(value: T | _Unset)` with UP047
- **Fix:** Changed to PEP 695 syntax `def is_set[T](value: T | _Unset)`
- **Files modified:** src/omnifocus_operator/contracts/base.py
- **Verification:** ruff check passes, mypy passes, runtime import OK
- **Committed in:** a4b8e3c (Task 1 commit)

**2. [Rule 1 - Bug] Added type: ignore for mypy bool-var narrowing limitation**
- **Found during:** Task 2 (service.py replacements)
- **Issue:** mypy can't propagate TypeGuard narrowing through boolean variables in compound expressions
- **Fix:** Added `# type: ignore[union-attr]` on 3 compound is_set() lines (150-152)
- **Files modified:** src/omnifocus_operator/service/service.py
- **Verification:** mypy passes with no errors
- **Committed in:** 2661e2e (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both anticipated by the plan. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- is_set() pattern established for all future sentinel checks
- Any new code using _Unset should use is_set() instead of isinstance

---
*Quick task: 260320-jd6*
*Completed: 2026-03-20*
