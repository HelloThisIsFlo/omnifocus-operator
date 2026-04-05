# Phase 37: Server Registration and Integration - Research

**Researched:** 2026-04-03
**Domain:** MCP tool registration, search filter expansion, end-to-end wiring
**Confidence:** HIGH

## Summary

This phase wires 5 existing service methods (list_tasks, list_projects, list_tags, list_folders, list_perspectives) as MCP tools, adds `search` filter to all 5 query model pairs, creates ListPerspectivesQuery/ListPerspectivesRepoQuery, updates protocols, writes tool descriptions, and adds integration tests. All patterns are well-established in the codebase from prior phases -- this is replication, not invention.

**Primary recommendation:** Follow the exact patterns from existing tools (get_task, add_tasks, edit_tasks) for registration, and the ListTasksQuery.search pattern for search expansion. No new libraries or architectural changes needed.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01a:** Field named `search` across all 5 query models -- consistent naming
- **D-01b:** Projects search name+notes; tags/folders/perspectives search name only
- **D-01c:** Full symmetry -- `search` on all RepoQuery models, both SQL and Python-filter paths
- **D-01d:** Cross-path equivalence tests include non-ASCII search term
- **D-01e:** search uses repo-level LIKE; "Did You Mean" uses service-level fuzzy -- documented asymmetry
- **D-02a:** Follows edit_tasks layered pattern -- zero overlap between description layers
- **D-02b:** Tool descriptions fit under 2048 bytes (DESC-08)
- **D-02c:** Key content: availability defaults, review_due_within format hint, response shape line
- **D-03a:** Full query model pair: ListPerspectivesQuery / ListPerspectivesRepoQuery in `contracts/use_cases/list/perspectives.py`
- **D-03b:** Single field: `search: str | None = None`
- **D-03c:** Follows ListTagsQuery/ListFoldersQuery single-field precedent
- **D-03d:** Service and repo methods updated for perspectives query param
- **D-04a:** Update ServiceProtocol and RepositoryProtocol
- **D-04b:** Same pattern as tags/folders availability filter wiring
- **D-05a:** Thin server tests: registration, structured output shape, annotations (2-3 per tool)
- **D-05b:** One golden-path filter test per tool
- **D-05c:** No filter combination coverage at server layer
- **D-05d:** Cross-path equivalence for search: Claude's discretion on organization

### Claude's Discretion

- Internal organization of search equivalence tests (extend existing vs separate)
- Exact field descriptions content (which fields fail fluency test)
- Pipeline step organization for search in tags/folders/perspectives service methods
- Test fixture data and golden-path filter selection per tool

### Deferred Ideas (OUT OF SCOPE)

None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-05 | Tool descriptions detailed enough for LLM to call correctly | D-02a/b/c: layered description pattern, 2048-byte limit, key content items |
| SRCH-01 | Search projects by name+notes | D-01b: name+notes, same implementation as tasks; add `search` to ListProjectsQuery/RepoQuery |
| SRCH-02 | Search tags by name | D-01b: name only; add `search` to ListTagsQuery/RepoQuery |
| SRCH-03 | Search folders by name | D-01b: name only; add `search` to ListFoldersQuery/RepoQuery |
| SRCH-04 | Search perspectives by name | D-01b/D-03a: name only; new ListPerspectivesQuery/RepoQuery models |
| RTOOL-01 | 5 list tools use typed query model params | Registration pattern: `@mcp.tool(description=CONSTANT)` with typed params |
| RTOOL-02 | Schema field names use camelCase aliases | QueryModel base class + Pydantic alias_generator handles this automatically |
| RTOOL-03 | Validation errors agent-friendly via middleware | ValidationReformatterMiddleware already global -- covers new tools for free |
| DOC-10 | List tool descriptions: behavioral guidance only | D-02a: tool desc = filter interaction, defaults, pagination, response shape |
| DOC-11 | Field descriptions where fluency test fails | search, availability defaults, review_due_within |
| DOC-12 | camelCase note + response structure hint | Consistent with DOC-07 pattern on existing read tools |
| DOC-13 | No implementation details in descriptions | Standard convention -- no RepoQuery, pipeline, SQL references |
| DOC-14 | Description constants from descriptions.py | Extends DESC-02/DESC-03 to new models |
| DESC-07 | Tool functions use centralized descriptions | Enforcement test already exists, will catch new tools |
| DESC-08 | Tool descriptions <= 2048 bytes | Enforcement test already exists |

</phase_requirements>

## Architecture Patterns

### Registration Pattern (from server.py)

Every list tool follows this exact pattern:

```python
# In server.py _register_tools()
@mcp.tool(
    description=LIST_TASKS_TOOL_DOC,  # constant from descriptions.py
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def list_tasks(
    # Typed query model -- FastMCP introspects for inputSchema
    query: ListTasksQuery,
    ctx: Context,
) -> ListResult[Task]:
    from omnifocus_operator.service import OperatorService
    service: OperatorService = ctx.lifespan_context["service"]
    return await service.list_tasks(query)
```

Key points:
- `description=CONSTANT` (not inline string) -- enforcement test catches violations
- `ToolAnnotations(readOnlyHint=True, idempotentHint=True)` for all list tools
- Typed param (`ListTasksQuery`) -- FastMCP generates inputSchema from Pydantic model
- Return type annotation (`ListResult[Task]`) needed at runtime for outputSchema
- `ListResult` import must be runtime (not TYPE_CHECKING) because of `from __future__ import annotations`

### Query Model Pair Pattern

Agent-facing and repo-facing always come in pairs:

```python
# contracts/use_cases/list/perspectives.py
class ListPerspectivesQuery(QueryModel):
    __doc__ = LIST_PERSPECTIVES_QUERY_DOC  # from descriptions.py
    search: str | None = None

class ListPerspectivesRepoQuery(QueryModel):
    """Repo-facing query -- identical fields today."""
    search: str | None = None
```

### Description Layering (zero overlap)

```
Layer                    Content                          Example
----                     -------                          -------
Tool description         Behavioral rules only            "Filters combine with AND logic"
  (@mcp.tool)            Response shape, defaults         "availability defaults to available+blocked"
                         Pagination constraints            "offset requires limit"

Field description        Per-field semantics where         search: "Case-insensitive substring match..."
  (Field(description=))  name+type are ambiguous           availability: "Defaults to available+blocked"

Class docstring          Minimal positional                "Filter and paginate tasks."
  (__doc__)              description only
```

### Service Pass-through Pattern (for tags/folders/perspectives)

Current tags/folders are inline pass-throughs. With search added:

```python
async def list_tags(self, query: ListTagsQuery) -> ListResult[Tag]:
    repo_query = ListTagsRepoQuery(
        availability=query.availability,
        search=query.search,  # NEW: pass through directly
    )
    repo_result = await self._repository.list_tags(repo_query)
    return ListResult(items=repo_result.items, total=repo_result.total, has_more=repo_result.has_more)
```

### Search Implementation Pattern

**SQL path (hybrid repo -- projects):**
```python
# In query_builder.py, build_list_projects_sql():
if query.search is not None:
    conditions.append("(p.name LIKE ? COLLATE NOCASE OR p.plainTextNote LIKE ? COLLATE NOCASE)")
    params.append(f"%{query.search}%")
    params.append(f"%{query.search}%")
```

**Python-filter path (bridge_only -- all entities):**
```python
# For name+notes (projects):
if query.search is not None:
    lower_search = query.search.lower()
    items = [p for p in items if lower_search in p.name.lower() or (p.note and lower_search in p.note.lower())]

# For name only (tags/folders/perspectives):
if query.search is not None:
    lower_search = query.search.lower()
    items = [t for t in items if lower_search in t.name.lower()]
```

**Hybrid repo (tags/folders/perspectives):** These use fetch-all + Python filter (not SQL query builder). Search filter added inline alongside existing availability filter.

### Protocol Update Pattern

```python
# In protocols.py:
# Service protocol -- ListPerspectivesQuery param added:
async def list_perspectives(self, query: ListPerspectivesQuery) -> ListResult[Perspective]: ...

# Repository protocol -- ListPerspectivesRepoQuery param added:
async def list_perspectives(self, query: ListPerspectivesRepoQuery) -> ListRepoResult[Perspective]: ...
```

### Test Patterns

**Server integration test (thin wire test):**
```python
class TestListTasks:
    async def test_list_tasks_returns_structured_content(self):
        """Registration + structured output shape."""
        service = OperatorService(repository=repo_with_data)
        server = _build_patched_server(service)
        _register_tools(server)
        async with Client(server) as client:
            result = await client.call_tool("list_tasks", {"limit": 10})
            assert result.structured_content is not None
            assert "items" in result.structured_content
            assert "total" in result.structured_content

    async def test_list_tasks_has_read_only_annotation(self):
        """Tool annotations."""
        async with Client(server) as client:
            tools = await client.list_tools()
            tool = next(t for t in tools if t.name == "list_tasks")
            assert tool.annotations.readOnlyHint is True

    async def test_list_tasks_golden_path_filter(self):
        """One specific filter flows end-to-end."""
        result = await client.call_tool("list_tasks", {"flagged": True})
        # Verify filter actually worked
```

**Cross-path equivalence for search:**
```python
# In test_cross_path_equivalence.py:
async def test_list_tags_search(self, cross_repo: Repository) -> None:
    result = await cross_repo.list_tags(ListTagsRepoQuery(search="term"))
    # assert correct items returned

async def test_list_tags_search_non_ascii(self, cross_repo: Repository) -> None:
    result = await cross_repo.list_tags(ListTagsRepoQuery(search="Buro"))
    # catches COLLATE NOCASE vs .lower() divergence
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| camelCase in JSON Schema | Manual alias on each field | QueryModel base class + Pydantic alias_generator | Already configured project-wide |
| Validation error formatting | Custom try/except per tool | ValidationReformatterMiddleware | Already global, covers new tools automatically |
| inputSchema generation | Manual schema definition | FastMCP + typed Pydantic params | Introspects model, generates schema |
| outputSchema generation | Manual schema definition | Return type annotation (ListResult[T]) | FastMCP generates from type hint |

## Common Pitfalls

### Pitfall 1: Runtime imports for return types
**What goes wrong:** `from __future__ import annotations` makes all annotations strings. FastMCP uses `get_type_hints()` to resolve return types for outputSchema.
**How to avoid:** `ListResult` and entity model imports MUST be runtime (not under `TYPE_CHECKING`). The existing server.py already has comments explaining this.
**Warning signs:** outputSchema missing from tool listing, or `NameError` at registration time.

### Pitfall 2: Protocol signature mismatch
**What goes wrong:** Updating `list_perspectives()` to take a query param in OperatorService but not in ServiceProtocol (or vice versa) breaks `runtime_checkable` protocol checks.
**How to avoid:** Update both protocols (Service and Repository) and all implementations (OperatorService, HybridRepository, BridgeOnlyRepository) simultaneously.
**Warning signs:** `TypeError` at runtime, mypy errors on protocol conformance.

### Pitfall 3: Missing search in repo_query construction
**What goes wrong:** Adding `search` to query models but forgetting to pass it through in service list methods or `_build_repo_query`.
**How to avoid:** For pipeline-based methods (tasks, projects), add `search=self._query.search` in `_build_repo_query()`. For pass-throughs (tags/folders/perspectives), add `search=query.search` in the inline construction.
**Warning signs:** Search filter silently ignored -- tests pass because no search test exists yet at that layer.

### Pitfall 4: Description byte limit
**What goes wrong:** Tool descriptions for list_tasks/list_projects (which have many filters) can exceed 2048 bytes.
**How to avoid:** Write behavioral guidance only (not field-by-field listing). Enforcement test catches violations. list_tags/list_folders/list_perspectives are simpler and won't be close to the limit.
**Warning signs:** DESC-08 enforcement test fails with exact byte count.

### Pitfall 5: Non-ASCII cross-path divergence
**What goes wrong:** SQLite `COLLATE NOCASE` only handles ASCII case-folding. Python `.lower()` handles Unicode. A search for "buro" won't match "Buro" in SQLite but will in Python.
**How to avoid:** D-01d requires non-ASCII test term. For tags/folders/perspectives (Python-filter only in both paths), this isn't an issue. For projects (SQL in hybrid), the test catches divergence.
**Warning signs:** Cross-path equivalence test fails only for non-ASCII terms.

### Pitfall 6: DESC-06 exception list
**What goes wrong:** New query model classes (ListPerspectivesQuery, ListPerspectivesRepoQuery) need centralized descriptions. DESC-06 enforcement test will flag them if they use inline docstrings/descriptions.
**How to avoid:** Use `__doc__ = CONSTANT` pattern and `Field(description=CONSTANT)` from descriptions.py. The repo-facing query (ListPerspectivesRepoQuery) docstring can be inline since it's internal (check if it's in the exception list).
**Warning signs:** test_descriptions.py fails for new classes.

## Integration Points Inventory

| File | Change | Impact |
|------|--------|--------|
| `server.py` | Register 5 `@mcp.tool()` functions | New tool handlers |
| `descriptions.py` | Add 5 `LIST_*_TOOL_DOC` constants + field descriptions + query docstrings | Agent-facing text |
| `contracts/use_cases/list/perspectives.py` | NEW file with ListPerspectivesQuery/RepoQuery | New query model pair |
| `contracts/use_cases/list/tags.py` | Add `search: str \| None = None` to both models | Search filter |
| `contracts/use_cases/list/folders.py` | Add `search: str \| None = None` to both models | Search filter |
| `contracts/use_cases/list/projects.py` | Add `search: str \| None = None` to both models | Search filter |
| `contracts/use_cases/list/__init__.py` | Add ListPerspectivesQuery/RepoQuery re-exports | Package API |
| `contracts/protocols.py` | Update Service.list_perspectives and Repository.list_perspectives signatures | Protocol boundary |
| `service/service.py` | Update list_tags/list_folders/list_perspectives to pass search; add search to _ListProjectsPipeline | Service wiring |
| `repository/hybrid/hybrid.py` | Add search filter to _list_tags_sync, _list_folders_sync, _list_perspectives_sync; update list_perspectives to accept query | Search in hybrid |
| `repository/hybrid/query_builder.py` | Add search clause to build_list_projects_sql | SQL search for projects |
| `repository/bridge_only/bridge_only.py` | Add search filter to list_tags, list_folders, list_perspectives, list_projects; update list_perspectives to accept query | Search in bridge |
| `tests/test_server.py` | Add test classes for 5 list tools (registration, annotations, golden-path) | Integration tests |
| `tests/test_cross_path_equivalence.py` | Add search equivalence tests with non-ASCII term | Cross-path tests |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_server.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RTOOL-01 | 5 list tools registered and callable | integration | `uv run pytest tests/test_server.py -x -q -k "list_"` | Wave 0 |
| RTOOL-02 | camelCase aliases in schema | integration | `uv run pytest tests/test_server.py -x -q -k "camelcase"` | Wave 0 |
| RTOOL-03 | Validation errors formatted | integration | `uv run pytest tests/test_server.py -x -q -k "validation"` | Wave 0 |
| INFRA-05 | Descriptions detailed enough | unit | `uv run pytest tests/test_descriptions.py -x -q` | Exists (DESC-07/08) |
| SRCH-01..04 | Search across all entity types | integration | `uv run pytest tests/test_cross_path_equivalence.py -x -q -k "search"` | Wave 0 |
| DOC-10..14 | Description content/centralization | unit | `uv run pytest tests/test_descriptions.py -x -q` | Exists (enforcement) |
| DESC-07 | Tool descriptions use constants | unit | `uv run pytest tests/test_descriptions.py::TestToolDescriptionEnforcement -x -q` | Exists |
| DESC-08 | Descriptions <= 2048 bytes | unit | `uv run pytest tests/test_descriptions.py::TestToolDescriptionEnforcement::test_tool_descriptions_within_client_byte_limit -x -q` | Exists |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_server.py tests/test_descriptions.py tests/test_cross_path_equivalence.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] Server integration tests for 5 list tools in `tests/test_server.py` -- registration, annotations, structured output, golden-path
- [ ] Search cross-path equivalence tests in `tests/test_cross_path_equivalence.py` -- including non-ASCII term
- [ ] Seed data for cross-path tests needs searchable entities for tags/folders/perspectives
- DESC-06 enforcement test tool count assertion (`assert len(tools) >= 6`) will need updating to `>= 11`

## Sources

### Primary (HIGH confidence)
- `server.py` (lines 104-238) -- complete tool registration pattern with 6 existing tools
- `descriptions.py` (lines 1-391) -- all existing description constants and layering convention
- `contracts/use_cases/list/tasks.py` -- ListTasksQuery.search as template for all search fields
- `contracts/protocols.py` -- current Service and Repository protocol signatures
- `service/service.py` (lines 182-203) -- existing inline pass-throughs for tags/folders/perspectives
- `repository/hybrid/hybrid.py` (lines 816-863) -- fetch-all + Python filter for tags/folders/perspectives
- `repository/bridge_only/bridge_only.py` (lines 215-237) -- Python filter pattern
- `repository/hybrid/query_builder.py` (line 152) -- existing search SQL clause for tasks
- `tests/test_server.py` -- existing test patterns for tool registration tests
- `tests/test_cross_path_equivalence.py` -- existing search equivalence test for tasks
- `tests/test_descriptions.py` (lines 266-379) -- DESC-07/08 enforcement tests

### Secondary (MEDIUM confidence)
- None needed -- all patterns are internal to this codebase

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns established
- Architecture: HIGH -- direct replication of existing patterns
- Pitfalls: HIGH -- identified from codebase inspection and prior phase decisions

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (stable -- internal codebase patterns)
