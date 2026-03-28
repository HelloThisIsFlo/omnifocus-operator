---
phase: 260328-sh9
plan: 01
subsystem: rrule
tags: [rrule, parser, builder, bysetpos, repetition-rule]

requires:
  - phase: 32-read-model-rewrite
    provides: RRULE parser, builder, MonthlyDayOfWeekFrequency model
provides:
  - BYSETPOS parsing for weekday/weekend_day day groups (12 combinations)
  - Builder round-trip for BYSETPOS rules
affects: [33-write-model, rrule, repetition-rule]

tech-stack:
  added: []
  patterns: [frozenset day-group lookup for multi-day BYDAY matching]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/rrule/parser.py
    - src/omnifocus_operator/rrule/builder.py
    - tests/test_rrule.py
    - .planning/phases/32-read-model-rewrite/32-CONTEXT.md

key-decisions:
  - "Narrowed BYSETPOS validation from blanket rejection to MONTHLY-only check"
  - "frozenset lookup for day group recognition — order-independent matching (SA,SU = SU,SA)"

patterns-established:
  - "Day group expansion: _DAY_GROUP_TO_NAME in parser, _DAY_GROUP_BYDAY in builder — mirror pattern for round-trip correctness"

requirements-completed: [BYSETPOS-FIX]

duration: 4min
completed: 2026-03-28
---

# Quick Task 260328-sh9: Fix BYSETPOS Repetition Rule Parsing Bug Summary

**BYSETPOS multi-day positional rules (weekday/weekend_day) now parse and round-trip correctly, unblocking UAT on databases with monthly weekday/weekend day repeats**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-28T20:54:42Z
- **Completed:** 2026-03-28T20:58:38Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Parser handles 12 BYSETPOS combinations (2 day groups x 6 ordinals) via `_parse_monthly_bysetpos` helper
- Builder emits `BYDAY=...;BYSETPOS=N` form for weekday/weekend_day values, prefix form for single days
- Round-trip identity verified: parse -> build -> parse produces identical models
- Educational error messages for unknown day groups and non-MONTHLY BYSETPOS usage
- D-05 decision documentation updated to reflect the narrowed scope
- Full test suite green: 875 passed, 97.60% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing BYSETPOS tests** - `30a3713` (test)
2. **Task 1 (GREEN): Implement BYSETPOS parsing and building** - `6372e21` (feat)
3. **Task 2: Update D-05 decision documentation** - `5bdc4d7` (docs)
4. **Task 3: Verify output schema and full test suite** - verification only, no commit needed

## Files Created/Modified
- `src/omnifocus_operator/rrule/parser.py` - Added `_DAY_GROUP_TO_NAME`, `_parse_monthly_bysetpos()`, replaced `_validate_no_bysetpos` with `_validate_bysetpos_freq`
- `src/omnifocus_operator/rrule/builder.py` - Added `_DAY_GROUP_BYDAY`, updated `_build_byday_positional()` to emit BYSETPOS form for day groups
- `tests/test_rrule.py` - Added `TestParseRruleBysetpos` (7 tests), `TestBuildRruleBysetpos` (3 tests), 3 round-trip cases, updated error tests
- `.planning/phases/32-read-model-rewrite/32-CONTEXT.md` - D-05 decision updated

## Decisions Made
- Replaced blanket `_validate_no_bysetpos()` with `_validate_bysetpos_freq()` that only rejects BYSETPOS for non-MONTHLY frequencies
- Used `frozenset` matching for day group recognition so `SA,SU` and `SU,SA` both resolve to `weekend_day`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Self-Check: PASSED

All files exist, all commits verified.

---
*Quick Task: 260328-sh9-fix-bysetpos-repetition-rule-parsing-bug*
*Completed: 2026-03-28*
