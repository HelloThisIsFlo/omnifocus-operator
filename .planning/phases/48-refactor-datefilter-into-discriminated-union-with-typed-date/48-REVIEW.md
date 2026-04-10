---
phase: 48-refactor-datefilter-into-discriminated-union-with-typed-date
reviewed: 2026-04-10T17:15:18Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/contracts/use_cases/list/__init__.py
  - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/service/resolve_dates.py
  - tests/test_date_filter_constants.py
  - tests/test_date_filter_contracts.py
  - tests/test_resolve_dates.py
  - tests/test_service_domain.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 48: Code Review Report

**Reviewed:** 2026-04-10T17:15:18Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 48 refactors `DateFilter` into a Pydantic v2 discriminated union of four concrete filter models (`ThisPeriodFilter`, `LastPeriodFilter`, `NextPeriodFilter`, `AbsoluteRangeFilter`). The design is sound: discriminator routing is clean, validation is thorough, and the test suite covers the full input space including edge cases.

No critical issues were found. Two warnings flag a latent bug path in `_to_utc_ts` and a fragile string-match sentinel in `detect_early_return`. Three info items cover code duplication and minor style inconsistencies.

The core contracts (`_date_filter.py`, `resolve_dates.py`) and supporting message files (`descriptions.py`, `errors.py`) are clean and well-organized.

---

## Warnings

### WR-01: `_to_utc_ts` — naive datetime fromisoformat could raise on Python 3.12+

**File:** `src/omnifocus_operator/service/domain.py:129-130`

**Issue:** The `str` branch calls `datetime.fromisoformat(val).astimezone(UTC)`. On Python 3.12+, calling `.astimezone()` on a naive `datetime` raises `ValueError`. This path is hit when comparing `EditTaskRepoPayload` date fields (which are `str | None`) against task date fields. Today, the payload builder always serializes `AwareDatetime` values with `.isoformat()`, so the strings are always timezone-aware — but the `str` branch has no guard. If any code path sets a date string without timezone (e.g., a date-only `"2026-04-01"`), this silently skips the no-op check and sends a redundant edit to the bridge, or crashes at the comparison step.

```python
# current (line 129-130):
if isinstance(val, str):
    return datetime.fromisoformat(val).astimezone(UTC).timestamp()
```

**Fix:** Assert or validate that the parsed datetime is aware before converting. Since all callers should supply timezone-aware strings, a hard failure is preferable to a silent wrong comparison:

```python
if isinstance(val, str):
    parsed = datetime.fromisoformat(val)
    if parsed.tzinfo is None:
        # This should never happen given the payload builder always uses .isoformat()
        # on AwareDatetime values. Log or raise to catch regressions early.
        raise AssertionError(f"_to_utc_ts received naive datetime string: {val!r}")
    return parsed.astimezone(UTC).timestamp()
```

---

### WR-02: `detect_early_return` — status-warning filter uses fragile substring match

**File:** `src/omnifocus_operator/service/domain.py:798`

**Issue:** The no-op detection filters status warnings using `"your changes were applied" not in w`. This string is embedded in the `EDIT_COMPLETED_TASK` warning template at `agent_messages/warnings.py`. If the template text changes, the filter silently breaks: status warnings would no longer be suppressed, and the agent would receive both a status warning and a redundant no-op message. There is no test that ties this substring to the actual warning constant.

```python
# current (line 797-798):
filtered = [w for w in warnings if "your changes were applied" not in w]
```

**Fix:** Import and reference the constant directly so refactoring the warning text is caught at the call site. Alternatively, use a structured sentinel (e.g., a tag or enum) to identify status warnings rather than substring matching:

```python
from omnifocus_operator.agent_messages.warnings import EDIT_COMPLETED_TASK

# Filter by checking if the warning starts with the template prefix,
# or store formatted warnings with a type tag.
_STATUS_WARNING_MARKER = "your changes were applied"  # co-locate with EDIT_COMPLETED_TASK
filtered = [w for w in warnings if _STATUS_WARNING_MARKER not in w]
```

The minimal fix is to define the marker string as a constant alongside `EDIT_COMPLETED_TASK` in `warnings.py`, so any change to the template is visible next to the marker.

---

## Info

### IN-01: Duplicated `_validate_duration` implementation in `LastPeriodFilter` and `NextPeriodFilter`

**File:** `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py:53-63` and `71-81`

**Issue:** `LastPeriodFilter._validate_duration` and `NextPeriodFilter._validate_duration` are byte-for-byte identical (10 lines each). Any change to duration validation (e.g., new unit support or different error message) must be applied in two places.

**Fix:** Extract to a module-level helper and call it from both validators:

```python
def _validate_duration_str(v: str) -> str:
    match = _DATE_DURATION_PATTERN.match(v)
    if not match:
        raise ValueError(err.DATE_FILTER_INVALID_DURATION.format(value=v))
    count_str = match.group(1)
    count = int(count_str) if count_str else 1
    if count <= 0:
        raise ValueError(err.DATE_FILTER_ZERO_NEGATIVE.format(value=v))
    return v

class LastPeriodFilter(QueryModel):
    @field_validator("last", mode="after")
    @classmethod
    def _validate_duration(cls, v: str) -> str:
        return _validate_duration_str(v)

class NextPeriodFilter(QueryModel):
    @field_validator("next", mode="after")
    @classmethod
    def _validate_duration(cls, v: str) -> str:
        return _validate_duration_str(v)
```

---

### IN-02: `expand_review_due` — `type: ignore` masks a potential `None` unit dereference

**File:** `src/omnifocus_operator/service/domain.py:258`

**Issue:** `unit: DurationUnit = f.unit  # type: ignore[assignment]` suppresses a type error because `f.unit` is `DurationUnit | None`. The guard `if f.amount is None: return now` fires first, but there is no guard for `f.unit is None` when `f.amount is not None`. If a `ReviewDueFilter` is constructed with `amount=5, unit=None`, the code falls through all four `if unit is ...` branches to `raise AssertionError`. This is not reachable via the validated query model, but the `type: ignore` hides the structural mismatch.

**Fix:** Add an explicit guard or document the invariant that `unit` is always non-None when `amount` is non-None:

```python
if f.amount is None:
    return now
unit = f.unit
assert unit is not None, "ReviewDueFilter.unit must be set when amount is set"
```

This makes the invariant explicit and removes the need for `type: ignore`.

---

### IN-03: Test assertions use `in` for full-string constant matching

**File:** `tests/test_service_domain.py:630, 663, 700, 711`

**Issue:** Several test assertions check `assert REPETITION_EMPTY_ON_DATES in warnings[0]` using `in` (substring containment) when the intent is equality — the constant IS the full warning string. Using `==` would be clearer and stricter. If the constant string ever becomes a substring of a longer message, the `in` check would still pass, masking the regression.

Representative lines:
```python
# line 630
assert REPETITION_EMPTY_ON_DATES in warnings[0]
# line 663
assert REPETITION_EMPTY_ON_DAYS in warnings[0]
```

**Fix:** Use direct equality:
```python
assert warnings[0] == REPETITION_EMPTY_ON_DATES
assert warnings[0] == REPETITION_EMPTY_ON_DAYS
```

---

_Reviewed: 2026-04-10T17:15:18Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
