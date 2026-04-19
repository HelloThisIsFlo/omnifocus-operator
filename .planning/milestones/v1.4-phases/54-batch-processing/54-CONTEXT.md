# Phase 54: Batch Processing - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Agents can create or edit up to 50 tasks in a single call with clear per-item success/failure reporting. Lift the `len(items) != 1` guard on both `add_tasks` and `edit_tasks`. Different failure semantics per tool: best-effort (add) vs fail-fast (edit). New response shape with `status` enum replacing `success: bool`.

No new tools. No service-layer architecture changes — pipelines are already stateless per-item. The work is in handlers, contracts, config, descriptions, and tests.

</domain>

<decisions>
## Implementation Decisions

### Validation boundary
- **D-01:** Whole-batch Pydantic validation. Schema errors (empty name, bad date format, missing required fields) reject the entire request — agent must fix all items and retry. Service-layer errors (task not found, tag not found, ambiguous name) are per-item and produce `status: "error"` on individual items.
- **Rationale:** Schema validation = malformed input (fix and retry). Service errors = legitimate item failures (partial success). Clean conceptual boundary. Zero change to existing validation path. `ValidationReformatterMiddleware` already formats per-item `Task N:` messages for schema errors.
- Handler parameter stays `items: list[AddTaskCommand]` (typed, rich inputSchema preserved).

### Response model design
- **D-02:** Flat model with optional fields. Single model per tool replaces existing `AddTaskResult`/`EditTaskResult` 1-for-1.
  - `status: Literal["success", "error", "skipped"]`
  - `id: str | None` — present on success and edit errors/skips (known from input), absent on failed add items
  - `name: str | None` — present on success only
  - `error: str | None` — present on error only
  - `warnings: list[str] | None` — available on all status types
- **Rationale:** Discriminated unions in this codebase are for inbound models (DateFilter, Frequency) where Pydantic routes ambiguous agent input. These are outbound results — system-constructed, not validated against input. Flat model with Literal status gives agents a clean enum in the schema without `oneOf` indirection. Construction discipline (not type system) enforces field conditionality — tests catch misuse.
- `success: bool` field removed from both models.

### Error detail & indexing
- **D-03:** Explicit `"Task N:"` prefix on per-item error strings. Consistent with `_format_validation_errors` in middleware.
  - Example: `"Task 3: Invalid tag 'Foo'"`
  - Per-item catch scope: `ToolError` and `ValueError` — covers all known service failure modes (tag not found, task not found, circular reference, date validation, ambiguous name).
  - Unexpected exceptions (`RuntimeError`, `AttributeError`, bridge I/O errors) re-raise and kill the whole batch — they indicate systemic failure, not item-level issues.

### Fail-fast skip message (edit_tasks)
- **D-04:** Skipped items reference the failing item in their warning.
  - Example: `"Skipped: task 2 failed"`
  - Preferred over generic "Skipped due to earlier failure" — gives agents direct pointer to root cause.
  - Trivial to implement: handler stores `failed_idx` from the enumerate loop.
  - **Fallback:** If implementation proves awkward, generic message is acceptable (but unlikely — it's one variable).

### Max batch size
- **D-05:** `MAX_BATCH_SIZE = 50` in `config.py` as a module-level constant (like `DEFAULT_LIST_LIMIT`). Not user-configurable via environment — architectural limit. Enforced via Pydantic model validator or `max_length` on the `items` list parameter.

### Tool description strategy
- **D-06:** Mixed approach: parameterized fragments for shared structure + inline prose for tool-specific semantics.
  - **Shared fragments (with `{placeholders}`):** Max items limit, status enum shape, no cross-item references, concurrency caveat. Template parameters inject tool-specific values (e.g., `{failure_mode}` = "best-effort" or "fail-fast").
  - **Inline per tool:** Failure mode explanation, tool-specific behavioral notes.
  - **Rationale:** Shared structural framing can't drift between tools (one template). Tool-specific semantics are explicit at the call site. Extends existing `_WRITE_RETURNS` fragment pattern with parameterization.
  - Follows Phase 53 pattern: `_STRIPPING_NOTE` is shared (identical across tools), tool-specific sections are inline.

### Claude's Discretion
- Exact fragment decomposition — how many fragments, what parameters, naming
- Whether `MAX_BATCH_SIZE` is enforced via `max_length` on the list parameter or a `@model_validator`
- Test organization for batch scenarios (unit tests on handler logic vs integration tests through tools)
- Whether `AddTaskResult` and `EditTaskResult` stay as separate models (same shape, different names) or merge into a shared `BatchItemResult`
- Exact wording of description fragments and inline prose (following existing `descriptions.py` patterns)

### Folded Todos
- None — matched todos were either already completed (same-container move fix), out of scope (serial execution guarantee → v1.6), or intentionally unmapped (return full task object in edit response).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec
- `.research/updated-spec/MILESTONE-v1.4.md` — Full spec for batch processing: failure semantics, response shape, max items, concurrency notes. §Batch Processing for Write Tools is the primary reference.

### Architecture & conventions
- `docs/architecture.md` — Three-layer architecture, method object pattern, service layer conventions. Batch processing is a handler/contract concern — service layer unchanged.
- `docs/model-taxonomy.md` — Model naming conventions. Result models use `Result` suffix, inherit `OmniFocusBaseModel`. Outbound models use optional fields (not discriminated unions).

### Prior phase context
- `.planning/phases/53-response-shaping/53-CONTEXT.md` — Phase 53 decisions. D-03 (no stripping on write results), D-09 (add/edit return as-is), D-11 (description fragment patterns).

### Current implementation (key files)
- `src/omnifocus_operator/server/handlers.py` — `add_tasks` and `edit_tasks` handlers with existing `len(items) != 1` guards, progress reporting loops, D-05 batch scaffolding comments
- `src/omnifocus_operator/contracts/use_cases/add/tasks.py` — `AddTaskCommand`, `AddTaskResult` models
- `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` — `EditTaskCommand`, `EditTaskResult` models
- `src/omnifocus_operator/config.py` — Centralized constants (`DEFAULT_LIST_LIMIT`), field group definitions. Add `MAX_BATCH_SIZE` here.
- `src/omnifocus_operator/agent_messages/descriptions.py` — All agent-facing description constants. Update `_WRITE_RETURNS`, add batch fragments.
- `src/omnifocus_operator/agent_messages/errors.py` — `ADD_TASKS_BATCH_LIMIT`, `EDIT_TASKS_BATCH_LIMIT` error messages (update for new max-50 semantics)
- `src/omnifocus_operator/middleware.py` — `_format_validation_errors` with `Task N:` prefix pattern (reference for error formatting convention)
- `src/omnifocus_operator/service/service.py` — `_AddTaskPipeline`, `_EditTaskPipeline` method objects. No changes needed — pipelines are stateless per-item.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Progress reporting loop** in both handlers — already scaffolded with `enumerate([command])` and `ctx.report_progress(progress=i, total=total)`. Just change `[command]` to `items`.
- **`_format_validation_errors`** in middleware — establishes `Task N:` prefix convention for error formatting.
- **`_WRITE_RETURNS`** description constant — existing shared fragment for write tool return shape. Extend with batch parameterization.
- **`DEFAULT_LIST_LIMIT = 50`** in config — precedent for module-level architectural constants.

### Established Patterns
- **Method Object pattern** — `_AddTaskPipeline` and `_EditTaskPipeline` process one item at a time, are stateless, and return a single result. Handler loops invoke them sequentially. No service changes needed for batch.
- **`ValidationReformatterMiddleware`** — catches Pydantic `ValidationError` at the middleware level and reformats to `ToolError`. Whole-batch validation continues to work through this path.
- **Parameterized description fragments** — Phase 53 established `_STRIPPING_NOTE`, `_DATE_INPUT_NOTE` as shared fragments. Phase 54 extends this with `{placeholder}` parameterization for tool-specific values.

### Integration Points
- **Handler `len(items) != 1` guards** — remove these (lines 133 and 160 in `handlers.py`). Replace with natural loop over all items.
- **`AddTaskResult` / `EditTaskResult`** — replace `success: bool` with `status: Literal["success", "error", "skipped"]`, make `id`/`name`/`error` optional.
- **`ADD_TASKS_BATCH_LIMIT` / `EDIT_TASKS_BATCH_LIMIT`** error messages — update to reflect max-50 limit instead of "exactly 1 item" restriction.
- **Test suite** — existing `test_add_tasks_single_item_constraint()` and `test_edit_tasks_rejects_multi_item_array()` need rewriting for batch scenarios.

</code_context>

<specifics>
## Specific Ideas

- The handler loop is trivially simple for add_tasks (best-effort): wrap each `service.add_task(command)` in try/except, always continue. For edit_tasks (fail-fast): break on first exception, mark remaining as skipped.
- `failed_idx` variable in edit handler: set on first error, used in skip message format string. One variable, zero complexity.
- Consider whether `AddTaskResult` and `EditTaskResult` should remain separate models (current pattern) or merge into a shared `BatchItemResult` — they now have identical fields. Decision deferred to Claude's discretion.
- Parameterized fragments: consider something like `_BATCH_ITEMS_NOTE = "Up to {max} items per call. {failure_mode}. Each item returns status: success, error, or skipped."` with `.format(max=MAX_BATCH_SIZE, failure_mode=...)`.
- The `_WRITE_RETURNS` constant currently says `"Returns: [{success, id, name, warnings?}]"` — needs updating to the new status-based shape.

</specifics>

<deferred>
## Deferred Ideas

- **Return full task object in edit response** — intentionally unmapped todo. Waiting for real-world usage data. Current minimal response (`id`, `name`, `warnings`) is fine with write-through sync making follow-up `get_task` fast.
- **Serial execution guarantee across concurrent batch calls** — v1.6 concern. Documented as known limitation in tool description.
- **Cross-item references in batch** — documented as unsupported. If agent needs 4-level hierarchy, it makes 4 sequential calls.

### Reviewed Todos (not folded)
- "Consider returning full task object in edit_tasks response" — intentionally unmapped; waiting for real-world usage data (see decision in todo file)
- "Investigate and enforce serial execution guarantee for bridge calls" — v1.6 scope, not v1.4
- "Field selection with curated defaults for read tools" — already shipped in Phase 53
- "Null-stripping for read tool responses" — already shipped in Phase 53

</deferred>

---

*Phase: 54-batch-processing*
*Context gathered: 2026-04-15*
