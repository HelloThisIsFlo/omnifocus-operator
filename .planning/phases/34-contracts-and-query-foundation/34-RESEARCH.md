# Phase 34: Contracts and Query Foundation - Research

**Researched:** 2026-03-29
**Domain:** Pydantic query contracts, parameterized SQL generation, protocol extensions
**Confidence:** HIGH

## Summary

Phase 34 creates the typed query contract layer (models, protocols, SQL generation) that all downstream phases (35-38) build on. No repository implementations, no service logic, no MCP tool registration -- just the independently testable contracts and pure functions.

The codebase already has well-established patterns for all the pieces needed: `CommandModel` for write-side contracts, `OmniFocusBaseModel` for outbound models, protocol-based boundaries, and parameterized SQL in hybrid.py. This phase introduces the read-side equivalents (`QueryModel`, `ListResult[T]`, query builder) following the same patterns.

**Primary recommendation:** Follow the existing contract/model patterns exactly. The architecture doc pre-documents everything. The riskiest piece is `ListResult[T]` as a Generic Pydantic model -- verified working with Pydantic 2.12.5 and FastMCP 3.1.1 output schema generation.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `ListResult[T]` has `items: list[T]`, `total: int`, `hasMore: bool`. Named `total` not `total_count`. No offset/limit echo. Uniform for all 5 list tools. Inherits `OmniFocusBaseModel`. Lives in `contracts/use_cases/list_entities.py`.
- **D-02:** Filter defaults live on the Pydantic model (contract concern). Shorthand expansion lives in the service (domain concern).
- **D-03:** Uniform `availability` list filter across all entities. No shorthands. Entity-specific enum values and defaults per table in CONTEXT.md.
- **D-04:** Extend existing `Repository` and `Service` protocols with `list_*` method signatures. No separate query protocols.
- **D-05:** Standalone `repository/query_builder.py` with pure functions producing parameterized SQL.
- **D-06:** Agent-friendly names: `project` (partial match), `tags` (names), `availability` (enum strings). Service resolves names to IDs.
- **D-07:** Server tool functions take flat params. Protocol/service methods take query objects. Server wraps flat params into query model.
- **D-08:** All query models + ListResult in `contracts/use_cases/list_entities.py`.
- **D-09:** `list_perspectives()` takes no query model.
- **D-10:** `limit=0` is valid (count-only request).
- **D-11:** `has_children` filter dropped from `list_tasks`.
- **D-12:** Final server-level signatures defined in CONTEXT.md.

### Claude's Discretion

- Query builder return type (NamedTuple, tuple, dataclass)
- Internal organization of query_builder.py (function grouping, helper patterns)
- Exact `hasMore` computation formula (likely `offset + len(items) < total`)

### Deferred Ideas (OUT OF SCOPE)

- `has_children` filter (TASK-05) -- dropped from v1.3
- Status shorthands (remaining, available, all) -- replaced by concrete availability values
- Standalone count tools (count_tasks, count_projects) -- `limit=0` covers it

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | SQL queries use parameterized values (no SQL injection) | Query builder pure functions return `(sql_string, params_tuple)` with `?` placeholders. Existing hybrid.py already uses this pattern for single-entity reads. |
| INFRA-04 | list_tasks and list_projects responses include total_count reflecting total matches ignoring limit/offset | `ListResult[T].total` field (D-01b renamed from total_count). Query builder generates both `SELECT ... LIMIT/OFFSET` and `SELECT COUNT(*)` variants. |

</phase_requirements>

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| Pydantic | 2.12.5 | Query models, ListResult[T], validation | Already installed. Generic model support verified. |
| FastMCP | 3.1.1 | MCP server, output schema generation | Already installed. Generic return type verified. |
| Python stdlib sqlite3 | 3.12+ | SQL string construction (no execution in this phase) | Already used in hybrid.py |

### No New Dependencies

Phase 34 requires zero new packages. Everything builds on existing Pydantic + stdlib.

## Architecture Patterns

### File Structure (new files only)

```
src/omnifocus_operator/
    contracts/
        base.py              -- ADD: StrictModel, QueryModel (refactor CommandModel inheritance)
        protocols.py         -- MODIFY: add list_* method signatures
        use_cases/
            list_entities.py -- NEW: ListTasksQuery, ListProjectsQuery, ListTagsQuery,
                                     ListFoldersQuery, ListResult[T]
    repository/
        query_builder.py     -- NEW: Pure functions producing parameterized SQL
```

### Pattern 1: StrictModel Refactoring

**What:** Introduce `StrictModel` as intermediate base between `OmniFocusBaseModel` and `CommandModel`. Create `QueryModel` sibling.

**Current state:** `CommandModel(OmniFocusBaseModel)` with `extra="forbid"` directly on `CommandModel`.

**Target state (from architecture.md):**
```python
class StrictModel(OmniFocusBaseModel):
    """Base for all agent-facing contract models. Rejects unknown fields."""
    model_config = ConfigDict(extra="forbid")

class CommandModel(StrictModel):
    """Write-side contracts."""
    def changed_fields(self) -> dict[str, Any]:
        return {name: value for name, value in self.__dict__.items() if is_set(value)}

class QueryModel(StrictModel):
    """Read-side contracts: query filters and pagination."""
    pass
```

**Key concern:** `CommandModel` currently has `extra="forbid"` in its own `model_config`. Moving it to `StrictModel` is a refactor that must not break existing tests. The `changed_fields` method stays on `CommandModel` (write-side concern, not needed for queries).

### Pattern 2: Generic ListResult[T]

**What:** Generic Pydantic model for all list responses.

**Verified behavior (Pydantic 2.12.5 + FastMCP 3.1.1):**
- `ListResult[Task]` generates correct JSON Schema with inlined `Task` properties
- `alias_generator=to_camel` produces `hasMore` from `has_more`
- FastMCP `output_schema` correctly resolves generic return types
- `model_dump(by_alias=True)` serializes correctly

```python
from typing import Generic, TypeVar
T = TypeVar("T")

class ListResult(OmniFocusBaseModel, Generic[T]):
    items: list[T]
    total: int
    has_more: bool
```

**Confidence:** HIGH -- verified with actual project dependencies.

### Pattern 3: Query Models with Defaults

**What:** Query models carry filter defaults as Pydantic field defaults.

```python
class ListTasksQuery(QueryModel):
    in_inbox: bool | None = None
    flagged: bool | None = None
    project: str | None = None
    tags: list[str] | None = None
    estimated_minutes_max: int | None = None
    availability: list[str] | None = None  # default applied in __init__ or validator
    search: str | None = None
    limit: int | None = None
    offset: int | None = None
```

**Default handling (D-02a):** The `availability` field defaults to `["available", "blocked"]` via `Field(default_factory=...)` or a `model_validator`. All other filter fields default to `None` (no filter applied).

**Important:** `extra="forbid"` (inherited from `QueryModel` -> `StrictModel`) means unknown fields raise `ValidationError` -- agents get an error for typos like `flagg: true`.

### Pattern 4: Query Builder as Pure Functions

**What:** Stateless functions that take a query model and return parameterized SQL.

```python
# Input: query model instance
# Output: (sql_string, params_tuple)

def build_list_tasks_sql(query: ListTasksQuery) -> tuple[str, tuple[Any, ...]]:
    """Build parameterized SQL for task listing."""
    ...

def build_list_projects_sql(query: ListProjectsQuery) -> tuple[str, tuple[Any, ...]]:
    """Build parameterized SQL for project listing."""
    ...
```

**Key SQLite column mappings (from hybrid.py):**

| Query field | SQLite table | SQLite column(s) | Notes |
|-------------|-------------|-------------------|-------|
| `in_inbox` | Task | `inInbox` | Boolean (0/1) |
| `flagged` | Task | `flagged` | Boolean (0/1) |
| `project` | Task | `containingProjectInfo` → ProjectInfo → Task.name | Requires JOIN for partial name match |
| `tags` | TaskToTag | `task`, `tag` | JOIN table, OR logic with `IN (?)` |
| `estimated_minutes_max` | Task | `estimatedMinutes` | `<= ?` |
| `availability` (task) | Task | `blocked`, `dateCompleted`, `dateHidden` | Derived -- same logic as `_map_task_availability` |
| `availability` (project) | Task + ProjectInfo | `effectiveStatus`, `dateCompleted`, `dateHidden` | Derived -- same logic as `_map_project_availability` |
| `availability` (tag) | Context | `allowsNextAction`, `dateHidden` | Derived -- same logic as `_map_tag_availability` |
| `availability` (folder) | Folder | `dateHidden` | Derived -- same logic as `_map_folder_availability` |
| `search` | Task | `name`, `plainTextNote` | `LIKE '%?%'` (parameterized) |
| `folder` (project) | ProjectInfo | `folder` → Folder.name | Requires JOIN for partial name match |
| `review_due_within` | ProjectInfo | `nextReviewDate` | Date comparison |
| `limit` | -- | SQL `LIMIT ?` | |
| `offset` | -- | SQL `OFFSET ?` | |

**Availability as SQL WHERE clauses:** The tricky part. Availability is derived from multiple columns:

- Task `available`: `blocked = 0 AND dateCompleted IS NULL AND dateHidden IS NULL`
- Task `blocked`: `blocked != 0 AND dateCompleted IS NULL AND dateHidden IS NULL`
- Task `completed`: `dateCompleted IS NOT NULL AND dateHidden IS NULL`
- Task `dropped`: `dateHidden IS NOT NULL`

The query builder must translate `availability: ["available", "blocked"]` into a compound OR clause. This is a pure function concern -- no execution.

### Pattern 5: Protocol Extension

**What:** Add list method signatures to existing Repository and Service protocols.

```python
# In contracts/protocols.py

class Service(Protocol):
    # ... existing methods ...
    async def list_tasks(self, query: ListTasksQuery) -> ListResult[Task]: ...
    async def list_projects(self, query: ListProjectsQuery) -> ListResult[Project]: ...
    async def list_tags(self, query: ListTagsQuery) -> ListResult[Tag]: ...
    async def list_folders(self, query: ListFoldersQuery) -> ListResult[Folder]: ...
    async def list_perspectives(self) -> ListResult[Perspective]: ...

class Repository(Protocol):
    # ... existing methods ...
    async def list_tasks(self, query: ListTasksQuery) -> ListResult[Task]: ...
    async def list_projects(self, query: ListProjectsQuery) -> ListResult[Project]: ...
    async def list_tags(self, query: ListTagsQuery) -> ListResult[Tag]: ...
    async def list_folders(self, query: ListFoldersQuery) -> ListResult[Folder]: ...
    async def list_perspectives(self) -> ListResult[Perspective]: ...
```

**Impact:** Adding methods to a Protocol does NOT break existing implementations at runtime (Python protocols are structural). But `mypy --strict` will flag `OperatorService`, `HybridRepository`, and `BridgeRepository` as incomplete implementations. This is intentional (D-04b: "Structure Over Discipline" -- incomplete implementations are type errors).

**Mitigation for CI:** Downstream phases (35+) implement these methods. During Phase 34, either:
- Temporarily suppress mypy errors on the specific classes (comment-based ignore)
- Accept that mypy will flag warnings until downstream phases complete

### Anti-Patterns to Avoid

- **String interpolation in SQL:** Never `f"WHERE name = '{value}'"`. Always `WHERE name = ?` with params tuple.
- **Separate repo-boundary query model:** Query models are shared across layers (D-06b). No `ListTasksRepoQuery`.
- **Logic in query builder:** Query builder produces SQL strings, nothing else. No validation, no resolution, no execution.
- **`None` vs missing confusion:** `None` in a query field means "no filter" -- don't confuse with UNSET/Patch semantics (that's write-side).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| camelCase serialization | Manual alias dict | `OmniFocusBaseModel.alias_generator=to_camel` | Already handles all snake_case -> camelCase |
| Unknown field rejection | Manual field checking | `StrictModel` with `extra="forbid"` | Pydantic validates automatically |
| Generic result container | Per-entity result classes | `ListResult[T]` (Generic Pydantic model) | One model, five entity types |
| SQL parameterization | String formatting | `?` placeholders with tuple params | sqlite3 standard, prevents injection |

## Common Pitfalls

### Pitfall 1: `model_rebuild()` for New Models

**What goes wrong:** New models with `from __future__ import annotations` fail at schema generation time because type annotations are strings.
**Why it happens:** The project uses `from __future__ import annotations` throughout. Forward references need explicit resolution.
**How to avoid:** Add all new models to `contracts/__init__.py` namespace dict and call `model_rebuild()`. Follow the exact pattern of existing models (see `contracts/__init__.py` lines 44-88).
**Warning signs:** `PydanticUserError` about unresolvable forward references, or JSON schema with `$ref` pointing to missing definitions.

### Pitfall 2: Generic Model Schema in test_output_schema

**What goes wrong:** `ListResult[T]` serialization doesn't validate against the MCP outputSchema that FastMCP advertises.
**Why it happens:** Generic models produce slightly different JSON Schema than concrete models. FastMCP inlines `$defs` in output schemas.
**How to avoid:** After creating `ListResult[T]`, verify by running `uv run pytest tests/test_output_schema.py -x -q`. Note: this test currently only covers existing tools. New list tools will be registered in Phase 38, but the ListResult model structure should be validated now.
**Warning signs:** Schema validation errors, missing `hasMore` in output, `has_more` appearing instead of `hasMore`.

### Pitfall 3: Availability Filter SQL Complexity

**What goes wrong:** The availability filter requires translating enum values into multi-column compound WHERE clauses. Getting the logic wrong produces incorrect result sets.
**Why it happens:** Availability is a derived concept (computed from `blocked`, `dateCompleted`, `dateHidden`, `effectiveStatus`). Each value maps to a different column combination.
**How to avoid:** Extract the exact logic from `_map_task_availability()`, `_map_project_availability()`, `_map_tag_availability()`, `_map_folder_availability()` in hybrid.py. Write tests comparing the SQL WHERE clause against these existing mappers.
**Warning signs:** Tests that manually construct expected SQL strings rather than testing semantic correctness via a real SQLite database.

### Pitfall 4: Protocol Extension Breaking mypy

**What goes wrong:** Adding list methods to the Protocol makes every existing Repository/Service implementation incomplete according to mypy.
**Why it happens:** Protocol is structural -- adding required methods means existing classes no longer satisfy the protocol.
**How to avoid:** Acknowledge this is intentional (D-04b). Either add `# type: ignore[override]` comments temporarily or accept mypy failures until Phase 35+ implements the methods. Document the decision clearly.
**Warning signs:** CI failing on mypy checks.

### Pitfall 5: Tags Filter Requires Service Resolution

**What goes wrong:** Query builder receives tag names (e.g., `["Work", "Home"]`) but SQL needs tag IDs.
**Why it happens:** Per D-06b, the query model carries names at input and IDs after service resolution. The query builder operates after service resolution.
**How to avoid:** In query builder tests, use IDs directly (mimicking post-service state). Document clearly that the builder expects resolved values.
**Warning signs:** Query builder tests using tag names instead of IDs.

## Code Examples

### QueryModel Base Class (contracts/base.py)

```python
# Source: architecture.md contract base classes section
class StrictModel(OmniFocusBaseModel):
    """Base for all agent-facing contract models. Rejects unknown fields."""
    model_config = ConfigDict(extra="forbid")

class CommandModel(StrictModel):
    """Write-side contracts: commands, payloads, results, specs, actions."""
    def changed_fields(self) -> dict[str, Any]:
        """Return only fields explicitly set by the caller (UNSET values excluded)."""
        return {name: value for name, value in self.__dict__.items() if is_set(value)}

class QueryModel(StrictModel):
    """Read-side contracts: query filters and pagination."""
    pass
```

### ListResult[T] (contracts/use_cases/list_entities.py)

```python
# Source: CONTEXT.md D-01, architecture.md result container section
from typing import Generic, TypeVar
from omnifocus_operator.models.base import OmniFocusBaseModel

T = TypeVar("T")

class ListResult(OmniFocusBaseModel, Generic[T]):
    """Generic result container for all list operations.

    Uniform shape for all 5 list tools including non-paginated entities.
    For non-paginated: total = len(items), has_more = False.
    """
    items: list[T]
    total: int
    has_more: bool
```

### Query Model Example (contracts/use_cases/list_entities.py)

```python
# Source: CONTEXT.md D-03, D-06, D-12
class ListTasksQuery(QueryModel):
    """Validated filter + pagination for task listing."""
    in_inbox: bool | None = None
    flagged: bool | None = None
    project: str | None = None
    tags: list[str] | None = None
    estimated_minutes_max: int | None = None
    availability: list[str] = Field(default=["available", "blocked"])
    search: str | None = None
    limit: int | None = None
    offset: int | None = None
```

### Query Builder Return Type (recommended: NamedTuple)

```python
# Claude's discretion area -- NamedTuple recommended for clarity
from typing import Any, NamedTuple

class SqlQuery(NamedTuple):
    """Parameterized SQL query ready for sqlite3 execution."""
    sql: str
    params: tuple[Any, ...]

def build_list_tasks_sql(query: ListTasksQuery) -> SqlQuery:
    clauses: list[str] = []
    params: list[Any] = []

    # Base query (tasks only, no projects)
    base = "SELECT t.* FROM Task t LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task WHERE pi.task IS NULL"

    if query.in_inbox is not None:
        clauses.append("t.inInbox = ?")
        params.append(int(query.in_inbox))

    if query.flagged is not None:
        clauses.append("t.flagged = ?")
        params.append(int(query.flagged))

    # ... more filters ...

    where = (" AND " + " AND ".join(clauses)) if clauses else ""
    sql = base + where

    if query.limit is not None:
        sql += " LIMIT ?"
        params.append(query.limit)
        if query.offset is not None:
            sql += " OFFSET ?"
            params.append(query.offset)

    return SqlQuery(sql=sql, params=tuple(params))
```

### Availability WHERE Clause (task example)

```python
# Source: hybrid.py _map_task_availability logic, inverted to SQL
def _task_availability_clause(values: list[str]) -> tuple[str, list[Any]]:
    """Build WHERE clause for task availability filter.

    Maps availability enum values to their SQLite column conditions.
    """
    conditions: list[str] = []
    for v in values:
        if v == "available":
            conditions.append("(t.blocked = 0 AND t.dateCompleted IS NULL AND t.dateHidden IS NULL)")
        elif v == "blocked":
            conditions.append("(t.blocked != 0 AND t.dateCompleted IS NULL AND t.dateHidden IS NULL)")
        elif v == "completed":
            conditions.append("(t.dateCompleted IS NOT NULL AND t.dateHidden IS NULL)")
        elif v == "dropped":
            conditions.append("(t.dateHidden IS NOT NULL)")
    return "(" + " OR ".join(conditions) + ")", []
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `CommandModel(OmniFocusBaseModel)` | `CommandModel(StrictModel(OmniFocusBaseModel))` | Phase 34 | Enables QueryModel sibling |
| No query contracts | `QueryModel` + `ListResult[T]` | Phase 34 | Typed read pipeline |
| Full snapshot reads | Parameterized filtered SQL | Phase 34-35 | 30-60x performance improvement |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/ -x -q --no-cov` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | SQL uses parameterized values (no injection) | unit | `uv run pytest tests/test_query_builder.py -x -q --no-cov` | No -- Wave 0 |
| INFRA-04 | ListResult includes total field | unit | `uv run pytest tests/test_list_contracts.py -x -q --no-cov` | No -- Wave 0 |

### Supplementary Tests (not tied to requirements but needed for correctness)

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| QueryModel rejects unknown fields | unit | `uv run pytest tests/test_list_contracts.py::test_unknown_field_rejected -x -q --no-cov` | No -- Wave 0 |
| ListResult[T] serializes with camelCase | unit | `uv run pytest tests/test_list_contracts.py::test_list_result_serialization -x -q --no-cov` | No -- Wave 0 |
| Query models accept all specified filter fields | unit | `uv run pytest tests/test_list_contracts.py -x -q --no-cov` | No -- Wave 0 |
| Availability defaults applied correctly | unit | `uv run pytest tests/test_list_contracts.py -x -q --no-cov` | No -- Wave 0 |
| SQL parameterization (no string interpolation) | unit | `uv run pytest tests/test_query_builder.py -x -q --no-cov` | No -- Wave 0 |
| Availability filter produces correct WHERE clauses | unit | `uv run pytest tests/test_query_builder.py -x -q --no-cov` | No -- Wave 0 |
| StrictModel refactor doesn't break existing CommandModel tests | regression | `uv run pytest tests/test_contracts_type_aliases.py tests/test_output_schema.py -x -q --no-cov` | Yes -- existing |
| Protocol extensions compile without error | unit | `uv run pytest tests/test_list_contracts.py -x -q --no-cov` | No -- Wave 0 |
| limit=0 produces count-only SQL | unit | `uv run pytest tests/test_query_builder.py -x -q --no-cov` | No -- Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_list_contracts.py tests/test_query_builder.py -x -q --no-cov`
- **Per wave merge:** `uv run pytest -x -q --no-cov`
- **Phase gate:** Full suite green (`uv run pytest`) + `uv run pytest tests/test_output_schema.py -x -q`

### Wave 0 Gaps

- [ ] `tests/test_list_contracts.py` -- query model validation, ListResult serialization, defaults
- [ ] `tests/test_query_builder.py` -- parameterized SQL generation, availability clauses, limit/offset

## Open Questions

1. **mypy handling for incomplete protocol implementations**
   - What we know: Adding list methods to Protocol will flag `OperatorService`, `HybridRepository`, `BridgeRepository` as incomplete
   - What's unclear: Whether CI currently runs mypy in strict mode and whether this will break the build
   - Recommendation: Check CI config. If mypy runs, add `# type: ignore[override]` on the three implementation classes with a TODO referencing Phase 35

2. **`ListResult` in `contracts/__init__.py` re-exports**
   - What we know: The contracts `__init__.py` re-exports all models and calls `model_rebuild()`. `ListResult[T]` needs the same treatment.
   - What's unclear: Whether generic models need special `model_rebuild` handling
   - Recommendation: Add `ListResult` to the re-export and namespace. Test that `ListResult[Task].model_json_schema()` works after rebuild.

3. **Query builder: COUNT(*) for total**
   - What we know: D-01a requires `total` to reflect all matches ignoring limit/offset. Query builder needs to generate both the data query and the count query.
   - What's unclear: Whether to return two separate SQL strings or combine them
   - Recommendation: Return two `SqlQuery` values (data + count) from each builder function. The repository calls both. This keeps the builder pure and testable.

## Sources

### Primary (HIGH confidence)

- `docs/architecture.md` -- Model taxonomy, QueryModel definition, ListResult[T], protocol patterns, "Why query models are shared across layers"
- `src/omnifocus_operator/contracts/base.py` -- Current CommandModel implementation
- `src/omnifocus_operator/contracts/protocols.py` -- Current Service/Repository protocol definitions
- `src/omnifocus_operator/repository/hybrid.py` -- SQLite column names, availability mapping functions, existing parameterized SQL patterns
- `src/omnifocus_operator/models/enums.py` -- Entity-specific availability enum values
- `.planning/phases/34-contracts-and-query-foundation/34-CONTEXT.md` -- All locked decisions (D-01 through D-12)

### Verification (HIGH confidence)

- Pydantic 2.12.5 Generic model behavior -- verified via interactive test (alias generation, JSON schema, serialization)
- FastMCP 3.1.1 output schema for generic return types -- verified via interactive test (correct schema generation)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all patterns established
- Architecture: HIGH -- architecture doc pre-documents everything, verified with actual code
- Pitfalls: HIGH -- identified from direct code inspection and interactive verification
- Query builder SQL: MEDIUM -- availability mapping logic is clear from hybrid.py, but edge cases (especially the tags JOIN for task queries, project name partial match JOIN) need careful implementation and testing

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable -- all dependencies pinned, no fast-moving components)
