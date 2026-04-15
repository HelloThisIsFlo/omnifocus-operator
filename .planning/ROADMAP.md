# Roadmap: OmniFocus Operator

## Milestones

- ✅ **v1.0 Foundation** - Phases 1-9 (shipped 2026-03-07)
- ✅ **v1.1 HUGE Performance Upgrade** - Phases 10-13 (shipped 2026-03-07)
- ✅ **v1.2 Writes & Lookups** - Phases 14-17 (shipped 2026-03-15)
- ✅ **v1.2.1 Architectural Cleanup** - Phases 18-28 (shipped 2026-03-23)
- ✅ **v1.2.2 FastMCP v3 Migration** - Phases 29-31 (shipped 2026-03-26)
- ✅ **v1.2.3 Repetition Rule Write Support** - Phases 32-33 (shipped 2026-03-29)
- ✅ **v1.3 Read Tools** - Phases 34-38 (shipped 2026-04-05)
- ✅ **v1.3.1 First-Class References** - Phases 39-44 (shipped 2026-04-07)
- ✅ **v1.3.2 Date Filtering** - Phases 45-50 (shipped 2026-04-11)
- ✅ **v1.3.3 Ordering & Move Fix** - Phases 51-52 (shipped 2026-04-12)

### v1.4 Response Shaping, Batch Processing & Notes Graduation

**Milestone Goal:** Give agents control over response shape and lift write constraints -- reduce token waste via stripping/projection, enable multi-item writes, graduate notes to actions block.

## Phases

- [x] **Phase 53: Response Shaping** - Server package restructure, response stripping, inherited rename, field selection, count-only mode (completed 2026-04-14)
- [x] **Phase 53.1: True Inherited Fields** - Strip self-echoed inherited fields from tasks, remove from projects (INSERTED) (completed 2026-04-14)
- [ ] **Phase 54: Batch Processing** - Multi-item writes with best-effort/fail-fast semantics
- [ ] **Phase 55: Notes Graduation** - Notes move to actions block with append/replace semantics

## Phase Details

### Phase 53: Response Shaping
**Goal**: All tool responses are leaner and agents control which fields list tools return -- stripping, rename, and field selection ship as one coherent response-shaping layer in a new server/ package
**Depends on**: Nothing (first phase of v1.4)
**Requirements**: STRIP-01, STRIP-02, STRIP-03, RENAME-01, FSEL-01, FSEL-02, FSEL-03, FSEL-04, FSEL-05, FSEL-06, FSEL-07, FSEL-08, FSEL-09, FSEL-10, FSEL-11, FSEL-12, FSEL-13, COUNT-01
**Success Criteria** (what must be TRUE):
  1. Agent calling any tool sees no null, [], "", false, or "none" values in entity fields; `availability` always appears; result envelope fields (hasMore, total, status) are never stripped; all `effective*` fields appear as `inherited*`
  2. Agent calling list_tasks with no include/only gets curated default fields; `include: ["notes", "metadata"]` adds those groups; `include: ["*"]` returns all fields; `only: ["project", "dueDate"]` returns exactly those fields plus id
  3. Providing both include and only produces a validation error; invalid group names produce validation error; invalid only field names produce a warning (not error)
  4. `limit: 0` on any list tool returns `{items: [], total: N, hasMore: true/false}` with no entities
  5. server.py is a server/ package; projection and stripping are server-layer concerns separate from tool handlers; service layer returns full Pydantic models unchanged
**Plans**: 5 plans

Plans:
- [x] 53-01-PLAN.md — Inherited rename (effective_* -> inherited_* across codebase)
- [x] 53-02-PLAN.md — Server package restructure (server.py -> server/ package)
- [x] 53-03-PLAN.md — Stripping + field group config + projection module
- [x] 53-04-PLAN.md — Field selection contracts + handler wiring
- [x] 53-05-PLAN.md — Description updates + count-only mode

### Phase 53.1: True Inherited Fields (INSERTED)

**Goal:** inherited* fields on tasks reflect true inheritance (ancestor set the value), not OmniFocus self-echoes; projects have no inherited fields (structurally impossible)
**Requirements**: INHERIT-01, INHERIT-02, INHERIT-03, INHERIT-04, INHERIT-05, INHERIT-06, INHERIT-07, INHERIT-08, INHERIT-09, INHERIT-10
**Depends on:** Phase 53
**Success Criteria** (what must be TRUE):
  1. Task with plannedDate but no ancestor setting plannedDate shows no inheritedPlannedDate in any response
  2. Task under a flagged project (no flagged ancestor tasks) shows inheritedFlagged in response
  3. Projects in get_all, get_project, and list_projects responses have zero inherited* fields
  4. get_all, get_task, and list_tasks all apply true inheritance processing
**Plans:** 3 plans

Plans:
- [x] 53.1-01-PLAN.md — Model surgery: move inherited fields from ActionableEntity to Task, cascade through repos/config/tests
- [x] 53.1-02-PLAN.md — Hierarchy walk: compute_true_inheritance on DomainLogic, wire into service layer
- [x] 53.1-03-PLAN.md — Gap closure: compute actual ancestor values instead of passing through OF effective values

### Phase 54: Batch Processing
**Goal**: Agents can create or edit up to 50 tasks in a single call with clear per-item success/failure reporting
**Depends on**: Phase 53 (response stripping applies to batch results)
**Requirements**: BATCH-01, BATCH-02, BATCH-03, BATCH-04, BATCH-05, BATCH-06, BATCH-07, BATCH-08, BATCH-09
**Success Criteria** (what must be TRUE):
  1. Agent can submit up to 50 items in a single add_tasks or edit_tasks call; >50 items produces a validation error
  2. add_tasks processes all items regardless of failures (best-effort) -- each item gets status "success" or "error"
  3. edit_tasks stops at the first error (fail-fast) -- earlier items committed, later items get status "skipped" with a warning
  4. Response is a flat array with `status`, `id` (when known), `name` (success only), `warnings` (any status), and `error` (error only)
  5. Same-task edits within a batch see the results of prior items; cross-item references are documented as unsupported
**Plans**: TBD

### Phase 55: Notes Graduation
**Goal**: Agents can append to or replace task notes via the actions block -- no more read-modify-write for note updates
**Depends on**: Phase 54 (notes actions must work in batch context)
**Requirements**: NOTE-01, NOTE-02, NOTE-03, NOTE-04, NOTE-05
**Success Criteria** (what must be TRUE):
  1. Top-level `note` field is absent from edit_tasks input schema; add_tasks retains its top-level `note` for initial content
  2. Agent using `actions.note.append` on a task with existing note sees text added with paragraph separator; on an empty note, text is set directly (no leading separator)
  3. Agent using `actions.note.replace` can set new note content, or clear the note entirely with null or ""
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 53 -> 53.1 -> 54 -> 55

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 53. Response Shaping | 5/5 | Complete    | 2026-04-14 |
| 53.1. True Inherited Fields | 3/3 | Gap closure pending (INHERIT-05–10) | 2026-04-15 |
| 54. Batch Processing | 0/TBD | Not started | - |
| 55. Notes Graduation | 0/TBD | Not started | - |
