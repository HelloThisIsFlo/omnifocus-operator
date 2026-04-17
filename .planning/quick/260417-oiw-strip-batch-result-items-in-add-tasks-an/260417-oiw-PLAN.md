---
quick_id: 260417-oiw
type: execute
wave: 1
depends_on: []
files_modified:
  - src/omnifocus_operator/server/projection.py
  - src/omnifocus_operator/server/handlers.py
  - tests/test_server.py
autonomous: true
requirements:
  - STRIP-batch-parity
must_haves:
  truths:
    - "add_tasks response items have null/empty/false/'none' fields removed (same rules as strip_entity)"
    - "edit_tasks response items have null/empty/false/'none' fields removed"
    - "status field is always preserved on every result item (required Literal)"
    - "Error and skipped items drop the null id/name/warnings fields they used to carry"
    - "Full test suite stays green after the change"
  artifacts:
    - path: "src/omnifocus_operator/server/projection.py"
      provides: "strip_batch_results helper alongside strip_all_entities"
      contains: "def strip_batch_results"
    - path: "src/omnifocus_operator/server/handlers.py"
      provides: "add_tasks and edit_tasks return stripped result lists with list[dict[str, Any]] annotation"
      contains: "strip_batch_results(results)"
  key_links:
    - from: "src/omnifocus_operator/server/handlers.py"
      to: "src/omnifocus_operator/server/projection.py"
      via: "from omnifocus_operator.server.projection import strip_batch_results"
      pattern: "strip_batch_results"
    - from: "tests/test_output_schema.py::_TOOL_SCHEMAS"
      to: "server create_server().list_tools() output_schema"
      via: "dynamic load — auto-picks up new list[dict[str, Any]] annotation"
      pattern: "list_tools"
---

<objective>
Strip null/empty/false/"none" fields from every item returned by `add_tasks` and `edit_tasks`, bringing batch tools in line with the list-tool and entity-tool stripping precedent. Source: v1.4 audit tech-debt entry (`.planning/milestones/v1.4-MILESTONE-AUDIT.md`) and todo `.planning/todos/pending/2026-04-17-strip-batch-result-items-in-add-tasks-and-edit-tasks.md`.

Purpose: Eliminate the asymmetry where batch responses carry explicit `null` fields (e.g. `"id": null, "warnings": null` on error items) while list/entity responses strip them. Most painful in error-heavy batches where half the fields are null noise.

Output: A new `strip_batch_results` helper in `server/projection.py`, updated return annotations and return statements on both batch handlers, and any reactive test fixes in `tests/test_server.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/quick/260417-oiw-strip-batch-result-items-in-add-tasks-an/260417-oiw-CONTEXT.md
@.planning/todos/pending/2026-04-17-strip-batch-result-items-in-add-tasks-and-edit-tasks.md
@src/omnifocus_operator/server/projection.py
@src/omnifocus_operator/server/handlers.py
@src/omnifocus_operator/contracts/use_cases/add/tasks.py
@src/omnifocus_operator/contracts/use_cases/edit/tasks.py

<interfaces>
<!-- Contracts the executor needs, extracted from the codebase. -->

From src/omnifocus_operator/models/base.py:
- `OmniFocusBaseModel` — base class with `model_dump(by_alias=True)` support.

From src/omnifocus_operator/contracts/use_cases/add/tasks.py:
```python
class AddTaskResult(OmniFocusBaseModel):
    status: Literal["success", "error", "skipped"]  # required -- always preserved
    id: str | None = None
    name: str | None = None
    error: str | None = None
    warnings: list[str] | None = None
```

From src/omnifocus_operator/contracts/use_cases/edit/tasks.py:
```python
class EditTaskResult(OmniFocusBaseModel):
    status: Literal["success", "error", "skipped"]  # required -- always preserved
    id: str | None = None
    name: str | None = None
    error: str | None = None
    warnings: list[str] | None = None
```

From src/omnifocus_operator/server/projection.py:
```python
def strip_entity(entity: dict[str, Any]) -> dict[str, Any]:
    """Remove keys whose values are in STRIP_VALUES, except NEVER_STRIP keys."""
    return {k: v for k, v in entity.items() if k in NEVER_STRIP or not _is_strip_value(v)}

def strip_all_entities(data: dict[str, Any]) -> dict[str, Any]:
    """Strip each entity in a get_all response."""
    # ...existing implementation (precedent for the new helper's style)
```

Current handler shape (src/omnifocus_operator/server/handlers.py, lines ~129 / ~168):
```python
async def add_tasks(...) -> list[AddTaskResult]:
    ...
    results: list[AddTaskResult] = [...]
    return results   # <-- becomes: return strip_batch_results(results)

async def edit_tasks(...) -> list[EditTaskResult]:
    ...
    results: list[EditTaskResult] = [...]
    return results   # <-- becomes: return strip_batch_results(results)
```
</interfaces>

<constraints>
Locked decisions (from CONTEXT.md — DO NOT revisit):
- Accept loose outputSchema: handler annotations become `list[dict[str, Any]]`. FastMCP will advertise `array of object`. Matches list-tool precedent.
- Helper lives in `server/projection.py` (not a new module).
- No `@model_serializer` on `AddTaskResult` / `EditTaskResult` — contracts are pure data (CLAUDE.md: "Model Conventions", memory: `feedback_contracts-are-pure-data.md`).
- **No changes to `tests/test_output_schema.py`**:
  - `_TOOL_SCHEMAS` is loaded dynamically from `create_server().list_tools()` (line 63) — it auto-updates when the handler annotation changes.
  - `_REGRESSION_GUARD_TYPES` (lines 67-74) uses `TypeAdapter(list[AddTaskResult]).json_schema()` directly, independent of FastMCP's advertised schema. Leave as-is — it's a separate guard against `@model_serializer` erasure.
  - The todo's "update _TOOL_SCHEMAS lines 72-73" was a line-number mistake (those lines are `_REGRESSION_GUARD_TYPES`).
- Test fixes are REACTIVE only: run the suite, fix exactly what fails, no speculative rewrites.

Project rules:
- After modifying any model-backed tool output → run `uv run pytest tests/test_output_schema.py -x -q` (CLAUDE.md).
- `AddTaskResult` / `EditTaskResult` imports in `handlers.py` are still needed (used when constructing error/skipped results inside the handler loops) — do NOT remove them.
</constraints>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Add strip_batch_results helper and wire both batch handlers</name>
  <files>
    src/omnifocus_operator/server/projection.py,
    src/omnifocus_operator/server/handlers.py
  </files>
  <action>
Single atomic change — one commit.

**1. Add `strip_batch_results` to `src/omnifocus_operator/server/projection.py`**

Place it in the "Stripping functions" section, right after `strip_all_entities` (around line 60). Style must mirror `strip_all_entities` — generic over `OmniFocusBaseModel`, short docstring, pure dict transform.

```python
def strip_batch_results[T: OmniFocusBaseModel](results: list[T]) -> list[dict[str, Any]]:
    """Strip each batch result item (AddTaskResult / EditTaskResult).

    Same strip semantics as strip_entity: null/""/false/[]/"none" removed.
    status is a required Literal, so it's always preserved.
    """
    return [strip_entity(item.model_dump(by_alias=True)) for item in results]
```

Note: `OmniFocusBaseModel` is already importable under `TYPE_CHECKING` in `projection.py` (line 16). Because PEP 695 `[T: OmniFocusBaseModel]` is a *runtime* bound, the import must be runtime-visible. Move the `OmniFocusBaseModel` import out of the `TYPE_CHECKING` block to the module-level imports at the top of the file. Leave `ListResult` in `TYPE_CHECKING` (it's only used in annotations).

**2. Update `src/omnifocus_operator/server/handlers.py`**

- Add `strip_batch_results` to the import block `from omnifocus_operator.server.projection import (...)` at line 61-66 (alphabetical with `strip_all_entities`, `strip_entity`).
- In `add_tasks` (line ~129):
  - Change return annotation `-> list[AddTaskResult]` to `-> list[dict[str, Any]]`.
  - Change the final `return results` (line ~160) to `return strip_batch_results(results)`.
- In `edit_tasks` (line ~168):
  - Change return annotation `-> list[EditTaskResult]` to `-> list[dict[str, Any]]`.
  - Change the final `return results` (line ~211) to `return strip_batch_results(results)`.
- Leave the inner `results: list[AddTaskResult] = []` and `results: list[EditTaskResult] = []` local annotations alone — they're still correct; only the public return annotation changes.
- Leave `AddTaskResult` / `EditTaskResult` imports — still used inside the handlers for error/skipped construction.
- No docstring changes required (handlers don't have doc comments today; the tool descriptions live in `agent_messages/descriptions.py`).

Commit after this step:
```
feat(server): strip null fields from add_tasks/edit_tasks batch results
```
  </action>
  <behavior>
    - `strip_batch_results([AddTaskResult(status="success", id="abc", name="T", error=None, warnings=None)])` returns `[{"status": "success", "id": "abc", "name": "T"}]`.
    - `strip_batch_results([AddTaskResult(status="error", error="Parent not found")])` returns `[{"status": "error", "error": "Parent not found"}]`.
    - `strip_batch_results([])` returns `[]`.
    - `add_tasks` / `edit_tasks` return types advertised by FastMCP are now `array of object` (loose), matching list-tool precedent.
    - `status` field is present on every returned item (required Literal — never stripped by construction).
  </behavior>
  <verify>
    <automated>uv run pytest tests/test_output_schema.py -x -q</automated>
  </verify>
  <done>
    - `strip_batch_results` exists in `server/projection.py` and imports cleanly at runtime.
    - Both handlers use `list[dict[str, Any]]` as their return annotation and call `strip_batch_results(results)`.
    - `tests/test_output_schema.py` passes — `_TOOL_SCHEMAS` auto-reloads the looser schema and fixture data still validates.
    - No changes to `tests/test_output_schema.py` itself.
    - `mypy` / `ruff` (via pre-commit or `uv run ...` equivalent) clean on changed files.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Run full test suite and fix reactive fallout</name>
  <files>tests/test_server.py</files>
  <action>
Run the full suite and repair only assertions that actually break. Do NOT speculatively rewrite.

```
uv run pytest -x -q
```

Expected fallout (per CONTEXT.md):
- `tests/test_server.py::TestAddTasksBatch` and `tests/test_server.py::TestEditTasksBatch` — assertions that inspect result items on successful calls.
- After the change, each `result` coming back from `add_tasks` / `edit_tasks` is a plain `dict`, not an `AddTaskResult` / `EditTaskResult` instance. And stripped success items no longer have an `error` key at all.

Translation rules for any failing assertion:
- `result.status == "success"` → `result["status"] == "success"`
- `result.id == "..."` → `result["id"] == "..."`
- `result.error is None` → `"error" not in result`
- `result.warnings is None` → `"warnings" not in result` (or keep as `result.get("warnings") is None` if you prefer)
- `result.error == "some msg"` → `result["error"] == "some msg"` (error path still carries `error` key)
- Type hints like `result: AddTaskResult` on local vars inside tests → update to `result: dict[str, Any]` (or drop the hint).

Rules of engagement:
- If a test file outside `tests/test_server.py` breaks, apply the same translation rule — but only after understanding why it was asserting on the batch handler output directly.
- Do NOT change `tests/test_output_schema.py`. If it fails, pause and investigate — the schema is dynamically loaded, so the right thing happened is it reloaded the new loose schema; fixture data must still validate. If it actually fails, surface it as a deviation before patching.
- Do NOT edit tests that are exercising the contract objects themselves (e.g. tests calling `AddTaskResult(...)` directly) — those are unaffected.
- Run `uv run pytest -x -q` iteratively. On each failure: read, translate, re-run.

Once all tests pass, run the output-schema check one more time as a belt-and-braces pass per CLAUDE.md:

```
uv run pytest tests/test_output_schema.py -x -q
```

Commit the test fixes (only if any tests needed changes):
```
test(server): adapt batch result assertions to stripped dict shape
```

If nothing needs to change in `tests/`, skip the commit — task is still complete.
  </action>
  <behavior>
    - `uv run pytest -x -q` exits 0.
    - All batch-handler assertions read dicts, not Pydantic model attributes.
    - Success-path items do not reference `.error` / `.warnings`; they assert absence via `not in` or `.get()`.
    - Error-path items still assert on `error` content.
    - No test file other than `tests/test_server.py` was modified unless an orthogonal break surfaced (document it in the commit message if so).
  </behavior>
  <verify>
    <automated>uv run pytest -x -q</automated>
  </verify>
  <done>
    - Full test suite green.
    - `tests/test_output_schema.py` green on its own (explicit re-run per CLAUDE.md rule).
    - Any fixed assertions follow the translation rules above.
    - `tests/test_output_schema.py` unchanged.
    - Working tree clean, commits made (one for source change, optionally one for tests).
  </done>
</task>

</tasks>

<verification>
- `uv run pytest -x -q` — full suite green.
- `uv run pytest tests/test_output_schema.py -x -q` — explicit check per CLAUDE.md "Model Conventions".
- Manual spot-check: call `add_tasks` with a deliberately bad parent to force an error item, confirm returned item has no `"id": null` / `"name": null` / `"warnings": null` keys — just `{"status": "error", "error": "..."}`.
- `git diff --stat` touches exactly: `src/omnifocus_operator/server/projection.py`, `src/omnifocus_operator/server/handlers.py`, and (reactively) `tests/test_server.py`. `tests/test_output_schema.py` is NOT in the diff.
</verification>

<success_criteria>
- `strip_batch_results` helper exists in `server/projection.py` and mirrors `strip_all_entities` in style.
- `add_tasks` and `edit_tasks` return `list[dict[str, Any]]` and pipe `results` through `strip_batch_results`.
- `AddTaskResult` / `EditTaskResult` contracts untouched (no `@model_serializer`, no field changes).
- `tests/test_output_schema.py` unchanged and passing (dynamic `_TOOL_SCHEMAS` absorbs the looser schema automatically).
- Test suite green; batch-handler tests updated to dict-style assertions where needed.
- Commit(s) follow repo style (lowercase prefix, colon, imperative).
</success_criteria>

<output>
On completion:
- Source + handler change committed.
- Test fixes committed separately (only if any changes landed).
- Return to the v1.4 audit session (per CONTEXT.md `<post_execution>`) so Claude can:
  - Double-check the diff.
  - Mark the tech-debt item "Batch result items (`AddTaskResult` / `EditTaskResult`) are not run through `strip_entity`" resolved in `.planning/milestones/v1.4-MILESTONE-AUDIT.md`.
  - Commit that audit file update.
- `git mv` the todo from `.planning/todos/pending/2026-04-17-strip-batch-result-items-in-add-tasks-and-edit-tasks.md` to `.planning/todos/completed/` (preserves git history — memory: `feedback_use-git-mv-for-todos.md`).
</output>
