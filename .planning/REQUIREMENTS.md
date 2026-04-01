# Requirements: OmniFocus Operator v1.3

**Defined:** 2026-03-29
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.3 Requirements

Requirements for the Read Tools milestone. Each maps to roadmap phases.

### Task Querying

- [x] **TASK-01**: Agent can list tasks filtered by inbox status
- [x] **TASK-02**: Agent can list tasks filtered by flagged status
- [x] **TASK-03**: Agent can list tasks filtered by project name (case-insensitive partial match, returns all tasks at any nesting depth within matching project)
- [x] **TASK-04**: Agent can list tasks filtered by tags (OR logic -- at least one matching tag)
- [x] **TASK-06**: Agent can list tasks filtered by estimated_minutes_max
- [x] **TASK-07**: Agent can list tasks filtered by availability (available/blocked)
- [x] **TASK-08**: Agent can search tasks by case-insensitive substring in name and notes
- [x] **TASK-09**: Agent can paginate task results with limit and offset (offset requires limit)
- [x] **TASK-10**: Agent can combine multiple task filters with AND logic
- [x] **TASK-11**: Completed/dropped tasks excluded from task list results by default

### Project Querying

- [x] **PROJ-01**: Agent can list projects filtered by availability list (available, blocked, completed, dropped) with OR logic (Phase 34 D-03: replaces original status filter with uniform availability across all entities)
- [x] **PROJ-02**: Default project listing returns available + blocked, excluding completed/dropped (Phase 34 D-03: uniform defaults across all entities; supersedes original PROJ-02 status shorthands and PROJ-03 default behavior)
- [x] **PROJ-04**: Agent can list projects filtered by folder name (case-insensitive partial match)
- [x] **PROJ-05**: Agent can list projects with reviews due within a duration (now, 1w, 2m); invalid values return helpful error messages
- [x] **PROJ-06**: Agent can list projects filtered by flagged status
- [x] **PROJ-07**: Agent can paginate project results with limit and offset

### Entity Browsing

- [x] **BROWSE-01**: Agent can list tags filtered by status list with OR logic (active, on_hold, dropped); defaults to remaining (active + on_hold)
- [x] **BROWSE-02**: Agent can list folders filtered by status list with OR logic; defaults to remaining (active + on_hold)
- [x] **BROWSE-03**: Agent can list all perspectives (built-in + custom) with id, name, builtin flag

### Entity Search

- [ ] **SRCH-01**: Agent can search projects by case-insensitive substring in name and notes — same implementation as TASK-08
- [ ] **SRCH-02**: Agent can search tags by case-insensitive substring in name — same implementation as TASK-08 (name only, tags have no notes)
- [ ] **SRCH-03**: Agent can search folders by case-insensitive substring in name — same implementation as TASK-08 (name only, folders have no notes)
- [ ] **SRCH-04**: Agent can search perspectives by case-insensitive substring in name — same implementation as TASK-08 (name only). Requires introducing `ListPerspectivesQuery` / `ListPerspectivesRepoQuery`.

### Write Tool Schema & Validation

- [x] **WRIT-01**: `add_tasks` inputSchema exposes all `AddTaskCommand` fields with types, enums, and constraints (52+ schema entries vs current 2)
- [x] **WRIT-02**: `edit_tasks` inputSchema exposes all `EditTaskCommand` fields with types, enums, and constraints (61+ schema entries vs current 2)
- [x] **WRIT-03**: Schema field names use camelCase aliases matching the existing API contract (no snake_case leakage)
- [x] **WRIT-04**: Validation errors use `"Task N: field"` location format (readable for agents, scales to future batches)
- [x] **WRIT-05**: UNSET sentinel noise filtered from validation errors (no `_Unset` artifacts in agent-facing messages)
- [x] **WRIT-06**: Unknown fields produce `"Unknown field '<name>'"` error messages
- [x] **WRIT-07**: Validation errors surface as `ToolError` with clean, agent-readable messages (no raw Pydantic output)
- [x] **WRIT-08**: All previously valid `add_tasks` / `edit_tasks` inputs produce identical results (no functional regression)
- [x] **WRIT-09**: Error messages maintain functional parity with pre-migration output and remain agent-friendly -- no internal model names, Pydantic internals, or implementation details leak into validation errors or warnings
- [x] **WRIT-10**: Validation errors are logged by the tool logger with timing and the reformatted error
- [x] **WRIT-11**: Canary test detects if a FastMCP upgrade moves validation outside the middleware chain -- with clear failure message explaining what broke and what to do

### Agent-Facing Documentation

- [x] **DOC-01**: Model docstrings visible in JSON Schema contain no implementation details — no references to validators, `extra='forbid'`, CommandModel, service layer, bridge internals, UNSET, or Patch/PatchOrClear
- [x] **DOC-02**: Write tool docstrings (add_tasks, edit_tasks) use approved verbatim text from CONTEXT.md — no field-by-field listings redundant with inputSchema
- [x] **DOC-03**: All three date fields (dueDate, deferDate, plannedDate) have `Field(description=...)` on both write-side commands and read-side models, faithful to `docs/omnifocus-concepts.md`
- [x] **DOC-04**: Tag resolution behavior (names or IDs, case-insensitive, non-existent rejected, ambiguous errors) documented in tool descriptions and on tag-accepting fields via `Field(description=...)`
- [x] **DOC-05**: Timezone requirement (ISO 8601 with offset or Z, naive rejected) documented in tool descriptions and on date `Field(description=...)`
- [x] **DOC-06**: Partial repetitionRule on task with no existing rule documented in edit_tasks tool description (all three root fields required when no rule exists)
- [x] **DOC-07**: All four read tool descriptions include camelCase field names note and hint at response shape (key non-obvious fields)
- [x] **DOC-08**: `Field(description=...)` added to read-side model fields that fail the fluency test — at minimum: `effective_due_date`, `effective_defer_date`, `effective_planned_date`, `effective_flagged`, `children_are_mutually_exclusive`, `next_task`
- [x] **DOC-09**: No Python conventions leak into JSON-facing schema descriptions — `None` → `null`, no UNSET references, no validator/model-internal language

### Description Centralization

- [x] **DESC-01**: `agent_messages/descriptions.py` exists with domain-organized constants following the errors.py/warnings.py pattern (comment headers, UPPER_SNAKE_CASE, module docstring)
- [x] **DESC-02**: All agent-visible `Field(description=...)` on models/ and contracts/ use constants imported from `descriptions.py` — no inline string literals in `Field(description=)` calls on agent-facing models
- [x] **DESC-03**: All agent-visible class docstrings use `__doc__ = CONSTANT` pattern with constants from `descriptions.py` — no inline docstrings on agent-facing classes
- [x] **DESC-04**: Every constant in `descriptions.py` is a non-empty string and is referenced in at least one consumer module (no dead constants)
- [x] **DESC-05**: JSON Schema output is identical before and after centralization — no functional regression (both inputSchema from tool registration and model_json_schema() on output models)
- [x] **DESC-06**: Enforcement test scans all classes in `models/` and `contracts/` with an exception list for known internal classes — new classes default to "must use centralized descriptions" unless explicitly excepted
- [ ] **DESC-07**: All `@mcp.tool()` function docstrings in `server.py` use constants from `descriptions.py` — no inline tool description strings. Enforcement test catches new tools with inline docstrings.
- [ ] **DESC-08**: All tool descriptions are at most 2048 bytes — Claude Code truncates at 2KB. Enforcement test checks each tool description constant's UTF-8 byte length and fails with the exact byte count if exceeded.

### Type Constraint Boundary

- [ ] **TYPE-01**: `FrequencyType`, `DayCode`, `OnDate`, `DayName` type aliases defined in `contracts/shared/repetition_rule.py`, not in `models/repetition_rule.py`
- [ ] **TYPE-02**: Core model `Frequency.type` uses plain `str`, not `FrequencyType` Literal
- [ ] **TYPE-03**: Core model `OrdinalWeekday` fields (`first` through `last`) use `str | None`, not `DayName | None`
- [ ] **TYPE-04**: `_VALID_DAY_NAMES` in `models/repetition_rule.py` is a plain set literal, not derived from `DayName.__args__`
- [ ] **TYPE-05**: Contract fields `FrequencyAddSpec.interval` and `EndByOccurrences.occurrences` advertise `minimum: 1` in JSON Schema via `Annotated[int, Field(ge=1)]`
- [ ] **TYPE-06**: `docs/model-taxonomy.md` documents the Literal/Annotated convention: constraint types on contract models, plain types on core models
- [ ] **TYPE-07**: AST enforcement test scans `models/` for `Literal` and `Annotated` field annotations in class bodies and fails if found (with exception list for known acceptable cases)

### List Tool Documentation

- [ ] **DOC-10**: List tool docstrings contain behavioral guidance only — filter interaction rules (AND logic, defaults, mutual exclusivity), response shape, pagination behavior — no field-by-field listings redundant with inputSchema
- [ ] **DOC-11**: List tool query model fields have `Field(description=...)` where the fluency test fails — field name + type leave ambiguity about behavior or valid values (same filter as DOC-03/DOC-08)
- [ ] **DOC-12**: All list tool descriptions include camelCase response field names note and hint at response structure (consistent with DOC-07 on read tools)
- [ ] **DOC-13**: No implementation details leak into list tool query model docstrings or field descriptions — no references to RepoQuery, pipelines, resolution cascades, or SQL internals
- [ ] **DOC-14**: List tool query model field descriptions and class docstrings use constants from `descriptions.py` — extends DESC-02/DESC-03 to new models added in Phase 37

### Read Tool Registration

- [ ] **RTOOL-01**: `list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives` use typed query model parameters -- rich inputSchema auto-generated from query models (not `dict[str, Any]`)
- [ ] **RTOOL-02**: Schema field names use camelCase aliases matching the API contract across all read tools
- [ ] **RTOOL-03**: Validation errors on read tools are agent-friendly via `ValidationReformatterMiddleware` -- consistent error surface across read and write tools

### Query Infrastructure

- [x] **INFRA-01**: SQL queries use parameterized values (no SQL injection)
- [x] **INFRA-02**: Filtered SQL queries measurably faster than full snapshot (<6ms vs ~46ms)
- [x] **INFRA-03**: Bridge fallback produces identical results to SQL path for same filters
- [x] **INFRA-04**: list_tasks and list_projects responses include total_count reflecting total matches ignoring limit/offset
- [ ] **INFRA-05**: Tool descriptions detailed enough for an LLM to call correctly
- [x] **INFRA-06**: Educational error messages for invalid filter values
- [x] **INFRA-07**: When a name-based filter (project, folder, tags) returns zero results, emit a "did you mean?" warning with close matches from the full entity list — see [design todo](../todos/pending/2026-03-30-add-did-you-mean-suggestions-for-zero-result-name-filters.md)
- [x] **INFRA-08**: Read-side contracts split at the service boundary — agent-facing query models (`List<Noun>Query`) and repo-facing query models (`List<Noun>RepoQuery`) are separate types for tasks, projects, tags, and folders
- [x] **INFRA-09**: Read-side result containers split at the service boundary — `ListResult[T]` (agent-facing) and `ListRepoResult[T]` (repo-facing) are separate generic types
- [x] **INFRA-10**: Repository protocol signatures use repo-boundary types (`RepoQuery`/`ListRepoResult`), Service protocol signatures use agent-boundary types (`Query`/`ListResult`)
- [x] **INFRA-11**: `contracts/use_cases/` organized into per-use-case packages (`list/`, `add/`, `edit/`) with all imports updated to new paths
- [x] **INFRA-12**: Service layer resolves all name-based filter values (project, folder, tags) to entity IDs before passing to the repository — resolution cascade: ID match → substring match (case-insensitive) → no match (skip filter + warn)
- [x] **INFRA-13**: Agent can pass either a name or an ID in any entity-reference filter field — the service resolves both uniformly (ID match takes priority, then substring match)
- [x] **INFRA-14**: RepoQuery models use ID-only fields (`project_ids: list[str]`, `folder_ids: list[str]`, `tag_ids: list[str]`) — no name strings cross the repository boundary
- [x] **INFRA-15**: `ListResult[T]` includes an optional `warnings: list[str] | None` field for attaching agent guidance (e.g., "did you mean?" suggestions)
- [x] **INFRA-16**: Service list methods for all 5 entity types are callable (not `NotImplementedError`) — tasks and projects via pipelines with resolution, tags/folders/perspectives via inline pass-throughs

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Date Filtering (v1.3.1)

- **DATE-01**: Agent can filter tasks by due date range
- **DATE-02**: Agent can filter tasks by defer date range
- **DATE-03**: Agent can filter tasks by completion date range
- **DATE-04**: Agent can filter tasks by added/modified date
- **DATE-05**: Agent can filter projects by date ranges

### Task Filtering (deferred from v1.3)

- **TASK-05**: Agent can list tasks filtered by has_children (parent tasks vs leaf tasks) — deferred per Phase 34 D-11, no clear agent use case identified

### Search & Output (v1.4+)

- **SEARCH-01**: Agent can fuzzy search tasks (v1.4.1)
- **OUTPUT-01**: Agent can select specific fields in list responses (v1.4)
- **OUTPUT-02**: Agent can get TaskPaper format output (v1.4.2)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Standalone count tools (count_tasks, count_projects) | total_count embedded in ListResult makes these redundant |
| Full-text search (FTS5) | Requires writable DB, overkill at current scale |
| Custom SQLite indexes | Read-only database; full scans <5ms at current scale |
| Nested/hierarchical responses | Spec says flat with ID references |
| ORDER BY configuration | Hardcode deterministic order; not in spec |
| Fuzzy search | Different algorithm from LIKE; deferred to v1.4.1 |
| Date-based filtering | Deferred to v1.3.1; WHERE clause infrastructure built now |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TASK-01 | Phase 35 | Complete |
| TASK-02 | Phase 35 | Complete |
| TASK-03 | Phase 35 | Complete |
| TASK-04 | Phase 35 | Complete |
| TASK-06 | Phase 35 | Complete |
| TASK-07 | Phase 35 | Complete |
| TASK-08 | Phase 35 | Complete |
| TASK-09 | Phase 35 | Complete |
| TASK-10 | Phase 35 | Complete |
| TASK-11 | Phase 35 | Complete |
| PROJ-01 | Phase 35 | Complete |
| PROJ-02 | Phase 35 | Complete |
| PROJ-04 | Phase 35 | Complete |
| PROJ-05 | Phase 35 | Complete |
| PROJ-06 | Phase 35 | Complete |
| PROJ-07 | Phase 35 | Complete |
| BROWSE-01 | Phase 35 | Complete |
| BROWSE-02 | Phase 35 | Complete |
| BROWSE-03 | Phase 35 | Complete |
| INFRA-01 | Phase 34 | Complete |
| INFRA-02 | Phase 35 | Complete |
| INFRA-03 | Phase 36 (merged) | Complete |
| INFRA-04 | Phase 34 | Complete |
| INFRA-05 | Phase 37 (was 38) | Pending |
| SRCH-01 | Phase 37 | Pending |
| SRCH-02 | Phase 37 | Pending |
| SRCH-03 | Phase 37 | Pending |
| SRCH-04 | Phase 37 | Pending |
| INFRA-06 | Phase 36 (merged) | Complete |
| INFRA-07 | Phase 35.2 | Complete |
| INFRA-08 | Phase 35.1 | Complete |
| INFRA-09 | Phase 35.1 | Complete |
| INFRA-10 | Phase 35.1 | Complete |
| INFRA-11 | Phase 35.1 | Complete |
| INFRA-12 | Phase 35.2 | Complete |
| INFRA-13 | Phase 35.2 | Complete |
| INFRA-14 | Phase 35.2 | Complete |
| INFRA-15 | Phase 35.2 | Complete |
| INFRA-16 | Phase 35.2 | Complete |
| WRIT-01 | Phase 36.1 | Complete |
| WRIT-02 | Phase 36.1 | Complete |
| WRIT-03 | Phase 36.1 | Complete |
| WRIT-04 | Phase 36.1 | Complete |
| WRIT-05 | Phase 36.1 | Complete |
| WRIT-06 | Phase 36.1 | Complete |
| WRIT-07 | Phase 36.1 | Complete |
| WRIT-08 | Phase 36.1 | Complete |
| WRIT-09 | Phase 36.1 | Complete |
| WRIT-10 | Phase 36.1 | Complete |
| WRIT-11 | Phase 36.1 | Complete |
| RTOOL-01 | Phase 37 | Pending |
| RTOOL-02 | Phase 37 | Pending |
| RTOOL-03 | Phase 37 | Pending |
| DOC-01 | Phase 36.2 | Complete |
| DOC-02 | Phase 36.2 | Complete |
| DOC-03 | Phase 36.2 | Complete |
| DOC-04 | Phase 36.2 | Complete |
| DOC-05 | Phase 36.2 | Complete |
| DOC-06 | Phase 36.2 | Complete |
| DOC-07 | Phase 36.2 | Complete |
| DOC-08 | Phase 36.2 | Complete |
| DOC-09 | Phase 36.2 | Complete |
| DESC-01 | Phase 36.3 | Complete |
| DESC-02 | Phase 36.3 | Complete |
| DESC-03 | Phase 36.3 | Complete |
| DESC-04 | Phase 36.3 | Complete |
| DESC-05 | Phase 36.3 | Complete |
| DESC-06 | Phase 36.3 | Complete |
| DESC-07 | Phase 36.3 | Pending |
| DESC-08 | Phase 36.3 | Pending |
| TYPE-01 | Phase 36.4 | Pending |
| TYPE-02 | Phase 36.4 | Pending |
| TYPE-03 | Phase 36.4 | Pending |
| TYPE-04 | Phase 36.4 | Pending |
| TYPE-05 | Phase 36.4 | Pending |
| TYPE-06 | Phase 36.4 | Pending |
| TYPE-07 | Phase 36.4 | Pending |
| DOC-10 | Phase 37 | Pending |
| DOC-11 | Phase 37 | Pending |
| DOC-12 | Phase 37 | Pending |
| DOC-13 | Phase 37 | Pending |
| DOC-14 | Phase 37 | Pending |

**Coverage:**
- v1.3 requirements: 80 total (PROJ-03 merged into PROJ-02, TASK-05 deferred, +4 SRCH, +11 WRIT, +3 RTOOL, +13 DOC, +1 DOC-14, +8 DESC, +7 TYPE)
- Mapped to phases: 78
- Unmapped: 0

---
*Requirements defined: 2026-03-29*
*Last updated: 2026-04-01 added TYPE-01..07 for Phase 36.4*
