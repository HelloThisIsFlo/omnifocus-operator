# Phase 11: DataSource Protocol - Research

**Researched:** 2026-03-07
**Domain:** Python protocol-based architecture refactoring
**Confidence:** HIGH

## Summary

Phase 11 restructures the repository layer from a single concrete class (`OmniFocusRepository` in `repository.py`) into a protocol-based package (`repository/`) with multiple implementations. The current `OmniFocusRepository` combines caching, bridge communication, and adapter transformation -- all of which become concerns of `BridgeRepository` only. A new `Repository` protocol defines the abstract interface, and `InMemoryRepository` provides a clean test double.

This is a pure refactoring phase -- no new functionality, no new dependencies, no runtime behavior changes. The complexity is in the migration: 233 tests must stay green throughout, imports must be updated across 8+ files, and `MtimeSource` must relocate from the repository module into the bridge package.

**Primary recommendation:** Execute as an incremental refactor -- introduce protocol and package structure first, then migrate implementations, then update consumers, then clean up tests. Never break tests between commits.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Repository becomes a **protocol** (not DataSource) -- no separate DataSource concept
- Three implementations: `BridgeRepository`, `InMemoryRepository`, `SQLiteRepository` (Phase 12)
- Service calls Repository directly: `Service -> Repository (protocol)`
- Each implementation owns both data access AND query strategy
- SQLite reads are ~46ms -- caching unnecessary for primary path
- Caching logic moves INTO `BridgeRepository` only
- `MtimeSource` protocol and implementations become internal to bridge package
- `bridge/` and `repository/` are **peer top-level packages** (flat, not nested)
- Bridge adapter (`adapt_snapshot`) stays in `bridge/adapter.py`
- All repository-level tests use `InMemoryRepository` -- no Bridge in repo tests
- Bridge tests stay in their own test files
- Zero backward compatibility -- clean break, no deprecation
- Create `docs/` folder with architecture overview document

### Claude's Discretion
- Repository protocol exact method signature (name, return type)
- InMemoryRepository constructor API (raw dict vs pre-built entities)
- Concurrency strategy per implementation (BridgeRepository keeps lock, others decide)
- Server wiring / factory pattern for selecting repository implementation
- File reorganization details during full cleanup
- Architecture doc structure and content depth

### Deferred Ideas (OUT OF SCOPE)
- Writes through Repository vs Bridge directly -- future milestone decision
- SQLiteRepository naming -- may rename to HybridRepository later
- Bridge nesting under Repository -- reconsidered only if all Bridge usage goes through Repository
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ARCH-01 | DataSource protocol abstracts the read path so SQLite and Bridge implementations are swappable | Repository protocol with `get_snapshot()` method; structural typing via `typing.Protocol` |
| ARCH-02 | Repository layer consumes DataSource protocol instead of Bridge + MtimeSource directly | `BridgeRepository` encapsulates Bridge + MtimeSource + adapter; service takes `Repository` protocol |
| ARCH-03 | InMemoryDataSource implementation exists for testing | `InMemoryRepository` accepts pre-built `DatabaseSnapshot` or entity lists; used in all repo-level tests |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typing.Protocol | stdlib | Structural subtyping for Repository protocol | Already used for Bridge and MtimeSource in this project |
| typing.runtime_checkable | stdlib | isinstance() checks in tests | Already used for MtimeSource protocol |
| asyncio.Lock | stdlib | Concurrency in BridgeRepository | Already used in current OmniFocusRepository |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic v2 | existing | DatabaseSnapshot model validation | BridgeRepository only (parse raw bridge data) |
| pytest | existing | Test framework | All test files |

### Alternatives Considered
None -- this phase uses only existing project dependencies. No new libraries needed.

## Architecture Patterns

### Target Package Structure
```
src/omnifocus_operator/
  bridge/
    __init__.py        # exports (add MtimeSource, FileMtimeSource, ConstantMtimeSource)
    adapter.py         # adapt_snapshot() -- unchanged
    errors.py          # unchanged
    factory.py         # create_bridge() -- unchanged
    in_memory.py       # InMemoryBridge -- unchanged
    mtime.py           # NEW: MtimeSource protocol + FileMtimeSource + ConstantMtimeSource (moved from repository.py)
    protocol.py        # Bridge protocol -- unchanged
    real.py            # RealBridge -- unchanged
    simulator.py       # SimulatorBridge -- unchanged
  repository/
    __init__.py        # exports Repository protocol + BridgeRepository + InMemoryRepository
    protocol.py        # Repository protocol definition
    bridge.py          # BridgeRepository (absorbs current OmniFocusRepository logic)
    in_memory.py       # InMemoryRepository (new, for testing)
  models/             # unchanged
  server.py           # updated imports + wiring
  service.py          # updated type hint: Repository instead of OmniFocusRepository
  simulator/          # unchanged
```

### Pattern 1: Repository Protocol
**What:** A `typing.Protocol` class defining the read interface.
**When to use:** All repository consumers (service, server, tests).
**Example:**
```python
from typing import Protocol, runtime_checkable
from omnifocus_operator.models.snapshot import DatabaseSnapshot

@runtime_checkable
class Repository(Protocol):
    async def get_snapshot(self) -> DatabaseSnapshot: ...
```

**Design notes:**
- Method name `get_snapshot()` matches current `OmniFocusRepository.get_snapshot()` -- zero service-layer changes
- `runtime_checkable` allows `isinstance(repo, Repository)` in tests
- Future phases add `get_tasks(filters)` etc. to this protocol

### Pattern 2: BridgeRepository (absorbs current caching logic)
**What:** Concrete implementation wrapping Bridge + MtimeSource + adapter.
**When to use:** Production with OmniJS bridge fallback.
**Example:**
```python
class BridgeRepository:
    def __init__(self, bridge: Bridge, mtime_source: MtimeSource) -> None:
        self._bridge = bridge
        self._mtime_source = mtime_source
        self._lock = asyncio.Lock()
        self._snapshot: DatabaseSnapshot | None = None
        self._last_mtime_ns: int = 0

    async def get_snapshot(self) -> DatabaseSnapshot:
        async with self._lock:
            current_mtime = await self._mtime_source.get_mtime_ns()
            if self._snapshot is None or current_mtime != self._last_mtime_ns:
                self._snapshot = await self._refresh(current_mtime)
            return self._snapshot

    async def _refresh(self, current_mtime: int) -> DatabaseSnapshot:
        raw = await self._bridge.send_command("snapshot")
        adapt_snapshot(raw)
        snapshot = DatabaseSnapshot.model_validate(raw)
        self._last_mtime_ns = current_mtime
        return snapshot
```

**Key insight:** This is essentially a copy of current `OmniFocusRepository` with a new name. The logic is identical.

### Pattern 3: InMemoryRepository (test double)
**What:** Repository that returns pre-built data without any bridge/adapter/validation.
**When to use:** All repository-level and service-level tests.
**Example:**
```python
class InMemoryRepository:
    def __init__(self, snapshot: DatabaseSnapshot) -> None:
        self._snapshot = snapshot

    async def get_snapshot(self) -> DatabaseSnapshot:
        return self._snapshot
```

**Design notes:**
- Accepts a pre-built `DatabaseSnapshot` (not raw dicts) -- tests use `conftest.make_snapshot_dict()` + `DatabaseSnapshot.model_validate()`
- No caching, no locking, no adapter -- just returns data
- Optionally add a `set_snapshot()` for tests that need to change data mid-test

### Pattern 4: MtimeSource relocation
**What:** Move `MtimeSource`, `FileMtimeSource`, `ConstantMtimeSource` from `repository.py` to `bridge/mtime.py`.
**When to use:** These are bridge-internal concerns (only `BridgeRepository` uses them).
**Key consideration:** Update `bridge/__init__.py` to export them, since `server.py` currently imports `ConstantMtimeSource` from `repository`.

### Anti-Patterns to Avoid
- **Re-validating data in InMemoryRepository:** Tests should construct valid `DatabaseSnapshot` objects once; the repository just returns them. Don't run `model_validate()` on every `get_snapshot()` call.
- **Keeping backward-compat aliases:** CONTEXT.md says "zero backward compatibility -- clean break." Don't leave `OmniFocusRepository` as a deprecated alias.
- **Mixing bridge concerns into Repository protocol:** The protocol should know nothing about bridges, mtime, or adapters. Just `get_snapshot() -> DatabaseSnapshot`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Protocol definition | ABC/base class | `typing.Protocol` | Structural subtyping; no inheritance needed; already project pattern |
| Test snapshot creation | Manual dict construction in every test | `conftest.make_snapshot_dict()` + `DatabaseSnapshot.model_validate()` | Factories already exist and maintain consistency |

## Common Pitfalls

### Pitfall 1: Import cycle between repository and bridge packages
**What goes wrong:** `repository/bridge.py` imports from `bridge/` and `bridge/mtime.py` could end up importing from `repository/`.
**Why it happens:** Refactoring moves code between packages; easy to create circular dependencies.
**How to avoid:** Dependency is one-way: `repository/bridge.py` -> `bridge/`. Bridge package never imports from repository package. MtimeSource lives in bridge, used by `repository/bridge.py`.
**Warning signs:** `ImportError` at module load time.

### Pitfall 2: Breaking test_service.py and test_server.py wiring
**What goes wrong:** These files currently construct `OmniFocusRepository(bridge=..., mtime_source=...)`. After refactoring, this class no longer exists at that import path.
**Why it happens:** Forgetting to update all consumers.
**How to avoid:** Grep for all imports of `OmniFocusRepository`, `ConstantMtimeSource`, `MtimeSource` from `repository` module. Update every occurrence.
**Warning signs:** `ImportError` in test collection.

### Pitfall 3: Losing the `repository.py` -> `repository/` migration
**What goes wrong:** Python sees both `repository.py` and `repository/` and gets confused.
**Why it happens:** Git doesn't track file renames as atomic operations.
**How to avoid:** Delete `repository.py` in the same commit that creates `repository/__init__.py`. Never have both exist simultaneously.
**Warning signs:** `ModuleNotFoundError` or wrong module loaded.

### Pitfall 4: server.py lifespan imports breaking
**What goes wrong:** `server.py` has lazy imports inside `app_lifespan()` -- `from omnifocus_operator.repository import ...`. These must be updated.
**Why it happens:** Lazy imports are easy to miss in grep because they're inside function bodies.
**How to avoid:** Search for ALL occurrences of `from omnifocus_operator.repository` across the entire codebase, including inside functions.
**Warning signs:** Runtime errors during server startup, not at import time.

### Pitfall 5: ErrorOperatorService inherits from OperatorService
**What goes wrong:** `ErrorOperatorService` inherits from `OperatorService` which takes `OmniFocusRepository` in its type hint. After refactoring, this type hint changes to `Repository`.
**Why it happens:** Cascading type changes.
**How to avoid:** Update `OperatorService.__init__` type hint to `Repository` (the protocol). `ErrorOperatorService` bypasses `__init__` anyway via `object.__setattr__`.
**Warning signs:** Type checker complaints.

## Code Examples

### Repository protocol definition
```python
# repository/protocol.py
from __future__ import annotations
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnifocus_operator.models.snapshot import DatabaseSnapshot

@runtime_checkable
class Repository(Protocol):
    """Protocol for OmniFocus data access implementations."""
    async def get_snapshot(self) -> DatabaseSnapshot: ...
```

### InMemoryRepository
```python
# repository/in_memory.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnifocus_operator.models.snapshot import DatabaseSnapshot

class InMemoryRepository:
    """Test repository that returns pre-built snapshot data."""

    def __init__(self, snapshot: DatabaseSnapshot) -> None:
        self._snapshot = snapshot

    async def get_snapshot(self) -> DatabaseSnapshot:
        return self._snapshot
```

### Updated service.py type hint
```python
# service.py (updated)
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnifocus_operator.repository import Repository

class OperatorService:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository
```

### Updated server.py wiring
```python
# server.py app_lifespan (updated)
from omnifocus_operator.repository import BridgeRepository
from omnifocus_operator.bridge.mtime import ConstantMtimeSource, FileMtimeSource

# For inmemory/simulator:
repository = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())

# For real:
repository = BridgeRepository(bridge=bridge, mtime_source=FileMtimeSource(path=ofocus_path))
```

### Migrated test pattern (test_service.py)
```python
# Before:
bridge = InMemoryBridge(data=make_snapshot_dict())
mtime = FakeMtimeSource()
repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime)
service = OperatorService(repository=repo)

# After:
from omnifocus_operator.models.snapshot import DatabaseSnapshot
from omnifocus_operator.repository import InMemoryRepository

snapshot = DatabaseSnapshot.model_validate(make_snapshot_dict())
repo = InMemoryRepository(snapshot=snapshot)
service = OperatorService(repository=repo)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `repository.py` file | `repository/` package with protocol | This phase | Clean separation of concerns |
| `OmniFocusRepository` concrete class | `Repository` protocol + implementations | This phase | Swappable data sources |
| MtimeSource in repository module | MtimeSource in bridge package | This phase | Correct ownership (bridge concern) |
| Tests use InMemoryBridge + ConstantMtimeSource | Tests use InMemoryRepository | This phase | Cleaner test isolation |

## Open Questions

1. **InMemoryRepository constructor: snapshot vs entities**
   - What we know: Tests currently use `make_snapshot_dict()` which returns raw dicts
   - Recommendation: Accept `DatabaseSnapshot` objects. Helper in conftest: `make_snapshot() -> DatabaseSnapshot` that wraps `DatabaseSnapshot.model_validate(make_snapshot_dict())`
   - Reasoning: InMemoryRepository should be above the validation layer; tests that need invalid data test the bridge/adapter, not the repository

2. **Repository `__init__.py` exports**
   - What we know: Need clean public API for the package
   - Recommendation: Export `Repository`, `BridgeRepository`, `InMemoryRepository` from `__init__.py`
   - Factory function is optional -- `server.py` can import implementations directly since routing logic is simple (env var check)

3. **Architecture doc scope**
   - What we know: CONTEXT.md says "create architecture overview in docs/"
   - Recommendation: Keep it concise -- diagram of Service -> Repository (protocol) -> implementations, plus rationale for key decisions (why Repository not DataSource, why flat not nested, deferred writes question)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run python -m pytest tests/ -x -q` |
| Full suite command | `uv run python -m pytest tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-01 | Repository protocol exists; BridgeRepository and InMemoryRepository satisfy it | unit | `uv run python -m pytest tests/test_repository.py -x -q` | Yes (will be restructured) |
| ARCH-02 | Service layer accepts Repository protocol; BridgeRepository encapsulates Bridge+MtimeSource | unit + integration | `uv run python -m pytest tests/test_service.py tests/test_server.py -x -q` | Yes (will be updated) |
| ARCH-03 | InMemoryRepository exists and all repo tests use it | unit | `uv run python -m pytest tests/test_repository.py tests/test_service.py -x -q` | Yes (will be migrated) |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/ -x -q`
- **Per wave merge:** `uv run python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. Tests will be migrated, not created from scratch.

## Impact Analysis

### Files to modify
| File | Change |
|------|--------|
| `repository.py` | DELETE (replaced by `repository/` package) |
| `repository/__init__.py` | NEW: package exports |
| `repository/protocol.py` | NEW: Repository protocol |
| `repository/bridge.py` | NEW: BridgeRepository (logic from old `repository.py`) |
| `repository/in_memory.py` | NEW: InMemoryRepository |
| `bridge/mtime.py` | NEW: MtimeSource + FileMtimeSource + ConstantMtimeSource (moved) |
| `bridge/__init__.py` | UPDATE: add mtime exports |
| `service.py` | UPDATE: type hint `OmniFocusRepository` -> `Repository` |
| `server.py` | UPDATE: imports, wiring (use `BridgeRepository`, import mtime from bridge) |
| `tests/conftest.py` | UPDATE: add `make_snapshot()` helper returning `DatabaseSnapshot` |
| `tests/test_repository.py` | UPDATE: split into bridge-repo tests + in-memory-repo tests; update imports |
| `tests/test_service.py` | UPDATE: use `InMemoryRepository` instead of `InMemoryBridge + FakeMtimeSource + OmniFocusRepository` |
| `tests/test_server.py` | UPDATE: imports for new paths |
| `docs/architecture.md` | NEW: architecture overview document |

### Files NOT changing
- `bridge/adapter.py`, `bridge/errors.py`, `bridge/factory.py`, `bridge/in_memory.py`, `bridge/protocol.py`, `bridge/real.py`, `bridge/simulator.py`
- `models/*` (all models unchanged)
- `tests/test_adapter.py`, `tests/test_bridge.py`, `tests/test_ipc_engine.py`, `tests/test_models.py`, `tests/test_simulator_bridge.py`, `tests/test_simulator_integration.py`, `tests/test_smoke.py`

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `repository.py`, `service.py`, `server.py`, `bridge/protocol.py`, all test files
- CONTEXT.md: locked decisions from discussion phase
- Python `typing.Protocol` -- stdlib, well-established pattern already used in this project

### Secondary (MEDIUM confidence)
- None needed -- this is a pure refactoring of existing code with no new external dependencies

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new deps, all stdlib + existing project libraries
- Architecture: HIGH -- decisions locked in CONTEXT.md, code patterns clear from existing codebase
- Pitfalls: HIGH -- identified through direct codebase inspection of all import sites and test wiring

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (stable -- pure internal refactoring, no external dependencies to go stale)
