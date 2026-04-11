# Quick Task 260411-h2p: Add date filters to list_projects — Summary

**Completed:** 2026-04-11
**Plan:** 260411-h2p-01 (3 tasks)

## Commits

| Hash | Message |
|------|---------|
| `3afb4c4` | feat(260411-h2p): add date filter fields to list_projects across all layers |
| `6cc6c1e` | test(260411-h2p): add cross-path and pipeline tests for project date filters |
| `7e53841` | fix(260411-h2p): update field parity test for project date filter fields |

## What Changed

### Production (6 files, +169 lines)
- **contracts/use_cases/list/projects.py** — 7 date filter fields on `ListProjectsQuery`, 14 `_after`/`_before` fields on `ListProjectsRepoQuery`, `_PATCH_FIELDS` updated
- **agent_messages/descriptions.py** — `COMPLETED_FILTER_DESC` and `DROPPED_FILTER_DESC` changed "tasks" → "items" for entity-agnostic phrasing
- **service/service.py** — `_ListProjectsPipeline` gains `_resolve_date_filters()` and date bounds unpacking in `_build_repo_query()`
- **service/domain.py** — `expand_task_availability` → `expand_availability` rename
- **repository/hybrid/query_builder.py** — `HasDateBounds` Protocol, `_add_date_conditions` widened type, called from `build_list_projects_sql`
- **repository/bridge_only/bridge_only.py** — `_BRIDGE_PROJECT_FIELD_MAP` with `completion_date` override, date filtering loop in `list_projects`

### Tests (4 files, +273 lines)
- **test_cross_path_equivalence.py** — 12 new tests in `TestProjectDateFilterCrossPath`, neutral data extended with completed/dropped projects
- **test_list_pipelines.py** — `TestListProjectsDateFiltering` with pipeline resolution and lifecycle expansion tests
- **test_service_domain.py** — `expand_task_availability` → `expand_availability` rename in 7 test calls
- **test_list_contracts.py** — Field parity test updated for new date filter fields

## Validation

- 1975 tests passing
- mypy clean
- Output schema valid
- Zero references to `expand_task_availability` remain

## Deviations

1. **Field parity test** — needed date field exclusions (auto-fixed in commit 3)
2. **Bridge seed adapter** — project status mapping was incomplete (had Active/Dropped, needed Done/OnHold) — auto-fixed
