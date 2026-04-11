---
phase: 48-refactor-datefilter-into-discriminated-union-with-typed-date
plan: 01
subsystem: contracts
tags: [pydantic, discriminated-union, date-filter, refactor]
dependency_graph:
  requires: []
  provides:
    - ThisPeriodFilter model
    - LastPeriodFilter model
    - NextPeriodFilter model
    - AbsoluteRangeFilter model
    - DateFilter discriminated union type alias
    - _route_date_filter callable discriminator
    - _reject_naive_datetime BeforeValidator
    - ABSOLUTE_RANGE_FILTER_EMPTY error constant
    - DATE_FILTER_NAIVE_DATETIME error constant
    - 9 description constants for 4-model structure
  affects:
    - src/omnifocus_operator/service/resolve_dates.py (needs isinstance dispatch rewrite)
    - src/omnifocus_operator/service/domain.py (needs isinstance target change)
    - tests/test_resolve_dates.py (needs construction updates)
    - tests/test_service_domain.py (needs construction updates)
tech_stack:
  added: []
  patterns:
    - "Callable Discriminator with Tag for union routing (new pattern in codebase)"
    - "BeforeValidator for input interception before union dispatch"
    - "Literal type for constrained enum on ThisPeriodFilter.this"
key_files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
    - src/omnifocus_operator/contracts/use_cases/list/__init__.py
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - tests/test_date_filter_contracts.py
    - tests/test_date_filter_constants.py
decisions:
  - "D-04/D-07: Callable Discriminator routes on dict key presence, default to absolute_range"
  - "D-12: BeforeValidator intercepts naive datetime strings before Pydantic union dispatch"
  - "D-15/D-16/D-17: 5 dead error constants deleted, 2 new constants added"
  - "D-17b: No DATE_FILTER_INVALID_TYPE constant -- non-dict routed to absolute_range for Pydantic rejection"
  - "Duration validators duplicated on Last/NextPeriodFilter (Claude's discretion)"
metrics:
  duration: 6m
  completed: "2026-04-10T16:57:12Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 6
---

# Phase 48 Plan 01: Rewrite DateFilter as discriminated union + update tests Summary

4-model discriminated union (ThisPeriodFilter, LastPeriodFilter, NextPeriodFilter, AbsoluteRangeFilter) with callable Discriminator routing, BeforeValidator for naive datetime rejection, typed bounds (AwareDatetime | date | Literal["now"]), 5 dead error constants removed, 9 new description constants added, 82 tests passing.

## Task Commits

| # | Commit | Description | Key Files |
|---|--------|-------------|-----------|
| 1 | 68682d3 | Rewrite _date_filter.py + update exports/errors/descriptions | _date_filter.py, __init__.py, errors.py, descriptions.py |
| 2 | 6832b28 | Update contract and constants tests for discriminated union | test_date_filter_contracts.py, test_date_filter_constants.py |

## Deviations from Plan

None -- plan executed exactly as written.

## What Changed

### _date_filter.py (core refactor)
- Flat `DateFilter(QueryModel)` with 5 optional fields replaced by 4 concrete models
- `ThisPeriodFilter`: `this: Literal["d","w","m","y"]` (structural enforcement, no regex)
- `LastPeriodFilter` / `NextPeriodFilter`: required `last`/`next` field with duration validator
- `AbsoluteRangeFilter`: `before`/`after` typed as `Literal["now"] | AwareDatetime | date | None` with BeforeValidator and model_validator for empty/ordering checks
- `_route_date_filter` callable discriminator routes on dict key presence
- `DateFilter` is now an `Annotated[Union[...], Discriminator(...)]` type alias (not a class)

### errors.py
- Deleted: `DATE_FILTER_MIXED_GROUPS`, `DATE_FILTER_MULTIPLE_SHORTHAND`, `DATE_FILTER_INVALID_THIS_UNIT`, `DATE_FILTER_INVALID_ABSOLUTE`, `DATE_FILTER_EMPTY`
- Added: `ABSOLUTE_RANGE_FILTER_EMPTY`, `DATE_FILTER_NAIVE_DATETIME`

### descriptions.py
- Removed: `DATE_FILTER_DOC`
- Added: 4 model docstrings + 5 field descriptions (9 new constants)
- Updated: 7 field descriptions to "Or use a period/range filter."

### __init__.py
- Exports: `AbsoluteRangeFilter`, `LastPeriodFilter`, `NextPeriodFilter`, `ThisPeriodFilter` added to imports and `__all__`

### Tests (82 passing)
- All `DateFilter(...)` constructions replaced with concrete classes
- Mutual exclusion tests rewritten as discriminator routing tests via TypeAdapter
- Empty filter test updated for `ABSOLUTE_RANGE_FILTER_EMPTY` message
- New tests: naive datetime rejection (before/after), typed bound parsing, non-dict input rejection
- Constants tests rewritten for surviving + new error constants

## Verification

```
uv run pytest tests/test_date_filter_contracts.py tests/test_date_filter_constants.py -x -q --no-cov
82 passed in 0.07s
```

## Self-Check: PASSED

- All 7 files: FOUND
- Commit 68682d3: FOUND
- Commit 6832b28: FOUND
