# Quick Task 260401-hz9: Replace opaque on: dict with OrdinalWeekday model - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Task Boundary

Replace `on: dict[str, str] | None` with a typed `OrdinalWeekday` model so JSON Schema exposes valid ordinals and day names instead of opaque `additionalProperties: {type: string}`. MoveAction-style design: one Optional field per ordinal, wire format unchanged.

</domain>

<decisions>
## Implementation Decisions

### Model Shape: Multi-field (MoveAction-style)
- Each ordinal (first, second, third, fourth, fifth, last) is its own `DayName | None` field
- `DayName = Literal["monday", "tuesday", ..., "sunday", "weekday", "weekend_day"]`
- Wire format preserved: `{"last": "friday"}` — no breaking change
- JSON Schema shows all 6 optional fields with DayName enum values
- Exactly-one constraint enforced at runtime via `@model_validator`, same as MoveAction's `_exactly_one_key`
- Agent ergonomics: `{"last": "friday"}` reads as natural language vs `{"ordinal": "last", "day_name": "friday"}`

### Validator Semantics: At-most-one (not exactly-one)
- Validator allows 0 OR 1 fields set (rejects 2+)
- Reason: preserves graceful empty-normalization path in `domain.py`
- Agent sends `{"on": {}}` → OrdinalWeekday with all None → flows to domain.py → normalized to `on=None` + warning
- Teaching without failing: agent learns via warning in response, no retry needed
- `normalize_empty_specialization_fields()` check changes from `len(frequency.on) == 0` to checking all fields None

### Spec→Core Conversion: `.model_dump()` at boundaries
- Existing codebase pattern: never pass Spec instances to `model_validate()` expecting Core models
- Always go Spec → `.model_dump()` → dict → `Core.model_validate(dict)`
- Established at `service.py:461`: `Frequency.model_validate(spec.frequency.model_dump())`
- Applies to `merge_frequency()` AND `_build_frequency_from_edit_spec()` — audit ALL paths where `FrequencyEditSpec.on` flows into `Frequency` construction

### Model Taxonomy Compliance
- Core `OrdinalWeekday` in `models/` — inherits `OmniFocusBaseModel`
- Write-side `OrdinalWeekdaySpec` in `contracts/shared/` — inherits `CommandModel` (extra="forbid")
- Same field structure, different base classes per model-taxonomy.md
- `DayName` type alias lives in `models/repetition_rule.py` (alongside existing `DayCode`, `FrequencyType`)

### Shared Logic: Standalone functions
- `normalize_day_name()` and `check_at_most_one_ordinal()` as standalone functions
- Same pattern as existing `normalize_day_codes()` / `validate_on_dates()`
- Error messages in `agent_messages/errors.py`
- `normalize_on()` function removed entirely — replaced by model's own validators
- `_normalize_on` wrappers on FrequencyAddSpec/FrequencyEditSpec removed

### Output Schema Safety
- `@model_serializer` on core model to exclude None fields → output stays `{"last": "friday"}`
- Same pattern as MoveAction — should be safe
- Hard gate: run `test_output_schema.py` after implementation to verify

</decisions>

<specifics>
## Specific Ideas

- Error message for at-most-one validator: `"on must specify exactly one ordinal (e.g. {\"last\": \"friday\"}), got N keys"`
- `@field_validator` on all 6 fields for day name case normalization (`"Friday"` → `"friday"`)
- Builder (`_build_byday_positional`) extracts the single set field from OrdinalWeekday instead of dict iteration
- Parser constructs `OrdinalWeekday(last="friday")` instead of `{"last": "friday"}`

</specifics>

<canonical_refs>
## Canonical References

- `docs/model-taxonomy.md` — model naming and base class conventions
- `contracts/shared/actions.py:59-83` — MoveAction `_exactly_one_key` pattern (reference implementation)
- `service/domain.py:279-321` — `merge_frequency()` merge logic
- `service/service.py:461` — Spec→Core `.model_dump()` pattern
- `agent_messages/errors.py:76-89` — existing repetition error messages

</canonical_refs>
