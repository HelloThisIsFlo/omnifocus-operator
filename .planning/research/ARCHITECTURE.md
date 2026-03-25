# Architecture: FastMCP v3 Migration Integration Map

**Domain:** Infrastructure migration -- mcp.server.fastmcp to standalone fastmcp>=3
**Researched:** 2026-03-25
**Confidence:** HIGH -- spike experiments verified, import paths confirmed against fastmcp 3.1.1

## Current Architecture (Pre-Migration)

```
__main__.py          -- Entrypoint: logging setup + server.run()
server.py            -- FastMCP instance, lifespan, tool registration, log_tool_call()
service/             -- Resolver, DomainLogic, PayloadBuilder, orchestrator
contracts/           -- Command, RepoPayload, RepoResult, Result models
repository/          -- HybridRepository, BridgeRepository
tests/conftest.py    -- _ClientSessionProxy (40 lines), server fixture
tests/test_server.py -- run_with_client (30 lines), integration tests
tests/test_simulator_bridge.py    -- _run_with_client (local copy)
tests/test_simulator_integration.py -- _run_with_client (local copy)
```

## Migration Impact Map

### Files DELETED (components removed entirely)

None. No files are deleted. Code is deleted from within existing files.

### Code DELETED (within existing files)

| Location | What | Lines | Replaced By |
|----------|------|-------|-------------|
| `server.py:53-63` | `log_tool_call()` function | ~11 | `ToolLoggingMiddleware` |
| `server.py` (6 sites) | `log_tool_call("tool_name", ...)` calls | 6 | Middleware fires automatically |
| `conftest.py:435-481` | `_ClientSessionProxy` class | ~47 | `Client(server)` pattern |
| `conftest.py:420-481` | `client_session` fixture body | ~62 | 3-line Client fixture |
| `test_server.py:51-82` | `run_with_client()` helper | ~32 | `Client(server)` pattern |
| `test_server.py:38-48` | `_build_patched_server()` helper | ~11 | Keep or adapt (still needed for tests with custom lifespan) |
| `test_simulator_bridge.py:77-102` | `_run_with_client()` (local copy) | ~26 | `Client(server)` |
| `test_simulator_integration.py:117-142` | `_run_with_client()` (local copy) | ~26 | `Client(server)` |
| `__main__.py:15` | Stderr hijacking misdiagnosis comment | 1 | Removed (was wrong) |
| `__main__.py:20` | `log.propagate = False` | 1 | Removed (need propagation for dual handler) |

### Files MODIFIED

| File | What Changes | Scope |
|------|-------------|-------|
| **`server.py`** | Import swap, lifespan_context shortcut, remove log_tool_call, add middleware wiring, add progress reporting | Heavy -- most changes in codebase |
| **`__main__.py`** | Dual-handler logging (stderr + file), remove misdiagnosis comment | Medium |
| **`conftest.py`** | Replace `_ClientSessionProxy` with `Client(server)` fixture, update imports | Medium |
| **`test_server.py`** | Replace `run_with_client` with `Client(server)`, update all assertions | Heavy -- 1164 lines, most test file |
| **`test_simulator_bridge.py`** | Replace `_run_with_client` with `Client(server)`, update imports | Light |
| **`test_simulator_integration.py`** | Replace `_run_with_client` with `Client(server)`, update imports | Light |
| **`pyproject.toml`** | Swap dependency `mcp>=1.26.0` to `fastmcp>=3`, move from spike group to main | Light |

### Files CREATED (new components)

| File | Purpose | Location Decision |
|------|---------|-------------------|
| **`middleware.py`** | `ToolLoggingMiddleware` class | `src/omnifocus_operator/middleware.py` -- same level as `server.py`, cross-cutting concern |

**Why a new file:** Middleware is a cross-cutting concern separate from tool business logic. It should not live in `server.py` (which owns tool registration and lifespan) or `__main__.py` (which owns entrypoint). A dedicated module keeps it independently testable and composable.

### Files UNCHANGED

- `service/` package -- no changes (service layer is below the MCP boundary)
- `contracts/` package -- no changes (model layer)
- `repository/` package -- no changes (data layer)
- `models/` package -- no changes
- `agent_messages/` package -- no changes
- `bridge/` package -- no changes
- `tests/doubles/` -- no changes (InMemoryBridge, StubBridge, SimulatorBridge unaffected)
- All other test files not listed above -- no changes

## Integration Points Per Feature

### 1. Dependency Swap

**What:** `mcp.server.fastmcp` imports become `fastmcp` imports.

**Import changes:**
```python
# server.py
- from mcp.server.fastmcp import Context, FastMCP
+ from fastmcp import FastMCP, Context

# mcp.types stays -- fastmcp does NOT re-export ToolAnnotations
  from mcp.types import ToolAnnotations  # unchanged
```

**Test imports:**
```python
# conftest.py, test_server.py, test_simulator_*.py
- from mcp.server.fastmcp import FastMCP
+ from fastmcp import FastMCP

# These are REMOVED entirely (replaced by Client pattern):
- from mcp.client.session import ClientSession
- from mcp.shared.message import SessionMessage
- import anyio
```

**pyproject.toml:**
```toml
dependencies = [
-   "mcp>=1.26.0",
+   "fastmcp>=3",
]
# Remove spike dependency group (merged into main)
```

**Verified:** `ToolAnnotations` is NOT re-exported by fastmcp -- `from mcp.types import ToolAnnotations` must remain. This works because fastmcp depends on mcp transitively.

**Architecture impact:** None. Import-only change. No structural changes.

### 2. Lifespan Context Shortcut

**What:** `ctx.request_context.lifespan_context["service"]` becomes `ctx.lifespan_context["service"]`.

**Affected:** 6 tool handlers in `server.py` (one per tool).

```python
# All 6 tool handlers
- service: OperatorService = ctx.request_context.lifespan_context["service"]
+ service: OperatorService = ctx.lifespan_context["service"]
```

**Architecture impact:** None. Syntactic shortcut. Both work in v3 (backward compatible). The lifespan pattern itself is unchanged -- `app_lifespan` still yields `{"service": service}`.

### 3. Test Client Migration

**What:** Replace manual memory-stream plumbing with `Client(server)`.

**Before (current):**
```python
# conftest.py -- 47-line _ClientSessionProxy class
# test_server.py -- 32-line run_with_client helper
# test_simulator_*.py -- 26-line _run_with_client copies
```

**After:**
```python
from fastmcp import Client

# conftest.py fixture
@pytest.fixture
def client(server: Any) -> Any:
    return Client(server)
```

**Test pattern change:**

```python
# Before:
async def test_something(self, client_session):
    result = await client_session.call_tool("tool", {"arg": "val"})
    assert result.isError is not True
    assert result.structuredContent["key"] == "value"

# After (two options):

# Option A: call_tool_mcp (minimal diff -- returns raw CallToolResult)
async def test_something(self, client):
    async with client:
        result = await client.call_tool_mcp("tool", {"arg": "val"})
        assert result.isError is not True
        assert result.structuredContent["key"] == "value"

# Option B: call_tool (idiomatic v3 -- raises ToolError on error)
async def test_something(self, client):
    async with client:
        result = await client.call_tool("tool", {"arg": "val"})
        # result is CallToolResult, but errors raise ToolError
```

**Critical adaptation points:**

1. **Error assertions** -- Current tests check `result.isError is True` and inspect `result.content[0].text`. With v3 Client:
   - `client.call_tool()` raises `ToolError` on error (default `raise_on_error=True`)
   - `client.call_tool(raise_on_error=False)` returns `CallToolResult` with `isError=True` (same as current)
   - `client.call_tool_mcp()` always returns raw `CallToolResult` (never raises)
   - **Recommendation:** Use `call_tool_mcp()` for tests that assert on error responses. Minimal assertion changes.

2. **Structured content** -- Tests access `result.structuredContent["key"]`. `call_tool_mcp()` returns `CallToolResult` which has the same `.structuredContent` attribute. No change needed if using `call_tool_mcp()`.

3. **Session lifecycle** -- `Client(server)` must be used as async context manager (`async with client:`). Current `client_session` fixture returns a proxy that works without `async with`. Two approaches:
   - Fixture returns `Client(server)` object, tests use `async with client:` explicitly
   - Fixture uses `@pytest.fixture` with `yield` inside `async with Client(server) as c:` (automates lifecycle)

**Fixture architecture decision:**

```python
# Option A: tests manage lifecycle (explicit)
@pytest.fixture
def client(server):
    return Client(server)

# Tests:
async def test_foo(self, client):
    async with client:
        result = await client.call_tool_mcp(...)

# Option B: fixture manages lifecycle (implicit, cleaner tests)
@pytest.fixture
async def client(server):
    async with Client(server) as c:
        yield c

# Tests:
async def test_foo(self, client):
    result = await client.call_tool_mcp(...)
```

**Recommendation:** Option B. Tests stay cleaner (no `async with` boilerplate in every test). The fixture handles connect/disconnect. Matches the existing `client_session` fixture pattern where the proxy handled lifecycle.

**Scope of test assertion changes:**
- `test_server.py`: ~112 uses of `run_with_client` or `client_session` across 1164 lines
- `test_simulator_bridge.py`: ~4 uses
- `test_simulator_integration.py`: ~2 uses

**Tests using `run_with_client` (callback pattern):**
```python
# Before:
async def _check(session: ClientSession) -> None:
    result = await session.call_tool("get_all")
    assert result.structuredContent is not None
await run_with_client(server, _check)

# After (with fixture):
async with Client(server) as client:
    result = await client.call_tool_mcp("get_all", {})
    assert result.structuredContent is not None
```

**Tests using `client_session` fixture:**
```python
# Before:
async def test_get_task(self, client_session):
    result = await client_session.call_tool("get_task", {"id": "task-001"})

# After:
async def test_get_task(self, client):
    result = await client.call_tool_mcp("get_task", {"id": "task-001"})
```

### 4. Middleware (ToolLoggingMiddleware)

**What:** Replace manual `log_tool_call()` with automatic middleware.

**New file:** `src/omnifocus_operator/middleware.py`

```python
# middleware.py
import logging
import time
from typing import Any
from fastmcp.server.middleware import Middleware, MiddlewareContext

class ToolLoggingMiddleware(Middleware):
    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        tool_name = context.message.name
        args = context.message.arguments
        self._log.info(...)
        start = time.monotonic()
        try:
            result = await call_next(context)
            elapsed_ms = (time.monotonic() - start) * 1000
            self._log.info(...)
            return result
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            self._log.error(...)
            raise
```

**Wiring point -- `server.py:create_server()`:**
```python
def create_server() -> FastMCP:
    mcp = FastMCP("omnifocus-operator", lifespan=app_lifespan)
    _register_tools(mcp)
+   # Middleware wired here, not in __main__, because middleware
+   # is part of the server configuration (same as lifespan and tools)
+   mcp.add_middleware(ToolLoggingMiddleware(stderr_logger))
+   mcp.add_middleware(ToolLoggingMiddleware(file_logger))
    return mcp
```

**Where do loggers come from?** Two options:

- **Option A:** `create_server()` accepts logger params. `__main__.py` creates and passes them.
- **Option B:** Logger factory in `middleware.py`, called from `create_server()`.
- **Option C:** Loggers created in `__main__.py` before `create_server()`, middleware attached after.

**Recommendation:** Option C. Logger setup belongs in `__main__.py` (entrypoint concern). Middleware class lives in `middleware.py`. Wiring happens in `__main__.py`:

```python
# __main__.py
server = create_server()
# ... set up loggers ...
server.add_middleware(ToolLoggingMiddleware(stderr_logger))
server.add_middleware(ToolLoggingMiddleware(file_logger))
server.run(transport="stdio")
```

This keeps `create_server()` pure (no logging side effects) and lets tests skip middleware entirely. Tests that want to verify middleware can add it explicitly.

**Architecture impact:** Removes cross-cutting concern from tool handlers. Tools become pure business logic -- no logging boilerplate. Middleware handles entry/exit/timing/errors automatically.

### 5. Logging Rework

**What:** Dual-handler logging replacing file-only setup.

**Modified file:** `__main__.py`

```python
# Before:
log.propagate = False  # REMOVED
handler = logging.FileHandler(log_path)  # single handler

# After:
# Handler 1: stderr (visible in Claude Desktop log page)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
))

# Handler 2: file (persistent, for Claude Code debugging)
file_handler = logging.FileHandler(log_path)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
))

log.addHandler(stderr_handler)
log.addHandler(file_handler)
```

**Architecture impact:** None on server/service/repository. Only affects `__main__.py` entrypoint. Independent of FastMCP migration (works on both SDKs). Bundled for convenience.

### 6. Progress Reporting

**What:** `ctx.report_progress()` in batch operations.

**Modified:** `server.py` tool handlers for `add_tasks` and `edit_tasks`.

```python
# add_tasks handler (currently single-item, but future-proofed)
async def add_tasks(items: list[dict[str, Any]], ctx: Context[Any, Any, Any]):
    ...
    for i, item in enumerate(validated_items):
        await ctx.report_progress(progress=i, total=len(validated_items))
        result = await service.add_task(item)
        results.append(result)
    await ctx.report_progress(progress=len(validated_items), total=len(validated_items))
```

**Current limitation:** Both `add_tasks` and `edit_tasks` are limited to 1 item per call (`len(items) != 1` raises). Progress reporting is trivially useful now but becomes meaningful when the batch limit is raised. Adding the pattern now means no code changes when limits are relaxed.

**Architecture impact:** None. Progress reporting is a presentation concern at the MCP layer. Service layer is unaware of it. Graceful no-op when client doesn't send `progressToken`.

## Component Boundary Analysis

```
                    CHANGES                         UNCHANGED
                    -------                         ---------

 __main__.py -----> Logging rework                  service/
                    Middleware wiring                contracts/
                                                    repository/
 server.py -------> Import swap                     models/
                    lifespan_context shortcut        agent_messages/
                    Remove log_tool_call()           bridge/
                    Progress reporting

 middleware.py ---> NEW: ToolLoggingMiddleware

 conftest.py -----> Replace _ClientSessionProxy     tests/doubles/
                    with Client fixture              tests/test_*.py (non-server)

 test_server.py --> Replace run_with_client
                    Update all assertions

 test_simulator_*.py -> Replace _run_with_client
```

**Key insight:** Changes are confined to the MCP layer (server, entrypoint, tests) and do not penetrate into service, repository, contracts, or models. The three-layer architecture boundary holds perfectly. This is the migration's biggest architectural virtue -- it validates the clean separation.

## Build Order (Dependency Chain)

Phases ordered by dependency: each phase can only start after its dependencies land.

### Phase 1: Dependency Swap + Import Migration
- Swap `mcp>=1.26.0` to `fastmcp>=3` in pyproject.toml
- Update all imports (server.py, conftest.py, test_server.py, test_simulator_*.py)
- Replace `ctx.request_context.lifespan_context` with `ctx.lifespan_context` (6 sites)
- **Dependency:** None. Foundation for everything else.
- **Verification:** All existing tests pass with new imports (before any behavior change)

### Phase 2: Test Client Migration
- Create new `client` fixture using `Client(server)` in conftest.py
- Migrate test_server.py from `run_with_client` + `client_session` to `Client`
- Migrate test_simulator_bridge.py and test_simulator_integration.py
- Delete `_ClientSessionProxy`, `run_with_client`, `_run_with_client` copies
- Remove `anyio`, `ClientSession`, `SessionMessage` imports from test files
- **Dependency:** Phase 1 (needs fastmcp installed for `from fastmcp import Client`)
- **Why before middleware:** Tests need to work before we change server behavior. Middleware changes what gets logged, which could confuse debugging if tests are broken.
- **Verification:** All tests pass with new client pattern. Exact same assertions (using `call_tool_mcp` for minimal diff).

### Phase 3: Middleware
- Create `src/omnifocus_operator/middleware.py` with `ToolLoggingMiddleware`
- Remove `log_tool_call()` function and 6 call sites from `server.py`
- Wire middleware in `__main__.py` (or `create_server()`)
- **Dependency:** Phase 1 (needs fastmcp for Middleware base class)
- **Independent of Phase 2** -- could run in parallel, but sequential is safer
- **Verification:** Middleware fires on tool calls (visible in logs). All tests pass.

### Phase 4: Logging Rework
- Replace single FileHandler with dual stderr + file handlers in `__main__.py`
- Remove misdiagnosis comment
- Remove `propagate = False`
- **Dependency:** Phase 3 (middleware loggers need to exist before wiring)
- **Note:** Technically SDK-independent, but logically after middleware since middleware creates the loggers that get dual destinations
- **Verification:** Server logs appear on both stderr and file.

### Phase 5: Progress Reporting
- Add `ctx.report_progress()` to `add_tasks` and `edit_tasks` batch loops
- **Dependency:** Phase 1 (needs fastmcp Context with report_progress)
- **Independent of Phases 2-4** -- can land anytime after Phase 1
- **Verification:** Progress bar visible in Claude Code CLI.

### Phase 6: Documentation
- Update README.md dependency section
- Update landing page if needed
- **Dependency:** All phases complete
- **Verification:** README matches actual dependencies.

```
Phase 1: Dep Swap ──┬──> Phase 2: Test Client ──> Phase 3: Middleware ──> Phase 4: Logging
                    │
                    └──> Phase 5: Progress (independent)
                                                                          Phase 6: Docs (last)
```

## Test Assertion Migration Strategy

**Two categories of test assertions:**

### Category A: Success assertions (majority)
```python
# Current:
result = await client_session.call_tool("tool", {"arg": "val"})
assert result.isError is not True
assert result.structuredContent["key"] == "value"

# Migrated (using call_tool_mcp -- minimal diff):
result = await client.call_tool_mcp("tool", {"arg": "val"})
assert result.isError is not True
assert result.structuredContent["key"] == "value"
```
Change: method name only (`call_tool` -> `call_tool_mcp`).

### Category B: Error assertions (~10 tests)
```python
# Current:
result = await client_session.call_tool("tool", {"arg": "bad"})
assert result.isError is True
text = result.content[0].text
assert "expected error" in text

# Migrated (using call_tool_mcp -- same shape):
result = await client.call_tool_mcp("tool", {"arg": "bad"})
assert result.isError is True
text = result.content[0].text
assert "expected error" in text
```
Change: method name only. `call_tool_mcp` never raises, always returns `CallToolResult`.

**Recommendation:** Use `call_tool_mcp()` uniformly across all test assertions. This preserves the existing assertion shapes and minimizes migration risk. `call_tool()` (the raising variant) can be adopted later if desired, but adds no value for tests.

## Anti-Patterns to Avoid

### Do NOT put middleware in server.py
`server.py` owns tool registration and lifespan. Middleware is a cross-cutting concern. Mixing them creates a module that's responsible for too many things.

### Do NOT create per-test Client instances
The fixture should manage the Client lifecycle. Tests that create their own Clients (e.g., for custom lifespan) should still use `async with Client(server) as client:` explicitly, not raw construction.

### Do NOT use ctx.info() / ctx.warning()
Spike conclusively proved these are dead ends -- no major MCP client renders them. Stick with response-payload warnings (existing pattern) for agent-facing messages and Python logging for developer diagnostics.

### Do NOT migrate to call_tool() (raising variant) during initial migration
`call_tool_mcp()` preserves existing assertion shapes. Switching to the raising variant simultaneously with infrastructure migration doubles the diff and debugging surface. Adopt it in a follow-up if desired.

## Sources

- Spike experiments: `.research/deep-dives/fastmcp-spike/FINDINGS.md` (8 experiments, 2026-03-24)
- Reference implementation: `.research/deep-dives/fastmcp-spike/experiments/05_middleware.py`
- Import verification: `fastmcp 3.1.1` installed, imports tested live
- `Client.call_tool` signature: `raise_on_error=True` default confirmed via source inspection
- `Client.call_tool_mcp`: returns raw `CallToolResult`, never raises -- confirmed via source
- `ToolAnnotations`: NOT re-exported by fastmcp, must stay at `from mcp.types` -- confirmed live
