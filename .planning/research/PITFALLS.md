# Domain Pitfalls: FastMCP v3 Migration

**Domain:** MCP server dependency migration (mcp SDK bundled -> standalone fastmcp v3)
**Researched:** 2026-03-24
**Confidence:** HIGH (official docs, source code analysis, GitHub issues, upgrade guides verified)

## Critical Pitfalls

### Pitfall 1: `ctx.request_context.lifespan_context` Accessor Path Changed

**What goes wrong:**
All 6 tool handlers access the service via `ctx.request_context.lifespan_context["service"]`. In FastMCP v3, the canonical accessor is `ctx.lifespan_context` (a direct property on Context). The old path technically still works (the property internally delegates to `request_context.lifespan_context`), but relying on it is fragile -- the `request_context` property returns `None` in some contexts (background tasks), and v3's Context has a fallback to `server._lifespan_result` that only the shortcut property uses.

**Why it happens:**
In the MCP SDK's bundled FastMCP 1.0, `Context` was generic (`Context[ServerDeps, ClientDeps, LifespanContext]`) and exposed lifespan via the nested `request_context.lifespan_context` path. FastMCP v3 replaced this with a non-generic `Context` dataclass providing `lifespan_context` as a first-class property with a two-path implementation: tries `request_context` first, falls back to `server._lifespan_result`.

**Consequences:**
- Old accessor may work in stdio (always has request context) but fail in other transport contexts
- Keeping old path means tests pass but production behavior diverges from documented API
- Future FastMCP updates could change the internal `request_context` shape

**Prevention:**
- Replace all 6 occurrences of `ctx.request_context.lifespan_context["service"]` with `ctx.lifespan_context["service"]`
- Grep for `request_context.lifespan_context` across entire codebase (src + tests + planning docs)
- Mechanical find-replace, must be done atomically (all or nothing)

**Detection:**
- `AttributeError: 'NoneType' object has no attribute 'lifespan_context'` in non-stdio contexts
- Works with stdio transport but breaks if transport changes

**Verified:** [FastMCP v3 Context source code](https://github.com/jlowin/fastmcp/blob/main/src/fastmcp/server/context.py) -- `lifespan_context` property with `request_context` fallback to `server._lifespan_result`

---

### Pitfall 2: `Context` Type Parameters Removed -- Strict Mypy Breaks

**What goes wrong:**
All 6 tool handlers annotate `ctx: Context[Any, Any, Any]`. In FastMCP v3, `Context` is a non-generic `@dataclass` -- subscripting it with type parameters is invalid. With `strict = true` in mypy, this produces errors.

**Why it happens:**
The MCP SDK's bundled Context was `class Context(Generic[ServerDependencies, LifespanContext, RequestContext])`. FastMCP v3 redesigned Context as a simple dataclass with no type parameters. Import path also changes: `from fastmcp import Context`.

**Consequences:**
- `mypy --strict` errors: `error: "Context" is not generic [type-arg]`
- 6 tool handler signatures need updating
- Tests referencing `Context[Any, Any, Any]` also break

**Prevention:**
- Change all `ctx: Context[Any, Any, Any]` to `ctx: Context`
- Remove `Any` imports if only used for Context type params
- Update import: `from fastmcp import Context, FastMCP`
- Run `uv run mypy --strict src/` before committing

**Detection:**
- mypy `[type-arg]` errors on every tool handler
- Python runtime: may or may not error (non-generic class `__class_getitem__` behavior varies)

**Verified:** [FastMCP v3 Context API docs](https://gofastmcp.com/python-sdk/fastmcp-server-context) -- Context is non-generic

---

### Pitfall 3: In-Process Test Pattern Completely Changed

**What goes wrong:**
Tests use the MCP SDK's low-level testing pattern:
```python
server._mcp_server.run(
    read_stream, write_stream,
    server._mcp_server.create_initialization_options(),
)
```
This relies on `_mcp_server` (a private attribute) and `create_initialization_options()` (MCP SDK internal). FastMCP v3 provides `Client(server)` as the canonical testing API, and the internal `_mcp_server` attribute may not exist or may have changed shape.

**Why it happens:**
When this project was built, FastMCP 1.0 (bundled with `mcp`) had no official in-process testing API. The `_mcp_server` pattern was the community workaround. FastMCP v3 introduced `from fastmcp import Client` with `async with Client(server) as client:` as the proper testing interface.

**Consequences:**
- 4 test locations break: `test_server.py`, `test_simulator_bridge.py`, `test_simulator_integration.py`, `conftest.py` (`client_session` fixture)
- The `run_with_client()` helper and `_ClientSessionProxy` class in conftest become obsolete
- Tests using `mcp.client.session.ClientSession` and `mcp.shared.message.SessionMessage` need rethinking

**Prevention:**
- **Phase this separately** from the import swap -- test infrastructure is its own task
- Replace `_ClientSessionProxy` in conftest.py with a new fixture using `from fastmcp import Client`
- New pattern:
  ```python
  async with Client(server) as client:
      result = await client.call_tool("get_all", {})
  ```
- Test the new pattern on ONE test file first before migrating all 4
- Note: `_mcp_server` may still work in v3.1.1 (private attr exists), but relying on it is a time bomb

**Detection:**
- `AttributeError: 'FastMCP' object has no attribute '_mcp_server'`
- `ImportError` if `ClientSession` or `SessionMessage` paths change
- Test timeout (new Client pattern uses different async machinery)

**Verified:** [FastMCP v3 testing docs](https://gofastmcp.com/development/tests) -- `Client(server)` pattern with in-memory transport

---

### Pitfall 4: Dependency Conflict Between `mcp` and `fastmcp`

**What goes wrong:**
FastMCP v3 depends on `mcp>=1.24.0,<2.0`. The project currently depends on `mcp>=1.26.0`. After migration, the dependency should be `fastmcp>=3.x` (which pulls in `mcp` transitively). If both `mcp>=1.26.0` AND `fastmcp>=3.x` are in pyproject.toml, the resolver may install conflicting or redundant versions.

**Why it happens:**
FastMCP v3 wraps the `mcp` package. Having an explicit direct dependency on `mcp` alongside `fastmcp` is redundant and can cause version pinning conflicts.

**Consequences:**
- `uv sync` may fail with conflicting version constraints
- CI environment may differ from local (different resolution strategies)
- Both `from mcp.types import ToolAnnotations` and `from fastmcp import FastMCP` still work (mcp is a transitive dep), but explicit + transitive = confusion

**Prevention:**
- **Replace** `mcp>=1.26.0` with `fastmcp>=3.1,<4` in pyproject.toml -- do NOT keep both
- `from mcp.types import ToolAnnotations` still works (fastmcp depends on mcp)
- Pin floor to 3.1 (avoids known-buggy 3.0.x releases); cap at <4 for safety
- After swap: `uv sync` then `uv pip list | grep -E "mcp|fastmcp"` -- verify both present at compatible versions
- Verify: `python -c "from fastmcp import FastMCP; from mcp.types import ToolAnnotations"` must work

**Detection:**
- `uv sync` version conflict errors
- `ModuleNotFoundError: No module named 'mcp.types'` if mcp not pulled in
- Tests pass locally but CI fails (different resolver cache)

**Verified:** [FastMCP pyproject.toml](https://github.com/jlowin/fastmcp/blob/main/pyproject.toml) -- `mcp>=1.24.0,<2.0`; [FastMCP installation docs](https://gofastmcp.com/getting-started/installation) -- "breaking changes may occur in minor versions"

---

## Moderate Pitfalls

### Pitfall 5: `ctx.info()` / `ctx.warning()` Are Async -- Logging Architecture Rethink

**What goes wrong:**
The migration goal includes replacing file-based logging with protocol-level `ctx.info()` / `ctx.warning()`. These methods:
1. Are **async** (must be awaited)
2. Send messages to the **MCP client**, not to a log file
3. Are only available **inside tool handlers** (not in lifespan, startup, module-level)
4. Silently fail if client doesn't support logging capability

The existing `logging.FileHandler` works everywhere. Replacing it entirely means losing server-side persistence.

**Why it happens:**
MCP protocol logging (`notifications/message`) is client-facing. Fundamentally different from server-side file logging:
- `ctx.info()`: tells the *agent* what happened
- `logger.info()`: records what happened for *debugging*

**Consequences:**
- Removing FileHandler loses all server-side debugging capability
- Lifespan startup/shutdown messages have no `ctx` available
- `log_tool_call()` helper needs async rework if using ctx methods
- Silent message loss if `ctx.info()` called without `await` (coroutine created but never awaited, no error raised)

**Prevention:**
- **Keep file logging** for server-side debugging -- do NOT remove FileHandler
- **Add** `await ctx.info()` / `await ctx.warning()` in tool handlers as agent-facing messages
- Two separate concerns: `logger.info(...)` for debug file + `await ctx.info(...)` for agent visibility
- Messages via ctx are also logged at DEBUG level under `fastmcp.server.context.to_client` -- don't rely on this as primary

**Detection:**
- `RuntimeWarning: coroutine was never awaited` if await missing
- Lifespan log messages disappear (no ctx)
- Agent stops seeing messages (if file logging removed without ctx replacement)

**Verified:** [FastMCP logging docs](https://gofastmcp.com/servers/logging) -- async methods, also logged to `fastmcp.server.context.to_client`

---

### Pitfall 6: Lifespan Signature Convention Change

**What goes wrong:**
Current lifespan uses `app: FastMCP` as the parameter:
```python
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict[str, object]]:
```
FastMCP v3 docs use `server` as convention. The `@asynccontextmanager` pattern still works (FastMCP constructor accepts `LifespanCallable | Lifespan | None`), but mixing conventions creates confusion.

**Why it happens:**
MCP SDK bundled FastMCP used `app` (ASGI/Starlette convention). FastMCP v3 uses `server`. The parameter name doesn't matter to Python, but `@lifespan` decorator from `fastmcp.server.lifespan` is the new canonical approach.

**Prevention:**
- **Keep `@asynccontextmanager`** -- explicitly supported, no need to switch to `@lifespan`
- Rename parameter `app` -> `server` for convention alignment
- Update type annotation to import FastMCP from `fastmcp`
- `@lifespan` decorator only needed for composition (`|` operator) -- unnecessary for this project

**Detection:**
- No runtime error (parameter name doesn't matter)
- Convention confusion in code review

**Verified:** [FastMCP lifespan docs](https://gofastmcp.com/servers/lifespan); [server source](https://github.com/jlowin/fastmcp/blob/main/src/fastmcp/server/server.py) -- `LifespanCallable | Lifespan | None`

---

### Pitfall 7: `_register_tools()` Pattern and Decorator Return Values

**What goes wrong:**
FastMCP v3 decorators return the **original function** unchanged, not a wrapper object. Code accessing `.name` or `.description` on decorated functions gets `AttributeError`. The current codebase doesn't do this, but it's a landmine for future changes.

**Also:** The `annotations` kwarg on `@mcp.tool()` with `ToolAnnotations` objects must still work. `ToolAnnotations` stays at `mcp.types` (not re-exported by fastmcp).

**Prevention:**
- Grep for attribute access on decorated tool functions: `get_all.`, `get_task.`, etc. -- none found in current codebase
- `from mcp.types import ToolAnnotations` still works (transitive dep)
- Test: `await client.list_tools()` and verify annotations appear correctly
- No action needed, but document for awareness

**Detection:**
- `AttributeError` on tool function attributes
- Tool annotations missing in `list_tools()` response

---

### Pitfall 8: Dependency Count Badge in README

**What goes wrong:**
README states "Dependencies 1" badge. After migration, direct dep is still 1 (`fastmcp`), but transitive deps increase from ~12 to ~30+ (fastmcp pulls in cyclopts, diskcache, etc.).

**Prevention:**
- Update badge. Options: "Dependencies 1" (direct only, technically true), or remove badge
- Run `uv tree` after migration to audit full tree
- FastMCP core extras are minimal; heavy deps (anthropic, openai) are optional extras
- Accept the tradeoff: slightly larger dep tree for maintained framework

---

## Minor Pitfalls

### Pitfall 9: Test Imports from `mcp.client` and `mcp.shared`

**What goes wrong:**
Tests import `ClientSession` from `mcp.client.session` and `SessionMessage` from `mcp.shared.message`. These are MCP SDK types. If migrating to `fastmcp.Client`, these imports become unnecessary but still work (fastmcp depends on mcp).

**Prevention:**
- Migrate to `from fastmcp import Client` for testing
- If some tests need raw MCP protocol types (simulator tests), keep `from mcp.client.session import ClientSession`
- Track which tests need low-level access vs. high-level Client

### Pitfall 10: `from __future__ import annotations` and Type Resolution

**What goes wrong:**
`server.py` uses `from __future__ import annotations` (PEP 563). FastMCP resolves tool return types via `get_type_hints()`. If `Context` or return type models are imported under different names or conditionally, resolution fails.

**Prevention:**
- Keep `Context` as a runtime import (not `TYPE_CHECKING`-only) -- current code already does this
- Keep `AllEntities`, `Task`, `Project`, `Tag` as runtime imports (already correct, with the NOTE comment explaining why)
- Verify: `from fastmcp import Context` in server.py must be a runtime import

**Detection:**
- `get_type_hints()` failure crashes at tool registration, caught immediately

### Pitfall 11: Lifespan Scope (Per-Server vs Per-Session)

**What goes wrong:**
In the MCP SDK, lifespan ran per-session (documented in issues [#166](https://github.com/jlowin/fastmcp/issues/166), [#1115](https://github.com/jlowin/fastmcp/issues/1115)). FastMCP v3 docs say lifespan runs "exactly once regardless of how many clients connect." For stdio (one process = one session), this doesn't matter. But it's a conceptual change.

**Prevention:**
- No action for stdio transport
- If SSE/HTTP transport added later (v1.6), re-evaluate lifespan assumptions
- The current IPC sweep + repo creation in lifespan is fine either way (idempotent initialization)

### Pitfall 12: `fastmcp` Pulls in Additional Transitive Dependencies

**What goes wrong:**
The project has a "single runtime dependency" claim. Switching to `fastmcp>=3.x` introduces: `cyclopts` (CLI), potentially `diskcache`, and other transitive deps.

**Prevention:**
- Run `uv tree` after migration to audit
- Core fastmcp extras are minimal; heavy deps are optional
- Accept tradeoff: bigger tree for maintained framework + proper logging + testing API

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Dependency swap | Conflict (#4), buggy 3.0.x | Replace `mcp` with `fastmcp>=3.1,<4`; do NOT keep both |
| Import migration | Context generics (#2), accessor (#1) | Remove `[Any, Any, Any]`; use `ctx.lifespan_context` directly |
| Test infrastructure | _mcp_server pattern (#3), client imports (#9) | Migrate conftest fixture to `Client(server)`; one file at a time |
| Logging migration | Async ctx methods (#5), FileHandler removal | Keep FileHandler; ADD ctx.info/warning alongside; always await |
| Tool registration | Decorator return value (#7), ToolAnnotations | Verify annotations work; no code accesses decorator returns |
| Entry point | `server.run(transport="stdio")` | Works in v3; manual UAT with Claude Desktop |
| Documentation | Dep count badge (#8) | Update badge honestly |

## Recommended Migration Order

Based on pitfall dependencies and blast radius:

1. **Dependency swap** -- `mcp>=1.26.0` -> `fastmcp>=3.1,<4` in pyproject.toml. `uv sync`. *(Pitfall #4)*
2. **Import swap** -- `from mcp.server.fastmcp import Context, FastMCP` -> `from fastmcp import Context, FastMCP`. Remove `Context[Any, Any, Any]` -> `Context`. *(Pitfalls #1, #2)*
3. **Lifespan context accessor** -- `ctx.request_context.lifespan_context` -> `ctx.lifespan_context` in all 6 handlers. *(Pitfall #1)*
4. **Run full test suite** -- Catch immediate breaks before touching test infrastructure
5. **Test infrastructure** -- Migrate conftest fixture from `_mcp_server` to `Client(server)`. Then test files one at a time. *(Pitfall #3)*
6. **Logging enhancement** -- Add `await ctx.info()` / `await ctx.warning()` alongside file logging. *(Pitfall #5)*
7. **Manual UAT** -- Start server, connect via Claude Desktop, exercise all 6 tools. *(Pitfall #6, #7)*

Steps 1-4 can be one commit. Step 5 is separate. Step 6 is separate. Step 7 is validation.

## Sources

- [FastMCP upgrade guide (from MCP SDK)](https://gofastmcp.com/getting-started/upgrading/from-mcp-sdk) -- official import migration
- [FastMCP upgrade guide (from FastMCP 2)](https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2) -- breaking changes
- [FastMCP Context API docs](https://gofastmcp.com/python-sdk/fastmcp-server-context) -- non-generic Context, lifespan_context property
- [FastMCP Context source code](https://github.com/jlowin/fastmcp/blob/main/src/fastmcp/server/context.py) -- lifespan_context with request_context fallback
- [FastMCP lifespan docs](https://gofastmcp.com/servers/lifespan) -- @asynccontextmanager supported, @lifespan optional
- [FastMCP logging docs](https://gofastmcp.com/servers/logging) -- async methods, logged to fastmcp.server.context.to_client
- [FastMCP testing docs](https://gofastmcp.com/development/tests) -- Client(server) in-memory pattern
- [FastMCP server source](https://github.com/jlowin/fastmcp/blob/main/src/fastmcp/server/server.py) -- lifespan accepts LifespanCallable | Lifespan | None
- [FastMCP installation guide](https://gofastmcp.com/getting-started/installation) -- version pinning, breaking changes in minors
- [FastMCP PyPI](https://pypi.org/project/fastmcp/) -- latest 3.1.1 (2026-03-14)
- [FastMCP GitHub](https://github.com/PrefectHQ/fastmcp) -- mcp>=1.24.0,<2.0 dependency
- [Context.set_state serialization issue #3156](https://github.com/PrefectHQ/fastmcp/issues/3156) -- undocumented v3 breaking change
- [Lifespan per-session issue #166](https://github.com/jlowin/fastmcp/issues/166) -- lifespan scope
- [Lifespan per-tool-call issue #1115](https://github.com/jlowin/fastmcp/issues/1115) -- lifespan scope as session-scoped
- [mcp.types import issue #2166](https://github.com/PrefectHQ/fastmcp/issues/2166) -- namespace shadowing
- Codebase analysis: `server.py` (317 lines, 6 tool handlers, 6 `ctx.request_context.lifespan_context` accesses), `__main__.py` (31 lines, FileHandler), `conftest.py` (4 `_mcp_server` usages), `test_server.py` / `test_simulator_*.py` (3 more `_mcp_server` usages), `pyproject.toml` (single `mcp>=1.26.0` dep)

---
*Pitfalls research for: v1.2.2 FastMCP v3 Migration*
*Researched: 2026-03-24*
