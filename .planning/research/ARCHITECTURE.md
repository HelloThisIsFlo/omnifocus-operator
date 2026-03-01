# Architecture Research

**Domain:** Python MCP server with file-based IPC to macOS application
**Researched:** 2026-03-01
**Confidence:** HIGH

## System Overview

```
                        MCP Host (Claude, etc.)
                              |
                         stdio / JSON-RPC
                              |
                +=========================+
                |      MCP Server         |   Thin: tool registration,
                |  (FastMCP decorators)   |   request routing, response
                +=========================+   formatting. No logic.
                              |
                   method calls (async)
                              |
                +=========================+
                |     Service Layer       |   Business logic: filtering,
                |  (OmniFocusService)     |   semantic translation,
                +=========================+   search. Thin in M1,
                              |              grows in M2+.
                   method calls (async)
                              |
                +=========================+
                |   OmniFocus Repository  |   Data access: owns the
                |  (OmniFocusRepository)  |   snapshot, freshness check,
                |                         |   dedup lock, bridge calls.
                +=========================+
                       |            |
              snapshot cache    bridge.send_command()
              (in-memory)            |
                              +============+
                              |   Bridge   |  Pluggable interface
                              | Interface  |  (Protocol class)
                              +============+
                             /      |       \
                 +---------+ +----------+ +---------+
                 | InMemory| | Simulator| |  Real   |
                 |  Bridge | |  Bridge  | | Bridge  |
                 +---------+ +----------+ +---------+
                     |             |            |
                  (none)     file IPC +    file IPC +
                           poll response   poll response +
                                          URL scheme trigger
                                               |
                                         +-----------+
                                         | OmniFocus |
                                         |  (macOS)  |
                                         +-----------+
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| **MCP Server** | Tool registration via `@mcp.tool()` decorators, request routing, response formatting. Zero business logic. | MCP host (upstream), Service Layer (downstream) |
| **Service Layer** | Business logic and use cases. Filtering, semantic translation (e.g. decomposing `taskStatus` into availability + urgency), search. Thin passthrough in M1, grows substantially in M2+. | MCP Server (upstream), Repository (downstream), Bridge directly for UI ops in M4+ |
| **Repository** | Owns the in-memory database snapshot. Manages snapshot freshness (mtime check), deduplication lock (asyncio.Lock), and bridge invocation. Hides all OmniFocus communication complexity. | Service Layer (upstream), Bridge (downstream) |
| **Bridge Interface** | Abstract contract: `send_command(operation, params) -> response`. Pluggable implementations injected at startup. | Repository (upstream), OmniFocus or test fixtures (downstream) |
| **InMemoryBridge** | Returns test data from Python memory. No I/O. | Repository only |
| **SimulatorBridge** | File-based IPC: writes request JSON, polls for response JSON. No URL scheme trigger. Works with standalone mock simulator process. | Repository (upstream), mock simulator process (downstream via filesystem) |
| **RealBridge** | File-based IPC + URL scheme trigger (`omnifocus:///omnijs-run?script=...&arg=...`). Production bridge. | Repository (upstream), OmniFocus app (downstream via filesystem + URL scheme) |
| **Bridge Script** (`operatorBridgeScript.js`) | OmniJS script running inside OmniFocus. Reads commands, dumps database, writes responses atomically. Source of truth for data shape. | RealBridge / SimulatorBridge (via file IPC) |
| **Mock Simulator** | Standalone Python script simulating what OmniFocus would do. Watches `requests/` directory, writes responses to `responses/`. | SimulatorBridge (via file IPC) |
| **Pydantic Models** | Type-safe data representation. Derived from bridge script output shape. snake_case fields with camelCase aliases. | Used throughout all layers |

## Recommended Project Structure

```
omnifocus-operator/
├── pyproject.toml              # Project metadata, dependencies, scripts
├── src/
│   └── omnifocus_operator/
│       ├── __init__.py
│       ├── __main__.py         # Entry point: parse args, wire DI, mcp.run()
│       ├── server.py           # FastMCP instance, @mcp.tool() definitions
│       ├── service.py          # OmniFocusService class
│       ├── repository.py       # OmniFocusRepository class (snapshot, freshness, lock)
│       ├── models/
│       │   ├── __init__.py
│       │   ├── task.py         # Task Pydantic model
│       │   ├── project.py      # Project Pydantic model
│       │   ├── tag.py          # Tag Pydantic model
│       │   ├── folder.py       # Folder Pydantic model
│       │   ├── perspective.py  # Perspective Pydantic model
│       │   └── snapshot.py     # DatabaseSnapshot (container for all entities)
│       ├── bridge/
│       │   ├── __init__.py
│       │   ├── protocol.py     # Bridge Protocol (abstract interface)
│       │   ├── in_memory.py    # InMemoryBridge (unit tests)
│       │   ├── file_ipc.py     # FileIPCBridge (shared SimulatorBridge/RealBridge logic)
│       │   └── url_trigger.py  # URL scheme trigger for RealBridge
│       └── config.py           # Server configuration (CLI flags, IPC directory)
├── scripts/
│   └── mock_simulator.py       # Standalone mock OmniFocus simulator
├── bridge/
│   └── operatorBridgeScript.js # OmniJS bridge script (deployed to OmniFocus)
├── tests/
│   ├── conftest.py             # Shared fixtures (InMemoryBridge, test data builders)
│   ├── test_server.py          # MCP tool integration tests
│   ├── test_service.py         # Service layer unit tests
│   ├── test_repository.py      # Repository unit tests (snapshot, freshness, lock)
│   ├── test_bridge_ipc.py      # File IPC integration tests (with mock simulator)
│   └── test_models.py          # Pydantic model serialization/deserialization
└── .research/                  # Discovery research (existing)
```

### Structure Rationale

- **`src/omnifocus_operator/`**: Standard Python src-layout. Prevents accidental imports from project root. The `src/` prefix is the recommended Python packaging convention.
- **`models/`**: Separate module per entity type because models are the most frequently referenced code and each entity has enough fields to warrant its own file. A `snapshot.py` collects them into a single `DatabaseSnapshot` container.
- **`bridge/`**: Isolated bridge implementations behind a `Protocol`. The key architectural seam. `file_ipc.py` contains the shared request/response file mechanics used by both Simulator and Real modes. `url_trigger.py` isolates the macOS-specific URL scheme trigger.
- **`scripts/mock_simulator.py`**: Standalone, not imported by the server. Simulates OmniFocus for IPC testing.
- **`bridge/operatorBridgeScript.js`**: Kept in repo root-ish location (not under `src/`) because it deploys to OmniFocus, not to Python.

## Architectural Patterns

### Pattern 1: FastMCP Lifespan for Dependency Injection

**What:** Use FastMCP's `lifespan` async context manager to initialize the bridge, repository, and service at startup, then inject them into tool handlers via the `Context` parameter.

**When to use:** Always. This is how the MCP SDK intends resources to be managed.

**Trade-offs:** Slightly more boilerplate than global singletons, but provides proper lifecycle management (cleanup on shutdown), testability (swap bridge implementations), and type safety.

**Example:**
```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from mcp.server.fastmcp import FastMCP, Context

@dataclass
class AppContext:
    service: OmniFocusService

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    bridge = create_bridge(config)  # InMemory, Simulator, or Real
    repository = OmniFocusRepository(bridge)
    service = OmniFocusService(repository)
    yield AppContext(service=service)

mcp = FastMCP("omnifocus-operator", lifespan=app_lifespan)

@mcp.tool()
async def list_all(ctx: Context) -> str:
    service = ctx.request_context.lifespan_context.service
    snapshot = await service.list_all()
    return snapshot.model_dump_json(by_alias=True)
```

**Confidence:** HIGH -- this pattern is directly from the official MCP Python SDK examples.

### Pattern 2: Bridge as Python Protocol (Structural Typing)

**What:** Define the bridge interface as a `typing.Protocol` class rather than an ABC. Implementations satisfy the contract by having the right method signatures, no inheritance required.

**When to use:** When you want maximum flexibility for test doubles and the interface is simple (one method: `send_command`).

**Trade-offs:** Less explicit than ABC (no forced inheritance), but more Pythonic and plays well with dataclasses and test fakes.

**Example:**
```python
from typing import Protocol, Any

class Bridge(Protocol):
    async def send_command(
        self, operation: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...
```

**Confidence:** HIGH -- standard Python pattern, well-supported by type checkers.

### Pattern 3: Pydantic Model with camelCase Alias Generator

**What:** Use Pydantic v2's `alias_generator=to_camel` so Python code uses `snake_case` attributes while JSON serialization/deserialization uses `camelCase` matching the bridge script output.

**When to use:** All entity models. The bridge script returns camelCase JSON; Python convention demands snake_case.

**Trade-offs:** Must remember to use `by_alias=True` when serializing for MCP responses. `populate_by_name=True` allows construction with either convention.

**Example:**
```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class OmniFocusBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

class Task(OmniFocusBaseModel):
    id: str
    name: str
    due_date: str | None = None       # serializes as "dueDate"
    effective_due_date: str | None = None  # serializes as "effectiveDueDate"
    estimated_minutes: float | None = None
    # ... all fields from bridge script
```

**Confidence:** HIGH -- Pydantic v2 official documentation confirms `to_camel` alias generator.

### Pattern 4: Atomic File IPC with Polling

**What:** Request/response via JSON files in a shared directory. Writer creates `.tmp` file, then `os.rename()` to `.json` (atomic on same filesystem). Reader polls for `.json` file appearance.

**When to use:** SimulatorBridge and RealBridge. This is the established IPC protocol with OmniFocus.

**Trade-offs:** Polling introduces latency (configurable interval). But file-based IPC works within OmniFocus's sandbox, requires no additional dependencies, and atomic rename prevents partial reads.

**Example:**
```python
import asyncio
import json
import os
import uuid
from pathlib import Path

async def send_file_ipc(
    ipc_dir: Path,
    operation: str,
    params: dict | None = None,
    timeout: float = 10.0,
    poll_interval: float = 0.05,
) -> dict:
    request_id = str(uuid.uuid4())
    request_dir = ipc_dir / "requests"
    response_dir = ipc_dir / "responses"

    # Write request atomically
    request_data = {"operation": operation, "params": params or {}}
    tmp_path = request_dir / f"{request_id}.tmp"
    final_path = request_dir / f"{request_id}.json"
    tmp_path.write_text(json.dumps(request_data))
    os.rename(tmp_path, final_path)

    # Poll for response
    response_path = response_dir / f"{request_id}.json"
    elapsed = 0.0
    while elapsed < timeout:
        if response_path.exists():
            data = json.loads(response_path.read_text())
            response_path.unlink()  # cleanup
            return data
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(
        f"OmniFocus did not respond within {timeout}s -- is it running?"
    )
```

**Confidence:** HIGH -- the IPC protocol is specified in the project brief and proven by the bridge script.

### Pattern 5: Snapshot with Mtime-Based Freshness

**What:** Cache the full OmniFocus database in memory as a `DatabaseSnapshot`. On each read, `stat()` the `.ofocus` directory for mtime. If unchanged, serve from cache. If changed, trigger a fresh dump via the bridge and replace the entire snapshot.

**When to use:** All read operations go through the repository, which manages this snapshot.

**Trade-offs:** No partial invalidation -- the entire snapshot is replaced. But at ~1.5MB this is sub-millisecond and eliminates cache coherence complexity.

**Example:**
```python
class OmniFocusRepository:
    def __init__(self, bridge: Bridge, ofocus_path: Path | None = None):
        self._bridge = bridge
        self._ofocus_path = ofocus_path
        self._snapshot: DatabaseSnapshot | None = None
        self._last_mtime: float = 0.0
        self._lock = asyncio.Lock()

    async def get_snapshot(self) -> DatabaseSnapshot:
        if self._is_fresh():
            return self._snapshot

        async with self._lock:
            # Double-check after acquiring lock
            if self._is_fresh():
                return self._snapshot
            return await self._refresh()

    def _is_fresh(self) -> bool:
        if self._snapshot is None:
            return False
        if self._ofocus_path is None:
            return True  # InMemory mode, never stale
        current_mtime = self._ofocus_path.stat().st_mtime
        return current_mtime == self._last_mtime
```

**Confidence:** HIGH -- specified in project brief, mtime-based freshness is a well-established OS-level pattern.

## Data Flow

### Read Flow (M1: `list_all`)

```
MCP Host
  | (JSON-RPC: tools/call "list_all")
  v
MCP Server (@mcp.tool list_all)
  | ctx.request_context.lifespan_context.service
  v
OmniFocusService.list_all()
  | (passthrough in M1)
  v
OmniFocusRepository.get_snapshot()
  | 1. Check mtime of .ofocus directory
  | 2a. If fresh: return cached snapshot
  | 2b. If stale: acquire lock, call bridge
  v
Bridge.send_command("dump")
  |
  +-- InMemoryBridge: return test data immediately
  |
  +-- SimulatorBridge/RealBridge:
  |     1. Write request JSON atomically to requests/<uuid>.json
  |     2. (RealBridge only) Trigger URL: omnifocus:///omnijs-run?script=...&arg=<uuid>::::dump
  |     3. Poll responses/<uuid>.json (50ms interval, 10s timeout)
  |     4. Parse response JSON
  v
Repository: parse bridge response into Pydantic models
  | DatabaseSnapshot(tasks=[Task(...)], projects=[...], ...)
  v
Service: return snapshot
  v
MCP Server: serialize to JSON (by_alias=True for camelCase)
  v
MCP Host (receives structured JSON response)
```

### UI Flow (M4+: `show_perspective`)

```
MCP Host
  | (JSON-RPC: tools/call "show_perspective" {name: "Review"})
  v
MCP Server
  v
OmniFocusService.show_perspective("Review")
  | (bypasses Repository -- UI op, not data op)
  v
Bridge.send_command("set_perspective", {"name": "Review"})
  | (file IPC + URL trigger)
  v
OmniFocus switches UI perspective
```

### IPC Dispatch Protocol

The bridge script receives a dispatch string via the URL scheme `arg` parameter, using `::::` (quadruple colon) as delimiter:

```
<request_id>::::<operation>               (read ops)
<request_id>::::<operation>::::<param>    (parameterized ops)
```

Examples:
```
req-abc-123::::dump                       -> full database dump
req-abc-123::::read_view                  -> read current perspective tasks
req-abc-123::::set_perspective::::Review  -> switch perspective
req-abc-123::::add_task                   -> create task (payload in request file)
```

Read operations encode everything in the argument string. Write operations read their payload from the request file (future milestones).

### Key Data Flows

1. **Initial snapshot load:** On first `list_all` call, repository has no snapshot. Acquires lock, calls bridge `dump`, parses response into `DatabaseSnapshot`, stores snapshot + mtime. All subsequent calls serve from memory until mtime changes.

2. **Concurrent request deduplication:** Multiple parallel `list_all` calls when snapshot is stale. First caller acquires `asyncio.Lock`, triggers bridge dump. Other callers await the lock, then find a fresh snapshot and return immediately. Only one bridge call happens.

3. **Bridge mode selection:** At startup, the `__main__.py` entry point reads configuration (CLI args or env vars) to determine which bridge to instantiate: InMemory (testing), Simulator (IPC testing), or Real (production). This bridge is injected through the lifespan context. No code in MCP or service layers knows which bridge is active.

## Build Order (Dependency Graph)

The components have clear dependency ordering. Build bottom-up:

```
Phase 1: Pydantic Models
  |  No dependencies. Derived from bridge script output shape.
  |  Build these first -- they're the shared language of the entire system.
  v
Phase 2: Bridge Interface + InMemoryBridge
  |  Depends on: models (for return types)
  |  Define the Protocol. Build InMemoryBridge returning test fixtures.
  v
Phase 3: Repository
  |  Depends on: Bridge interface, models
  |  Snapshot management, mtime freshness, asyncio.Lock dedup.
  |  Testable with InMemoryBridge.
  v
Phase 4: Service Layer
  |  Depends on: Repository
  |  Thin passthrough in M1. Exists to reserve the architectural slot.
  v
Phase 5: MCP Server (tool registration)
  |  Depends on: Service, FastMCP lifespan pattern
  |  Wire @mcp.tool() decorators, lifespan context, entry point.
  v
Phase 6: File IPC Bridge (SimulatorBridge)
  |  Depends on: Bridge interface
  |  Atomic file writes, polling, request/response protocol.
  v
Phase 7: Mock Simulator Script
  |  Depends on: IPC protocol knowledge (but no code dependency)
  |  Standalone Python script. Tests IPC end-to-end.
  v
Phase 8: RealBridge (URL scheme trigger)
  |  Depends on: File IPC Bridge
  |  Adds macOS `open -g "omnifocus:///omnijs-run?..."` trigger.
  |  Same file IPC, different trigger mechanism.
```

**Build order rationale:**
- Models first because everything depends on them and they have zero dependencies.
- Bridge interface + InMemoryBridge second because the repository needs something to call. InMemoryBridge lets you test the repository without file I/O.
- Repository before service because the service calls the repository (even if it's a passthrough in M1).
- MCP Server last among the core layers because it depends on everything below it.
- File IPC and mock simulator after the core pipeline works end-to-end with InMemoryBridge. This way you validate the architecture first, then add IPC complexity.
- RealBridge last because it's just SimulatorBridge + a URL trigger. The only macOS-specific piece.

## Anti-Patterns

### Anti-Pattern 1: Leaking Bridge Awareness Into Upper Layers

**What people do:** MCP tool handlers or service methods directly reference bridge operations, IPC details, or bridge-specific error types.
**Why it's wrong:** Breaks the layering. If the bridge protocol changes, you'd need to update MCP tools and service methods. Makes testing harder -- you can't swap bridges without touching upper layers.
**Do this instead:** Upper layers speak in terms of domain objects (Task, Project, Snapshot). Only the repository knows the bridge exists. The service knows the repository. The MCP server knows the service.

### Anti-Pattern 2: Blocking File I/O in the Async Event Loop

**What people do:** Use synchronous `open()`, `read()`, `write()` for the file IPC polling in async code.
**Why it's wrong:** Blocks the asyncio event loop during file operations. For small JSON files (~1.5MB) the blocking time is negligible, but the `stat()` polling loop is the real concern -- synchronous `os.stat()` in a tight async loop could accumulate.
**Do this instead:** Use `asyncio.sleep()` for poll intervals (this naturally yields to the event loop). For the actual file reads/writes, synchronous is acceptable at this data size -- `Path.write_text()` and `Path.read_text()` for ~1.5MB complete in under 1ms. Do NOT add `aiofiles` dependency for this -- it adds complexity without meaningful benefit at this scale.

### Anti-Pattern 3: Inventing Fields Not in the Bridge Script

**What people do:** Add fields to Pydantic models that seem useful but aren't in the bridge dump (e.g., computed `priority_score`, `time_remaining`).
**Why it's wrong:** The bridge script is the schema source of truth. Adding fields creates a mismatch between what the bridge returns and what the model expects, causing deserialization failures. Computed fields belong in the service layer.
**Do this instead:** Models match the bridge dump exactly. Computed/derived values go in the service layer as separate methods or as presentation-layer transformations.

### Anti-Pattern 4: Global Mutable State Instead of Lifespan DI

**What people do:** Create module-level globals for the repository/service (e.g., `_service = None; def get_service(): global _service; ...`).
**Why it's wrong:** Untestable, no lifecycle management, race conditions during initialization, can't swap bridges for testing.
**Do this instead:** Use FastMCP's lifespan context manager. Resources initialize on startup, are available via `ctx.request_context.lifespan_context`, and clean up on shutdown.

### Anti-Pattern 5: Complex Nested Tool Arguments

**What people do:** Accept deeply nested dictionaries or complex objects as MCP tool parameters.
**Why it's wrong:** AI agents struggle with complex argument structures. Nested objects increase hallucination risk. Per MCP best practices, flatten arguments to top-level primitives and use constrained types (Literal, enums).
**Do this instead:** Use flat argument lists with clear names and types. Example: `list_tasks(project: str | None, flagged: bool | None, status: Literal["active", "completed"])` instead of `list_tasks(filters: dict)`.

## Integration Points

### External: OmniFocus Application

| Integration | Pattern | Notes |
|-------------|---------|-------|
| Database dump | File IPC (JSON request/response) | OmniJS bridge script handles serialization inside OmniFocus process |
| Script trigger | macOS URL scheme: `omnifocus:///omnijs-run?script=...&arg=...` | Triggered via `subprocess.run(["open", "-g", url])`. The `-g` flag opens in background without stealing focus. |
| Freshness detection | `.ofocus` directory mtime via `os.stat()` | The `.ofocus` package is OmniFocus's database bundle. Its mtime changes on any sync/edit. |
| IPC directory | `~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/` | Inside OmniFocus's sandbox. Both sides can read/write. Configurable for dev/test. |

### External: MCP Host (Claude, etc.)

| Integration | Pattern | Notes |
|-------------|---------|-------|
| Transport | stdio (JSON-RPC over stdin/stdout) | Default for Claude Desktop/Claude Code integration. Never write to stdout except via MCP SDK. |
| Tool discovery | FastMCP decorators auto-generate tool schemas | Docstrings become tool descriptions. Type hints become parameter schemas. |
| Configuration | `claude_desktop_config.json` or Claude Code MCP config | Points to `uv run` or `python -m omnifocus_operator` with args |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| MCP Server <-> Service | Direct async method calls | Service is injected via lifespan context |
| Service <-> Repository | Direct async method calls | Repository is a dependency of Service |
| Repository <-> Bridge | `bridge.send_command()` async method | Bridge is injected into Repository at construction |
| Service <-> Bridge (UI ops, M4+) | Direct `bridge.send_command()` | Bypasses repository for UI operations that don't touch the snapshot |

## Scaling Considerations

This is a single-user local tool (one OmniFocus installation, one MCP host). Traditional scaling concerns do not apply. The relevant "scaling" concerns are:

| Concern | Current Design | If It Becomes a Problem |
|---------|---------------|------------------------|
| Database size (~1.5MB, ~2400 tasks) | Full in-memory snapshot. Sub-ms filtering. | Even at 10x current size, in-memory is fine. Would need to reconsider only at >100MB, which is unrealistic for a personal task manager. |
| Concurrent MCP calls | asyncio.Lock deduplicates parallel bridge dumps. | Already handled. The lock ensures one dump at a time. |
| Bridge response time | 10s timeout, 50ms poll interval. | Tune poll interval if latency matters. Could use filesystem events (kqueue/FSEvents) instead of polling, but polling is simpler and adequate. |
| Stdout corruption | Never write to stdout (stdio transport). | Use `logging` module configured to stderr. |

## Sources

- [MCP Python SDK (official)](https://github.com/modelcontextprotocol/python-sdk) -- FastMCP API, lifespan pattern, tool registration (HIGH confidence)
- [Build an MCP Server (official tutorial)](https://modelcontextprotocol.io/docs/develop/build-server) -- Server structure, decorator pattern, logging rules (HIGH confidence)
- [MCP Best Practices by Philipp Schmid](https://www.philschmid.de/mcp-best-practices) -- Tool design: flat arguments, outcome-oriented tools, naming conventions (MEDIUM confidence)
- [IBM MCP Context Forge Best Practices](https://ibm.github.io/mcp-context-forge/best-practices/developing-your-mcp-server-python/) -- Testing approach, error handling, project structure (MEDIUM confidence)
- [Omni Automation Script URLs](https://omni-automation.com/script-url/index.html) -- `omnijs-run` URL scheme format, argument passing (HIGH confidence)
- [Pydantic ConfigDict (official)](https://docs.pydantic.dev/latest/api/config/) -- `alias_generator=to_camel`, `populate_by_name` (HIGH confidence)
- [MCP PyPI package](https://pypi.org/project/mcp/) -- Version 1.26.0, Python 3.10+ (HIGH confidence)
- [FastMCP Dependencies](https://gofastmcp.com/python-sdk/fastmcp-server-dependencies) -- DI pattern with Context, CurrentContext (MEDIUM confidence)

---
*Architecture research for: Python MCP server with file-based IPC to macOS application*
*Researched: 2026-03-01*
