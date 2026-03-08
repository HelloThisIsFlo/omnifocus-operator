# Architecture Overview

## Layer Diagram

```
MCP Tool (list_all)
    |
OperatorService          -- orchestration, future caching policies
    |
Repository (protocol)    -- async get_all() -> AllEntities
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

## Method Naming Convention

- `get_all()` -> `AllEntities`: structured container with all entity types (tasks, projects, folders, tags)
- `list_*(filters)` -> flat list of one entity type (e.g., `list_tasks(status=...)`)
- `get_*` = heterogeneous structured return; `list_*` = homogeneous filtered collection
- `AllEntities` (not `DatabaseSnapshot`) -- no caching/snapshot semantics at the protocol level

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

## Write Pipeline (v1.2)

- Writes go through Repository protocol -> Bridge (service validates, bridge executes)
- **HybridRepository**: reads from SQLite, writes via Bridge, marks stale after writes
- Service layer validates before bridge execution: parent exists, tags exist, name non-empty
- Tag resolution in service: case-insensitive name match, ID fallback, ambiguity error with IDs
- Parent resolution in service: try `get_project` first, then `get_task` -- **project takes precedence** (intentional, deterministic)

## Patch Semantics (edit_tasks)

- Three-way field distinction: omit = no change, null = clear, value = set
- Pydantic sentinel pattern (UNSET) distinguishes "not provided" from "explicitly null"
- Clearable fields: dates, note, estimated_minutes. Value-only: name, flagged

## Task Movement (moveTo)

"Key IS the position" design -- `moveTo` object has exactly one key:

```
{"moveTo": {"ending": "proj-123"}}       -- last child of container
{"moveTo": {"beginning": "proj-123"}}    -- first child of container
{"moveTo": {"after": "task-sibling"}}    -- after this sibling (parent inferred)
{"moveTo": {"before": "task-sibling"}}   -- before this sibling (parent inferred)
{"moveTo": {"beginning": null}}          -- move to inbox
```

- One key = one position + one reference. Invalid combos are structurally impossible.
- Maps directly to OmniJS position API: `container.beginning`, `container.ending`, `task.before`, `task.after`
- Full cycle validation via SQLite parent chain walk before bridge call

## Educational Warnings

- Write results include optional `warnings` array for no-ops
- Hints teach agents patch semantics: "Tag 'X' was not on this task -- omit remove_tags to skip"
- Design principle: LLMs learn in-context from tool responses, so warnings serve as runtime documentation

## Deferred Decisions

- Multi-repository coordination in OperatorService (if needed)
