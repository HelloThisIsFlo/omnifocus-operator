# Architecture Overview

## Layer Diagram

```
MCP Tool (list_all)
    |
OperatorService          -- orchestration, future caching policies
    |
Repository (protocol)    -- async get_snapshot() -> DatabaseSnapshot
    |
    +-- BridgeRepository    (production: Bridge + MtimeSource + adapter, with caching)
    +-- InMemoryRepository  (testing: returns pre-built snapshot)
    +-- SQLiteRepository    (Phase 12: direct DB read, ~46ms)
```

## Package Structure

```
omnifocus_operator/
    bridge/          -- OmniFocus communication (IPC, in-memory, simulator)
    repository/      -- Data access protocol + implementations
    models/          -- Pydantic models (snapshot, entities, enums)
    server.py        -- FastMCP wiring (concrete implementation selection)
    service.py       -- Service layer (depends on Repository protocol only)
```

## Why Repository, Not DataSource

- Repository implies querying/filtering -- future `get_tasks(filters)` (v1.2+)
- DataSource implies raw data access -- too thin an abstraction
- Repository is the richer contract for how consumers interact with data

## Why Flat Packages (bridge/ and repository/ as peers)

- Bridge is a general OmniFocus communication channel, not just data access
- Future milestones: perspective switching, UI actions, write operations -- all via Bridge directly
- `repository/` depends on `bridge/` (never reverse)
- Keeping them as siblings avoids false nesting (`repository/bridge/` would imply ownership)

## Dependency Direction

- `service.py` -> `Repository` protocol (never concrete implementations)
- `server.py` -> concrete `BridgeRepository` + `Bridge` + `MtimeSource` (wiring only)
- `repository/bridge.py` -> `bridge/` package (Bridge protocol, MtimeSource, adapter)
- `repository/in_memory.py` -> `models/` only (zero bridge dependency)

## Caching Strategy

- **BridgeRepository**: mtime-based cache invalidation (fallback mode)
  - Checks file mtime before each read; serves cached snapshot if unchanged
  - Concurrent reads coalesce into a single bridge dump
- **InMemoryRepository**: no caching (returns constructor snapshot as-is)
- **SQLiteRepository** (Phase 12): no caching (SQLite ~46ms is fast enough)
- **Primary read path** (Phase 12+): SQLite direct, no cache layer needed

## Deferred Decisions

- Whether writes go through Repository or Bridge directly (future milestone)
- SQLiteRepository naming may change based on Phase 12 implementation
- Multi-repository coordination in OperatorService (if needed)
