# Requirements: OmniFocus Operator

**Defined:** 2026-04-14
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.4 Requirements

Requirements for milestone v1.4: Response Shaping, Batch Processing & Notes Graduation.

### Response Stripping

- [x] **STRIP-01**: All tool responses strip null, [], "", false, and "none" from entity fields automatically
- [x] **STRIP-02**: availability field is never stripped from entity responses
- [x] **STRIP-03**: Result envelope fields (hasMore, total, status) are never stripped
- [x] **STRIP-04**: Batch result items (`AddTaskResult`, `EditTaskResult`) in add_tasks / edit_tasks responses are stripped using STRIP-01 rules — null/""/false/[]/"none" removed from each item. `status` field is always preserved (required Literal — never matches the strip set).

### Inherited Rename

- [x] **RENAME-01**: effective* fields renamed to inherited* across all tool responses (6 fields)

### Field Selection

- [x] **FSEL-01**: Agent can use `include` on list_tasks/list_projects to add semantic groups to curated defaults
- [x] **FSEL-02**: ~~Default task fields: id, name, availability, order, project, dueDate, inheritedDueDate, deferDate, inheritedDeferDate, plannedDate, inheritedPlannedDate, flagged, inheritedFlagged, urgency, tags (projects additionally: folder)~~ Default task fields: id, name, availability, order, project, dueDate, inheritedDueDate, deferDate, inheritedDeferDate, plannedDate, inheritedPlannedDate, flagged, inheritedFlagged, urgency, tags. Projects share the same defaults (folder moved to hierarchy group)
- [x] **FSEL-03**: Available include groups: notes, metadata, hierarchy, time, * (list_tasks); additionally review (list_projects)
- [x] **FSEL-04**: Invalid include group names produce validation error
- [x] **FSEL-05**: Agent can use `only` for individual field selection (id always included)
- [x] **FSEL-06**: include and only mutually exclusive — providing both produces validation error
- [x] **FSEL-07**: Invalid only field names produce warning in response (not error)
- [x] **FSEL-08**: include: ["*"] returns all fields
- [x] **FSEL-09**: get_task, get_project, get_tag, get_all return full stripped entities (no field selection)
- [x] **FSEL-10**: Group definitions centralized in config.py
- [x] **FSEL-11**: Projection is post-filter, pre-serialization — doesn't affect query behavior
- [x] **FSEL-12**: Service layer returns full Pydantic models; projection and stripping are server-layer concerns
- [x] **FSEL-13**: server.py becomes a server/ package containing existing server and middleware modules plus a new projection module

### True Inherited Fields

- [x] **INHERIT-01**: inherited* fields on tasks only appear when truly inherited from an ancestor (parent task or containing project) — self-echoes are stripped
- [x] **INHERIT-02**: Projects never have inherited* fields in any response (task-only — folders cannot set dates/flags)
- [x] **INHERIT-03**: Walk covers all 6 inherited field pairs: flagged, dueDate, deferDate, plannedDate, dropDate, completionDate
- [x] **INHERIT-04**: True inheritance applies to get_all, get_task, and list_tasks responses

### Per-Field Aggregation Semantics

Each inherited field uses a specific aggregation strategy when walking the ancestor chain. These rules match OmniFocus's own `effective*` resolution, empirically verified in `.research/deep-dives/omnifocus-inheritance-semantics/FINDINGS.md`.

- [x] **INHERIT-05**: inheritedDueDate uses **min** across all ancestors — tightest deadline in the hierarchy wins. A child cannot escape a parent's deadline
- [x] **INHERIT-06**: inheritedDeferDate uses **max** across all ancestors — latest block in the hierarchy wins. A child cannot unblock itself past a parent's deferral
- [x] **INHERIT-07**: inheritedPlannedDate uses **first-found** — nearest ancestor's planned date walking up. No aggregation; own planned date always overrides ancestors (scoped intent)
- [x] **INHERIT-08**: inheritedFlagged uses **any-True** (boolean OR) — if any ancestor is flagged, the attention signal propagates to all descendants
- [x] **INHERIT-09**: inheritedDropDate uses **first-found** — nearest ancestor's drop date walking up. No aggregation; effective values are derived from current tree state, not latched
- [x] **INHERIT-10**: inheritedCompletionDate uses **first-found** — nearest ancestor's completion date walking up. Same semantics as drop date (override family)

### Count-Only

- [x] **COUNT-01**: limit: 0 returns count-only response ({items: [], total: N, hasMore: <total > 0>})

### Batch Processing

- [x] **BATCH-01**: add_tasks and edit_tasks accept up to 50 items per call (Pydantic maxItems)
- [x] **BATCH-02**: add_tasks uses best-effort — all items processed regardless of earlier failures
- [x] **BATCH-03**: edit_tasks uses fail-fast — stop at first error, remaining items skipped
- [x] **BATCH-04**: Response is flat array with status: "success" | "error" | "skipped" per item
- [x] **BATCH-05**: name on success only; id on success and edit errors/skips; absent on failed add items
- [x] **BATCH-06**: warnings array available on all status types
- [x] **BATCH-07**: Items processed serially in array order within a batch
- [x] **BATCH-08**: Same-task edits allowed — each sees prior item's result
- [x] **BATCH-09**: Cross-item references not supported — batch items cannot reference other items in the same batch (documented in tool description)
- [x] **BATCH-10**: Batch tools (`add_tasks`, `edit_tasks`) advertise a loose `array of object` outputSchema. Clients infer item shape from BATCH-04/05/06. Enforced by `tests/test_server.py::test_write_tools_have_loose_output_schema`.

### Notes Graduation

- [x] **NOTE-01**: Top-level note removed from edit_tasks input schema
- [x] **NOTE-02**: actions.note.append (Patch[str] — null rejected, ~~`""` is no-op~~ `""` or whitespace-only is no-op) adds text with ~~\n\n paragraph separator~~ `\n` newline separator (agent prepends own `\n` for blank-line break)
  - *Revised 2026-04-17 (UAT Phase 55):* Two revisions from the original requirement:
    - **No-op scope broadened**: OmniFocus normalizes whitespace-only notes to empty and trims trailing whitespace on write (verified via OmniJS — `"   "` stored as `""`, `"Existing\n\n   "` stored as `"Existing"`). `append="   "` was previously classified as a real change but was silently no-op'd by OmniFocus, giving agents no feedback. Now treated as an N1 no-op with `NOTE_APPEND_EMPTY` warning to match observable behavior.
    - **Separator tightened** from `\n\n` to `\n`: agent-controllability argument — with `\n` as the default, agents can prepend their own `\n` to compose `\n\n` (paragraph break) when desired; but `\n\n` as default couldn't be unpacked to `\n`. Minimal-useful-separator principle. OmniFocus renders `\n` as a visible soft break in note text, so separation is preserved visually.
- [x] **NOTE-03**: actions.note.replace (PatchOrClear[str] — null and "" both clear the note) replaces entire note content
- [x] **NOTE-04**: Append on empty/whitespace-only note sets directly (no leading separator)
- [x] **NOTE-05**: add_tasks retains top-level note field for initial content

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
| STRIP-01 | Phase 53 | Complete |
| STRIP-02 | Phase 53 | Complete |
| STRIP-03 | Phase 53 | Complete |
| STRIP-04 | Quick 260417-oiw | Complete |
| RENAME-01 | Phase 53 | Complete |
| FSEL-01 | Phase 53 | Complete |
| FSEL-02 | Phase 53 | Complete |
| FSEL-03 | Phase 53 | Complete |
| FSEL-04 | Phase 53 | Complete |
| FSEL-05 | Phase 53 | Complete |
| FSEL-06 | Phase 53 | Complete |
| FSEL-07 | Phase 53 | Complete |
| FSEL-08 | Phase 53 | Complete |
| FSEL-09 | Phase 53 | Complete |
| FSEL-10 | Phase 53 | Complete |
| FSEL-11 | Phase 53 | Complete |
| FSEL-12 | Phase 53 | Complete |
| FSEL-13 | Phase 53 | Complete |
| COUNT-01 | Phase 53 | Complete |
| BATCH-01 | Phase 54 | Complete |
| BATCH-02 | Phase 54 | Complete |
| BATCH-03 | Phase 54 | Complete |
| BATCH-04 | Phase 54 | Complete |
| BATCH-05 | Phase 54 | Complete |
| BATCH-06 | Phase 54 | Complete |
| BATCH-07 | Phase 54 | Complete |
| BATCH-08 | Phase 54 | Complete |
| BATCH-09 | Phase 54 | Complete |
| BATCH-10 | Quick 260417-oiw | Complete |
| NOTE-01 | Phase 55 | Complete |
| NOTE-02 | Phase 55 | Complete |
| NOTE-03 | Phase 55 | Complete |
| NOTE-04 | Phase 55 | Complete |
| NOTE-05 | Phase 55 | Complete |
| INHERIT-01 | Phase 53.1 | Complete |
| INHERIT-02 | Phase 53.1 | Complete |
| INHERIT-03 | Phase 53.1 | Complete |
| INHERIT-04 | Phase 53.1 | Complete |
| INHERIT-05 | Phase 53.1 | Complete |
| INHERIT-06 | Phase 53.1 | Complete |
| INHERIT-07 | Phase 53.1 | Complete |
| INHERIT-08 | Phase 53.1 | Complete |
| INHERIT-09 | Phase 53.1 | Complete |
| INHERIT-10 | Phase 53.1 | Complete |

**Coverage:**
- v1.4 requirements: 41 total
- Mapped to phases: 41
- Unmapped: 0

---
*Requirements defined: 2026-04-14*
*Last updated: 2026-04-17 — added STRIP-04 and BATCH-10 from Quick 260417-oiw (batch result stripping follow-up)*
