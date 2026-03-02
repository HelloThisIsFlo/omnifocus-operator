# Phase 4: Repository and Snapshot Management - Research

**Researched:** 2026-03-02
**Domain:** Async caching repository with mtime-based invalidation
**Confidence:** HIGH

## Summary

Phase 4 builds a repository layer that loads a full `DatabaseSnapshot` from the bridge, caches it in memory, and refreshes only when the OmniFocus `.ofocus` directory's modification time changes. The technical domain is straightforward: an `asyncio.Lock` serializes access to the cached snapshot, `os.stat().st_mtime_ns` detects changes, and `asyncio.to_thread()` keeps the stat call non-blocking. The bridge protocol and snapshot model are already implemented (Phases 2-3), so this phase wires them together with caching, concurrency control, and a pluggable mtime source for testability.

The user's decisions are clear and narrow the design space significantly: fail-fast on all errors (no stale fallback), abort server startup on pre-warm failure, block all reads during refresh (no stale serving), and use a single `asyncio.Lock` for everything. These decisions simplify the implementation considerably -- there is no retry logic, no cooldown, no stale-data path.

**Primary recommendation:** Implement a single `OmniFocusRepository` class with constructor-injected bridge and mtime source, an `asyncio.Lock` guarding all snapshot access, and a `get_snapshot()` method that checks mtime and conditionally refreshes. Pre-warm via an async `initialize()` method called from the MCP lifespan context manager.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Fail fast on all errors: bridge failures, parse/validation failures propagate to caller immediately
- No stale data fallback -- if refresh fails, the error reaches the caller regardless of whether a cached snapshot exists
- No cooldown or backoff between failed refresh attempts -- next read simply tries again (MCP traffic is low-volume, no risk of hammering)
- Abort server startup if pre-warm dump fails -- server refuses to start without initial data
- MCP host (Claude Desktop, Claude Code) handles restart/retry -- server doesn't need its own retry logic
- Pre-warm naturally fits inside the MCP lifespan context manager -- if it raises, server never starts
- All reads block while a refresh is in progress -- reads wait for fresh data, never return stale
- Single `asyncio.Lock` for everything: prevents duplicate dumps AND serializes reads during refresh
- On first load (no cache), all reads block on the lock since there's no stale data to serve anyway
- After cache is warm, reads that don't trigger a refresh (mtime unchanged) return immediately without contention

### Claude's Discretion
- Error type strategy: whether to wrap BridgeErrors in RepositoryError or let them propagate raw
- Pre-warm location: inside MCP lifespan vs repository's own init -- pick what fits cleanest
- Mtime source abstraction: pluggable callable/protocol vs hardcoded path with temp dirs in tests

### Deferred Ideas (OUT OF SCOPE)
- Detect OmniFocus "closed" vs "broken" at startup -- return actionable message ("please open OmniFocus") vs generic error -- future milestone
- Auto-open OmniFocus via AppleScript if it's just closed -- future milestone
- Graceful degradation (serve stale data + warning on refresh failure) -- revisit if fail-fast proves too strict in real usage
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SNAP-01 | Repository loads full database snapshot from bridge dump into memory | Bridge `send_command("dump_all")` returns dict; `DatabaseSnapshot.model_validate()` parses it. Repository stores the result as `self._snapshot`. See Architecture Pattern 1. |
| SNAP-02 | Subsequent reads serve from in-memory snapshot without calling the bridge again | `get_snapshot()` checks mtime; if unchanged, returns `self._snapshot` directly. Verifiable via `InMemoryBridge.call_count`. See Architecture Pattern 2. |
| SNAP-03 | Repository checks `.ofocus` directory mtime (`st_mtime_ns`) on each read -- unchanged mtime serves cached data | `asyncio.to_thread(os.stat, path)` returns `stat_result.st_mtime_ns` (integer nanoseconds). Compare against stored `self._last_mtime_ns`. See Code Examples. |
| SNAP-04 | Changed mtime triggers fresh dump replacing the entire snapshot atomically | Simple Python attribute assignment `self._snapshot = new_snapshot` is atomic at the Python level. Under the lock, old snapshot is fully replaced before any reader sees it. |
| SNAP-05 | `asyncio.Lock` prevents parallel MCP calls from each triggering separate dumps | Single lock acquired in `get_snapshot()` before mtime check; all concurrent callers queue behind it. See Architecture Pattern 3. |
| SNAP-06 | Cache is pre-warmed at startup so the first request hits warm data | `initialize()` async method calls `_refresh()` once. Called from MCP lifespan context manager. If it raises, server startup aborts. See Architecture Pattern 4. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` (stdlib) | Python 3.12 | `asyncio.Lock` for concurrency, `asyncio.to_thread()` for non-blocking stat | Part of Python stdlib; no additional dependencies needed |
| `os` (stdlib) | Python 3.12 | `os.stat()` for file metadata, `st_mtime_ns` for nanosecond mtime | stdlib; provides integer nanosecond timestamps avoiding float precision issues |
| `pydantic` | 2.12.x (installed) | `DatabaseSnapshot.model_validate()` for parsing bridge response | Already used throughout project for all models |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-asyncio` | 1.3.x (installed) | Async test support (`asyncio_mode = "auto"`) | All repository tests are async |
| `pytest` | 9.x (installed) | Test framework | All unit tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncio.to_thread(os.stat, ...)` | `aiofiles.os.stat()` | Would add a dependency for a single stat call; `asyncio.to_thread` is lighter and already the project pattern |
| `asyncio.Lock` | `asyncio.Semaphore(1)` | Semaphore is more flexible but Lock is semantically correct and simpler for mutual exclusion |
| Storing mtime as `int` | Storing as `float` (`st_mtime`) | `st_mtime_ns` avoids floating-point comparison issues; project MEMORY.md already specifies this |

**Installation:** No new dependencies required. All stdlib + already installed.

## Architecture Patterns

### Recommended Project Structure
```
src/omnifocus_operator/
├── repository/
│   ├── __init__.py          # Re-exports OmniFocusRepository
│   └── _repository.py       # Repository implementation
├── bridge/                  # (existing)
└── models/                  # (existing)
```

### Pattern 1: Repository with Constructor Injection
**What:** Repository accepts a `Bridge` protocol and an mtime source via constructor, matching the project's established DI pattern.
**When to use:** Always -- this is the only pattern for the repository.
**Example:**
```python
from __future__ import annotations

import asyncio
from typing import Any, Callable, Protocol

from omnifocus_operator.bridge import Bridge
from omnifocus_operator.models import DatabaseSnapshot


class MtimeSource(Protocol):
    """Protocol for checking data freshness."""

    async def get_mtime_ns(self) -> int:
        """Return nanosecond mtime of the data source."""
        ...


class OmniFocusRepository:
    """Caching repository that loads snapshots from the bridge."""

    def __init__(
        self,
        bridge: Bridge,
        mtime_source: MtimeSource,
    ) -> None:
        self._bridge = bridge
        self._mtime_source = mtime_source
        self._lock = asyncio.Lock()
        self._snapshot: DatabaseSnapshot | None = None
        self._last_mtime_ns: int = 0
```

### Pattern 2: Mtime-Gated Cache Read
**What:** Check mtime before deciding whether to refresh. Under the lock, compare stored mtime against current mtime. If unchanged, return cached snapshot.
**When to use:** Every `get_snapshot()` call.
**Example:**
```python
async def get_snapshot(self) -> DatabaseSnapshot:
    async with self._lock:
        current_mtime = await self._mtime_source.get_mtime_ns()
        if self._snapshot is not None and current_mtime == self._last_mtime_ns:
            return self._snapshot
        return await self._refresh(current_mtime)
```

### Pattern 3: Lock-Serialized Refresh (Thundering Herd Prevention)
**What:** The `asyncio.Lock` ensures that if 10 concurrent MCP calls arrive while a refresh is in progress, only one refresh executes. The other 9 wait, then all see the fresh snapshot.
**When to use:** Built into `get_snapshot()`.
**Key insight:** Because the mtime check is INSIDE the lock, a waiting coroutine re-checks mtime after acquiring the lock. If another coroutine just refreshed, the mtime will match and no second refresh occurs.

**Important note on the user's design:** The user explicitly chose to have ALL reads block during refresh (no stale serving). This means the lock wraps the entire get_snapshot flow including the mtime check. This is simpler than a double-check pattern and matches the user's decision that "reads wait for fresh data, never return stale."

### Pattern 4: Pre-Warm via Lifespan
**What:** Repository exposes an `async initialize()` method. The MCP lifespan context manager calls it. If it raises, the server never starts.
**When to use:** Server startup.
**Example:**
```python
# In repository:
async def initialize(self) -> None:
    """Pre-warm the cache. Raises on failure (fail-fast)."""
    await self.get_snapshot()

# In MCP server lifespan (Phase 5 will wire this):
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime_source)
    await repo.initialize()  # Fails fast if bridge or mtime fails
    try:
        yield AppContext(repo=repo)
    finally:
        pass  # No cleanup needed for in-memory cache
```

### Pattern 5: Pluggable MtimeSource for Testing
**What:** Define an `MtimeSource` protocol. Production implementation wraps `os.stat().st_mtime_ns`. Test implementation returns controllable values.
**When to use:** Production uses `FileMtimeSource`; tests use a simple `FakeMtimeSource`.
**Example:**
```python
import os
import asyncio


class FileMtimeSource:
    """Production mtime source: checks a directory's modification time."""

    def __init__(self, path: str) -> None:
        self._path = path

    async def get_mtime_ns(self) -> int:
        stat_result = await asyncio.to_thread(os.stat, self._path)
        return stat_result.st_mtime_ns


class FakeMtimeSource:
    """Test mtime source: returns controllable values."""

    def __init__(self, mtime_ns: int = 0) -> None:
        self._mtime_ns = mtime_ns

    def set_mtime_ns(self, value: int) -> None:
        self._mtime_ns = value

    async def get_mtime_ns(self) -> int:
        return self._mtime_ns
```

### Anti-Patterns to Avoid
- **Double-check locking without the lock:** Never check mtime outside the lock and then re-check inside. The user's decision is clear: the entire `get_snapshot()` flow (mtime check + conditional refresh) runs under the lock.
- **Returning stale data on refresh failure:** User explicitly chose fail-fast. Never catch a bridge error and return the old snapshot.
- **Creating the Lock in `__init__` of a non-async context with a running loop:** `asyncio.Lock()` is safe to create outside an event loop in Python 3.10+. The lock binds to the loop when first used. No issue here.
- **Using `st_mtime` (float) instead of `st_mtime_ns` (int):** Float comparison can have precision issues. Project MEMORY.md mandates `st_mtime_ns`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async mutex | Custom locking mechanism | `asyncio.Lock` | stdlib, battle-tested, fair (FIFO), async context manager support |
| Non-blocking stat | Thread pool management | `asyncio.to_thread(os.stat, path)` | stdlib since 3.9, handles thread pool automatically |
| JSON-to-model parsing | Custom dict traversal | `DatabaseSnapshot.model_validate(data)` | Pydantic handles validation, type coercion, error reporting |
| Nanosecond timestamps | `time.time_ns()` or custom | `os.stat().st_mtime_ns` | Directly from filesystem, integer precision, no float issues |

**Key insight:** This phase uses only Python stdlib for all new functionality. The complexity is in the concurrency design, not the technology stack.

## Common Pitfalls

### Pitfall 1: Lock Starvation Under Slow Bridge
**What goes wrong:** If the bridge dump takes 5+ seconds, all concurrent reads block for that duration.
**Why it happens:** The lock serializes everything, including reads that would have been served from cache.
**How to avoid:** This is acceptable per user's design decision ("all reads block while refresh is in progress"). The MCP traffic volume is low (one call every ~5 seconds). Document this as a known design choice, not a bug.
**Warning signs:** If bridge dumps consistently take >2 seconds, monitor for MCP timeout issues in Phase 5.

### Pitfall 2: Mtime Not Updating on OmniFocus Changes
**What goes wrong:** The `.ofocus` directory mtime doesn't change when OmniFocus modifies individual files inside it (macOS may not update parent directory mtime for in-place file edits).
**Why it happens:** macOS HFS+/APFS behavior: modifying a file inside a directory does NOT always update the directory's mtime. Only adding/removing files does.
**How to avoid:** This is a known limitation documented in project MEMORY.md (the research noted this). The `.ofocus` bundle uses a transaction-log format where new files ARE added on each sync, so directory mtime should update. If it doesn't, this would need investigation in Phase 8 (UAT). For Phase 4, implement the mtime check as designed and test with the fake mtime source.
**Warning signs:** During UAT (Phase 8), if data appears stale after OmniFocus changes, this is the first thing to check.

### Pitfall 3: Forgetting `from __future__ import annotations`
**What goes wrong:** Forward references and `X | None` syntax may fail at runtime without the future import.
**Why it happens:** Project convention uses this consistently but it's easy to forget in new files.
**How to avoid:** Every new `.py` file must start with `from __future__ import annotations`.
**Warning signs:** `TypeError` or `NameError` at import time.

### Pitfall 4: Creating asyncio.Lock Before Event Loop Exists
**What goes wrong:** In Python <3.10, creating `asyncio.Lock()` without a running loop raised `DeprecationWarning` or `RuntimeError`.
**Why it happens:** Older Python versions bound the lock to the current event loop at creation time.
**How to avoid:** Python 3.12 (project target) has no such issue. `asyncio.Lock()` created in `__init__` is safe -- it binds to the running loop when first awaited. No workaround needed.
**Warning signs:** None on Python 3.12.

### Pitfall 5: Testing Concurrency Without Actually Testing Concurrency
**What goes wrong:** Tests verify sequential behavior but miss race conditions.
**Why it happens:** Async tests that `await` each call sequentially don't exercise the lock.
**How to avoid:** Use `asyncio.gather()` to fire multiple `get_snapshot()` calls simultaneously, then verify `bridge.call_count == 1` (only one dump occurred despite N concurrent callers).
**Warning signs:** Tests pass but lock is commented out and nothing breaks.

## Code Examples

Verified patterns from official sources and project conventions:

### Non-Blocking File Stat
```python
# Source: Python 3.12 stdlib (asyncio.to_thread + os.stat)
import asyncio
import os

async def get_mtime_ns(path: str) -> int:
    """Get file/directory mtime in nanoseconds, non-blocking."""
    stat_result = await asyncio.to_thread(os.stat, path)
    return stat_result.st_mtime_ns
```

### Mtime-Gated Refresh Under Lock
```python
# Pattern derived from user decisions in CONTEXT.md
async def get_snapshot(self) -> DatabaseSnapshot:
    """Return current snapshot, refreshing if data has changed."""
    async with self._lock:
        current_mtime = await self._mtime_source.get_mtime_ns()
        if self._snapshot is not None and current_mtime == self._last_mtime_ns:
            return self._snapshot
        return await self._refresh(current_mtime)

async def _refresh(self, current_mtime: int) -> DatabaseSnapshot:
    """Dump from bridge and replace cached snapshot. Caller holds the lock."""
    raw = await self._bridge.send_command("dump_all")
    snapshot = DatabaseSnapshot.model_validate(raw)
    self._snapshot = snapshot
    self._last_mtime_ns = current_mtime
    return snapshot
```

### Concurrent Access Test Pattern
```python
# Testing that the lock prevents duplicate dumps
import asyncio
from omnifocus_operator.bridge import InMemoryBridge
from tests.conftest import make_snapshot_dict

async def test_concurrent_reads_single_dump():
    bridge = InMemoryBridge(data=make_snapshot_dict())
    mtime = FakeMtimeSource(mtime_ns=1000)
    repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime)

    # Fire 10 concurrent reads
    results = await asyncio.gather(*[
        repo.get_snapshot() for _ in range(10)
    ])

    # All 10 got the same snapshot, but bridge was called only once
    assert bridge.call_count == 1
    assert all(r is results[0] for r in results)
```

### MCP Lifespan Pre-Warm (Preview for Phase 5)
```python
# Source: MCP Python SDK official docs (Context7, HIGH confidence)
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from mcp.server.fastmcp import FastMCP

@dataclass
class AppContext:
    repo: OmniFocusRepository

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime_source)
    await repo.initialize()  # Pre-warm; raises on failure = server won't start
    yield AppContext(repo=repo)

mcp = FastMCP("OmniFocus Operator", lifespan=app_lifespan)
```

## Discretion Recommendations

### Error Type Strategy
**Recommendation: Let BridgeErrors propagate raw.** Do NOT wrap in a RepositoryError.

Rationale:
- The repository is a thin caching layer, not a business logic layer
- Wrapping adds noise without information: `RepositoryError(cause=BridgeTimeoutError(...))` tells the caller nothing that `BridgeTimeoutError(...)` doesn't
- The user said "fail fast" -- errors should reach the caller with maximum context
- If a RepositoryError is needed later (e.g., "snapshot parse failed"), add it then (YAGNI)
- One exception: Pydantic `ValidationError` from `model_validate()` could optionally be wrapped to add the operation context, but this is a bridge protocol error (malformed response), so `BridgeProtocolError` may be more appropriate

### Pre-Warm Location
**Recommendation: Repository's own `async initialize()` method, called from MCP lifespan.**

Rationale:
- Repository owns its initialization logic; the lifespan just calls `initialize()`
- This keeps the repository testable independently of the MCP server
- Tests call `await repo.initialize()` directly
- The lifespan context manager (Phase 5) calls the same method
- Matches the pattern from MCP SDK docs where lifespan initializes resources

### Mtime Source Abstraction
**Recommendation: Use a `Protocol` with a single `async get_mtime_ns() -> int` method.**

Rationale:
- Matches the project's established pattern (Bridge uses Protocol)
- Clean separation: `FileMtimeSource` for production, `FakeMtimeSource` for tests
- `FakeMtimeSource` with `set_mtime_ns()` makes cache invalidation tests trivial
- No need for temp directories or real filesystem in unit tests
- More explicit than a bare `Callable` -- the Protocol name documents intent

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `st_mtime` (float seconds) | `st_mtime_ns` (int nanoseconds) | Python 3.3 | Avoids float comparison bugs |
| `@asyncio.coroutine` + `yield from` | `async def` + `await` | Python 3.5 | Modern syntax, project standard |
| `loop.run_in_executor(None, fn)` | `asyncio.to_thread(fn)` | Python 3.9 | Cleaner API, same behavior |
| Lock creation requires running loop | Lock binds on first use | Python 3.10 | Safe to create Lock in `__init__` |

**Deprecated/outdated:**
- `asyncio.Lock(loop=...)` parameter: Removed in Python 3.10. Don't pass a loop argument.
- `with await lock:` syntax: Removed in Python 3.9. Use `async with lock:`.

## Open Questions

1. **OmniFocus `.ofocus` directory mtime behavior on data changes**
   - What we know: The `.ofocus` bundle uses a transaction-log format where new `.zip` files are added on each sync. Adding files to a directory DOES update its mtime on macOS.
   - What's unclear: Whether ALL types of OmniFocus data changes (task edits, project moves, tag changes) result in new transaction files, or if some are batched.
   - Recommendation: Implement as designed using mtime. Verify behavior during Phase 8 UAT against live OmniFocus. The mtime source abstraction makes it easy to swap strategies later if needed.

2. **Snapshot size and parse performance**
   - What we know: A typical OmniFocus database has hundreds to low thousands of tasks. Pydantic v2 is fast (Rust core).
   - What's unclear: Parse time for very large databases (10k+ tasks).
   - Recommendation: Not a concern for Phase 4. If profiling shows issues in Phase 8 UAT, optimize then. The architecture supports swapping the parse strategy without changing the repository contract.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 1.3.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_repository.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SNAP-01 | First call triggers bridge dump and returns populated snapshot | unit | `uv run pytest tests/test_repository.py::TestRepository::test_first_call_triggers_dump -x` | Wave 0 |
| SNAP-02 | Subsequent calls return cached snapshot (no bridge call) | unit | `uv run pytest tests/test_repository.py::TestRepository::test_cached_read_no_bridge_call -x` | Wave 0 |
| SNAP-03 | Unchanged mtime serves cached data | unit | `uv run pytest tests/test_repository.py::TestRepository::test_unchanged_mtime_serves_cache -x` | Wave 0 |
| SNAP-04 | Changed mtime triggers fresh dump replacing snapshot | unit | `uv run pytest tests/test_repository.py::TestRepository::test_changed_mtime_triggers_refresh -x` | Wave 0 |
| SNAP-05 | Lock prevents parallel dumps on concurrent reads | unit | `uv run pytest tests/test_repository.py::TestRepository::test_concurrent_reads_single_dump -x` | Wave 0 |
| SNAP-06 | Pre-warm at startup (initialize) | unit | `uv run pytest tests/test_repository.py::TestRepository::test_initialize_prewarms_cache -x` | Wave 0 |

### Additional Test Scenarios
| Scenario | Test Type | Automated Command |
|----------|-----------|-------------------|
| Bridge error propagates to caller (fail-fast) | unit | `uv run pytest tests/test_repository.py::TestRepository::test_bridge_error_propagates -x` |
| Parse error (invalid data from bridge) propagates | unit | `uv run pytest tests/test_repository.py::TestRepository::test_parse_error_propagates -x` |
| Initialize failure prevents usage | unit | `uv run pytest tests/test_repository.py::TestRepository::test_initialize_failure_raises -x` |
| Mtime source error propagates | unit | `uv run pytest tests/test_repository.py::TestRepository::test_mtime_error_propagates -x` |
| FileMtimeSource with real file (integration) | integration | `uv run pytest tests/test_repository.py::TestFileMtimeSource -x` |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_repository.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_repository.py` -- covers SNAP-01 through SNAP-06 + error propagation
- [ ] Shared fixtures: `FakeMtimeSource` in conftest.py or test file (TBD by planner)

*(No framework install needed -- pytest + pytest-asyncio already configured)*

## Sources

### Primary (HIGH confidence)
- Python 3.12 stdlib: `asyncio.Lock` -- [asyncio sync primitives docs](https://docs.python.org/3/library/asyncio-sync.html)
- Python 3.12 stdlib: `os.stat`, `stat_result.st_mtime_ns` -- [os module docs](https://docs.python.org/3/library/os.html)
- Python 3.12 stdlib: `asyncio.to_thread` -- [asyncio task docs](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
- MCP Python SDK: FastMCP lifespan pattern -- Context7 `/modelcontextprotocol/python-sdk` (verified code examples from README.md)
- Existing project code: `Bridge` protocol, `InMemoryBridge`, `DatabaseSnapshot`, `BridgeError` hierarchy

### Secondary (MEDIUM confidence)
- OmniFocus `.ofocus` bundle format uses transaction logs (zip files) -- [Omni Group forums](https://discourse.omnigroup.com/t/how-to-migrate-data-from-of3-to-of4/70273)
- macOS directory mtime updates when files are added/removed (not modified in place) -- general POSIX knowledge verified against Python docs

### Tertiary (LOW confidence)
- OmniFocus 4 sandbox path `~/Library/Containers/com.omnigroup.OmniFocus4/` -- inferred from OmniFocus 3 path pattern; needs verification in Phase 8 UAT

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib, no new dependencies, patterns verified in official docs
- Architecture: HIGH -- user decisions eliminate ambiguity; single Lock + mtime + fail-fast is simple and clear
- Pitfalls: HIGH -- concurrency pitfalls well-understood; mtime edge case documented with mitigation plan

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable domain -- stdlib APIs don't change)
