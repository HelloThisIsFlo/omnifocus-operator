# Architecture Patterns: FastMCP v3 Migration

**Domain:** MCP server dependency migration (`mcp.server.fastmcp` -> standalone `fastmcp>=3`)
**Researched:** 2026-03-24
**Confidence:** HIGH -- verified against official docs (gofastmcp.com), PyPI, GitHub

## Executive Summary

The migration is architecturally clean. The three-layer architecture is unaffected. Changes are concentrated in:

1. **Import paths** -- `from mcp.server.fastmcp` -> `from fastmcp`
2. **Context access** -- `ctx.request_context.lifespan_context["key"]` -> `ctx.lifespan_context["key"]`
3. **Context type** -- `Context[Any, Any, Any]` -> `Context` (no generics)
4. **Logging** -- file-based `logging.FileHandler` workaround -> protocol-level `await ctx.info()`/`await ctx.warning()`
5. **Dependency** -- `mcp>=1.26.0` -> `fastmcp>=3.1,<4` (which depends on `mcp>=1.24.0,<2.0` internally)

Service layer, repository layer, bridge layer, contracts, models -- all untouched.

## Dependency Relationship

```
BEFORE:
  pyproject.toml: dependencies = ["mcp>=1.26.0"]
  FastMCP class comes FROM mcp SDK (bundled copy of FastMCP 1.0)

AFTER:
  pyproject.toml: dependencies = ["fastmcp>=3.1,<4"]
  fastmcp package depends on mcp>=1.24.0,<2.0 internally
  mcp.types (ToolAnnotations etc.) still available as transitive dep
  mcp.client.session (ClientSession) still available for tests
  mcp.shared.message (SessionMessage) still available for tests
```

- `fastmcp>=3` is a standalone package (PyPI: `fastmcp`, latest 3.1.1 as of 2026-03-24)
- It includes `mcp` SDK as a dependency, so all `mcp.*` imports still resolve
- No need to declare `mcp` separately -- `fastmcp` brings it
- License: Apache-2.0 (compatible with MIT project)
- Python: >=3.10 (project uses 3.12, no conflict)

**Transitive dependency impact:** fastmcp brings ~19 direct dependencies (httpx, authlib, uvicorn, rich, cyclopts, opentelemetry-api, etc.). Many overlap with what `mcp` already brings. The project goes from 1 declared dep to 1 declared dep with a heavier tree.

## Files That Change

### Production Code

| File | Change Type | What Changes |
|------|-------------|--------------|
| `pyproject.toml` | Modify | `mcp>=1.26.0` -> `fastmcp>=3.1,<4` |
| `src/omnifocus_operator/server.py` | Modify | Imports, Context type, lifespan access, tool logging |
| `src/omnifocus_operator/__main__.py` | Modify | Simplify file-based logging (keep for lifecycle, reduce for tools) |

### Test Code

| File | Change Type | What Changes |
|------|-------------|--------------|
| `tests/conftest.py` | Modify | `from mcp.server.fastmcp import FastMCP` -> `from fastmcp import FastMCP` |
| `tests/test_server.py` | Modify | Same import change |
| `tests/test_simulator_bridge.py` | Modify | Same import change |
| `tests/test_simulator_integration.py` | Modify | Same import change |

### Unchanged

- `src/omnifocus_operator/service/` -- no MCP imports
- `src/omnifocus_operator/repository/` -- no MCP imports
- `src/omnifocus_operator/bridge/` -- no MCP imports
- `src/omnifocus_operator/contracts/` -- no MCP imports
- `src/omnifocus_operator/models/` -- no MCP imports
- `src/omnifocus_operator/agent_messages/` -- no MCP imports

## Migration Details

### 1. Import Changes in server.py

```python
# BEFORE
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

# AFTER
from fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations  # stays -- no fastmcp equivalent
```

- `FastMCP` and `Context` move to `from fastmcp import ...`
- `ToolAnnotations` stays at `from mcp.types` (or use dict format as alternative)
- `Context` is no longer generic -- `Context[Any, Any, Any]` becomes just `Context`

### 2. Lifespan (No Change Required)

```python
# Current pattern -- fully compatible with FastMCP v3
@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict[str, object]]:
    # ... setup ...
    yield {"service": service}

mcp = FastMCP("omnifocus-operator", lifespan=app_lifespan)
```

FastMCP v3 also offers `@lifespan` decorator and composable lifespans (`|` operator), but `@asynccontextmanager` works as-is. **Do not rewrite.**

### 3. Context Access in Tool Handlers

```python
# BEFORE
async def get_all(ctx: Context[Any, Any, Any]) -> AllEntities:
    service: OperatorService = ctx.request_context.lifespan_context["service"]

# AFTER
async def get_all(ctx: Context) -> AllEntities:
    service: OperatorService = ctx.lifespan_context["service"]
```

- `ctx.lifespan_context` is a direct property in v3, returns `dict[str, Any]`
- Returns empty dict if no lifespan configured (safe fallback)
- The `.request_context.lifespan_context` chain still exists but `request_context` can be `None`

### 4. Logging Migration

```python
# BEFORE (server.py) -- logging goes to file, invisible to agent
logger.debug("server.get_all: returning tasks=%d, projects=%d", ...)

# AFTER (server.py) -- dual channel
await ctx.info(f"Returning {len(result.tasks)} tasks, {len(result.projects)} projects")
logger.debug("get_all complete")  # optional: file-only for developer debugging
```

Available `ctx` logging methods (all async):
- `await ctx.debug(message)` -- detailed execution info
- `await ctx.info(message)` -- normal execution milestones
- `await ctx.warning(message)` -- non-critical issues
- `await ctx.error(message)` -- recoverable errors

**Keep FileHandler for lifecycle events** (startup, IPC sweep, shutdown) where Context is not available.

### 5. Test Imports (Minimal Change)

```python
# BEFORE (tests/)
from mcp.server.fastmcp import FastMCP

# AFTER
from fastmcp import FastMCP

# These stay unchanged (still available via transitive mcp dep):
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage
```

**Test harness decision: Keep existing pattern for v1.2.2.** The `_ClientSessionProxy` + anyio streams + `_mcp_server.run()` pattern still works because:
- `_mcp_server` attribute still exists in FastMCP v3 (it wraps the low-level `Server`)
- `ClientSession` and `SessionMessage` come from transitive `mcp` dep
- Refactoring to `fastmcp.Client(transport=server)` is a future DX improvement

### 6. Tool Registration (Unchanged)

```python
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def get_all(ctx: Context) -> AllEntities:
    ...
```

Only change: `Context` without generic params. `@mcp.tool()` API is identical.

### 7. Entry Point (Unchanged)

```python
server.run(transport="stdio")
```

`run(transport="stdio")` works identically. Constructor kwargs that moved to `run()` in v3 (host, port, etc.) are irrelevant for stdio transport.

## Component Boundary Diagram

```
BEFORE:                              AFTER:

  pyproject.toml                      pyproject.toml
  deps: [mcp>=1.26.0]                deps: [fastmcp>=3.1,<4]
                                           |
                                           +-- mcp>=1.24.0 (transitive)
                                           +-- httpx, authlib, ... (transitive)

  __main__.py                         __main__.py
  - FileHandler logging               - FileHandler (lifecycle only)
  - server.run("stdio")               - server.run("stdio")  [unchanged]

  server.py                           server.py
  - from mcp.server.fastmcp           - from fastmcp import FastMCP, Context
  - Context[Any,Any,Any]              - Context (no generics)
  - ctx.request_context               - ctx.lifespan_context["service"]
      .lifespan_context["service"]    - await ctx.info/warning/debug/error
  - logger.debug(...)
  - @mcp.tool(annotations=...)        - @mcp.tool(annotations=...)  [unchanged]

  service/ ---- UNCHANGED ----        service/ ---- UNCHANGED ----
  repository/ - UNCHANGED ----        repository/ - UNCHANGED ----
  bridge/ ---- UNCHANGED ----         bridge/ ---- UNCHANGED ----
  contracts/ -- UNCHANGED ----        contracts/ -- UNCHANGED ----
  models/ ----- UNCHANGED ----        models/ ----- UNCHANGED ----
```

## Patterns to Follow

### Pattern 1: Minimal Import Migration
**What:** Change only imports that must change. Leave `mcp.types` and `mcp.client.*` imports alone.
**Why:** `fastmcp` depends on `mcp` and does not re-export `mcp.types`. Don't create unnecessary churn.

### Pattern 2: Dual Logging Strategy
**What:** Keep file-based `logging` for server infrastructure (startup, IPC sweep, shutdown). Use `ctx.info()`/`ctx.warning()` for agent-relevant messages inside tool handlers.
**Why:** Different audiences, different channels. `ctx` methods reach the agent. File logging captures developer diagnostics.

### Pattern 3: Keep Existing Test Harness
**What:** Only change `FastMCP` import paths in test files. Keep `_ClientSessionProxy` + anyio streams pattern.
**Why:** Minimizes migration scope. The pattern still works. Refactoring to `fastmcp.Client` can be done separately.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Importing Everything from fastmcp
**What:** Replacing all `mcp.types` imports with fastmcp equivalents.
**Why bad:** `ToolAnnotations`, `TextContent`, etc. live in `mcp.types`. No `fastmcp.types` equivalent exists.
**Instead:** Only change `FastMCP` and `Context` imports.

### Anti-Pattern 2: Rewriting Lifespan Pattern
**What:** Using `@lifespan` decorator or composable lifespans when `@asynccontextmanager` works.
**Why bad:** Unnecessary diff, imports from internal module path, adds no value.
**Instead:** Keep `@asynccontextmanager` pattern. FastMCP 3 accepts it directly.

### Anti-Pattern 3: Removing File Logging Entirely
**What:** Deleting the FileHandler in `__main__.py` since `ctx` methods exist.
**Why bad:** `ctx` is only available inside tool handlers. Startup, shutdown, IPC sweep have no ctx.
**Instead:** Keep file logging for infrastructure. Add ctx logging for tool-handler messages.

### Anti-Pattern 4: Pinning to `fastmcp==3.x.x` or `>=3.0.0`
**What:** Exact version pin or floor at 3.0.0.
**Why bad:** Exact pin misses patches. Floor at 3.0.0 includes buggy v3.0.0 release (middleware state bug, decorator type issues).
**Instead:** Use `fastmcp>=3.1,<4`.

### Anti-Pattern 5: Test Refactoring in Migration Scope
**What:** Rewriting `_ClientSessionProxy` to `fastmcp.Client(transport=server)` during this milestone.
**Why bad:** Mixes infrastructure changes with dependency migration. Harder to isolate regressions. `CallToolResult.data` return type differs from `ClientSession.call_tool()`.
**Instead:** Verify existing tests pass. Defer to future milestone.

## Sources

- [FastMCP Official Docs](https://gofastmcp.com) -- server, tools, context, lifespan, logging
- [FastMCP PyPI](https://pypi.org/project/fastmcp/) -- v3.1.1, dependencies, Python version
- [FastMCP GitHub (pyproject.toml)](https://github.com/PrefectHQ/fastmcp) -- mcp>=1.24.0,<2.0 dependency
- [FastMCP Upgrade Guide](https://gofastmcp.com/development/upgrade-guide) -- import changes, breaking changes
- [FastMCP 3.0 GA Announcement](https://www.jlowin.dev/blog/fastmcp-3-launch)
- [FastMCP Context API](https://gofastmcp.com/python-sdk/fastmcp-server-context) -- ctx.lifespan_context, logging methods
- [FastMCP Tools](https://gofastmcp.com/servers/tools) -- @mcp.tool() API, ToolAnnotations
- [FastMCP Testing](https://gofastmcp.com/servers/testing) -- Client in-process testing pattern
- [FastMCP Client](https://gofastmcp.com/clients/client) -- Client class API
