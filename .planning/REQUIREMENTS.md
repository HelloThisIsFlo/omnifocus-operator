# Requirements: OmniFocus Operator

**Defined:** 2026-04-14
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.4 Requirements

Requirements for milestone v1.4: Response Shaping, Batch Processing & Notes Graduation.

### Response Stripping

- [ ] **STRIP-01**: All tool responses strip null, [], "", false, and "none" from entity fields automatically
- [ ] **STRIP-02**: availability field is never stripped from entity responses
- [ ] **STRIP-03**: Result envelope fields (hasMore, total, status) are never stripped

### Inherited Rename

- [ ] **RENAME-01**: effective* fields renamed to inherited* across all tool responses (6 fields)

### Field Selection

- [ ] **FSEL-01**: Agent can use `include` on list_tasks/list_projects to add semantic groups to curated defaults
- [ ] **FSEL-02**: ~~Default task fields: id, name, availability, order, project, dueDate, inheritedDueDate, deferDate, inheritedDeferDate, plannedDate, inheritedPlannedDate, flagged, inheritedFlagged, urgency, tags (projects additionally: folder)~~ Default task fields: id, name, availability, order, project, dueDate, inheritedDueDate, deferDate, inheritedDeferDate, plannedDate, inheritedPlannedDate, flagged, inheritedFlagged, urgency, tags. Projects share the same defaults (folder moved to hierarchy group)
- [ ] **FSEL-03**: Available include groups: notes, metadata, hierarchy, time, * (list_tasks); additionally review (list_projects)
- [ ] **FSEL-04**: Invalid include group names produce validation error
- [ ] **FSEL-05**: Agent can use `only` for individual field selection (id always included)
- [ ] **FSEL-06**: include and only mutually exclusive — providing both produces validation error
- [ ] **FSEL-07**: Invalid only field names produce warning in response (not error)
- [ ] **FSEL-08**: include: ["*"] returns all fields
- [ ] **FSEL-09**: get_task, get_project, get_tag, get_all return full stripped entities (no field selection)
- [ ] **FSEL-10**: Group definitions centralized in config.py
- [ ] **FSEL-11**: Projection is post-filter, pre-serialization — doesn't affect query behavior
- [ ] **FSEL-12**: Service layer returns full Pydantic models; projection and stripping are server-layer concerns
- [ ] **FSEL-13**: server.py becomes a server/ package containing existing server and middleware modules plus a new projection module

### True Inherited Fields

- [x] **INHERIT-01**: inherited* fields on tasks only appear when truly inherited from an ancestor (parent task or containing project) — self-echoes are stripped
- [x] **INHERIT-02**: Projects never have inherited* fields in any response (task-only — folders cannot set dates/flags)
- [x] **INHERIT-03**: Walk covers all 6 inherited field pairs: flagged, dueDate, deferDate, plannedDate, dropDate, completionDate
- [x] **INHERIT-04**: True inheritance applies to get_all, get_task, and list_tasks responses

### Per-Field Aggregation Semantics

Each inherited field uses a specific aggregation strategy when walking the ancestor chain. These rules match OmniFocus's own `effective*` resolution, empirically verified in `.research/deep-dives/omnifocus-inheritance-semantics/FINDINGS.md`.

- [ ] **INHERIT-05**: inheritedDueDate uses **min** across all ancestors — tightest deadline in the hierarchy wins. A child cannot escape a parent's deadline
- [ ] **INHERIT-06**: inheritedDeferDate uses **max** across all ancestors — latest block in the hierarchy wins. A child cannot unblock itself past a parent's deferral
- [ ] **INHERIT-07**: inheritedPlannedDate uses **first-found** — nearest ancestor's planned date walking up. No aggregation; own planned date always overrides ancestors (scoped intent)
- [ ] **INHERIT-08**: inheritedFlagged uses **any-True** (boolean OR) — if any ancestor is flagged, the attention signal propagates to all descendants
- [ ] **INHERIT-09**: inheritedDropDate uses **first-found** — nearest ancestor's drop date walking up. No aggregation; effective values are derived from current tree state, not latched
- [ ] **INHERIT-10**: inheritedCompletionDate uses **first-found** — nearest ancestor's completion date walking up. Same semantics as drop date (override family)

### Count-Only

- [ ] **COUNT-01**: limit: 0 returns count-only response ({items: [], total: N, hasMore: <total > 0>})

### Batch Processing

- [ ] **BATCH-01**: add_tasks and edit_tasks accept up to 50 items per call (Pydantic maxItems)
- [ ] **BATCH-02**: add_tasks uses best-effort — all items processed regardless of earlier failures
- [ ] **BATCH-03**: edit_tasks uses fail-fast — stop at first error, remaining items skipped
- [ ] **BATCH-04**: Response is flat array with status: "success" | "error" | "skipped" per item
- [ ] **BATCH-05**: name on success only; id on success and edit errors/skips; absent on failed add items
- [ ] **BATCH-06**: warnings array available on all status types
- [ ] **BATCH-07**: Items processed serially in array order within a batch
- [ ] **BATCH-08**: Same-task edits allowed — each sees prior item's result
- [ ] **BATCH-09**: Cross-item references not supported — batch items cannot reference other items in the same batch (documented in tool description)

### Notes Graduation

- [ ] **NOTE-01**: Top-level note removed from edit_tasks input schema
- [ ] **NOTE-02**: actions.note.append (Patch[str] — null rejected, "" is no-op) adds text with \n\n paragraph separator
- [ ] **NOTE-03**: actions.note.replace (PatchOrClear[str] — null and "" both clear the note) replaces entire note content
- [ ] **NOTE-04**: Append on empty/whitespace-only note sets directly (no leading separator)
- [ ] **NOTE-05**: add_tasks retains top-level note field for initial content

## Future Requirements

Deferred to later milestones. Tracked but not in current roadmap.

### UI & Perspectives (v1.5)

- **PERSP-01**: show_perspective tool to switch active OmniFocus perspective
- **PERSP-02**: get_current_perspective tool to read active perspective
- **PERSP-03**: open_task tool to deep-link into OmniFocus UI

### Production Hardening (v1.6)

- **HARD-01**: Retry logic for bridge timeouts
- **HARD-02**: Crash recovery with persistent state
- **HARD-03**: Serial execution guarantee across concurrent batch calls

### Project Writes (v1.7)

- **PROJ-01**: add_projects tool for creating projects
- **PROJ-02**: edit_projects tool for editing projects

## Out of Scope

| Feature | Reason |
|---------|--------|
| Task deletion (delete_tasks) | Move-to-container is safer — discarded in v1.4 restructure |
| Dedicated count_tasks/count_projects tools | Redundant with limit: 0 on list tools |
| Fuzzy search | Deferred to MAYBE-IDEAS during roadmap restructure |
| TaskPaper output format | Deferred to MAYBE-IDEAS during roadmap restructure |
| Cross-batch concurrency serialization | v1.6 concern — documented as known limitation |
| Hierarchy creation within a single batch | Batch items cannot reference siblings — documented limitation |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| STRIP-01 | Phase 53 | Pending |
| STRIP-02 | Phase 53 | Pending |
| STRIP-03 | Phase 53 | Pending |
| RENAME-01 | Phase 53 | Pending |
| FSEL-01 | Phase 53 | Pending |
| FSEL-02 | Phase 53 | Pending |
| FSEL-03 | Phase 53 | Pending |
| FSEL-04 | Phase 53 | Pending |
| FSEL-05 | Phase 53 | Pending |
| FSEL-06 | Phase 53 | Pending |
| FSEL-07 | Phase 53 | Pending |
| FSEL-08 | Phase 53 | Pending |
| FSEL-09 | Phase 53 | Pending |
| FSEL-10 | Phase 53 | Pending |
| FSEL-11 | Phase 53 | Pending |
| FSEL-12 | Phase 53 | Pending |
| FSEL-13 | Phase 53 | Pending |
| COUNT-01 | Phase 53 | Pending |
| BATCH-01 | Phase 54 | Pending |
| BATCH-02 | Phase 54 | Pending |
| BATCH-03 | Phase 54 | Pending |
| BATCH-04 | Phase 54 | Pending |
| BATCH-05 | Phase 54 | Pending |
| BATCH-06 | Phase 54 | Pending |
| BATCH-07 | Phase 54 | Pending |
| BATCH-08 | Phase 54 | Pending |
| BATCH-09 | Phase 54 | Pending |
| NOTE-01 | Phase 55 | Pending |
| NOTE-02 | Phase 55 | Pending |
| NOTE-03 | Phase 55 | Pending |
| NOTE-04 | Phase 55 | Pending |
| NOTE-05 | Phase 55 | Pending |
| INHERIT-01 | Phase 53.1 | Complete |
| INHERIT-02 | Phase 53.1 | Complete |
| INHERIT-03 | Phase 53.1 | Complete |
| INHERIT-04 | Phase 53.1 | Complete |
| INHERIT-05 | Phase 53.1 | Pending |
| INHERIT-06 | Phase 53.1 | Pending |
| INHERIT-07 | Phase 53.1 | Pending |
| INHERIT-08 | Phase 53.1 | Pending |
| INHERIT-09 | Phase 53.1 | Pending |
| INHERIT-10 | Phase 53.1 | Pending |

**Coverage:**
- v1.4 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0

---
*Requirements defined: 2026-04-14*
*Last updated: 2026-04-14 after roadmap revision (merged Phases 53+54 into Phase 53)*
