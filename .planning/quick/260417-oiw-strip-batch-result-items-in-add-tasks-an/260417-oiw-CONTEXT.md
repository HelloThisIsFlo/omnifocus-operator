---
quick_id: 260417-oiw
status: Ready for planning
gathered: 2026-04-17
---

# Quick Task 260417-oiw: Strip batch result items in add_tasks and edit_tasks — Context

<domain>
## Task Boundary

Make `add_tasks` and `edit_tasks` run each result item through `strip_entity` before returning, so null/empty/false/"none" fields drop out — matching the shape/stripping semantics already applied to list and entity tool responses. Source: `.planning/todos/pending/2026-04-17-strip-batch-result-items-in-add-tasks-and-edit-tasks.md`.

Scope:
- `src/omnifocus_operator/server/projection.py` — add helper
- `src/omnifocus_operator/server/handlers.py` — update two handlers
- Test-suite updates (reactive; only if failures surface)

Out of scope:
- No changes to `AddTaskResult` / `EditTaskResult` contracts (pure data — no `model_serializer` per CLAUDE.md).
- No changes to batch result envelope / error semantics.
- No changes to list tools (already strip).

</domain>

<decisions>
## Implementation Decisions

### OutputSchema tradeoff
- **Accept loose schema**. Change handler return annotations from `list[AddTaskResult]` / `list[EditTaskResult]` to `list[dict[str, Any]]`. FastMCP will advertise `array of object` (loose). Matches list-tool precedent, and `@model_serializer` on contracts is banned (MEMORY: contracts are pure data).

### Helper location
- **Add `strip_batch_results` helper to `server/projection.py`**, alongside `strip_all_entities`. Consistent with the existing "projection owns stripping" pattern. Generic form: `strip_batch_results[T: OmniFocusBaseModel](results: list[T]) -> list[dict[str, Any]]`.

### `_REGRESSION_GUARD_TYPES` in `tests/test_output_schema.py`
- **Leave as-is**. The todo's "update _TOOL_SCHEMAS lines 72-73" is a line-number mistake — lines 72-73 are `_REGRESSION_GUARD_TYPES`, a separate dict that uses `TypeAdapter(return_type).json_schema()` directly (raw Pydantic, independent of FastMCP's advertised schema). `_TOOL_SCHEMAS` is loaded dynamically from the running server (line 63) and will auto-update when the handler annotation changes. Net test_output_schema.py edit = none.

### test_server.py `TestAddTasksBatch` / `TestEditTasksBatch` fixup
- **Reactive**: run the full suite first; only convert assertions that actually fail. Expected pattern: `result.error is None` or `result["error"] is None` → `"error" not in result`. Avoid speculative rewrites.

### Claude's Discretion
- Exact names, docstrings, and type-var usage inside `strip_batch_results` — keep it consistent with `strip_all_entities` style.
- Whether to remove unused `AddTaskResult` / `EditTaskResult` imports from `handlers.py` after the annotation swap (the symbols are still used when constructing error results inside the handlers, so likely still imported).
- Handler docstring tweaks, if any, to note that the return is stripped.

</decisions>

<specifics>
## Specific Ideas

Reference snippets from the todo file:

Helper signature (projection.py):
```python
def strip_batch_results[T: OmniFocusBaseModel](results: list[T]) -> list[dict[str, Any]]:
    return [strip_entity(item.model_dump(by_alias=True)) for item in results]
```

Handler changes (handlers.py):
```python
async def add_tasks(...) -> list[dict[str, Any]]:
    ...
    return strip_batch_results(results)

async def edit_tasks(...) -> list[dict[str, Any]]:
    ...
    return strip_batch_results(results)
```

Expected output shape after stripping:
- Success: `{"status": "success", "id": "abc", "name": "Task 1"}` (no null error/warnings)
- Error: `{"status": "error", "error": "Parent not found"}` (no null id/name/warnings)
- Skipped (edit only): `{"status": "skipped", "id": "abc", "warnings": ["Skipped: task 1 failed"]}`

Key invariant:
- `status` is a required Literal ("success" / "error" / "skipped") — none match the strip set, so it's always preserved by construction.
- `AddTaskResult` and `EditTaskResult` have defaults (`= None`) on every optional field, so `AddTaskResult.model_validate({stripped dict})` still works (missing keys → defaults).

</specifics>

<canonical_refs>
## Canonical References

- `.planning/todos/pending/2026-04-17-strip-batch-result-items-in-add-tasks-and-edit-tasks.md` — todo source
- `.planning/milestones/v1.4-MILESTONE-AUDIT.md` — origin (tech_debt entry, 2026-04-17)
- CLAUDE.md → "Model Conventions" — contracts are pure data; no `@model_serializer`
- Memory: `feedback_contracts-are-pure-data.md`

</canonical_refs>

<post_execution>
## Post-Execution

When this quick task lands, resume the v1.4 audit session so Claude can:
- Double-check the changes in `handlers.py`, `projection.py`, and affected tests
- Mark the tech-debt item "Batch result items … not run through `strip_entity`" resolved in `.planning/milestones/v1.4-MILESTONE-AUDIT.md`
- Commit the audit file update

Also: move the todo file from `.planning/todos/pending/` to `.planning/todos/completed/` via `git mv`.

</post_execution>
