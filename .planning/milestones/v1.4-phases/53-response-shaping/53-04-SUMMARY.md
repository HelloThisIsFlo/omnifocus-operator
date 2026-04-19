---
phase: 53-response-shaping
plan: 04
subsystem: server, contracts
tags: [field-selection, include, only, handler-wiring, response-shaping]
dependency_graph:
  requires:
    - phase: 53-03
      provides: projection functions (strip_entity, shape_list_response, etc.) and field group config
  provides:
    - "include/only parameters on ListTasksQuery and ListProjectsQuery"
    - "All 11 handlers wired to appropriate shaping functions per D-09"
    - "shape_list_response_strip_only() for list_tags/list_folders/list_perspectives"
    - "INCLUDE_INVALID_TASK/PROJECT error constants"
  affects: [53-05]
tech_stack:
  added: []
  patterns:
    - "Literal type per tool for include validation (TaskFieldGroup, ProjectFieldGroup)"
    - "mode='before' field_validator to intercept Pydantic Literal rejection with educational message"
    - "Handler return type dict[str, Any] for shaped responses (accepted trade-off per D-09)"
key_files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/use_cases/list/tasks.py
    - src/omnifocus_operator/contracts/use_cases/list/projects.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/server/handlers.py
    - src/omnifocus_operator/server/projection.py
    - tests/test_server.py
    - tests/test_projection.py
    - tests/test_list_contracts.py
decisions:
  - "Used separate Literal types per tool (TaskFieldGroup vs ProjectFieldGroup) per D-04b — projects get 'review' group"
  - "Handler return types changed from typed models to dict[str, Any] — accepted trade-off per D-09 (MCP clients strip outputSchema)"
  - "Error constants extracted to errors.py (INCLUDE_INVALID_TASK, INCLUDE_INVALID_PROJECT) to satisfy AST enforcement test"
metrics:
  duration: 9m
  completed: "2026-04-14T14:15:00Z"
  tasks: 2/2
  tests: 2084 passed (11 new)
  files_modified: 9
requirements_completed: [FSEL-01, FSEL-03, FSEL-04, FSEL-05, FSEL-06, FSEL-07, FSEL-08, FSEL-09]
---

# Phase 53 Plan 04: Field Selection Parameters and Handler Wiring Summary

include/only field selection on list query contracts, all 11 handlers wired to shaping functions per D-09, educational validation for invalid include groups, full integration test coverage.

## Changes

### Production Code

- **contracts/use_cases/list/tasks.py**: Added `TaskFieldGroup = Literal["notes", "metadata", "hierarchy", "time", "*"]`, `include: list[TaskFieldGroup] | None` and `only: list[str] | None` on `ListTasksQuery`, `@field_validator("include", mode="before")` with educational error via `err.INCLUDE_INVALID_TASK`. No changes to `ListTasksRepoQuery`.
- **contracts/use_cases/list/projects.py**: Same pattern with `ProjectFieldGroup` adding `"review"` group. `@field_validator("include", mode="before")` uses `err.INCLUDE_INVALID_PROJECT`.
- **agent_messages/descriptions.py**: Added `INCLUDE_FIELD_DESC`, `ONLY_FIELD_DESC` constants. Updated `LIMIT_DESC` with count-only tip.
- **agent_messages/errors.py**: Added `INCLUDE_INVALID_TASK`, `INCLUDE_INVALID_PROJECT` parameterized error constants.
- **server/handlers.py**: All 11 handlers wired per D-09:
  - `get_task/get_project/get_tag` -> `strip_entity(result.model_dump(by_alias=True))`
  - `get_all` -> `strip_all_entities(result.model_dump(by_alias=True))`
  - `list_tasks/list_projects` -> `shape_list_response(result, include=query.include, only=query.only, ...)`
  - `list_tags/list_folders/list_perspectives` -> `shape_list_response_strip_only(result)`
  - `add_tasks/edit_tasks` -> return as-is (no shaping)
  - All read handler return types changed from typed models to `dict[str, Any]`
- **server/projection.py**: Added `shape_list_response_strip_only()` for list tools without field selection.

### Tests

- **tests/test_server.py**: 13 changes:
  - Replaced `test_output_schema_uses_camelcase` with `test_write_tools_retain_typed_output_schema` (read tools now return dict)
  - Fixed 2 assertions checking `field is None` to `field not in sc` (stripping removes null values)
  - Added `TestResponseShaping` class with 11 integration tests: get_task stripping, get_all stripping, list_tasks stripping, include notes, only name, include *, invalid include error, list_tags stripping, add_tasks unmodified
- **tests/test_projection.py**: Added `TestShapeListResponseStripOnly` with 2 tests (strips items + preserves envelope, no warnings omitted)
- **tests/test_list_contracts.py**: Updated `query_only` sets to include `"include", "only"` in field parity tests (server-layer fields not on RepoQuery)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Convention] Extracted inline error strings to errors.py**
- **Found during:** Task 2 (full test suite run)
- **Issue:** AST enforcement test (`test_no_inline_error_strings_in_consumers`) caught inline f-string error messages in `@field_validator("include")` validators
- **Fix:** Created `INCLUDE_INVALID_TASK` and `INCLUDE_INVALID_PROJECT` constants in `errors.py`, updated validators to use `.format()`
- **Files modified:** errors.py, tasks.py, projects.py
- **Commit:** 75a0e74c

**2. [Rule 1 - Bug] Updated tests for stripping behavior**
- **Found during:** Task 2 (test run)
- **Issue:** Two existing tests asserted `field is None` after clearing, but stripping now removes null fields entirely
- **Fix:** Changed assertions to `field not in structured_content` (absent field = not set)
- **Files modified:** tests/test_server.py
- **Commit:** 75a0e74c

**3. [Rule 1 - Bug] Updated field parity tests for query-only fields**
- **Found during:** Task 2 (full test suite)
- **Issue:** Parity test between Query and RepoQuery failed because include/only exist only on Query
- **Fix:** Added `"include", "only"` to `query_only` exclusion sets in both task and project parity tests
- **Files modified:** tests/test_list_contracts.py
- **Commit:** 75a0e74c

**4. [Rule 1 - Bug] Updated outputSchema test for dict return types**
- **Found during:** Task 2 (test run)
- **Issue:** `test_output_schema_uses_camelcase` checked typed outputSchema on `get_all`, but dict return produces generic schema
- **Fix:** Replaced with `test_write_tools_retain_typed_output_schema` verifying write tools still have structured outputSchema
- **Files modified:** tests/test_server.py
- **Commit:** 75a0e74c

## Decisions Made

- **Separate Literal types per tool**: `TaskFieldGroup` and `ProjectFieldGroup` ensure projects can accept `"review"` while tasks cannot, with tool-specific error messages listing valid groups.
- **mode="before" for include validator**: Runs before Pydantic's Literal validation, producing a clean educational message instead of raw Pydantic rejection.
- **dict return types accepted**: Handler return types changed from typed models to `dict[str, Any]`. FastMCP produces generic outputSchema for these, but per D-09 context: "MCP clients strip outputSchema anyway; available fields documented in tool description." Write tools retain typed returns.

## Verification

- `uv run pytest tests/ -q`: 2084 passed, 97.65% coverage
- `uv run pytest tests/test_server.py -q`: 105 passed
- `uv run pytest tests/test_projection.py -q`: 36 passed
- `uv run pytest tests/test_output_schema.py -q`: 34 passed
- `ListTasksQuery(include=["notes"])` succeeds
- `ListTasksQuery(include=["invalid"])` raises with "Unknown field group"
- `ListProjectsQuery(include=["review"])` succeeds (review valid for projects)
- `ListTasksQuery(include=["review"])` raises (review not valid for tasks)
- `ListTasksQuery(include=["notes"], only=["name"])` succeeds (conflict handled at projection layer)

## Self-Check: PASSED

- All 9 key files exist
- Commit e64b5fb0 exists (Task 1)
- Commit 75a0e74c exists (Task 2)
- SUMMARY.md exists
