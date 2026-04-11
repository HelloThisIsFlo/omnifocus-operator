---
created: 2026-04-09T09:48:45.756Z
title: Add date filters to list_projects
area: service
files:
  - src/omnifocus_operator/contracts/use_cases/list/projects.py
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
  - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
  - src/omnifocus_operator/service/service.py:440-499
  - src/omnifocus_operator/service/resolve_dates.py
  - src/omnifocus_operator/service/domain.py:153-223
  - src/omnifocus_operator/repository/hybrid/query_builder.py:24-53
  - src/omnifocus_operator/repository/hybrid/hybrid.py:398-450
  - src/omnifocus_operator/repository/bridge_only/bridge_only.py
  - tests/test_cross_path_equivalence.py
---

## Problem

`list_projects` does not support any of the 7 date filters added to `list_tasks` in v1.3.2 (Phases 45-47). This was a planning gap -- the spec only covered tasks. Projects should support the same date filtering: `due`, `defer`, `planned`, `completed`, `dropped`, `added`, `modified`.

**Active regression (since Phase 47):** Phase 47 removed `COMPLETED` and `DROPPED` from the `AvailabilityFilter` enum. For tasks, this is fine -- the new `completed`/`dropped` date filters (with `"any"` shortcut) replaced that access path. But `list_projects` never got those date filters, so there is currently **no way to query completed or dropped projects at all**. Before Phase 47, `list_projects(availability=["completed"])` worked. Now it's a validation error with no alternative.

Decision: Accept the gap rather than temporarily restoring the old enum values. The date filter phase is the real fix -- it restores and exceeds the old capability. Adding throwaway compatibility code would create churn for behavior that's about to be superseded. Pre-release, one user, low practical risk.

## What exists (reusable as-is)

- **DateFilter contract** (`_date_filter.py`): Shared model with validators for shorthand (`this`/`last`/`next`) and absolute (`before`/`after`) forms. Entity-agnostic.
- **Shortcut enums** (`_enums.py`): `DueDateShortcut` (overdue/soon/today), `LifecycleDateShortcut` (any/today). Shared.
- **Pure resolver** (`resolve_dates.py`): ~300 lines of pure functions converting filter forms to `ResolvedDateBounds(after, before)`. No task-specific logic.
- **Domain pipeline helper** (`domain.py:153-223`): `resolve_date_filters()` iterates field names generically, handles lifecycle auto-expansion and defer hints. Entity-agnostic.
- **SQL predicate builder** (`query_builder.py:24-53`): `_DATE_COLUMN_MAP` and `_add_date_conditions()` map field names to SQL columns. Works on any `Task` table row -- projects use the same table.
- **Cross-path test infrastructure** (`test_cross_path_equivalence.py`): Neutral data builders, seed adapters for bridge/SQLite formats. Can be extended for project scenarios.

## What needs to be built

1. **Contracts** (`projects.py`):
   - Add 7 date filter fields to `ListProjectsQuery` (same types as `ListTasksQuery`)
   - Add 14 `_after`/`_before` datetime fields to `ListProjectsRepoQuery`

2. **Service pipeline** (`service.py`, `_ListProjectsPipeline`):
   - Add `_resolve_date_filters()` method (copy from `_ListTasksPipeline:388-407`)
   - Update `_build_repo_query()` to unpack date bounds into repo query

3. **SQL builder** (`query_builder.py`, `build_list_projects_sql()`):
   - Add one call: `_add_date_conditions(conditions, params, query)` after existing folder conditions
   - Widen `_add_date_conditions` type signature — see "Protocol for date bounds" below

4. **Bridge path** (`bridge_only.py`):
   - Add in-memory date filtering for projects (same pattern as tasks, shared resolver)

5. **Tests**:
   - Cross-path equivalence scenarios for projects (extend existing neutral data infrastructure)
   - Service-level tests for date filter resolution in project pipeline

6. **Server** (`server.py`): Nothing -- FastMCP introspects `ListProjectsQuery` automatically.

## Column mapping: verified, no overrides needed

All 7 `_DATE_COLUMN_MAP` entries work for projects as-is. No project-specific column overrides required.

**Source:** Ground truth script 02 (`02-project-effective-fields.js`) ran against all 368 projects and confirmed zero divergences for all 6 effective fields. Full results in `.research/deep-dives/omnifocus-api-ground-truth/FINDINGS.md`, section "2. Project Type > Effective Fields Bug".

| Filter | SQLite Column | Projects with data (of 368) | Notes |
|--------|---------------|----------------------------|-------|
| `due` | `effectiveDateDue` | 17 | Works identically to tasks |
| `defer` | `effectiveDateToStart` | 10 | Works identically to tasks |
| `planned` | `effectiveDatePlanned` | 0 (all null) | Column exists, no projects use planned dates — filter just won't match |
| `completed` | `effectiveDateCompleted` | 6 | Already used by `_PROJECT_AVAILABILITY_CLAUSES` (line 140) |
| `dropped` | `effectiveDateHidden` | 23 | Already used by `_PROJECT_AVAILABILITY_CLAUSES` (line 143); includes folder-inherited drops |
| `added` | `dateAdded` | 368 (all) | Always present |
| `modified` | `dateModified` | 368 (all) | Always present |

The earlier concern that `effectiveDateCompleted` might be "task-only — always null on projects" was disproven by the ground truth audit. The existing `_PROJECT_AVAILABILITY_CLAUSES` already rely on these columns in production.

**Further reading:**
- SQLite schema: `.research/deep-dives/direct-database-access/1-initial-discovery/sqlite_schema.sql`
- Field coverage verification: `.research/deep-dives/direct-database-access/4-final-checks/FINDINGS.md`
- Ground truth audit scripts: `.research/deep-dives/omnifocus-api-ground-truth/scripts/`

## Protocol for date bounds

`_add_date_conditions()` currently types `query` as `ListTasksRepoQuery` (query_builder.py:42). To reuse it for projects, introduce a `HasDateBounds` Protocol rather than a union:

- The function only does `getattr(query, f"{field_name}_after", None)` — pure structural access
- Protocol expresses "has the right shape" without coupling to specific query types
- Open for extension if other entity types get date filters later

## Design decisions (already made)

- **`due: "soon"`**: Apply identically to projects -- same `due_soon` OmniFocus setting, same behavior as tasks. Confirmed by user.
- **Lifecycle expansion**: `completed`/`dropped` date filters auto-add `Availability.COMPLETED`/`Availability.DROPPED` -- same pattern for projects.
- **All 7 filters**: Projects get all 7 date filter fields, not a subset.

## Complexity estimate

Low. The v1.3.2 infrastructure was designed as a general-purpose date filtering system. ~15 lines of new production code (mostly copy-paste from tasks), plus tests. Single phase, likely single plan.
