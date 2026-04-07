---
phase: 45-date-models-resolution
reviewed: 2026-04-07T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/contracts/use_cases/list/__init__.py
  - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
  - src/omnifocus_operator/contracts/use_cases/list/_enums.py
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
  - src/omnifocus_operator/service/resolve_dates.py
  - tests/test_date_filter_constants.py
  - tests/test_date_filter_contracts.py
  - tests/test_descriptions.py
  - tests/test_errors.py
  - tests/test_list_contracts.py
  - tests/test_resolve_dates.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 45: Code Review Report

**Reviewed:** 2026-04-07
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

This phase introduces the date filter contract models (`DateFilter`, `DueDateShortcut`, `LifecycleDateShortcut`), wires them into `ListTasksQuery` / `ListTasksRepoQuery`, adds the pure `resolve_date_filter` function, consolidates descriptions and error strings, and adds comprehensive test coverage.

The work is well-structured and the test suite is thorough. No security vulnerabilities or data-loss risks were found. The issues below are logic correctness concerns and one silent-ambiguity trap in the validator.

## Warnings

### WR-01: `_validate_duration` runs after `_validate_this_unit` can't catch positive-count `this`

**File:** `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py:27-48`

**Issue:** `_validate_duration` is registered for `"last"` and `"next"` only. `_validate_this_unit` rejects anything that doesn't match `^[dwmy]$` via `_THIS_UNIT_PATTERN`. The pattern is correct, but the zero/negative guard in `_validate_duration` (lines 36-38) is NOT applied to `"this"`. A user who passes `this="0d"` gets `"Invalid duration"` from `_validate_this_unit` (because `"0d"` doesn't match `^[dwmy]$`), which is the right rejection but for a slightly wrong reason. This is a latent semantic confusion: the error message says "Invalid duration" but the real reason `this="0d"` is rejected is that `this` accepts only a single-character unit, not a count+unit. The existing test `test_this_only_accepts_single_unit` documents this correctly, but the error surfaced to the agent is `DATE_FILTER_INVALID_DURATION` (not a dedicated "this only accepts d/w/m/y" message).

This is a user-facing clarity issue rather than a correctness bug — the value is rejected either way. However, if `_THIS_UNIT_PATTERN` were ever relaxed to allow count+unit on `this`, the zero/negative guard would be silently missing.

**Fix:** Either keep the current approach and document the intentional reuse of `DATE_FILTER_INVALID_DURATION`, or add a dedicated error constant for `this` unit validation. At minimum, add a comment to `_validate_this_unit`:

```python
@field_validator("this", mode="after")
@classmethod
def _validate_this_unit(cls, v: str | None) -> str | None:
    if v is None:
        return v
    # 'this' accepts only a bare unit (d/w/m/y), not a count+unit.
    # _DATE_DURATION_PATTERN is intentionally NOT used here.
    if not _THIS_UNIT_PATTERN.match(v):
        raise ValueError(err.DATE_FILTER_INVALID_DURATION.format(value=v))
    return v
```

---

### WR-02: `_validate_groups` reversed-bounds check silently skips mixed datetime/date comparisons

**File:** `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py:87-98`

**Issue:** The reversed-bounds guard (lines 87-98) calls `_parse_to_comparable` and only raises if both results are non-`None`. `_parse_to_comparable` returns `None` if parsing fails — but both `before` and `after` have already been validated by `_validate_absolute` at the field level, so they are guaranteed to be either `"now"` or a valid ISO date/datetime. The `None` path in `_parse_to_comparable` therefore can never be reached in practice, but the guard silently skips the check if it were hit.

More concretely: `datetime.fromisoformat` can parse both `"2026-04-14"` (Python 3.11+ accepts date-only) AND `"2026-04-14T12:00:00"`. But `_parse_to_comparable` tries `datetime.fromisoformat` first, then falls back to `date.fromisoformat`. This means that when `after` is a datetime `"2026-04-14T12:00:00"` and `before` is a date-only `"2026-04-14"`, the comparison is between a `datetime` and a `date` object. In Python, `datetime > date` raises `TypeError`.

**Reproduction:** `DateFilter(after="2026-04-14T12:00:00", before="2026-04-14")` — both are valid by field validators, not "now", so the comparison code runs. `after_dt` = `datetime(2026, 4, 14, 12, 0)`, `before_dt` = `date(2026, 4, 14)`. Comparing them raises `TypeError`, which is not caught, resulting in an unhandled exception during validation instead of a clean `ValidationError`.

**Fix:** Normalize both values to `datetime` before comparing, or ensure `_parse_to_comparable` always returns a `datetime`:

```python
def _parse_to_comparable(value: str) -> datetime | None:
    """Parse string to datetime for comparison. Returns None if unparseable."""
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        pass
    try:
        d = date.fromisoformat(value)
        return datetime(d.year, d.month, d.day)  # normalize to datetime
    except (ValueError, TypeError):
        return None
```

This ensures all comparisons are between homogeneous types and eliminates the `TypeError` crash path.

---

### WR-03: `_PENDING_CONSUMER_CONSTANTS` exemption in `test_descriptions.py` will silently pass even if the constants are never wired

**File:** `tests/test_descriptions.py:122-131`

**Issue:** The test `test_all_description_constants_referenced_in_consumers` has a hardcoded exemption set `_PENDING_CONSUMER_CONSTANTS` for 7 date-filter field description constants. The comment says "Remove this exemption once the fields are wired." The exemption subtracts these constants from the `unreferenced` set before asserting. If the constants are wired (consumed) in Phase 46 but the exemption is not removed, the test will still pass — the subtraction of an already-empty intersection is a no-op. The risk is that the exemption persists indefinitely and the enforcement test loses coverage for those 7 constants.

**Fix:** This is acceptable as a temporary scaffold for phase 45, but add a `TODO` comment referencing a specific follow-up action so it doesn't get forgotten:

```python
# TODO(Phase 46): Remove _PENDING_CONSUMER_CONSTANTS once date filter fields
# are wired into ListTasksQuery Field(description=...) calls.
_PENDING_CONSUMER_CONSTANTS = {
    "DUE_FILTER_DESC",
    ...
}
```

---

## Info

### IN-01: `_duration_to_timedelta` uses naive 30d/365d for months/years with no doc at call sites

**File:** `src/omnifocus_operator/service/resolve_dates.py:263-274`

**Issue:** `_duration_to_timedelta` explicitly documents "Uses naive 30d/365d for m/y" in its docstring (line 264). This is intentional and matches the requirement. However, the callers `_resolve_last` and `_resolve_next` don't carry any comment acknowledging the approximation. The test comments do acknowledge this (e.g., `test_last_1_month_naive` says "30 days"), which is good. The sole concern is that a future maintainer editing `_resolve_last` or `_resolve_next` without reading `_duration_to_timedelta` might not realize months/years are approximated.

**Fix:** One-line comment at the call site in `_resolve_last` and `_resolve_next`:

```python
def _resolve_last(duration: str, now: datetime) -> tuple[datetime, datetime]:
    count, unit = _parse_duration(duration)
    delta = _duration_to_timedelta(count, unit)  # m/y are naive 30d/365d
    start = _midnight(now - delta)
    return (start, now)
```

---

### IN-02: `test_descriptions.py` AST check for `Field(...)` has a dead branch

**File:** `tests/test_descriptions.py:150-155`

**Issue:** The `Field(...)` detection logic at lines 150-155 has a logical dead branch. The `if` condition is:

```python
if not (
    isinstance(node.func, ast.Name) and node.func.attr == "Field"
    if isinstance(node.func, ast.Attribute)
    else isinstance(node.func, ast.Name) and node.func.id == "Field"
):
```

This is a ternary nested inside `not(...)`. When `node.func` is an `ast.Attribute`, it evaluates `isinstance(node.func, ast.Name) and node.func.attr == "Field"`. But `node.func` is an `ast.Attribute`, so `isinstance(node.func, ast.Name)` is `False` — the `.attr` check is never reached. As a result, attribute-form `Field(...)` calls (e.g., `pydantic.Field(...)`) are never detected. The intended logic was likely: `isinstance(node.func, ast.Attribute) and node.func.attr == "Field"` for the attribute branch. The same pattern appears in `test_no_inline_examples_in_agent_models` (lines 229-234).

In practice, `Field` is imported directly (`from pydantic import Field`) so it always appears as `ast.Name`, not `ast.Attribute`. The dead branch is harmless today but is misleading code.

**Fix:**
```python
# Correct intent: match Field(...) as a bare name OR as attr.Field(...)
if not (
    (isinstance(node.func, ast.Attribute) and node.func.attr == "Field")
    or (isinstance(node.func, ast.Name) and node.func.id == "Field")
):
    continue
```

---

_Reviewed: 2026-04-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
