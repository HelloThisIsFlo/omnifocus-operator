---
created: 2026-04-17T16:35:25.706Z
title: Strip batch result items in add_tasks and edit_tasks
area: server
files:
  - src/omnifocus_operator/server/projection.py
  - src/omnifocus_operator/server/handlers.py
  - tests/test_output_schema.py
---

## Problem

v1.4 audit (`.planning/milestones/v1.4-MILESTONE-AUDIT.md`) surfaced an asymmetry between list/entity responses and batch responses:

- **List tools** (`list_tasks`, `list_projects`, etc.) and **entity tools** (`get_task`, etc.) run every response through `strip_entity` — null/empty/false/"none" are removed. Spec: STRIP-01, STRIP-02, FSEL-09.
- **Batch tools** (`add_tasks`, `edit_tasks`) do NOT strip their result arrays. Every `AddTaskResult` / `EditTaskResult` keeps all optional fields as explicit `null`:

  ```json
  [
    {"status": "success", "id": "abc", "name": "Task 1", "error": null, "warnings": null},
    {"status": "error",   "id": null,  "name": null,     "error": "Parent not found", "warnings": null}
  ]
  ```

  vs stripped (what we want):

  ```json
  [
    {"status": "success", "id": "abc", "name": "Task 1"},
    {"status": "error", "error": "Parent not found"}
  ]
  ```

Flo confirmed during v1.4 audit (2026-04-17) that this was an accidental omission, not a deliberate envelope carve-out: batch responses commonly include many null IDs after error/skipped items, making the asymmetry actively annoying.

Architecture concern was "is this clean to retrofit." Research answer: yes — `server/projection.py` already owns all stripping, and this change makes all 11 tools follow the same pattern (service returns Pydantic → handler dumps + strips → dict goes out) rather than keeping batch tools as the outlier.

## Solution

### Three-spot change (~15 lines)

**1. Add helper to `src/omnifocus_operator/server/projection.py`** (alongside `strip_all_entities`):

```python
def strip_batch_results[T: OmniFocusBaseModel](results: list[T]) -> list[dict[str, Any]]:
    """Strip each batch result item (AddTaskResult / EditTaskResult).

    Same strip semantics as strip_entity: null/""/false/[]/"none" removed.
    status is a required Literal, so it's always preserved.
    """
    return [strip_entity(item.model_dump(by_alias=True)) for item in results]
```

**2. Update both batch handlers in `src/omnifocus_operator/server/handlers.py`:**

```python
# add_tasks  (line 129-160)
async def add_tasks(...) -> list[dict[str, Any]]:  # was: list[AddTaskResult]
    ...
    return strip_batch_results(results)            # was: return results

# edit_tasks (line 168-211)
async def edit_tasks(...) -> list[dict[str, Any]]:  # was: list[EditTaskResult]
    ...
    return strip_batch_results(results)             # was: return results
```

**3. Update `_TOOL_SCHEMAS` in `tests/test_output_schema.py` (lines 72-73):**

```python
"add_tasks": list[dict[str, Any]],    # was: list[AddTaskResult]
"edit_tasks": list[dict[str, Any]],   # was: list[EditTaskResult]
```

Other assertions in that file that use `AddTaskResult.model_validate(dict)` still work because they validate the concrete response against the model, which remains compatible with a dict that just has fewer keys.

### Why strip_entity (not model_dump(exclude_none=True))

The existing `strip_entity` strips null/""/false/[]/"none" — same rules as list/entity responses. Using it keeps strip semantics symmetric across all 11 tools, and handles future cases where someone might add a `bool = False` optional field to a result model.

### One tradeoff to discuss at implementation time

FastMCP infers `outputSchema` from return annotations. Switching from `list[AddTaskResult]` to `list[dict[str, Any]]` loses the structured outputSchema for batch tools — clients that introspect the schema get a looser shape (`array of object` instead of `array of {status, id?, name?, error?, warnings?}`). Agents getting runtime JSON are unaffected; no runtime behavior change.

List tools already have loose outputSchema (`dict[str, Any]`), so this brings batch tools in line with that precedent — no one asked for structured outputSchema on list tools, and no downstream client depends on it.

## Verification

- `tests/test_server.py` `TestAddTasksBatch` + `TestEditTasksBatch` assertions need review — any that check `result.error is None` on success items need to become "error not in result" instead.
- Full test suite should stay green.
- Golden master tests unaffected (don't cover batch handlers).

## Context

- Research done during v1.4 audit session (2026-04-17): `.planning/milestones/v1.4-MILESTONE-AUDIT.md` — see `tech_debt` entry "Batch result items (`AddTaskResult` / `EditTaskResult`) are not run through `strip_entity`"
- Related but distinct from `2026-03-08-return-full-task-object-in-edit-tasks-response.md` — that todo is about response CONTENT (minimal → full); this one is about stripping nulls from whatever content is there.
- Workflow to resume: Flo implements in a separate session. When done, returns to the audit session so Claude can:
  - Double-check the changes
  - Update `.planning/milestones/v1.4-MILESTONE-AUDIT.md` to mark the tech-debt item resolved
  - Then commit the audit file
