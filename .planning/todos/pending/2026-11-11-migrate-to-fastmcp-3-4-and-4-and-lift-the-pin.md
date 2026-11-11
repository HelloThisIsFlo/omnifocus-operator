---
created: 2026-11-11T19:39:51.104Z
title: Migrate to FastMCP 3.4+ and 4 and lift the pin
area: server
severity: major
files:
  - pyproject.toml (fastmcp>=3.1.1,<3.4)
  - src/omnifocus_operator/middleware.py (ValidationReformatterMiddleware)
  - tests/test_server.py
---

## Problem

`uvx` resolves dependencies fresh from PyPI and ignores `uv.lock`, so the old open-ended `fastmcp>=3.1.1` let every user drift onto versions the suite never ran against. Found 2026-11-10 when the installed server turned out to be running FastMCP 4.1.8.

**Full-suite results per FastMCP version (2026-11-11, clean `main`):**
- 3.1.1, 3.2.4, 3.3.1 → green
- **3.4.11 → 11 failures.** All "clean error" tests: `ValidationReformatterMiddleware` no longer catches the validation error, so agents get raw Pydantic text ("Extra inputs are not permitted…") instead of `Unknown field 'bogusField'`. Includes `TestCanaryMiddleware::test_canary_middleware_catches_validation_error`.
- **4.1.8 → same breakage**, plus MCP SDK 1.26 → 2.3 (field renames such as `protocolVersion` → `protocol_version`; starlette 1.x; new `mcp-types` package).

**Temporary fix shipped to `main`:** `fastmcp>=3.1.1,<3.4`, lock at 3.3.1 (commit `b51a888b`). Published v1.4.4 still has the open bound until a release goes out.

The pin must not become permanent: upstream fixes land only on newer lines.

## Solution

- Find how 3.4+ surfaces invalid tool input (the logging middleware shows `1 validation error for call[add_tasks]`; FastMCP's own server logs `Invalid arguments for tool`) and adapt the reformatter so the teaching messages come back.
- Then move to 4.x: run the suite, fix SDK 2 renames, check anything the suite does not cover (lifespan, stdio transport, progress notifications, output schema — run `tests/test_output_schema.py`).
- Exit condition: suite green on the newest 4.x, pin becomes `>=4,<5`, release.
- Keep testing the **upper edge** of the declared range, not just the lock (e.g. `uv run --with 'fastmcp==X' pytest`); consider a CI job for it.
- Watch for the venv hiccup seen on 2026-11-11: `fastmcp` and `fastmcp-slim` share a folder; after a lock change, "cannot import name 'FastMCP'" → `uv sync --reinstall-package fastmcp --reinstall-package fastmcp-slim`.
