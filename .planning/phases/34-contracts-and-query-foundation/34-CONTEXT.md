# Phase 34: Contracts and Query Foundation - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Typed query contracts and SQL generation as independently testable pure functions. This phase creates the models, protocols, and query builder that all downstream phases (35-38) build on. No repository implementations, no service logic, no MCP tool registration — just contracts and SQL generation.

**Requirements:** INFRA-01 (parameterized SQL), INFRA-04 (total_count in list responses)

</domain>

<decisions>
## Implementation Decisions

### ListResult Shape (D-01)

- **D-01a:** `ListResult[T]` has three fields: `items: list[T]`, `total: int`, `hasMore: bool`
- **D-01b:** Named `total` (not `total_count`) — cleaner
- **D-01c:** No offset/limit echo — the agent already knows what it sent. The only new information is `total` and `hasMore` (which depend on the actual data)
- **D-01d:** Uniform shape for ALL 5 list tools, including non-paginated entities (tags, folders, perspectives). For non-paginated: `total = len(items)`, `hasMore = false`
- **D-01e:** `ListResult[T]` inherits `OmniFocusBaseModel` (outbound, system-constructed, no `extra="forbid"`)
- **D-01f:** Lives in `contracts/use_cases/list_entities.py` alongside query models

### Filter Defaults — Split Concern (D-02)

Two distinct concerns, two distinct locations:

- **D-02a: Defaults live on the Pydantic model** (contract concern). Example: `ListTasksQuery.availability` defaults to `["available", "blocked"]`. The model is self-describing — you read it and know what happens when a field is omitted.
- **D-02b: Shorthand expansion lives in the service** (domain concern). Example: the service resolves tag names to IDs, validates availability values against the entity-specific enum, etc. Repository receives concrete, resolved values only.
- **D-02c:** This split is consistent with the existing architecture: the model carries agent-friendly values, the service resolves them into implementation-ready values. The default just means the agent doesn't have to explicitly say "available, blocked" every time.

### Availability Filter — Uniform Across All Entities (D-03)

**Spec deviation:** The original milestone spec had a project `status` filter with shorthands (`remaining`, `available`, `all`). This is replaced by a uniform `availability` list filter across all entities. Simpler, fewer concepts, same expressiveness.

- **D-03a:** Every list tool that supports filtering has an `availability` parameter accepting a **list** with OR semantics
- **D-03b:** No shorthands — agents pass concrete enum values only
- **D-03c:** No `include_completed` flag — the availability default handles exclusion naturally
- **D-03d:** Entity-specific enum values and defaults:

  | Entity | Enum values | Default |
  |--------|------------|---------|
  | Tasks | `available`, `blocked`, `completed`, `dropped` | `["available", "blocked"]` |
  | Projects | `available`, `blocked`, `completed`, `dropped` | `["available", "blocked"]` |
  | Tags | `available`, `blocked`, `dropped` | `["available", "blocked"]` |
  | Folders | `available`, `dropped` | `["available"]` |
  | Perspectives | (no filter) | (no filter) |

- **D-03e:** Agent opts into completed/dropped by explicitly including them: `availability: ["available", "blocked", "completed"]`

### Protocol Extension (D-04)

- **D-04a:** Extend the existing `Repository` and `Service` protocols in `contracts/protocols.py` with new `list_*` method signatures
- **D-04b:** No separate query protocols — "Structure Over Discipline" means incomplete implementations are type errors, not silent gaps
- **D-04c:** All three repository implementations (HybridRepository, BridgeRepository, InMemoryBridge) will need to implement list methods in downstream phases

### Query Builder (D-05)

- **D-05a:** Standalone `repository/query_builder.py` with pure functions producing parameterized SQL
- **D-05b:** v1.3.1 date filter predicates will slot directly into this module without touching hybrid.py
- **D-05c:** Return type is Claude's discretion (implementation detail — only consumed by HybridRepository)

### Query Field Naming (D-06)

- **D-06a:** Agent-friendly names throughout: `project` (name for partial match), `tags` (tag names), `availability` (enum strings)
- **D-06b:** Service resolves names to IDs where needed (e.g., tag names → tag IDs). The query model is shared across layers — same `list[str]` field carries names at input and IDs after service resolution
- **D-06c:** `inbox` renamed to `in_inbox` to match the existing Task model field name

### Method Signatures — Flat at Server, Query Object at Protocol (D-07)

- **D-07a:** Server tool functions take flat params (natural for agents): `list_tasks(flagged=True, limit=10)`
- **D-07b:** Protocol/service methods take a query object: `list_tasks(query: ListTasksQuery) -> ListResult[Task]`
- **D-07c:** Server wraps flat params into the query model before passing to service — same pattern as write tools (server accepts agent-friendly input, wraps in typed object, delegates)
- **D-07d:** FastMCP generates the tool schema from the flat function signature

### Query Module Organization (D-08)

- **D-08a:** All query models + ListResult live in `contracts/use_cases/list_entities.py` — a single file for the "list entities" use case
- **D-08b:** One file because query models are shared across layers (no separate repo-boundary versions), so each entity is just one small model
- **D-08c:** Follows the refactored `contracts/` structure:
  ```
  contracts/
      base.py              -- StrictModel, CommandModel, QueryModel, UNSET
      protocols.py         -- Service, Repository, Bridge protocols
      shared/
          actions.py       -- TagAction, MoveAction (was common.py)
          repetition_rule.py -- RepetitionRule specs (moved from use_cases/)
      use_cases/
          add_task.py      -- AddTask* models
          edit_task.py     -- EditTask* models
          list_entities.py -- ListTasksQuery, ListProjectsQuery, ListTagsQuery,
                              ListFoldersQuery, ListResult[T]  (NEW)
  ```

### Perspectives Signature (D-09)

- **D-09a:** `list_perspectives()` takes no query model — no filters, YAGNI
- **D-09b:** Protocol: `async def list_perspectives(self) -> ListResult[Perspective]`
- **D-09c:** If filters are added in a future milestone, a query model can be introduced then

### Count-Only Requests (D-10)

- **D-10a:** `limit=0` is valid and acts as a count-only request
- **D-10b:** Returns `{items: [], total: N, hasMore: true/false}` — total reflects all matching entities
- **D-10c:** SQL can optimize `limit=0` to `SELECT COUNT(*)` instead of fetching rows

### Dropped Filter: has_children (D-11)

- **D-11a:** `has_children` filter dropped from `list_tasks` — no clear agent use case identified
- **D-11b:** TASK-05 requirement deferred to a future milestone
- **D-11c:** Can be added later if an actual use case emerges

### Tool Signatures (D-12)

Final server-level signatures for all 5 list tools:

```python
# list_tasks — 9 optional filter params
async def list_tasks(
    ctx: Context,
    in_inbox: bool | None = None,
    flagged: bool | None = None,
    project: str | None = None,
    tags: list[str] | None = None,
    estimated_minutes_max: int | None = None,
    availability: list[str] | None = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> ListResult[Task]: ...

# list_projects — 5 optional filter params
async def list_projects(
    ctx: Context,
    availability: list[str] | None = None,
    folder: str | None = None,
    review_due_within: str | None = None,
    flagged: bool | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> ListResult[Project]: ...

# list_tags — 1 optional filter param
async def list_tags(
    ctx: Context,
    availability: list[str] | None = None,
) -> ListResult[Tag]: ...

# list_folders — 1 optional filter param
async def list_folders(
    ctx: Context,
    availability: list[str] | None = None,
) -> ListResult[Folder]: ...

# list_perspectives — no params
async def list_perspectives(
    ctx: Context,
) -> ListResult[Perspective]: ...
```

### Claude's Discretion

- Query builder return type (NamedTuple, tuple, dataclass — implementation detail)
- Internal organization of query_builder.py (function grouping, helper patterns)
- Exact `hasMore` computation formula (likely `offset + len(items) < total`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `docs/architecture.md` — Full model taxonomy (CQRS naming, QueryModel base, ListResult[T] definition, "Why query models are shared across layers", Scenario D example). Protocol definitions. Package structure.
- `docs/architecture.md` §Show-More Principle — Inclusion-biased tiebreaker for ambiguous filter boundaries

### Specifications
- `.research/updated-spec/MILESTONE-v1.3.md` — Original milestone spec. **NOTE:** Deviations captured in this context file:
  - Project `status` filter with shorthands → replaced by uniform `availability` list (D-03)
  - `has_children` task filter → dropped (D-11)
  - `count_tasks`/`count_projects` standalone tools → already removed (total_count in ListResult)
- `.planning/REQUIREMENTS.md` — v1.3 requirements. TASK-05 (has_children) deferred per D-11

### Existing Code (patterns to follow)
- `src/omnifocus_operator/models/enums.py` — Availability, TagAvailability, FolderAvailability enum definitions (entity-specific values for D-03)
- `src/omnifocus_operator/contracts/protocols.py` — Current Repository/Service protocols to extend (D-04)
- `src/omnifocus_operator/contracts/base.py` — StrictModel, CommandModel, QueryModel (documented but not yet created) base classes
- `src/omnifocus_operator/server.py` — Existing tool registration pattern (flat params, ToolAnnotations, readOnlyHint)
- `src/omnifocus_operator/repository/hybrid.py` — Existing SQL patterns (base queries, parameterized WHERE, row mappers)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OmniFocusBaseModel` (models/base.py): Base for ListResult[T] — camelCase serialization via `alias_generator=to_camel`
- `StrictModel` / `CommandModel` (contracts/base.py): Pattern for QueryModel — `extra="forbid"` rejects unknown fields. **QueryModel is documented in architecture.md but not yet created** — Phase 34 creates it
- Availability enums (models/enums.py): Entity-specific enums already exist with the exact values needed for filter defaults
- `_format_validation_errors` (server.py): Existing validation error formatting for agent-friendly messages — reusable for query validation errors
- `test_output_schema.py`: Existing output schema regression test — must pass for ListResult[T] serialization

### Established Patterns
- **Server → Service → Repository**: Three-layer architecture. Server wraps input → service processes → repository executes
- **camelCase serialization**: All models use `alias_generator=to_camel` for JSON output. `has_more` → `hasMore`, `in_inbox` → `inInbox`
- **Query models shared across layers**: Architecture doc explicitly documents this — no separate repo-boundary query model needed
- **Parameterized SQL**: Existing single-entity lookups use `?` placeholders with tuple params. Query builder extends this pattern

### Integration Points
- `contracts/protocols.py`: Add list method signatures to Repository and Service protocols
- `contracts/use_cases/list_entities.py`: New file — query models + ListResult
- `repository/query_builder.py`: New file — pure SQL generation functions
- `contracts/base.py`: Create QueryModel base class (documented, not yet implemented)

</code_context>

<specifics>
## Specific Ideas

### Spec Deviations Summary
Three deviations from MILESTONE-v1.3.md, all simplifications:
1. **Availability replaces status** — uniform `availability` list filter for all entities instead of project-specific `status` with shorthands. Same expressiveness, fewer concepts.
2. **has_children dropped** — TASK-05 deferred, no agent use case identified
3. **No shorthands** — agents pass concrete availability enum values, no `remaining`/`available`/`all` expansion

### Default Behavior Principle
The split between "model defaults" and "service resolution" is the key architectural insight:
- **Model**: defines what happens when a field is omitted (contract concern)
- **Service**: resolves agent-friendly values into implementation-ready values (domain concern)
- **Repository**: receives only concrete, resolved values (implementation concern)

This keeps each layer's responsibility clean and matches the existing write pipeline pattern.

</specifics>

<deferred>
## Deferred Ideas

- **has_children filter** (TASK-05) — dropped from v1.3. Add if a real agent use case emerges.
- **Status shorthands** (remaining, available, all) — replaced by concrete availability values. Could be reconsidered if agents frequently need to type `["available", "blocked"]` and it becomes friction.
- **Standalone count tools** (count_tasks, count_projects) — already decided out of scope; `limit=0` with `total` field covers the use case.

### Reviewed Todos (not folded)
All 7 matched todos were write-path concerns, not relevant to read-side query contracts:
- "Add position field to expose child task ordering" — models area, but write/display concern
- "Enforce mutually exclusive tags at service layer" — service, write-path
- "Return full task object in edit_tasks response" — service, write-path
- "Move no-op warning check ordinal position" — service, write-path
- "Migrate write tools to typed params" — server, write-path
- "Fix same-container move" — service, write-path
- "Remove misleading single runtime dependency messaging" — docs

</deferred>

---

*Phase: 34-contracts-and-query-foundation*
*Context gathered: 2026-03-29*
