---
phase: 25-patch-patchorclear-type-aliases-for-command-models
plan: 01
subsystem: contracts
tags: [pydantic, type-aliases, patch-semantics, command-models]

# Dependency graph
requires:
  - phase: 24-move-test-doubles-to-tests-doubles
    provides: clean contracts layer with _Unset sentinel and CommandModel
provides:
  - Patch[T], PatchOrClear[T], PatchOrNone[T] type aliases for self-documenting field annotations
  - changed_fields() method on CommandModel for iterating explicitly set fields
  - All command model fields migrated from raw unions to aliased annotations
affects: [26-replace-inmemoryrepository-with-stateful-inmemorybridge]

# Tech tracking
tech-stack:
  added: []
  patterns: [TypeVar+Union type aliases for Pydantic models, changed_fields() on CommandModel]

key-files:
  created:
    - tests/test_contracts_type_aliases.py
  modified:
    - src/omnifocus_operator/contracts/base.py
    - src/omnifocus_operator/contracts/common.py
    - src/omnifocus_operator/contracts/use_cases/edit_task.py
    - src/omnifocus_operator/contracts/__init__.py

key-decisions:
  - "TypeVar+Union approach for aliases (only approach with clean JSON schema + mypy pass)"
  - "PatchOrNone[T] as distinct alias from PatchOrClear[T] for domain-meaningful None values"
  - "changed_fields() on CommandModel base, not standalone function"

patterns-established:
  - "Patch[T] for value-only patchable fields, PatchOrClear[T] for clearable fields, PatchOrNone[T] for domain-meaningful None"
  - "changed_fields() for generic iteration of set fields (complements is_set() for per-field type-safe branching)"

requirements-completed: [TYPE-01, TYPE-02, TYPE-03, TYPE-04]

# Metrics
duration: 5min
completed: 2026-03-20
---

# Phase 25 Plan 01: Type Aliases Summary

**Patch[T]/PatchOrClear[T]/PatchOrNone[T] aliases and changed_fields() on CommandModel, all command model annotations migrated with identical JSON schema output**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-20T21:15:20Z
- **Completed:** 2026-03-20T21:20:01Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 5

## Accomplishments
- Defined three type aliases in `base.py`: `Patch[T]`, `PatchOrClear[T]`, `PatchOrNone[T]` using TypeVar+Union approach
- Added `changed_fields()` method to `CommandModel` base class
- Migrated all field annotations in `TagAction`, `MoveAction`, `EditTaskActions`, `EditTaskCommand`
- Re-exported aliases from `contracts/__init__.py`
- JSON schema output byte-for-byte identical before and after migration
- All 610 tests pass (597 existing + 13 new), mypy clean, no alias name leakage

## Task Commits

Each task was committed atomically (TDD flow):

1. **Task 1 RED: Failing tests for aliases and changed_fields** - `49edd7d` (test)
2. **Task 1 GREEN: Implement aliases, changed_fields, migrate annotations** - `abb173d` (feat)

## Files Created/Modified
- `src/omnifocus_operator/contracts/base.py` - Added T, Patch, PatchOrClear, PatchOrNone, changed_fields()
- `src/omnifocus_operator/contracts/common.py` - Migrated TagAction and MoveAction field annotations
- `src/omnifocus_operator/contracts/use_cases/edit_task.py` - Migrated EditTaskCommand and EditTaskActions field annotations
- `src/omnifocus_operator/contracts/__init__.py` - Re-export Patch, PatchOrClear, PatchOrNone
- `tests/test_contracts_type_aliases.py` - Schema identity, alias leakage, and changed_fields tests

## Decisions Made
- TypeVar+Union approach chosen for aliases (only approach validated in research that produces clean JSON schema + passes mypy)
- PatchOrNone[T] kept as distinct alias from PatchOrClear[T] despite same Union -- prevents future cleanup that merges them without understanding MoveAction's None=inbox semantics
- changed_fields() placed on CommandModel (inherited by all command models) rather than standalone function
- TagAction.replace uses PatchOrNone (None = "clear all tags" is a domain operation, not a field-clear)
- MoveAction.beginning/ending use PatchOrNone (None = inbox is a domain value)
- edit_task.py drops `_Unset` import entirely (aliases make direct `_Unset` references unnecessary)
- common.py retains `_Unset` import (model validators use `is_set()` which references `_Unset` via TypeGuard)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All type aliases and changed_fields() available for Phase 26 (InMemoryBridge)
- changed_fields() provides generic field iteration that InMemoryBridge can use for applying edits

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 25-patch-patchorclear-type-aliases-for-command-models*
*Completed: 2026-03-20*
