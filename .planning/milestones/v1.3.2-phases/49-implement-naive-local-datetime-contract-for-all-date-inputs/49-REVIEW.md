---
phase: 49-implement-naive-local-datetime-contract-for-all-date-inputs
reviewed: 2026-04-10T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - docs/architecture.md
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/contracts/use_cases/add/tasks.py
  - src/omnifocus_operator/contracts/use_cases/edit/tasks.py
  - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/service/payload.py
  - src/omnifocus_operator/service/resolve_dates.py
  - src/omnifocus_operator/service/service.py
  - tests/doubles/bridge.py
  - tests/test_contracts_field_constraints.py
  - tests/test_date_filter_constants.py
  - tests/test_date_filter_contracts.py
  - tests/test_models.py
  - tests/test_output_schema.py
  - tests/test_service_payload.py
  - tests/test_service.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 49: Code Review Report

**Reviewed:** 2026-04-10
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Phase 49 implements the naive-local datetime contract across all date inputs. The core approach is sound and well-reasoned: `str` type on contract models (avoids RFC 3339 timezone requirement), ISO syntax validation at the contract layer, and `normalize_date_input()` in the domain layer as the single point of aware-to-local conversion. The architecture doc section ("Naive-Local DateTime Principle") clearly describes the rationale.

The implementation is coherent and the test coverage for the new contract is good (`TestDateFieldStrType`, `TestWriteSchemaNoDateTimeFormat`, `TestDateFilterStringBounds`). No critical issues found.

Three warnings are raised: a correctness gap in the `_validate_date_string` function's interaction with `None`, a correctness edge case in the bounds-ordering check when mixing tz-aware inputs with different offsets, and a silent data-loss risk in `_to_utc_ts` when receiving non-string/non-datetime values from task fields. Three info items cover code duplication, a missing test case, and a minor comment imprecision.

---

## Warnings

### WR-01: `_validate_date_string` passes non-string values silently, including invalid types

**File:** `src/omnifocus_operator/contracts/use_cases/add/tasks.py:31-39` and `src/omnifocus_operator/contracts/use_cases/edit/tasks.py:42-50`

**Issue:** Both copies of `_validate_date_string` return non-string values immediately without validation:

```python
def _validate_date_string(v: object) -> object:
    if not isinstance(v, str):
        return v   # <-- passes ANY non-string through: int, list, dict, ...
    ...
```

The `@field_validator("due_date", ..., mode="before")` runs before Pydantic's type coercion. If an agent sends `{"due_date": 12345}`, the validator passes it through, and Pydantic then raises a type error — but with a generic Pydantic message instead of the educational `INVALID_DATE_FORMAT` error. The intent is to pass `UNSET` through (which is `_Unset`, not a string), but `not isinstance(v, str)` is too broad.

**Fix:** Narrow the early-return to the sentinel type specifically:

```python
from omnifocus_operator.contracts.base import _Unset

def _validate_date_string(v: object) -> object:
    if isinstance(v, _Unset):
        return v  # UNSET passthrough only
    if not isinstance(v, str):
        raise ValueError(INVALID_DATE_FORMAT.format(value=repr(v)))
    try:
        _datetime.fromisoformat(v)
    except ValueError:
        raise ValueError(INVALID_DATE_FORMAT.format(value=v))
    return v
```

Or alternatively, since these are `mode="before"` validators, `None` for clearable fields also needs to pass through on the edit side. The simplest safe fix: check `v is None` and `isinstance(v, _Unset)` explicitly, reject everything else that isn't a string.

---

### WR-02: Mixed-offset reversed-bounds check can produce a false negative

**File:** `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py:98-105`

**Issue:** The `_validate_bounds` model validator strips timezone info before comparing `after` and `before`, but does so by replacing tzinfo with None (not by converting to UTC):

```python
after_cmp = after_dt.replace(tzinfo=None) if after_dt.tzinfo else after_dt
before_cmp = before_dt.replace(tzinfo=None) if before_dt.tzinfo else before_dt
if after_cmp > before_cmp:
    raise ValueError(...)
```

Consider `after="2026-04-14T23:00:00+14:00"` and `before="2026-04-14T01:00:00-12:00"`. Stripping tz makes `after_cmp = 23:00` and `before_cmp = 01:00`, so the validator correctly flags this as reversed. But the inverse can fail: `after="2026-04-14T12:00:00+12:00"` (= UTC 00:00) and `before="2026-04-14T12:00:00-12:00"` (= UTC 24:00) — stripping tz makes them look equal (valid), but they are ordered correctly anyway in this case.

The real gap: `after="2026-04-15T00:00:00+14:00"` (UTC Apr 14 10:00) and `before="2026-04-14T23:00:00-01:00"` (UTC Apr 15 00:00). Stripping tz: `after_cmp = Apr 15 00:00 > before_cmp = Apr 14 23:00` — the validator would reject this as reversed even though `after` is chronologically *before* `before` in UTC.

This causes false rejections for valid cross-timezone ranges, not a security issue but user-facing validation failures.

**Fix:** Convert both datetimes to UTC before comparison when both are aware. Naive datetimes can stay as-is (they're already local-matched per contract):

```python
from datetime import timezone

def _to_utc_for_cmp(dt: _datetime) -> _datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

after_cmp = _to_utc_for_cmp(after_dt)
before_cmp = _to_utc_for_cmp(before_dt)
if after_cmp > before_cmp:
    raise ValueError(...)
```

---

### WR-03: `_to_utc_ts` silently passes through unexpected value types

**File:** `src/omnifocus_operator/service/domain.py:151-170`

**Issue:** `_to_utc_ts` is used to compare task date fields (from the `Task` model) against payload dates (from the command, after `normalize_date_input`). The function has a catch-all `return val` for unknown types:

```python
def _to_utc_ts(val: object) -> object:
    if val is None:
        return None
    if isinstance(val, datetime):
        ...
    if isinstance(val, str):
        ...
    return val  # <-- silently passes through int, float, date objects, etc.
```

Task date fields are typed as `str | None` (after Phase 49), but the function handles `datetime` objects for backward compatibility with the read side (which may still return tz-aware datetimes from the repository layer). If a `date` object (without time) slips through — which could happen if the `Task` model field type ever widens — the comparison would silently use object identity rather than chronological ordering, making no-op detection unreliable.

**Fix:** Add an assertion or explicit error for unrecognized types rather than silently passing them through:

```python
def _to_utc_ts(val: object) -> object:
    if val is None:
        return None
    if isinstance(val, datetime):
        ...
    if isinstance(val, str):
        ...
    # Unexpected type: fail loudly rather than silently corrupting comparison
    raise TypeError(f"_to_utc_ts: unexpected type {type(val).__name__!r}: {val!r}")
```

Alternatively, add a `date` case explicitly if it's a known expected input.

---

## Info

### IN-01: `_validate_date_string` is duplicated verbatim in two modules

**File:** `src/omnifocus_operator/contracts/use_cases/add/tasks.py:31-39` and `src/omnifocus_operator/contracts/use_cases/edit/tasks.py:42-50`

**Issue:** The function is identical in both files — same logic, same error constant. Any future change (e.g., fixing WR-01) must be applied in two places.

**Fix:** Extract to a shared location. Given the project's dependency direction (`contracts/` → nothing outside contracts), a natural home is `contracts/base.py` or a new `contracts/shared/validators.py`. The function should be importable by both `add/tasks.py` and `edit/tasks.py` without creating circular dependencies.

---

### IN-02: No test for the `normalize_date_input` date-only midnight-append path with a verify round-trip

**File:** `tests/test_service.py` (service-level integration) and `tests/test_contracts_field_constraints.py`

**Issue:** `TestDateFieldStrType.test_add_date_only_accepted` verifies the contract accepts `"2026-07-15"` (date-only string). However, there is no test that verifies the service-level normalization of date-only input: that `due_date="2026-07-15"` sent through `add_task` actually results in a task with `dueDate="2026-07-15T00:00:00"` stored in the bridge. The normalization logic in `normalize_date_input` is exercised by the unit path in `domain.py` but the round-trip from contract → service → bridge is not explicitly verified.

**Fix:** Add a service-level test that uses a date-only string and verifies the stored task has the expected midnight datetime:

```python
async def test_date_only_normalized_to_midnight(
    self, service: OperatorService, repo: BridgeOnlyRepository
) -> None:
    """Date-only due_date is normalized to midnight (T00:00:00)."""
    result = await service.add_task(
        AddTaskCommand(name="Midnight test", due_date="2026-07-15")
    )
    task = await repo.get_task(result.id)
    assert task is not None
    assert task.due_date is not None
    assert "T00:00:00" in task.due_date
```

---

### IN-03: Architecture doc comment for `_midnight(now)` fallback in "soon" without `due_soon_setting` uses naive datetime

**File:** `src/omnifocus_operator/service/domain.py:238-241`

**Issue:** The "soon without config" fallback in `resolve_date_filters` uses `now.replace(hour=0, ...)` to produce `midnight`. Since `now` from `local_now()` is tz-aware, `midnight` here is also tz-aware. This is correct behavior. However, the comment block (`# Warn: fallback to TODAY`) says nothing about the tz-awareness of the result, and the pattern is inconsistent with the standalone `_midnight()` helper in `resolve_dates.py`. The domain and the resolver both compute "midnight" independently using slightly different code paths.

**Fix:** Reuse the `_midnight` helper from `resolve_dates.py` (import it) rather than duplicating the `replace()` inline. This removes the duplication and makes the intent more explicit:

```python
from omnifocus_operator.service.resolve_dates import _midnight  # or expose as public

# In domain.py:
midnight = _midnight(now)
bounds[field_name] = ResolvedDateBounds(
    after=midnight,
    before=midnight + timedelta(days=1),
)
```

Note: `_midnight` is currently private (underscore prefix) in `resolve_dates.py`. If importing it, either make it public or move it to a shared utility.

---

_Reviewed: 2026-04-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
