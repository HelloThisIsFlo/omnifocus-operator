# Requirements: OmniFocus Operator

**Defined:** 2026-03-07
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.1 Requirements

Requirements for v1.1 HUGE Performance Upgrade. Each maps to roadmap phases.

**Model spec source of truth:** `.research/deep-dives/direct-database-access/RESULTS_pydantic-model.md`

### Data Models

- [x] **MODEL-01**: Task and Project expose `urgency` field (overdue / due_soon / none) instead of single-winner status enum
- [x] **MODEL-02**: Task and Project expose `availability` field (available / blocked / completed / dropped) instead of single-winner status enum
- [x] **MODEL-03**: `TaskStatus` and `ProjectStatus` enums are removed and replaced by shared `Urgency` and `Availability` enums
- [x] **MODEL-04**: Fields `active`, `effective_active`, `completed` (bool), `sequential`, `completed_by_children`, `should_use_floating_time_zone` are removed from entity models
- [x] **MODEL-05**: `contains_singleton_actions` removed from Project, `allows_next_action` removed from Tag
- [x] **MODEL-06**: All existing tests and fixtures updated to reflect new model shape

### SQLite Read Path

- [ ] **SQLITE-01**: Server reads OmniFocus data from SQLite cache at the documented path (~46ms full snapshot)
- [ ] **SQLITE-02**: SQLite reader opens connections in read-only mode (`?mode=ro`) and creates a fresh connection per read
- [ ] **SQLITE-03**: SQLite reader maps database rows to Pydantic models with two-axis status (urgency + availability from pre-computed columns)
- [ ] **SQLITE-04**: OmniFocus does not need to be running for reads to succeed

### Freshness

- [ ] **FRESH-01**: After a bridge write, server detects SQLite staleness via WAL file `st_mtime_ns` and waits for fresh data (poll every 50ms, 2s timeout)
- [ ] **FRESH-02**: When WAL file does not exist (clean OmniFocus shutdown), freshness detection falls back to main `.db` file mtime

### Fallback

- [ ] **FALL-01**: Setting `OMNIFOCUS_BRIDGE=omnijs` env var switches read path from SQLite to OmniJS bridge
- [ ] **FALL-02**: In OmniJS fallback mode, urgency is fully populated; availability is reduced to `available` / `completed` / `dropped` (no `blocked`)
- [ ] **FALL-03**: When SQLite database is not found, server enters error-serving mode with actionable message including the expected path and instructions to set `OMNIFOCUS_BRIDGE=omnijs` as a quick fallback

### Architecture

- [ ] **ARCH-01**: DataSource protocol abstracts the read path so SQLite and Bridge implementations are swappable
- [ ] **ARCH-02**: Repository layer consumes DataSource protocol instead of Bridge + MtimeSource directly
- [ ] **ARCH-03**: InMemoryDataSource implementation exists for testing

## Future Requirements

Deferred to v1.2+ milestones.

### Filtering

- **FILT-01**: Server supports filtering tasks by status, project, tag, due date
- **FILT-02**: Server supports filtering projects by status, folder
- **FILT-03**: Filtered queries leverage SQLite indexes (<6ms)

### Entity Browsing

- **BROWSE-01**: Dedicated tools for individual entity types (tasks, projects, tags, folders)
- **BROWSE-02**: Entity detail views with related entities

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automatic SQLite-to-OmniJS failover | Silent fallback hides broken state; user must know which path is active |
| SQLite write path | OmniFocus owns the database; writing to its cache corrupts state |
| Caching layer on top of SQLite | 46ms full snapshot is fast enough; caching adds complexity for no gain |
| `next` availability value | Not present in SQLite or OmniJS; niche use case |
| Partial/incremental SQLite reads | Full snapshot is 46ms; incremental adds complexity at current scale |
| Schema migration / version detection | OmniFocus SQLite schema stable since OF1 (2008); breakage is path changes, not schema |
| `completed` boolean alongside `availability` | Redundant -- derive from `availability == completed` or `completion_date is not None` |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MODEL-01 | Phase 10 | Complete |
| MODEL-02 | Phase 10 | Complete |
| MODEL-03 | Phase 10 | Complete |
| MODEL-04 | Phase 10 | Complete |
| MODEL-05 | Phase 10 | Complete |
| MODEL-06 | Phase 10 | Complete |
| SQLITE-01 | Phase 12 | Pending |
| SQLITE-02 | Phase 12 | Pending |
| SQLITE-03 | Phase 12 | Pending |
| SQLITE-04 | Phase 12 | Pending |
| FRESH-01 | Phase 12 | Pending |
| FRESH-02 | Phase 12 | Pending |
| FALL-01 | Phase 13 | Pending |
| FALL-02 | Phase 13 | Pending |
| FALL-03 | Phase 13 | Pending |
| ARCH-01 | Phase 11 | Pending |
| ARCH-02 | Phase 11 | Pending |
| ARCH-03 | Phase 11 | Pending |

**Coverage:**
- v1.1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-03-07*
*Last updated: 2026-03-07 after roadmap creation*
