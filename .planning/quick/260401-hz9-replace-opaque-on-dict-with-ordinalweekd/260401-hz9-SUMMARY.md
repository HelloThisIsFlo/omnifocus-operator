---
phase: quick-260401-hz9
plan: 01
subsystem: models
tags: [pydantic, json-schema, repetition-rule, type-safety]

requires:
  - phase: none
    provides: existing Frequency model with opaque on: dict field
provides:
  - OrdinalWeekday model with 6 typed ordinal fields and DayName enum
  - OrdinalWeekdaySpec contract model for write-side validation
  - JSON Schema exposing structured ordinal fields instead of additionalProperties
affects: [rrule, service-domain, contracts]

tech-stack:
  added: []
  patterns:
    - "Shared standalone validators (normalize_day_name, check_at_most_one_ordinal) across core/contract model hierarchies"
    - "extra='forbid' on core value objects that double as input validators"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/models/repetition_rule.py
    - src/omnifocus_operator/contracts/shared/repetition_rule.py
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/rrule/parser.py
    - src/omnifocus_operator/rrule/builder.py
    - src/omnifocus_operator/service/domain.py
    - tests/test_validation_repetition.py
    - tests/test_contracts_repetition_rule.py
    - tests/test_output_schema.py
    - tests/test_rrule.py
    - tests/test_service_domain.py
    - tests/test_service.py

key-decisions:
  - "OrdinalWeekday gets extra='forbid' despite being a core model -- rejects unknown ordinals at validation time"
  - "Removed REPETITION_INVALID_ORDINAL constant (dead code after normalize_on removal)"
  - "merge_frequency uses model_dump(exclude_defaults=True) boundary for Spec->Core conversion"

patterns-established:
  - "Value objects in models/ can use extra='forbid' when field names ARE the valid domain vocabulary"

requirements-completed: [hz9-01]

duration: 12min
completed: 2026-04-01
---

# Quick Task 260401-hz9: Replace opaque on: dict with OrdinalWeekday Summary

**Typed OrdinalWeekday model with 6 ordinal fields and DayName enum replacing opaque dict[str, str] across all layers**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-01T12:38:05Z
- **Completed:** 2026-04-01T12:50:00Z
- **Tasks:** 2 (combined into 1 commit due to mypy whole-repo hook)
- **Files modified:** 12

## Accomplishments

- JSON Schema for `on` field now exposes 6 named ordinal fields with DayName enum (9 values) instead of opaque `additionalProperties: {type: string}`
- Wire format unchanged: `{"last": "friday"}` round-trips through add/edit/read paths
- At-most-one validator rejects multi-field `on`, accepts empty and single-field
- Empty `on: {}` flows through normalization with warning (no crash)
- `normalize_on()` function removed -- validation now handled by Pydantic model structure
- Full test suite green (1395 tests), mypy clean, output schema verified

## Task Commits

1. **Tasks 1+2: OrdinalWeekday models + consumer updates** - `94abe6b` (feat)

Note: Tasks combined into single commit because mypy pre-commit hook validates the entire repo -- intermediate states with mismatched types in consumer files would fail.

## Files Created/Modified

- `src/omnifocus_operator/models/repetition_rule.py` - Added DayName, OrdinalWeekday, normalize_day_name(), check_at_most_one_ordinal(); updated Frequency.on type; removed normalize_on() and _VALID_ORDINALS
- `src/omnifocus_operator/contracts/shared/repetition_rule.py` - Added OrdinalWeekdaySpec; updated FrequencyAddSpec.on and FrequencyEditSpec.on types; removed _normalize_on validator
- `src/omnifocus_operator/agent_messages/errors.py` - Added REPETITION_AT_MOST_ONE_ORDINAL; removed REPETITION_INVALID_ORDINAL
- `src/omnifocus_operator/rrule/parser.py` - Constructs OrdinalWeekday instances instead of dicts
- `src/omnifocus_operator/rrule/builder.py` - Extracts single set field from OrdinalWeekday instead of dict iteration
- `src/omnifocus_operator/service/domain.py` - Updated empty-on detection to check all fields None; added model_dump boundary in merge_frequency
- `tests/test_validation_repetition.py` - Added OrdinalWeekday-specific tests (case normalization, at-most-one, zero fields)
- `tests/test_contracts_repetition_rule.py` - Added OrdinalWeekdaySpec tests (extra forbid, coercion)
- `tests/test_output_schema.py` - Added test_on_field_has_ordinal_weekday_schema; updated flat model assertion
- `tests/test_rrule.py` - Updated assertions from dict to OrdinalWeekday comparisons
- `tests/test_service_domain.py` - Updated merge_frequency assertions
- `tests/test_service.py` - Updated integration test assertions

## Decisions Made

- **OrdinalWeekday gets extra="forbid"**: Despite being a core model (OmniFocusBaseModel), it needs to reject unknown ordinals like `{"invalid": "tuesday"}`. The field names ARE the valid ordinal vocabulary, so extra="forbid" is the correct validation. Documented as a pattern for value objects where field names define the domain.
- **Removed REPETITION_INVALID_ORDINAL**: The `normalize_on()` function was the only consumer. With ordinal validation now implicit in field names + extra="forbid", the constant is dead code. The test_warnings consolidation test caught this.
- **merge_frequency uses model_dump boundary**: When merging OrdinalWeekdaySpec from edit spec into Frequency (which expects OrdinalWeekday), the spec value is dumped to dict first. This prevents potential cross-hierarchy coercion issues.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] OrdinalWeekday needed extra="forbid" for unknown ordinal rejection**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Without extra="forbid", `Frequency(on={"invalid": "tuesday"})` silently ignored the unknown key, creating an empty OrdinalWeekday. The test_invalid_ordinal_rejected test caught this.
- **Fix:** Added `model_config = ConfigDict(extra="forbid")` to OrdinalWeekday
- **Files modified:** src/omnifocus_operator/models/repetition_rule.py
- **Verification:** test_invalid_ordinal_rejected passes, JSON Schema shows additionalProperties: false

**2. [Rule 1 - Bug] REPETITION_INVALID_ORDINAL became dead code**
- **Found during:** Task 2 (full test suite)
- **Issue:** test_warnings.py consolidation test detected unreferenced error constant after normalize_on() removal
- **Fix:** Removed REPETITION_INVALID_ORDINAL from errors.py
- **Files modified:** src/omnifocus_operator/agent_messages/errors.py

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered

- **mypy whole-repo hook prevented atomic per-task commits**: The pre-commit mypy hook validates all source files. Changing the `on` type in models but not yet updating consumers (parser, builder, domain) caused mypy failures. Both tasks had to be committed together.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Next Phase Readiness

- Typed OrdinalWeekday model ready for any future extensions (e.g., adding validation messages, documentation)
- All consumers updated and tested

---
*Phase: quick-260401-hz9*
*Completed: 2026-04-01*
