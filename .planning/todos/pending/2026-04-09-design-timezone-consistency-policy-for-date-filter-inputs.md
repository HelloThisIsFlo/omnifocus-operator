---
created: 2026-04-09T14:21:54.667Z
title: Design timezone consistency policy for date filter inputs
area: contracts
files:
  - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py:52-69
  - src/omnifocus_operator/contracts/use_cases/add/tasks.py:55-69
  - src/omnifocus_operator/contracts/use_cases/edit/tasks.py:72-86
  - src/omnifocus_operator/service/resolve_dates.py:215-246
  - src/omnifocus_operator/service/domain.py
  - tests/test_resolve_dates.py
---

## Problem

The date filter system has no explicit policy on timezone awareness for datetime inputs. The contract validator accepts any valid ISO datetime string — naive or tz-aware — but production code passes a UTC-aware `now` timestamp. When a naive datetime string reaches the resolver and gets compared against tz-aware model fields, Python raises `TypeError: can't compare offset-naive and offset-aware datetimes`.

A defensive fix was applied (WR-01 from Phase 47 code review) that silently inherits `now.tzinfo` when the parsed datetime is naive. This masks the ambiguity instead of surfacing it.

## Decision

Replace the `str | None` fields on `AbsoluteRangeFilter` (`before`/`after`) with a typed union:

```python
before: Literal["now"] | AwareDatetime | date | None = None
after:  Literal["now"] | AwareDatetime | date | None = None
```

### Why this works

All valid input shapes are covered:

| Agent sends | Branch matched | Result |
|---|---|---|
| `"now"` | `Literal["now"]` | ✅ |
| `"2026-04-01T14:00:00Z"` | `AwareDatetime` | ✅ |
| `"2026-04-01T14:00:00+02:00"` | `AwareDatetime` | ✅ |
| `"2026-04-01"` (date-only) | `date` | ✅ unambiguous, no tz needed |
| `"2026-04-01T14:00:00"` (naive) | fails all branches | ❌ rejected structurally |
| omitted | `None` | ✅ |

Naive datetimes are rejected structurally — no custom validator, no WR-01 hack. Pydantic handles it.

### JSON Schema produced

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

### Alignment with write side

Write contracts (`add_tasks`, `edit_tasks`) already use `AwareDatetime` to reject naive datetimes. This brings the read/filter side into alignment using the same Pydantic type, wrapped in a union to accommodate `"now"` and date-only strings.

### Taxonomy

`Literal` and `AwareDatetime` annotations on contract model fields is exactly where they belong per `model-taxonomy.md` — constraint types live in `contracts/`, not `models/`.

## Implementation changes

- **`AbsoluteRangeFilter`**: Change `before`/`after` field types to `Literal["now"] | AwareDatetime | date | None`
- **Remove custom string validator** for `before`/`after` — no longer needed for format/tz checking
- **Resolver** (`resolve_dates.py:215-246`): `_parse_absolute_after`/`_parse_absolute_before` receive typed Python objects (`str | datetime | date`) instead of raw strings. Simplify to type dispatch — no more `datetime.fromisoformat()`.
- **Remove WR-01 defensive fix** — replace with an assertion that the value is already tz-aware when it's a `datetime`. The contract guarantees this; the assertion makes the invariant explicit.
- **`_parse_to_comparable` ordering check**: Update to handle `date` vs `datetime` comparison (normalize `date` to `datetime` for comparison).
- **Test `NOW` fixture** (`test_resolve_dates.py`): Make it tz-aware (UTC). The naive-vs-aware mismatch path was never exercised; this closes the gap.

## Note on date-only strings

Date-only inputs (`"2026-04-01"`) remain valid and tz-free by design — the granularity is a full day, so there's no sub-day ambiguity. The resolver's existing logic (start-of-day for `after`, start-of-next-day for `before`) is correct and unchanged.
