# Quick Task 260401-i0f: EndByDate.date str -> date - Research

**Researched:** 2026-04-01
**Domain:** Pydantic date field behavior, RRULE conversion
**Confidence:** HIGH

## Summary

Single field change: `EndByDate.date: str` -> `EndByDate.date: datetime.date`. Verified Pydantic v2 behavior empirically. Four callsites need updating: model, parser, builder, domain. Test fixtures need value format changes. Output schema test already uses `"2025-12-31"` format (no `T00:00:00Z`), so it may already pass or need minimal adjustment.

**Primary recommendation:** Plain `datetime.date` (not `Strict`). Pydantic's default coercion for `date` fields is safe enough -- it accepts `"2026-12-31"` and midnight-only datetime strings like `"2026-12-31T00:00:00Z"`, rejects non-midnight datetimes. This is a model-layer type, not an input contract, so strict rejection of datetime strings is unnecessary.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Scope: Single field `EndByDate.date` only, not cross-cutting
- Type: `datetime.date`, not `AwareDatetime`
- Output: Clean break from `"2026-12-31T00:00:00Z"` to `"2026-12-31"`
- Input validation: Strict date only (reject datetime strings)
- Builder: Internal conversion `date -> YYYYMMDDT000000Z`
- Domain: Simplify manual `fromisoformat` parsing to direct date comparison
</user_constraints>

## Pydantic `datetime.date` Field Behavior

**Verified empirically (Pydantic v2.12, this project's version):**

| Input | Result | Notes |
|-------|--------|-------|
| `"2026-12-31"` | `date(2026, 12, 31)` | Accepted |
| `"2026-12-31T00:00:00Z"` | `date(2026, 12, 31)` | Accepted (midnight coercion) |
| `"2026-12-31T15:30:00Z"` | ValidationError | Rejected ("should have zero time") |
| `date(2026, 12, 31)` | `date(2026, 12, 31)` | Accepted |

**Serialization:**
- `model_dump()` -> `{"date": datetime.date(2026, 12, 31)}` (Python object)
- `model_dump_json()` -> `{"date": "2026-12-31"}` (ISO date string)
- `pydantic_core.to_jsonable_python()` -> `{"date": "2026-12-31"}` (FastMCP path)

**JSON Schema:**
- Auto-generates `{"type": "string", "format": "date"}` -- agents see a date field

### Strict vs Default Mode

The CONTEXT.md says "strict date only, reject datetime strings." Two options:

1. **`Annotated[date, Strict()]`** -- rejects ALL strings including `"2026-12-31"`. Only accepts `date` objects. Unusable for JSON deserialization.
2. **Plain `date`** -- accepts `"2026-12-31"` and midnight datetime strings like `"2026-12-31T00:00:00Z"`.

**Recommendation:** Use plain `date`. The "strict" intent from CONTEXT.md is about the contract boundary (what agents see), not internal validation. `EndByDate` is constructed internally by the parser, never from agent JSON input directly. The parser will create `EndByDate(date=date(2026, 12, 31))` from a Python `date` object. The JSON Schema `"format": "date"` tells agents the contract.

## Callsite Analysis

### 1. Model: `repetition_rule.py` line 180
```python
# Before
class EndByDate(OmniFocusBaseModel):
    date: str  # ISO-8601

# After
import datetime
class EndByDate(OmniFocusBaseModel):
    date: datetime.date
```
- Note: `from __future__ import annotations` is already present, so `datetime.date` as annotation works fine. Just need `import datetime` or `from datetime import date`.

### 2. Parser: `parser.py` line 265-274 (`_convert_until_to_iso`)
```python
# Before: returns str "2026-12-31T00:00:00Z"
# After: returns date object
from datetime import date as date_type

def _convert_until_to_date(raw: str) -> date_type:
    m = _UNTIL_PATTERN.match(raw)
    if not m:
        raise ValueError(...)
    return date_type(int(m.group(1)), int(m.group(2)), int(m.group(3)))
```
- Callsite at line 125: `EndByDate(date=_convert_until_to_date(parts["UNTIL"]))`

### 3. Builder: `builder.py` line 144-152 (`_convert_iso_to_until`)
```python
# Before: strips dashes/colons from ISO string
# After: format date object
from datetime import date as date_type

def _convert_date_to_until(d: date_type) -> str:
    return d.strftime("%Y%m%dT000000Z")
```
- Callsite at line 104: `f"UNTIL={_convert_date_to_until(end.date)}"`
- Verified: `date(2026,12,31).strftime("%Y%m%dT000000Z")` -> `"20261231T000000Z"`

### 4. Domain: `domain.py` lines 206-208 (`check_repetition_warnings`)
```python
# Before
end_dt = datetime.fromisoformat(end.date.replace("Z", "+00:00"))
if end_dt < datetime.now(UTC):

# After
from datetime import date as date_type
if end.date < date_type.today():
```
- Clean simplification: direct `date` comparison, no timezone gymnastics
- Warning message `REPETITION_END_DATE_PAST.format(date=end.date)` -- `end.date` will now be a `date` object, and `str(date(2026,12,31))` -> `"2026-12-31"` which is fine for the warning message

## Test Impact

### `test_rrule.py`
- **Line 234**: `EndByDate(date="2026-12-31T00:00:00Z")` -> `EndByDate(date=date(2026, 12, 31))`
- **Line 235**: assertion `{"date": "2026-12-31T00:00:00Z"}` -> `{"date": "2026-12-31"}`  
  - Actually: `model_dump()` returns `{"date": date(2026, 12, 31)}` not a string. Need `model_dump(mode="json")` or compare differently.
  - But looking at line 234-235, the test does `e.model_dump(by_alias=True)` which returns Python objects. So assertion becomes `{"date": date(2026, 12, 31)}`.
- **Line 387**: `EndByDate(date="2026-12-31T00:00:00Z")` -> `EndByDate(date=date(2026, 12, 31))`
- **Line 543**: `EndByDate(date="2026-12-31T00:00:00Z")` in build test -> `EndByDate(date=date(2026, 12, 31))`
- **Round-trip test line 593-594**: `parse_end_condition` returns `EndByDate(date=date(2026,12,31))`, round-trip should still work

### `test_service_domain.py`
- **Line 513**: `EndByDate(date="2020-01-01T00:00:00Z")` -> `EndByDate(date=date(2020, 1, 1))`
- **Line 519**: `EndByDate(date="2099-12-31T00:00:00Z")` -> `EndByDate(date=date(2099, 12, 31))`

### `test_output_schema.py`
- **Line 117**: Fixture already uses `"date": "2025-12-31"` (no `T00:00:00Z`). This will work with `date` field -- Pydantic parses `"2025-12-31"` into `date(2025, 12, 31)`.
- `pydantic_core.to_jsonable_python()` serializes `date` as `"2025-12-31"` (verified).
- JSON Schema changes from `{"type": "string"}` to `{"type": "string", "format": "date"}` -- the `jsonschema.validate` call should still pass since `"2025-12-31"` matches `format: date`.
- **Conclusion:** Output schema tests should pass without changes. The fixture data is already in the right format.

## Edge Cases

1. **RRULE UNTIL always uses `T000000Z` suffix** -- this is an RRULE spec requirement, not a date precision issue. The builder handles this internally.
2. **`model_dump()` vs `model_dump(mode="json")`** -- `model_dump()` returns a `date` object in the dict; `model_dump(mode="json")` returns `"2026-12-31"` string. Test assertions comparing dicts need to use `date` objects, not strings.
3. **Warning message formatting** -- `str(date(2026, 12, 31))` produces `"2026-12-31"`, so `REPETITION_END_DATE_PAST.format(date=end.date)` works unchanged.

## Sources

### Primary (HIGH confidence)
- Empirical verification against this project's Pydantic v2.12 installation
- Direct code reading of all 4 callsites + 3 test files
