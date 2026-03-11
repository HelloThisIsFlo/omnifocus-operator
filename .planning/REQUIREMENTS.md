# Requirements: OmniFocus Operator v1.2

**Defined:** 2026-03-07
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.2 Requirements

Requirements for Writes & Lookups milestone. Each maps to roadmap phases.

### Naming

- [x] **NAME-01**: MCP tool renamed from `list_all` to `get_all` to match repository/service nomenclature (`getAll` = single composite entity, not a flat list)

### Lookups

- [x] **LOOK-01**: Agent can look up a single task by ID and receive the full Task object (including urgency/availability)
- [x] **LOOK-02**: Agent can look up a single project by ID and receive the full Project object
- [x] **LOOK-03**: Agent can look up a single tag by ID and receive the full Tag object
- [x] **LOOK-04**: Looking up a non-existent ID returns a clear "not found" error message

### Models

- [x] **MODL-01**: Task read model replaces `project` + `parent` fields with unified `parent: { type, id } | null` (type = project or task; null = inbox)
- [x] **MODL-02**: All existing Pydantic models, adapters, and serialization updated for the new parent structure

### Task Creation

- [x] **CREA-01**: Agent can create a task with a name (minimum required field)
- [x] **CREA-02**: Agent can assign a task to a parent (project ID or task ID); server resolves the type
- [x] **CREA-03**: Agent can set tags, due_date, defer_date, planned_date, flagged, estimated_minutes, note on creation
- [x] **CREA-04**: Task with no parent (or parent omitted) goes to inbox
- [x] **CREA-05**: Service validates inputs before bridge execution (name required, parent ID exists, tags exist)
- [x] **CREA-06**: Tool returns per-item result with success status, created ID, and name
- [x] **CREA-07**: API accepts arrays (`add_tasks([...])`) with single-item constraint initially
- [x] **CREA-08**: Snapshot is invalidated after successful write; next read returns fresh data

### Task Editing

- [x] **EDIT-01**: Agent can edit task fields using patch semantics (omit = no change, null = clear, value = set)
- [x] **EDIT-02**: Agent can edit: name, note, due_date, defer_date, planned_date, flagged, estimated_minutes
- [x] **EDIT-03**: Agent can replace all tags on a task (`tags: [...]`)
- [x] **EDIT-04**: Agent can add tags without removing existing (`add_tags: [...]`)
- [x] **EDIT-05**: Agent can remove specific tags (`remove_tags: [...]`)
- [x] **EDIT-06**: Mutually exclusive tag modes are validated (`tags` vs `add_tags`/`remove_tags`)
- [x] **EDIT-07**: Agent can move a task to a different parent (`parent: id` -- project or task, server resolves)
- [x] **EDIT-08**: Agent can move a task to inbox (`parent: null`)
- [x] **EDIT-09**: API accepts arrays (`edit_tasks([...])`) with single-item constraint initially

### Task Lifecycle

- [x] **LIFE-01**: Agent can mark a task as complete via edit_tasks
- [x] **LIFE-02**: Agent can drop a task via edit_tasks
- [x] **LIFE-03**: Agent can reactivate a completed task via edit_tasks
- [x] **LIFE-04**: Lifecycle interface design is resolved via research spike on OmniJS APIs
- [x] **LIFE-05**: Edge cases documented: repeating tasks, dropped task reactivation limits

## Future Requirements

### Read Tools (v1.3)

- **READ-01**: SQL filtering for tasks, projects, tags
- **READ-02**: list/count for all entities
- **READ-03**: Substring search

### Output, UI & Remaining Tools (v1.4)

- **OUTP-01**: Perspectives support
- **OUTP-02**: Field selection
- **OUTP-03**: TaskPaper output format
- **OUTP-04**: Project writes (add_projects, edit_projects)
- **OUTP-05**: delete_tasks

### Production Hardening (v1.5)

- **HARD-01**: Retry logic for bridge timeouts
- **HARD-02**: Crash recovery
- **HARD-03**: Fuzzy search
- **HARD-04**: App Nap mitigation

## Out of Scope

| Feature | Reason |
|---------|--------|
| SQLite write path | OmniFocus owns the database; direct writes corrupt state |
| True batch (multi-item) execution | No OmniJS transactions; partial failures unrecoverable. Prove single-item first |
| Rollback / undo support | `document.undo()` is fragile; not a real transaction mechanism |
| Dry run / preview mode | Validation catches most errors; unclear benefit vs complexity |
| delete_tasks | Deferred to v1.4; `drop` + `edit_tasks` with movement handles most cases |
| Project writes | Unverified OmniJS APIs; low priority for current workflow |
| Tag/folder writes | Low priority; tags created manually |
| Idempotency / retry logic | Production hardening (v1.5); v1.2 proves the pipeline |
| Optimistic concurrency | Overkill for single-user local MCP server |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| NAME-01 | Phase 14 | Complete |
| LOOK-01 | Phase 14 | Complete |
| LOOK-02 | Phase 14 | Complete |
| LOOK-03 | Phase 14 | Complete |
| LOOK-04 | Phase 14 | Complete |
| MODL-01 | Phase 14 | Complete |
| MODL-02 | Phase 14 | Complete |
| CREA-01 | Phase 15 | Complete |
| CREA-02 | Phase 15 | Complete |
| CREA-03 | Phase 15 | Complete |
| CREA-04 | Phase 15 | Complete |
| CREA-05 | Phase 15 | Complete |
| CREA-06 | Phase 15 | Complete |
| CREA-07 | Phase 15 | Complete |
| CREA-08 | Phase 15 | Complete |
| EDIT-01 | Phase 16 | Complete |
| EDIT-02 | Phase 16 | Complete |
| EDIT-03 | Phase 16 | Complete |
| EDIT-04 | Phase 16 | Complete |
| EDIT-05 | Phase 16 | Complete |
| EDIT-06 | Phase 16 | Complete |
| EDIT-07 | Phase 16 | Complete |
| EDIT-08 | Phase 16 | Complete |
| EDIT-09 | Phase 16 | Complete |
| LIFE-01 | Phase 17 | Complete |
| LIFE-02 | Phase 17 | Complete |
| LIFE-03 | Phase 17 | Complete |
| LIFE-04 | Phase 17 | Complete |
| LIFE-05 | Phase 17 | Complete |

**Coverage:**
- v1.2 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0

---
*Requirements defined: 2026-03-07*
*Last updated: 2026-03-07 after roadmap creation*
