---
phase: 32-read-model-rewrite
plan: 01
subsystem: models
tags: [pydantic, discriminated-union, rrule, parser, builder]

requires: []
provides:
  - ~~FrequencySpec~~ → Frequency discriminated union with 8 frequency subtypes
  - RRULE parser (parse_rrule, parse_end_condition)
  - RRULE builder (build_rrule) with round-trip validation
  - RepetitionRule model with frequency, schedule, basedOn, end
  - Schedule enum (3 values), BasedOn enum (3 values)
  - EndByDate/EndByOccurrences end condition models
affects: [32-02, 33-write-model]

tech-stack:
  added: []
  patterns:
    - "~~@model_serializer for nested serialization control (interval=1 omission)~~ (reverted before UAT — erased serialization schema)"
    - "Discriminated union via Annotated[Union[...], Field(discriminator='type')]"
    - "Reverse mapping tables for bidirectional RRULE conversion"

key-files:
  created:
    - src/omnifocus_operator/models/repetition_rule.py
    - src/omnifocus_operator/rrule/__init__.py
    - src/omnifocus_operator/rrule/parser.py
    - src/omnifocus_operator/rrule/builder.py
    - tests/test_rrule.py
  modified: []

key-decisions:
  - "~~Used @model_serializer instead of model_dump override for D-08 interval omission -- ensures correct behavior when frequency is nested inside RepetitionRule~~ (reverted before UAT — @model_serializer erased serialization schema)"
  - "Parser returns plain dicts (not model instances) -- keeps parser decoupled from Pydantic, dicts validated at model layer"

patterns-established:
  - "~~@model_serializer on _FrequencyBase: interval=1 omission + None-field exclusion, works in nested context~~ (reverted before UAT)"
  - "RRULE mapping tables: _POS_TO_ORDINAL/_DAY_CODE_TO_NAME for parser, reverse tables for builder"
  - "Golden master RRULE test: parametrized test extracting all ruleString values from 08-repetition/ snapshots"

requirements-completed: [READ-01, READ-02, READ-04]

duration: 6min
completed: 2026-03-28
---

# Phase 32 Plan 01: RRULE Parser/Builder and Frequency Models Summary

**8-type ~~FrequencySpec~~ → Frequency discriminated union with RRULE parser/builder, round-trip validated against 15 golden master rule strings**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-28T00:44:44Z
- **Completed:** 2026-03-28T00:50:57Z
- **Tasks:** 2
- **Files created:** 5

## Accomplishments
- Complete type hierarchy: 8 frequency subtypes, ~~FrequencySpec~~ → Frequency discriminated union, EndCondition models, RepetitionRule model, Schedule/BasedOn enums
- RRULE parser handling all 8 frequency types including BYDAY positional prefix (2TU, -1FR), MINUTELY/HOURLY, COUNT/UNTIL end conditions
- RRULE builder with reverse mapping and round-trip validation
- 89 tests covering models, parser, builder, round-trips, and all 15 golden master RRULE strings

## Task Commits

Each task was committed atomically (TDD: test then feat):

1. **Task 1: Pydantic frequency models and RepetitionRule** - `4bf4174` (test) + `344d8f4` (feat)
2. **Task 2: RRULE parser and builder** - `f78feeb` (test) + `1fa2eca` (feat)

## Files Created
- `src/omnifocus_operator/models/repetition_rule.py` - 8 frequency subtypes, ~~FrequencySpec~~ → Frequency union, EndCondition, RepetitionRule, Schedule, BasedOn
- `src/omnifocus_operator/rrule/__init__.py` - Package re-exports
- `src/omnifocus_operator/rrule/parser.py` - parse_rrule and parse_end_condition
- `src/omnifocus_operator/rrule/builder.py` - build_rrule with round-trip validation
- `tests/test_rrule.py` - 89 tests across 12 test classes

## Decisions Made
- ~~Used `@model_serializer` instead of `model_dump` override for D-08 interval omission -- Pydantic's `model_dump` override doesn't propagate to nested models, `@model_serializer` does~~ (reverted before UAT — @model_serializer erased serialization schema, breaking MCP outputSchema)
- Parser returns plain dicts rather than model instances -- keeps parser decoupled from Pydantic; dicts are validated when passed to models in the read path

## Deviations from Plan

### Auto-fixed Issues

~~**1. [Rule 1 - Bug] Switched from model_dump override to @model_serializer**~~
~~- **Found during:** Task 1 (frequency model serialization)~~
~~- **Issue:** Custom `model_dump` override on `_FrequencyBase` did not apply when the frequency model was serialized as a nested field inside `RepetitionRule`. Pydantic calls its internal serializer for nested models, bypassing the Python-level `model_dump` override.~~
~~- **Fix:** Replaced `model_dump` override with `@model_serializer` decorator, which Pydantic respects during both direct and nested serialization.~~
~~- **Files modified:** `src/omnifocus_operator/models/repetition_rule.py`~~
~~- **Verification:** `test_frequency_interval_omission_in_nested_dump` passes~~
~~- **Committed in:** `344d8f4` (Task 1 feat commit)~~

> **Reverted before UAT**: `@model_serializer` erased the serialization-mode JSON Schema, breaking MCP outputSchema validation. `@field_serializer` returning None had the same effect. The fix: remove all custom serializers, let `interval=1` appear in output.

---

**Total deviations:** 1 auto-fixed (1 bug), later reverted before UAT
**Impact on plan:** ~~Essential fix for correct nested serialization.~~ The serializer approach was correct for nested propagation but broke the JSON Schema contract that FastMCP depends on.

## Issues Encountered
None -- all tests passed on first implementation after the serializer fix.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None -- all code is fully wired and functional.

## Next Phase Readiness
- All types and parser/builder ready for Plan 02 (model swap + read path wiring)
- `models/__init__.py` not yet updated with new exports (Plan 02 scope)
- Existing `RepetitionRule` in `common.py` not yet replaced (Plan 02 scope)

---
*Phase: 32-read-model-rewrite*
*Completed: 2026-03-28*
