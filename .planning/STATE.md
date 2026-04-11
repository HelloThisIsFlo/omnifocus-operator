---
gsd_state_version: 1.0
milestone: v1.3.2
milestone_name: Date Filtering
status: planning
last_updated: "2026-04-10T22:22:11.696Z"
last_activity: 2026-04-10
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 21
  completed_plans: 21
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-07)

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.
**Current focus:** Phase 49 — naive-local-datetime-contract

## Current Position

Phase: 49
Plan: Not started
Status: Phase 49 context gathered, pending planning
Last activity: 2026-04-10

Progress: [████████░░] 80% (4/5 phases complete, Phase 49 pending)

## Performance Metrics

**Velocity:**

- Cumulative: 143 plans across v1.0-v1.3.1

*Updated after each plan completion*

## Accumulated Context

### Decisions

Cleared at milestone boundary. See PROJECT.md Key Decisions for full history.

Key design decisions for v1.3.2:

- `"overdue"` and `"soon"` use OmniFocus pre-computed columns — no threshold config needed
- `COMPLETED`/`DROPPED` removed from AvailabilityFilter; `ALL` removed with educational error
- DateRange is internal resolved type, not agent-facing contract
- `count_tasks` out of scope for this milestone
- Naive-local datetime contract for all date inputs — `str` type (no `format: "date-time"`), normalization in domain.py, centralized local timezone helper

### Pending Todos

Carried forward from v1.3.1:

1. Add retry logic for OmniFocus bridge timeouts (v1.6)
2. Investigate macOS App Nap impact on OmniFocus responsiveness (v1.6)
3. Make UAT folder discoverable for verification agents
4. Investigate `replace: []` bug in production (may not be staleness-related)
5. Remove misleading "single runtime dependency" messaging from README + landing page
6. Reorganize test suite into unit/integration/golden-master folders
7. Add built-in perspectives to list_perspectives (repository — needs design discussion)
8. Return full inbox hierarchy from inInbox query (repository)
9. Add path field for hierarchical entities (models)
10. Field selection with curated defaults for read tools (v1.4)
11. Null-stripping for read tool responses (v1.4)
12. Fix OrdinalWeekdaySpec → OrdinalWeekday cross-layer coercion in edit pipeline (service)
13. Golden master re-capture required after Phase 42 mapper rewrites (human-only per GOLD-01)
14. ~~Add date filters to list_projects — reuse v1.3.2 infrastructure, investigate effective* columns~~ → completed by quick task 260411-h2p
15. ~~Design timezone consistency policy for date filter inputs~~ → completed, superseded by #18
16. Refactor DateFilter into discriminated union for schema-level validation (contracts)
17. ~~Rethink timezone handling strategy for date filter inputs~~ → completed by timezone deep-dive
18. Implement naive-local datetime contract for all date inputs (contracts)
19. Use OmniFocus settings API for date preferences and due-soon threshold (service) — depends on #18

### Roadmap Evolution

- Phase 48 added: Refactor DateFilter into discriminated union with typed date bounds
- Phase 49 added: Implement naive-local datetime contract for all date inputs
- Phase 50 added: Use OmniFocus settings API for date preferences and due-soon threshold

### Blockers/Concerns

(None)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260411-fv2 | Make date filter before/after bounds inclusive for datetime | 2026-04-11 | cfa9de8 | [260411-fv2-make-date-filter-before-after-bounds-inc](./quick/260411-fv2-make-date-filter-before-after-bounds-inc/) |
| 260411-h2p | Add date filters to list_projects | 2026-04-11 | 7e53841 | [260411-h2p-add-date-filters-to-list-projects](./quick/260411-h2p-add-date-filters-to-list-projects/) |

## Session Continuity

Last activity: 2026-04-11 - Completed quick task 260411-h2p: Add date filters to list_projects
Resume: .planning/phases/49-implement-naive-local-datetime-contract-for-all-date-inputs/49-CONTEXT.md
