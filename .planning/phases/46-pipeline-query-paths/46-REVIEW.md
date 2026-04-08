---
phase: 46-pipeline-query-paths
reviewed: 2026-04-08T14:30:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/contracts/protocols.py
  - src/omnifocus_operator/repository/bridge_only/bridge_only.py
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/repository/hybrid/query_builder.py
  - src/omnifocus_operator/service/resolve_dates.py
  - src/omnifocus_operator/service/service.py
  - tests/test_due_soon_setting.py
  - tests/test_list_pipelines.py
  - tests/test_query_builder.py
  - tests/test_resolve_dates.py
  - tests/test_warnings.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 46: Code Review Report

**Reviewed:** 2026-04-08T14:30:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 46 introduces the pipeline query path: a parameterized SQL query builder, pure date filter resolution, `get_due_soon_setting` on both repository implementations, and the `_ListTasksPipeline` / `_ListProjectsPipeline` method objects. Security posture is strong -- all SQL user values flow through `?` placeholders (INFRA-01), confirmed by comprehensive query builder tests. The date resolver is cleanly separated as a pure function with no I/O. Test coverage is thorough across all three layers.

Two warnings identified: an unescaped LIKE wildcard issue in the SQL query builder's search parameter, and a `matches_inbox_name` function that produces false positives for short strings. Three info-level items cover code duplication, an unused import pattern, and a minor naming concern.

## Warnings

### WR-01: LIKE wildcard characters in search input are not escaped

**File:** `src/omnifocus_operator/repository/hybrid/query_builder.py:203-204` (same pattern at lines 268-269)
**Issue:** The search parameter is wrapped with `%` for LIKE matching but the user's input is not escaped for LIKE metacharacters. If a user searches for a literal `%` or `_`, these act as wildcards in SQLite LIKE. For example, searching for `"100%"` would match `"100 things"` because `%` is a wildcard. The same pattern appears in `build_list_projects_sql` at line 268.

This is not a SQL injection vulnerability (the `?` parameterization prevents that), but it is a correctness issue: the search results will be broader than expected when input contains `%` or `_`.

The bridge-only path (`bridge_only.py:197-201`) uses Python `in` for string matching, which is literal and does not have this issue -- creating a behavioral inconsistency between the two repository implementations.

**Fix:** Escape LIKE metacharacters before wrapping with `%`:
```python
def _escape_like(value: str) -> str:
    """Escape LIKE wildcards for literal matching."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

# In build_list_tasks_sql and build_list_projects_sql:
if query.search is not None:
    conditions.append(
        "(t.name LIKE ? ESCAPE '\\' COLLATE NOCASE"
        " OR t.plainTextNote LIKE ? ESCAPE '\\' COLLATE NOCASE)"
    )
    escaped = f"%{_escape_like(query.search)}%"
    params.append(escaped)
    params.append(escaped)
```

---

### WR-02: `matches_inbox_name` returns True for any single character found in "inbox"

**File:** `src/omnifocus_operator/service/service.py:99-103`
**Issue:** The function checks `value.lower() in "inbox"` -- meaning value must be a **substring of** "inbox". This causes false positives: `"n"`, `"o"`, `"x"`, `"bo"`, `"ox"` all return True. Any single-character search value that appears in the word "inbox" will trigger the inbox warning. For example, `project="o"` would produce a misleading "Inbox is a virtual location" warning.

The test suite intentionally tests `"inb"` returning True (line 388-393 in test_list_pipelines.py), suggesting this breadth is deliberate for prefix matching. But the current implementation also matches non-prefix substrings like `"x"` or `"box"`, which are unlikely to be inbox-related searches.

**Fix:** If the intent is prefix matching, use `startswith`:
```python
def matches_inbox_name(value: object) -> bool:
    """Check if a value is a case-insensitive prefix of 'Inbox'."""
    if not isinstance(value, str):
        return False
    return "inbox".startswith(value.lower())
```
This preserves `"in"` -> True, `"inb"` -> True, `"inbox"` -> True, while fixing `"x"` -> False, `"box"` -> False.

## Info

### IN-01: `_paginate` helper duplicated across two repository modules

**File:** `src/omnifocus_operator/repository/bridge_only/bridge_only.py:64-75` and `src/omnifocus_operator/repository/hybrid/hybrid.py:78-89`
**Issue:** Identical `_paginate` function is copy-pasted in both repository implementations. Additionally, `list_tasks` and `list_projects` in `bridge_only.py` (lines 221-232, 260-272) use an inline pagination formula `(offset + len(items)) < total` instead of calling the `_paginate` helper defined in the same file.
**Fix:** Extract `_paginate` into a shared module (e.g., `repository/pagination.py`) and use it consistently in both `list_tasks` and `list_projects` instead of the inline formula.

---

### IN-02: `_ListTasksPipeline` fetches all projects and all tags unconditionally

**File:** `src/omnifocus_operator/service/service.py:344-351`
**Issue:** `execute()` always issues two repo queries via `asyncio.gather` -- `list_tags(limit=None)` and `list_projects(limit=None)` -- even when neither `query.project` nor `query.tags` are set. When both filters are unset, these are wasted I/O (two full table scans on the hybrid path). The results are used only in `_resolve_project` and `_resolve_tags`, which both short-circuit when the query field is unset.

Not a correctness issue. Performance is out of v1 scope, flagged for awareness.

**Fix:** Gate the resolution queries behind `is_set()` checks on the respective query fields.

---

### IN-03: Inline `list_tasks` / `list_projects` pagination diverges from `_paginate` helper

**File:** `src/omnifocus_operator/repository/bridge_only/bridge_only.py:221-232`
**Issue:** `list_tasks` and `list_projects` in `BridgeOnlyRepository` compute `has_more` using `(offset + len(items)) < total` after limit-slicing, while other list methods (`list_tags`, `list_folders`, `list_perspectives`) delegate to the `_paginate` helper which uses `len(items) > limit` before slicing. Both formulas produce correct results, but the inconsistency makes the codebase harder to reason about and creates risk if one formula is updated without the other.
**Fix:** Use `_paginate` consistently, or extract the inline pagination into a clearly documented shared pattern.

---

_Reviewed: 2026-04-08T14:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
