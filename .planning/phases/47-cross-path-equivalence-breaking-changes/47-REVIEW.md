---
phase: 47-cross-path-equivalence-breaking-changes
reviewed: 2026-04-08T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/contracts/use_cases/list/_enums.py
  - src/omnifocus_operator/contracts/use_cases/list/projects.py
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
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
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 47: Code Review Report

**Reviewed:** 2026-04-08
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 47 introduces cross-path equivalence tests proving that `BridgeOnlyRepository` and `HybridRepository` produce identical results, along with supporting changes to date filter contracts, availability enums, and domain logic. The code is generally well-structured and the test design is solid. No security issues or critical bugs were found.

Two warnings: one is a logic gap in the `_SQLITE_TASK_AVAILABILITY` defaults map for the "completed" case (falls back to a wrong sentinel date when actual completion date is not in neutral data), and one is a missing consumer module in `test_errors.py` that would let an error string go undetected as an inline error.

Three info items: a redundant `_Unset` type check in the `review_due_within` validator, a timezone-awareness gap in `_parse_absolute_after`/`_parse_absolute_before` for full datetime strings, and a minor docstring imprecision.

---

## Warnings

### WR-01: SQLite availability defaults silently use wrong sentinel date for completed tasks

**File:** `tests/test_cross_path_equivalence.py:561`

**Issue:** The `_SQLITE_TASK_AVAILABILITY` map's "completed" entry sets `dateCompleted` to `_to_cf_epoch(_MODIFIED)` (a fixed sentinel date distinct from `_COMPLETED_DATE`). The seed adapter correctly overrides this when `t.get("completed")` is truthy (line 674), so any task that explicitly provides a "completed" date in neutral data works correctly. However, if a task has `"availability": "completed"` but `"completed": None` in neutral data, the `avail_cols["dateCompleted"]` fallback inserts `_MODIFIED` instead of `None`. This creates a silent inconsistency: the task will be treated as completed at `_MODIFIED`, not as having no completion timestamp.

The existing test data does not hit this case (task-5 has an explicit `_COMPLETED_DATE`), but a future test author adding a completed task without a date will get a subtly wrong SQLite row that is not immediately obvious.

**Fix:** Use `None` as the default for `dateCompleted` in the completed entry, consistent with the data-driven override pattern that follows it:

```python
_SQLITE_TASK_AVAILABILITY = {
    "available": {"blocked": 0, "dateCompleted": None, "dateHidden": None},
    "blocked": {"blocked": 1, "dateCompleted": None, "dateHidden": None},
    "completed": {"blocked": 0, "dateCompleted": None, "dateHidden": None},  # overridden by neutral data
    "dropped": {"blocked": 0, "dateCompleted": None, "dateHidden": None},    # overridden by neutral data
}
```

The availability columns (`blocked`) are all that should be hard-coded in this map; the date columns should default to `None` and be supplied by the neutral data. The same applies to the "dropped" entry's `dateHidden`.

---

### WR-02: `test_errors.py` omits `contracts_list_tasks` from error-consumer scan

**File:** `tests/test_errors.py:32-50`

**Issue:** The `_ERROR_CONSUMERS` list scans all modules that should use error constants from `agent_messages.errors`. The `contracts/use_cases/list/tasks.py` module is absent. While that module currently delegates null-rejection to `_validators.py` (which is included), if a future contributor adds a direct error reference to `tasks.py`, it will not be detected by `test_no_inline_error_strings_in_consumers` or `test_all_error_constants_referenced_in_consumers`. The omission creates a blind spot in the coverage guarantee.

**Fix:** Add `contracts_list_tasks` to the import list and `_ERROR_CONSUMERS`:

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

### IN-01: Timezone-naive datetime returned by `_parse_absolute_after`/`_parse_absolute_before` for full datetime strings

**File:** `src/omnifocus_operator/service/resolve_dates.py:227,240`

**Issue:** When the input is a full ISO datetime string (e.g. `"2026-04-01T14:00:00"`), both `_parse_absolute_after` and `_parse_absolute_before` return `datetime.fromisoformat(value)` directly, with no timezone applied. The docstrings state that tzinfo is inherited from `now` for date-only values ("inherits tzinfo from now so the result is tz-aware when now is tz-aware"), but this inheritance does not apply to the full datetime path. If the caller passes a timezone-aware `now`, a date-only value gets UTC tzinfo, but a full datetime string stays naive.

This is inconsistent: `DateFilter(after="2026-04-01")` produces an aware datetime (if `now` is aware), while `DateFilter(after="2026-04-01T14:00:00")` produces a naive one. The existing tests (in `test_resolve_dates.py`) use a naive `now`, so this discrepancy does not surface there. It would surface in the bridge path that compares resolved bounds against `AwareDatetime` task fields.

**Fix:** Apply `now.tzinfo` to the full datetime case as well:

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

### IN-02: Redundant `_Unset` type check in `_parse_review_due_within`

**File:** `src/omnifocus_operator/contracts/use_cases/list/projects.py:89`

**Issue:** The validator explicitly checks `isinstance(v, (ReviewDueFilter, _Unset))` and returns `v` early. However, the field is declared as `Patch[ReviewDueFilter]` with `default=UNSET`, and the validator mode is `"before"`. At `"before"` validation time, Pydantic has not yet constructed the field value; it passes raw input. A `ReviewDueFilter` instance arriving at `"before"` would be unusual — it suggests the caller is constructing the model programmatically. The `_Unset` guard is the meaningful one (protects UNSET from being cast through `.format()`). The `ReviewDueFilter` guard is technically safe but unexplained and slightly misleading because `_Unset` is not a public type — callers seeing this code may wonder why it's there.

**Fix:** Add a comment clarifying the intent:

```python
@field_validator("review_due_within", mode="before")
@classmethod
def _parse_review_due_within(cls, v: object) -> object:
    # Already resolved (e.g. programmatic construction) or UNSET -- pass through
    if isinstance(v, (ReviewDueFilter, _Unset)):
        return v
    if isinstance(v, str):
        return parse_review_due_within(v)
    raise ValueError(err.REVIEW_DUE_WITHIN_INVALID.format(value=v))
```

---

### IN-03: Docstring comment in `_resolve_shortcut` is misleading about "all"

**File:** `src/omnifocus_operator/service/resolve_dates.py:102-107`

**Issue:** The `_resolve_shortcut` function raises `ValueError` for `"all"` with the message `"'all' on field '...' is not a date filter — it expands availability. The pipeline handles this, not the date resolver."` This is correct behavior, but the error message will propagate to the test as an opaque internal crash if the domain layer ever accidentally passes "all" without filtering it first. The domain's guard (line 197 in `domain.py`) does catch this before calling `resolve_date_filter`, so the ValueError path is unreachable under normal operation — it exists purely as a programming contract assertion. A `raise AssertionError` (or `raise RuntimeError`) would communicate this intent more clearly than `raise ValueError`, which is normally reserved for user-input errors.

**Fix:** Change the raise type to `AssertionError` or add an assertion:

```python
if value == "all":
    raise AssertionError(
        f"'all' on field '{field_name}' is not a date filter -- "
        "the domain must handle this before calling resolve_date_filter."
    )
```

---

_Reviewed: 2026-04-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
