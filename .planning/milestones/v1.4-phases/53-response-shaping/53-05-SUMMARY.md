---
phase: 53-response-shaping
plan: 05
subsystem: agent_messages, server
tags: [tool-descriptions, inherited-rename, stripping-note, count-only, include-groups]
dependency_graph:
  requires:
    - phase: 53-04
      provides: "include/only parameters on query contracts, handler wiring to shaping functions"
  provides:
    - "Updated tool descriptions with inherited* naming, stripping note, include group documentation"
    - "_STRIPPING_NOTE, _INHERITED_TASKS/PROJECTS_EXPLANATION, _COUNT_ONLY_TIP reusable fragments"
    - "Count-only integration tests (limit: 0)"
  affects: []
tech_stack:
  added: []
  patterns:
    - "Reusable fragment extraction (_STRIPPING_NOTE, _INHERITED_*_EXPLANATION, _COUNT_ONLY_TIP, _DATE_INPUT_NOTE split)"
key_files:
  created: []
  modified:
    - src/omnifocus_operator/agent_messages/descriptions.py
    - tests/test_server.py
decisions:
  - "Made _INHERITED_FIELD_DESC private (underscore prefix) since it is only used internally within descriptions.py, consistent with _STRIPPING_NOTE pattern"
  - "Split _DATE_INPUT_NOTE into short version (list tools) and _DATE_INPUT_NOTE_FULL (write tools with restart reminder)"
  - "Kept 'inherited (effective)' parenthetical in filter explanation text for backward compatibility with agents that know the 'effective' concept"
metrics:
  duration: 7m
  completed: "2026-04-14T14:25:00Z"
  tasks: 2/2
  tests: 2086 passed (2 new)
  files_modified: 2
requirements_completed: [COUNT-01]
---

# Phase 53 Plan 05: Tool Descriptions and Count-Only Mode Summary

Updated all 11 tool descriptions with inherited* naming, stripping note, include group documentation, and count-only tip. Extracted 5 reusable fragments. Count-only mode verified end-to-end via limit: 0 integration tests.

## Changes

### Production Code

- **agent_messages/descriptions.py**: Complete description overhaul:
  - Added `_INHERITED_FIELD_DESC` shared constant; all 6 `INHERITED_*` constants now delegate to it
  - Added `_STRIPPING_NOTE` fragment used in all read tool descriptions
  - Added `_INHERITED_TASKS_EXPLANATION` and `_INHERITED_PROJECTS_EXPLANATION` fragments
  - Added `_COUNT_ONLY_TIP` fragment
  - Split `_DATE_INPUT_NOTE` (short, for list tools) from `_DATE_INPUT_NOTE_FULL` (with restart reminder, for write tools)
  - Rewrote `LIST_TASKS_TOOL_DOC`: include group docs (notes/metadata/hierarchy/time/*), default fields list, count-only tip, inherited* naming, stripping note
  - Rewrote `LIST_PROJECTS_TOOL_DOC`: include group docs with review group (nextReviewDate, reviewInterval, lastReviewDate, nextTask), inherited* from folder hierarchy
  - Updated `GET_TASK_TOOL_DOC`: stripping note, inherited* fields, inherited explanation
  - Updated `GET_PROJECT_TOOL_DOC`: stripping note, inherited* fields, inherited explanation
  - Updated `GET_TAG_TOOL_DOC`: stripping note added
  - Updated `GET_ALL_TOOL_DOC`: stripping note added
  - Updated `LIST_TAGS_TOOL_DOC`, `LIST_FOLDERS_TOOL_DOC`, `LIST_PERSPECTIVES_TOOL_DOC`: stripping note added
  - Updated `DUE_FILTER_DESC`, `DEFER_FILTER_DESC`, `PLANNED_FILTER_DESC`: "effective/inherited" -> "inherited"
  - All descriptions verified within 2048-byte limit (largest: LIST_TASKS_TOOL_DOC at 1880 bytes)

### Tests

- **tests/test_server.py**: Added 2 count-only integration tests:
  - `test_list_tasks_limit_zero_returns_count_only`: verifies `{items: [], total: 2, hasMore: true}` for tasks
  - `test_list_projects_limit_zero_returns_count_only`: verifies same pattern for projects
  - Both confirm COUNT-01: limit: 0 passes through naturally with no special-casing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Convention] Made _INHERITED_FIELD_DESC private**
- **Found during:** Task 1 (test_descriptions.py validation)
- **Issue:** Public `INHERITED_FIELD_DESC` constant failed `test_all_description_constants_referenced_in_consumers` because no consumer module imports it directly (the 6 `INHERITED_*` aliases are what consumers use)
- **Fix:** Prefixed with underscore to make it a private fragment, consistent with `_STRIPPING_NOTE`, `_DATE_INPUT_NOTE`, etc.
- **Files modified:** descriptions.py
- **Commit:** da33e826

## Decisions Made

- **Private fragment for shared inherited text**: `_INHERITED_FIELD_DESC` follows the underscore-prefix pattern for internal fragments. The 6 public `INHERITED_*` constants delegate to it. Consistent with `_STRIPPING_NOTE`, `_DATE_INPUT_NOTE`.
- **Short vs full date input note**: List tool descriptions use the shorter `_DATE_INPUT_NOTE` (no restart reminder) to save bytes. Write tools use `_DATE_INPUT_NOTE_FULL` which includes the restart guidance.
- **Kept "inherited (effective)" parenthetical**: In filter explanation paragraphs, retained "(effective)" as a parenthetical for agents that might know the concept by its old name. This is explanatory text, not a field name reference.

## Verification

- `uv run pytest tests/ -q`: 2086 passed, 97.65% coverage
- `uv run pytest tests/test_descriptions.py -q`: 9 passed (byte limits, consolidation)
- `uv run pytest tests/test_output_schema.py -q`: 34 passed
- `uv run pytest tests/test_server.py -q -k limit_zero`: 2 passed
- No `effective*` field name references in descriptions.py (regex verified)
- All 11 tool descriptions within 2048-byte limit

## Self-Check: PASSED

- src/omnifocus_operator/agent_messages/descriptions.py exists: FOUND
- tests/test_server.py exists: FOUND
- Commit da33e826 exists (Task 1): FOUND
- Commit 41df54bd exists (Task 2): FOUND
- SUMMARY.md exists: FOUND
