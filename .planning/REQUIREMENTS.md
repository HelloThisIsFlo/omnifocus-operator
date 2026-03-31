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

**Coverage:**
- v1.3 requirements: 37 total (PROJ-03 merged into PROJ-02, TASK-05 deferred, +4 SRCH)
- Mapped to phases: 37
- Unmapped: 0

---
*Requirements defined: 2026-03-29*
*Last updated: 2026-03-31 added SRCH-01..04 entity search requirements for Phase 37*
