# Architecture Research

**Domain:** SQLite read path integration into existing OmniFocus MCP server
**Researched:** 2026-03-07
**Confidence:** HIGH (all integration points verified against existing codebase)

## Current Architecture (v1.0)

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Server Layer                       │
│  ┌─────────────┐                                         │
│  │  list_all    │ ─── ctx.service ──┐                    │
│  └─────────────┘                    │                    │
├─────────────────────────────────────┼────────────────────┤
│                    Service Layer    ▼                     │
│  ┌───────────────────┐  ┌──────────────────────┐         │
│  │  OperatorService  │  │  ErrorOperatorService │         │
│  └────────┬──────────┘  └──────────────────────┘         │
│           │                                              │
├───────────┼──────────────────────────────────────────────┤
│           ▼          Repository Layer                     │
│  ┌─────────────────────────────────────────┐             │
│  │  OmniFocusRepository                    │             │
│  │  - MtimeSource (freshness)              │             │
│  │  - Bridge (data fetch)                  │             │
│  │  - _snapshot cache + _lock              │             │
│  └────────┬────────────────────────────────┘             │
│           │                                              │
├───────────┼──────────────────────────────────────────────┤
│           ▼          Bridge Layer                         │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────┐      │
│  │ InMemory   │  │  Simulator   │  │    Real      │      │
│  └────────────┘  └──────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────┘
```

**Key characteristic:** Repository owns both data fetching (Bridge) and freshness detection (MtimeSource). These are separate concerns passed via constructor DI.

## v1.1 Target Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Server Layer                       │
│  ┌─────────────┐                                         │
│  │  list_all    │ ─── ctx.service ──┐                    │
│  └─────────────┘                    │                    │
├─────────────────────────────────────┼────────────────────┤
│                    Service Layer    ▼                     │
│  ┌───────────────────┐  ┌──────────────────────┐         │
│  │  OperatorService  │  │  ErrorOperatorService │         │
│  └────────┬──────────┘  └──────────────────────┘         │
│           │                                              │
├───────────┼──────────────────────────────────────────────┤
│           ▼          Repository Layer                     │
│  ┌─────────────────────────────────────────┐             │
│  │  OmniFocusRepository                    │             │
│  │  - DataSource (replaces Bridge+Mtime)   │             │
│  │  - _snapshot cache + _lock              │             │
│  └────────┬────────────────────────────────┘             │
│           │                                              │
├───────────┼──────────────────────────────────────────────┤
│           ▼       Data Source Layer (NEW)                 │
│  ┌─────────────────────┐  ┌─────────────────────┐        │
│  │  SQLiteDataSource   │  │  BridgeDataSource   │        │
│  │  (primary)          │  │  (fallback/legacy)  │        │
│  │  - SQL queries      │  │  - Bridge protocol  │        │
│  │  - WAL freshness    │  │  - .ofocus mtime    │        │
│  └─────────────────────┘  └─────────────────────┘        │
│                                                          │
│  ┌─────────────────────┐                                 │
│  │  InMemoryDataSource │ (testing)                       │
│  └─────────────────────┘                                 │
└─────────────────────────────────────────────────────────┘
```

## What Changes, What Stays

### UNCHANGED

| Component | Why |
|-----------|-----|
| `server.py` tool handlers | `list_all` still calls `service.get_all_data()` -- same interface |
| `OperatorService` | Still delegates to `repository.get_snapshot()` |
| `ErrorOperatorService` | Error-serving pattern reused for SQLite-not-found |
| `DatabaseSnapshot` | Same aggregation model (lists of entities) |
| `Perspective` model | No status fields, unchanged per research |
| `OmniFocusBaseModel` | ConfigDict with camelCase aliases stays |
| `ReviewInterval`, `TagRef`, `RepetitionRule` | Common models unaffected |
| Bridge implementations | Stay for fallback and writes (future) |

### MODIFIED

| Component | What changes | Why |
|-----------|-------------|-----|
| `OmniFocusEntity` | Remove `active`, `effective_active` | Subsumed by status axes / entity-specific status |
| `ActionableEntity` | Remove `completed` (bool), `completed_by_children`, `sequential`, `should_use_floating_time_zone`. Add `urgency: Urgency`, `availability: Availability` | Two-axis status model |
| `Task` | Remove `status: TaskStatus`. Keep `in_inbox`, `project`, `parent` | Status replaced by shared axes |
| `Project` | Remove `status`, `task_status`, `contains_singleton_actions`. Keep review + relationship fields | Status replaced by shared axes |
| `Tag` | Remove `allows_next_action` | Redundant with `status` |
| `enums.py` | Delete `TaskStatus`, `ProjectStatus`. Add `Urgency`, `Availability` | Two-axis model |
| `models/__init__.py` | Update exports, `_ns` dict, remove deleted types | Reflect enum/field changes |
| `OmniFocusRepository` | Replace `Bridge + MtimeSource` constructor params with single `DataSource` | Unified abstraction |
| `server.py` lifespan | Route `OMNIFOCUS_BRIDGE` env var to correct DataSource | SQLite vs bridge selection |
| `bridge/factory.py` | Becomes data source factory or is replaced | New routing logic |
| `InMemoryBridge` data | Update sample data to match new model shape (no old fields) | Test fixture alignment |

### NEW Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `DataSource` protocol | `get_mtime_ns() -> int` + `get_raw_snapshot() -> DatabaseSnapshot` | `src/omnifocus_operator/datasource/protocol.py` |
| `SQLiteDataSource` | SQL queries, row-to-model mapping, WAL mtime | `src/omnifocus_operator/datasource/sqlite.py` |
| `BridgeDataSource` | Wraps Bridge + MtimeSource, maps old enums to two-axis | `src/omnifocus_operator/datasource/bridge.py` |
| `InMemoryDataSource` | Testing: returns fixture data, constant mtime | `src/omnifocus_operator/datasource/in_memory.py` |
| `Urgency` enum | `overdue / due_soon / none` | `src/omnifocus_operator/models/enums.py` |
| `Availability` enum | `available / blocked / completed / dropped` | `src/omnifocus_operator/models/enums.py` |

## Architectural Patterns

### Pattern 1: DataSource Protocol (replaces Bridge + MtimeSource)

**What:** Single protocol combining data fetching and freshness detection. Currently these are split across `Bridge` (fetch) and `MtimeSource` (freshness). SQLite doesn't fit this split -- freshness comes from WAL mtime, fetch is a SQL query, not a bridge command.

**Design:**
```python
class DataSource(Protocol):
    async def get_mtime_ns(self) -> int: ...
    async def get_raw_snapshot(self) -> DatabaseSnapshot: ...
```

**Why this shape:** Repository keeps its existing caching + lock logic unchanged. DataSource replaces the two injected dependencies with one. Repository calls `get_mtime_ns()` for freshness, `get_raw_snapshot()` for data -- same pattern, fewer moving parts.

**Trade-offs:**
- Pro: Repository logic barely changes (rename `bridge.send_command("snapshot")` to `data_source.get_raw_snapshot()`)
- Pro: Each DataSource implementation is fully self-contained
- Con: DataSource must produce fully validated Pydantic models (not raw dicts). This is intentional -- validation at the boundary.

### Pattern 2: SQLite Row-to-Model Mapping

**What:** Convert raw SQLite rows into Pydantic models with two-axis status.

**Key concerns:**
- SQLite columns use OmniFocus internal names (`dateAdded`, `dateModified`, `blocked`, `overdue`, `dueSoon`, `blockedByFutureStartDate`)
- Status axes derived from boolean columns: `blocked` -> Availability, `overdue`/`dueSoon` -> Urgency
- Must handle timezone conversion (SQLite stores timestamps differently than bridge JSON)

**Approach:** `sqlite3.Row` factory for dict-like access, explicit mapper functions per entity type. Co-locate SQL queries with their mapper code in `SQLiteDataSource`.

### Pattern 3: Fallback Mode via Env Var

**What:** `OMNIFOCUS_BRIDGE=omnijs` switches from SQLiteDataSource to BridgeDataSource. Default changes from `"real"` to `"sqlite"`.

**Lifespan routing:**
```python
bridge_type = os.environ.get("OMNIFOCUS_BRIDGE", "sqlite")  # NEW default
match bridge_type:
    case "sqlite":     -> SQLiteDataSource(db_path=...)
    case "omnijs":     -> BridgeDataSource(bridge=RealBridge(...), mtime=FileMtimeSource(...))
    case "inmemory":   -> InMemoryDataSource(...)
    case "simulator":  -> BridgeDataSource(bridge=SimulatorBridge(...), mtime=ConstantMtimeSource())
```

**Status quality in fallback:** BridgeDataSource maps old single-winner enums to two-axis with reduced Availability (no `blocked`). Mapping logic lives in BridgeDataSource, not in models.

### Pattern 4: WAL-Based Freshness

**What:** SQLiteDataSource checks `st_mtime_ns` of the `-wal` file for cache invalidation, replacing `.ofocus` bundle mtime.

**Why WAL:** In WAL mode, readers read directly from the WAL file. WAL write = data queryable. Documented SQLite guarantee.

**Location:** Same dir as `.db` file with `-wal` suffix:
```
~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/
  com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel/OmniFocusDatabase.db-wal
```

## Data Flow

### v1.1 Read (SQLite, default)

```
list_all tool
  -> OperatorService.get_all_data()
  -> OmniFocusRepository.get_snapshot()
      -> SQLiteDataSource.get_mtime_ns()     # stat() on WAL file
      -> if changed: SQLiteDataSource.get_raw_snapshot()
          -> sqlite3.connect(db_path, mode="ro")
          -> SELECT from Task, ProjectInfo, Context, Folder tables
          -> Row mapper: boolean columns -> Urgency + Availability
          -> DatabaseSnapshot(tasks=..., projects=..., ...)
      -> cached snapshot returned
```

### v1.1 Read (OmniJS fallback)

```
list_all tool
  -> OperatorService.get_all_data()
  -> OmniFocusRepository.get_snapshot()
      -> BridgeDataSource.get_mtime_ns()     # stat() on .ofocus bundle
      -> if changed: BridgeDataSource.get_raw_snapshot()
          -> Bridge.send_command("snapshot")
          -> Map TaskStatus/ProjectStatus -> Urgency + Availability
          -> Availability.blocked never returned (can't distinguish)
          -> DatabaseSnapshot assembled
      -> cached snapshot returned
```

## Integration Points

### Boundaries

| Boundary | Communication | v1.1 Change |
|----------|---------------|-------------|
| Server -> Service | Direct method call | None |
| Service -> Repository | Direct method call | None |
| Repository -> DataSource | Protocol methods | **NEW** -- replaces Bridge + MtimeSource |
| DataSource -> SQLite | `sqlite3` stdlib | **NEW** |
| DataSource -> Bridge | Existing Bridge protocol | Wrapped in BridgeDataSource |

### External Dependencies

| Dependency | v1.0 | v1.1 |
|-----------|------|------|
| OmniFocus process | Required for all reads | **Not needed for reads** (SQLite cache on disk) |
| SQLite database | Not used | **Primary read source** |
| `.ofocus` bundle | Freshness signal | Only for OmniJS fallback |
| WAL file | Not used | **Freshness signal for SQLite mode** |
| `sqlite3` stdlib | Not used | **New dependency** (stdlib, no pip install) |

## Anti-Patterns

### Anti-Pattern 1: SQL in Repository

**What people do:** Put SQL queries directly in OmniFocusRepository.
**Why it's wrong:** Repository's job is caching + freshness. Data source details leak upward.
**Do this instead:** Repository calls `data_source.get_raw_snapshot()`. All SQL lives behind DataSource protocol.

### Anti-Pattern 2: Dual Model Hierarchies

**What people do:** Keep old model fields for bridge compatibility, create new fields for SQLite, maintain both.
**Why it's wrong:** Divergence, maintenance burden, confusion about which shape is canonical.
**Do this instead:** One set of Pydantic models (new two-axis). Both DataSource implementations produce the same types. BridgeDataSource handles old-to-new mapping internally.

### Anti-Pattern 3: Automatic Silent Fallback

**What people do:** Try SQLite, catch error, silently fall back to bridge.
**Why it's wrong:** Hides broken config. User unknowingly loses `blocked` status.
**Do this instead:** Error-serving mode when SQLite not found. Manual `OMNIFOCUS_BRIDGE=omnijs` switch. Visible, intentional.

### Anti-Pattern 4: Shared Connection Pool

**What people do:** Keep a persistent SQLite connection open for reuse.
**Why it's wrong:** OmniFocus owns this database. Holding connections could interfere with its WAL checkpointing.
**Do this instead:** Open read-only connection per snapshot, query, close. At 46ms per full snapshot, connection setup overhead is negligible.

## Suggested Build Order

Based on dependency analysis:

**Phase 1: Pydantic model overhaul** -- everything depends on the new shape
- New enums (`Urgency`, `Availability`)
- Remove fields from `OmniFocusEntity`, `ActionableEntity`, `Task`, `Project`, `Tag`
- Add `urgency` + `availability` to `ActionableEntity`
- Update `models/__init__.py` exports and `_ns` dict
- Update all test fixtures and assertions

**Phase 2: DataSource protocol + InMemoryDataSource** -- testing infrastructure
- Define `DataSource` protocol
- Create `InMemoryDataSource` (replaces InMemoryBridge for tests)
- Update `OmniFocusRepository` to accept DataSource instead of Bridge + MtimeSource
- All existing repository/service/server tests pass with InMemoryDataSource

**Phase 3: SQLiteDataSource** -- the core feature
- SQLite reader with row-to-model mapping
- WAL-based freshness detection (`get_mtime_ns()`)
- Error handling (file not found, permission denied, corrupt DB)
- Unit tests with temporary SQLite databases

**Phase 4: BridgeDataSource** -- fallback wrapper
- Wraps existing Bridge + MtimeSource
- Maps old single-winner enums to two-axis (reduced Availability)
- Preserves SimulatorBridge path for IPC testing

**Phase 5: Server lifespan wiring** -- tie it together
- Route `OMNIFOCUS_BRIDGE` env var (default: `"sqlite"`)
- Error-serving when SQLite not found
- UAT validation

**Ordering rationale:**
- Models first: every component imports them
- DataSource protocol before implementations: interface before concrete
- InMemoryDataSource before SQLite: need test infra to validate integration
- SQLite before Bridge fallback: primary path first
- Server wiring last: integrates all pieces, needs everything below

## Performance Comparison

| Metric | v1.0 (Bridge) | v1.1 (SQLite) |
|--------|---------------|---------------|
| Full snapshot | 2-5s (IPC round-trip) | ~46ms |
| Filtered query | N/A (filter in-memory after full load) | <6ms |
| OmniFocus required | Yes | No |
| Startup | Lazy (first call triggers) | Lazy (unchanged) |
| Cache invalidation | `.ofocus` bundle mtime | WAL file mtime |

## Sources

- Existing codebase: `src/omnifocus_operator/` (v1.0 shipped, verified by direct reading)
- `.research/deep-dives/direct-database-access/RESULTS.md` (SQLite research, HIGH confidence)
- `.research/deep-dives/direct-database-access/RESULTS_pydantic-model.md` (model design, HIGH confidence)
- `.planning/PROJECT.md` (project context and requirements)
- SQLite WAL documentation: documented guarantee that WAL write = data queryable

---
*Architecture research for: OmniFocus Operator v1.1 SQLite integration*
*Researched: 2026-03-07*
