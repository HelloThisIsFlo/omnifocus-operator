---
phase: 32-read-model-rewrite
plan: 02
subsystem: models
tags: [pydantic, rrule, read-path, adapter, hybrid-repo, enums]

requires:
  - phase: 32-01
    provides: FrequencySpec discriminated union, RRULE parser/builder, RepetitionRule model, Schedule/BasedOn enums
provides:
  - Structured RepetitionRule as canonical model (old 4-field version removed)
  - Both read paths (SQLite + bridge) wired to RRULE parser
  - 3-value Schedule enum (replacing 2-value ScheduleType)
  - BasedOn enum (replacing AnchorDateKey)
  - _derive_schedule helper for D-06 (scheduleType + catchUp -> 3-value)
affects: [33-write-model, service, server]

tech-stack:
  added: []
  patterns:
    - "_derive_schedule() derives 3-value Schedule from 2 raw columns in both read paths"
    - "Adapter produces camelCase keys (basedOn), SQLite path produces snake_case (based_on) -- Pydantic validates both"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/models/common.py
    - src/omnifocus_operator/models/enums.py
    - src/omnifocus_operator/models/__init__.py
    - src/omnifocus_operator/models/base.py
    - src/omnifocus_operator/models/repetition_rule.py
    - src/omnifocus_operator/repository/hybrid.py
    - src/omnifocus_operator/bridge/adapter.py
    - tests/test_models.py
    - tests/test_adapter.py
    - tests/test_hybrid_repository.py
    - tests/test_service_domain.py

key-decisions:
  - "Schedule/BasedOn canonical location is enums.py (consistent with all other enums), re-exported from repetition_rule.py via runtime import"
  - "Adapter output uses camelCase (basedOn) matching bridge JSON convention; SQLite path uses snake_case (based_on) -- both valid via Pydantic's validate_by_alias + validate_by_name"

patterns-established:
  - "_derive_schedule: from_completion+catchUp=true raises ValueError (impossible state), regularly+catchUp=true -> regularly_with_catch_up"
  - "Both read paths share identical parse_rrule/parse_end_condition calls with path-specific dict key conventions"

requirements-completed: [READ-01, READ-03]

duration: 9min
completed: 2026-03-28
---

# Phase 32 Plan 02: Model Swap and Read Path Wiring Summary

**Replaced old RepetitionRule (ruleString/scheduleType/anchorDateKey/catchUpAutomatically) with structured model (frequency/schedule/basedOn/end) and wired both read paths to RRULE parser**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-28T00:53:41Z
- **Completed:** 2026-03-28T01:03:24Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Old RepetitionRule (4 fields) removed from common.py, new structured RepetitionRule from repetition_rule.py is canonical
- ScheduleType (2 values) replaced by Schedule (3 values: regularly, regularly_with_catch_up, from_completion)
- AnchorDateKey replaced by BasedOn (same values, clearer name)
- Both SQLite and bridge read paths call parse_rrule/parse_end_condition, producing identical structured output
- from_completion + catchUp=true raises ValueError in both paths (impossible state detection)
- 830 tests pass, 97% coverage, mypy strict clean, golden master unaffected

## Task Commits

Each task was committed atomically:

1. **Task 1: Swap model layer** - `e4a8393` (feat)
2. **Task 2: Wire read paths + update tests** - `c27cbe4` (feat)

## Files Created/Modified
- `src/omnifocus_operator/models/common.py` - Removed old RepetitionRule class
- `src/omnifocus_operator/models/enums.py` - Replaced ScheduleType/AnchorDateKey with Schedule/BasedOn
- `src/omnifocus_operator/models/__init__.py` - Updated exports and _ns dict for new types
- `src/omnifocus_operator/models/base.py` - TYPE_CHECKING import now references repetition_rule module
- `src/omnifocus_operator/models/repetition_rule.py` - Moved Schedule/BasedOn to enums.py import
- `src/omnifocus_operator/repository/hybrid.py` - _build_repetition_rule calls parse_rrule, _derive_schedule
- `src/omnifocus_operator/bridge/adapter.py` - _adapt_repetition_rule calls parse_rrule, produces structured output
- `tests/test_models.py` - Updated enum tests, RepetitionRule tests, project nested rule test
- `tests/test_adapter.py` - Updated to verify frequency/schedule/basedOn output format
- `tests/test_hybrid_repository.py` - Updated repetition rule assertions
- `tests/test_service_domain.py` - Updated repeating task fixture format

## Decisions Made
- Schedule/BasedOn enums canonically live in enums.py (consistent with project convention), imported at runtime in repetition_rule.py (not TYPE_CHECKING, since Pydantic needs them for validation)
- Adapter produces camelCase keys (basedOn) while SQLite path produces snake_case (based_on) -- matches existing conventions in each path

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated test_service_domain.py repeating task fixtures**
- **Found during:** Task 2 (full test suite run)
- **Issue:** test_service_domain.py had two tests using old RepetitionRule format that weren't listed in the plan's files section
- **Fix:** Updated repetitionRule dicts from old format to new structured format
- **Files modified:** tests/test_service_domain.py
- **Verification:** All 830 tests pass
- **Committed in:** c27cbe4 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix -- missed test file that used old model shape. No scope creep.

## Issues Encountered
None -- after fixing the missed test file, all tests passed on first run.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None -- all code is fully wired and functional.

## Next Phase Readiness
- Phase 32 complete: structured RepetitionRule is the canonical model across all read paths
- All types (FrequencySpec, Schedule, BasedOn, EndCondition) ready for Phase 33 (write model)
- Both read paths produce identical structured output for the same raw data

---
*Phase: 32-read-model-rewrite*
*Completed: 2026-03-28*
