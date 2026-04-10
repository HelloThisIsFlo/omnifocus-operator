---
created: "2026-04-10T12:01:58.691Z"
title: Refactor DateFilter into discriminated union for schema-level validation
area: contracts
files:
  - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
  - src/omnifocus_operator/contracts/shared/repetition_rule.py:70-87
---

## Problem

The current `DateFilter` model is a flat object with 5 optional `str | None` fields (`this`, `last`, `next`, `before`, `after`). All mutual-exclusion rules are enforced at runtime via validators. The JSON Schema agents see exposes all 5 fields simultaneously with no per-field descriptions, no format constraints, and no structural hint that shorthand and absolute groups can't be mixed.

This means agents can easily construct invalid inputs (`{this: "2w"}`, `{this: "w", after: "..."}`, `{}`) that the schema doesn't prevent. Error messages are good, but prevention is better.

## Solution

Replace the flat `DateFilter` with a discriminated union of 4 models, following the proven `EndConditionSpec = EndByDateSpec | EndByOccurrencesSpec` pattern already in the codebase:

```python
class ThisPeriod(QueryModel):
    this: Literal["d", "w", "m", "y"]

class LastPeriod(QueryModel):
    last: str   # runtime: count > 0, valid unit

class NextPeriod(QueryModel):
    next: str   # runtime: count > 0, valid unit

class AbsoluteRange(QueryModel):
    before: str | None = None
    after: str | None = None
    # runtime: at least one set, after <= before

DateFilter = ThisPeriod | LastPeriod | NextPeriod | AbsoluteRange
```

**Structurally prevents** (no validators needed):
- Mixed shorthand + absolute (`{this: "w", after: "..."}`)
- Empty object (`{}`)
- Multiple shorthand keys (`{this: "w", last: "3d"}`)
- Invalid `this` values (`this: "2w"`) — now a Literal enum

**Still needs runtime validators:**
- `last`/`next` count > 0 and valid unit
- `before`/`after` valid ISO datetime or "now"
- `after <= before` ordering
- `AbsoluteRange` at least one field set

**Input shape is unchanged** — agents send the same JSON, schema is just tighter.

Spike before implementing: confirm Pydantic smart union error messages stay clean when no branch matches.
