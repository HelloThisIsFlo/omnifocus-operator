---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Read Tools
status: executing
stopped_at: "Completed quick task 260401-i0f: Date type normalization"
last_updated: "2026-04-01T12:34:33.638Z"
last_activity: 2026-04-01
progress:
  total_phases: 8
  completed_phases: 7
  total_plans: 15
  completed_plans: 15
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-29)

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.
**Current focus:** Phase 36.2 — sweep-agent-facing-schema-descriptions-and-tool-documentation

## Current Position

Phase: 37
Plan: Not started
Status: Ready to execute
Last activity: 2026-03-31

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
- [Phase 35.1]: Service protocol list signatures unchanged (Query/ListResult) per D-06 -- service wiring is Phase 37
- [Phase 35.1]: Clean break import migration: no re-exports from old paths, old files deleted immediately
- [Phase 35.2]: RepoQuery field parity tests replaced with divergence-aware assertions -- RepoQuery deliberately differs from Query
- [Phase 35.2]: Project filter SQL uses pi2.task IN (?) subquery; folder filter simplified to direct pi.folder IN (?)
- [Phase 35.2]: _ReadPipeline as separate base from _Pipeline for read-side Method Objects
- [Phase 35.2]: BridgeRepository gets fetch-all + Python filter list methods as fallback path
- [Phase 36]: ReviewDueFilter uses QueryModel base -- first <noun>Filter pattern in codebase
- [Phase 36]: Calendar arithmetic for months/years without dateutil dependency
- [Phase 36]: CF epoch conversion in query builder (not pipeline) -- keeps datetime types in Python as long as possible
- [Phase 36]: Tests assert against expected data, parametrization proves equivalence by construction
- [Phase 36.1]: ValidationReformatterMiddleware registered before ToolLoggingMiddleware (LIFO order) so logging sees the reformatted ToolError
- [Phase 36.1]: D-08a: ctx-based _Unset filtering replaces fragile string-based check
- [Phase 36.1]: Snake_case schema check uses property key extraction, not substring matching -- basedOn enum values legitimately contain due_date
- [Phase 36.2]: Date field descriptions faithful to docs/omnifocus-concepts.md: due=deadline, defer=blocked, planned=intention
- [Phase 36.2]: Used double-dash consistently in tool docstrings matching approved text convention
- [Phase quick-260401-i0f]: date_type alias (from datetime import date as date_type) to avoid field name shadowing in EndByDate

### Roadmap Evolution

- Phase 35.1 inserted after Phase 35: Introduce read-side contract boundary split (RepoQuery / RepoResult) (URGENT)
- Phase 35.2 inserted after Phase 35: Uniform name-vs-ID resolution at service boundary for all list filters (URGENT)
- Old Phases 36 (In-Memory Fallback) + 37 (Service Orchestration) merged into Phase 36; old Phase 38 renumbered to 37
- Phase 36.1 inserted after Phase 36: Migrate write tools to typed params with validation middleware (URGENT)
- Phase 36.2 inserted after Phase 36: Sweep agent-facing schema descriptions and tool documentation (URGENT)

### Pending Todos

Carried forward:

1. Add retry logic for OmniFocus bridge timeouts (v1.6)
2. Investigate macOS App Nap impact on OmniFocus responsiveness (v1.6)
3. Make UAT folder discoverable for verification agents
4. Investigate `replace: []` bug in production (may not be staleness-related)
5. Remove misleading "single runtime dependency" messaging from README + landing page
6. Migrate write tools to typed params with validation middleware (Approach 1 from fastmcp-middleware-validation research)
7. Reorganize test suite into unit/integration/golden-master folders
8. Add search tool for projects symmetric with task search (v1.3+)
9. Sweep agent-facing schema descriptions and tool documentation
10. ~~Tighten schema field constraints: flagged default and name min_length~~ (DONE: quick-260331-v9q)
11. Reserve Literal and Annotated types for contract models only
12. Centralize field descriptions into constants like warnings and errors

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260331-v9q | Tighten schema field constraints: flagged default and name min_length | 2026-03-31 | b064078 | [260331-v9q-tighten-schema-field-constraints-flagged](./quick/260331-v9q-tighten-schema-field-constraints-flagged/) |
| 260401-i0f | Date type normalization: EndByDate.date str -> datetime.date | 2026-04-01 | 6964d28 | [260401-i0f-date-type-normalization-str-to-datetime-](./quick/260401-i0f-date-type-normalization-str-to-datetime-/) |
| Phase 36.2 P01 | 3min | 2 tasks | 5 files |
| Phase 36.2 P02 | 3min | 2 tasks | 4 files |
| Phase 36.2 P03 | 3min | 2 tasks | 1 files |

### Blockers/Concerns

None yet.

## Session Continuity

Last activity: 2026-03-31 - Completed quick task 260331-v9q: Tighten schema field constraints
Stopped at: Completed quick task 260401-i0f: Date type normalization
Resume file: None
