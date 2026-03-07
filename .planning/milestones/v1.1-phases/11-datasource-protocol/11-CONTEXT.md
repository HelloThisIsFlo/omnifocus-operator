# Phase 11: DataSource Protocol - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Abstract the read path behind a Repository protocol, refactor the existing concrete Repository into BridgeRepository, create InMemoryRepository for testing, and clean up the codebase. Despite the phase name ("DataSource Protocol"), the decision was made to use Repository as the protocol -- no separate DataSource concept.

</domain>

<decisions>
## Implementation Decisions

### Architecture: Repository as protocol
- Repository becomes a **protocol** (currently a concrete class with caching logic)
- Three implementations: `BridgeRepository`, `InMemoryRepository`, `SQLiteRepository` (Phase 12)
- No separate "DataSource" concept -- Repository IS the data access abstraction
- Service calls Repository directly: `Service -> Repository (protocol)`
- Each implementation owns both data access AND query strategy
- When filtering arrives (v1.2), `get_tasks(filters)` is added to the protocol. SQLiteRepository uses SQL WHERE, BridgeRepository loads all and filters in Python. Same interface, different strategies.

### Architecture: No caching in primary path
- SQLite reads are ~46ms -- caching is unnecessary for the primary (SQLite) path
- Caching logic moves INTO `BridgeRepository` only (bridge calls are slow, mtime-based caching justified)
- `MtimeSource` protocol and implementations (`FileMtimeSource`, `ConstantMtimeSource`) become internal to `BridgeRepository` / bridge package
- `InMemoryRepository` and future `SQLiteRepository` have no caching

### Package structure: Bridge and Repository as sibling packages
- `bridge/` and `repository/` are **peer top-level packages** (flat, not nested)
- Bridge is a general-purpose OmniFocus communication layer, not just a data source
- Bridge will be used directly for non-data operations in future milestones (perspective switching, UI actions, other OmniFocus interactions)
- Whether writes go through Repository or Bridge directly: **deferred decision** for future milestone
- Bridge adapter (`adapt_snapshot`) stays in `bridge/adapter.py` -- BridgeRepository imports it

### Package structure after refactor
```
src/omnifocus_operator/
  bridge/              # general OmniFocus communication (sibling, not nested)
    adapter.py         # adapt_snapshot() -- bridge-specific transform
    errors.py
    factory.py         # create_bridge()
    in_memory.py       # InMemoryBridge (used by BridgeRepository)
    protocol.py        # Bridge protocol
    real.py            # RealBridge
    simulator.py       # SimulatorBridge
  repository/          # NEW package (was single file repository.py)
    __init__.py        # exports Repository protocol + factory
    protocol.py        # Repository protocol
    bridge.py          # BridgeRepository (wraps Bridge + adapter + mtime cache)
    in_memory.py       # InMemoryRepository (test data, no bridge)
    # sqlite.py        # Phase 12
  models/
  server.py            # creates repository via factory, passes to service
  service.py           # calls repository methods
  simulator/
```

### Protocol method naming
- Repository protocol method naming should align with the MCP tool naming convention (`list_all`, `list_tasks`, `list_projects`)
- For now, the protocol exposes a method for full snapshot retrieval
- Claude's discretion on exact method name, but should feel consistent with service layer naming

### Migration scope: Full cleanup
- Full refactor: introduce Repository protocol, create implementations, reorganize files
- Move MtimeSource into bridge package (it's a bridge-internal concern now)
- Clean up imports across the codebase
- Update all test fixtures and wiring
- Create `docs/` folder at project root with architecture overview document

### Test migration: Clean break
- All repository-level tests use `InMemoryRepository` -- no `InMemoryBridge + ConstantMtimeSource` in repo tests
- Bridge tests (InMemoryBridge, SimulatorBridge, adapter, IPC) stay in their own test files
- No coverage loss -- existing bridge/simulator test coverage preserved, just restructured
- Zero backward compatibility -- clean break, no deprecation

### Claude's Discretion
- Repository protocol exact method signature (name, return type)
- InMemoryRepository constructor API (raw dict vs pre-built entities)
- Concurrency strategy per implementation (BridgeRepository keeps lock, others decide)
- Server wiring / factory pattern for selecting repository implementation
- File reorganization details during full cleanup
- Architecture doc structure and content depth

</decisions>

<specifics>
## Specific Ideas

- "OmniFocus is extremely slow -- keep the bridge as dumb as possible. Any computation, put it in Python" (carried from Phase 10)
- Bridge is NOT just for reads/writes -- it's a general OmniFocus communication channel (perspective switching, UI actions in future milestones). This is why it stays as a sibling package, not nested under repository.
- Repository as protocol was chosen because "DataSource" doesn't imply filtering/querying naturally, and when v1.2 filtering arrives, the interface should feel like a Repository (`repo.get_tasks(status=done)`)
- The decision to drop caching from the primary path was driven by: "SQLite makes caching unnecessary. Caching is useful for OmniJS Bridge, but since this is a fallback mode that will almost never be used, don't keep caching logic for this niche use case." Caching survived only inside BridgeRepository.
- Create architecture overview in `docs/` -- capture the deep discussion about why Repository (not DataSource), why flat (not nested), and deferred decisions about writes and naming

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Bridge` protocol (`bridge/protocol.py`): stays as-is, used by BridgeRepository internally
- `InMemoryBridge` (`bridge/in_memory.py`): continues to exist for bridge-level tests
- `adapt_snapshot()` (`bridge/adapter.py`): stays in bridge package, used by BridgeRepository
- `MtimeSource` protocol + `FileMtimeSource` + `ConstantMtimeSource` (currently in `repository.py`): move to bridge package, used by BridgeRepository only

### Established Patterns
- Fail-fast on unknown enum values at bridge boundary -- maintain
- `StrEnum` for all enums -- continue
- `OmniFocusBaseModel` with ConfigDict (camelCase aliases) -- unaffected
- `TYPE_CHECKING` + `model_rebuild` pattern -- continue using
- SimulatorBridge inherits RealBridge -- unaffected (BridgeRepository uses either)
- Lazy cache hydration pattern -- replaced by no-caching-in-primary-path

### Integration Points
- `repository.py` (single file) -> `repository/` (package with protocol + implementations)
- `server.py`: currently creates Bridge + MtimeSource + Repository separately; refactor to create Repository directly (factory or env var routing)
- `service.py`: currently takes `OmniFocusRepository`; update to take `Repository` protocol
- `tests/test_repository.py`: migrate from `InMemoryBridge + ConstantMtimeSource` to `InMemoryRepository`
- `tests/test_service.py` and `tests/test_server.py`: update wiring to new Repository creation

</code_context>

<deferred>
## Deferred Ideas

- **Writes through Repository vs Bridge directly** -- Decide when write operations are scoped (future milestone). Repository could be the single data gateway, or writes could go through Bridge directly for non-CRUD operations (perspective switching).
- **SQLiteRepository naming** -- Called SQLiteRepository for now. May rename to HybridRepository or similar when it also handles writes via Bridge internally. Revisit in Phase 12.
- **Bridge nesting under Repository** -- If all Bridge usage eventually goes through Repository, nesting could be reconsidered. Currently kept flat because Bridge has direct-use cases beyond data access.

</deferred>

---

*Phase: 11-datasource-protocol*
*Context gathered: 2026-03-07*
