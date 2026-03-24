# Feature Landscape

**Domain:** FastMCP v3 migration for OmniFocus MCP server (v1.2.2)
**Researched:** 2026-03-24

## Table Stakes

Features the migration MUST deliver. Without these, the migration is pointless or broken.

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| Import swap: `mcp.server.fastmcp` -> `fastmcp` | The entire point of the migration. Two import sites in `server.py`, five in tests | Low | `fastmcp>=3.0.0` in deps |
| Dep swap: `mcp>=1.26.0` -> `fastmcp>=3.0.0` in pyproject.toml | fastmcp depends on mcp transitively, so mcp stays available but is no longer the direct dep | Low | None |
| Protocol-level logging: `ctx.info()` / `ctx.warning()` / `ctx.error()` | Replaces the FileHandler workaround in `__main__.py`. Messages flow to the MCP client (Claude Desktop) via protocol notifications instead of writing to `~/Library/Logs/` | Med | Context available in all tool handlers (already is) |
| Existing tool behavior preserved | All 6 tools must behave identically. No behavioral changes in this milestone | Low | Comprehensive test suite (697 tests) catches regressions |
| Lifespan pattern compatibility | Current `@asynccontextmanager` lifespan works in fastmcp v3 -- confirmed backward-compatible. `ContextManagerLifespan` wrapper exists if composition needed later | Low | None -- existing pattern is compatible |
| ToolAnnotations still importable | `ToolAnnotations` stays at `mcp.types.ToolAnnotations` or can be passed as dict. Both work in fastmcp v3 | Low | mcp is transitive dep of fastmcp |
| Context type change: `Context[Any, Any, Any]` -> `Context` | Bundled version uses `Context[ServerDeps, ClientDeps, LifespanContext]` generic. Standalone uses plain `Context` | Low | Update type annotations in all 6 tool handlers |

## Differentiators

Features unlocked by the migration that go beyond parity. Not required for v1.2.2 but available.

| Feature | Value Proposition | Complexity | When to Use |
|---------|-------------------|------------|-------------|
| `ctx.lifespan_context` direct property | Bundled: `ctx.request_context.lifespan_context["service"]`. Standalone adds `ctx.lifespan_context["service"]` shortcut. Cleaner, with fallback behavior for edge cases | Low | Adopt immediately during migration -- simpler access pattern |
| Middleware framework | Logging, timing, rate limiting, error handling, caching -- all as composable middleware. `mcp.add_middleware(LoggingMiddleware())` | Med-High | v1.6 production hardening, not v1.2.2 |
| Dependency injection via `Depends()` | Hide parameters from LLM schema, inject services at runtime. Could replace manual `ctx.lifespan_context` dict access | Med | Future milestone when DI simplifies tool signatures |
| Decorated functions remain callable | `@mcp.tool` returns the original function in v3 (not a component object). Enables direct function testing without MCP server | Low | Testing improvement -- can unit test tool functions directly |
| Tool timeout parameter | `@mcp.tool(timeout=30.0)` -- server-side execution time limit | Low | v1.6 production hardening |
| Tool versioning | `@mcp.tool(version="1.0")` -- version metadata for tools | Low | Future, when tool API evolves |
| Composable lifespans | `lifespan=db_lifespan | cache_lifespan` -- combine multiple lifespans with `|` operator | Low | Future, if startup gets complex |
| Component visibility control | `mcp.disable(tags={"admin"})` -- dynamically show/hide tools | Low | Future, if admin/debug tools added |
| Structured output (`structuredContent`) | Tool returns produce both text and machine-parseable JSON automatically | Low | Already happens for Pydantic model returns; may improve agent parsing |
| `mask_error_details=True` | Hide internal exception details from clients while preserving `ToolError` messages | Low | v1.6 production hardening |
| Session state: `ctx.set_state()` / `ctx.get_state()` | Per-session state persisting across tool calls | Med | Future, if agent session tracking needed |
| ToolAnnotations as dict | `@mcp.tool(annotations={"readOnlyHint": True})` -- dict shorthand instead of importing ToolAnnotations class | Low | Cosmetic simplification during migration |

## Anti-Features

Features to explicitly NOT adopt in v1.2.2.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full middleware stack | Adds complexity for zero current need. The server has 6 tools, no auth, single-user local process. Middleware is for v1.6 hardening | Keep direct tool implementations. Note middleware availability for future |
| Dependency injection (`Depends()`) for service access | Current `ctx.lifespan_context["service"]` pattern is explicit and well-understood. DI adds indirection for no functional gain at this scale | Keep lifespan context dict access, optionally adopt `ctx.lifespan_context` shorthand |
| HTTP/SSE transport | Project is stdio-only by design (macOS local server). HTTP transport adds attack surface and deps for no benefit | Keep `server.run(transport="stdio")` |
| `FASTMCP_DECORATOR_MODE=object` compat mode | Deprecated v2 compatibility flag. Don't use; go directly to v3 behavior | Use v3 decorator behavior (functions remain callable) |
| Switching to `@lifespan` decorator from `@asynccontextmanager` | The `@lifespan` decorator is new in v3 but `@asynccontextmanager` is fully backward-compatible. Switching is churn for zero benefit | Keep `@asynccontextmanager` pattern, which is already correct |
| Remove FileHandler logging entirely | Protocol logging (`ctx.info`) only works during tool calls. Server startup, IPC sweep, shutdown logging still needs a file target or stderr. FileHandler is still useful for lifecycle events outside tool context | Keep FileHandler for startup/shutdown. Use `ctx.info`/`ctx.warning` for in-tool logging that reaches the agent |
| Aggressive dependency trimming | fastmcp has ~20 runtime deps (vs 1 before). Attempting to pin or strip optional deps is fragile | Accept the dependency footprint. fastmcp is the community standard. Update README badge from "Dependencies 1" to reflect reality |
| Adopting `ToolError` exception class | fastmcp provides `ToolError` for structured error responses. Current pattern uses `ValueError` with educational messages, which works fine | Keep `ValueError` pattern. Evaluate `ToolError` in v1.3+ when error handling matures |

## Feature Dependencies

```
Import swap (server.py)
  -- Requires: fastmcp>=3.0.0 in pyproject.toml
  -- Parallel with: test import updates
  -- Blocks: everything else (logging, context changes)

Test import updates (tests/)
  -- Requires: fastmcp>=3.0.0 in pyproject.toml
  -- Parallel with: server import swap
  -- Note: mcp.client.session, mcp.shared.message may stay as-is
           (fastmcp re-exports some but not all mcp internals)

Context type simplification
  -- Requires: import swap complete
  -- Context[Any, Any, Any] -> Context (plain)
  -- Affects: all 6 tool handler signatures

Lifespan context access update
  -- Requires: Context type change
  -- ctx.request_context.lifespan_context["service"]
     -> ctx.lifespan_context["service"]
  -- Optional but recommended: cleaner access pattern

Protocol-level logging migration
  -- Requires: Context available in tool handlers (already is)
  -- Parallel with: lifespan context update
  -- Pattern: replace `logger.debug("server.get_all: ...")` with
     `await ctx.info("Returning N tasks, N projects, N tags")`
  -- Keep: FileHandler for startup/shutdown logging (outside tool context)
  -- Key decision: which log calls become protocol messages (agent-visible)
     vs stay as file-only (developer-visible)

Documentation updates
  -- Requires: all code changes complete
  -- README: dependency badge, import examples
  -- Landing page: reflect fastmcp as framework
```

**Critical path:** dep swap -> import swap + test imports (parallel) -> context simplification -> logging migration -> docs

## Logging Migration Detail

Current logging has two audiences with different needs:

### Developer logs (keep as FileHandler)
- Server startup/shutdown lifecycle
- IPC sweep status
- Repository type selection
- Fatal startup errors
- Debug-level details (returned task count, validation errors)

### Agent-visible logs (migrate to ctx.info/ctx.warning)
- Tool invocation confirmations
- Summary of returned data (e.g., "Returning 2400 tasks, 363 projects")
- Validation warnings (unknown fields, lifecycle hints)
- Write operation results

### Dual logging strategy
```python
# Before (all goes to file)
logger.debug("server.get_all: returning tasks=%d", len(result.tasks))

# After (agent sees the important bits, file gets everything)
logger.debug("get_all: tasks=%d, projects=%d", len(result.tasks), len(result.projects))
await ctx.info(f"Returning {len(result.tasks)} tasks, {len(result.projects)} projects")
```

This is NOT a binary switch. Both channels serve different purposes.

## Dependency Impact Assessment

| Metric | Before (`mcp>=1.26.0`) | After (`fastmcp>=3.0.0`) |
|--------|------------------------|--------------------------|
| Direct runtime deps | 1 | 1 (fastmcp, which depends on mcp) |
| Transitive deps | ~12 (via mcp) | ~30+ (via fastmcp -> mcp + fastmcp extras) |
| Notable new transitive deps | -- | rich, pyyaml, watchfiles, opentelemetry-api, authlib, pyperclip |
| README badge | "Dependencies 1" | Still technically 1 direct dep, but heavier tree |
| Install size impact | Minimal | Moderate increase |

**Verdict:** The dependency increase is real but acceptable. fastmcp is the de facto standard (claims 70% of MCP servers). The transitive deps are well-maintained libraries. The README badge can stay "Dependencies 1" (direct dep count) or be updated to be more honest.

## Lifespan Behavior Note

**Important discovery:** In MCP's Python SDK (which fastmcp wraps), lifespan runs per-session (per client connection), NOT per-application like FastAPI. This is the same behavior in both bundled and standalone versions. For stdio transport with a single client (Claude Desktop), this is effectively per-application. No migration concern here, but worth documenting for future HTTP transport considerations.

## MVP Recommendation

**Phase 1 -- Dependency and import swap:**
1. Replace `mcp>=1.26.0` with `fastmcp>=3.0.0` in pyproject.toml
2. Update `server.py`: `from fastmcp import FastMCP, Context`
3. Update `server.py`: `Context[Any, Any, Any]` -> `Context` in all 6 handlers
4. Update test files: `from fastmcp import FastMCP` where applicable
5. Verify: `uv run pytest` -- all 697 tests pass

**Phase 2 -- Context and logging migration:**
6. Adopt `ctx.lifespan_context["service"]` shorthand (replace `ctx.request_context.lifespan_context`)
7. Add `await ctx.info()` / `await ctx.warning()` calls for agent-visible logging in tool handlers
8. Keep FileHandler for lifecycle logging (startup, shutdown, IPC sweep)
9. Remove or reduce file-only logging in tool handlers where protocol logging replaces it

**Phase 3 -- Documentation:**
10. Update README dependency badge
11. Update landing page framework reference
12. Update any install/setup instructions

**Defer to future milestones:**
- Middleware (v1.6)
- Dependency injection (when DI simplifies code)
- Tool timeouts (v1.6)
- HTTP transport (out of scope)

## Sources

- [FastMCP migration guide (from MCP SDK)](https://gofastmcp.com/getting-started/upgrading/from-mcp-sdk) -- official upgrade path, HIGH confidence
- [FastMCP Context API](https://gofastmcp.com/servers/context) -- ctx.info/warning/error signatures, HIGH confidence
- [FastMCP Context API reference](https://gofastmcp.com/python-sdk/fastmcp-server-context) -- lifespan_context property, method signatures, HIGH confidence
- [FastMCP tools documentation](https://gofastmcp.com/servers/tools) -- tool registration, annotations, ToolResult, HIGH confidence
- [FastMCP middleware documentation](https://gofastmcp.com/servers/middleware) -- middleware framework overview, HIGH confidence
- [FastMCP 3.0 what's new](https://www.jlowin.dev/blog/fastmcp-3-whats-new) -- breaking changes, new features, HIGH confidence
- [FastMCP lifespan documentation](https://gofastmcp.com/servers/lifespan) -- composable lifespans, @lifespan decorator, HIGH confidence
- [FastMCP PyPI](https://pypi.org/project/fastmcp/) -- version 3.1.1 latest, deps list, HIGH confidence
- [Lifespan per-session behavior (GitHub issue #1115)](https://github.com/jlowin/fastmcp/issues/1115) -- lifespan is per-session not per-app, confirmed by maintainer, HIGH confidence
- Local verification: `uv run pip show fastmcp`, `uv run pip show mcp`, introspection of bundled Context class methods and signatures
