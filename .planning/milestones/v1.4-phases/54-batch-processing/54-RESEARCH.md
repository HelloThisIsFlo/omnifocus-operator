# Phase 54: Batch Processing - Research

**Researched:** 2026-04-15
**Domain:** Handler/contract modification — batch semantics for write tools
**Confidence:** HIGH

## Summary

Phase 54 is a well-scoped handler-and-contract change. The scaffolding (progress reporting loops, `Task N:` error prefix, service pipelines) is already in place. The work is: remove two guards, update two result models, update two error strings, update two description constants, add one config constant, and write tests for multi-item paths.

No service-layer changes. No new tools. No architectural shifts.

**Primary recommendation:** Work in five discrete units — (1) config constant, (2) result model updates, (3) handler logic, (4) description updates, (5) test rewrite.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Whole-batch Pydantic validation. Schema errors reject the entire request. Service-layer errors are per-item and produce `status: "error"`.
- **D-02:** Flat model with optional fields. `status: Literal["success", "error", "skipped"]`. `id: str | None`. `name: str | None` (success only). `error: str | None` (error only). `warnings: list[str] | None` (all statuses). `success: bool` removed.
- **D-03:** `"Task N:"` prefix on per-item error strings. Per-item catch scope: `ToolError` and `ValueError`. Unexpected exceptions re-raise.
- **D-04:** Skipped items reference the failing item: `"Skipped: task 2 failed"`. Fallback to generic message if awkward.
- **D-05:** `MAX_BATCH_SIZE = 50` in `config.py`, enforced via Pydantic `max_length` or `@model_validator`.
- **D-06:** Parameterized description fragments. Shared fragments with `{placeholders}` for tool-specific values. Inline per-tool for failure mode explanation.

### Claude's Discretion

- Exact fragment decomposition (how many, what parameters, naming)
- Whether `MAX_BATCH_SIZE` is enforced via `max_length` on the list parameter or a `@model_validator`
- Test organization for batch scenarios
- Whether `AddTaskResult` and `EditTaskResult` stay separate or merge into `BatchItemResult`
- Exact wording of description fragments and inline prose

### Deferred Ideas (OUT OF SCOPE)

- Return full task object in edit response
- Serial execution guarantee across concurrent batch calls (v1.6)
- Cross-item references in batch (documented as unsupported, not built)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BATCH-01 | add_tasks and edit_tasks accept up to 50 items per call | MAX_BATCH_SIZE = 50 in config.py; enforce via max_length or model_validator on items list |
| BATCH-02 | add_tasks uses best-effort — all items processed regardless of earlier failures | Handler loop with try/except per item, always continue; service already stateless per-item |
| BATCH-03 | edit_tasks uses fail-fast — stop at first error, remaining items skipped | Handler loop with break on first exception; failed_idx variable for skip messages |
| BATCH-04 | Response is flat array with status: "success" \| "error" \| "skipped" per item | Replace success: bool with status: Literal in AddTaskResult/EditTaskResult |
| BATCH-05 | name on success only; id on success and edit errors/skips; absent on failed add items | Make id/name Optional on result models; construct conditionally in handler |
| BATCH-06 | warnings array available on all status types | Already present as `warnings: list[str] \| None = None` — preserved on all statuses |
| BATCH-07 | Items processed serially in array order within a batch | Already sequential — enumerate loop, no concurrency added |
| BATCH-08 | Same-task edits allowed — each sees prior item's result | Implicit from sequential processing; service pipelines re-fetch task state |
| BATCH-09 | Cross-item references not supported — documented in tool description | Description fragment update only; no code enforcement needed |
</phase_requirements>

---

## Standard Stack

No new libraries. All work is within existing dependencies.

| Layer | File | Change |
|-------|------|--------|
| Config | `src/omnifocus_operator/config.py` | Add `MAX_BATCH_SIZE = 50` |
| Contracts | `src/omnifocus_operator/contracts/use_cases/add/tasks.py` | Rewrite `AddTaskResult` |
| Contracts | `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` | Rewrite `EditTaskResult` |
| Handler | `src/omnifocus_operator/server/handlers.py` | Remove guards, rewrite loops |
| Error strings | `src/omnifocus_operator/agent_messages/errors.py` | Update `ADD_TASKS_BATCH_LIMIT`, `EDIT_TASKS_BATCH_LIMIT` |
| Descriptions | `src/omnifocus_operator/agent_messages/descriptions.py` | Update `_WRITE_RETURNS`, add batch fragments, update tool docs |
| Tests | `tests/test_server.py` | Rewrite batch constraint tests, add multi-item scenarios |
| Tests | `tests/test_output_schema.py` | Update fixtures — remove `success=True`, add `status=` |
| Tests | `tests/test_descriptions.py` | Update any description assertions if present |

[VERIFIED: codebase grep]

---

## Architecture Patterns

### Current Handler Structure (add_tasks)

```python
# handlers.py — CURRENT (scaffolded, awaiting lift)
async def add_tasks(items: list[AddTaskCommand], ctx: Context) -> list[AddTaskResult]:
    if len(items) != 1:                          # ← REMOVE THIS
        raise ValueError(ADD_TASKS_BATCH_LIMIT.format(count=len(items)))
    service: OperatorService = ctx.lifespan_context["service"]
    command = items[0]
    total = len(items)
    results: list[AddTaskResult] = []
    for i, validated in enumerate([command]):    # ← [command] → items
        await ctx.report_progress(progress=i, total=total)
        result = await service.add_task(validated)
        results.append(result)
    await ctx.report_progress(progress=total, total=total)
    return results
```

[VERIFIED: codebase read]

### Target Handler — add_tasks (best-effort)

```python
async def add_tasks(items: list[AddTaskCommand], ctx: Context) -> list[AddTaskResult]:
    service: OperatorService = ctx.lifespan_context["service"]
    total = len(items)
    results: list[AddTaskResult] = []
    for i, command in enumerate(items):
        await ctx.report_progress(progress=i, total=total)
        try:
            result = await service.add_task(command)
            results.append(result)
        except (ToolError, ValueError) as e:
            results.append(AddTaskResult(
                status="error",
                error=f"Task {i + 1}: {e}",
            ))
    await ctx.report_progress(progress=total, total=total)
    return results
```

### Target Handler — edit_tasks (fail-fast)

```python
async def edit_tasks(items: list[EditTaskCommand], ctx: Context) -> list[EditTaskResult]:
    service: OperatorService = ctx.lifespan_context["service"]
    total = len(items)
    results: list[EditTaskResult] = []
    failed_idx: int | None = None
    for i, command in enumerate(items):
        await ctx.report_progress(progress=i, total=total)
        if failed_idx is not None:
            results.append(EditTaskResult(
                status="skipped",
                id=command.id,
                warnings=[f"Skipped: task {failed_idx + 1} failed"],
            ))
            continue
        try:
            result = await service.edit_task(command)
            results.append(result)
        except (ToolError, ValueError) as e:
            failed_idx = i
            results.append(EditTaskResult(
                status="error",
                id=command.id,
                error=f"Task {i + 1}: {e}",
            ))
    await ctx.report_progress(progress=total, total=total)
    return results
```

[ASSUMED — pattern derived from CONTEXT.md spec; exact implementation is Claude's discretion]

### Target Result Models

```python
# contracts/use_cases/add/tasks.py
class AddTaskResult(OmniFocusBaseModel):
    __doc__ = ADD_TASK_RESULT_DOC
    status: Literal["success", "error", "skipped"]
    id: str | None = None
    name: str | None = None
    error: str | None = None
    warnings: list[str] | None = None

# contracts/use_cases/edit/tasks.py
class EditTaskResult(OmniFocusBaseModel):
    __doc__ = EDIT_TASK_RESULT_DOC
    status: Literal["success", "error", "skipped"]
    id: str | None = None
    name: str | None = None
    error: str | None = None
    warnings: list[str] | None = None
```

[VERIFIED: field design from CONTEXT.md D-02; base class from codebase read]

### MAX_BATCH_SIZE Enforcement Options

**Option A: `max_length` on list annotation** — declared in handler signature, Pydantic enforces at deserialization:

```python
from typing import Annotated
from pydantic import Field
items: Annotated[list[AddTaskCommand], Field(max_length=50)]
```

**Option B: `@model_validator` on a wrapper model** — requires a wrapper model, more overhead.

**Option C: manual check in handler** — loses schema-level enforcement (not ideal).

Option A is the simplest and aligns with D-05 ("Pydantic model validator or `max_length` on the `items` list parameter"). The `max_length` annotation approach uses Pydantic's native JSON Schema `maxItems` constraint, which will appear in the tool's inputSchema. [VERIFIED: codebase grep for `DEFAULT_LIST_LIMIT` pattern; Pydantic max_length behavior is [ASSUMED]]

### Config Constant

```python
# config.py — alongside DEFAULT_LIST_LIMIT
MAX_BATCH_SIZE: int = 50
```

[VERIFIED: precedent from `DEFAULT_LIST_LIMIT = 50` in config.py]

### Description Fragment Pattern

```python
# descriptions.py
_BATCH_RETURNS = (
    "Returns: array of per-item results. "
    "Each item: status ('success' | 'error' | 'skipped'), "
    "id (success + edit errors/skips), name (success only), "
    "warnings (any status), error (error only)."
)

_BATCH_LIMIT_NOTE = f"Up to {MAX_BATCH_SIZE} items per call."

_BATCH_CROSS_ITEM_NOTE = (
    "Cross-item references not supported: batch items cannot reference "
    "other items created in the same batch. For hierarchies, use sequential calls."
)

_BATCH_CONCURRENCY_NOTE = (
    "Concurrent batch calls from separate agents are not serialized. "
    "Serial execution guarantee is a v1.6 concern."
)
```

[ASSUMED — exact decomposition is Claude's discretion per D-06]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Schema-level max items | Custom validation in handler | Pydantic `max_length` annotation on list |
| Per-item error message prefix | Custom formatter | Follow existing `_format_validation_errors` `Task N:` convention |
| Result model discrimination | `oneOf` / discriminated union | Flat model with `Literal` status (D-02 is explicit) |

---

## Common Pitfalls

### Pitfall 1: Catching too broadly in handlers
**What goes wrong:** Catching `Exception` instead of `ToolError | ValueError` causes systemic errors (bridge I/O failures, `RuntimeError`) to silently swallow into per-item errors.
**How to avoid:** Catch only `ToolError` and `ValueError` per D-03. Let everything else propagate.
**Warning signs:** Bridge timeout appears as item error rather than killing the batch.

### Pitfall 2: `success: bool` references in tests
**What goes wrong:** `test_output_schema.py` has `AddTaskResult(success=True, ...)` and `EditTaskResult(success=True, ...)` at lines 244-245 and 344-360. These become construction errors after model update.
**How to avoid:** Update all fixtures in `test_output_schema.py` simultaneously with model changes.
**Files affected:** `tests/test_output_schema.py` (lines 244, 245, 344, 359), `tests/test_server.py` (`items[0]["success"]` assertions at lines 619, 631, 639, 663, 778, 801, 838, 860, 888).
**Warning signs:** `TypeError: unexpected keyword argument 'success'`.

### Pitfall 3: `test_server.py` output schema assertion checks for `"success"` in props
**What goes wrong:** `tests/test_server.py` around lines 369/372 asserts `"success" in add_props` and `"success" in edit_props`. After model change, `success` is gone.
**How to avoid:** Update these assertions to check `"status"` instead.

### Pitfall 4: edit_tasks skipped items need `id` from input, not service
**What goes wrong:** Skipped items haven't been processed by the service — there's no `repo_result.id`. The id must come from `command.id` (available from `EditTaskCommand.id`).
**How to avoid:** In the fail-fast loop, build `EditTaskResult(status="skipped", id=command.id, ...)` before calling the service.

### Pitfall 5: add_tasks error items should NOT include `id`
**What goes wrong:** For failed add items, no OmniFocus ID exists yet. Including a dummy `id` or `command.id` (there is none — `AddTaskCommand` has no `id`) is impossible and wrong.
**How to avoid:** Leave `id=None` on add error results. The model allows it. [VERIFIED: `AddTaskCommand` has no `id` field — confirmed in contracts read]

### Pitfall 6: `_format_validation_errors` already adds `Task N:` prefix for schema errors
**What goes wrong:** If handler also adds `Task N:` on the per-item catch, a schema error for item 3 would show `"Task 3: Task 3: ..."` double-prefix.
**How to avoid:** Handler catch only applies to service-layer errors (`ToolError`/`ValueError` from service). Schema validation errors are caught upstream by `ValidationReformatterMiddleware` and kill the whole batch — they never reach the handler catch.

---

## Code Examples

### Service pipelines return exactly what we need — no change

```python
# service/service.py — _AddTaskPipeline._delegate() — no change needed
async def _delegate(self) -> AddTaskResult:
    repo_result = await self._repository.add_task(self._repo_payload)
    all_warnings = self._preferences_warnings + self._repetition_warnings
    return AddTaskResult(
        success=True,   # ← becomes status="success"
        id=repo_result.id,
        name=repo_result.name,
        warnings=all_warnings or None
    )
```

After model update, service constructs `AddTaskResult(status="success", id=..., name=..., warnings=...)`. The handler's catch block constructs `AddTaskResult(status="error", error=...)`. [VERIFIED: codebase read]

### Error message format

```python
# Per D-03: "Task N:" prefix on per-item error strings (1-indexed, consistent with middleware)
error=f"Task {i + 1}: {str(e)}"
```

This aligns with `_format_validation_errors` convention in `middleware.py` line 147. [VERIFIED: codebase read]

---

## Tests to Update / Add

### Tests to Rewrite (existing, now invalid)

| Test | File | Line | What Changes |
|------|------|------|--------------|
| `test_add_tasks_single_item_constraint` | `test_server.py` | ~667 | Rewrite: 2 items should succeed (best-effort), not raise |
| `test_add_tasks_empty_array` | `test_server.py` | ~675 | Rewrite: should still error (0 < 1, but now via maxItems = min? Or just len check?) |
| `test_edit_tasks_rejects_multi_item_array` | `test_server.py` | ~746 | Rewrite: 2+ items should process, not raise |
| `test_edit_tasks_rejects_empty_array` | `test_server.py` | ~741 | Rewrite: empty array behavior |
| All `items[0]["success"]` assertions | `test_server.py` | multiple | Replace with `items[0]["status"] == "success"` |
| OutputSchema assertions for `"success" in props` | `test_server.py` | ~369-373 | Replace with `"status" in props` |
| `AddTaskResult(success=True, ...)` fixtures | `test_output_schema.py` | ~244, 344, 359 | Replace with `status="success"` |
| `EditTaskResult(success=True, ...)` fixtures | `test_output_schema.py` | ~245 | Replace with `status="success"` |

[VERIFIED: codebase read]

### New Tests to Add

**add_tasks batch scenarios (best-effort):**
- All items succeed → `[status: success, status: success, ...]`
- First item fails, second succeeds → `[status: error, status: success]`
- All items fail → `[status: error, status: error]`
- Up to 50 items accepted → no error
- 51 items rejected → whole-batch validation error

**edit_tasks batch scenarios (fail-fast):**
- All items succeed → `[status: success, ...]`
- Item 1 fails → `[status: error, status: skipped, status: skipped]`
- Item 2 fails → `[status: success, status: error, status: skipped]`
- Skipped message references failing item index: `"Skipped: task 2 failed"`
- `id` present on skipped items (from `command.id`)
- Up to 50 items accepted

**Result field presence tests (BATCH-05):**
- Success: `id` present, `name` present, `error` absent
- Error (add): `id` absent, `name` absent, `error` present
- Error (edit): `id` present (from command), `name` absent, `error` present
- Skipped: `id` present (from command), `name` absent, `error` absent, `warnings` present

---

## State of the Art

| Old | New | Impact |
|-----|-----|--------|
| `success: bool` field | `status: Literal["success", "error", "skipped"]` | Agent gets typed enum in schema, no boolean inference |
| `len(items) != 1` guard | `max_length=50` + handler loop | Batch enabled, schema-enforced upper bound |
| Error messages: "exactly 1 item" | "up to 50 items" | Match new semantics |
| `_WRITE_RETURNS` fragment | Updated with status-based shape | Tool docs stay in sync |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/test_server.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BATCH-01 | 50 items accepted, 51 rejected | integration (via client) | `pytest tests/test_server.py -x -q` | Wave 0 needed |
| BATCH-02 | add_tasks: item 2 fails, item 3 still processed | integration | `pytest tests/test_server.py -x -q` | Wave 0 needed |
| BATCH-03 | edit_tasks: item 2 fails, items 3+ skipped | integration | `pytest tests/test_server.py -x -q` | Wave 0 needed |
| BATCH-04 | status enum in each item | integration | `pytest tests/test_server.py -x -q` | Wave 0 needed |
| BATCH-05 | id/name field presence by status | integration | `pytest tests/test_server.py -x -q` | Wave 0 needed |
| BATCH-06 | warnings on all status types | integration | `pytest tests/test_server.py -x -q` | Wave 0 needed |
| BATCH-07 | serial order (implicit from sequential impl) | unit | `pytest tests/test_server.py -x -q` | Wave 0 needed |
| BATCH-08 | same-task edits see prior result | integration | `pytest tests/test_server.py -x -q` | Wave 0 needed |
| BATCH-09 | cross-item ref documented (no code behavior) | n/a — description only | n/a | n/a |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_server.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

The existing `TestAddTasks` and `TestEditTasks` classes in `tests/test_server.py` need:
- Rewrite of 4 constraint tests (single-item guards → batch behavior)
- New batch-specific test methods added to both classes
- Updated assertions wherever `items[0]["success"]` is checked

`tests/test_output_schema.py` needs fixture updates (no new tests, just model construction fix).

No new test files needed — all batch tests belong in `tests/test_server.py` alongside existing tool tests.

---

## Open Questions

1. **Empty array behavior (0 items)**
   - What we know: current tests assert "exactly 1 item" error for 0 items
   - What's unclear: should 0 items return empty `[]` (valid call, no work done) or a validation error?
   - Recommendation: use `min_length=1` alongside `max_length=50` — empty batch is meaningless, error is appropriate. Aligns with current behavior intent. [ASSUMED]

2. **Separate models vs shared `BatchItemResult`**
   - What we know: D-02 says "Single model per tool replaces existing `AddTaskResult`/`EditTaskResult` 1-for-1" — the language implies keeping separate models
   - What's unclear: CONTEXT.md also lists merge into `BatchItemResult` as Claude's discretion
   - Recommendation: keep separate (cleaner outputSchema per tool, matches existing naming pattern). Merge offers no benefit since models have identical shape.

3. **`max_length` annotation syntax with FastMCP**
   - What we know: FastMCP uses `get_type_hints()` for parameter introspection; `items: list[AddTaskCommand]` is the current signature
   - What's unclear: whether `items: Annotated[list[AddTaskCommand], Field(max_length=50)]` survives FastMCP's annotation resolution
   - Recommendation: if `Annotated` + `Field(max_length=)` doesn't work cleanly with FastMCP, fall back to a `@model_validator` on a thin wrapper, or a manual check at the top of the handler (after removing the old guard). Test the schema output to confirm `maxItems` appears. [ASSUMED — needs verification at implementation time]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `Annotated[list[T], Field(max_length=50)]` produces `maxItems: 50` in FastMCP inputSchema | Architecture Patterns | Implementation may need `@model_validator` fallback |
| A2 | `min_length=1` should be applied alongside `max_length=50` for empty array rejection | Open Questions | Behavioral change from current — empty array may be intended to be valid |
| A3 | Handler catch of `ToolError \| ValueError` covers all known service failure modes | Architecture Patterns | Other exception types may leak silently as systemic errors |
| A4 | Exact description fragment decomposition | Architecture Patterns | Low risk — Claude's discretion |

---

## Sources

### Primary (HIGH confidence)
- Codebase read: `handlers.py`, `contracts/use_cases/add/tasks.py`, `contracts/use_cases/edit/tasks.py`, `config.py`, `errors.py`, `descriptions.py`, `middleware.py`, `models/base.py`, `contracts/base.py`
- Codebase read: `tests/test_server.py`, `tests/test_output_schema.py`
- `.planning/phases/54-batch-processing/54-CONTEXT.md` — locked decisions D-01 through D-06
- `.research/updated-spec/MILESTONE-v1.4.md` §Batch Processing for Write Tools

### Secondary (MEDIUM confidence)
- `REQUIREMENTS.md` BATCH-01 through BATCH-09 — canonical requirement text

---

## Metadata

**Confidence breakdown:**
- What to change: HIGH — exact files and line locations verified
- How to change it: HIGH for handler logic; MEDIUM for `max_length` annotation behavior with FastMCP
- Test impact: HIGH — specific test names and line numbers identified
- Description fragments: MEDIUM — exact decomposition is discretionary

**Research date:** 2026-04-15
**Valid until:** Stable — no external dependencies, pure internal refactor
