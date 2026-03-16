# Milestone v1.2.2 -- FastMCP v3 Migration

## Goal

Migrate from the built-in `mcp.server.fastmcp` to the standalone `fastmcp>=3` package. Fixes broken logging (protocol-level `ctx.info()`/`ctx.warning()` instead of file-based workaround), unlocks better middleware/lifecycle support, and aligns with the actively maintained package. No new tools, no behavioral changes -- infrastructure upgrade.

## What to Build

### Dependency Swap

- Replace `from mcp.server.fastmcp import Context, FastMCP` with `from fastmcp import FastMCP, Context`
- Add `fastmcp>=3` to dependencies (replaces implicit use via `mcp` SDK)
- Review FastMCP v3 migration guide for API changes (lifespan, tool registration, settings)
- Update all imports in tests

### Logging Migration

The main driver. Currently `stdio_server()` hijacks stderr, making `logging.getLogger()` useless during tool execution. The workaround is a file-based `logging.FileHandler` writing to `~/Library/Logs/omnifocus-operator.log`.

**Fix:** Migrate to `ctx.info()` / `ctx.warning()` protocol-level logging. These messages flow through the MCP protocol to the client, visible in Claude Desktop / agent logs. Remove the file-based logging workaround.

### Documentation Updates

- Update README.md and landing page: runtime dependency changes from `mcp>=1.26.0` to `fastmcp>=3`
- Update "single runtime dependency" messaging (still one dep, just a different one)
- Update Claude Desktop config example if entry point changes

See: `2026-03-10-migrate-to-fastmcp-v3-standalone-package.md`

## Key Acceptance Criteria

- Server starts and all tools work with `fastmcp>=3`
- `ctx.info()` and `ctx.warning()` messages appear in client logs
- File-based logging workaround removed
- All existing tests pass
- README and landing page reflect new dependency
- No new tools, no behavioral changes

## Tools After This Milestone

Six (unchanged from v1.2): `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`.
