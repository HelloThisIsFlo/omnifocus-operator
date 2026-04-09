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

4. **Bridge path** (`bridge_only.py`):
   - Add in-memory date filtering for projects (same pattern as tasks, shared resolver)

5. **Tests**:
   - Cross-path equivalence scenarios for projects (extend existing neutral data infrastructure)
   - Service-level tests for date filter resolution in project pipeline

6. **Server** (`server.py`): Nothing -- FastMCP introspects `ListProjectsQuery` automatically.

## Investigation needed before implementation

**Key question**: Which `effective*` date columns are actually populated for projects in the SQLite DB?

Projects are Task table rows joined to ProjectInfo. Tasks have `effective*` columns because they inherit dates from parent projects. Projects sit at the top of the hierarchy (in folders, not nested under other projects), so inheritance semantics differ.

Specific columns to verify against the live OmniFocus SQLite database:

| Column | Question | Why it matters |
|--------|----------|----------------|
| `effectiveDateDue` | Populated for projects with a due date? Probably yes (equals direct `dateDue`). | The `_DATE_COLUMN_MAP` maps `"due"` -> `effectiveDateDue`. If NULL for projects, need project-specific column override. |
| `effectiveDateToStart` | Same question for defer dates. | Maps to `"defer"` filter. |
| `effectiveDatePlanned` | Same question for planned dates. | Maps to `"planned"` filter. |
| `effectiveDateCompleted` | Populated for completed projects? **Likely NOT** -- projects don't have `effective_completion_date` in the model (task.py:21 comment: "task-only -- always null on projects"). | If NULL, `"completed"` filter must map to `dateCompleted` instead for projects. |
| `effectiveDateHidden` | Populated for dropped projects? **Uncertain** -- folders CAN be dropped, so projects might inherit drop status. | If folder dropping cascades an effective date, the existing column works. If not, need `dateHidden`. |

**How to verify**: Query the live OmniFocus SQLite DB for a few projects:
- An active project with due/defer dates set
- A completed project
- A dropped project (if one exists)
- A project inside a dropped folder (if possible -- tests folder-to-project inheritance)

Check whether `effective*` columns have values vs NULL compared to their direct counterparts (`dateDue`, `dateCompleted`, `dateHidden`, etc.).

## Design decisions (already made)

- **`due: "soon"`**: Apply identically to projects -- same `due_soon` OmniFocus setting, same behavior as tasks. Confirmed by user.
- **Lifecycle expansion**: `completed`/`dropped` date filters auto-add `Availability.COMPLETED`/`Availability.DROPPED` -- same pattern for projects.
- **All 7 filters**: Projects get all 7 date filter fields, not a subset.

## Complexity estimate

Low. The v1.3.2 infrastructure was designed as a general-purpose date filtering system. ~15 lines of new production code (mostly copy-paste from tasks), plus tests. Single phase, likely single plan. The only variable is the column investigation above, which determines whether `_DATE_COLUMN_MAP` needs a project-specific override for `completed`/`dropped`.
