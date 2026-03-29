---
created: 2026-03-29T17:17:07.866Z
title: Migrate write tools to typed params with validation middleware
area: server
files:
  - src/omnifocus_operator/server.py
  - .research/deep-dives/fastmcp-middleware-validation/FINDINGS.md
---

## Problem

Write tools (`add_tasks`, `edit_tasks`) use `items: list[dict[str, Any]]` signatures, exposing a near-empty inputSchema to agents (2 fields). Agents get no structural guidance on available fields, types, or required params. Handlers contain manual `model_validate()` + try/except boilerplate.

## Solution

Implement "Approach 1" from the fastmcp-middleware-validation research (FINDINGS.md):

1. Add `ValidationReformatterMiddleware` — catches `ValidationError` from typed param validation, reformats via `_format_validation_errors`, raises `ToolError`
2. Move `_format_validation_errors` out of `server.py` into middleware module. Improve UNSET filtering to use `ctx`-based matching instead of string matching.
3. Change handler signatures: `items: list[dict[str, Any]]` → `items: list[AddTaskCommand]` / `items: list[EditTaskCommand]`
4. Remove try/except + `model_validate()` from handler bodies
5. Restructure tool docstrings — remove structural field docs (now redundant with rich schema), keep behavioral docs (patch semantics, frequency guidance, examples)
6. Strip `items.0.` loc prefix in error formatter for agent-facing parity
7. Update tests asserting on validation error paths (errors arrive as `ToolError` from middleware instead of `ValueError` from handler)

Research validated E2E: 12/12 add, 15/15 edit, 10/12 integration scenarios pass. Rich schema exposes 52-61 fields/enums/refs.
