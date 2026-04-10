---
created: "2026-04-10T13:48:43.323Z"
title: Refactor DateFilter into discriminated union with typed date bounds
area: contracts
files:
  - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
  - src/omnifocus_operator/contracts/use_cases/list/__init__.py
  - src/omnifocus_operator/contracts/shared/repetition_rule.py:70-87
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/service/resolve_dates.py:118-252
  - src/omnifocus_operator/service/domain.py:187-191
  - tests/test_resolve_dates.py
  - tests/test_date_filter_contracts.py
  - tests/test_date_filter_constants.py
  - tests/test_cross_path_equivalence.py
  - tests/test_list_pipelines.py
  - tests/test_service_domain.py
---

## Problem

The current `DateFilter` model is a flat object with 5 optional `str | None` fields (`this`, `last`, `next`, `before`, `after`). Two problems compound each other:

**1. No structural validation — agents see a bad schema**

All mutual-exclusion rules are enforced at runtime via validators. The JSON Schema agents see exposes all 5 fields simultaneously with no per-field descriptions, no format constraints, and no structural hint that shorthand and absolute groups can't be mixed. Agents can easily construct invalid inputs (`{this: "2w"}`, `{this: "w", after: "..."}`, `{}`) that the schema doesn't prevent.

**2. `before`/`after` accept naive datetimes — silent tz bug**

The contract accepts any ISO datetime string (naive or tz-aware). Production `now` is UTC-aware. When a naive datetime reaches the resolver and is compared against tz-aware fields, Python raises `TypeError: can't compare offset-naive and offset-aware datetimes`. A defensive fix (WR-01) silently inherits `now.tzinfo` when the parsed datetime is naive — masking the problem. The write side (`add_tasks`, `edit_tasks`) already uses `AwareDatetime` to reject naive datetimes at the contract boundary; the filter side is inconsistent.

## Solution

Replace the flat `DateFilter` with a discriminated union of 4 models. Define `before`/`after` with typed bounds from day one — no placeholder `str | None`.

### Model structure

Following the `EndConditionSpec = EndByDateSpec | EndByOccurrencesSpec` pattern already in the codebase. Per model taxonomy `<noun>Filter` convention for read-side value objects nested in queries:

```python
class ThisPeriodFilter(QueryModel):
    __doc__ = THIS_PERIOD_FILTER_DOC
    this: Literal["d", "w", "m", "y"] = Field(description=THIS_PERIOD_UNIT)

class LastPeriodFilter(QueryModel):
    __doc__ = LAST_PERIOD_FILTER_DOC
    last: str = Field(description=LAST_PERIOD_DURATION)

class NextPeriodFilter(QueryModel):
    __doc__ = NEXT_PERIOD_FILTER_DOC
    next: str = Field(description=NEXT_PERIOD_DURATION)

class AbsoluteRangeFilter(QueryModel):
    __doc__ = ABSOLUTE_RANGE_FILTER_DOC
    before: Literal["now"] | AwareDatetime | date | None = Field(default=None, description=ABSOLUTE_RANGE_BEFORE)
    after:  Literal["now"] | AwareDatetime | date | None = Field(default=None, description=ABSOLUTE_RANGE_AFTER)

DateFilter = ThisPeriodFilter | LastPeriodFilter | NextPeriodFilter | AbsoluteRangeFilter
```

### Why `Literal["now"] | AwareDatetime | date | None` for `before`/`after`

All valid input shapes are covered:

| Agent sends | Branch matched | Result |
|---|---|---|
| `"now"` | `Literal["now"]` | ✅ |
| `"2026-04-01T14:00:00Z"` | `AwareDatetime` | ✅ |
| `"2026-04-01T14:00:00+02:00"` | `AwareDatetime` | ✅ |
| `"2026-04-01"` (date-only) | `date` | ✅ unambiguous, no tz needed |
| `"2026-04-01T14:00:00"` (naive) | fails all branches | ❌ rejected structurally |
| omitted | `None` | ✅ |

JSON Schema produced for each bound field:
```json
{
  "anyOf": [
    {"enum": ["now"]},
    {"type": "string", "format": "date-time"},
    {"type": "string", "format": "date"}
  ]
}
```

`format: "date-time"` and `format: "date"` are standard JSON Schema annotations — agents understand these natively.

### Descriptions (in `descriptions.py`)

Class docstrings: short, name the concept only. Field descriptions: terse, carry the detail.

```python
THIS_PERIOD_FILTER_DOC = "Filter to the current calendar period."
LAST_PERIOD_FILTER_DOC = "Filter to a recent window ending now."
NEXT_PERIOD_FILTER_DOC = "Filter to an upcoming window starting now."
ABSOLUTE_RANGE_FILTER_DOC = "Filter by explicit date bounds. Set before, after, or both."

THIS_PERIOD_UNIT = "Calendar period: d (today), w (this week), m (this month), y (this year)."
LAST_PERIOD_DURATION = "How far back from now. Count + unit: '3d', '2w', 'm'. Omit count for 1."
NEXT_PERIOD_DURATION = "How far ahead from now. Count + unit: '3d', '2w', 'm'. Omit count for 1."
ABSOLUTE_RANGE_BEFORE = "Upper bound (inclusive). ISO date, ISO datetime with timezone, or 'now'."
ABSOLUTE_RANGE_AFTER = "Lower bound (inclusive). ISO date, ISO datetime with timezone, or 'now'."
```

### What this structurally prevents (no validators needed)

- Mixed shorthand + absolute (`{this: "w", after: "..."}`)
- Empty object (`{}`)
- Multiple shorthand keys (`{this: "w", last: "3d"}`)
- Invalid `this` values (`this: "2w"`) — now a Literal enum
- Naive datetimes in `before`/`after` — fail all branches

### What still needs runtime validators

- `last`/`next` count > 0 and valid unit — move existing `_validate_duration` validator to `LastPeriodFilter` and `NextPeriodFilter`
- `this` bare unit check — move existing `_validate_this_unit` validator to `ThisPeriodFilter` (but this becomes redundant since `this: Literal["d","w","m","y"]` already enforces it structurally — remove the validator)
- `after <= before` ordering (when both are concrete, non-"now" values) — keep in `AbsoluteRangeFilter` as `@model_validator`
- `AbsoluteRangeFilter` at least one field set — keep as `@model_validator`; error message must be educative: explain what `before`/`after` accept, not just that one is required. Update or replace `err.DATE_FILTER_EMPTY` accordingly.

Module-level regex patterns (`_DATE_DURATION_PATTERN`, `_THIS_UNIT_PATTERN`) stay at module level.

### Input shape is unchanged

Agents send the same JSON. Schema is just tighter and now documented.

## Cascading changes

### `_date_filter.py`
- **Remove `DATE_FILTER_DOC` import**: Line 11 imports it; remove the import along with the constant in `descriptions.py`.
- **Add imports**: `from pydantic import AwareDatetime`, `from typing import Literal` (or `from __future__ import annotations` already covers it at type-check time — confirm at runtime usage).
- **Move validators to model classes**: `_validate_duration` → `LastPeriodFilter` and `NextPeriodFilter`; `_validate_this_unit` → `ThisPeriodFilter` (then remove it — `Literal` makes it redundant).
- **Dead error constants** (`errors.py`): `DATE_FILTER_MIXED_GROUPS`, `DATE_FILTER_MULTIPLE_SHORTHAND`, `DATE_FILTER_INVALID_THIS_UNIT`, `DATE_FILTER_INVALID_ABSOLUTE` are now unreachable — remove them.

### `descriptions.py`
- **Remove `DATE_FILTER_DOC`**: Orphaned — `DateFilter` is now a type alias.
- **Update field descriptions referencing "DateFilter" by name**: `DUE_FILTER_DESC`, `DEFER_FILTER_DESC`, `COMPLETED_FILTER_DESC`, `DROPPED_FILTER_DESC`, `ADDED_FILTER_DESC`, `MODIFIED_FILTER_DESC` say "Or use DateFilter for range/shorthand." Update to e.g. "Or use a period/range filter."
- **Add all new constants**: `THIS_PERIOD_FILTER_DOC`, `LAST_PERIOD_FILTER_DOC`, `NEXT_PERIOD_FILTER_DOC`, `ABSOLUTE_RANGE_FILTER_DOC`, `THIS_PERIOD_UNIT`, `LAST_PERIOD_DURATION`, `NEXT_PERIOD_DURATION`, `ABSOLUTE_RANGE_BEFORE`, `ABSOLUTE_RANGE_AFTER`.

### `contracts/use_cases/list/__init__.py`
- **Export the 4 concrete classes**: `ThispPeriodFilter`, `LastPeriodFilter`, `NextPeriodFilter`, `AbsoluteRangeFilter` must be exported alongside `DateFilter` (the type alias). `domain.py` needs to import `AbsoluteRangeFilter` at runtime for `isinstance`.

### `domain.py:187`
- **`isinstance(value, DateFilter)` is a correctness fix, not style**: Python raises `TypeError` at runtime when `DateFilter` is a union type alias (`X | Y | Z`). This must be changed to `isinstance(value, AbsoluteRangeFilter)`.
- **Import guard**: Move `AbsoluteRangeFilter` import out of the `TYPE_CHECKING` block — `isinstance` is a runtime check and needs the class available at runtime.

### `resolve_dates.py`
- **`_resolve_date_filter_obj` dispatch rewrite** (`resolve_dates.py:118+`): The function currently dispatches by probing fields (`if df.this is not None`, `if df.last is not None`, etc.). With the union, rewrite to `isinstance` dispatch:
  ```python
  if isinstance(df, ThisPeriodFilter): ...
  elif isinstance(df, LastPeriodFilter): ...
  elif isinstance(df, NextPeriodFilter): ...
  elif isinstance(df, AbsoluteRangeFilter): ...
  ```
- **`_parse_absolute_after`/`_parse_absolute_before`**: Receive `Literal["now"] | AwareDatetime | date` (not `str`). Rewrite to type dispatch — no `datetime.fromisoformat()`, no `_is_date_only()`.
- **Remove WR-01 defensive fix** (lines 228-229): Replace with `assert value.tzinfo is not None` when `isinstance(value, datetime)`. Contract guarantees this; assertion makes the invariant explicit.
- **`_parse_to_comparable` rewrite** (currently takes `str`, calls `fromisoformat`): Now receives `Literal["now"] | AwareDatetime | date | None`. Rewrite signature and body. For `date` vs `AwareDatetime` comparison, normalize `date` → midnight UTC (`datetime(d.year, d.month, d.day, tzinfo=UTC)`), consistent with how `_parse_absolute_after` handles date-only bounds.
- **Remove `_is_date_only`**: Dead code after typed dispatch.

### Tests
- **`test_resolve_dates.py`**: Make `NOW` fixture tz-aware (UTC). Check for broader impact — existing tests that construct naive datetimes directly may need updating too.
- **5 additional test files** need updating to reflect the union shape: `test_date_filter_contracts.py`, `test_date_filter_constants.py`, `test_cross_path_equivalence.py`, `test_list_pipelines.py`, `test_service_domain.py`.

### Schema shape
Each date field's `anyOf` goes from 2 branches (shortcut enum + DateFilter object) to 5 branches (shortcut enum + 4 filter objects). Verify rendered schema looks clean after implementation.

## Spike results (verified)

Both spikes completed — no open unknowns remain.

**1. Pydantic parsing order** — ✅ confirmed

| Input | Parsed as | Correct? |
|---|---|---|
| `"2026-04-01"` | `date(2026, 4, 1)` | ✅ lands on `date`, not consumed by `AwareDatetime` |
| `"2026-04-01T14:00:00Z"` | `datetime(..., tzinfo=UTC)` | ✅ |
| `"2026-04-01T14:00:00"` (naive) | `ValidationError` | ✅ rejected structurally |
| `"now"` | `str "now"` | ✅ `Literal["now"]` match |
| `None` / omitted | `None` | ✅ |

**2. Rendered JSON Schema** — ✅ clean

Each `before`/`after` field renders as:
```json
"anyOf": [
  {"const": "now", "type": "string"},
  {"format": "date-time", "type": "string"},
  {"format": "date", "type": "string"},
  {"type": "null"}
]
```

`Literal["now"]` renders as `const` (not `enum`) — cleaner. Three distinct branches, all using standard JSON Schema annotations agents understand natively. Massive improvement over the previous bare `{"type": "string"}`.
