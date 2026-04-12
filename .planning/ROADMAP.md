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
- 🚧 **v1.3.3 Ordering & Move Fix** - Phases 51-52 (in progress)

## Phases

- [x] **Phase 51: Task Ordering** - Add `order` field to task responses with correct outline ordering via recursive CTE (completed 2026-04-12)
- [ ] **Phase 52: Same-Container Move Fix** - Service-layer translation of beginning/ending to moveBefore/moveAfter, with accurate no-op detection

## Phase Details

### Phase 51: Task Ordering
**Goal**: Agents can see where each task sits among its siblings via an `order` field, and tasks are returned in correct outline order
**Depends on**: Nothing (first phase of v1.3.3)
**Requirements**: ORDER-01, ORDER-02, ORDER-03, ORDER-04, ORDER-05
**Success Criteria** (what must be TRUE):
  1. Task responses include an integer `order` field reflecting position within parent (1-based, gap-free)
  2. Siblings under the same parent have sequential order values (1, 2, 3...) matching OmniFocus display order
  3. `get_all` and `list_tasks` return tasks in outline order -- siblings grouped under their parent, depth respected
  4. ~~Inbox tasks appear after project tasks~~ → Inbox tasks appear **before** project tasks in get_all/list_tasks responses
  5. `order` field cannot be set via `edit_tasks` -- it is read-only
**Plans:** 2/2 plans complete

Plans:
- [x] 51-01-PLAN.md -- Model field, descriptions, bridge adapter, test infrastructure
- [x] 51-02-PLAN.md -- CTE ordering, dotted path computation, hybrid repository integration

### Phase 52: Same-Container Move Fix
**Goal**: `moveTo beginning/ending` reliably reorders tasks even when already in the target container, with accurate no-op warnings
**Depends on**: Phase 51 (rank infrastructure)
**Requirements**: MOVE-01, MOVE-02, MOVE-03, MOVE-04, MOVE-05, MOVE-06, WARN-01, WARN-02, WARN-03
**Success Criteria** (what must be TRUE):
  1. `moveTo beginning` on the same container moves the task to first position (not silently ignored)
  2. `moveTo ending` on the same container moves the task to last position (not silently ignored)
  3. Moving to a different container via beginning/ending works as before (no regression)
  4. Moving to an empty container works without translation (direct moveTo, no first/last child to reference)
  5. The "same-container move not fully supported" warning is removed
  6. Moving the last child to "beginning" does NOT trigger a no-op warning (it would actually reorder)
  7. Moving the first child to "ending" does NOT trigger a no-op warning (it would actually reorder)
  8. Moving the first child to "beginning" DOES trigger a no-op warning (already in position)
  9. Moving the last child to "ending" DOES trigger a no-op warning (already in position)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 51 → 52

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 51. Task Ordering | v1.3.3 | 2/2 | Complete   | 2026-04-12 |
| 52. Same-Container Move Fix | v1.3.3 | 0/? | Not started | - |
