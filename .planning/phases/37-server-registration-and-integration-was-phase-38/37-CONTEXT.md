# Phase 37: Server Registration and Integration - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire 5 new MCP tools (list_tasks, list_projects, list_tags, list_folders, list_perspectives) end-to-end through server → service → repository. Add search filters to projects (name+notes), tags/folders/perspectives (name only). Create ListPerspectivesQuery/ListPerspectivesRepoQuery models.

**Requirements:** INFRA-05, SRCH-01, SRCH-02, SRCH-03, SRCH-04, RTOOL-01, RTOOL-02, RTOOL-03, DOC-10, DOC-11, DOC-12, DOC-13, DOC-14, DESC-07, DESC-08

### What this phase delivers

1. **5 MCP tool registrations** in `server.py` — list_tasks, list_projects, list_tags, list_folders, list_perspectives with `ToolAnnotations(readOnlyHint=True, idempotentHint=True)`
2. **5 tool description constants** in `descriptions.py` — behavioral guidance + response shape, following the edit_tasks layered pattern
3. **Search filter expansion** — `search: str | None` on all 5 query model pairs (agent + repo), wired through both SQL and Python-filter implementations
4. **ListPerspectivesQuery / ListPerspectivesRepoQuery** — new query model pair with `search` field, following tags/folders single-field precedent
5. **Protocol updates** — ServiceProtocol and RepositoryProtocol updated for perspectives query param and search fields on tags/folders/perspectives
6. **Field descriptions** on query model fields where fluency test fails
7. **End-to-end integration tests** — thin wire-only tests + one golden-path filter test per tool
8. **Cross-path equivalence** for search, including non-ASCII test term

### NOT in scope

- New filter types beyond search
- Fuzzy search (v1.4.1)
- Field selection / projection
- TaskPaper output format
- Standalone count tools (total_count embedded in ListResult)

</domain>

<decisions>
## Implementation Decisions

### Search Expansion (D-01)

- **D-01a:** Field named `search` across all 5 query models — consistent naming, tool description explains what each matches
- **D-01b:** Projects search on name+notes (like tasks); tags/folders/perspectives search name only
- **D-01c:** Full symmetry — `search` on all RepoQuery models, handled in both SQL and Python-filter implementations. Follows tasks precedent (ListTasksRepoQuery.search already exists)
- **D-01d:** Cross-path equivalence tests include a non-ASCII search term to catch COLLATE NOCASE vs `.lower()` divergence
- **D-01e:** Notable asymmetry (documented, not fixed): search uses repo-level LIKE, "Did You Mean" uses service-level fuzzy matching — different mechanisms at different layers serving different purposes (explicit filter vs proactive guidance)

### Tool Description Content (D-02)

- **D-02a:** Follows the edit_tasks layered pattern — zero overlap between description layers:
  - **Tool description** (`@mcp.tool(description=CONSTANT)`): behavioral rules the schema can't express — filter interaction (AND logic), non-obvious defaults (availability = available+blocked), pagination constraints (offset requires limit), response shape (items, total, has_more, warnings), camelCase note
  - **Query model class docstring** (`LIST_*_QUERY_DOC`): stays minimal positional description ("Filter and paginate tasks.")
  - **Field descriptions** (`Field(description=...)`): per-field semantics where name+type are ambiguous — search, review_due_within, availability defaults
- **D-02b:** Tool descriptions must fit under 2048 bytes (DESC-08)
- **D-02c:** Key content that must appear in tool descriptions: availability defaults (non-obvious), review_due_within format hint for list_projects, response shape line

### Perspectives Query Model (D-03)

- **D-03a:** Full query model pair: `ListPerspectivesQuery` / `ListPerspectivesRepoQuery` in `contracts/use_cases/list/perspectives.py`
- **D-03b:** Single field: `search: str | None = None`
- **D-03c:** Follows ListTagsQuery/ListFoldersQuery single-field precedent — SC#7 names these models explicitly
- **D-03d:** Service method `list_perspectives()` updated to accept `ListPerspectivesQuery` param; repo method updated to accept `ListPerspectivesRepoQuery`

### Protocol Updates (D-04)

- **D-04a:** Straightforward wiring — update ServiceProtocol and RepositoryProtocol, implementations follow
- **D-04b:** Same pattern as when tags/folders got availability filters

### Test Strategy (D-05)

- **D-05a:** Thin server tests per tool: registration, structured output shape, annotations (2-3 tests each)
- **D-05b:** One golden-path filter test per tool — verifies a specific filter flows end-to-end through all layers
- **D-05c:** No filter combination coverage at server layer — that's already covered by ~1400 service/repo tests
- **D-05d:** Cross-path equivalence for search: Claude's discretion on whether to extend existing tests or add separate search-specific tests

### Claude's Discretion

- Internal organization of search equivalence tests (extend existing vs separate)
- Exact field descriptions content (which fields fail the fluency test)
- Pipeline step organization for search in tags/folders/perspectives service methods
- Test fixture data and golden-path filter selection per tool

### Folded Todos

- "Add search tool for projects symmetric with task search" — covered by SRCH-01

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Conventions
- `docs/model-taxonomy.md` — QueryModel base class, query model naming, `@mcp.tool(description=CONSTANT)` pattern (line 182), agent-facing descriptions convention (lines 170-184), type constraint boundary
- `docs/architecture.md` — Three-layer architecture, agent message centralization
- `docs/structure-over-discipline.md` — Module boundaries, service boundary principle

### Existing Tool Patterns (follow these)
- `src/omnifocus_operator/server.py` — Tool registration pattern, `_build_patched_server()` test helper, existing get_* and add_*/edit_* tool wiring
- `src/omnifocus_operator/agent_messages/descriptions.py` — All existing tool description constants (GET_*_TOOL_DOC, ADD_TASKS_TOOL_DOC, EDIT_TASKS_TOOL_DOC) as templates for list tool descriptions
- `src/omnifocus_operator/middleware.py` — ValidationReformatterMiddleware (already global, covers new tools automatically)

### Query Model Patterns (follow these)
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` — ListTasksQuery/ListTasksRepoQuery with search field
- `src/omnifocus_operator/contracts/use_cases/list/tags.py` — Single-field query model pair (availability only)
- `src/omnifocus_operator/contracts/use_cases/list/folders.py` — Single-field query model pair
- `src/omnifocus_operator/contracts/use_cases/list/projects.py` — Multi-field query with validators, ReviewDueFilter

### Service Layer
- `src/omnifocus_operator/service/service.py` — _ListTasksPipeline, _ListProjectsPipeline (complex), list_tags/list_folders/list_perspectives (inline pass-throughs)
- `src/omnifocus_operator/contracts/protocols.py` — ServiceProtocol and RepositoryProtocol definitions

### Repository Implementations
- `src/omnifocus_operator/repository/hybrid/hybrid.py` — SQL-based list methods, query builder integration
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` — Python-filter list methods
- `src/omnifocus_operator/repository/hybrid/query_builder.py` — SQL query builder for tasks/projects

### Test Infrastructure
- `tests/test_server.py` — ARCH-01, TOOL-01/02/03 patterns, `_build_patched_server()`, Client(server) in-process testing
- `tests/test_hybrid_repository.py` — Cross-path equivalence test patterns

### Prior Phase Decisions
- `.planning/phases/36-service-orchestration-cross-path-equivalence-merged-from-old-phases-36-37/36-CONTEXT.md` — D-01 (validation placement), D-05 (cross-path equivalence structure)
- `.planning/phases/36.1-migrate-write-tools-to-typed-params-with-validation-middleware/36.1-CONTEXT.md` — D-01..D-04 (middleware architecture), D-05..D-07 (typed handler migration)
- `.planning/phases/36.2-sweep-agent-facing-schema-descriptions-and-tool-documentation/36.2-CONTEXT.md` — Documentation patterns
- `.planning/phases/36.3-centralize-field-descriptions-into-constants-like-warnings-and-errors/36.3-CONTEXT.md` — Centralization patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ListTasksQuery.search` / `ListTasksRepoQuery.search`: Exact pattern for adding search to other entity types
- `EDIT_TASKS_TOOL_DOC`: Template for behavioral-only tool descriptions with zero schema overlap
- `GET_TASK_TOOL_DOC`: Template for read tool descriptions with response shape + camelCase note
- `ValidationReformatterMiddleware`: Already global — new list tools get validation error formatting for free
- `_format_validation_errors()` in middleware.py: Catches Pydantic ValidationError, reformats to clean ToolError

### Established Patterns
- **Tool registration**: `@mcp.tool(description=CONSTANT, annotations=ToolAnnotations(...))` with typed params
- **Description layering**: tool description = behavioral rules, Field(description=) = per-field semantics, class docstring = minimal. Zero overlap.
- **Query model pairs**: agent-facing + repo-facing, even for single-field models (tags, folders)
- **Service pass-throughs**: tags/folders/perspectives use inline query→repo_query conversion, not pipelines
- **Cross-path equivalence**: parametrized repo fixture, sorted by ID, seed adapters per repo type

### Integration Points
- `server.py`: Register 5 new `@mcp.tool()` functions
- `descriptions.py`: Add 5 tool description constants + field descriptions for search
- `contracts/use_cases/list/`: Add `perspectives.py`, add `search` field to projects/tags/folders query models
- `contracts/protocols.py`: Update ServiceProtocol and RepositoryProtocol signatures
- `service/service.py`: Update list_perspectives to accept query, add search handling to pass-throughs
- `repository/hybrid/hybrid.py` + `query_builder.py`: Add search SQL for projects
- `repository/bridge_only/bridge_only.py`: Add search Python filter for projects/tags/folders/perspectives

</code_context>

<specifics>
## Specific Ideas

### Description Layering (the edit_tasks pattern)

```
Tool description (@mcp.tool)     Field descriptions (Field(description=))     Query docstring (__doc__)
─────────────────────────────    ─────────────────────────────────────────    ──────────────────────────
Behavioral rules:                Per-field semantics:                         Minimal positional:
- Filter interaction (AND)       - search: "case-insensitive substring..."   "Filter and paginate tasks."
- Defaults (availability)        - review_due_within: "duration: 1w, 2m"
- Pagination (offset→limit)      - availability: "defaults to..."
- Response shape (items, total)
- camelCase note
```

### Search Flow

```
Agent sends           Query model           Repo query           SQL / Python filter
────────────          ────────────          ──────────           ──────────────────
search="review"  →  ListTasksQuery     →  ListTasksRepoQuery  →  LIKE '%review%' on name+notes
                    search="review"       search="review"         / .lower() in Python

search="home"    →  ListTagsQuery      →  ListTagsRepoQuery   →  Python .lower() on name only
                    search="home"         search="home"           (fetch-all + filter)

search="Büro"    →  ListFoldersQuery   →  ListFoldersRepoQuery →  Python .lower() on name only
                    search="Büro"         search="Büro"           (cross-path: non-ASCII test)
```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

### Reviewed Todos (not folded)
- "Add position field to expose child task ordering" — models concern, not server registration
- "Enforce mutually exclusive tags at service layer" — write-path, not relevant
- "Return full task object in edit_tasks response" — write-path, not relevant
- "Move no-op warning check ordinal position" — write-path, not relevant
- "Fix same-container move by translating to moveBefore/moveAfter" — write-path, not relevant
- "Clarify repetition schedule and repeat mode edge cases" — docs concern, partially done
- "Investigate and enforce serial execution guarantee for bridge calls" — bridge/v1.6, not relevant
- "Reorganize test suite into unit/integration/golden-master folders" — infrastructure, not relevant
- "Investigate macOS App Nap impact on OmniFocus responsiveness" — bridge/v1.6, not relevant

</deferred>

---

*Phase: 37-server-registration-and-integration-was-phase-38*
*Context gathered: 2026-04-03*
