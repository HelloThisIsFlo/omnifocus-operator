# Phase 5: Service Layer and MCP Server - Research

**Researched:** 2026-03-02
**Domain:** MCP Server (FastMCP SDK), Service Layer, Dependency Injection
**Confidence:** HIGH

## Summary

Phase 5 wires together the existing repository/bridge/models layers into a running MCP server with a single `list_all` tool. The MCP Python SDK (v1.26.0) already provides everything needed via `mcp.server.fastmcp.FastMCP`: tool registration with annotations, structured output from Pydantic models, lifespan-managed dependency injection, and stdio transport.

The implementation is straightforward because FastMCP auto-detects Pydantic `BaseModel` return types and generates `outputSchema` + structured content automatically. The existing `DatabaseSnapshot` model (with camelCase aliases via `by_alias=True`) produces correct structured output with zero additional schema work. Tool annotations (`readOnlyHint`, `idempotentHint`) are first-class parameters on the `@tool()` decorator.

**Primary recommendation:** Use FastMCP's lifespan async context manager to create the bridge/repository/service dependency chain at startup, pass the service via the lifespan context dict, and access it in tools via `ctx.request_context.lifespan_context`. Stdlib `logging` is sufficient for stderr logging since it defaults to stderr and the SDK's own `configure_logging` uses it.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Service Layer Design
- Thin passthrough -- exists as an architectural seam for future phases (filtering, writes) but delegates directly to Repository in Phase 5
- Typed methods per operation: e.g., `get_all_data() -> DatabaseSnapshot`. Each future tool gets its own service method
- Named `OperatorService` -- the service is the core of the "Operator" product, not just OmniFocus data access. Distinct from `OmniFocusRepository` which is about data access
- Lives in a new `service/` package (`src/omnifocus_operator/service/`) consistent with bridge/, models/, repository/

#### DI and Lifespan Wiring
- Bridge selected via environment variable `OMNIFOCUS_BRIDGE` (values: `inmemory`, `simulator`, `real`)
- Default bridge is `real` -- users should just start the server and have it work; inmemory/simulator are for development only
- Phase 5 shipping behavior: defaults to `real`, but since RealBridge doesn't exist yet, startup fails with a clear error message telling the user to set `OMNIFOCUS_BRIDGE=inmemory`. When RealBridge ships in Phase 8, the default "just works"
- Lifespan pre-warms the repository cache at startup via `repository.initialize()` -- first MCP call hits warm data, fail-fast if bridge is broken
- Server module lives in a new `server/` package (`src/omnifocus_operator/server/`) for FastMCP setup and lifespan wiring

#### list_all Tool Output
- Returns the full `DatabaseSnapshot` Pydantic dump -- no truncation, no summary layer, no information loss
- Uses MCP structured output with `outputSchema` derived from DatabaseSnapshot's JSON Schema (TOOL-03)
- camelCase field names via Pydantic `by_alias=True` serialization -- matches MCP protocol conventions and standard JSON idiom
- Tool includes MCP annotations: `readOnlyHint: true`, `idempotentHint: true` (TOOL-02)

#### Logging and stderr
- Default log level: INFO (startup, bridge selection, cache pre-warm, tool invocations)
- Configurable via `OMNIFOCUS_LOG_LEVEL` environment variable
- Redirect `sys.stdout` to `stderr` at startup as safety net against accidental print() corrupting MCP protocol traffic (TOOL-04)
- Log key events: startup, bridge type selected, cache pre-warm result, tool invocations

### Claude's Discretion
- Logging library choice -- stdlib logging vs structlog vs other. Researcher should evaluate what works best with the MCP SDK and the project's single-dependency philosophy
- Exact lifespan implementation pattern (FastMCP's context manager vs custom)
- Log message format and structure
- Error response format when tool invocation fails

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ARCH-01 | Server uses three-layer architecture (MCP Server -> Service Layer -> Repository) | FastMCP lifespan creates Repository and OperatorService; tool functions call service methods; verified in-process testing pattern |
| ARCH-02 | Bridge implementation is injected at startup -- no code changes to switch | OMNIFOCUS_BRIDGE env var read in lifespan; bridge factory creates the selected implementation; service/MCP layers never reference concrete bridge types |
| TOOL-01 | `list_all` tool returns full structured database as typed Pydantic data | FastMCP auto-detects BaseModel return type -> structured output; verified DatabaseSnapshot produces correct outputSchema and structuredContent |
| TOOL-02 | Tool includes MCP annotations (`readOnlyHint`, `idempotentHint`) | `ToolAnnotations(readOnlyHint=True, idempotentHint=True)` passed to `@tool()` decorator; verified end-to-end |
| TOOL-03 | Tool exposes structured output schema from Pydantic models | `func_metadata` auto-generates `output_schema` from return type annotation; `model_json_schema(by_alias=True)` produces camelCase schema; verified with DatabaseSnapshot |
| TOOL-04 | Server logs to stderr only | stdlib logging StreamHandler defaults to stderr; FastMCP configure_logging uses stderr; stdout redirect to stderr as safety net |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp` (FastMCP) | 1.26.0 | MCP server framework | Already the project's sole runtime dependency; provides FastMCP, tool registration, lifespan, stdio transport |
| stdlib `logging` | 3.12 | Application logging | Zero extra dependencies; SDK's own configure_logging uses it; StreamHandler defaults to stderr |
| stdlib `os` | 3.12 | Environment variable access | `os.environ.get("OMNIFOCUS_BRIDGE", "real")` for bridge selection |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `anyio` | (transitive via mcp) | Async runtime, memory streams | In-process testing with memory object streams; already available |
| `pydantic` | (transitive via mcp) | Model validation, schema generation | Already used for all data models; `model_json_schema()` for output schema |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `logging` | `structlog` | Structured JSON logs, nicer API, but adds a dependency violating single-dep philosophy; stdlib is sufficient and SDK already uses it |
| stdlib `logging` | FastMCP's built-in `configure_logging` | SDK uses it internally; we can leverage it or configure our own -- recommend own configuration for control over format and log-level env var |

**Installation:**
No new dependencies needed. `mcp>=1.26.0` already provides everything.

## Architecture Patterns

### Recommended Project Structure
```
src/omnifocus_operator/
├── bridge/           # Bridge protocol + InMemoryBridge (existing)
├── models/           # Pydantic data models (existing)
├── repository/       # OmniFocusRepository + MtimeSource (existing)
├── service/          # NEW: OperatorService (thin passthrough)
│   ├── __init__.py   # Re-exports OperatorService
│   └── _service.py   # OperatorService implementation
├── server/           # NEW: MCP server wiring
│   ├── __init__.py   # Re-exports create_server or the FastMCP app
│   └── _server.py    # FastMCP setup, lifespan, tool registration
├── __init__.py
├── __main__.py       # Entry point: calls server.run()
└── py.typed
```

### Pattern 1: Lifespan-Based Dependency Injection
**What:** FastMCP's lifespan async context manager creates all dependencies at startup and yields them as a dict accessible from tool functions via `ctx.request_context.lifespan_context`.
**When to use:** Always -- this is the canonical FastMCP DI pattern.
**Example:**
```python
# Source: Verified against mcp 1.26.0 FastMCP server.py + lowlevel/server.py
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from mcp.server.fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations

@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict]:
    # Create bridge based on env var
    bridge = create_bridge_from_env()
    mtime_source = create_mtime_source(bridge_type)
    repository = OmniFocusRepository(bridge=bridge, mtime_source=mtime_source)
    service = OperatorService(repository=repository)

    # Pre-warm cache (SNAP-06)
    await repository.initialize()

    yield {"service": service}

mcp = FastMCP("omnifocus-operator", lifespan=app_lifespan)

@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def list_all(ctx: Context) -> DatabaseSnapshot:
    service = ctx.request_context.lifespan_context["service"]
    return await service.get_all_data()
```

### Pattern 2: Bridge Factory with Environment Variable
**What:** A factory function reads `OMNIFOCUS_BRIDGE` and returns the appropriate bridge implementation. For Phase 5, only `inmemory` is functional; `real` fails with a clear error.
**When to use:** At startup in the lifespan.
**Example:**
```python
import os

def create_bridge(bridge_type: str) -> Bridge:
    match bridge_type:
        case "inmemory":
            return InMemoryBridge(data=...)  # or empty for testing
        case "simulator":
            msg = "SimulatorBridge not yet implemented (Phase 7)"
            raise NotImplementedError(msg)
        case "real":
            msg = (
                "RealBridge not yet implemented (Phase 8). "
                "Set OMNIFOCUS_BRIDGE=inmemory for development."
            )
            raise NotImplementedError(msg)
        case _:
            msg = f"Unknown bridge type: {bridge_type!r}. Use: inmemory, simulator, real"
            raise ValueError(msg)

bridge_type = os.environ.get("OMNIFOCUS_BRIDGE", "real")
bridge = create_bridge(bridge_type)
```

### Pattern 3: Stdout Redirect Safety Net
**What:** Redirect `sys.stdout` to `sys.stderr` early in startup so any accidental `print()` call does not corrupt MCP protocol traffic on stdout.
**When to use:** In `__main__.py` before any other code runs.
**Example:**
```python
import sys

def main() -> None:
    # TOOL-04: stdout is reserved for MCP protocol traffic
    sys.stdout = sys.stderr  # type: ignore[assignment]

    # Now set up logging to stderr (which is where it goes by default)
    import logging
    logging.basicConfig(
        level=os.environ.get("OMNIFOCUS_LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    from omnifocus_operator.server import create_server
    server = create_server()
    server.run(transport="stdio")
```

### Pattern 4: MtimeSource for InMemoryBridge
**What:** InMemoryBridge needs a compatible MtimeSource. Since there is no filesystem path to watch, use a constant mtime source that always returns 0 (cache never invalidates -- which is correct for in-memory test data).
**When to use:** When `OMNIFOCUS_BRIDGE=inmemory`.
**Example:**
```python
class ConstantMtimeSource:
    """MtimeSource that always returns the same value (no cache invalidation)."""
    async def get_mtime_ns(self) -> int:
        return 0

# In the bridge factory:
if bridge_type == "inmemory":
    mtime_source = ConstantMtimeSource()
else:
    mtime_source = FileMtimeSource(path=ofocus_path)
```

### Anti-Patterns to Avoid
- **Importing concrete bridge types in service/server layers:** The service and MCP layers should only depend on the `Bridge` protocol, never on `InMemoryBridge` or `RealBridge` directly. Concrete types are only referenced in the factory function.
- **Creating the FastMCP instance at module level:** Module-level `FastMCP()` runs before lifespan, making DI impossible. Create it in a factory function.
- **Using `@mcp.tool()` at module level with closure over service:** This couples tool registration to module import order. Instead, register tools inside a function that receives the FastMCP instance.
- **Calling `asyncio.run()` in `__main__.py`:** FastMCP's `run()` method is synchronous and handles the async runtime internally via `anyio.run()`. Wrapping it in `asyncio.run()` would create a nested event loop error.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tool registration & schema | Custom JSON-RPC handler | `@mcp.tool()` decorator | FastMCP handles parameter/output schema generation, argument validation, error wrapping |
| Structured output schema | Manual `model_json_schema()` call | Return type annotation on tool function | FastMCP auto-detects BaseModel return types and generates outputSchema automatically |
| Stdio transport | Custom stdin/stdout reader/writer | `server.run(transport="stdio")` | SDK handles line-delimited JSON-RPC, encoding, stream management |
| Lifespan / DI | Manual async setup/teardown | FastMCP `lifespan` parameter | SDK manages context lifecycle, makes it available to tools via Context |
| Logging to stderr | Custom print-to-stderr wrapper | stdlib `logging.StreamHandler()` | Defaults to stderr; SDK's own logging uses the same mechanism |

**Key insight:** FastMCP 1.26.0 provides a complete, production-ready tool server framework. The only custom code needed is the domain-specific wiring (bridge factory, service layer, tool implementation).

## Common Pitfalls

### Pitfall 1: stdout Corruption Breaks MCP Protocol
**What goes wrong:** Any `print()` call or library that writes to stdout inserts non-JSON-RPC data into the MCP protocol stream, causing the client to fail silently or crash.
**Why it happens:** Python's default `print()` goes to stdout. Libraries like `pdb`, `warnings`, or debug output can write to stdout unexpectedly.
**How to avoid:** Redirect `sys.stdout = sys.stderr` as the very first action in `__main__.py`, before any imports that might trigger print statements. This is a safety net; proper code should use logging, but the redirect catches mistakes.
**Warning signs:** MCP client disconnects with parse errors; "invalid JSON" errors in client logs.

### Pitfall 2: Nested Event Loop from asyncio.run()
**What goes wrong:** Calling `asyncio.run()` around `server.run()` creates a nested event loop, raising `RuntimeError: This event loop is already running`.
**Why it happens:** FastMCP's `run()` calls `anyio.run()` internally, which creates its own event loop.
**How to avoid:** Call `server.run(transport="stdio")` directly from the synchronous `main()` function. Do not wrap it in `asyncio.run()`.
**Warning signs:** RuntimeError on startup about event loop.

### Pitfall 3: Forgetting model_rebuild() for Schema Generation
**What goes wrong:** Pydantic forward references in DatabaseSnapshot cause schema generation to fail with `PydanticUndefinedAnnotation`.
**Why it happens:** Models use `TYPE_CHECKING` imports and string annotations that need resolution.
**How to avoid:** The existing `models/__init__.py` already calls `model_rebuild()` with `_types_namespace` for all models. As long as `from omnifocus_operator.models import DatabaseSnapshot` is used (which triggers `__init__.py`), schemas work correctly. Verified: `DatabaseSnapshot.model_json_schema(by_alias=True)` produces correct camelCase schema.
**Warning signs:** `PydanticUndefinedAnnotation` errors at tool registration time.

### Pitfall 4: Lifespan Context Access Pattern
**What goes wrong:** Trying to access the service directly from a closure or global variable instead of via the Context parameter.
**Why it happens:** It's tempting to close over a service variable or use a module-level global.
**How to avoid:** Always access via `ctx.request_context.lifespan_context["service"]`. The Context is injected by FastMCP when it sees a parameter annotated with `Context` type.
**Warning signs:** `AttributeError` or `None` when accessing service; tests can't inject mocks.

### Pitfall 5: MtimeSource for InMemoryBridge
**What goes wrong:** InMemoryBridge has no filesystem path, so `FileMtimeSource` fails with `OSError`.
**Why it happens:** The repository requires an MtimeSource, and `FileMtimeSource` expects a real path.
**How to avoid:** Create a `ConstantMtimeSource` (always returns 0) for use with InMemoryBridge. The constant value means the cache never invalidates, which is correct behavior for in-memory test data.
**Warning signs:** `OSError: No such file or directory` at startup when using `OMNIFOCUS_BRIDGE=inmemory`.

## Code Examples

Verified patterns from MCP SDK 1.26.0 source and in-process testing:

### FastMCP Tool Registration with Annotations and Structured Output
```python
# Source: Verified against mcp 1.26.0 server/fastmcp/server.py
# and tested end-to-end with in-process client
from mcp.server.fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations
from omnifocus_operator.models import DatabaseSnapshot

mcp = FastMCP("omnifocus-operator", lifespan=app_lifespan)

@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def list_all(ctx: Context) -> DatabaseSnapshot:
    """Return the full OmniFocus database as structured data."""
    service: OperatorService = ctx.request_context.lifespan_context["service"]
    return await service.get_all_data()
```

When `list_all` is registered:
- `outputSchema` is auto-generated from `DatabaseSnapshot.model_json_schema()` with camelCase aliases
- Return value is serialized via `model_dump(mode="json", by_alias=True)` into `structuredContent`
- Unstructured fallback (TextContent with JSON) is also provided automatically by the SDK

### In-Process MCP Server Testing Pattern
```python
# Source: Verified end-to-end with mcp 1.26.0
import anyio
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage

async def test_list_all_returns_structured_data():
    server = create_server()  # Returns configured FastMCP instance

    # Create paired memory streams
    s2c_send, s2c_recv = anyio.create_memory_object_stream[SessionMessage](0)
    c2s_send, c2s_recv = anyio.create_memory_object_stream[SessionMessage](0)

    async with anyio.create_task_group() as tg:
        async def run_server():
            await server._mcp_server.run(
                c2s_recv, s2c_send,
                server._mcp_server.create_initialization_options(),
            )
        tg.start_soon(run_server)

        async with ClientSession(s2c_recv, c2s_send) as session:
            await session.initialize()

            # Verify tool listing
            tools = await session.list_tools()
            assert any(t.name == "list_all" for t in tools.tools)

            # Verify tool call
            result = await session.call_tool("list_all", {})
            assert result.structuredContent is not None
            assert "tasks" in result.structuredContent

            tg.cancel_scope.cancel()
```

### Lifespan with Pre-Warm and Logging
```python
# Source: Verified pattern against mcp 1.26.0 lifespan mechanism
import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("omnifocus_operator")

@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict]:
    bridge_type = os.environ.get("OMNIFOCUS_BRIDGE", "real")
    logger.info("Bridge type: %s", bridge_type)

    bridge = create_bridge(bridge_type)
    mtime_source = create_mtime_source(bridge_type)
    repository = OmniFocusRepository(bridge=bridge, mtime_source=mtime_source)
    service = OperatorService(repository=repository)

    logger.info("Pre-warming repository cache...")
    await repository.initialize()
    logger.info("Cache pre-warmed successfully")

    yield {"service": service}

    logger.info("Server shutting down")
```

### OperatorService (Thin Passthrough)
```python
# Service layer: architectural seam for future phases
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnifocus_operator.models import DatabaseSnapshot
    from omnifocus_operator.repository import OmniFocusRepository

class OperatorService:
    def __init__(self, repository: OmniFocusRepository) -> None:
        self._repository = repository

    async def get_all_data(self) -> DatabaseSnapshot:
        return await self._repository.get_snapshot()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual JSON-RPC handling | FastMCP decorator-based tools | mcp SDK 1.0+ | Zero boilerplate for tool registration |
| Custom schema generation | Auto-detect from return type | mcp SDK ~1.20+ | BaseModel return types auto-produce outputSchema |
| `structuredContent` manual | SDK handles conversion | mcp SDK ~1.20+ | `model_dump(mode="json", by_alias=True)` called automatically |
| Separate `outputSchema` kwarg | `structured_output` parameter on `@tool()` | mcp 1.26.0 | Auto-detection is default; explicit `structured_output=True/False` for override |

**Deprecated/outdated:**
- Standalone `fastmcp` package: Project correctly uses `mcp.server.fastmcp` from the official SDK, not the deprecated standalone package.
- Manual `outputSchema` construction: No need to call `model_json_schema()` manually -- FastMCP's `func_metadata` does it automatically from the return type annotation.

## Discretion Recommendations

### Logging Library: Use stdlib `logging`
**Recommendation:** stdlib `logging` (not structlog, not custom).

**Rationale:**
1. **Zero dependencies:** Project philosophy is single runtime dependency (`mcp`). Adding `structlog` violates this.
2. **SDK compatibility:** The MCP SDK's own `configure_logging` uses stdlib `logging`. Using the same system avoids configuration conflicts.
3. **stderr by default:** `logging.StreamHandler()` writes to stderr by default. No extra configuration needed.
4. **Sufficient for Phase 5:** The server logs startup, bridge selection, cache pre-warm, and tool invocations. This does not require structured JSON logging.

**Configuration:**
```python
import logging
import os

def configure_app_logging() -> None:
    level = os.environ.get("OMNIFOCUS_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
```

### Lifespan Pattern: FastMCP's Built-in Async Context Manager
**Recommendation:** Use FastMCP's `lifespan` parameter with `@asynccontextmanager`.

**Rationale:** This is the canonical FastMCP pattern. The yielded dict becomes the lifespan context, accessible from tools via `ctx.request_context.lifespan_context`. No custom machinery needed. Verified end-to-end with mcp 1.26.0.

### Error Response Format
**Recommendation:** Let FastMCP's default error handling propagate exceptions.

FastMCP wraps tool exceptions in `ToolError` and returns them as `CallToolResult(isError=True, content=[TextContent(text=str(error))])`. This is sufficient for Phase 5. Custom error formatting can be added in future phases if needed.

The lifespan errors (bridge not found, cache pre-warm failure) should propagate as raw exceptions, which will crash the server at startup with a clear traceback. This is the correct fail-fast behavior.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ --cov --cov-report=term-missing` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-01 | Three-layer architecture (MCP -> Service -> Repository) | integration | `uv run pytest tests/test_server.py::TestARCH01 -x` | Wave 0 |
| ARCH-02 | Bridge injection via env var, no code changes to switch | unit + integration | `uv run pytest tests/test_server.py::TestARCH02 -x` | Wave 0 |
| TOOL-01 | list_all returns full DatabaseSnapshot as structured data | integration | `uv run pytest tests/test_server.py::TestTOOL01 -x` | Wave 0 |
| TOOL-02 | Tool has readOnlyHint and idempotentHint annotations | integration | `uv run pytest tests/test_server.py::TestTOOL02 -x` | Wave 0 |
| TOOL-03 | Tool exposes outputSchema from Pydantic models | integration | `uv run pytest tests/test_server.py::TestTOOL03 -x` | Wave 0 |
| TOOL-04 | Server logs to stderr only, stdout reserved for MCP | unit | `uv run pytest tests/test_server.py::TestTOOL04 -x` | Wave 0 |

### Testing Strategy

**In-process MCP testing:** Use `anyio.create_memory_object_stream` to create paired streams, run server and client in the same process via `anyio.create_task_group`. This avoids subprocess overhead and provides direct access to structured results. Verified working with mcp 1.26.0.

**Service layer testing:** Unit tests with `InMemoryBridge` and `FakeMtimeSource` (reuse from test_repository.py). Service is a thin passthrough, so tests are simple delegation checks.

**Bridge factory testing:** Unit tests verifying env var -> bridge type mapping, error messages for unknown/unimplemented bridges.

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ --cov --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_service.py` -- covers OperatorService delegation to repository
- [ ] `tests/test_server.py` -- covers MCP server integration (tool registration, annotations, structured output, lifespan)
- [ ] Update `tests/conftest.py` -- may need shared fixtures for server testing (memory streams, server factory)

## Open Questions

1. **InMemoryBridge snapshot data for server startup**
   - What we know: InMemoryBridge accepts `data={}` for empty data or `data=make_snapshot_dict()` for test data. The lifespan needs to provide meaningful data when `OMNIFOCUS_BRIDGE=inmemory`.
   - What's unclear: Should the inmemory bridge start with empty collections or a small set of sample data?
   - Recommendation: Empty collections `{"tasks": [], "projects": [], "tags": [], "folders": [], "perspectives": []}` for production inmemory mode. Test fixtures provide their own data via `make_snapshot_dict()`. This keeps the inmemory bridge clean and predictable.

2. **ConstantMtimeSource location**
   - What we know: InMemoryBridge needs a MtimeSource that never invalidates. FileMtimeSource requires a real path.
   - What's unclear: Should ConstantMtimeSource live in repository/ (next to MtimeSource protocol) or in the bridge factory?
   - Recommendation: Place it in `repository/_mtime.py` alongside `MtimeSource` and `FileMtimeSource`. It satisfies the same protocol and is a legitimate MtimeSource implementation, not just a test double.

## Sources

### Primary (HIGH confidence)
- MCP SDK 1.26.0 source code (installed at `.venv/lib/python3.12/site-packages/mcp/`) -- FastMCP server, tool registration, func_metadata, lifespan, stdio transport, ToolAnnotations
- In-process verification: Tested FastMCP tool registration, structured output, annotations, lifespan context access, and in-process client-server communication -- all patterns confirmed working
- Existing codebase: DatabaseSnapshot, OmniFocusRepository, InMemoryBridge, MtimeSource -- verified schema generation and model_rebuild compatibility

### Secondary (MEDIUM confidence)
- None needed -- all findings verified against SDK source and in-process tests

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Only uses existing mcp dependency; all APIs verified against installed SDK source
- Architecture: HIGH - Lifespan DI pattern verified end-to-end with in-process testing; all SDK mechanisms confirmed working
- Pitfalls: HIGH - Each pitfall identified from SDK source analysis; stdout corruption and event loop nesting are well-documented MCP concerns

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable -- mcp SDK version pinned, patterns verified against installed version)
