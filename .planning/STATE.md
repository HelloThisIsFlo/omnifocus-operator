---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Read Tools
status: executing
stopped_at: Completed 37-03-PLAN.md
last_updated: "2026-04-04T15:09:19.445Z"
last_activity: 2026-04-04
progress:
  total_phases: 10
  completed_phases: 10
  total_plans: 24
  completed_plans: 24
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-29)

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.
**Current focus:** Phase 37 — server-registration-and-integration-was-phase-38

## Current Position

Phase: 37 (server-registration-and-integration-was-phase-38) — EXECUTING
Plan: 2 of 2
Status: Ready to execute
Last activity: 2026-04-04

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
- [Phase quick-260401-hz9]: OrdinalWeekday core model uses extra='forbid' -- value objects where field names define valid vocabulary
- [Phase 36.3]: D-05 docstring cleanup applied during centralization: 7 class docstrings trimmed of implementation details
- [Phase 36.3]: 21 internal classes in exception list covering base classes, protocols, repo-boundary models, and sentinels
- [Phase 36.4]: Private _FrequencyType/_DayName aliases in models/ for output schema correctness -- read models are agent-facing
- [Phase 36.4]: EndByOccurrences.occurrences gets Annotated[int, Field(ge=1)] despite models/ location -- it IS agent-facing
- [Phase 36.4]: Patch[Annotated[int, Field(ge=1)]] propagates minimum: 1 through Pydantic -- no outer Annotated wrapper needed
- [Phase 36.4]: EndByOccurrences.occurrences sole exception in type boundary enforcement -- agent-facing via EndCondition union
- [Phase 36.4]: Private Literal aliases removed from models/ -- plain str with runtime validators replaces schema-level constraints
- [Phase 36.4]: AST enforcement extended to detect module-level Literal/Annotated aliases used on class fields
- [Phase quick-260402-pic]: is_set() guard on type field -- skip all cross-type checks when type is UNSET, deferring to service layer after merge
- [Phase 260402-pj2]: build_add gets optional repetition_rule_payload param for pre-converted payloads
- [Phase 260402-pj2]: payload.py fallback path also uses convert functions for direct callers
- [Phase 260402-pj2]: EndByDate/EndByOccurrences moved to runtime imports in builder.py for isinstance dispatch
- [Phase 37]: Project search SQL uses t.name/t.plainTextNote (projects share Task table)
- [Phase 37]: Perspectives search is name-only (no notes field); non-ASCII test uses ASCII 'Buro'
- [Phase 37]: List tools take query param (not individual params) -- FastMCP introspects QueryModel for inputSchema
- [Phase 37]: _paginate helper duplicated in hybrid and bridge_only repos -- keeps repos self-contained
- [Phase 37]: Default list limit is 50, agent can override with limit=None to get all results

### Roadmap Evolution

- Phase 35.1 inserted after Phase 35: Introduce read-side contract boundary split (RepoQuery / RepoResult) (URGENT)
- Phase 35.2 inserted after Phase 35: Uniform name-vs-ID resolution at service boundary for all list filters (URGENT)
- Old Phases 36 (In-Memory Fallback) + 37 (Service Orchestration) merged into Phase 36; old Phase 38 renumbered to 37
- Phase 36.1 inserted after Phase 36: Migrate write tools to typed params with validation middleware (URGENT)
- Phase 36.2 inserted after Phase 36: Sweep agent-facing schema descriptions and tool documentation (URGENT)
- Phase 36.3 inserted after Phase 36: Centralize field descriptions into constants like warnings and errors (URGENT)
- Phase 36.4 inserted after Phase 36: Reserve Literal and Annotated types for contract models only (URGENT)

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
13. ~~Improve MCP tool schema descriptions and field documentation~~ (DONE: quick-260401-twg)
14. ~~Clarify repetition schedule and repeat mode edge cases~~ (HALF DONE: schedule modes clarified in eec6241; basedOn unset anchor still open)
15. Convert specs to core models at service boundary (post-merge follow-up to #11)
16. Fix effectiveCompletionDate availability ghost tasks (repository)
17. Add built-in perspectives to list_perspectives (repository — needs design discussion)
18. Return full inbox hierarchy from inInbox query (repository)
19. Add path field for hierarchical entities (models)
20. Add disambiguation warnings for ambiguous entity names (server)
21. Improve ambiguous tag error message with resolution guidance (service)
22. Make inbox a first-class value instead of null overloading (design effort)
23. Document edit_tasks action combinability and null-inbox semantics (docs)

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260331-v9q | Tighten schema field constraints: flagged default and name min_length | 2026-03-31 | b064078 | | [260331-v9q-tighten-schema-field-constraints-flagged](./quick/260331-v9q-tighten-schema-field-constraints-flagged/) |
| 260401-i0f | Date type normalization: EndByDate.date str -> datetime.date | 2026-04-01 | 6964d28 | Verified | [260401-i0f-date-type-normalization-str-to-datetime-](./quick/260401-i0f-date-type-normalization-str-to-datetime-/) |
| Phase 36.2 P01 | 3min | 2 tasks | 5 files | | |
| Phase 36.2 P02 | 3min | 2 tasks | 4 files | | |
| Phase 36.2 P03 | 3min | 2 tasks | 1 files | | |
| 260401-hz9 | Replace opaque on: dict with typed OrdinalWeekday | 2026-04-01 | cf0d426 | Verified | [260401-hz9-replace-opaque-on-dict-with-ordinalweekd](./quick/260401-hz9-replace-opaque-on-dict-with-ordinalweekd/) |
| Phase 36.3 P01 | 8min | 2 tasks | 20 files |
| Phase 36.3 P02 | 3min | 1 tasks | 1 files |
| Phase 36.4 P01 | 5min | 2 tasks | 2 files |
| Phase 36.4 P02 | 2min | 2 tasks | 2 files |
| Phase 36.4 P03 | 2min | 2 tasks | 3 files |
| 260401-twg | Improve MCP tool schema descriptions and field documentation | 2026-04-01 | b63e981, 7885e5d | | [260401-twg-improve-mcp-tool-schema-descriptions-and](./quick/260401-twg-improve-mcp-tool-schema-descriptions-and/) |
| 260402-phi | Add validation set sync tests between models and contracts | 2026-04-02 | 8f0f89b | | [260402-phi-add-validation-set-sync-tests-between-mo](./quick/260402-phi-add-validation-set-sync-tests-between-mo/) |
| 260402-pic | Add cross-type model_validator to FrequencyEditSpec | 2026-04-02 | 9c92c8e, b82a0c2 | | [260402-pic-add-cross-type-model-validator-to-freque](./quick/260402-pic-add-cross-type-model-validator-to-freque/) |
| 260402-pj2 | Convert specs to core models at service boundary | 2026-04-02 | 2633181 | Verified | [260402-pj2-convert-specs-to-core-models-at-service-](./quick/260402-pj2-convert-specs-to-core-models-at-service-/) |
| Phase 37 P01 | 9min | 2 tasks | 16 files |
| Phase 37 P02 | 7min | 2 tasks | 5 files |
| Phase 37 P03 | 10min | 2 tasks | 13 files |

### Blockers/Concerns

None yet.

## Session Continuity

Last activity: 2026-04-02 - Completed quick task 260402-pj2: Convert specs to core models at service boundary
Stopped at: Completed 37-03-PLAN.md
Resume file: None
