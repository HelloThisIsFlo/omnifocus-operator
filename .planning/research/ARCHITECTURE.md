# Architecture Patterns

**Domain:** Write pipeline and get-by-ID integration for OmniFocus MCP server (v1.2)
**Researched:** 2026-03-07
**Confidence:** HIGH (based on existing codebase analysis + BRIDGE-SPEC empirical data)

## Current Architecture (v1.1)

```
MCP Tool (server.py)
  -> OperatorService (service.py)
    -> Repository Protocol (repository/protocol.py)
      -> HybridRepository (SQLite read, no bridge)
      -> BridgeRepository (OmniJS read via bridge + mtime cache)
      -> InMemoryRepository (tests, static snapshot)
```

- **Read-only today.** Repository protocol: `async get_all() -> AllEntities`
- **Two read paths:** SQLite (46ms, default) and OmniJS bridge (fallback)
- **Bridge layer exists but is decoupled from HybridRepository:** `Bridge.send_command(operation, params)` supports arbitrary operations, but HybridRepository has zero bridge dependency
- **Snapshot invalidation already prototyped:** HybridRepository has `_stale` flag + WAL mtime polling via `TEMPORARY_simulate_write()`
- **Request file IPC already supports payloads:** `_write_request()` writes `{"operation": "...", "params": {...}}` -- write payloads just go in `params`

## Recommended Architecture for v1.2

### Key Principle: Asymmetric Read/Write Paths

Reads and writes take fundamentally different paths. Do NOT unify them.

```
READ PATH (existing, unchanged):
  MCP tool -> Service -> Repository.get_all() -> SQLite or Bridge snapshot

WRITE PATH (new):
  MCP tool -> Service (validate against snapshot) -> Repository.add/edit_tasks()
    -> Bridge.send_command() -> mark snapshot stale

GET-BY-ID PATH (new):
  MCP tool -> Service.get_task/project/tag(id) -> Repository.get_all() -> filter in Python
```

### Why get-by-ID Uses get_all()

The snapshot is cached in memory. Filtering one entity from an in-memory list is microseconds. Adding per-entity SQL queries or bridge commands adds a second code path with zero user-visible benefit at 2,400 tasks.

The milestone spec mentions `get_task`/`get_project`/`get_tag` bridge commands -- these are unnecessary. Both HybridRepository (SQLite cache) and BridgeRepository (in-memory snapshot) already have all entities loaded. Only add bridge-level get-by-ID if a future use case requires guaranteed real-time freshness (not currently needed).

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **MCP tools** (server.py) | Parse args, call service, format response | Service |
| **OperatorService** (service.py) | Validate inputs against snapshot, delegate writes | Repository |
| **Repository protocol** | Abstract interface for reads + writes | (implementations below) |
| **HybridRepository** | SQLite reads, delegates writes to bridge, invalidates via WAL mtime | Bridge (writes only), SQLite (reads) |
| **BridgeRepository** | Snapshot cache reads, delegates writes to bridge, invalidates cache | Bridge |
| **InMemoryRepository** | Test double: reads + writes against in-memory snapshot | None |
| **Bridge protocol** | `send_command(operation, params)` -- IPC to OmniFocus | RealBridge (file IPC) |
| **bridge.js** | Execute OmniJS commands inside OmniFocus runtime | OmniFocus Omni Automation |

### New vs Modified vs Unchanged Components

**New:**
- Service methods: `get_task()`, `get_project()`, `get_tag()`, `add_tasks()`, `edit_tasks()`
- Pydantic request/response models: `AddTaskRequest`, `EditTaskRequest`, `TaskChanges`, `WriteResult`
- Bridge.js operation handlers: `add_task`, `edit_task`
- MCP tool registrations: 5 new tools in server.py

**Modified:**
- `Repository` protocol -- add `add_tasks()`, `edit_tasks()` method signatures
- `HybridRepository` -- add bridge dependency (optional constructor param), write methods, replace `TEMPORARY_simulate_write` with `_mark_stale()`
- `BridgeRepository` -- add write methods (thin delegation to existing bridge)
- `InMemoryRepository` -- add write methods (mutate in-memory snapshot)
- `OperatorService` -- add validation + delegation methods
- `bridge.js dispatch()` -- add new operation cases
- `repository/factory.py` -- inject bridge into HybridRepository

**Unchanged:**
- Bridge protocol (`send_command` already supports arbitrary operations)
- RealBridge IPC mechanics (request/response files, URL scheme trigger)
- SQLite read path (queries, row mapping, timestamp parsing)
- Adapter layer (only transforms bridge read snapshots)
- AllEntities / entity Pydantic models (read shapes unchanged)

## Data Flow

### add_tasks Flow

```
1. MCP tool: add_tasks([{name: "Buy milk", project: "abc123", tags: ["errands"]}])
2. Service validates against current snapshot (via get_all()):
   - name is non-empty
   - project ID "abc123" exists in snapshot.projects
   - tag name "errands" exists in snapshot.tags -> resolves to tag ID
   - project and parent_task_id not both set
3. Service calls Repository.add_tasks(validated_requests)
4. Repository delegates to Bridge.send_command("add_task", {name, projectId, tagIds, ...})
5. Bridge writes request file, triggers OmniFocus URL scheme
6. bridge.js reads request, creates task via OmniJS, writes response file
7. Bridge returns {success: true, data: {id: "xyz789", name: "Buy milk"}}
8. Repository calls _mark_stale() (captures WAL mtime, sets _stale=True)
9. Service returns WriteResult to MCP tool
10. Next read: _stale flag triggers WAL poll -> fresh SQLite read
```

### edit_tasks Flow

```
1. MCP tool: edit_tasks([{id: "xyz789", changes: {due_date: "2026-03-10", tags: null}}])
2. Service validates:
   - task ID "xyz789" exists in snapshot
   - patch semantics: omit=no change, null=clear, value=set
   - tag mode exclusivity (tags vs add_tags/remove_tags)
3. Service calls Repository.edit_tasks(validated_edits)
4. Repository translates field names (snake_case -> camelCase for bridge)
5. Bridge.send_command("edit_task", {id, changes: {dueDate, tags}})
6. bridge.js applies changes via hasOwnProperty checks on each field
7. Returns success/error
8. Repository marks stale
```

### get_task Flow

```
1. MCP tool: get_task(id="xyz789")
2. Service calls repository.get_all() (cached, sub-ms if warm)
3. Service filters: next(t for t in snapshot.tasks if t.id == id)
4. Returns full Task object (same shape as list_all results)
5. If not found: raises clear error with the ID
```

## Patterns to Follow

### Pattern 1: HybridRepository Gains a Bridge (Optional Dependency)

HybridRepository currently has NO bridge dependency. For writes, it needs one.

```python
class HybridRepository:
    def __init__(self, db_path: Path | None = None, bridge: Bridge | None = None) -> None:
        self._db_path = ...
        self._bridge = bridge  # None = read-only mode

    async def add_tasks(self, tasks: list[AddTaskRequest]) -> list[WriteResult]:
        if self._bridge is None:
            raise RuntimeError("Write operations require a bridge (OmniFocus must be running)")
        result = await self._bridge.send_command("add_task", ...)
        self._mark_stale()
        return [WriteResult(...)]
```

**Why optional:** Tests may want read-only HybridRepository (SQLite testing without bridge). Clear error when writes attempted without bridge.

### Pattern 2: Stale-After-Write (Extend Existing)

Replace `TEMPORARY_simulate_write()` with `_mark_stale()`:

```python
def _mark_stale(self) -> None:
    """Capture current WAL mtime and set stale flag."""
    wal_path = self._db_path + "-wal"
    try:
        self._last_wal_mtime_ns = os.stat(wal_path).st_mtime_ns
    except FileNotFoundError:
        self._last_wal_mtime_ns = os.stat(self._db_path).st_mtime_ns
    self._stale = True
```

Existing `_wait_for_fresh_data()` (50ms poll, 2s timeout) handles the rest. OmniFocus syncs writes to SQLite within ~100ms.

For BridgeRepository: `self._cached = None` forces full refresh on next read.

For InMemoryRepository: mutate the snapshot directly -- no invalidation needed.

### Pattern 3: Validation in Service, Execution in Repository

Service validates against the current snapshot before delegating writes:

| Validation | Where | Why |
|-----------|-------|-----|
| name non-empty | Service | Business rule |
| project ID exists | Service | Requires snapshot lookup |
| tag names exist + resolve to IDs | Service | Requires snapshot lookup |
| project vs parent_task_id mutual exclusivity | Service | Business rule |
| task ID exists (for edits) | Service | Requires snapshot lookup |
| tag mode exclusivity (tags vs add_tags/remove_tags) | Service | Business rule |

Repository receives pre-validated payloads and executes blindly. Bridge is dumb (BRIDGE-SPEC principle: "dumb bridge, smart Python").

### Pattern 4: Per-Item Results for Batch Operations

```python
@dataclass
class WriteResult:
    success: bool
    id: str | None = None
    name: str | None = None
    error: str | None = None
```

**Best-effort processing:** Continue on failure. OmniFocus has no transactions -- already-applied changes persist even if later items fail. Return per-item results so the agent knows exactly what succeeded.

### Pattern 5: Tag Name-to-ID Resolution in Service

The spec says `add_tasks` accepts tag names (not IDs). Resolve in Python:

```python
# Service layer
tag_map = {t.name: t.id for t in snapshot.tags}
for tag_name in request.tags:
    if tag_name not in tag_map:
        raise ValueError(f"Unknown tag: {tag_name}")
    tag_ids.append(tag_map[tag_name])
# Send tag_ids to bridge
```

Bridge uses `Tag.byIdentifier(id)` -- no OmniJS iteration needed. Python already has the full tag list cached (microsecond lookup vs ~65ms OmniJS iteration).

### Pattern 6: Field Name Translation at Repository Boundary

Python uses snake_case, bridge expects camelCase. Translation at the repository layer:

```python
_FIELD_MAP = {
    "due_date": "dueDate",
    "defer_date": "deferDate",
    "planned_date": "plannedDate",
    "estimated_minutes": "estimatedMinutes",
    "parent_task_id": "parentTaskId",
}
```

Same dict-based approach used throughout the codebase (adapter.py pattern).

## Anti-Patterns to Avoid

### Anti-Pattern 1: SQLite Write Path
**What:** Writing directly to OmniFocus's SQLite cache
**Why bad:** OmniFocus owns that database. Corrupts state, breaks sync, may crash OmniFocus.
**Instead:** All writes through OmniJS bridge -> OmniFocus processes them -> SQLite cache updates automatically.

### Anti-Pattern 2: Separate Write Repository
**What:** Creating a `WriteRepository` separate from read repositories
**Why bad:** Writes need to invalidate the read cache. Separate objects require coordination (events, callbacks).
**Instead:** Add write methods to existing repository implementations. Same object manages cache + invalidation.

### Anti-Pattern 3: Bridge-Side Validation
**What:** Validating field values, checking ID existence in bridge.js
**Why bad:** OmniJS is ~1ms/task. Iterating 2,800 tasks to check an ID takes 2.8 seconds of frozen UI.
**Instead:** Validate everything in Python. Bridge receives pre-validated payloads.

### Anti-Pattern 4: Per-Entity Bridge Commands for get-by-ID
**What:** Adding `get_task`/`get_project`/`get_tag` as OmniJS bridge operations
**Why bad:** Each bridge round-trip is ~1-3 seconds. Filtering from cached snapshot is sub-ms.
**Instead:** Implement get-by-ID as a filter on `get_all()` result.

### Anti-Pattern 5: Eager Snapshot Refresh After Write
**What:** Force full snapshot refresh immediately after every write
**Why bad:** Adds 46ms+ latency to every write. The returned `{id, name}` is sufficient confirmation.
**Instead:** Mark stale (lazy invalidation). Next read triggers refresh. Already how the codebase works.

## Repository Protocol Changes

### Current
```python
class Repository(Protocol):
    async def get_all(self) -> AllEntities: ...
```

### Proposed (v1.2)
```python
class Repository(Protocol):
    async def get_all(self) -> AllEntities: ...
    async def add_tasks(self, tasks: list[AddTaskRequest]) -> list[WriteResult]: ...
    async def edit_tasks(self, edits: list[EditTaskRequest]) -> list[WriteResult]: ...
```

Service calls writes polymorphically -- same code path regardless of repository type. InMemoryRepository mutates snapshot directly for integration tests.

## Bridge Script Changes

### New Operations in dispatch()

| Operation | Request Params | Response Data |
|-----------|---------------|---------------|
| `add_task` | `{name, projectId?, parentTaskId?, tagIds?, dueDate?, deferDate?, plannedDate?, flagged?, estimatedMinutes?, note?}` | `{id, name}` |
| `edit_task` | `{id, changes: {name?, note?, dueDate?, deferDate?, plannedDate?, flagged?, estimatedMinutes?, projectId?, parentTaskId?, tagIds?, addTagIds?, removeTagIds?}}` | `{id, name}` |

### Bridge JS Implementation Notes

- **Task creation:** `new Task(name, project)` or `new Task(name)` for inbox. `Task.byIdentifier()` and `Project.byIdentifier()` for lookups.
- **Parent task:** After creation, look up parent via `Task.byIdentifier(parentTaskId)`, set `task.parent = parentTask`
- **Tag assignment:** `task.addTag(Tag.byIdentifier(tagId))` per tag. Service resolves names to IDs.
- **Property writes:** Direct assignment: `task.dueDate = new Date(isoString)`, `task.flagged = true`, `task.dueDate = null` (clears)
- **Patch semantics:** `if (changes.hasOwnProperty("dueDate")) { task.dueDate = changes.dueDate === null ? null : new Date(changes.dueDate); }`
- **Tag modes:**
  - `tagIds` present: `task.clearTags()` then `task.addTag()` each
  - `addTagIds` present: `task.addTag()` each
  - `removeTagIds` present: `task.removeTag()` each
  - `removeTagIds` + `addTagIds`: remove first, then add (add wins on conflicts)
- **Task movement:** `task.containingProject` for project assignment (BRIDGE-SPEC says `assignedContainer` is always null -- verify `containingProject` setter works or use alternative)

### Open Bridge Questions (Resolve During Implementation)

- Does `task.containingProject = project` work for moving tasks? Or use `moveTasks()`?
- Does setting `task.parent = null` un-nest a task to project root?
- Does `task.containingProject = null` move to inbox?
- Does `markIncomplete()` on an already-incomplete task throw or no-op?

## Suggested Build Order

Ordered by dependency chain and risk:

### Phase 1: Get-by-ID Tools (warmup, zero new patterns)
- Add `get_task()`, `get_project()`, `get_tag()` to OperatorService
- Filter on `get_all()` result, raise not-found errors
- Register 3 MCP tools in server.py
- Test with InMemoryRepository
- **No** bridge changes, protocol changes, or new models
- **Risk:** Very low. Pure Python filtering.
- **Dependency:** None

### Phase 2: Write Pipeline Foundation (new pattern, highest risk)
- Define `AddTaskRequest`, `EditTaskRequest`, `TaskChanges`, `WriteResult` Pydantic models
- Add `add_tasks()`, `edit_tasks()` to Repository protocol
- Implement in InMemoryRepository first (mutate snapshot)
- Add optional bridge param to HybridRepository constructor
- Implement `_mark_stale()` replacing `TEMPORARY_simulate_write()`
- Update repository factory to inject bridge into HybridRepository
- **Risk:** Medium. New pattern but mechanically straightforward.
- **Dependency:** None (parallel with Phase 1)

### Phase 3: add_tasks End-to-End
- Add `add_task` handler to bridge.js
- Add service validation (name required, project exists, tag name->ID resolution)
- Implement `add_tasks()` in HybridRepository and BridgeRepository
- Register `add_tasks` MCP tool
- UAT: create task, verify via get_task with returned ID
- **Risk:** Medium. First real write through the full stack.
- **Dependency:** Phase 1 (get-by-ID for verification) + Phase 2 (models + protocol)

### Phase 4: edit_tasks -- Simple Fields
- Add `edit_task` handler to bridge.js with hasOwnProperty patch semantics
- Implement field edits: name, note, dates, flagged, estimated_minutes
- Implement tag modes: replace (tagIds), add (addTagIds), remove (removeTagIds)
- Implement task movement: project, parent_task_id
- Service validation: task exists, tag mode exclusivity, mutual exclusivity
- Register `edit_tasks` MCP tool
- UAT: edit various fields, verify via get_task
- **Risk:** Medium-high. Patch semantics + tag modes + movement = most complex phase.
- **Dependency:** Phase 3 (need tasks to edit, pipeline proven)

### Phase 5: edit_tasks -- Lifecycle Changes
- Research spike: OmniJS `markComplete()`, `drop()`, `markIncomplete()` behavior
- Determine interface: field edit (availability value) vs action-style
- Handle repeating task edge cases (complete instance vs series)
- Implement in bridge.js + wire through edit_tasks
- UAT: complete, drop, reactivate tasks
- **Risk:** Higher. Repeating tasks + drop permanence need careful investigation.
- **Dependency:** Phase 4 (edit pipeline established)

## Sources

- Existing codebase: `repository/protocol.py`, `repository/hybrid.py`, `repository/bridge.py`, `repository/in_memory.py`, `service.py`, `server.py`, `bridge/real.py`, `bridge/bridge.js`, `bridge/adapter.py`
- `.research/deep-dives/omnifocus-api-ground-truth/BRIDGE-SPEC.md` (Section 4: Write Operations)
- `.research/updated-spec/MILESTONE-v1.2.md`
- `.planning/PROJECT.md`
