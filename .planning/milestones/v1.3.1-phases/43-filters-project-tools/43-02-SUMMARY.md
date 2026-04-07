---
phase: 43-filters-project-tools
plan: 02
subsystem: service
tags: [inbox-guard, search-warning, tool-description]
dependency_graph:
  requires: [43-01]
  provides: [GET_PROJECT_INBOX_ERROR, LIST_PROJECTS_INBOX_WARNING, updated GET_PROJECT_TOOL_DOC]
  affects: [service/resolve.py, service/service.py, agent_messages/]
tech_stack:
  added: []
  patterns: [$-prefix guard in lookup methods, search term warning in read pipelines]
key_files:
  created: []
  modified:
    - src/omnifocus_operator/service/resolve.py
    - src/omnifocus_operator/service/service.py
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/agent_messages/warnings.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - tests/test_service_resolve.py
    - tests/test_list_pipelines.py
decisions:
  - "lookup_project $-prefix guard catches ALL system locations, not just $inbox (D-12)"
  - "list_projects search warning uses substring match against SYSTEM_LOCATIONS['inbox'].name (D-18)"
  - "DESC-03 intentional no-op: filter descriptions omit $inbox per D-21"
  - "PROJ-02 no-code: inbox is virtual, never appears in list_projects (D-15)"
metrics:
  duration: 276s
  completed: "2026-04-07"
  tasks: 2
  files: 7
---

# Phase 43 Plan 02: Inbox Guard & Search Warning Summary

lookup_project rejects $-prefixed IDs with educational error; list_projects warns on inbox-related search terms; GET_PROJECT_TOOL_DOC updated with $inbox behavior.

## Changes Made

### Task 1: get_project $inbox guard and list_projects search warning (TDD)

- Added `GET_PROJECT_INBOX_ERROR` template to `errors.py`
- Added `LIST_PROJECTS_INBOX_WARNING` template to `warnings.py`
- Added $-prefix guard to `Resolver.lookup_project()` -- raises before repo call
- Added `_check_inbox_search_warning()` to `_ListProjectsPipeline` -- appends warning when search term is substring of "Inbox" (case-insensitive)
- Tests: 3 new tests in `TestLookupProjectInboxGuard`, 5 new tests in `TestListProjectsInboxWarning`
- TDD: RED (9dc7715) -> GREEN (4dd3678)

### Task 2: Description update and requirement cleanup

- Updated `GET_PROJECT_TOOL_DOC` with $inbox error paragraph before Fields listing
- Verified DESC-03 is intentional no-op (filter descriptions omit $inbox per D-21)
- Verified PROJ-02 is no-code (inbox is virtual, not in SQLite or bridge)
- NRES-07 already marked `[x]` in REQUIREMENTS.md -- no change needed

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 (RED) | 9dc7715 | test(43-02): add failing tests for $inbox guard and list_projects search warning |
| 1 (GREEN) | 4dd3678 | feat(43-02): implement $inbox guard and list_projects search warning |
| 2 | 3c0b6da | feat(43-02): update GET_PROJECT_TOOL_DOC with $inbox error behavior |

## Verification

- `uv run pytest tests/test_service_resolve.py tests/test_list_pipelines.py -x -q -k "inbox"` -- 27 passed
- `uv run pytest tests/test_output_schema.py -x -q` -- 32 passed (schema valid)
- `uv run pytest -x -q` -- 1628 passed, 98.10% coverage
