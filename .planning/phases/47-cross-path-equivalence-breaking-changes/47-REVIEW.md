---
phase: 47-cross-path-equivalence-breaking-changes
reviewed: 2026-04-09T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/contracts/use_cases/list/_enums.py
  - src/omnifocus_operator/contracts/use_cases/list/projects.py
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
  - src/omnifocus_operator/repository/bridge_only/bridge_only.py
  - src/omnifocus_operator/repository/hybrid/query_builder.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/service/resolve_dates.py
  - tests/test_cross_path_equivalence.py
  - tests/test_date_filter_contracts.py
  - tests/test_errors.py
  - tests/test_list_contracts.py
  - tests/test_list_pipelines.py
  - tests/test_resolve_dates.py
  - tests/test_service_domain.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 47: Code Review Report

**Reviewed:** 2026-04-09
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 47 introduces cross-path equivalence tests proving `BridgeOnlyRepository` and `HybridRepository` produce identical results, along with supporting changes to date filter contracts, availability enums, and domain logic. The overall architecture is clean and the test design is solid. No security issues or critical bugs found.

Three warnings: a SQLite seed adapter that silently uses a wrong sentinel date for completed/dropped tasks, a missing consumer module in the error-consolidation scanner, and a timezone-awareness gap in absolute datetime parsing. Four info items: deferred imports inside a loop, a redundant type guard, a docstring gap in `_resolve_shortcut`, and a minor `has_more` inconsistency between the two pagination paths.

---

## Warnings

### WR-01: SQLite seed uses wrong sentinel dates for completed/dropped availability defaults

**File:** `tests/test_cross_path_equivalence.py:561-563`

**Issue:** `_SQLITE_TASK_AVAILABILITY` hard-codes sentinel dates for the "completed" and "dropped" map entries:

```python
"completed": {"blocked": 0, "dateCompleted": _to_cf_epoch(_MODIFIED), "dateHidden": None},
"dropped": {"blocked": 0, "dateCompleted": None, "dateHidden": _to_cf_epoch(_MODIFIED)},
```

The seed adapter correctly overrides these when the neutral data supplies an explicit date (lines 674-686). But if a future test author creates a task with `"availability": "completed"` and `"completed": None`, the fallback inserts `_MODIFIED` as the completion date instead of `None`. This produces a silently wrong SQLite row — the task will appear completed at `_MODIFIED`, which is not what the neutral data says. The existing test data avoids this (task-5 has explicit `_COMPLETED_DATE`), so the bug is latent, not currently triggered.

**Fix:** Default both date columns to `None`; the neutral data override block that follows is the authoritative source:

```python
_SQLITE_TASK_AVAILABILITY = {
    "available": {"blocked": 0, "dateCompleted": None, "dateHidden": None},
    "blocked": {"blocked": 1, "dateCompleted": None, "dateHidden": None},
    "completed": {"blocked": 0, "dateCompleted": None, "dateHidden": None},
    "dropped": {"blocked": 0, "dateCompleted": None, "dateHidden": None},
}
```

---

### WR-02: `test_errors.py` does not scan `contracts/use_cases/list/tasks.py` for inline errors

**File:** `tests/test_errors.py:32-50`

**Issue:** `_ERROR_CONSUMERS` includes `contracts_list_validators`, `contracts_list_projects`, `contracts_list_folders`, and `contracts_list_tags`, but omits `contracts/use_cases/list/tasks.py`. That module currently delegates null-rejection to `_validators.py`, but it has its own `@field_validator` for tags and its own `_PATCH_FIELDS` list. If a contributor ever adds a direct error reference or inline error string to `tasks.py`, neither `test_no_inline_error_strings_in_consumers` nor `test_all_error_constants_referenced_in_consumers` will catch it.

**Fix:**

```python
from omnifocus_operator.contracts.use_cases.list import tasks as contracts_list_tasks

_ERROR_CONSUMERS = [
    ...
    contracts_list_tasks,
    contracts_list_validators,
    ...
]
```

---

### WR-03: `_parse_absolute_after` / `_parse_absolute_before` drop timezone for full datetime strings

**File:** `src/omnifocus_operator/service/resolve_dates.py:227, 240`

**Issue:** Both functions explicitly inherit `now.tzinfo` for date-only strings (documented in their docstrings), but fall through to bare `datetime.fromisoformat(value)` for full datetime strings (e.g. `"2026-04-01T14:00:00"`). When the input has no timezone suffix, `fromisoformat` returns a naive datetime. If `now` is tz-aware (as it is in production — the service layer passes a UTC-aware timestamp), comparing this naive result against task model `AwareDatetime` fields in the bridge path raises a `TypeError: can't compare offset-naive and offset-aware datetimes` at runtime.

The existing tests in `test_resolve_dates.py` use a naive `NOW`, so this path is not exercised. The cross-path equivalence tests in `test_cross_path_equivalence.py` do not use absolute datetime strings, so the gap is also not caught there.

**Fix:** Apply `now.tzinfo` to the full datetime path consistently:

```python
def _parse_absolute_after(value: str, now: datetime) -> datetime:
    if value == "now":
        return now
    if _is_date_only(value):
        d = date.fromisoformat(value)
        return datetime(d.year, d.month, d.day, tzinfo=now.tzinfo)
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None and now.tzinfo is not None:
        return dt.replace(tzinfo=now.tzinfo)
    return dt
```

Apply the same pattern to `_parse_absolute_before`.

---

## Info

### IN-01: Deferred imports inside a loop in `resolve_date_filters`

**File:** `src/omnifocus_operator/service/domain.py:181-187`

**Issue:** Inside the `for field_name in self._DATE_FIELD_NAMES:` loop, two imports are deferred:

```python
from omnifocus_operator.agent_messages.warnings import (
    DEFER_AFTER_NOW_HINT,
    DEFER_BEFORE_NOW_HINT,
)
from omnifocus_operator.contracts.use_cases.list._date_filter import (
    DateFilter,
)
```

These execute on every loop iteration (Python caches module imports, so the performance cost is negligible, but the placement is misleading — it implies these are conditionally needed). They should be at module level with the rest of the imports in this file.

**Fix:** Move both import blocks to the top of `domain.py` alongside the existing imports.

---

### IN-02: Redundant `ReviewDueFilter` check in `_parse_review_due_within`

**File:** `src/omnifocus_operator/contracts/use_cases/list/projects.py:89`

**Issue:** The early-return guard `isinstance(v, (ReviewDueFilter, _Unset))` protects against double-parsing when the field is already resolved. The `_Unset` guard is meaningful (protects UNSET from being passed to `.format()`). The `ReviewDueFilter` guard is unusual for a `mode="before"` validator — at that point Pydantic passes the raw user input, not a constructed model. The check is harmless but unexplained and slightly confusing for future readers.

**Fix:** Add a comment clarifying the intent:

```python
@field_validator("review_due_within", mode="before")
@classmethod
def _parse_review_due_within(cls, v: object) -> object:
    # Pass through if already resolved (programmatic construction) or UNSET
    if isinstance(v, (ReviewDueFilter, _Unset)):
        return v
    ...
```

---

### IN-03: `_resolve_shortcut` raises `ValueError` for a programming-contract violation

**File:** `src/omnifocus_operator/service/resolve_dates.py:102-107`

**Issue:** The `"all"` branch raises `ValueError`, which is normally reserved for user-input errors. This path is unreachable under correct usage — the domain layer filters out `"all"` before calling `resolve_date_filter` (domain.py line 197). The `ValueError` would only surface if a developer incorrectly calls the function directly. Using `AssertionError` or `raise RuntimeError` would communicate this as a programming contract violation, not a user-input problem, and would not accidentally be caught by `except ValueError` handlers.

**Fix:**

```python
if value == "all":
    raise AssertionError(
        f"'all' on field '{field_name}' is not a date filter -- "
        "the domain must handle this before calling resolve_date_filter."
    )
```

---

### IN-04: `_paginate` and `list_tasks`/`list_projects` use different `has_more` formulas

**File:** `src/omnifocus_operator/repository/bridge_only/bridge_only.py:71, 231, 270`

**Issue:** `list_tasks` (line 231) and `list_projects` (line 270) compute `has_more` as `(offset + len(items)) < total`. After applying the limit slice, `len(items)` is at most `limit`. The formula is equivalent to `offset + min(limit, remaining) < total`, which is correct.

`_paginate` (used by `list_tags`, `list_folders`, `list_perspectives`) computes `has_more = len(items) > limit` before slicing — also correct.

However the two formulas are not obviously equivalent at a glance, and `_paginate` is not used for tasks/projects. A reader auditing these methods might not realize they produce the same result, especially if pagination behavior ever needs to change. The inconsistency is not a bug but will cause confusion during future edits.

**Fix:** Consider using `_paginate` in `list_tasks` and `list_projects` as well, or at minimum adding a comment in `list_tasks`/`list_projects` explaining why the inline formula matches `_paginate` semantics.

---

_Reviewed: 2026-04-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
