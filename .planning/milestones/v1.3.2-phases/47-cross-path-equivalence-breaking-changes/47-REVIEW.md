---
phase: 47-cross-path-equivalence-breaking-changes
reviewed: 2026-04-09T14:07:58Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/contracts/use_cases/list/__init__.py
  - src/omnifocus_operator/contracts/use_cases/list/_enums.py
  - src/omnifocus_operator/contracts/use_cases/list/projects.py
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
  - src/omnifocus_operator/repository/bridge_only/bridge_only.py
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/repository/hybrid/query_builder.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/service/resolve_dates.py
  - tests/test_cross_path_equivalence.py
  - tests/test_date_filter_contracts.py
  - tests/test_due_soon_setting.py
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

**Reviewed:** 2026-04-09T14:07:58Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Phase 47 introduces cross-path equivalence tests proving BridgeOnlyRepository and HybridRepository produce identical results for all list operations, alongside date filter contracts, availability enums, due-soon threshold detection, and domain logic for resolving date filters. The architecture is clean: neutral test data defined once with seed adapters for each repository path, parameterized fixtures for cross-path comparison, and a layered resolution pipeline (contract enums -> domain logic -> absolute datetime bounds -> repo queries).

No security issues or critical bugs found. Three warnings: a timezone-awareness gap in absolute datetime parsing that would cause a runtime TypeError with tz-aware inputs, a SQLite seed adapter with latent incorrect sentinel dates, and a missing module in the error-consolidation scanner. Four info items covering code clarity and consistency.

## Warnings

### WR-01: Naive datetime returned by absolute date parser when input lacks timezone

**File:** `src/omnifocus_operator/service/resolve_dates.py:227, 240`

**Issue:** `_parse_absolute_after` and `_parse_absolute_before` correctly inherit `now.tzinfo` for date-only strings (e.g. `"2026-04-01"`) and for the `"now"` literal. However, for full datetime strings without a timezone suffix (e.g. `"2026-04-01T14:00:00"`), both functions call `datetime.fromisoformat(value)` which returns a naive datetime.

In production, the service layer passes a UTC-aware `now` timestamp. When the bridge-only repository compares these resolved bounds against Task model `AwareDatetime` fields, a `TypeError: can't compare offset-naive and offset-aware datetimes` will be raised at runtime. This path is not exercised by existing tests because `test_resolve_dates.py` uses a naive `NOW` fixture and `test_cross_path_equivalence.py` does not use absolute datetime filter strings.

**Fix:** Apply the same tz-inheritance pattern to the full datetime fallback:

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

### WR-02: SQLite seed adapter has latent incorrect sentinel dates for completed/dropped

**File:** `tests/test_cross_path_equivalence.py:559-563`

**Issue:** `_SQLITE_TASK_AVAILABILITY` maps availability strings to SQLite column defaults:

```python
"completed": {"blocked": 0, "dateCompleted": _to_cf_epoch(_MODIFIED), "dateHidden": None},
"dropped": {"blocked": 0, "dateCompleted": None, "dateHidden": _to_cf_epoch(_MODIFIED)},
```

The seed adapter (lines 672-686) correctly overrides these when the neutral data supplies explicit dates. But if a future test adds a task with `"availability": "completed"` and `"completed": None` (intentionally no completion date -- e.g., testing an edge case), the fallback silently inserts `_MODIFIED` as the completion timestamp, producing a wrong SQLite row. The existing test data always supplies explicit dates for completed/dropped tasks, so this is latent.

**Fix:** Default the date columns to `None` in the map; the explicit override block is the authoritative source:

```python
_SQLITE_TASK_AVAILABILITY = {
    "available": {"blocked": 0, "dateCompleted": None, "dateHidden": None},
    "blocked": {"blocked": 1, "dateCompleted": None, "dateHidden": None},
    "completed": {"blocked": 0, "dateCompleted": None, "dateHidden": None},
    "dropped": {"blocked": 0, "dateCompleted": None, "dateHidden": None},
}
```

---

### WR-03: `test_errors.py` does not scan `contracts/use_cases/list/tasks.py` for inline errors

**File:** `tests/test_errors.py:32-50`

**Issue:** `_ERROR_CONSUMERS` includes `contracts_list_validators`, `contracts_list_projects`, `contracts_list_folders`, and `contracts_list_tags`, but omits `contracts/use_cases/list/tasks.py`. That module has its own `@field_validator` (`_reject_empty_tags`) and `_PATCH_FIELDS` list. While it currently delegates error handling to `_validators.py`, if a contributor adds a direct error reference or inline error string to `tasks.py`, neither the inline-error scanner nor the referenced-constants check will detect it.

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

## Info

### IN-01: Deferred imports inside a loop in `resolve_date_filters`

**File:** `src/omnifocus_operator/service/domain.py:181-187`

**Issue:** Inside the `for field_name in self._DATE_FIELD_NAMES:` loop, two import blocks are deferred:

```python
from omnifocus_operator.agent_messages.warnings import (
    DEFER_AFTER_NOW_HINT,
    DEFER_BEFORE_NOW_HINT,
)
from omnifocus_operator.contracts.use_cases.list._date_filter import (
    DateFilter,
)
```

Python caches module imports after first load, so the runtime cost is negligible, but the placement inside the loop is misleading -- it implies these are conditionally needed per iteration. They should be at module level alongside the existing warning imports at the top of the file.

**Fix:** Move both import blocks to the top of `domain.py` with the other imports from the same packages.

---

### IN-02: Redundant `ReviewDueFilter` type guard in `mode="before"` validator

**File:** `src/omnifocus_operator/contracts/use_cases/list/projects.py:89`

**Issue:** The `_parse_review_due_within` validator has `isinstance(v, (ReviewDueFilter, _Unset))` as an early return guard. In `mode="before"`, Pydantic passes raw user input, not constructed models, so `ReviewDueFilter` should not appear. The guard is harmless (protects programmatic construction paths) but is unexplained, creating reader confusion.

**Fix:** Add a clarifying comment:

```python
# Pass through if already resolved (programmatic construction) or UNSET
if isinstance(v, (ReviewDueFilter, _Unset)):
    return v
```

---

### IN-03: `_resolve_shortcut` raises `ValueError` for a programming-contract violation

**File:** `src/omnifocus_operator/service/resolve_dates.py:102-107`

**Issue:** The `"all"` branch raises `ValueError`, which is normally reserved for user-input errors. This path is unreachable under correct usage -- the domain layer filters `"all"` before calling `resolve_date_filter`. Using `AssertionError` (matching the `"soon"` guard on line 93) would communicate this as a programming contract violation rather than a user error, and would avoid being accidentally swallowed by `except ValueError` handlers.

**Fix:**

```python
if value == "all":
    raise AssertionError(
        f"'all' on field '{field_name}' is not a date filter -- "
        "the domain must handle this before calling resolve_date_filter."
    )
```

---

### IN-04: Two different `has_more` computation patterns in BridgeOnlyRepository

**File:** `src/omnifocus_operator/repository/bridge_only/bridge_only.py:75, 251, 290`

**Issue:** `_paginate` (line 75, used for tags/folders/perspectives) computes `has_more = len(items) > limit` before slicing. `list_tasks` (line 251) and `list_projects` (line 290) compute `has_more = (offset + len(items)) < total` after slicing. Both are correct but use different formulas that are not obviously equivalent at a glance. If pagination behavior ever needs to change, a maintainer might fix one pattern and miss the other.

**Fix:** Either use `_paginate` consistently for all entity types, or add a comment in `list_tasks`/`list_projects` explaining why the inline formula matches `_paginate` semantics.

---

_Reviewed: 2026-04-09T14:07:58Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
