---
phase: 53-response-shaping
plan: 01
subsystem: models
tags: [rename, refactor, models, descriptions, repository]
dependency_graph:
  requires: []
  provides: [inherited-field-names]
  affects: [models/common.py, models/task.py, agent_messages/descriptions.py, repository/hybrid, repository/bridge_only]
tech_stack:
  added: []
  patterns: [bridge-to-model key rename in adapter]
key_files:
  created: []
  modified:
    - src/omnifocus_operator/models/common.py
    - src/omnifocus_operator/models/task.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - src/omnifocus_operator/repository/hybrid/hybrid.py
    - src/omnifocus_operator/repository/bridge_only/bridge_only.py
    - src/omnifocus_operator/repository/bridge_only/adapter.py
    - tests/conftest.py
    - tests/test_models.py
    - tests/test_hybrid_repository.py
    - tests/test_server.py
decisions:
  - Adapter owns bridge-to-model key rename (effective* -> inherited*) at adapt_snapshot level
metrics:
  duration: 10m
  completed: "2026-04-14T13:49:00Z"
  tasks: 2/2
  tests: 2041 passed
  files_modified: 10
---

# Phase 53 Plan 01: Inherited Field Rename Summary

Renamed 6 `effective_*` model fields to `inherited_*` across models, descriptions, mappers, adapter, and tests. Clearer agent-facing semantics -- "inherited" communicates parent-hierarchy origin.

## Changes

### Production Code
- **models/common.py**: 5 fields renamed (`inherited_flagged`, `inherited_due_date`, `inherited_defer_date`, `inherited_planned_date`, `inherited_drop_date`), import updates
- **models/task.py**: 1 field renamed (`inherited_completion_date`), import update
- **descriptions.py**: 6 constants renamed (`INHERITED_FLAGGED`, `INHERITED_DUE_DATE`, etc.) -- description text unchanged (Plan 05 will update)
- **hybrid.py**: 2 mapper dicts updated (task + project) -- model-side target names changed, bridge-side source keys (`effectiveFlagged`, `effectiveDateDue`, etc.) unchanged
- **bridge_only.py**: `_BRIDGE_FIELD_MAP` and `_BRIDGE_PROJECT_FIELD_MAP` updated, attribute access in filter lambdas updated

### Adapter (Rule 3 auto-fix)
- **adapter.py**: Added `_rename_inherited_fields()` to rename bridge camelCase keys (`effectiveFlagged` -> `inheritedFlagged`, etc.) during `adapt_snapshot`. Called unconditionally on tasks and projects so both old-format (bridge.js) and new-format (simulator) data get renamed.

### Tests
- **conftest.py**: `make_model_task_dict` and `make_model_project_dict` updated to `inheritedFlagged`, `inheritedDueDate`, etc.
- **test_models.py**: Model kwargs and attribute assertions updated
- **test_hybrid_repository.py**: Model attribute assertions updated
- **test_server.py**: camelCase output assertions and schema property checks updated

### Preserved (NOT modified)
- Bridge-format factories (`make_task_dict`, `make_project_dict`) in conftest.py
- All golden master JSON files
- `golden_master/normalize.py`
- `tests/doubles/bridge.py` (bridge-format keys)
- `tests/test_cross_path_equivalence.py` (neutral seed keys + bridge-format)
- `tests/test_query_builder.py` (SQL column names)
- `tests/test_list_pipelines.py` (bridge-format factory calls)
- `tests/test_adapter.py` (bridge-format dicts)
- `tests/test_service.py` (bridge-format + `effective_dates` local variable)
- `tests/test_stateful_bridge.py` (bridge-format output)
- `service/domain.py` and `service/service.py` local variables (`effective_dates`, `effective_type`, `effective_parent_id`)
- `simulator/data.py` (bridge-format fixture data)
- `bridge/bridge.js` (OmniFocus API field names)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added _rename_inherited_fields to adapter.py**
- **Found during:** Task 2 (test run)
- **Issue:** Bridge-format data has `effectiveFlagged` etc. as camelCase keys. After renaming model fields to `inherited_*`, the Pydantic alias generator produces `inheritedFlagged` -- but bridge data still arrives with `effectiveFlagged`. The adapter (bridge -> model format translator) needed a rename step.
- **Fix:** Added `_INHERITED_FIELD_RENAMES` mapping dict and `_rename_inherited_fields()` helper in adapter.py, called from `adapt_snapshot()` on all tasks and projects unconditionally (handles both old-format bridge data and new-format simulator data).
- **Files modified:** `src/omnifocus_operator/repository/bridge_only/adapter.py`
- **Commit:** 165ccaee

## Decisions Made

- **Adapter owns the rename**: The bridge->model key rename lives in `adapt_snapshot()` rather than in model validators or a separate middleware. This is consistent with the existing adapter pattern (status mapping, dead field removal, parent ref transformation all happen here).

## Verification

- `uv run pytest tests/ -q`: 2041 passed, 97.76% coverage
- `uv run pytest tests/test_output_schema.py -x -q`: 34 passed
- `grep -r "effective_flagged" src/`: 0 hits
- `grep -r "EFFECTIVE_FLAGGED" src/`: 0 hits
- Golden master files: 0 modified

## Self-Check: PASSED

- All 10 modified files exist on disk
- Commit 53a45918 (Task 1) found
- Commit 165ccaee (Task 2) found
