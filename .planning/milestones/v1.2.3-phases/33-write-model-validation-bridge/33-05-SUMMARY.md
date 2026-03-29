---
phase: 33-write-model-validation-bridge
plan: 05
subsystem: rrule, service
tags: [rrule, bymonthday, repetition-rule, no-op-detection, bug-fix]

# Dependency graph
requires:
  - phase: 33-write-model-validation-bridge (plans 01-04)
    provides: repetition rule write pipeline, rrule builder/parser, no-op detection framework
provides:
  - Multi-value BYMONTHDAY round-trip (build + parse) for onDates arrays
  - Per-field repetition rule no-op detection in _apply_repetition_rule
affects: [uat, service, rrule]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inline no-op detection in pipeline step (not deferred to whole-edit no-op)"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/rrule/builder.py
    - src/omnifocus_operator/rrule/parser.py
    - src/omnifocus_operator/service/service.py
    - tests/test_rrule.py
    - tests/test_service.py

key-decisions:
  - "Inline no-op comparison in _apply_repetition_rule rather than extracting to domain -- keeps detection at the payload build site"

patterns-established: []

requirements-completed: [EDIT-16, ADD-01]

# Metrics
duration: 5min
completed: 2026-03-29
---

# Phase 33 Plan 05: Gap Closure -- BYMONTHDAY Multi-Value and Repetition No-Op Warning Summary

**Fixed two UAT-discovered bugs: multi-value BYMONTHDAY silently dropped extra values; no-op repetition rule warning suppressed when combined with other field changes**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-28T23:56:57Z
- **Completed:** 2026-03-29T00:02:21Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Multi-value BYMONTHDAY (`onDates=[1, 15, -1]`) now round-trips correctly through build_rrule and parse_rrule
- REPETITION_NO_OP warning fires regardless of whether other task fields are modified in the same edit
- Redundant bridge call skipped when repetition rule is unchanged (payload cleared to None)

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Fix multi-value BYMONTHDAY in builder and parser**
   - `033a784` (test: RED -- add failing tests for multi-value BYMONTHDAY)
   - `852385a` (fix: GREEN -- emit comma-joined values in builder, split in parser)
2. **Task 2: Fix no-op repetition rule warning when other fields change**
   - `e677cc3` (test: RED -- add failing test for no-op with other field change)
   - `456b2a6` (fix: GREEN -- inline no-op detection in _apply_repetition_rule)

## Files Created/Modified
- `src/omnifocus_operator/rrule/builder.py` -- Emit all on_dates comma-separated instead of hardcoded [0]
- `src/omnifocus_operator/rrule/parser.py` -- Split BYMONTHDAY on commas, parse each integer
- `src/omnifocus_operator/service/service.py` -- Add no-op detection after payload build in _apply_repetition_rule
- `tests/test_rrule.py` -- 3 new tests (builder multi-value, parser multi-value, round-trip parametrize)
- `tests/test_service.py` -- 1 new test (test_noop_same_rule_with_other_field_change)

## Decisions Made
- Inlined no-op comparison in `_apply_repetition_rule` rather than extracting a new domain method -- the comparison is 4 fields at the payload build site, keeping it local avoids indirection. The existing `_all_fields_match` in domain.py remains as a redundant fallback for the pure-repetition-only no-op case.

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None -- no external service configuration required.

## Known Stubs

None

## Next Phase Readiness
- Both UAT bugs (test 11/1d and test 40/11b) are now fixed with test coverage
- Full test suite passes (1020 tests), mypy clean
- Ready for UAT re-verification of these specific cases

## Self-Check: PASSED

All 5 modified files verified present. All 4 commit hashes verified in git log.

---
*Phase: 33-write-model-validation-bridge*
*Completed: 2026-03-29*
