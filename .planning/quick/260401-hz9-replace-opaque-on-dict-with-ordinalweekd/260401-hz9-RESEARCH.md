# Quick Task 260401-hz9: Replace opaque on: dict with OrdinalWeekday - Research

**Researched:** 2026-04-01
**Domain:** Pydantic model replacement, repetition rule subsystem
**Confidence:** HIGH

## Summary

Replace `on: dict[str, str] | None` with typed `OrdinalWeekday` / `OrdinalWeekdaySpec` models across 6 source files and 6 test files. The change is self-contained within the rrule/repetition subsystem.

**Key finding:** No `@model_serializer` needed. The existing `RepetitionRule._serialize_frequency` uses `freq.model_dump(exclude_defaults=True)` which is recursive in Pydantic v2 -- nested `OrdinalWeekday` fields defaulting to `None` are automatically excluded. Verified empirically.

**Primary recommendation:** Follow the MoveAction validator pattern but skip the `@model_serializer` -- rely on the existing `exclude_defaults=True` chain.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Model shape: multi-field MoveAction-style, one `DayName | None` field per ordinal
- `DayName = Literal["monday", ..., "sunday", "weekday", "weekend_day"]`
- Validator: at-most-one (not exactly-one) -- preserves empty-normalization path
- Spec->Core conversion via `.model_dump()` at boundaries
- Core `OrdinalWeekday` in `models/` (OmniFocusBaseModel), write-side `OrdinalWeekdaySpec` in `contracts/shared/` (CommandModel)
- Shared standalone functions: `normalize_day_name()`, `check_at_most_one_ordinal()`
- `normalize_on()` function removed entirely
- Error messages in `agent_messages/errors.py`

### Specific Ideas
- Error: `"on must specify exactly one ordinal (e.g. {\"last\": \"friday\"}), got N keys"`
- `@field_validator` on all 6 fields for case normalization
- Builder extracts single set field from OrdinalWeekday instead of dict iteration
- Parser constructs `OrdinalWeekday(last="friday")` instead of `{"last": "friday"}`
</user_constraints>

## Exhaustive Code Path Inventory

### Source files that touch `on: dict[str, str]`

| # | File | Lines | What it does with `on` | Change needed |
|---|------|-------|------------------------|---------------|
| 1 | `models/repetition_rule.py` | L42-53, L81-93, L105-129, L145, L163-166 | Core `Frequency.on` field, `normalize_on()` function, `check_frequency_cross_type_fields()` param, `_VALID_ORDINALS`/`_VALID_DAY_NAMES` constants | Replace field type, remove `normalize_on()`, add `OrdinalWeekday` model, update cross-type check signature |
| 2 | `contracts/shared/repetition_rule.py` | L59, L82-85, L99 | `FrequencyAddSpec.on` field + `_normalize_on` validator, `FrequencyEditSpec.on` field | Replace field types with `OrdinalWeekdaySpec`, remove `_normalize_on` validator |
| 3 | `rrule/parser.py` | L210, L244 | Constructs `on={ordinal: day_name}` dict | Construct `OrdinalWeekday(last="friday")` instead |
| 4 | `rrule/builder.py` | L95-96, L117-141 | `_build_byday_positional(on: dict[str, str])` iterates dict | Extract single set field from `OrdinalWeekday` model |
| 5 | `service/domain.py` | L262-264, L302-319 | `normalize_empty_specialization_fields()` checks `len(frequency.on) == 0`; `merge_frequency()` merges `on` field | Change emptiness check to "all fields None"; merge produces dict then validates |
| 6 | `service/service.py` | L701 | `_build_frequency_from_edit_spec()` iterates `("on_days", "on", "on_dates")` | No structural change needed -- `getattr(edit_spec, "on")` still works with new type |
| 7 | `agent_messages/errors.py` | L80-89 | `REPETITION_INVALID_ORDINAL`, `REPETITION_INVALID_DAY_NAME` messages | Keep or replace with at-most-one validator message |

### Test files that reference `on`

| # | File | Count | Categories |
|---|------|-------|------------|
| 1 | `tests/test_rrule.py` | ~18 sites | Constructing `Frequency(on={...})`, asserting `result.on == {...}`, `build_rrule` with `on` |
| 2 | `tests/test_contracts_repetition_rule.py` | ~10 sites | Constructing `FrequencyAddSpec(on={...})`, `FrequencyEditSpec(on={...})`, `is_set(spec.on)` |
| 3 | `tests/test_service_domain.py` | ~8 sites | `Frequency(on={})` empty check, `FrequencyEditSpec(on={...})` merge tests |
| 4 | `tests/test_service.py` | ~7 sites | `FrequencyAddSpec(on={...})`, `FrequencyEditSpec(on={...})`, asserting `task.repetition_rule.frequency.on` |
| 5 | `tests/test_validation_repetition.py` | ~8 sites | Constructing `Frequency(on={...})`, invalid ordinal/day tests, `on=None` |
| 6 | `tests/test_output_schema.py` | ~3 sites | `"on": {"second": "tuesday"}` in fixture, schema property assertion |

**Golden master snapshots:** NOT affected. Snapshots store raw `ruleString` from OmniFocus; `on` is only produced at parse time.

## Serialization Chain (Critical Finding)

**No `@model_serializer` needed on `OrdinalWeekday`.**

The serialization chain for output is:
1. `RepetitionRule._serialize_frequency` calls `freq.model_dump(exclude_defaults=True, by_alias=True)`
2. Pydantic v2's `exclude_defaults=True` is **recursive** -- it applies to nested models
3. `OrdinalWeekday(last="friday")` with all fields defaulting to `None` serializes as `{"last": "friday"}`

**Empirically verified:**
```python
class Inner(BaseModel):
    a: str | None = None
    b: str | None = None
class Outer(BaseModel):
    inner: Inner | None = None

Outer(inner=Inner(b='hello')).model_dump(exclude_defaults=True)
# → {'inner': {'b': 'hello'}}  ✓
```

**JSON Schema also verified:** `OrdinalWeekday` with `DayName | None` fields generates schema with `enum` constraints per field. Serialized `{"last": "friday"}` validates against this schema (all fields are optional with `default: null`).

This avoids the `@model_serializer` schema erasure problem that `test_output_schema.py` explicitly guards against.

## MoveAction Pattern Reference

`contracts/shared/actions.py:59-83` -- the reference implementation:
- Uses `PatchOrNone[str]` fields with `UNSET` defaults (write-side CommandModel)
- `@model_validator(mode="after")` with `_exactly_one_key`
- Counts set fields via `sum(1 for v in (...) if is_set(v))`

**Difference for OrdinalWeekday:**
- Core model uses `DayName | None = None` (not UNSET -- it's a read model)
- Spec model uses `DayName | None = None` with CommandModel base (extra="forbid")
- Validator: at-most-one (not exactly-one) per CONTEXT.md decision
- Counting: `sum(1 for f in fields if f is not None)` (simpler than `is_set()`)

## Empty Dict Edge Case Flow

Current flow for `on={}`:
1. Agent sends `{"on": {}}` in add/edit payload
2. `FrequencyAddSpec(on={})` or `FrequencyEditSpec(on={})` -- passes (no validation on empty dict)
3. `Frequency.model_validate({"type": "monthly", "on": {}})` -- passes (normalize_on returns `{}`)
4. `domain.py:262` -- `normalize_empty_specialization_fields()` checks `len(frequency.on) == 0` -> sets `on=None` + warning

New flow for `on=OrdinalWeekday()` (all None):
1. Agent sends `{"on": {}}` in add/edit payload
2. `OrdinalWeekdaySpec()` or `OrdinalWeekday()` -- passes at-most-one (0 fields set = OK)
3. `domain.py` -- check changes to: all fields None -> sets `on=None` + warning
4. Same behavior, different check: `all(getattr(freq.on, f) is None for f in ordinal_fields)`

## `check_frequency_cross_type_fields` Signature Update

Current: `on: dict[str, str] | None`
New: `on: OrdinalWeekday | None`

The function only checks `on is not None` and `on is not None and on_dates is not None`. No dict-specific operations. Type change is safe.

## `_build_byday_positional` Refactor

Current signature: `def _build_byday_positional(on: dict[str, str]) -> str`
- Uses `len(on)`, `next(iter(on.items()))` to extract single key-value

New approach: extract the single set field from OrdinalWeekday:
```python
def _build_byday_positional(on: OrdinalWeekday) -> str:
    # Find the one non-None field
    ordinal, day_name = next(
        (name, val) for name, val in [
            ("first", on.first), ("second", on.second), ...
        ] if val is not None
    )
```

## `merge_frequency` Impact

`domain.py:302` -- iterates `("on_days", "on", "on_dates")` with `getattr(edit_spec, field_name)` and `getattr(existing, field_name)`:
- `merged[field_name] = edit_val` puts the raw value (OrdinalWeekday or OrdinalWeekdaySpec) into dict
- `Frequency.model_validate(merged)` at L321 -- this works because Pydantic accepts model instances for model-typed fields
- **BUT**: `merged["on"]` from edit_spec is `OrdinalWeekdaySpec`, and Frequency expects `OrdinalWeekday`
- The `.model_dump()` boundary pattern handles this: spec -> dict -> core model validation

Actually, looking more carefully at `merge_frequency`:
- L302-307: builds `merged` dict with raw values from either edit_spec or existing
- L321: `Frequency.model_validate(merged)` -- Pydantic will coerce `OrdinalWeekdaySpec` -> `OrdinalWeekday` IF the fields match (they do by design)
- Pydantic v2 accepts dicts and model instances for nested model fields, so this should work
- **Verify empirically during implementation** -- if it doesn't, add `.model_dump()` for the `on` field specifically

## Common Pitfalls

### Pitfall 1: Forgetting to update `__all__` exports
- `models/repetition_rule.py` exports `normalize_on` -- must remove and add `OrdinalWeekday`, `DayName`
- `contracts/shared/repetition_rule.py` imports `normalize_on` -- must remove

### Pitfall 2: `model_dump()` boundary at merge
- `merge_frequency()` puts values into a dict then calls `Frequency.model_validate()`
- If OrdinalWeekdaySpec (CommandModel) is placed in dict as-is, Pydantic might reject extra="forbid" vs regular model mismatch
- Safe path: ensure the merged dict contains plain dicts (via `.model_dump()`) not model instances for `on`

### Pitfall 3: test_output_schema.py fixture update
- `test_output_schema.py:112` has `"on": {"second": "tuesday"}` as raw dict in fixture
- This will still work -- Pydantic accepts dicts for model-typed fields
- But the schema assertion at L426 (`assert "on" in props`) now needs to check for OrdinalWeekday structure, not just existence

### Pitfall 4: FrequencyEditSpec `on` type
- Currently `PatchOrClear[dict[str, str]]` -- supports UNSET / None / dict value
- New: `PatchOrClear[OrdinalWeekdaySpec]` -- supports UNSET / None / OrdinalWeekdaySpec value
- The `is_set()` checks in domain.py and service.py work the same way

## Project Constraints (from CLAUDE.md)

- **SAFE-01/02**: No automated tests touch the real Bridge. All testing via InMemoryBridge/SimulatorBridge.
- **Model taxonomy**: Core models in `models/` (OmniFocusBaseModel), write-side in `contracts/` (CommandModel). Read `docs/model-taxonomy.md` before creating models.
- **Output schema**: Run `uv run pytest tests/test_output_schema.py -x -q` after any model change that appears in tool output.
- **Dev commands**: Always use `uv run pytest`, never bare `pytest`.

## Sources

### Primary (HIGH confidence)
- Direct code inspection of all 7 source files and 6 test files
- Empirical Pydantic v2 verification: `model_dump(exclude_defaults=True)` recursion and JSON Schema generation
- `docs/model-taxonomy.md` for naming conventions

## Metadata

**Confidence breakdown:**
- Code paths: HIGH -- exhaustive grep + manual read of every file
- Serialization safety: HIGH -- empirically verified with Pydantic v2
- Test impact: HIGH -- complete inventory with line numbers
- Merge flow: MEDIUM -- Pydantic coercion of Spec->Core at model_validate needs runtime verification

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable codebase, no external deps)
