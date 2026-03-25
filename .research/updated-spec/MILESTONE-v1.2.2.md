# Milestone v1.2.2 -- FastMCP v3 Migration

## Goal

Migrate from the built-in `mcp.server.fastmcp` to the standalone `fastmcp>=3` package. Primary drivers: test client simplification (~70 lines of plumbing → 3 lines) and automatic middleware (replaces manual `log_tool_call()` wiring). Also unlocks progress reporting for batch operations. Logging improvements are bundled but SDK-independent. No new tools, no behavioral changes -- infrastructure upgrade.

## What to Build

### Dependency Swap

- Replace `from mcp.server.fastmcp import Context, FastMCP` with `from fastmcp import FastMCP, Context`
- Add `fastmcp>=3` to dependencies (replaces implicit use via `mcp` SDK)
- Replace `ctx.request_context.lifespan_context` → `ctx.lifespan_context` across all 6 tool handlers (v3 shortcut)
- Review FastMCP v3 migration guide for API changes (lifespan, tool registration, settings)
- Update all imports in tests

### Logging Rework

Not a migration driver -- works identically on both SDKs. Bundled in this milestone because the current setup is based on a misdiagnosis.

**Background:** `__main__.py:15` says "stdio_server() hijacks stderr" -- this was wrong. Neither SDK touches stderr. The real issue was Claude Code swallowing stderr during tool execution (issue [#29035](https://github.com/anthropics/claude-code/issues/29035)). `StreamHandler(stderr)` was always safe.

**Fix:** Dual-handler logging:
- **Primary:** `StreamHandler(stderr)` -- visible in Claude Desktop's log page
- **Fallback:** `FileHandler(~/Library/Logs/omnifocus-operator.log)` -- for Claude Code debugging (stderr invisible during tool calls)
- Both handlers on the same logger, both always active

**Do NOT use** `ctx.info()` / `ctx.warning()` -- protocol-level `notifications/message` that no major client renders. Claude Code closed the feature request as "not planned" ([#3174](https://github.com/anthropics/claude-code/issues/3174)). Claude Desktop only shows them in raw dev logs. Dead end.

**Logger hierarchy:** `omnifocus_operator`, `omnifocus_operator.service`, `omnifocus_operator.service.add_tasks`, etc.

**Formats:**
- stderr (live debugging): `%(asctime)s %(levelname)-8s [%(name)s] %(message)s` with `datefmt="%H:%M:%S"`
- File (persistent, cross-session): `%(asctime)s %(levelname)-8s [%(name)s] %(message)s` (default `asctime` with date)

**Cleanup:**
- Remove the stderr hijacking misdiagnosis comment in `__main__.py:15`
- Remove `propagate = False` / `FileHandler`-only setup from `__main__.py`

### Test Client Migration

The biggest DX win. Replace ~70 lines of manual test plumbing with FastMCP v3's built-in `Client`.

**Delete:**
- `_ClientSessionProxy` class (conftest.py, ~40 lines) -- memory streams, task groups, manual session management
- `run_with_client` helper (test_server.py, ~30 lines)
- `anyio`, `ClientSession`, `SessionMessage` imports from test infra

**Replace with:**
```python
async with Client(server) as client:
    result = await client.call_tool("tool", {})
```

**Adaptation points (not blockers):**
- Error handling: v3 test client raises `ToolError` instead of returning `CallToolResult(is_error=True)` -- update test assertions
- List returns: `result.data` returns Pydantic `Root()` objects instead of raw dicts -- update extraction pattern

### Middleware

Replace manual `log_tool_call()` function + 6 explicit call sites with automatic `ToolLoggingMiddleware`.

**Delete:**
- `log_tool_call()` (server.py:53-63)
- All 6 `log_tool_call("tool_name", ...)` calls at the top of each tool handler

**Replace with:**
- `ToolLoggingMiddleware` class using `on_call_tool` hook
- Two instances: one with stderr logger, one with file logger -- both fire automatically on every tool call
- Logs entry with args, exit with elapsed time, errors with exception details

Reference implementation: `.research/deep-dives/fastmcp-spike/experiments/05_middleware.py`

### Progress Reporting

Add `ctx.report_progress()` to `add_tasks` / `edit_tasks` batch loops.

- Works beautifully in Claude Code CLI (real progress bar with percentage)
- No-ops gracefully when client doesn't send `progressToken` -- no fallback needed
- Invisible in Claude Desktop, no harm

### Documentation Updates

- Update README.md and landing page: runtime dependency changes from `mcp>=1.26.0` to `fastmcp>=3`
- Update "single runtime dependency" messaging (still one dep, just a different one)
- Update Claude Desktop config example if entry point changes

## Key Acceptance Criteria

- Server starts and all tools work with `fastmcp>=3`
- Dual logging in place: `StreamHandler(stderr)` + `FileHandler`
- `ctx.info()`/`ctx.warning()` NOT used anywhere
- stderr hijacking misdiagnosis comment removed from `__main__.py`
- `_ClientSessionProxy` and `run_with_client` deleted, replaced by `Client(server)`
- `log_tool_call()` and all 6 call sites deleted, replaced by `ToolLoggingMiddleware`
- `ctx.report_progress()` in batch operations
- `ctx.lifespan_context` shorthand across all tool handlers
- All existing tests pass (updated for new test client patterns)
- README and landing page reflect new dependency
- No new tools, no behavioral changes

## Spike Reference

Decisions in this spec are backed by the FastMCP v3 spike (8 experiments, 2026-03-24):
- **FINDINGS.md:** `.research/deep-dives/fastmcp-spike/FINDINGS.md`
- **Experiments:** `.research/deep-dives/fastmcp-spike/experiments/`

| Section | Informed by |
|---------|-------------|
| Dependency Swap | Exp 01 (Server & Context) |
| Logging Rework | Exp 02 (Client vs Server Logging), Exp 03 (stderr Hijacking) |
| Test Client Migration | Exp 04 (Test Client) |
| Middleware | Exp 05 (Middleware) |
| Progress Reporting | Exp 06 (Progress) |
| -- | Exp 07 (DI): Keep lifespan, no changes needed |
| -- | Exp 08 (Elicitation): Future milestone, not now |

See: `2026-03-10-migrate-to-fastmcp-v3-standalone-package.md`

## Tools After This Milestone

Six (unchanged from v1.2): `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`.
