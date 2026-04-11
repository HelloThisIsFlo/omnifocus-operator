# Quick Task 260411-h2p: Add date filters to list_projects - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Task Boundary

Add the 7 date filters (`due`, `defer`, `planned`, `completed`, `dropped`, `added`, `modified`) to `list_projects`, reusing the infrastructure built for `list_tasks` in v1.3.2 (Phases 45-47). This fixes the regression where completed/dropped projects became unqueryable after Phase 47 removed those values from `AvailabilityFilter`.

</domain>

<decisions>
## Implementation Decisions

### Lifecycle auto-expansion
- Same function for tasks and projects — both use `AvailabilityFilter` enum, the expand function just unions the set
- Rename `expand_task_availability()` → `expand_availability()` to reflect the broader scope

### Test coverage scope
- Cross-path equivalence tests (SQL vs bridge produce identical results for project date filters)
- Service-level tests (pipeline wires resolution correctly)
- No separate contract validation tests — existing DateFilter validation covers shared model

### Bridge path filtering
- Full parity with hybrid path — mirror exact same date filtering logic
- Cross-path tests enforce this

### HasDateBounds Protocol
- Introduce `HasDateBounds` Protocol in `query_builder.py` for `_add_date_conditions()`
- Structural typing over Union — self-documenting, fits strict mypy stance
- Private to query_builder.py (only consumer)

### Documentation & DRY descriptions
- If task and project date filter field descriptions differ only by "task" vs "project", use shared description strings or templates — don't duplicate prose
- Follow exact naming pattern from `ListTasksRepoQuery` (swap "Tasks" → "Projects")
- Update all docstrings/descriptions to stay current
- Read `docs/model-taxonomy.md` and `docs/architecture.md` during planning to verify conventions

</decisions>

<specifics>
## Specific Ideas

- Rename: `expand_task_availability()` → `expand_availability()`
- Protocol location: `query_builder.py` itself (private, only consumer)
- Server layer: no changes needed — FastMCP introspects `ListProjectsQuery` automatically

</specifics>

<canonical_refs>
## Canonical References

- Todo with full analysis: `.planning/todos/pending/2026-04-09-add-date-filters-to-list-projects.md`
- Model naming conventions: `docs/model-taxonomy.md`
- Architecture patterns: `docs/architecture.md`
- Ground truth column verification: `.research/deep-dives/omnifocus-api-ground-truth/FINDINGS.md`

</canonical_refs>
