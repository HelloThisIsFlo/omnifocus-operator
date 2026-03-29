# Architecture Patterns

**Domain:** SQL-filtered list/count tools for existing MCP server
**Researched:** 2026-03-29
**Confidence:** HIGH -- existing codebase is well-understood, patterns are extensions of established conventions

## Recommended Architecture

Extend the existing three-layer architecture (MCP Server -> Service -> Repository) with a new **filter resolution** concern in the service layer and **parameterized SQL query building** in the repository layer. No new layers. No new protocols. The Repository protocol gains new methods; service gains a new pipeline; server gains new tool registrations.

### High-Level Data Flow

```
Agent calls list_tasks(flagged=true, search="review", limit=10)
  |
  v
server.py: validate params, construct ListTasksQuery model
  |
  v
service/service.py: _ListTasksPipeline.execute(query)
  - resolve filter values (tag names -> IDs, project name -> project ID match)
  - default exclusions (completed/dropped out unless explicitly requested)
  |
  v
repository protocol: list_tasks(query) -> ListResult[Task]
  |
  +-- HybridRepository (SQL path):
  |     query_builder.py: Query -> (sql_string, params_tuple)
  |     Execute parameterized SQL, map rows -> Task models
  |     Return ListResult(items=[Task, ...], total_count=N)
  |
  +-- BridgeRepository (in-memory fallback):
        get_all() -> AllEntities
        filter.py: apply filters in-memory against snapshot
        Return ListResult(items=[Task, ...], total_count=N)
```

### count_tasks / count_projects

Same pipeline, same query model, different return type. Two implementation strategies, pick one:

- **Recommended: shared code path.** `list_tasks` and `count_tasks` call the same service pipeline. The pipeline returns `ListResult` which always includes `total_count`. `count_tasks` tool returns just the count. `list_tasks` tool returns the items. This guarantees count/list parity (spec requirement: `count_tasks() == len(list_tasks())` for same filters).
- **Alternative: SQL COUNT(*).** HybridRepository could run `SELECT COUNT(*)` instead of `SELECT *` for count operations. ~50% faster on large result sets. But introduces a second code path that could diverge. Not worth the risk for a ~2,400-task database.

Decision: **shared code path.** Performance is irrelevant at this scale. Correctness guarantee is valuable.

## Component Boundaries

### New Components

| Component | Location | Responsibility | Why New |
|-----------|----------|----------------|---------|
| `ListTasksQuery` | `contracts/use_cases/list_tasks.py` | Validated filter parameters for task listing | New use case, follows existing pattern |
| `ListProjectsQuery` | `contracts/use_cases/list_projects.py` | Validated filter parameters for project listing | New use case |
| `ListResult[T]` | `contracts/use_cases/list_common.py` | Generic result container with items + total_count | Shared by list/count, both entity types |
| `_ListTasksPipeline` | `service/service.py` | Filter resolution, default exclusions, delegation | Method Object pattern (established convention) |
| `_ListProjectsPipeline` | `service/service.py` | Same for projects | Method Object pattern |
| `query_builder.py` | `repository/query_builder.py` | Query model -> (SQL string, params tuple) | SQL generation needs dedicated module, not inline in hybrid.py |
| `filter.py` | `repository/filter.py` | In-memory filtering for BridgeRepository fallback | Separate from BridgeRepository to keep it testable independently |

### Modified Components

| Component | Change |
|-----------|--------|
| `contracts/protocols.py` | Add `list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives` to Repository and Service protocols |
| `repository/hybrid.py` | Add list methods using query_builder for SQL generation |
| `repository/bridge.py` | Add list methods using filter.py for in-memory filtering |
| `service/service.py` | Add list/count pipelines, new read delegation methods |
| `server.py` | Register 7 new tools (list_tasks, list_projects, list_tags, list_folders, list_perspectives, count_tasks, count_projects) |
| `service/resolve.py` | Add tag-name-to-ID resolution helper for filter use (or reuse existing `resolve_tags`) |
| `models/__init__.py` | Export any new result models |

### Unchanged Components

| Component | Why Unchanged |
|-----------|---------------|
| `bridge/` | Bridge protocol stays dumb -- no filter commands needed. BridgeRepository loads full snapshot via existing `get_all`, then filters in Python |
| `contracts/base.py` | No patch semantics needed for read-only queries |
| `service/domain.py` | No business rules for reads beyond filter resolution |
| `service/payload.py` | No write payloads |
| `models/task.py`, `models/project.py`, etc. | Entity models unchanged -- same Task/Project/Tag/Folder/Perspective returned |
| `middleware.py` | Logging middleware applies automatically to new tools |
| `rrule/` | No repetition rule involvement |

## Data Flow: SQL Path (HybridRepository)

### list_tasks with filters

```
1. server.py receives filter params from agent
2. Pydantic validates into ListTasksQuery (extra="forbid")
3. Service pipeline resolves:
   - tag names -> tag IDs via get_all() snapshot
   - project name -> partial match (resolved at SQL level, not pre-resolved)
   - applies default exclusions (completed/dropped out)
4. Repository.list_tasks(query) called
5. query_builder.build_task_query(query) generates:
   - Base SQL: same _TASKS_SQL (Task LEFT JOIN ProjectInfo WHERE pi.task IS NULL)
   - Dynamic WHERE clauses appended with AND logic
   - Parameterized values collected into params tuple
   - LIMIT/OFFSET appended if present
6. Fresh read-only connection, execute parameterized query
7. Map rows -> Task dicts (reuse existing _map_task_row)
8. Validate with Task.model_validate() per row
9. Return ListResult(items=[Task, ...], total_count=len_before_pagination)
```

### SQL Query Building Strategy

**Parameterized WHERE clause composition.** Not an ORM. Not string interpolation. Build a list of `(clause_str, params)` tuples, join with AND:

```python
# Conceptual -- not final API
clauses: list[str] = []
params: list[Any] = []

if query.flagged is not None:
    clauses.append("t.flagged = ?")
    params.append(1 if query.flagged else 0)

if query.inbox is not None:
    clauses.append("t.inInbox = ?")
    params.append(1 if query.inbox else 0)

if query.search is not None:
    clauses.append("(t.name LIKE ? OR t.plainTextNote LIKE ?)")
    pattern = f"%{query.search}%"
    params.extend([pattern, pattern])

if query.tags:  # list of tag IDs (already resolved)
    placeholders = ",".join("?" * len(query.tags))
    clauses.append(f"t.persistentIdentifier IN (SELECT task FROM TaskToTag WHERE tag IN ({placeholders}))")
    params.extend(query.tags)
```

Key SQL column mappings for Task filters:

| Filter param | SQLite column | Notes |
|-------------|--------------|-------|
| `inbox` | `t.inInbox` | Boolean (0/1) |
| `flagged` | `t.flagged` | Boolean (0/1) |
| `project` | Join through `containingProjectInfo` -> `ProjectInfo.task` -> `Task.name` | Case-insensitive LIKE on project name |
| `tags` | `TaskToTag` join table | Subquery: task IN (SELECT task FROM TaskToTag WHERE tag IN (?)) |
| `has_children` | `t.childrenCount` | `> 0` for true, `= 0` for false |
| `estimated_minutes_max` | `t.estimatedMinutes` | `<= ?` |
| `availability` | `t.blocked`, `t.dateCompleted`, `t.dateHidden` | Computed from columns, same logic as `_map_task_availability` |
| `search` | `t.name`, `t.plainTextNote` | `LIKE %?%` (case-insensitive by SQLite default) |
| Default exclusion | `t.dateCompleted IS NULL AND t.dateHidden IS NULL` | Always applied unless overridden by date filters (v1.3.1) |

Key SQL column mappings for Project filters:

| Filter param | SQLite column | Notes |
|-------------|--------------|-------|
| `status` | `pi.effectiveStatus`, `t.dateCompleted`, `t.dateHidden` | Derived: active/on_hold/done/dropped from status + dates |
| `folder` | `pi.folder` -> `Folder.name` | Join for case-insensitive partial match |
| `review_due_within` | `pi.nextReviewDate` | Compare parsed duration against current timestamp |
| `flagged` | `t.flagged` | Boolean (0/1) |

### Total Count for Pagination

For `list_tasks(limit=5, offset=10)`, the response needs `total_count` (so agents can compute pages). Two approaches:

- **Run the query twice:** Once `SELECT COUNT(*)` without LIMIT/OFFSET, once `SELECT *` with. Two queries, correct count.
- **Recommended: use Python len().** Run the full query without LIMIT/OFFSET, get all matching rows, count them, then slice. With ~2,400 tasks max, the full query takes <6ms. The slice is free. Simpler, one query, one code path.

Decision: **Python len() + slice.** Performance is not a concern at this dataset size. When it becomes a concern (v1.6 production hardening), switch to dual-query. The ListResult abstraction hides this implementation detail.

Alternative for future: window function `COUNT(*) OVER ()` in the SELECT to get total in a single query. SQLite supports this. But complicates row mapping with an extra column. Not worth it now.

## Data Flow: In-Memory Path (BridgeRepository)

### list_tasks with filters (bridge fallback)

```
1. Same server.py / service pipeline as SQL path
2. Repository.list_tasks(query) called
3. BridgeRepository calls self.get_all() -> AllEntities (cached snapshot)
4. filter.py applies filters in-memory:
   - Iterate through all_entities.tasks
   - Apply each filter as a Python predicate
   - AND logic: task must pass all filters
5. Count total matches, then apply limit/offset slice
6. Return ListResult(items=[Task, ...], total_count=total_matches)
```

### In-Memory Filter Implementation

Separate module `repository/filter.py` with pure functions:

```python
def filter_tasks(tasks: list[Task], query: ListTasksQuery) -> list[Task]:
    """Apply all filters, return matching tasks."""
    results = tasks
    for predicate in _build_task_predicates(query):
        results = [t for t in results if predicate(t)]
    return results
```

Each filter maps to a predicate function operating on the Task Pydantic model (not raw dicts). This uses the already-parsed domain models, so field names match Python conventions (snake_case).

**Tag resolution difference:** SQL path joins on tag IDs. In-memory path can match on tag names directly from `task.tags[].name`. The service layer should pre-resolve tag names to IDs for the SQL path, but the in-memory filter can accept either. Keep resolution in the service layer (not repository) for consistency.

**Project name matching difference:** SQL path does `LIKE` on project name via join. In-memory path uses `task.parent.name` (already resolved in the snapshot). The service layer does NOT pre-resolve the project name -- both paths handle it internally.

## Patterns to Follow

### Pattern 1: Query Model as Contract

**What:** Define `ListTasksQuery` as a Pydantic model in `contracts/use_cases/`. All filter parameters are typed, validated, with defaults. This is the contract between server -> service -> repository.

**Why:** Same pattern as `AddTaskCommand` / `EditTaskCommand`. The query model travels through all three layers unchanged. Server constructs it from agent params, service reads it for resolution, repository reads it for query building.

**Naming:** `ListTasksQuery` (not `ListTasksCommand` -- reads don't command, they query). Not `ListTasksFilter` either -- the model includes pagination (`limit`/`offset`) which isn't a filter. `Query` covers both.

```python
# contracts/use_cases/list_tasks.py
class ListTasksQuery(CommandModel):
    """Validated filter + pagination parameters for task listing."""
    inbox: bool | None = None
    flagged: bool | None = None
    project: str | None = None           # partial name match
    tags: list[str] | None = None        # tag names or IDs (pre-resolved to IDs by service)
    has_children: bool | None = None
    estimated_minutes_max: int | None = None
    availability: Literal["available", "blocked"] | None = None
    search: str | None = None            # substring search
    limit: int | None = None
    offset: int | None = None
```

Open question: Should `ListTasksQuery` inherit `CommandModel` (which has `extra="forbid"`)? Yes -- agent sends these params, unknown params should error. But there's a naming tension: it's not a "command." The `extra="forbid"` behavior is what matters, not the base class name. Pragmatic answer: inherit `CommandModel` for the behavior, accept the naming imperfection. Or introduce a `QueryModel` alias. Lean toward `CommandModel` -- don't proliferate base classes for a naming quibble.

### Pattern 2: ListResult as Generic Container

**What:** A single result type wrapping items + total_count, generic over entity type.

```python
# contracts/use_cases/list_common.py
from typing import Generic, TypeVar
T = TypeVar("T")

class ListResult(OmniFocusBaseModel, Generic[T]):
    items: list[T]
    total_count: int
```

**Why:** Both list_tasks and list_projects need the same structure. count_tasks just reads `total_count`. Agents get pagination info without a separate call.

**MCP tool return:** The server layer returns `ListResult[Task]` directly -- FastMCP handles Pydantic serialization. The agent sees `{"items": [...], "totalCount": N}` (camelCase via alias).

For count tools, the server returns just the integer (or a thin wrapper). Not a `ListResult` -- no point returning an empty items list.

### Pattern 3: Query Builder as Pure Function Module

**What:** `repository/query_builder.py` contains pure functions: query model in, (sql_string, params) out. No database access, no connection management, no state.

**Why:** Pure functions are trivially testable. You can assert on SQL strings and params without touching SQLite. The HybridRepository calls `build_task_query(query)`, gets a tuple, and executes it. Separation of concerns: query_builder knows SQL syntax, HybridRepository knows connection lifecycle.

```python
# repository/query_builder.py
def build_task_query(query: ListTasksQuery) -> tuple[str, tuple[Any, ...]]:
    """Build parameterized SQL for task listing."""
    ...
    return sql, tuple(params)

def build_project_query(query: ListProjectsQuery) -> tuple[str, tuple[Any, ...]]:
    """Build parameterized SQL for project listing."""
    ...
    return sql, tuple(params)
```

### Pattern 4: Method Object Pipeline for List Operations

**What:** `_ListTasksPipeline` and `_ListProjectsPipeline` in `service/service.py`, same pattern as `_AddTaskPipeline` and `_EditTaskPipeline`.

```python
class _ListTasksPipeline(_Pipeline):
    async def execute(self, query: ListTasksQuery) -> ListResult[Task]:
        self._resolve_tag_names()        # tag names -> IDs
        self._apply_default_exclusions() # exclude completed/dropped
        self._validate_pagination()      # offset requires limit
        return await self._repository.list_tasks(self._query)
```

**Why:** Consistent with established convention. Even though list pipelines are simpler than write pipelines (no payload building, no bridge interaction), the pattern keeps orchestration self-documenting.

### Pattern 5: Simpler Tools Without Pipelines (Tags, Folders, Perspectives)

**What:** `list_tags`, `list_folders`, `list_perspectives` are simple enough to NOT need pipelines. Single filter (status), no pagination, no cross-entity resolution. Direct pass-through from service to repository.

**Why:** Method Object pattern is for multi-step orchestration. A single-filter list is a one-liner. Don't over-pattern it.

```python
# In OperatorService
async def list_tags(self, status: str | None = None) -> list[Tag]:
    return await self._repository.list_tags(status)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Inline SQL in HybridRepository

**What:** Building SQL strings directly in `HybridRepository.list_tasks()` with if/elif chains.

**Why bad:** HybridRepository is already 700+ lines. Adding filter SQL inline would push it past 1000 lines. SQL generation is independently testable -- mixing it with connection management and row mapping hurts testability.

**Instead:** Extract to `query_builder.py`. Pure functions in, SQL out. Test the builder with unit tests on SQL strings.

### Anti-Pattern 2: Duplicating Filter Logic Between SQL and In-Memory

**What:** Writing filter predicates independently in query_builder.py and filter.py, hoping they stay in sync.

**Why bad:** The spec requires "bridge fallback produces identical results to SQL path for the same filters." Two independent implementations will drift.

**Instead:**
- Shared query model (`ListTasksQuery`) ensures both paths receive identical input
- Shared test suite: parametrize tests over both repository implementations
- Test the equivalence directly: for each filter combo, run against both paths, compare results
- Accept that the implementations differ (SQL vs Python) but the contracts are tested identically

### Anti-Pattern 3: Pre-Resolving Everything in Service

**What:** Resolving project names to IDs, tag names to IDs, and all other lookups in the service layer before passing to repository.

**Why bad:** Some resolutions are naturally SQL operations (project name partial match is a JOIN + LIKE). Pre-resolving would require loading the full snapshot just to resolve a project name, then passing the ID to SQL -- defeating the purpose of SQL filtering.

**Instead:**
- **Tag names -> IDs:** Resolve in service (needs full tag list for case-insensitive matching). Pass resolved IDs in the query.
- **Project name matching:** Pass raw string to repository. SQL does LIKE, in-memory does Python string matching. Both handle it internally.
- **Availability mapping:** Pass the enum string. SQL maps to column predicates, in-memory checks the model field.

### Anti-Pattern 4: Returning Raw Dicts from List Methods

**What:** Having list methods return `list[dict]` instead of `list[Task]`.

**Why bad:** Breaks type safety, loses Pydantic validation, inconsistent with get_task/get_project which return models.

**Instead:** Always return Pydantic models. The row mapping functions already exist (`_map_task_row`, `_map_project_row`). Reuse them.

## Protocol Extensions

### Repository Protocol (new methods)

```python
class Repository(Protocol):
    # Existing reads
    async def get_all(self) -> AllEntities: ...
    async def get_task(self, task_id: str) -> Task | None: ...
    async def get_project(self, project_id: str) -> Project | None: ...
    async def get_tag(self, tag_id: str) -> Tag | None: ...

    # New list methods
    async def list_tasks(self, query: ListTasksQuery) -> ListResult[Task]: ...
    async def list_projects(self, query: ListProjectsQuery) -> ListResult[Project]: ...
    async def list_tags(self, status: str | None = None) -> list[Tag]: ...
    async def list_folders(self, status: str | None = None) -> list[Folder]: ...
    async def list_perspectives(self) -> list[Perspective]: ...

    # Existing writes
    async def add_task(self, payload: AddTaskRepoPayload) -> AddTaskRepoResult: ...
    async def edit_task(self, payload: EditTaskRepoPayload) -> EditTaskRepoResult: ...
```

### Service Protocol (new methods)

```python
class Service(Protocol):
    # Existing
    async def get_all_data(self) -> AllEntities: ...
    async def get_task(self, task_id: str) -> Task: ...
    async def get_project(self, project_id: str) -> Project: ...
    async def get_tag(self, tag_id: str) -> Tag: ...
    async def add_task(self, command: AddTaskCommand) -> AddTaskResult: ...
    async def edit_task(self, command: EditTaskCommand) -> EditTaskResult: ...

    # New list/count methods
    async def list_tasks(self, query: ListTasksQuery) -> ListResult[Task]: ...
    async def list_projects(self, query: ListProjectsQuery) -> ListResult[Project]: ...
    async def list_tags(self, status: str | None = None) -> list[Tag]: ...
    async def list_folders(self, status: str | None = None) -> list[Folder]: ...
    async def list_perspectives(self) -> list[Perspective]: ...
    async def count_tasks(self, query: ListTasksQuery) -> int: ...
    async def count_projects(self, query: ListProjectsQuery) -> int: ...
```

## Suggested Build Order

Dependencies flow downward. Each step is independently testable.

### Phase 1: Query Models + Query Builder (foundation)

1. **Query models** -- `ListTasksQuery`, `ListProjectsQuery` in `contracts/use_cases/`
2. **ListResult** container in `contracts/use_cases/list_common.py`
3. **query_builder.py** -- pure functions, unit tested against SQL strings
4. **Protocol extensions** -- add new methods to Repository and Service protocols

Rationale: Everything else depends on these. Query builder is pure functions, testable without SQLite.

### Phase 2: Repository Layer (data access)

5. **HybridRepository.list_tasks** -- uses query_builder, reuses _map_task_row
6. **filter.py** -- in-memory filter predicates for BridgeRepository fallback
7. **BridgeRepository.list_tasks** -- uses filter.py on get_all() snapshot
8. **list_projects for both repos** -- same pattern
9. **list_tags / list_folders / list_perspectives** for both repos -- simple, no query builder needed

Rationale: Repository is the core data path. Test with InMemoryBridge (via BridgeRepository) and test SQLite queries with a test database fixture.

### Phase 3: Service Layer (orchestration)

10. **_ListTasksPipeline** -- tag resolution, default exclusions, pagination validation, delegation
11. **_ListProjectsPipeline** -- status shorthand expansion, folder resolution, delegation
12. **Simple list pass-throughs** (tags, folders, perspectives)
13. **count_tasks / count_projects** -- thin wrappers calling list pipeline, returning total_count

Rationale: Service depends on repository. Pipelines are thin for reads.

### Phase 4: Server Layer (tool registration)

14. **Register all 7 new tools** in server.py
15. **Tool descriptions** -- detailed enough for LLM discoverability (spec has proposed descriptions)
16. **Validation error formatting** for filter params

Rationale: Server is the outermost layer. Registration wires everything together.

### Phase 5: Integration + Cross-Path Testing

17. **Equivalence tests:** Same filters, both repository implementations, compare results
18. **Edge cases:** Empty results, no filters (return all), limit=0, offset without limit errors
19. **Performance sanity check:** Filtered query measurably faster than get_all

## Key Design Decisions for Implementation

### Where Does Filter Logic Live?

| Concern | Layer | Rationale |
|---------|-------|-----------|
| Input validation (unknown fields, type errors) | Server (Pydantic) | `extra="forbid"` on query model |
| Default exclusions (completed/dropped) | Service | Domain knowledge: "agents don't want completed tasks by default" |
| Tag name -> ID resolution | Service | Cross-entity lookup, same as write path |
| Pagination validation (offset requires limit) | Service | Business rule, not schema validation |
| SQL WHERE generation | Repository (query_builder) | Implementation detail of SQL path |
| In-memory predicate application | Repository (filter.py) | Implementation detail of bridge fallback |
| Row -> model mapping | Repository | Already exists, reuse |

### Tag Filter Resolution Flow

The `tags` filter accepts tag names OR IDs (same convention as `add_tasks`). Resolution happens in the service pipeline:

```
Agent sends: tags=["Work", "Planning"]
Service: resolve_tags(["Work", "Planning"]) -> ["tagId1", "tagId2"]
Query model updated with resolved IDs
Repository: SQL uses IDs directly (no name matching at SQL level)
```

This reuses `Resolver.resolve_tags()` which already handles case-insensitive name matching with ID fallback.

### Project Name Filter: Partial Match at Repository Level

The `project` filter is a case-insensitive partial match on project name. This stays in the repository:

- **SQL path:** JOIN through `containingProjectInfo` -> `ProjectInfo.task` -> `Task.name`, LIKE `%query%`
- **In-memory path:** Check `task.parent.name` with Python `in` operator (case-insensitive)

Not pre-resolved in service because partial matching is a repository concern.

## Scalability Considerations

| Concern | At ~2,400 tasks (current) | At ~10K tasks | At ~100K tasks |
|---------|--------------------------|---------------|----------------|
| Full snapshot for list | ~46ms | ~200ms | Unacceptable |
| SQL filtered query | <6ms | <20ms | <100ms (with indexes) |
| In-memory filter after get_all | ~46ms + filter | ~200ms + filter | Unacceptable |
| Count via len() | Free | Free | Switch to COUNT(*) |
| Tag resolution via get_all | ~46ms | ~200ms | Needs dedicated tag query |

**Current scale (2,400 tasks):** No performance concern. All approaches work.

**Future scale (10K+):** SQL path stays fast. In-memory fallback degrades. Bridge fallback is already documented as "slower" -- acceptable degradation.

**Indexes:** OmniFocus owns the SQLite schema. We cannot add indexes. The existing schema likely has indexes on `persistentIdentifier` (PK) and `blocked`, `flagged`, `inInbox`, `dateCompleted`, `dateHidden` (used by OmniFocus internally). We should `EXPLAIN QUERY PLAN` on our generated queries during development to verify.

## Sources

- Existing codebase: `repository/hybrid.py`, `repository/bridge.py`, `contracts/protocols.py`, `service/service.py`, `server.py`
- Milestone spec: `.research/updated-spec/MILESTONE-v1.3.md`
- SQLite research: `.research/deep-dives/direct-database-access/RESULTS.md`
- Architecture docs: `docs/architecture.md`
