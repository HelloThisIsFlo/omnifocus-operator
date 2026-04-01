---
created: 2026-03-29T17:17:07.866Z
title: Migrate write tools to typed params with validation middleware
area: server
files:
  - src/omnifocus_operator/server.py
  - src/omnifocus_operator/middleware.py
  - .research/deep-dives/fastmcp-middleware-validation/FINDINGS.md
---

## Problem

Write tools (`add_tasks`, `edit_tasks`) use `items: list[dict[str, Any]]` signatures, exposing a near-empty inputSchema to agents (2 fields). Agents get no structural guidance on available fields, types, or required params. Handlers contain manual `model_validate()` + try/except boilerplate.

## Solution

Implement "Approach 1" from the fastmcp-middleware-validation research (FINDINGS.md):

1. Add `ValidationReformatterMiddleware` to existing `middleware.py` — catches `ValidationError` from typed param validation, reformats via `_format_validation_errors`, raises `ToolError`
2. Move `_format_validation_errors` out of `server.py` into `middleware.py`. Improve UNSET filtering to use `ctx`-based matching (`e.get("ctx", {}).get("class") == "_Unset"`) instead of fragile string matching.
3. Change handler signatures: `items: list[dict[str, Any]]` → `items: list[AddTaskCommand]` / `items: list[EditTaskCommand]`
4. Remove try/except + `model_validate()` from handler bodies
5. Strip `items.N.` loc prefix — rewrite to readable `"Task {N}: {field}"` format (future-proof for batches)
6. Update tests asserting on validation error paths

Research validated E2E: 12/12 add, 15/15 edit, 10/12 integration scenarios pass. Rich schema exposes 52-61 fields/enums/refs.

## Decisions (brainstormed 2026-03-31)

### Batch limit stays at handler level
The `if len(items) != 1` check stays in the handler, not as `max_length=1` on the list param. It's temporary scaffolding — no need to bake it into the schema where it becomes a contract agents cache. No hard upper limit needed either; bridge throughput is self-regulating.

### Don't touch docstrings yet
Leave the 45-55 line field-listing docstrings as-is during this migration. After Phase 37 completes and the typed params are live, inspect the actual agent experience via MCP Inspector, then iterate on docstring density in a follow-up. The concern: some agents rely on docstrings more than inputSchema, so we want to see it in practice before cutting content.

### Error location prefix: "Task N: field" format
Use `f"Task {idx+1}: {field}"` instead of raw `items.0.field` or stripped `field`. This is readable for batch-of-1 ("Task 1: dueDate") and scales to future batch support without code changes. One-liner in the formatter.

### Middleware module placement
`ValidationReformatterMiddleware` goes in the existing `src/omnifocus_operator/middleware.py` alongside `ToolLoggingMiddleware`. `_format_validation_errors` and `_clean_loc` move there too (they're middleware concerns, not server concerns).

### Test impact is limited
Server tests (`test_server.py`) already assert `ToolError` (FastMCP wraps `ValueError` → `ToolError`). The middleware produces `ToolError` directly — same type, same messages. Main changes: error paths through middleware instead of handler try/except. Service tests (`test_service.py`) are unaffected (service layer untouched).

### PydanticJsonSchemaWarning
When FastMCP generates schema for `list[AddTaskCommand]`, Pydantic warns about UNSET defaults not being JSON-serializable. Expected and correct (UNSET excluded from schema). Executor should suppress this — either in the middleware module or in `create_server()`. Low risk.

### Canary test
FINDINGS.md recommends a canary test: verify that FastMCP's validation still happens inside `call_next()` (i.e., the middleware can catch it). This guards against a future FastMCP version moving validation before middleware. Simple assertion that the middleware receives and reformats a `ValidationError`.

## Not in scope
- Docstring restructuring (follow-up after MCP Inspector review)
- Custom UNSET error type (`custom_error_schema`) — optional enhancement, separate decision
- Batch support expansion — separate todo
- `strict_input_validation` on FastMCP (Pydantic lax mode coercion like `flagged: "yes"` → `True` is acceptable)
