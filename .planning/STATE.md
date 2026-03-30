---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Read Tools
status: executing
stopped_at: Completed 35.1-01-PLAN.md
last_updated: "2026-03-30T20:22:20.633Z"
last_activity: 2026-03-30
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 6
  completed_plans: 5
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-29)

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.
**Current focus:** Phase 35.1 — introduce-read-side-contract-boundary-split-repoquery-reporesult

## Current Position

Phase: 35.1 (introduce-read-side-contract-boundary-split-repoquery-reporesult) — EXECUTING
Plan: 2 of 2
Status: Ready to execute
Last activity: 2026-03-30

Progress: [██░░░░░░░░] 20%

## Performance Metrics

**Velocity:**

- Total plans completed: 1 (this milestone)
- Cumulative: 103 plans across v1.0-v1.3

*Updated after each plan completion*

## Accumulated Context

### Decisions

Recent decisions affecting current work:

- No standalone count tools — total_count embedded in ListResult
- Query models inherit QueryModel (not CommandModel) — read-side taxonomy
- Service resolves all shorthands before repository layer — prevents SQL/in-memory drift
- Bridge fallback parity is a hard requirement — cross-path equivalence tests mandatory
- [Phase 34]: StrictModel extracted as shared base for CommandModel/QueryModel; Query suffix added to contract naming convention
- [Phase 34]: ListResult inherits OmniFocusBaseModel (not StrictModel) since it is an output model
- [Phase 34]: Availability clauses use static lookup dicts (no user params) -- column-only SQL conditions avoid injection surface
- [Phase 34]: SqlQuery NamedTuple as standard return type for parameterized SQL in repository layer
- [Phase 35]: Shared lookup helpers extracted as module-level functions for reuse across _read_all and list methods
- [Phase 35]: list_projects only needs tag lookups (not project_info/task_name) since _map_project_row takes 2 params
- [Phase 35]: Fetch-all + Python filter for tags/folders/perspectives per D-01a (no query builder needed for small collections)
- [Phase 35.1]: RepoQuery fields use names (not IDs) -- identical to Query today, Structure Over Discipline
- [Phase 35.1]: Per-use-case package structure: contracts/use_cases/{verb}/ with __init__.py re-exports

### Roadmap Evolution

- Phase 35.1 inserted after Phase 35: Introduce read-side contract boundary split (RepoQuery / RepoResult) (URGENT)

### Pending Todos

Carried forward:

1. Add retry logic for OmniFocus bridge timeouts (v1.6)
2. Investigate macOS App Nap impact on OmniFocus responsiveness (v1.6)
3. Make UAT folder discoverable for verification agents
4. Investigate `replace: []` bug in production (may not be staleness-related)
5. Remove misleading "single runtime dependency" messaging from README + landing page
6. Migrate write tools to typed params with validation middleware (Approach 1 from fastmcp-middleware-validation research)
7. Migrate tag filter to accept names at repository level (contract consistency — urgent, before phase 36)
8. Add "did you mean?" suggestions for zero-result name filters (INFRA-07, Phase 37)
9. Reorganize test suite into unit/integration/golden-master folders

### Blockers/Concerns

None yet.

## Session Continuity

Last activity: 2026-03-30 -- Plan 35-01 completed
Stopped at: Completed 35.1-01-PLAN.md
Resume file: None
