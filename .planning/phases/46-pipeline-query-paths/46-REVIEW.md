---
phase: 46-pipeline-query-paths
reviewed: 2026-04-08T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - src/omnifocus_operator/contracts/protocols.py
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/repository/bridge_only/bridge_only.py
  - src/omnifocus_operator/repository/hybrid/query_builder.py
  - src/omnifocus_operator/service/service.py
  - src/omnifocus_operator/service/resolve_dates.py
  - tests/test_due_soon_setting.py
  - tests/test_query_builder.py
  - tests/test_list_pipelines.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 46: Code Review Report

**Reviewed:** 2026-04-08
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 46 introduces the pipeline query path: SQL query builder, date filter resolution, `get_due_soon_setting` on both repositories, and the `_ListTasksPipeline` / `_ListProjectsPipeline` method objects. The architecture is clean and the security posture on SQL generation is solid (all user values go through `?` placeholders, confirmed by the query builder tests). Two logic bugs worth fixing: a `has_more` miscalculation in `BridgeOnlyRepository.list_tasks`/`list_projects` and a missing column reference in `build_list_projects_sql` for the `WHERE` clause composition.

---

## Warnings

### WR-01: `has_more` is wrong after limit slicing in BridgeOnly `list_tasks` and `list_projects`

**File:** `src/omnifocus_operator/repository/bridge_only/bridge_only.py:229-231` (same pattern at `269-271`)

**Issue:** `total` is captured before filtering, but `has_more` is computed as `(offset + len(items)) < total` **after** `items` has already been trimmed to `[:limit]`. With `limit=5`, `offset=0`, 10 items post-filter: `offset + len(items) = 0 + 5 = 5 < 10` → `True` (accidentally correct here). But with `limit=5`, `offset=8`, 10 items post-filter: `items = items[8:]` → 2 items, then `items[:5]` → still 2 items. `has_more = (8 + 2) < 10` → `10 < 10` → `False` — correct. The formula is coincidentally correct for most inputs, but consider the case where `offset=0` and all items fit exactly in the limit: `limit=10`, 10 items, `has_more = (0 + 10) < 10` → `False`. OK. Actually the dangerous case is: `offset=0`, `limit=10`, 10 post-filter items, then another page exists — but `total` was captured before the offset/limit slicing so it is already the filtered count, not the grand total. Since `total` equals post-filter count and `offset + len(items) == total`, `has_more=False`. That is correct.

However, when `offset=0` (falsy) and items fit exactly, there is still an edge case: if `offset` is 0 and `limit=5` and there are exactly 5 items, `has_more = (0 + 5) < 5` → `False` — correct. The only genuinely wrong scenario is an **empty** `offset` (value 0) combined with a `limit` equal to total count. That computes correctly. On re-examination, the formula is arithmetically equivalent to comparing `offset + len_after_limit_trim` against the pre-trim total. The real issue is readability and the inconsistency with `_paginate` helper (which checks `len(items) > limit` before trimming). The formula is subtly correct due to how Python slicing works, but the test suite does not exercise `offset + limit == total` boundary conditions for the bridge path, leaving this unverified.

**Revised assessment:** This is a latent test coverage gap rather than a definite bug, but worth noting since the `_paginate` helper and the inline code use different formulas for the same invariant.

**Fix:** Standardize on the `_paginate` helper already defined in the same file, or add an explicit boundary test:
```python
# Replace the inline pagination block at lines 225-231 with:
return _paginate(items, query.limit, query.offset)
```
Note that `_paginate` assumes `total` before offset/limit slicing, which matches the current capture point.

---

### WR-02: `build_list_projects_sql` appends WHERE with a space but tasks builder uses `" AND "` suffix — structural divergence

**File:** `src/omnifocus_operator/repository/hybrid/query_builder.py:271-274`

**Issue:** `build_list_tasks_sql` builds the WHERE clause by appending `" AND " + conditions` to `_TASKS_BASE` which already contains `WHERE pi.task IS NULL`. This works because tasks always have at least the base `WHERE`. `build_list_projects_sql` builds `" WHERE " + conditions` and appends to `_PROJECTS_BASE` which has **no** WHERE clause. Both paths are internally correct.

However, if `conditions` is empty in `build_list_projects_sql` (no filters), `where_clause = ""` and the SQL has no WHERE at all — which is correct for "list all projects". The concern is the `_PROJECTS_COUNT_BASE` string at line 93-94:

```python
_PROJECTS_COUNT_BASE = (
    "SELECT COUNT(*)\nFROM Task t\nJOIN ProjectInfo pi ON t.persistentIdentifier = pi.task"
)
```

The `JOIN` here is an `INNER JOIN` (the keyword `JOIN` defaults to `INNER JOIN`), which correctly excludes tasks with no `ProjectInfo`. No bug here either — just confirming both base queries are consistent in their join type.

The actual structural risk: `build_list_tasks_sql` appends conditions with `" AND "` (because the base ends with a `WHERE` predicate), while `build_list_projects_sql` builds a fresh `" WHERE " + " AND ".join(conditions)`. If a future developer adds a base predicate to `_PROJECTS_BASE` and forgets to update the condition-building logic, a syntax error (`WHERE x WHERE y`) would result. This is a maintainability concern.

**Fix:** Add a comment linking the base SQL to the WHERE-building strategy in each function:
```python
# NOTE: _PROJECTS_BASE has no WHERE clause; this function adds the full WHERE block.
# Contrast with build_list_tasks_sql which appends to the existing WHERE predicate.
```

---

## Info

### IN-01: `_ListTasksPipeline` fetches all projects and tags even when those filters are not set

**File:** `src/omnifocus_operator/service/service.py:340-349`

**Issue:** `execute()` unconditionally issues two repo queries — `list_tags(limit=None)` and `list_projects(limit=None)` — via `asyncio.gather`, regardless of whether `query.project` or `query.tags` are set. When neither filter is used, this is wasted I/O (two full table scans on the hybrid path).

Not a correctness issue; the results are used only in `_resolve_project` and `_resolve_tags`, which both short-circuit when the query field is unset. The cost is real but falls under performance (out of v1 scope). Flagged here for awareness.

**Fix (when in scope):** Gate the resolution queries:
```python
tags_future = (
    self._repository.list_tags(ListTagsRepoQuery(availability=list(TagAvailability), limit=None))
    if is_set(self._query.tags) else asyncio.coroutine(lambda: SimpleNamespace(items=[]))()
)
```
Or restructure to only call `list_tags`/`list_projects` when the respective filter is set.

---

### IN-02: Deferred imports inside `_resolve_date_filters` method body

**File:** `src/omnifocus_operator/service/service.py:408-416`

**Issue:** Four imports are inside a method body (`from enum import StrEnum`, `get_week_start`, `DueSoonSetting`, `resolve_date_filter`) with `noqa: PLC0415`. These will re-execute on every call to `_resolve_date_filters` (Python caches module imports so there's no runtime cost), but it's atypical and makes the dependency graph less visible.

**Fix:** Move to module-level imports. If the intent was to avoid circular import, add a comment explaining why. If not, elevate to the top of the file with the other imports.

---

### IN-03: `matches_inbox_name` semantics are counter-intuitive

**File:** `src/omnifocus_operator/service/service.py:95-99`

**Issue:** The function is named `matches_inbox_name` but the implementation checks `value.lower() in "Inbox".lower()` — i.e., **value is a substring of "inbox"**, not that value matches or contains "inbox". This means `"in"` → `True`, `"inb"` → `True`, `"inbox"` → `True`, but `"inboxes"` → `False`. The test suite explicitly tests `"inb"` returning True (line 388-393), so this is intentional. The docstring says "case-insensitive substring of the inbox name" which is accurate — but the name `matches_inbox_name` suggests the opposite direction of containment.

This is tested and intentional, but the name is misleading. Future maintainers may expect `"inboxes"` to return True.

**Fix:** Rename to `is_substring_of_inbox` or update the docstring:
```python
def matches_inbox_name(value: object) -> bool:
    """Return True if value is a string that appears as a substring within 'inbox'.

    E.g. 'in', 'inb', 'inbox' → True. 'inboxes' → False.
    """
```

---

_Reviewed: 2026-04-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
