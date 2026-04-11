---
phase: 48-refactor-datefilter-into-discriminated-union-with-typed-date
plan: 02
subsystem: service
tags: [resolver, domain, isinstance-dispatch, typed-dates, refactor]
dependency_graph:
  requires:
    - "Plan 01: 4 concrete filter classes + DateFilter union type alias"
  provides:
    - "isinstance-based dispatch in resolve_dates.py"
    - "Typed parse functions (date/AwareDatetime/Literal['now'])"
    - "AbsoluteRangeFilter isinstance check in domain.py defer hints"
  affects: []
tech_stack:
  added: []
  patterns:
    - "isinstance dispatch on concrete filter classes (replaces attribute probing)"
    - "Typed value handling in parse functions (no string parsing)"
key_files:
  created: []
  modified:
    - src/omnifocus_operator/service/resolve_dates.py
    - src/omnifocus_operator/service/domain.py
    - tests/test_resolve_dates.py
    - tests/test_service_domain.py
decisions:
  - "D-18/D-19: domain.py isinstance targets AbsoluteRangeFilter (only variant with .after/.before)"
  - "Resolver signature uses concrete union type instead of DateFilter alias for clarity"
  - "Parse functions use str|datetime|date type hint (covering Literal['now'], AwareDatetime, date)"
metrics:
  duration: 9m
  completed: "2026-04-10T17:09:52Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 48 Plan 02: Rewrite resolver dispatch + fix domain isinstance + migrate tests Summary

isinstance-based dispatch replacing attribute probing in resolve_dates.py, typed parse functions accepting date/AwareDatetime/Literal["now"] instead of strings, _is_date_only and WR-01 defensive fix removed, domain.py defer hint targeting AbsoluteRangeFilter, all tests migrated to concrete filter classes with tz-aware NOW, 1931 tests passing.

## Task Commits

| # | Commit | Description | Key Files |
|---|--------|-------------|-----------|
| 1 | 459cbc2 | Rewrite resolver dispatch + fix domain isinstance | resolve_dates.py, domain.py |
| 2 | bf01605 | Migrate resolver and domain tests to concrete classes | test_resolve_dates.py, test_service_domain.py |

## Deviations from Plan

None -- plan executed exactly as written.

## What Changed

### resolve_dates.py (dispatch rewrite)
- Imports: 4 concrete filter classes imported at runtime (not TYPE_CHECKING) for isinstance dispatch
- `_resolve_date_filter_obj`: attribute probing (`if df.this is not None`) replaced with isinstance dispatch on ThisPeriodFilter, LastPeriodFilter, NextPeriodFilter, AbsoluteRangeFilter
- `_resolve_absolute`: type annotation changed from DateFilter to AbsoluteRangeFilter, null check changed to `is not None` for explicit correctness
- `_parse_absolute_after`/`_parse_absolute_before`: accept typed values (date, AwareDatetime, Literal["now"]) instead of strings, no datetime.fromisoformat parsing, no _is_date_only check
- WR-01 defensive `dt.replace(tzinfo=now.tzinfo)` removed -- contract guarantees AwareDatetime
- `_is_date_only` helper deleted (dead code after typed dispatch)
- Function signature uses explicit union of concrete types

### domain.py (isinstance fix)
- Import: `DateFilter` replaced with `AbsoluteRangeFilter` (runtime, not TYPE_CHECKING)
- Defer hint detection: `isinstance(value, DateFilter)` changed to `isinstance(value, AbsoluteRangeFilter)` -- only this variant has `.after`/`.before` fields (D-18)

### test_resolve_dates.py (test migration)
- NOW fixture changed from naive to tz-aware: `datetime(2026, 4, 7, 14, 0, 0, tzinfo=UTC)`
- All 29 `DateFilter(...)` constructions replaced with concrete classes
- All datetime assertions updated with `tzinfo=UTC`
- Absolute test datetime strings updated to include `Z` suffix for AwareDatetime parsing

### test_service_domain.py (test migration)
- Import: `DateFilter` replaced with `AbsoluteRangeFilter, ThisPeriodFilter`
- 9 `DateFilter(...)` constructions replaced: 1 ThisPeriodFilter, 8 AbsoluteRangeFilter
- Defer hint section header updated to reference D-18/D-19

## Verification

```
uv run pytest tests/test_resolve_dates.py tests/test_service_domain.py -x -q
147 passed in 0.52s

uv run pytest -x -q
1931 passed in 27.46s (98% coverage)
```

## Self-Check: PASSED

- src/omnifocus_operator/service/resolve_dates.py: FOUND
- src/omnifocus_operator/service/domain.py: FOUND
- tests/test_resolve_dates.py: FOUND
- tests/test_service_domain.py: FOUND
- Commit 459cbc2: FOUND
- Commit bf01605: FOUND
