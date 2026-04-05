# Phase 35: SQL Repository - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

HybridRepository list methods with filtered SQL queries for all 5 entity types. This phase wires the Phase 34 query builder and existing row mappers into 5 new async methods on HybridRepository that return `ListResult[T]`.

**Requirements:** TASK-01 through TASK-11, PROJ-01 through PROJ-07, BROWSE-01 through BROWSE-03, INFRA-02

### Methods Created (exhaustive list)

| Method | Entity | Filters | Lookup Tables | Pagination |
|--------|--------|---------|---------------|------------|
| `list_tasks(query)` | Task | 8 params (in_inbox, flagged, project, tags, estimated_minutes_max, availability, search, limit/offset) | tag_name_lookup, task_tag_map, project_info_lookup, task_name_lookup | Yes |
| `list_projects(query)` | Project | 5 params (availability, folder, review_due_within, flagged, limit/offset) | tag_name_lookup, task_tag_map, project_info_lookup | Yes |
| `list_tags(query)` | Tag | 1 param (availability) | None | No |
| `list_folders(query)` | Folder | 1 param (availability) | None | No |
| `list_perspectives()` | Perspective | None | None | No |

### NOT in scope

- BridgeRepository list methods (~~Phase 36~~ delivered in Phase 35.2)
- Service layer orchestration (~~Phase 37~~ now Phase 36)
- MCP tool registration (~~Phase 38~~ now Phase 37)
- InMemoryBridge list methods (~~Phase 36~~ delivered in Phase 35.2)

</domain>

<decisions>
## Implementation Decisions

### Tags/Folders Query Approach (D-01)

- **D-01a:** Tags and folders use **fetch-all + Python filter**, NOT the query builder
- **D-01b:** Reuse existing `_TAGS_SQL` and `_FOLDERS_SQL` constants from hybrid.py
- **D-01c:** Filter availability in Python after fetching all rows (~64 tags, ~79 folders — trivially fast)
- **D-01d:** query_builder.py stays focused on complex entities (tasks, projects) with parameterized multi-condition WHERE clauses
- **D-01e:** If tags/folders gain more filters in a future milestone, migrate to query_builder then

### Lookup Table Strategy (D-02)

- **D-02a:** `list_tasks` and `list_projects` build **full lookup tables**, same pattern as `_read_all()`
- **D-02b:** Reuse existing lookup-building code: tag_name_lookup, task_tag_map, project_info_lookup, task_name_lookup
- **D-02c:** Row mappers (`_map_task_row`, `_map_project_row`) called unchanged — same signature, same behavior
- **D-02d:** At ~64 tags, ~363 projects, ~2,400 tasks — full table scans for lookups are sub-millisecond
- **D-02e:** Tags, folders, perspectives need zero lookup tables — direct row mapping

### Performance Validation — INFRA-02 (D-03)

- **D-03a:** Automated **comparative test** in pytest: run filtered query AND full `get_all()` in same test process, assert filtered is faster
- **D-03b:** Seed test database with ~200 rows to make the performance gap meaningful in in-memory SQLite
- **D-03c:** UAT note for validating the real-database gap (~6ms filtered vs ~46ms full snapshot)
- **D-03d:** No hard timing thresholds (machine-dependent, CI-flaky)

### Plan Structure (D-04)

- **D-04a:** **Two plans** split by complexity
- **D-04b:** Plan 1: `list_tasks` + `list_projects` — query builder integration, full lookup tables, pagination, estimated 150+ test cases
- **D-04c:** Plan 2: `list_tags` + `list_folders` + `list_perspectives` — fetch-all + Python filter, no lookups, no pagination, estimated ~30 test cases

### Claude's Discretion

- Internal organization of list method sync helpers (`_list_tasks_sync`, etc.)
- Exact `hasMore` computation formula (likely `offset + len(items) < total`)
- Whether lookup-building code is extracted into shared helpers or duplicated between `_read_all` and list methods
- Test fixture design for the ~200 row performance seed
- How perspectives plist data flows through `list_perspectives`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `docs/architecture.md` — Full model taxonomy, protocol definitions, package structure, "Why query models are shared across layers"

### Specifications
- `.research/updated-spec/MILESTONE-v1.3.md` — Original milestone spec. Deviations captured in Phase 34 context (availability replaces status, has_children dropped, no shorthands)
- `.planning/REQUIREMENTS.md` — v1.3 requirements (TASK-01 through TASK-11, PROJ-01 through PROJ-07, BROWSE-01 through BROWSE-03, INFRA-02)

### Phase 34 Foundation (MUST read)
- `.planning/phases/34-contracts-and-query-foundation/34-CONTEXT.md` — All contract decisions: ListResult shape (D-01), filter defaults (D-02), availability semantics (D-03), query builder design (D-05), field naming (D-06), count-only via limit=0 (D-10)
- `src/omnifocus_operator/repository/query_builder.py` — `build_list_tasks_sql()` and `build_list_projects_sql()` pure functions returning `(SqlQuery, SqlQuery)` tuples
- `src/omnifocus_operator/contracts/use_cases/list_entities.py` — ListTasksQuery, ListProjectsQuery, ListTagsQuery, ListFoldersQuery, ListResult[T]

### Existing Code (patterns to follow)
- `src/omnifocus_operator/repository/hybrid.py` — Row mappers (`_map_task_row`, `_map_project_row`, `_map_tag_row`, `_map_folder_row`, `_map_perspective_row`), lookup table building, connection management, `asyncio.to_thread` wrapping
- `src/omnifocus_operator/contracts/protocols.py` — Repository/Service protocol signatures (list methods already declared by Phase 34)
- `src/omnifocus_operator/models/enums.py` — Availability, TagAvailability, FolderAvailability enums

### Test Patterns
- `tests/test_query_builder.py` — Query builder test patterns (parameterized SQL assertions)
- `tests/test_hybrid_repository.py` — Repository test fixtures (in-memory SQLite, schema creation)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_map_task_row(row, tag_map, project_lookup, task_name_lookup)`: Pure function mapping SQLite row → Task dict. Reuse unchanged for list_tasks
- `_map_project_row(row, tag_map, project_lookup)`: Pure function mapping joined row → Project dict. Reuse unchanged for list_projects
- `_map_tag_row(row)`: Pure function mapping Context row → Tag dict. Reuse for list_tags
- `_map_folder_row(row)`: Pure function mapping Folder row → Folder dict. Reuse for list_folders
- `_map_perspective_row(row)`: Maps Perspective plist → dict. Reuse for list_perspectives
- `build_list_tasks_sql(query)` / `build_list_projects_sql(query)`: Phase 34 query builder returning `(data_query, count_query)` SqlQuery tuples
- `_TAGS_SQL`, `_FOLDERS_SQL`, `_PERSPECTIVES_SQL`: Base SQL constants for fetching all entities

### Established Patterns
- **Fresh read-only connection per call**: `sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)`
- **Async via thread**: `await asyncio.to_thread(self._sync_method, ...)`
- **Lookup table building**: Separate queries for TaskToTag, Context (tags), ProjectInfo, then dict comprehensions
- **Row mapping → model_validate**: `Entity.model_validate(_map_entity_row(row, lookups))`

### Integration Points
- `HybridRepository` class in `repository/hybrid.py`: Add 5 new async methods + sync helpers
- Existing `_read_all()` method: Reference pattern for lookup building and row mapping

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The implementation path is well-constrained by Phase 34 contracts and existing patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Reviewed Todos (not folded)
All 8 matched todos were write-path or unrelated concerns:
- "Enforce mutually exclusive tags at service layer" — write-path
- "Return full task object in edit_tasks response" — write-path
- "Remove misleading single runtime dependency messaging" — docs
- "Migrate write tools to typed params with validation middleware" — server/write-path
- "Add position field to expose child task ordering" — models/display
- "Investigate serial execution guarantee for bridge calls" — bridge
- "Move no-op warning check ordinal position" — service/write-path
- "Add retry logic for bridge timeouts" — bridge

</deferred>

---

*Phase: 35-sql-repository*
*Context gathered: 2026-03-30*
