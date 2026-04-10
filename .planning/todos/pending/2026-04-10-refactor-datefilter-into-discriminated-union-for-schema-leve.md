---
created: "2026-04-10T12:01:58.691Z"
title: Refactor DateFilter into discriminated union for schema-level validation
area: contracts
files:
  - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
  - src/omnifocus_operator/contracts/shared/repetition_rule.py:70-87
  - src/omnifocus_operator/agent_messages/descriptions.py
---

## Problem

The current `DateFilter` model is a flat object with 5 optional `str | None` fields (`this`, `last`, `next`, `before`, `after`). All mutual-exclusion rules are enforced at runtime via validators. The JSON Schema agents see exposes all 5 fields simultaneously with no per-field descriptions, no format constraints, and no structural hint that shorthand and absolute groups can't be mixed.

This means agents can easily construct invalid inputs (`{this: "2w"}`, `{this: "w", after: "..."}`, `{}`) that the schema doesn't prevent. Error messages are good, but prevention is better.

Additionally, `DateFilter` fields have no `Field(description=...)` at all — agents see bare `string | null` with zero guidance on what values are valid.

## Solution

Replace the flat `DateFilter` with a discriminated union of 4 models, following the proven `EndConditionSpec = EndByDateSpec | EndByOccurrencesSpec` pattern already in the codebase.

### Naming

Per model taxonomy `<noun>Filter` convention for read-side value objects nested in queries:

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
    before: str | None = Field(default=None, description=ABSOLUTE_RANGE_BEFORE)
    after: str | None = Field(default=None, description=ABSOLUTE_RANGE_AFTER)

DateFilter = ThisPeriodFilter | LastPeriodFilter | NextPeriodFilter | AbsoluteRangeFilter
```

### Descriptions (in `descriptions.py`)

```python
# --- Date Filter Branch Models ---

THIS_PERIOD_FILTER_DOC = (
    "Filter to the current calendar period. "
    "d = today, w = this week, m = this month, y = this year."
)

LAST_PERIOD_FILTER_DOC = (
    "Filter to a recent window ending now. "
    "Duration: optional count + unit (e.g. '3d', '2w', 'm'). Omit count for 1."
)

NEXT_PERIOD_FILTER_DOC = (
    "Filter to an upcoming window starting now. "
    "Duration: optional count + unit (e.g. '3d', '2w', 'm'). Omit count for 1."
)

ABSOLUTE_RANGE_FILTER_DOC = (
    "Filter by explicit date bounds. Set before, after, or both. "
    "Accepts ISO date ('2026-04-01'), ISO datetime ('2026-04-01T14:00:00Z'), or 'now'."
)

# Field descriptions

THIS_PERIOD_UNIT = "Calendar period: d (today), w (this week), m (this month), y (this year)."

LAST_PERIOD_DURATION = (
    "How far back from now. Optional count + unit: "
    "'3d' (3 days), '2w' (2 weeks), 'm' (1 month). Omit count for 1."
)

NEXT_PERIOD_DURATION = (
    "How far ahead from now. Optional count + unit: "
    "'3d' (3 days), '2w' (2 weeks), 'm' (1 month). Omit count for 1."
)

ABSOLUTE_RANGE_BEFORE = "Upper bound (exclusive). ISO date, ISO datetime with timezone, or 'now'."

ABSOLUTE_RANGE_AFTER = "Lower bound (inclusive). ISO date, ISO datetime with timezone, or 'now'."
```

### What this structurally prevents (no validators needed)

- Mixed shorthand + absolute (`{this: "w", after: "..."}`)
- Empty object (`{}`)
- Multiple shorthand keys (`{this: "w", last: "3d"}`)
- Invalid `this` values (`this: "2w"`) — now a Literal enum

### What still needs runtime validators

- `last`/`next` count > 0 and valid unit
- `before`/`after` valid ISO datetime or "now"
- `after <= before` ordering
- `AbsoluteRangeFilter` at least one field set

### Input shape is unchanged

Agents send the same JSON, schema is just tighter.

## Cascading changes

- **`DATE_FILTER_DOC` becomes orphaned**: `DateFilter` is now a type alias, not a class — the old docstring has no home. The branch docstrings replace it entirely. Remove `DATE_FILTER_DOC`.
- **Field descriptions reference "DateFilter" by name**: `DUE_FILTER_DESC`, `DEFER_FILTER_DESC`, etc. say "Or use DateFilter for range/shorthand." After the refactor, "DateFilter" isn't a named concept agents see in the schema — each branch appears directly in the `anyOf`. Update these descriptions to reference the actual options (e.g. "Or use a period/range filter").
- **Schema shape change**: Each date field's `anyOf` goes from 2 branches (shortcut enum + DateFilter object) to 5 branches (shortcut enum + 4 filter objects). Each branch is small and well-described, so this is a net improvement — but worth verifying the rendered schema looks clean.
## Spike before implementing

Confirm Pydantic smart union error messages stay clean when no branch matches. E.g., `{"this": "3d"}` fails `Literal` on branch 1, fails because `this` isn't a valid field on branches 2-4. Verify the agent gets a useful error, not a wall of per-branch failures.
