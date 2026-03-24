# Technology Stack: FastMCP v3 Migration

**Project:** OmniFocus Operator v1.2.2 -- FastMCP v3 Migration
**Researched:** 2026-03-24

## Recommended Stack Change

### Dependency Swap

| Current | New | Purpose | Why |
|---------|-----|---------|-----|
| `mcp>=1.26.0` | `fastmcp>=3.1,<4` | MCP server framework | Standalone FastMCP v3 is the actively maintained project (1M+ downloads/day). Fixes broken logging (protocol-level `ctx.info()`/`ctx.warning()` replaces file-based `FileHandler` workaround). `mcp` becomes a transitive dependency (fastmcp requires `mcp>=1.24.0,<2.0`), so `mcp.types.ToolAnnotations` and test imports still work |

### Version Pinning

```toml
# pyproject.toml
dependencies = [
    "fastmcp>=3.1,<4",
]
```

**Why `>=3.1` not `>=3.0`:** v3.0.1 (2026-02-20) fixed critical bugs -- middleware state surviving to tool handlers, decorator overload types. v3.1.1 (2026-03-14) is current. Floor at 3.1 avoids known-buggy releases.

**Why `<4` not `<3.2`:** FastMCP follows semver. Major version = breaking changes. Upper-bound at `<4` gives us all 3.x improvements while protecting against breaks.

**Why not keep `mcp>=1.26.0`:** The `mcp` package bundles FastMCP v1 (frozen). Standalone FastMCP v3 has protocol-level logging, better lifespan management, structured output, and active development. The `mcp` package remains as a transitive dependency via fastmcp.

## Import Migration Map

### Production Code (server.py)

| Current Import | New Import | Notes |
|---------------|------------|-------|
| `from mcp.server.fastmcp import Context, FastMCP` | `from fastmcp import FastMCP, Context` | Core change. Both exported from top-level `fastmcp` |
| `from mcp.types import ToolAnnotations` | `from mcp.types import ToolAnnotations` | **No change needed.** `mcp` is a transitive dep of fastmcp. Can also use dict format: `annotations={"readOnlyHint": True}` |

### Test Code

| Current Import | New Import | Notes |
|---------------|------------|-------|
| `from mcp.server.fastmcp import FastMCP` | `from fastmcp import FastMCP` | conftest.py, test files |
| `from mcp.client.session import ClientSession` | `from mcp.client.session import ClientSession` | **No change needed.** Still available via transitive `mcp` dep |
| `from mcp.shared.message import SessionMessage` | `from mcp.shared.message import SessionMessage` | **No change needed.** Still available via transitive `mcp` dep |

### Summary: Only 2 files need import changes in src/, 4 in tests/

**src changes:**
- `server.py`: `from mcp.server.fastmcp import Context, FastMCP` -> `from fastmcp import FastMCP, Context`

**test changes:**
- `tests/conftest.py`: `from mcp.server.fastmcp import FastMCP` -> `from fastmcp import FastMCP`
- `tests/test_server.py`: same
- `tests/test_simulator_bridge.py`: same
- `tests/test_simulator_integration.py`: same

## API Migration Map

### Context Access in Tools

**Current pattern** (works in both, but verbose):
```python
async def get_all(ctx: Context[Any, Any, Any]) -> AllEntities:
    service = ctx.request_context.lifespan_context["service"]
```

**New pattern** (FastMCP v3 simplification):
```python
async def get_all(ctx: Context) -> AllEntities:
    service = ctx.lifespan_context["service"]
```

Key changes:
- `Context` no longer needs generic params `[Any, Any, Any]` -- just `Context`
- `ctx.lifespan_context` directly accesses the lifespan dict (no `.request_context.` chain)
- Both are functionally equivalent; the v3 form is cleaner

**Alternative v3 pattern** (dependency injection, not recommended for this migration):
```python
from fastmcp.dependencies import CurrentContext

async def get_all(ctx: Context = CurrentContext()) -> AllEntities:
    ...
```

Not recommended because: current `ctx: Context` type-hint injection still works fine in v3. `CurrentContext()` is for advanced DI scenarios. Stick with the simpler form.

### Lifespan

**Current pattern** (still works in v3):
```python
@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict[str, object]]:
    # ... setup ...
    yield {"service": service}
```

**No change required.** FastMCP v3 accepts the same lifespan signature. The `lifespan=` constructor kwarg is preserved.

### Server Creation

**Current pattern** (still works in v3):
```python
mcp = FastMCP("omnifocus-operator", lifespan=app_lifespan)
```

**No change required.** `name` and `lifespan` constructor params preserved.

### Server Run

**Current pattern** (still works in v3):
```python
server.run(transport="stdio")
```

**No change required.** `run(transport="stdio")` is the v3 default pattern.

### Tool Registration

**Current pattern** (still works in v3):
```python
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def get_all(ctx: Context[Any, Any, Any]) -> AllEntities:
    ...
```

**Minimal change** -- only Context type simplification:
```python
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def get_all(ctx: Context) -> AllEntities:
    ...
```

`@mcp.tool()` decorator API is unchanged. `annotations=` param still accepts `ToolAnnotations` objects.

### Tool Annotations (two options, both valid)

```python
# Option A: Keep using mcp.types.ToolAnnotations (no change)
from mcp.types import ToolAnnotations
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))

# Option B: Use dict format (simpler, no mcp.types import)
@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
```

Recommendation: **Option B** (dict format) to reduce coupling to `mcp.types`. Cleaner, fewer imports, FastMCP v3 docs show this as idiomatic.

## Protocol-Level Logging (the key win)

### Current (file-based workaround)

```python
# __main__.py -- elaborate FileHandler setup
log_path = os.path.expanduser("~/Library/Logs/omnifocus-operator.log")
handler = logging.FileHandler(log_path)
log.addHandler(handler)

# server.py -- python logging, invisible to MCP client
logger.debug("server.get_all: returning tasks=%d, ...", ...)
```

### New (protocol-level notifications via Context)

```python
# In tool handlers:
await ctx.info(f"Returning {len(result.tasks)} tasks, {len(result.projects)} projects")
await ctx.warning("Some warning visible to the agent")
```

Key properties:
- `await ctx.debug(msg)` -- detailed execution info
- `await ctx.info(msg)` -- normal milestones
- `await ctx.warning(msg)` -- non-critical issues
- `await ctx.error(msg)` -- recoverable errors
- All are `async` -- require `await`
- Messages go to the **MCP client** (agent sees them), not just a log file
- File-based logging can be **removed or demoted** to dev-only debugging

### Migration strategy for logging

Phase the logging migration:
1. Keep `logging.FileHandler` for development debugging
2. Add `ctx.info()`/`ctx.warning()` for agent-visible messages
3. Remove `logging.FileHandler` workaround from `__main__.py` once validated
4. Keep `logger.debug()` calls as internal dev logging (optional, doesn't hurt)

## Testing Pattern Migration

### Current pattern (low-level anyio streams)

```python
# conftest.py -- manual stream wiring
s2c_send, s2c_recv = anyio.create_memory_object_stream[SessionMessage](0)
c2s_send, c2s_recv = anyio.create_memory_object_stream[SessionMessage](0)
await self._server._mcp_server.run(c2s_recv, s2c_send, ...)
async with ClientSession(s2c_recv, c2s_send) as session:
    await session.initialize()
    result = await session.call_tool(...)
```

### New pattern (FastMCP Client)

```python
from fastmcp.client import Client

@pytest.fixture
async def client():
    async with Client(transport=server) as c:
        yield c

# In tests:
result = await client.call_tool("get_all", {})
```

**Decision: Defer test refactoring.** The current low-level pattern uses `server._mcp_server` (private attr) and raw anyio streams. This still works in v3 because:
- `_mcp_server` is still present (FastMCP wraps the low-level `Server`)
- `ClientSession` and `SessionMessage` come from `mcp` (transitive dep)
- Refactoring to `Client(transport=server)` is a quality-of-life improvement, not a necessity

Recommendation: **Keep existing test pattern for v1.2.2 scope.** Refactor to `fastmcp.Client` in a future milestone as a DX improvement.

## Dependency Weight Assessment

### Current state
- Runtime deps: 1 (`mcp>=1.26.0`)
- Installed packages (including dev): ~56

### After migration
- Runtime deps: 1 (`fastmcp>=3.1,<4`)
- Transitive deps of fastmcp: ~19 direct (including `mcp`, `httpx`, `uvicorn`, `rich`, `authlib`, `pydantic[email]`, `opentelemetry-api`, `watchfiles`, etc.)
- **Significant increase in transitive dependency tree**

### Risk assessment

| Concern | Impact | Mitigation |
|---------|--------|------------|
| Dependency bloat | MEDIUM -- from 1 declared dep to 1 declared dep, but transitive tree grows significantly | This is the tradeoff for protocol-level logging + active maintenance. `mcp` itself already pulls in httpx, anyio, pydantic, etc. Many deps overlap |
| Supply chain surface | LOW -- FastMCP is maintained by Prefect (well-funded, established company) | Pinned to `<4` for safety |
| Install size | LOW -- most deps are already pulled by `mcp` transitively | Verify with `uv pip list` after migration |

**Honest assessment:** The project goes from "single runtime dep" (a marketing point in README) to "single declared dep with heavier transitive tree." This is a real tradeoff. The gains (fixed logging, active maintenance, better APIs) justify it, but the README badge should be updated.

## What NOT to Add

| Technology | Why Not |
|------------|---------|
| `fastmcp[tasks]` extra | Background tasks not needed -- OmniFocus Operator is request/response only |
| `fastmcp[anthropic/openai/gemini]` extras | LLM provider integration not needed -- server doesn't call LLMs |
| `fastmcp[apps]` extra | UI/app features not needed -- stdio-only server |
| `fastmcp.server.providers.*` | OpenAPI, Proxy, FileSystem providers not needed -- static tool registration suffices |
| `fastmcp.server.transforms.*` | Transforms not needed -- no component manipulation required |
| `fastmcp.dependencies.Depends` | Over-engineered for this use case -- type-hint injection is sufficient |
| `fastmcp.prompts.Message` | No prompts in OmniFocus Operator (out of scope per PROJECT.md) |
| Auth providers | No auth needed -- stdio transport, local server |

## Installation

```bash
# In pyproject.toml, replace:
#   "mcp>=1.26.0"
# with:
#   "fastmcp>=3.1,<4"

# Then:
uv sync
```

## Sources

- [FastMCP Upgrade Guide](https://gofastmcp.com/development/upgrade-guide) -- MEDIUM confidence (official docs, verified)
- [FastMCP v3 Context API](https://gofastmcp.com/python-sdk/fastmcp-server-context) -- HIGH confidence (official docs, detailed)
- [FastMCP v3 Tools Documentation](https://gofastmcp.com/servers/tools) -- HIGH confidence (official docs)
- [FastMCP v3 Testing Documentation](https://gofastmcp.com/servers/testing) -- MEDIUM confidence (official docs, pattern verified)
- [FastMCP v3 GA Announcement](https://www.jlowin.dev/blog/fastmcp-3-launch) -- MEDIUM confidence (author blog)
- [FastMCP Changelog](https://gofastmcp.com/changelog) -- HIGH confidence (official changelog)
- [FastMCP PyPI](https://pypi.org/project/fastmcp/) -- HIGH confidence (package registry)
- [FastMCP GitHub pyproject.toml](https://github.com/PrefectHQ/fastmcp) -- HIGH confidence (source of truth for deps)
- [FastMCP Running Server docs](https://gofastmcp.com/deployment/running-server) -- HIGH confidence (official docs)
