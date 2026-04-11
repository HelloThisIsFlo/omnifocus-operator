# Quick Task: Add Date Filters to list_projects - Research

**Researched:** 2026-04-11
**Domain:** Reusing v1.3.2 date filter infrastructure for projects
**Confidence:** HIGH

## Summary

All v1.3.2 date filter infrastructure is entity-agnostic and ready for reuse. The SQL path works with zero changes to `_DATE_COLUMN_MAP` (projects share the Task table). The bridge path needs a **project-specific field map** because `effective_completion_date` exists only on `Task`, not `Project`. Description strings are generic enough for sharing. The `expand_task_availability` rename has 10 call sites across 4 files.

**Primary recommendation:** Build a project-specific `_BRIDGE_PROJECT_FIELD_MAP` in bridge_only.py (overriding only the `completed` entry), and use shared/templated description strings for the 7 date filter fields.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Implementation Decisions
- Lifecycle auto-expansion: same function for tasks and projects, rename `expand_task_availability()` to `expand_availability()`
- Cross-path equivalence tests + service-level tests; no separate contract validation tests
- Bridge path: full parity, enforced by cross-path tests
- `HasDateBounds` Protocol in `query_builder.py` for `_add_date_conditions()` -- structural typing, private to query_builder
- DRY descriptions: share strings or templates where task/project descriptions differ only by entity name
- Follow exact naming pattern from `ListTasksRepoQuery` (swap "Tasks" to "Projects")

### Specific Ideas
- Protocol location: `query_builder.py` itself
- Server layer: no changes needed (FastMCP introspects automatically)
</user_constraints>

## Finding 1: Bridge Field Map Needs Project Override

**Confidence:** HIGH [VERIFIED: runtime check against Project model]

`_BRIDGE_FIELD_MAP` in `bridge_only.py` maps `"completed"` to `"effective_completion_date"`. This attribute exists on `Task` but NOT on `Project`:

| Filter | Task attribute | Project attribute | Same? |
|--------|---------------|-------------------|-------|
| `due` | `effective_due_date` | `effective_due_date` | YES (ActionableEntity) |
| `defer` | `effective_defer_date` | `effective_defer_date` | YES |
| `planned` | `effective_planned_date` | `effective_planned_date` | YES |
| `completed` | `effective_completion_date` | `completion_date` | **NO** |
| `dropped` | `effective_drop_date` | `effective_drop_date` | YES |
| `added` | `added` | `added` | YES |
| `modified` | `modified` | `modified` | YES |

**Why the difference:** `ActionableEntity` (shared base) has `completion_date` (the direct date). `Task` adds `effective_completion_date` (inherited from parent). Projects don't inherit completion dates from anywhere -- they're always root entities -- so `completion_date` IS the effective completion date.

**Recommendation:** Define `_BRIDGE_PROJECT_FIELD_MAP` as a copy of `_BRIDGE_FIELD_MAP` with `"completed": "completion_date"`. This is the minimal divergence approach -- one dict override vs. a complex parametrized function.

**Alternative considered:** Use `getattr` with a fallback. Rejected -- silent fallback hides bugs, explicit map is clearer.

## Finding 2: SQL Path Works As-Is

**Confidence:** HIGH [VERIFIED: codebase inspection]

- `_DATE_COLUMN_MAP` maps filter names to SQLite columns on the `Task` table
- Projects share the `Task` table (joined via `ProjectInfo`)
- All 7 columns exist for project rows (`effectiveDateCompleted`, `effectiveDateHidden`, etc.)
- Verified by ground truth audit (todo section "Column mapping: verified, no overrides needed")
- `_add_date_conditions` uses `t.{column}` prefix -- correct for both `build_list_tasks_sql` and `build_list_projects_sql` (both query `Task t`)

**The `HasDateBounds` Protocol** (per CONTEXT.md decision):
- Currently typed as `ListTasksRepoQuery` at line 42
- `_add_date_conditions` only uses `getattr(query, f"{field_name}_after", None)` -- pure structural access
- Protocol needs 14 optional `datetime | None` properties (7 fields x `_after`/`_before`)
- Private to `query_builder.py` -- define right above `_add_date_conditions`

## Finding 3: Description Strings Analysis

**Confidence:** HIGH [VERIFIED: descriptions.py lines 153-191]

Current description strings in `descriptions.py`:

| Constant | Entity-specific content? |
|----------|------------------------|
| `DUE_FILTER_DESC` | "effective/inherited" -- applies to both tasks and projects |
| `DEFER_FILTER_DESC` | "task hidden and unavailable" -- slightly task-oriented but also applies to projects |
| `PLANNED_FILTER_DESC` | "when you intend to work on this" -- generic |
| `COMPLETED_FILTER_DESC` | "adds completed tasks" -- says "tasks" |
| `DROPPED_FILTER_DESC` | "adds dropped tasks" -- says "tasks" |
| `ADDED_FILTER_DESC` | Generic |
| `MODIFIED_FILTER_DESC` | Generic |

**Only `COMPLETED_FILTER_DESC` and `DROPPED_FILTER_DESC` say "tasks" explicitly.** The rest are entity-agnostic.

**Recommendation:** Two approaches, both valid:
1. **Reuse as-is** -- the descriptions say "tasks" but the semantics are identical for projects. Agents won't be confused. Minimal change.
2. **Template approach** -- change "tasks" to "{entity}" in the two lifecycle descriptions, format at field definition time. Slightly cleaner but adds complexity.

The CONTEXT.md says "shared description strings or templates" -- so use approach 2 for the two that differ, reuse the other 5 directly.

## Finding 4: `expand_task_availability()` Rename Impact

**Confidence:** HIGH [VERIFIED: grep across codebase]

10 references across 4 files:

| File | Count | Nature |
|------|-------|--------|
| `service/service.py` | 2 | Call sites in `_ListTasksPipeline._build_repo_query` and `_ListProjectsPipeline._build_repo_query` |
| `service/domain.py` | 1 | Method definition |
| `tests/test_service_domain.py` | 7 | Test method calls |

All references are to the method name `expand_task_availability`. Rename to `expand_availability` -- straightforward find-and-replace. No dynamic references or string-based lookups.

## Finding 5: Cross-Path Test Infrastructure

**Confidence:** HIGH [VERIFIED: test_cross_path_equivalence.py inspection]

**Existing infrastructure:**
- `_build_neutral_test_data()` already includes 4 projects with date fields (`due`, `defer`, `planned`, `completed`, `dropped`, `effective_*` variants)
- `seed_bridge_repo()` translates project date fields to bridge format (ISO strings)
- `seed_sqlite_repo()` translates project date fields to SQLite format (CF epoch floats)
- `TestDateFilterCrossPath` class has 12 tests -- all for tasks via `ListTasksRepoQuery`
- The `cross_repo` fixture parametrizes both repo types

**Neutral project data already has dates on `proj-due`** (due date set). But no projects have completed/dropped dates yet. Need to extend `_build_neutral_test_data()` to add:
- A completed project (with `effective_completed` set)
- A dropped project (with `effective_dropped` set)

**Test pattern to follow:** Mirror `TestDateFilterCrossPath` structure but with `ListProjectsRepoQuery`. Key scenarios:
- Due before/after (proj-due has due date)
- Completed date filter with COMPLETED availability
- Dropped date filter with DROPPED availability
- Lifecycle additive semantics (remaining projects preserved)
- Date filter combined with existing project filters (folder, flagged)

## Finding 6: Contract Model Changes

**Confidence:** HIGH [VERIFIED: model-taxonomy.md + existing code]

**`ListProjectsQuery`** (agent-facing, `contracts/use_cases/list/projects.py`):
- Add 7 date filter fields matching `ListTasksQuery` pattern exactly
- Same types: `Patch[DueDateShortcut | DateFilter]`, `Patch[LifecycleDateShortcut | DateFilter]`, etc.
- Add field names to `_PATCH_FIELDS` list (for null rejection validator)
- Import `DateFilter`, shortcut enums from shared `_date_filter.py` / `_enums.py`

**`ListProjectsRepoQuery`** (repo-facing):
- Add 14 `datetime | None` fields: `{field}_after` / `{field}_before` for all 7 dimensions
- Exact same field names as `ListTasksRepoQuery`

**No new models needed.** `DateFilter`, shortcut enums, `ResolvedDateBounds` are all shared.

## Finding 7: Service Pipeline Changes

**Confidence:** HIGH [VERIFIED: service.py inspection]

`_ListProjectsPipeline` currently has no date resolution. Needs:
1. `_resolve_date_filters()` method -- copy from `_ListTasksPipeline` (lines 389-408)
2. Update `_build_repo_query()` to unpack date bounds and pass lifecycle additions to `expand_availability()`
3. Call `_resolve_date_filters()` in `execute()` between `_resolve_folder()` and `_build_repo_query()`

Current `_build_repo_query` in `_ListProjectsPipeline` (line 485) already calls `expand_task_availability` with empty lifecycle_additions `[]`. After the change, it passes `self._date_result.lifecycle_additions` instead.

## Common Pitfalls

### Pitfall 1: Bridge field map divergence
**What goes wrong:** Using `_BRIDGE_FIELD_MAP` directly for projects causes `AttributeError` on `getattr(project, "effective_completion_date")`
**How to avoid:** Explicit `_BRIDGE_PROJECT_FIELD_MAP` with the `completed` override

### Pitfall 2: Missing test data for completed/dropped projects
**What goes wrong:** Cross-path tests pass vacuously because no project has lifecycle dates
**How to avoid:** Add completed and dropped projects to `_build_neutral_test_data()`

### Pitfall 3: `_PATCH_FIELDS` list not updated
**What goes wrong:** Null rejection validator doesn't cover new date fields, allowing `null` through
**How to avoid:** Add all 7 date field names to `_PATCH_FIELDS` in projects.py

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| - | (none) | - | All claims verified against codebase |

## Sources

### Primary (HIGH confidence)
- Codebase grep + runtime verification for Project model attributes
- `_BRIDGE_FIELD_MAP` at `bridge_only.py:53-61`
- `_DATE_COLUMN_MAP` at `query_builder.py:24-32`
- `descriptions.py:153-191` for description string content
- `test_cross_path_equivalence.py` for test infrastructure analysis
- `service.py` for pipeline patterns
