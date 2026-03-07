# Requirements: OmniFocus Operator v1.2

**Defined:** 2026-03-07
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.2 Requirements

Requirements for Writes & Lookups milestone. Each maps to roadmap phases.

### Naming

- [ ] **NAME-01**: MCP tool renamed from `list_all` to `get_all` to match repository/service nomenclature (`getAll` = single composite entity, not a flat list)

### Lookups

- [ ] **LOOK-01**: Agent can look up a single task by ID and receive the full Task object (including urgency/availability)
- [ ] **LOOK-02**: Agent can look up a single project by ID and receive the full Project object
- [ ] **LOOK-03**: Agent can look up a single tag by ID and receive the full Tag object
- [ ] **LOOK-04**: Looking up a non-existent ID returns a clear "not found" error message

### Models

- [ ] **MODL-01**: Task read model replaces `project` + `parent` fields with unified `parent: { type, id } | null` (type = project or task; null = inbox)
- [ ] **MODL-02**: All existing Pydantic models, adapters, and serialization updated for the new parent structure

### Task Creation

- [ ] **CREA-01**: Agent can create a task with a name (minimum required field)
- [ ] **CREA-02**: Agent can assign a task to a parent (project ID or task ID); server resolves the type
- [ ] **CREA-03**: Agent can set tags, due_date, defer_date, planned_date, flagged, estimated_minutes, note on creation
- [ ] **CREA-04**: Task with no parent (or parent omitted) goes to inbox
- [ ] **CREA-05**: Service validates inputs before bridge execution (name required, parent ID exists, tags exist)
- [ ] **CREA-06**: Tool returns per-item result with success status, created ID, and name
- [ ] **CREA-07**: API accepts arrays (`add_tasks([...])`) with single-item constraint initially
- [ ] **CREA-08**: Snapshot is invalidated after successful write; next read returns fresh data

### Task Editing

- [ ] **EDIT-01**: Agent can edit task fields using patch semantics (omit = no change, null = clear, value = set)
- [ ] **EDIT-02**: Agent can edit: name, note, due_date, defer_date, planned_date, flagged, estimated_minutes
- [ ] **EDIT-03**: Agent can replace all tags on a task (`tags: [...]`)
- [ ] **EDIT-04**: Agent can add tags without removing existing (`add_tags: [...]`)
- [ ] **EDIT-05**: Agent can remove specific tags (`remove_tags: [...]`)
- [ ] **EDIT-06**: Mutually exclusive tag modes are validated (`tags` vs `add_tags`/`remove_tags`)
- [ ] **EDIT-07**: Agent can move a task to a different parent (`parent: id` -- project or task, server resolves)
- [ ] **EDIT-08**: Agent can move a task to inbox (`parent: null`)
- [ ] **EDIT-09**: API accepts arrays (`edit_tasks([...])`) with single-item constraint initially

### Task Lifecycle

- [ ] **LIFE-01**: Agent can mark a task as complete via edit_tasks
- [ ] **LIFE-02**: Agent can drop a task via edit_tasks
- [ ] **LIFE-03**: Agent can reactivate a completed task via edit_tasks
- [ ] **LIFE-04**: Lifecycle interface design is resolved via research spike on OmniJS APIs
- [ ] **LIFE-05**: Edge cases documented: repeating tasks, dropped task reactivation limits

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
| NAME-01 | -- | Pending |
| LOOK-01 | -- | Pending |
| LOOK-02 | -- | Pending |
| LOOK-03 | -- | Pending |
| LOOK-04 | -- | Pending |
| MODL-01 | -- | Pending |
| MODL-02 | -- | Pending |
| CREA-01 | -- | Pending |
| CREA-02 | -- | Pending |
| CREA-03 | -- | Pending |
| CREA-04 | -- | Pending |
| CREA-05 | -- | Pending |
| CREA-06 | -- | Pending |
| CREA-07 | -- | Pending |
| CREA-08 | -- | Pending |
| EDIT-01 | -- | Pending |
| EDIT-02 | -- | Pending |
| EDIT-03 | -- | Pending |
| EDIT-04 | -- | Pending |
| EDIT-05 | -- | Pending |
| EDIT-06 | -- | Pending |
| EDIT-07 | -- | Pending |
| EDIT-08 | -- | Pending |
| EDIT-09 | -- | Pending |
| LIFE-01 | -- | Pending |
| LIFE-02 | -- | Pending |
| LIFE-03 | -- | Pending |
| LIFE-04 | -- | Pending |
| LIFE-05 | -- | Pending |

**Coverage:**
- v1.2 requirements: 29 total
- Mapped to phases: 0
- Unmapped: 29

---
*Requirements defined: 2026-03-07*
*Last updated: 2026-03-07 after initial definition*
