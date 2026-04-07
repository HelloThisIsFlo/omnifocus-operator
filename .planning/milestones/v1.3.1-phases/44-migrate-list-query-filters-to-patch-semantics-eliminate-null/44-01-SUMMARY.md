---
phase: 44-migrate-list-query-filters-to-patch-semantics-eliminate-null
plan: 01
subsystem: contracts, service
tags: [patch-semantics, validation, query-models, null-elimination]
dependency_graph:
  requires: []
  provides: [patch-query-models, unset-to-none-utility, null-rejection-validators]
  affects: [service-layer, list-pipelines]
tech_stack:
  added: []
  patterns: [model_validator-mode-before-for-null-rejection, reject_null_filters-shared-helper]
key_files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/base.py
    - src/omnifocus_operator/contracts/use_cases/list/_validators.py
    - src/omnifocus_operator/contracts/use_cases/list/tasks.py
    - src/omnifocus_operator/contracts/use_cases/list/projects.py
    - src/omnifocus_operator/contracts/use_cases/list/tags.py
    - src/omnifocus_operator/contracts/use_cases/list/folders.py
    - src/omnifocus_operator/contracts/use_cases/list/perspectives.py
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/service/service.py
    - tests/test_list_contracts.py
    - tests/test_default_pagination.py
decisions:
  - Removed AVAILABILITY_EMPTY error template (AST enforcement test requires all constants be referenced; availability validation not yet implemented)
  - Used Sequence[object] instead of list[object] for validate_non_empty_list to satisfy mypy --strict covariance
  - Service layer updated with unset_to_none() at query-to-repo boundary (blocking fix, Rule 3)
metrics:
  duration: ~13 minutes
  completed: "2026-04-07T14:41:00Z"
---

# Phase 44 Plan 01: Migrate List Query Filters to Patch Semantics Summary

All 5 list query models migrated from `T | None = None` to `Patch[T] = UNSET` for filter fields, with null-rejection validators and educational error messages.

## What Changed

- **13 filter fields** across 5 query models: `T | None = None` -> `Patch[T] = UNSET`
- **5 offset fields**: `int | None = None` -> `int = 0`
- **New infrastructure**: `unset_to_none()` utility, `reject_null_filters()` and `validate_non_empty_list()` shared validators, `FILTER_NULL` and `TAGS_EMPTY` error templates
- **Null rejection**: `model_validator(mode="before")` on all 5 models catches null before Pydantic sees it (prevents _Unset leak in error messages)
- **Empty tags rejection**: `field_validator` on ListTasksQuery rejects `tags=[]`
- **review_due_within validator**: Simplified to handle `_Unset` passthrough, removed dead `if v is None` branch
- **Service layer**: `unset_to_none()` at 8 query-to-repo boundary points

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | fb3a0e5 | Infrastructure: unset_to_none, error templates, shared validators |
| 2 | 6f31bc4 | Migrate 5 query models + service layer + tests |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Service layer UNSET propagation**
- **Found during:** Task 2
- **Issue:** Service layer code checked `query.tags is None`, `query.folder is None`, etc. which are now UNSET (not None), causing TypeError on iteration and incorrect repo query construction
- **Fix:** Added `unset_to_none()` import to service.py; converted all Patch field accesses at the query-to-repo boundary; changed `is None` checks to `is_set()` where needed
- **Files modified:** src/omnifocus_operator/service/service.py
- **Commit:** 6f31bc4

**2. [Rule 1 - Bug] AVAILABILITY_EMPTY unused constant**
- **Found during:** Task 2
- **Issue:** AST enforcement test (`test_errors.py`) requires all error constants in errors.py to be referenced in consumer modules. AVAILABILITY_EMPTY was defined per plan but not yet consumed.
- **Fix:** Removed AVAILABILITY_EMPTY from errors.py. Can be re-added when availability empty-list validation is implemented.
- **Files modified:** src/omnifocus_operator/agent_messages/errors.py
- **Commit:** 6f31bc4

**3. [Rule 1 - Bug] mypy --strict covariance error**
- **Found during:** Task 2
- **Issue:** `validate_non_empty_list(value: list[object], ...)` rejected `list[str]` due to list invariance under mypy --strict
- **Fix:** Changed parameter type to `Sequence[object]` (covariant)
- **Files modified:** src/omnifocus_operator/contracts/use_cases/list/_validators.py
- **Commit:** 6f31bc4

**4. [Rule 3 - Blocking] test_default_pagination.py offset assertion**
- **Found during:** Task 2
- **Issue:** Existing test asserted `query.offset is None` but offset now defaults to 0
- **Fix:** Updated assertion to `query.offset == 0`
- **Files modified:** tests/test_default_pagination.py
- **Commit:** 6f31bc4

## Verification Results

- `uv run pytest tests/test_list_contracts.py -x -q`: 94 passed
- `uv run pytest tests/test_output_schema.py -x -q`: 32 passed
- `uv run mypy src/omnifocus_operator/contracts/use_cases/list/ --strict`: Success (0 errors)
- `uv run pytest tests/ --ignore=tests/doubles`: 1668 passed, 98.14% coverage

## Self-Check: PASSED

- All 11 modified files exist
- Both commits (fb3a0e5, 6f31bc4) found in history
- Key content verified: unset_to_none, FILTER_NULL, TAGS_EMPTY, reject_null_filters, Patch[bool], TestNullRejection, TestEmptyListRejection
