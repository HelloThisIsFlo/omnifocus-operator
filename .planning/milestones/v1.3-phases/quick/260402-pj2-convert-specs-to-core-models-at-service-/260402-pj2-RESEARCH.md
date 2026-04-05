# Quick Task 260402-pj2: Convert Specs to Core Models at Service Boundary - Research

**Researched:** 2026-04-02
**Domain:** Service layer type boundary cleanup
**Confidence:** HIGH

## Summary

Traced all call sites where `FrequencyAddSpec` and `EndConditionSpec` leak past the pipeline boundary into `payload.py` and `builder.py`. Found a real bug: the edit pipeline's `end` variable can hold `EndByDateSpec` (contract) while `domain.py:check_repetition_warnings` checks `isinstance(end, EndByDate)` (core model) -- the warning for "end date in past" silently fails on edit operations.

**Primary recommendation:** Create `service/convert.py` with two pure functions, call them in both pipelines, then narrow all downstream signatures to core-only types.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- New `service/convert.py` module for spec-to-core conversion
- Eliminate the Frequency round-trip in add pipeline (spec->core->spec is wrong)
- Update `docs/architecture.md` package structure and reinforce `docs/model-taxonomy.md`
- FrequencyEditSpec in domain.py:merge_frequency() is NOT in scope

### Specific Implementation
- `convert.py` contains: `frequency_from_spec(FrequencyAddSpec) -> Frequency` and `end_condition_from_spec(EndConditionSpec | None) -> EndCondition | None`
- `payload.py::_build_repetition_rule_payload` changes to core-only: `frequency: Frequency`, `end: EndCondition | None`
- `builder.py::build_rrule` changes similarly -- removes union types, restores `isinstance` dispatch
</user_constraints>

## Leak Point Inventory

### 1. Add pipeline (`service.py:448-472`)
- **Line 461**: `Frequency.model_validate(spec.frequency.model_dump())` -- correctly converts to core Frequency
- **Line 468**: `FrequencyAddSpec.model_validate(normalized_freq.model_dump())` -- WRONG: converts back to spec. This is the round-trip to eliminate
- **Line 465-472**: After normalization, the pipeline rebuilds the command with a new spec instead of keeping the core Frequency
- **The `end` field**: stays as `EndConditionSpec` on `command.repetition_rule.end`, flows to `_build_repetition_rule_payload` at line 65-70 of payload.py

### 2. Edit pipeline (`service.py:562-663`)
- **Line 596-598**: `end = spec.end` -- assigns `EndConditionSpec` (from `RepetitionRuleEditSpec.end`) to `end: EndCondition | None` type annotation. The annotation lies; the value is `EndConditionSpec`.
- **Line 639**: `self._domain.check_repetition_warnings(end=end, task=self._task)` -- passes `EndConditionSpec` to domain.py
- **BUG in domain.py:207**: `isinstance(end, EndByDate)` fails when `end` is `EndByDateSpec` because they're different classes. The "end date in past" warning is never emitted for edit operations.
- **Line 636**: `frequency` is already core `Frequency` here (from `_merge_frequency` or `_build_frequency_from_edit_spec`) -- no leak
- **Line 661**: `_build_repetition_rule_payload(frequency, schedule, based_on, end)` -- `frequency` is core, `end` is spec (leak)

### 3. `payload.py:118-134` (`_build_repetition_rule_payload`)
- **Line 120**: `frequency: Frequency | FrequencyAddSpec` -- union signature
- **Line 123**: `end: EndCondition | EndConditionSpec | None` -- union signature
- **Line 126**: Passes both to `build_rrule(frequency, end)`
- Called from: `build_add` (line 65, via command fields) and edit pipeline (line 661, directly)

### 4. `builder.py:69-71` (`build_rrule`)
- **Line 70**: `frequency: Frequency | FrequencyAddSpec` -- union signature
- **Line 71**: `end: EndByDate | EndByOccurrences | EndConditionSpec | None` -- union signature
- **Line 107-109**: `hasattr(end, "occurrences")` / `hasattr(end, "date")` -- duck-typing to handle both spec and core types

### 5. No other leak sites
- `domain.py:repetition_payload_matches_existing` uses `existing.frequency`/`existing.end` which are already core models
- `domain.py:merge_frequency` takes `FrequencyEditSpec` + `Frequency`, outputs `Frequency` -- this is the edit-only merge, correctly out of scope
- `domain.py:normalize_empty_specialization_fields` takes/returns `Frequency` -- already core-only

## Field Mapping Verification

Conversion via `model_validate(spec.model_dump())` is trivial -- fields are identical:

| Spec field | Core field | Type match |
|-----------|------------|------------|
| `FrequencyAddSpec.type` | `Frequency.type` | `Literal[...]` -> `str` (widening, safe) |
| `FrequencyAddSpec.interval` | `Frequency.interval` | `Annotated[int, Field(ge=1)]` -> `int` (widening, safe) |
| `FrequencyAddSpec.on_days` | `Frequency.on_days` | `list[DayCode] \| None` -> `list[str] \| None` (widening, safe) |
| `FrequencyAddSpec.on` | `Frequency.on` | `OrdinalWeekdaySpec \| None` -> `OrdinalWeekday \| None` (same fields, model_dump round-trips) |
| `FrequencyAddSpec.on_dates` | `Frequency.on_dates` | `list[OnDate] \| None` -> `list[int] \| None` (widening, safe) |
| `EndByDateSpec.date` | `EndByDate.date` | `date` -> `date` (identical) |
| `EndByOccurrencesSpec.occurrences` | `EndByOccurrences.occurrences` | `Annotated[int, Field(ge=1)]` -> `int` (widening, safe) |

All conversions widen types (contract constraints -> plain types). No data loss. `model_dump()` + `model_validate()` works because field names and shapes are identical.

**End condition dispatch**: `EndConditionSpec = EndByDateSpec | EndByOccurrencesSpec`. The conversion function needs to check which variant and construct the corresponding core type. Can use `isinstance` or check for field presence.

## Test Impact

### Tests that use FrequencyAddSpec in payload/builder context (need updating)
- `tests/test_service_payload.py` (lines 266-352): 7 tests construct `RepetitionRuleAddSpec` with `FrequencyAddSpec` and call `build_add` -- these test the full flow through `_build_repetition_rule_payload`. After the change, the conversion happens in the pipeline before payload.py, so these tests still pass without changes (they test `build_add` which takes a `Command` -- the conversion is upstream)
- `tests/test_rrule.py` (lines 212-594): Already uses core `Frequency`, `EndByDate`, `EndByOccurrences` -- no changes needed

### Tests that will NOT break
- `tests/test_service.py`: Uses `FrequencyAddSpec` to construct commands -- this is correct, specs are the contract input. The conversion happens inside the pipeline.
- `tests/test_contracts_repetition_rule.py`: Tests contract model validation -- unaffected
- `tests/test_validation_repetition.py`: Tests spec validators -- unaffected
- `tests/test_output_schema.py`: Tests JSON Schema of specs -- unaffected

### No tests assert on union signatures or hasattr behavior
- No test directly tests `_build_repetition_rule_payload` with a `FrequencyAddSpec` argument -- it's always called through `build_add` which wraps the full command
- No test for `build_rrule` passes spec types -- all use core models

## Import Changes per File

### New file: `service/convert.py`
- From `contracts.shared.repetition_rule`: `FrequencyAddSpec`, `EndByDateSpec`, `EndByOccurrencesSpec`, `EndConditionSpec`
- From `models.repetition_rule`: `Frequency`, `EndByDate`, `EndByOccurrences`, `EndCondition`

### `service/service.py`
- ADD: `from omnifocus_operator.service.convert import frequency_from_spec, end_condition_from_spec`
- REMOVE: `from omnifocus_operator.contracts.shared.repetition_rule import FrequencyAddSpec` (line 29)
- REMOVE: `from omnifocus_operator.models.repetition_rule import Frequency` (line 47) -- unless still needed elsewhere
  - CHECK: `Frequency` is used at line 461 directly. After refactor, conversion moves to `convert.py`, so the import can go.

### `service/payload.py`
- REMOVE from TYPE_CHECKING: `EndConditionSpec`, `FrequencyAddSpec` (lines 26-27)
- The `Frequency` and `EndCondition` imports stay (already in TYPE_CHECKING block at lines 32)
  - CHECK: `Frequency` and `EndCondition` are NOT currently imported. They need to be ADDED to TYPE_CHECKING.
  - Current TYPE_CHECKING imports: `FrequencyAddSpec`, `EndConditionSpec`, `AddTaskCommand`, `EditTaskCommand`, `BasedOn`, `Schedule`, `EndCondition`, `Frequency`
  - After: Remove `FrequencyAddSpec`, `EndConditionSpec`. Keep `EndCondition`, `Frequency`.

### `rrule/builder.py`
- REMOVE from TYPE_CHECKING: `EndConditionSpec`, `FrequencyAddSpec` (lines 20-21)
- The remaining TYPE_CHECKING imports (`EndByDate`, `EndByOccurrences`, `Frequency`, `OrdinalWeekday`) stay
- Signature changes: remove union types, use `EndCondition | None` for end parameter

## Bug Fix Bonus

Converting `EndConditionSpec` to `EndCondition` at the service boundary fixes the silent bug in `domain.py:207`:
- Before: `isinstance(EndByDateSpec_instance, EndByDate)` -> `False` -> warning never emitted on edits
- After: `isinstance(EndByDate_instance, EndByDate)` -> `True` -> warning correctly emitted

## Sources

### Primary (HIGH confidence)
- Direct code analysis of `service.py`, `payload.py`, `builder.py`, `domain.py`
- Direct code analysis of `models/repetition_rule.py`, `contracts/shared/repetition_rule.py`
- Test file analysis of `test_service_payload.py`, `test_rrule.py`, `test_service.py`
