# Phase 14: Model Refactor & Lookups - Research

**Researched:** 2026-03-07
**Domain:** Pydantic model refactor + MCP tool registration + SQLite queries
**Confidence:** HIGH

## Summary

This phase introduces three changes to the existing codebase: (1) replace Task's separate `project`/`parent` string fields with a unified `parent: ParentRef | None` field, (2) rename the `list_all` MCP tool to `get_all`, and (3) add three get-by-ID tools (`get_task`, `get_project`, `get_tag`).

All changes are internal refactors and extensions of well-understood patterns already in the codebase. No new libraries needed. The main complexity is in the SQLite layer, where `containingProjectInfo` (FK to `ProjectInfo.pk`) must be resolved to a project's `persistentIdentifier` and name, and `parent` (task ID) must also get a name lookup.

**Primary recommendation:** Build ParentRef as a Pydantic model mirroring TagRef. Implement get-by-ID as filtered queries in HybridRepository (not reuse `_read_all`). Raise `ValueError` in tool handlers for not-found -- MCP SDK auto-converts to `isError: true`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Unified `parent` field: `{ type, id, name } | null`
- `type` values: `"project"` or `"task"` (string literal, not enum)
- Includes `name` for agent convenience -- consistent with existing TagRef pattern (id + name)
- Inbox tasks: `parent: null` (not a fake parent object); `in_inbox` field already handles inbox detection
- Immediate parent only -- no `containing_project` shortcut
- Raise MCP error (`isError: true`) for non-existent IDs
- Simple error message: "Task not found: {id}" (no hints about other entity types)
- No ID format validation -- just query the database and let "not found" cover invalid/missing IDs
- get-by-ID tools return the bare entity object directly (no envelope/wrapper)
- Same fields as in `get_all` -- identical Pydantic model, no enrichment
- Hard rename: `list_all` removed, `get_all` added (breaking change, acceptable pre-v2)
- Simple singular names: `get_task`, `get_project`, `get_tag`, `get_all`
- No namespace prefix -- MCP server itself is the namespace
- Single `id` parameter (not batch/list)

### Claude's Discretion
- ParentRef as Pydantic model vs TypedDict vs inline dict
- SQLite query strategy for get-by-ID (single query vs reuse existing _read_all)
- How to handle the `containingProjectInfo` -> parent type mapping in the SQLite adapter
- Test structure for new tools

### Deferred Ideas (OUT OF SCOPE)
- Summary/lightweight mode for get_all -- boolean flag that returns only `{ id, name }` per entity. Related to v1.4 field selection (OUTP-02).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NAME-01 | Rename `list_all` to `get_all` | Server tool registration change; update `_register_tools` function name + docstring |
| MODL-01 | Task replaces `project`/`parent` with unified `parent: { type, id } | null` | New ParentRef model + Task field change + adapter/repository updates |
| MODL-02 | All models, adapters, serialization updated for new parent structure | Bridge adapter, hybrid repository mapper, in-memory repo, test factories all need updates |
| LOOK-01 | get_task by ID with full Task object | New Repository protocol method + HybridRepository SQLite query + InMemoryRepository lookup + service method + server tool |
| LOOK-02 | get_project by ID with full Project object | Same pattern as LOOK-01 for projects |
| LOOK-03 | get_tag by ID with full Tag object | Same pattern as LOOK-01 for tags |
| LOOK-04 | Non-existent ID returns clear "not found" error | Raise ValueError in service/tool; MCP SDK auto-wraps as isError response |
</phase_requirements>

## Architecture Patterns

### Discretion Decision: ParentRef as Pydantic Model

**Recommendation: Pydantic model** (not TypedDict or inline dict)

Rationale:
- Consistent with existing `TagRef` model in `models/common.py` (same pattern: id + name, ParentRef adds type)
- Gets camelCase serialization for free via `OmniFocusBaseModel` ConfigDict
- Participates in `model_rebuild` / `_types_namespace` pattern already established
- Appears in JSON schema for `outputSchema` on tools

```python
# models/common.py
class ParentRef(OmniFocusBaseModel):
    """Reference to a task's parent (project or task)."""
    type: str  # "project" or "task" -- string literal, not enum
    id: str
    name: str
```

### Discretion Decision: SQLite Query Strategy for Get-By-ID

**Recommendation: Dedicated single-entity queries** (not reuse `_read_all`)

Rationale:
- `_read_all()` fetches ALL entities across ALL types every time -- wasteful for single-entity lookup
- Single-entity queries are simple `WHERE persistentIdentifier = ?` with existing row mappers
- Tag lookup for tasks still needed but can be scoped to one task: `WHERE task = ?`
- Project/tag queries are even simpler (no tag join needed for projects, tags have no joins)

```python
# Approximate shapes for new HybridRepository methods

def _read_task(self, task_id: str) -> dict[str, Any] | None:
    """Read a single task by persistentIdentifier. Returns None if not found."""
    # 1. Query task row (same filter as _TASKS_SQL + WHERE clause)
    # 2. Build tag lookup for just this task
    # 3. Map with _map_task_row
    # 4. Return dict or None

def _read_project(self, project_id: str) -> dict[str, Any] | None:
    """Read a single project by persistentIdentifier."""
    # Query Task+ProjectInfo JOIN + WHERE t.persistentIdentifier = ?

def _read_tag(self, tag_id: str) -> dict[str, Any] | None:
    """Read a single tag by persistentIdentifier."""
    # Query Context WHERE persistentIdentifier = ?
```

### Discretion Decision: containingProjectInfo -> ParentRef Type Mapping

**Recommendation: Build parent lookup table during _read_all; use targeted JOINs for single-entity queries**

Current state in `_map_task_row`:
```python
"project": row["containingProjectInfo"],  # ProjectInfo.pk
"parent": row["parent"],                  # parent task ID
```

Key SQLite semantics:
- `Task.parent` = parent task's `persistentIdentifier` (direct ID)
- `Task.containingProjectInfo` = `ProjectInfo.pk` (NOT the project's `persistentIdentifier`)
- To get project ID: `JOIN ProjectInfo pi2 ON t.containingProjectInfo = pi2.pk` then use `pi2.task`
- To determine parent type: if `parent` is NULL, parent is the containing project. If `parent` is non-NULL, parent is a task.

**Parent type logic:**
```
if parent IS NOT NULL:
    -> ParentRef(type="task", id=parent, name=<task name lookup>)
elif containingProjectInfo IS NOT NULL:
    -> ParentRef(type="project", id=<project persistentIdentifier>, name=<project name>)
else:
    -> None  (inbox task)
```

For `_read_all` (bulk): Pre-build lookup dicts for task names and project info (ProjectInfo.pk -> {id, name}).

For `_read_task` (single): Use a JOIN in the SQL query to get parent info in one query.

### Discretion Decision: Test Structure

**Recommendation: Extend existing test files, add focused test classes**

- `test_hybrid_repository.py`: Add `TestGetTask`, `TestGetProject`, `TestGetTag` classes
- `test_service.py`: Add service delegation tests for new methods
- `test_server.py`: Add MCP integration tests for new tools (get_all rename + get-by-ID)
- `test_models.py`: Add ParentRef tests + updated Task parent field tests
- `conftest.py`: Update `make_task_dict` to use new parent shape
- `test_adapter.py`: Update bridge adapter tests for parent field mapping

### Modified Project Structure

```
src/omnifocus_operator/
  models/
    common.py           # ADD ParentRef model
    task.py             # CHANGE: remove project/parent str fields, add parent: ParentRef | None
    __init__.py         # ADD ParentRef to namespace + model_rebuild
  repository/
    protocol.py         # ADD get_task, get_project, get_tag methods
    hybrid.py           # ADD _read_task, _read_project, _read_tag + UPDATE _map_task_row
    in_memory.py        # ADD get_task, get_project, get_tag lookup methods
    bridge.py           # ADD get_task, get_project, get_tag (delegate through get_all + filter)
  bridge/
    adapter.py          # UPDATE _adapt_task for new parent field structure
  service.py            # ADD get_task, get_project, get_tag delegation
  server.py             # RENAME list_all -> get_all, ADD 3 get-by-ID tools
```

### Error Handling Pattern

MCP SDK behavior (confirmed from v1.0 Phase 9 research):
- Any exception raised in a tool handler is caught by FastMCP
- Converted to `CallToolResult(isError=True, content=[TextContent(text=str(error))])`
- No special error class needed -- plain `ValueError` is sufficient

```python
# server.py tool handler pattern
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def get_task(id: str, ctx: Context[Any, Any, Any]) -> Task:
    service: OperatorService = ctx.request_context.lifespan_context["service"]
    result = await service.get_task(id)
    if result is None:
        raise ValueError(f"Task not found: {id}")
    return result
```

### Anti-Patterns to Avoid

- **Don't add an enum for parent type**: CONTEXT.md explicitly says `"project"` or `"task"` as string literals, not enum
- **Don't validate ID format**: CONTEXT.md says no ID format validation -- query and let not-found handle it
- **Don't add `containing_project` shortcut**: CONTEXT.md says immediate parent only
- **Don't wrap return values**: CONTEXT.md says bare entity object, no envelope
- **Don't reuse `_read_all` for single lookups**: wasteful for the common case

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| camelCase serialization for ParentRef | Custom serializer | Inherit `OmniFocusBaseModel` | Already handles alias_generator + validate_by_name |
| Error response formatting | Custom error handler | MCP SDK's built-in exception wrapping | Raises -> `isError: true` automatically |
| Forward ref resolution | Manual type wiring | `model_rebuild(_types_namespace=_ns)` | Established pattern in `models/__init__.py` |
| Tool parameter validation | Custom ID validation | MCP SDK + Pydantic | FastMCP validates tool parameters automatically |

## Common Pitfalls

### Pitfall 1: containingProjectInfo is NOT a persistentIdentifier
**What goes wrong:** Using `containingProjectInfo` directly as the project ID in ParentRef
**Why it happens:** Column name suggests it's a project reference, but it's a FK to `ProjectInfo.pk`
**How to avoid:** Always JOIN through `ProjectInfo` to get the project's `persistentIdentifier` (= `ProjectInfo.task`)
**Warning signs:** ParentRef.id values look like `"pi-xxx"` instead of standard OmniFocus IDs

### Pitfall 2: Parent Logic Requires Both Columns
**What goes wrong:** Looking at only `parent` or only `containingProjectInfo` to determine the parent
**Why it happens:** They serve different purposes -- `parent` = direct parent task, `containingProjectInfo` = containing project
**How to avoid:** Check `parent` first (if non-NULL, parent type is "task"). Only fall back to `containingProjectInfo` if `parent` is NULL.
**Warning signs:** Tasks inside projects showing as inbox (parent: null) when they should show the project as parent

### Pitfall 3: Subtask Parent vs Containing Project
**What goes wrong:** A subtask of a task that's inside a project has BOTH `parent` (task ID) and `containingProjectInfo` (project ref) set
**Why it happens:** OmniFocus tracks both the immediate parent and the containing project independently
**How to avoid:** CONTEXT.md says immediate parent only. Use `parent` (task ID) when set, regardless of `containingProjectInfo`.
**Warning signs:** Subtasks showing project as parent instead of their actual parent task

### Pitfall 4: Task model_rebuild Ordering
**What goes wrong:** `ParentRef` not available when `Task.model_rebuild()` runs
**Why it happens:** `models/__init__.py` has a specific ordering for model_rebuild calls
**How to avoid:** Add `ParentRef` to the `_ns` namespace dict AND call `ParentRef.model_rebuild()` before `Task.model_rebuild()`
**Warning signs:** Pydantic `PydanticUndefinedAnnotation` errors at import time

### Pitfall 5: Forgetting to Update Bridge Adapter
**What goes wrong:** Bridge path (BridgeRepository) returns old-format task dicts with `project`/`parent` strings
**Why it happens:** The adapter transforms bridge output format, but needs updating for the new parent structure
**How to avoid:** Update `_adapt_task` in `adapter.py` to build the ParentRef dict structure from bridge data
**Warning signs:** Tests pass with HybridRepository but fail with BridgeRepository

### Pitfall 6: InMemoryBridge/InMemoryRepository Not Updated
**What goes wrong:** Tests using `InMemoryRepository` or `InMemoryBridge` fail because they hold old-shape data
**Why it happens:** Test fixtures and factory functions use old `project`/`parent` string fields
**How to avoid:** Update `make_task_dict()` in `conftest.py` to use new `parent` shape; update InMemoryBridge default data
**Warning signs:** Test failures in `test_service.py`, `test_server.py`, `test_models.py`

### Pitfall 7: Name Lookup for Parent Task IDs
**What goes wrong:** ParentRef needs `name` but the `parent` column only stores an ID
**Why it happens:** SQLite `Task.parent` is just a string ID, no name
**How to avoid:** In `_read_all`: build a task-name lookup dict (`persistentIdentifier -> name`). In `_read_task`: use a subquery or second query.
**Warning signs:** ParentRef with empty or missing `name` field

## Code Examples

### ParentRef Model (models/common.py)
```python
class ParentRef(OmniFocusBaseModel):
    """Reference to a task's parent (project or task)."""
    type: str  # "project" or "task"
    id: str
    name: str
```

### Updated Task Model (models/task.py)
```python
from omnifocus_operator.models.base import ActionableEntity

if TYPE_CHECKING:
    from omnifocus_operator.models.common import ParentRef

class Task(ActionableEntity):
    in_inbox: bool
    effective_completion_date: AwareDatetime | None = None
    parent: ParentRef | None = None  # replaces project: str | None + parent: str | None
```

### Parent Resolution in _map_task_row (repository/hybrid.py)
```python
def _build_parent_ref(
    row: sqlite3.Row,
    project_lookup: dict[str, dict[str, str]],  # ProjectInfo.pk -> {id, name}
    task_name_lookup: dict[str, str],            # task persistentIdentifier -> name
) -> dict[str, str] | None:
    """Build ParentRef dict from SQLite row columns."""
    parent_task_id = row["parent"]
    if parent_task_id is not None:
        return {
            "type": "task",
            "id": parent_task_id,
            "name": task_name_lookup.get(parent_task_id, ""),
        }
    containing_project = row["containingProjectInfo"]
    if containing_project is not None:
        proj_info = project_lookup.get(containing_project)
        if proj_info:
            return {
                "type": "project",
                "id": proj_info["id"],
                "name": proj_info["name"],
            }
    return None
```

### Repository Protocol Extension
```python
@runtime_checkable
class Repository(Protocol):
    async def get_all(self) -> AllEntities: ...
    async def get_task(self, task_id: str) -> Task | None: ...
    async def get_project(self, project_id: str) -> Project | None: ...
    async def get_tag(self, tag_id: str) -> Tag | None: ...
```

### MCP Tool Registration
```python
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def get_task(id: str, ctx: Context[Any, Any, Any]) -> Task:
    """Look up a single task by its ID. Returns the full Task object."""
    service: OperatorService = ctx.request_context.lifespan_context["service"]
    result = await service.get_task(id)
    if result is None:
        raise ValueError(f"Task not found: {id}")
    return result
```

### InMemoryRepository Get-By-ID
```python
class InMemoryRepository:
    async def get_task(self, task_id: str) -> Task | None:
        return next((t for t in self._snapshot.tasks if t.id == task_id), None)

    async def get_project(self, project_id: str) -> Project | None:
        return next((p for p in self._snapshot.projects if p.id == project_id), None)

    async def get_tag(self, tag_id: str) -> Tag | None:
        return next((t for t in self._snapshot.tags if t.id == tag_id), None)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `project: str \| None` + `parent: str \| None` | `parent: ParentRef \| None` | This phase | Breaking change to Task model shape |
| `list_all` tool name | `get_all` tool name | This phase | Breaking change to MCP tool API |
| No get-by-ID tools | `get_task`, `get_project`, `get_tag` | This phase | New functionality |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 1.3+ |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x --no-cov -q` |
| Full suite command | `uv run pytest tests/` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NAME-01 | `list_all` renamed to `get_all` | integration | `uv run pytest tests/test_server.py -x -k "get_all"` | Needs update (existing tests reference `list_all`) |
| MODL-01 | Task.parent is ParentRef or None | unit | `uv run pytest tests/test_models.py -x -k "parent"` | Needs new tests |
| MODL-02 | Adapter/repo/serialization updated | unit+integration | `uv run pytest tests/test_adapter.py tests/test_hybrid_repository.py -x` | Needs updates |
| LOOK-01 | get_task returns full Task | unit+integration | `uv run pytest tests/test_hybrid_repository.py tests/test_server.py -x -k "get_task"` | Needs new tests |
| LOOK-02 | get_project returns full Project | unit+integration | `uv run pytest tests/test_hybrid_repository.py tests/test_server.py -x -k "get_project"` | Needs new tests |
| LOOK-03 | get_tag returns full Tag | unit+integration | `uv run pytest tests/test_hybrid_repository.py tests/test_server.py -x -k "get_tag"` | Needs new tests |
| LOOK-04 | Not-found returns error | unit+integration | `uv run pytest tests/test_server.py -x -k "not_found"` | Needs new tests |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x --no-cov -q`
- **Per wave merge:** `uv run pytest tests/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Update `conftest.py::make_task_dict` -- change `project`/`parent` string fields to `parent: ParentRef` shape
- [ ] Update all existing tests referencing `task.project` or `task.parent` as strings
- [ ] Update all existing tests referencing `list_all` tool name to `get_all`

## Open Questions

1. **BridgeRepository get-by-ID implementation**
   - What we know: BridgeRepository wraps bridge + adapter. Bridge returns full snapshot.
   - What's unclear: Should `get_task` call `get_all()` then filter, or should bridge get a new method?
   - Recommendation: Reuse `get_all()` + filter. Bridge only speaks in full snapshots (OmniJS limitation). This is the fallback path anyway (main path is HybridRepository/SQLite).

2. **Parent name when parent task doesn't exist**
   - What we know: SQLite has referential integrity issues (soft-deleted tasks may still be referenced)
   - What's unclear: Can `parent` reference a deleted task?
   - Recommendation: Use empty string for name if lookup fails (`task_name_lookup.get(id, "")`). Defensive but practical.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: all source files in `src/omnifocus_operator/`
- SQLite schema: `.research/deep-dives/direct-database-access/1-initial-discovery/sqlite_schema.sql`
- Phase 9 research on MCP error handling: `.planning/milestones/v1.0-phases/09-error-serving-degraded-mode/09-RESEARCH.md`
- Existing test patterns: `tests/test_server.py`, `tests/test_hybrid_repository.py`

### Secondary (MEDIUM confidence)
- `containingProjectInfo` FK semantics verified in `.research/deep-dives/direct-database-access/4-final-checks/verify_field_coverage.py` (JOIN `ProjectInfo.pk`)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, pure internal refactor
- Architecture: HIGH -- extends existing patterns (TagRef, Repository protocol, tool registration)
- Pitfalls: HIGH -- verified against actual codebase and SQLite schema
- SQLite parent mapping: HIGH -- verified through research scripts and test fixtures

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (stable internal architecture, no external dependencies)
