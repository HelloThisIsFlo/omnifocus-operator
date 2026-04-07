---
phase: 43-filters-project-tools
plan: 01
subsystem: service
tags: [resolve-inbox, contradictory-filters, list-tasks, pipeline]
dependency_graph:
  requires: []
  provides: [resolve_inbox, CONTRADICTORY_INBOX_FALSE, CONTRADICTORY_INBOX_PROJECT]
  affects: [_ListTasksPipeline]
tech_stack:
  added: []
  patterns: [inbox-normalization-before-resolution]
key_files:
  created: []
  modified:
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/service/resolve.py
    - src/omnifocus_operator/service/service.py
    - tests/test_service_resolve.py
    - tests/test_list_pipelines.py
decisions:
  - resolve_inbox is synchronous (no I/O, delegates to static _resolve_system_location)
  - Pipeline calls resolve_inbox BEFORE _resolve_project so $inbox never reaches resolve_filter
metrics:
  duration: 4m 16s
  completed: "2026-04-07T00:42:48Z"
  tasks_completed: 2
  tasks_total: 2
  test_count: 16
  files_changed: 5
---

# Phase 43 Plan 01: Resolve Inbox & Pipeline Wiring Summary

resolve_inbox method on Resolver normalizes $inbox to in_inbox=True with contradictory filter detection for all inbox/project combinations, wired into _ListTasksPipeline before project resolution.

## What Was Done

### Task 1: Error templates and resolve_inbox method
- Added `CONTRADICTORY_INBOX_FALSE` and `CONTRADICTORY_INBOX_PROJECT` error templates to `errors.py` (locked strings from CONTEXT.md)
- Implemented `resolve_inbox(in_inbox, project) -> (bool|None, str|None)` on Resolver
- 10 unit tests covering all scenarios: pass-through, $inbox consumption, redundant acceptance, contradictory combos, unknown $ prefix

### Task 2: Pipeline wiring and integration tests
- `_ListTasksPipeline.execute()` calls `resolve_inbox` before `_resolve_project`
- `_resolve_project()` uses `self._project_to_resolve` (output of resolve_inbox)
- `_build_repo_query()` uses `self._in_inbox` (output of resolve_inbox)
- 6 integration tests verifying FILT-01 through FILT-05 at pipeline level

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (RED) | e7efd40 | Failing tests for resolve_inbox |
| 1 (GREEN) | 0bc71b2 | Implement resolve_inbox + error templates |
| 2 (RED) | b8065d7 | Failing integration tests for inbox filter pipeline |
| 2 (GREEN) | 08768cb | Wire resolve_inbox into _ListTasksPipeline |

## Verification

- `uv run pytest tests/test_service_resolve.py -x -q -k resolve_inbox --no-cov` -- 10 passed
- `uv run pytest tests/test_list_pipelines.py -x -q --no-cov` -- all passed
- `uv run pytest -x -q --no-cov` -- 1620 passed, full suite green

## Deviations from Plan

None -- plan executed exactly as written.

## Self-Check: PASSED
