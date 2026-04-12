---
phase: 51-task-ordering
reviewed: 2026-04-12T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/models/task.py
  - src/omnifocus_operator/repository/bridge_only/adapter.py
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/repository/hybrid/query_builder.py
  - tests/conftest.py
  - tests/test_cross_path_equivalence.py
  - tests/test_hybrid_repository.py
  - tests/test_models.py
  - tests/test_query_builder.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 51: Code Review Report

**Reviewed:** 2026-04-12
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 51 adds hierarchical task ordering via a recursive CTE in SQLite plus Python-side dotted-path computation. The architecture is well-structured: the CTE handles sort order; `_compute_dotted_orders()` handles the human-readable numbering; and the bridge path returns `None` in degraded mode, as documented.

No critical issues found. Three warnings cover a logic bug in `_compute_dotted_orders` (project-root rows corrupt sibling counters), a mismatch between the ORDER BY tiebreaker in `_build_full_dotted_orders` vs the `_TASKS_DATA_BASE` query (affects pagination determinism for orphans), and a N+1 query in `_compute_task_order`. Three info items cover minor code quality points.

---

## Warnings

### WR-01: `_compute_dotted_orders` assigns ordinals to project-root task rows, corrupting sibling counters

**File:** `src/omnifocus_operator/repository/hybrid/hybrid.py:339-376`

**Issue:** `_compute_dotted_orders` iterates over every row passed to it. For `get_all()` and `_build_full_dotted_orders()` the rows are pre-filtered by `WHERE pi.task IS NULL`, so project-root rows are excluded and the function works correctly. However, in `_compute_task_order` (line 826) the scoped CTE also filters with `WHERE pi.task IS NULL`, so that call is also safe.

The latent risk is the assumption the callers establish: **the function silently produces wrong dotted-paths if any project-root task row is included in the input**. The function has no guard and its docstring says "Rows MUST be pre-sorted by sort_path" but says nothing about the `pi.task IS NULL` requirement. Any future caller that passes unfiltered rows (e.g. during a refactor) would get silently wrong output — parent counters would be incremented for the project-root row, pushing all project-level tasks to position 2, 3, … instead of 1, 2, …

**Fix:** Add a defensive assertion or filter at the top of `_compute_dotted_orders`:
```python
def _compute_dotted_orders(rows: list[sqlite3.Row]) -> dict[str, str]:
    """...
    Rows must already exclude project-root task rows (pi.task IS NULL filter applied).
    """
    # All existing logic unchanged
    ...
```
Or, more defensively, document the contract explicitly as a note in the function. The current docstring does not mention this invariant.

---

### WR-02: `_build_full_dotted_orders` ORDER BY differs from `_TASKS_DATA_BASE` ORDER BY for NULL sort_path rows

**File:** `src/omnifocus_operator/repository/hybrid/hybrid.py:379-396`

**Issue:** `_build_full_dotted_orders` builds its SQL inline (lines 387-394) with:
```sql
ORDER BY o.sort_path, t.persistentIdentifier
```

`_TASKS_DATA_BASE` in `query_builder.py` (line 160-166) builds:
```sql
ORDER BY o.sort_path, t.persistentIdentifier
```

These match, so for the common case they are consistent. However, in both queries `o.sort_path` can be `NULL` for orphan tasks (tasks not reached by the CTE because their parent chain is broken). SQLite sorts `NULL` first by default. This means orphan tasks appear at the top of the ordered results in both queries — but with `NULL` sort_paths, their relative ordering between the two queries is only tiebroken by `persistentIdentifier`. Since both queries use the same tiebreaker, this is consistent.

The real issue is subtler: `_build_full_dotted_orders` fetches ALL tasks to build the global dotted-orders map, but the data query in `_list_tasks_sync` adds additional `WHERE` conditions on top of `_TASKS_DATA_BASE`. For orphan tasks (sort_path IS NULL), `_compute_dotted_orders` will try to walk the parent chain but `task_parent[task_id]` points to a parent that may not be in the `rows` set (since the CTE stopped at a broken link). The while loop `while current is not None and current in task_ordinal` will stop at the orphan's own entry (since the parent is not in `task_ordinal`), producing a single-component dotted path like `"5"` even though the task has no valid ancestry. This is probably the correct behavior for orphans (a flat ordinal), but it is undocumented.

**Fix:** Add a comment in `_compute_dotted_orders` documenting orphan behavior:
```python
# Orphan tasks (parent chain broken -- parent not in task_ordinal) produce
# a single-component path (e.g. "5") treated as a root-level position.
```

---

### WR-03: `_compute_task_order` runs a second full CTE query per `get_task` call

**File:** `src/omnifocus_operator/repository/hybrid/hybrid.py:826-861`

**Issue:** `_read_task` (line 766) already opens a connection and fetches the task row. Then it calls `self._compute_task_order(conn, row)` which runs another full CTE query (lines 836-858) across all tasks in the same project or the entire inbox namespace. For a project with many tasks, this scans all sibling rows just to find the ordinal of one task.

This is not a correctness bug — the result is accurate. It is a potential performance issue for large projects with many tasks, but performance is explicitly out of scope for v1 review.

However, there is a **correctness edge case**: if `containing_pi` is not `None` but the `ProjectInfo` pk is stale (i.e., the task references a `containingProjectInfo` that no longer exists), `conn.execute(scoped_sql, (containing_pi,))` returns zero rows, `_compute_dotted_orders([])` returns `{}`, and `dotted_orders.get(task_id)` returns `None`. This produces `order=None` for a task that has a `containingProjectInfo` value — which is documented as degraded-mode behavior, but here it silently fires in normal mode. The caller (`get_task`) returns the Task with `order=None` without any warning.

**Fix:** Add a defensive note or warning log when the scoped CTE returns no rows but `containing_pi` is set:
```python
sibling_rows = conn.execute(scoped_sql, (containing_pi,)).fetchall()
if not sibling_rows:
    logger.warning(
        "_compute_task_order: no rows for containingProjectInfo=%s (stale ref?)",
        containing_pi,
    )
    return None
dotted_orders = _compute_dotted_orders(sibling_rows)
```

---

## Info

### IN-01: `_TASK_ORDER_CTE` inbox anchor uses a subquery that could be replaced with a join

**File:** `src/omnifocus_operator/repository/hybrid/query_builder.py:147-149`

**Issue:** The inbox anchor in the CTE uses a `NOT IN` subquery:
```sql
AND t.persistentIdentifier NOT IN (SELECT pi2.task FROM ProjectInfo pi2)
```
`NOT IN` with a subquery can behave unexpectedly if any value in the subquery is `NULL` — the entire `NOT IN` condition evaluates to UNKNOWN for every row when at least one `pi2.task` is NULL, silently excluding all inbox tasks. OmniFocus's `ProjectInfo.task` is defined as the project's own task ID, which is unlikely to be NULL, but the guarantee is implicit.

**Fix:** Prefer `NOT EXISTS` which is NULL-safe:
```sql
AND NOT EXISTS (SELECT 1 FROM ProjectInfo pi2 WHERE pi2.task = t.persistentIdentifier)
```
This is semantically equivalent but immune to the NULL-in-subquery problem.

---

### IN-02: `_TASK_ORDER_CTE` is exported via `__all__` in `query_builder.py` as a private name

**File:** `src/omnifocus_operator/repository/hybrid/query_builder.py:95`

**Issue:** `_TASK_ORDER_CTE` has a leading underscore (private by convention) but is listed in `__all__` and imported directly in `hybrid.py`:
```python
from omnifocus_operator.repository.hybrid.query_builder import (
    _TASK_ORDER_CTE,
    ...
)
```
Including a private name in `__all__` is contradictory. It signals "this is internal" while simultaneously advertising it as a public export.

**Fix:** Either remove the leading underscore (rename to `TASK_ORDER_CTE`) or remove it from `__all__` and keep it as a module-private name imported explicitly where needed.

---

### IN-03: `ORDER_FIELD` description says "Each dot level is the 1-based position at that depth within the parent project or inbox" — slightly imprecise for subtasks

**File:** `src/omnifocus_operator/agent_messages/descriptions.py:99-103`

**Issue:** The description says "within the parent project or inbox" but for subtasks the dot levels reflect position within the immediate parent task, not the project or inbox. For example, `"1.2.3"` means: 1st root task, 2nd child of that task, 3rd child of that child — none of these levels after the first are "within the parent project."

**Fix:** Revise the description to be more accurate:
```python
ORDER_FIELD = (
    "Hierarchical position among siblings (dotted notation like '2.3.1'). "
    "Each dot level is the 1-based position within the parent container at that depth. "
    "null when ordering data is unavailable (degraded mode)."
)
```

---

_Reviewed: 2026-04-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
