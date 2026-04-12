# Requirements: OmniFocus Operator

**Defined:** 2026-04-11
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.3.3 Requirements

Requirements for Ordering & Move Fix milestone. Each maps to roadmap phases.

### Ordering

- [x] **ORDER-01**: Task responses include an `order` integer field reflecting display order within parent
- [x] **ORDER-02**: Siblings under the same parent have sequential, gap-free order values (1, 2, 3...)
- [x] **ORDER-03**: `order` field is read-only — not settable via `edit_tasks`
- [x] **ORDER-04**: Tasks returned in outline order (siblings grouped, depth and relative order respected); recursive CTE for HybridRepository, approximate ordering acceptable for BridgeOnlyRepository fallback
- [ ] **ORDER-05**: ~~Inbox tasks sort after projects~~ → Inbox tasks sort **before** projects in get_all/list_tasks responses

### Move Fix

- [ ] **MOVE-01**: `moveTo beginning` on same container reorders task to first position
- [ ] **MOVE-02**: `moveTo ending` on same container reorders task to last position
- [ ] **MOVE-03**: Service translates to `moveBefore`/`moveAfter` when target container has children
- [ ] **MOVE-04**: Move to empty container works without translation (direct `moveTo`)
- [ ] **MOVE-05**: Move to different container works as before (no regression)
- [ ] **MOVE-06**: Remove the "same-container move not fully supported" warning — it's now fixed

### Warning Accuracy

- [ ] **WARN-01**: No-op warning only fires when task is already in the requested position
- [ ] **WARN-02**: "beginning" position check uses `MIN(rank)` among siblings
- [ ] **WARN-03**: "ending" position check uses `MAX(rank)` among siblings

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Field Selection (v1.4)

- **FIELD-01**: Agents can select which fields to include in read responses
- **FIELD-02**: Curated default field sets for common use cases

### Task Writes (v1.4)

- **WRITE-01**: Task deletion support
- **WRITE-02**: Notes append mode (add to existing note)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Setting `order` via edit_tasks | Order is computed from rank; reordering is done via move actions |
| Cross-path ordering equivalence | BridgeOnlyRepository is a degraded fallback; approximate ordering acceptable |
| Task reordering without move | Would require new API; use moveBefore/moveAfter via existing move actions |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ORDER-01 | Phase 51 | Complete |
| ORDER-02 | Phase 51 | Complete |
| ORDER-03 | Phase 51 | Complete |
| ORDER-04 | Phase 51 | Complete |
| ORDER-05 | Phase 51 | Revised — ~~after~~ → **before** projects |
| MOVE-01 | Phase 52 | Pending |
| MOVE-02 | Phase 52 | Pending |
| MOVE-03 | Phase 52 | Pending |
| MOVE-04 | Phase 52 | Pending |
| MOVE-05 | Phase 52 | Pending |
| MOVE-06 | Phase 52 | Pending |
| WARN-01 | Phase 52 | Pending |
| WARN-02 | Phase 52 | Pending |
| WARN-03 | Phase 52 | Pending |

**Coverage:**
- v1.3.3 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-04-11*
*Last updated: 2026-04-11 after roadmap creation*
