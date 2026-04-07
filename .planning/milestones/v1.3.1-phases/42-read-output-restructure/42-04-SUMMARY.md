---
phase: 42-read-output-restructure
plan: 04
subsystem: models, repository
tags: [bugfix, serialization, parent-ref, next-task, gap-closure]
dependency_graph:
  requires: []
  provides: [ParentRef-exclude-none, root-task-project-parent, nextTask-self-ref-guard]
  affects: [models/common.py, hybrid/hybrid.py, bridge_only/adapter.py]
tech_stack:
  added: []
  patterns: [model_dump-override-exclude-none, self-reference-guard]
key_files:
  created: []
  modified:
    - src/omnifocus_operator/models/common.py
    - src/omnifocus_operator/repository/hybrid/hybrid.py
    - src/omnifocus_operator/repository/bridge_only/adapter.py
    - tests/test_models.py
    - tests/test_hybrid_repository.py
    - tests/test_adapter.py
    - tests/test_service.py
decisions:
  - Used model_dump override with exclude_none=True instead of @model_serializer (preserves JSON Schema)
metrics:
  duration: 313s
  completed: "2026-04-06T21:19:27Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 7
  tests_added: 5
  tests_total: 1604
---

# Phase 42 Plan 04: Gap Closure (ParentRef + nextTask) Summary

Fix ParentRef exclude_none serialization, root-task parent classification, and project nextTask self-reference guard across both hybrid and bridge code paths.

## Task Summary

| Task | Name | Commit(s) | Key Changes |
|------|------|-----------|-------------|
| 1 | ParentRef serialization + root-task parent | f76317e (RED), 6c01d79 (GREEN) | model_dump override, is_root_in_project guard in both paths |
| 2 | Project nextTask self-reference | 21fb096 (RED), 75ccc0e (GREEN) | nextTask != task_id filter in hybrid and adapter |

## Changes Made

### Task 1: ParentRef serialization and root-task parent classification

- **models/common.py**: Added `model_dump` override on `ParentRef` that defaults `exclude_none=True` -- serializes only the set branch (no null keys in JSON output)
- **hybrid/hybrid.py**: Added `is_root_in_project` detection in `_build_parent_and_project` -- when `parent_task_id == project info["id"]`, falls through to project parent branch
- **bridge_only/adapter.py**: Added `is_root_in_project` guard in `_adapt_parent_ref` -- when `parent_task_id == project_id`, skips task branch

### Task 2: Project nextTask self-reference

- **hybrid/hybrid.py**: Added `row["nextTask"] != task_id` condition in `_map_project_row` -- self-referencing nextTask becomes None
- **bridge_only/adapter.py**: Added self-reference check in `_enrich_project` -- when `next_task_val == project_id`, nullifies instead of enriching

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Output schema erasure from @model_serializer**
- **Found during:** Task 1 GREEN phase
- **Issue:** `@model_serializer` on ParentRef erased JSON Schema structure, failing `test_output_schema.py`
- **Fix:** Switched to `model_dump` override with `exclude_none=True` default (plan anticipated this fallback)
- **Files modified:** src/omnifocus_operator/models/common.py
- **Commit:** 6c01d79

**2. [Rule 1 - Bug] Service test expected old incorrect parent classification**
- **Found during:** Task 2 full test suite run
- **Issue:** `test_move_to_project_ending` expected `parent.task.id == "proj-001"` for a root task moved to a project -- this was the old incorrect behavior
- **Fix:** Updated assertion to expect `parent.project.id == "proj-001"` (correct classification)
- **Files modified:** tests/test_service.py
- **Commit:** 75ccc0e

## Verification

- All 1604 tests pass
- Output schema validation passes (no JSON Schema erasure)
- Coverage: 98.08%

## Self-Check: PASSED
