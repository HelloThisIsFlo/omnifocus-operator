# Requirements: OmniFocus Operator v1.3

**Defined:** 2026-03-29
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.3 Requirements

Requirements for the Read Tools milestone. Each maps to roadmap phases.

### Task Querying

- [ ] **TASK-01**: Agent can list tasks filtered by inbox status
- [ ] **TASK-02**: Agent can list tasks filtered by flagged status
- [ ] **TASK-03**: Agent can list tasks filtered by project name (case-insensitive partial match, returns all tasks at any nesting depth within matching project)
- [ ] **TASK-04**: Agent can list tasks filtered by tags (OR logic -- at least one matching tag)
- [ ] **TASK-05**: Agent can list tasks filtered by has_children (parent tasks vs leaf tasks)
- [ ] **TASK-06**: Agent can list tasks filtered by estimated_minutes_max
- [ ] **TASK-07**: Agent can list tasks filtered by availability (available/blocked)
- [ ] **TASK-08**: Agent can search tasks by case-insensitive substring in name and notes
- [ ] **TASK-09**: Agent can paginate task results with limit and offset (offset requires limit)
- [ ] **TASK-10**: Agent can combine multiple task filters with AND logic
- [ ] **TASK-11**: Completed/dropped tasks excluded from task list results by default

### Project Querying

- [ ] **PROJ-01**: Agent can list projects filtered by status (active, on_hold, done, dropped)
- [ ] **PROJ-02**: Agent can use status shorthands (remaining, available, all) for project listing
- [ ] **PROJ-03**: Default project listing returns remaining (active + on_hold), not done/dropped
- [ ] **PROJ-04**: Agent can list projects filtered by folder name (case-insensitive partial match)
- [ ] **PROJ-05**: Agent can list projects with reviews due within a duration (now, 1w, 2m); invalid values return helpful error messages
- [ ] **PROJ-06**: Agent can list projects filtered by flagged status
- [ ] **PROJ-07**: Agent can paginate project results with limit and offset

### Entity Browsing

- [ ] **BROWSE-01**: Agent can list tags filtered by status list with OR logic (active, on_hold, dropped); defaults to remaining (active + on_hold)
- [ ] **BROWSE-02**: Agent can list folders filtered by status list with OR logic; defaults to remaining (active + on_hold)
- [ ] **BROWSE-03**: Agent can list all perspectives (built-in + custom) with id, name, builtin flag

### Query Infrastructure

- [x] **INFRA-01**: SQL queries use parameterized values (no SQL injection)
- [ ] **INFRA-02**: Filtered SQL queries measurably faster than full snapshot (<6ms vs ~46ms)
- [ ] **INFRA-03**: Bridge fallback produces identical results to SQL path for same filters
- [x] **INFRA-04**: list_tasks and list_projects responses include total_count reflecting total matches ignoring limit/offset
- [ ] **INFRA-05**: Tool descriptions detailed enough for an LLM to call correctly
- [ ] **INFRA-06**: Educational error messages for invalid filter values

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Date Filtering (v1.3.1)

- **DATE-01**: Agent can filter tasks by due date range
- **DATE-02**: Agent can filter tasks by defer date range
- **DATE-03**: Agent can filter tasks by completion date range
- **DATE-04**: Agent can filter tasks by added/modified date
- **DATE-05**: Agent can filter projects by date ranges

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
| TASK-01 | Phase 35 | Pending |
| TASK-02 | Phase 35 | Pending |
| TASK-03 | Phase 35 | Pending |
| TASK-04 | Phase 35 | Pending |
| TASK-05 | Phase 35 | Pending |
| TASK-06 | Phase 35 | Pending |
| TASK-07 | Phase 35 | Pending |
| TASK-08 | Phase 35 | Pending |
| TASK-09 | Phase 35 | Pending |
| TASK-10 | Phase 35 | Pending |
| TASK-11 | Phase 35 | Pending |
| PROJ-01 | Phase 35 | Pending |
| PROJ-02 | Phase 35 | Pending |
| PROJ-03 | Phase 35 | Pending |
| PROJ-04 | Phase 35 | Pending |
| PROJ-05 | Phase 35 | Pending |
| PROJ-06 | Phase 35 | Pending |
| PROJ-07 | Phase 35 | Pending |
| BROWSE-01 | Phase 35 | Pending |
| BROWSE-02 | Phase 35 | Pending |
| BROWSE-03 | Phase 35 | Pending |
| INFRA-01 | Phase 34 | Complete |
| INFRA-02 | Phase 35 | Pending |
| INFRA-03 | Phase 36 | Pending |
| INFRA-04 | Phase 34 | Complete |
| INFRA-05 | Phase 38 | Pending |
| INFRA-06 | Phase 37 | Pending |

**Coverage:**
- v1.3 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-03-29*
*Last updated: 2026-03-29 after roadmap creation*
