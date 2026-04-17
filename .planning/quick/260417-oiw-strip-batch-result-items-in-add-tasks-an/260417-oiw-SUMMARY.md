---
quick_id: 260417-oiw
subsystem: server
tags: [refactor, projection, response-shaping]
requires:
  - OmniFocusBaseModel.model_dump(by_alias=True)
  - strip_entity
provides:
  - strip_batch_results helper (server/projection.py)
  - Loose list[dict[str, Any]] outputSchema on add_tasks/edit_tasks
affects:
  - add_tasks response shape (null id/name/warnings dropped on error/skipped items)
  - edit_tasks response shape (null id/name/warnings dropped on error/skipped items)
  - FastMCP-advertised outputSchema for both batch tools (now "array of object")
tech_stack:
  added: []
  patterns:
    - PEP 695 generic helper over OmniFocusBaseModel, mirrors strip_all_entities
    - strip_entity pipe on batch items, matches list/entity tool precedent
key_files:
  created: []
  modified:
    - src/omnifocus_operator/server/projection.py
    - src/omnifocus_operator/server/handlers.py
    - tests/test_server.py
decisions:
  - Accepted loose outputSchema (list[dict[str, Any]]) over forcing @model_serializer on contracts (contracts-are-pure-data).
  - Helper placed in server/projection.py alongside strip_all_entities — consistent with "projection owns stripping."
  - Moved OmniFocusBaseModel import out of TYPE_CHECKING in projection.py (runtime PEP 695 type bound).
  - test_write_tools_retain_typed_output_schema inverted and renamed — the assertion it encoded was the thing this task deliberately removed.
metrics:
  tasks_completed: 2
  commits: 2
  duration_minutes: 6
  files_modified: 3
  tests_passed: 2168
  completed_date: "2026-04-17"
---

# Quick Task 260417-oiw: Strip batch result items in add_tasks and edit_tasks

Strip null/empty/false/"none" fields from every item returned by `add_tasks` and `edit_tasks` via a new `strip_batch_results` helper — bringing batch tools in line with the stripping semantics already applied to list and entity tool responses.

## What Changed

- **New helper** `strip_batch_results[T: OmniFocusBaseModel](results: list[T]) -> list[dict[str, Any]]` in `src/omnifocus_operator/server/projection.py` (after `strip_all_entities`). Pipes each item through `strip_entity(item.model_dump(by_alias=True))`.
- **Both batch handlers** in `src/omnifocus_operator/server/handlers.py` now:
  - Advertise return annotation `list[dict[str, Any]]` (was `list[AddTaskResult]` / `list[EditTaskResult]`).
  - Pipe `results` through `strip_batch_results` before returning.
- **Import fix** in `projection.py`: `OmniFocusBaseModel` moved from `TYPE_CHECKING` to runtime imports (PEP 695 type parameter bounds are evaluated at runtime).
- **Reactive test fix** in `tests/test_server.py`: `test_write_tools_retain_typed_output_schema` renamed to `test_write_tools_have_loose_output_schema`; assertions flipped from "status/id in schema" to "status/id NOT in schema" since the typed outputSchema is exactly what this task traded away.

## Response shape before/after

Before:
```json
[
  {"status": "success", "id": "abc", "name": "T1", "error": null, "warnings": null},
  {"status": "error",   "id": null,  "name": null, "error": "Parent not found", "warnings": null}
]
```

After:
```json
[
  {"status": "success", "id": "abc", "name": "T1"},
  {"status": "error", "error": "Parent not found"}
]
```

`status` is a required Literal — always preserved.

## Commits

- `85bab2f5` — refactor(server): strip batch result items in add_tasks and edit_tasks
- `adecc261` — test(server): adapt write-tool output schema assertion to loose shape

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing test `test_write_tools_retain_typed_output_schema` asserted the inverse of our new invariant**
- **Found during:** Task 2 (full-suite run)
- **Issue:** The test asserted that `add_tasks` / `edit_tasks` advertised typed outputSchemas with `status` / `id` properties. Our deliberate change removed exactly that (per CONTEXT.md locked decision: "Accept loose schema").
- **Fix:** Renamed the test to `test_write_tools_have_loose_output_schema` and flipped the assertions (`in add_props` → `not in add_props`), updated the docstring to explain the new contract.
- **Files modified:** `tests/test_server.py`
- **Commit:** `adecc261`

This was reactive test fallout — the test wasn't flagged explicitly in the plan's "expected fallout" list (which focused on `TestAddTasksBatch` / `TestEditTasksBatch` assertion patterns) but falls under the same principle: a test encoding the old contract must be flipped to encode the new one. `TestAddTasksBatch` / `TestEditTasksBatch` were already dict-style and did NOT need changes.

### Planned fallout that didn't materialize

- No assertion translations needed in `TestAddTasksBatch` / `TestEditTasksBatch`. Those tests already used dict access (`items[0]["status"]`) and defensive `.get()` patterns (`items[0].get("id") is None`, `items[0].get("warnings") is not None`) that stay green under the stripped shape.
- No changes needed to `tests/test_output_schema.py` — `_TOOL_SCHEMAS` dynamically loads from the running server and auto-absorbed the looser schema.

## Verification

- `uv run pytest -x -q` — 2168 passed, 0 failed.
- `uv run pytest tests/test_output_schema.py -x -q` — 35 passed (belt-and-braces per CLAUDE.md "Model Conventions").
- `git diff --stat b14bb3cd..HEAD` — touches only `src/omnifocus_operator/server/projection.py`, `src/omnifocus_operator/server/handlers.py`, `tests/test_server.py`. `tests/test_output_schema.py` is NOT in the diff.
- Pre-commit hooks (ruff check, ruff format, mypy) pass on both commits.

## Self-Check: PASSED

- Files modified (all confirmed present in working tree):
  - `src/omnifocus_operator/server/projection.py` — FOUND (contains `def strip_batch_results`)
  - `src/omnifocus_operator/server/handlers.py` — FOUND (imports `strip_batch_results`, both handlers return `list[dict[str, Any]]`)
  - `tests/test_server.py` — FOUND (test renamed and assertions flipped)
- Commits (both present in `git log`):
  - `85bab2f5` — FOUND
  - `adecc261` — FOUND

## Post-Execution (per CONTEXT.md)

Return to the v1.4 audit session to:
- Mark the tech-debt item "Batch result items (`AddTaskResult` / `EditTaskResult`) are not run through `strip_entity`" resolved in `.planning/milestones/v1.4-MILESTONE-AUDIT.md`.
- Commit that audit-file update.
- `git mv` the todo from `.planning/todos/pending/2026-04-17-strip-batch-result-items-in-add-tasks-and-edit-tasks.md` to `.planning/todos/completed/`.
