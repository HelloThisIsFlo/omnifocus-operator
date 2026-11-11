---
phase: 261111-wdz
plan: 01
mode: quick
status: complete
subsystem: server / middleware / dependencies
tags: [fastmcp, dependency, middleware, validation, mcp-sdk-v2, warnings]
requires: []
provides:
  - "fastmcp>=4,<5 (locked fastmcp 4.1.8, mcp 2.3.0)"
  - "ValidationReformatterMiddleware unwrapping FastMCP's wrapped validation error"
  - "pytest gate: error::fastmcp.FastMCPDeprecationWarning"
affects: [release v1.x (orchestrator-owned), uvx users on FastMCP 4]
tech-stack:
  added: []
  patterns:
    - "Catch fastmcp.exceptions.ValidationError, format its Pydantic __cause__, re-raise anything else unchanged"
    - "FastMCP deprecations are test failures (filterwarnings error entry)"
key-files:
  created: []
  modified:
    - pyproject.toml
    - uv.lock
    - src/omnifocus_operator/middleware.py
    - src/omnifocus_operator/server/handlers.py
    - tests/test_middleware.py
    - tests/test_server.py
    - CONTRIBUTING.md
decisions:
  - "Middleware handles the FastMCP 4 wrapped shape only; the bare-Pydantic except branch is removed (DD-1)"
  - "Tool-body Pydantic errors are not reformatted; private _ToolBodyError untouched (DD-2)"
  - "Drift gate scoped to fastmcp.FastMCPDeprecationWarning only (DD-3)"
  - "MCP SDK v2 snake_case names in source and tests (DD-4)"
metrics:
  duration: "~8 min"
  completed: 2026-11-11
estimate:
  tokens: 60000
  tasks: 3
actuals:
  tokens: 18000
  tasks: 3
  commits: 4
plan_head_before: 31c163927de84f6dea25e6fe3b79c401ea6446aa
plan_head_after: 80f55656413a4f0f2b44eeb55b66e8ede9e70f69
---

# Quick 261111-wdz: FastMCP 4, teaching messages restored

**FastMCP 4.1.8 / MCP SDK 2.3.0 locked; the middleware unwraps FastMCP's wrapped `ValidationError` so agents get `Unknown field '…'`-style messages again; FastMCP deprecations now fail the suite.**

## 📦 Resolved versions

- `pyproject.toml` → `fastmcp>=4,<5`
- `uv.lock` → **fastmcp 4.1.8**, fastmcp-slim 4.1.8, **mcp 2.3.0**, mcp-types 2.3.0
  - 4.1.8 = newest on PyPI (`info.version`, checked at execution time)
  - Transitive churn as planned: starlette 0.52.1 → 1.10.0; httpx/httpcore/httpx-sse → httpx2/httpcore2/httpx2-jsfetch; truststore added; keyring + jaraco/secretstorage/jeepney/more-itertools/pywin32-ctypes dropped
  - Also bumped transitively (not listed at planning time): aiofile, caio, certifi, idna, openapi-pydantic, py-key-value-aio, uncalled-for; beartype now locks two versions
- `uv lock --check` passes

## 🧩 Middleware shape (final)

```python
except FastMCPValidationError as exc:
    cause = exc.__cause__
    if not isinstance(cause, ValidationError):  # pydantic
        raise
    messages = _format_validation_errors(cause)
    raise ToolError("; ".join(messages) or INVALID_INPUT) from None
```

- Bare-Pydantic branch deleted; helpers unchanged; docstring describes the FastMCP 4 shape

## ✅ Results

- Full suite: **2586 passed**, zero warnings (baseline 2583 + 3 new middleware tests)
- `FASTMCP_MCP_CAMELCASE_COMPAT=false` full run: **2586 passed**
- `tests/test_output_schema.py`: 35 passed
- `uv run mypy src/`: clean; ruff check/format clean
- `just ci`: **passed** (2586 tests, coverage 97.57%)
- Gate probe (temp dir outside repo, reads `ToolAnnotations.readOnlyHint`, run with repo config): **failed with `FastMCPDeprecationWarning`** as intended; probe deleted
- `git diff ca06ac18 -- tests/test_server.py`: 31 attribute renames + canary docstring; 0 `pytest.raises` / `match=` lines changed

## 🧾 Commits

| Task | Commit | What |
|---|---|---|
| 1 (RED) | f1afcc6e | `TestValidationReformatterMiddleware` (wrapped → ToolError; no cause / non-Pydantic cause → same object) |
| 1 (GREEN) | b4b19e5a | FastMCP 4 bump + lock, middleware unwrap, `handlers.py` snake_case `ToolAnnotations` (one commit: pre-commit mypy) |
| 2 | f7e7a27a | SDK v2 attribute reads in `tests/test_server.py`, canary docstring, deprecation error filter |
| 3 | 80f55656 | `CONTRIBUTING.md` names FastMCP 4 |

## TDD Gate Compliance

- RED: f1afcc6e — wrapped-form test failed on FastMCP 3.3.1 code (1 failed, 2 passed: the propagation tests already held)
- GREEN: b4b19e5a — all three pass

## ⚠️ Owner's manual check

- stdio transport and the real lifespan are **not covered by the suite** and cannot be smoke-tested by an agent: the lifespan builds the real Bridge (SAFE-01/02). The post-release `uvx` check covers them.

## Deviations from Plan

None in substance.
- Tooling only: BSD `sed` ignores `\b`, so the test renames used `perl -pi`; result identical to the plan's intent.

## Self-Check: PASSED

- Files exist: pyproject.toml, uv.lock, middleware.py, handlers.py, test_middleware.py, test_server.py, CONTRIBUTING.md
- Commits f1afcc6e, b4b19e5a, f7e7a27a, 80f55656 are ancestors of HEAD
