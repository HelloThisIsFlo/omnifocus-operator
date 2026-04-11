---
phase: 45-date-models-resolution
plan: 01
subsystem: contracts
tags: [date-filter, enums, validation, agent-messages]
dependency_graph:
  requires: []
  provides: [DateFilter, DueDateShortcut, LifecycleDateShortcut, date-error-constants, date-description-constants]
  affects: [contracts.use_cases.list, agent_messages]
tech_stack:
  added: []
  patterns: [QueryModel-with-validators, StrEnum-shortcut, field-validator-chain, model-validator-mutual-exclusion]
key_files:
  created:
    - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
    - tests/test_date_filter_contracts.py
    - tests/test_date_filter_constants.py
  modified:
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - src/omnifocus_operator/contracts/use_cases/list/_enums.py
    - src/omnifocus_operator/contracts/use_cases/list/__init__.py
    - tests/test_descriptions.py
    - tests/test_errors.py
decisions:
  - DateFilter uses field_validator chain (duration then model_validator) matching MoveAction pattern
  - "'this' field restricted to single unit char (d/w/m/y) — no count prefix — matching calendar-aligned semantics"
  - Per-field description constants (DUE_FILTER_DESC etc.) added as forward declarations with test exemption for Plan 02
metrics:
  duration: ~9m
  completed: 2026-04-07T22:21:56Z
  tasks_completed: 2
  tasks_total: 2
  test_count: 44
  test_pass: 44
requirements_covered: [DATE-02, DATE-03, DATE-04, DATE-05, DATE-06, DATE-09]
---

# Phase 45 Plan 01: Date Filter Contracts Summary

DateFilter QueryModel with shorthand/absolute mutual exclusion, DueDateShortcut + LifecycleDateShortcut StrEnums, and 17 agent message constants for date filter validation and descriptions.

## Task Results

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Agent message constants for date filters | 243507b | errors.py, descriptions.py |
| 2 | DateFilter model + StrEnums + tests | 73f1660 | _date_filter.py, _enums.py, __init__.py, test_date_filter_contracts.py |

## Implementation Details

### DateFilter Model
- 5 optional `str | None` fields: `this`, `last`, `next`, `before`, `after`
- Shorthand group (this/last/next) and absolute group (before/after) mutually exclusive
- `this` restricted to single unit char (`d`/`w`/`m`/`y`)
- `last`/`next` validate duration format via `_DATE_DURATION_PATTERN` regex
- `before`/`after` accept ISO 8601, date-only, or `"now"`
- Reversed bounds detection when both `after` and `before` are concrete dates
- Equal date-only bounds valid (single-day range per DATE-09)

### StrEnums
- `DueDateShortcut`: overdue, soon, today
- `LifecycleDateShortcut`: any, today

### Agent Messages
- 7 error constants with educational guidance and format placeholders
- 10 description constants (model doc, shortcut docs, 7 per-field filter descriptions)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Registered _date_filter.py in consolidation test consumer lists**
- **Found during:** Task 2
- **Issue:** `test_descriptions.py` and `test_errors.py` AST enforcement tests require every constant to appear in a registered consumer module. New `_date_filter.py` was not registered.
- **Fix:** Added `contracts_list_date_filter` to consumer lists in both test files.
- **Files modified:** tests/test_descriptions.py, tests/test_errors.py

**2. [Rule 3 - Blocking] Added exemption for forward-declared description constants**
- **Found during:** Task 2
- **Issue:** 7 per-field description constants (DUE_FILTER_DESC, COMPLETED_FILTER_DESC, etc.) have no consumer until Plan 02 adds date fields to ListTasksQuery.
- **Fix:** Added `_PENDING_CONSUMER_CONSTANTS` exemption set in test_descriptions.py with TODO comment to remove once Plan 02 wires the fields.
- **Files modified:** tests/test_descriptions.py

## Verification

- `uv run pytest tests/test_date_filter_contracts.py -x -q` -- 38 passed
- `uv run pytest tests/test_date_filter_constants.py -x -q` -- 6 passed
- `uv run pytest -x -q` -- 1737 passed, 97.94% coverage
- All imports verified via `python -c` commands

## Self-Check: PASSED
