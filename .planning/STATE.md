---
gsd_state_version: 1.0
milestone: v1.3.3
milestone_name: Ordering & Move Fix
status: defining_requirements
last_updated: "2026-04-11T22:00:00.000Z"
last_activity: 2026-04-11
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.
**Current focus:** Milestone v1.3.3 — Ordering & Move Fix

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-11 — Milestone v1.3.3 started

## Performance Metrics

**Velocity:**

- Cumulative: 166 plans across v1.0-v1.3.2

*Updated after each plan completion*

## Accumulated Context

### Decisions

Cleared at milestone boundary. See PROJECT.md Key Decisions for full history.

### Pending Todos

Carried forward to next milestone:

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

### Blockers/Concerns

(None)

### Quick Tasks Completed

Cleared at milestone boundary. See v1.3.2-ROADMAP.md for history.

## Session Continuity

Last activity: 2026-04-11 - Milestone v1.3.2 Date Filtering shipped
Resume: `/gsd-new-milestone` for v1.4
