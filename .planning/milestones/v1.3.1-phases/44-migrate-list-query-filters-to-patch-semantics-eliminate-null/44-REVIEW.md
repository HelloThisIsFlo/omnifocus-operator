---
phase: 44-migrate-list-query-filters-to-patch-semantics-eliminate-null
reviewed: 2026-04-07T00:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/contracts/base.py
  - src/omnifocus_operator/contracts/use_cases/list/__init__.py
  - src/omnifocus_operator/contracts/use_cases/list/_enums.py
  - src/omnifocus_operator/contracts/use_cases/list/_validators.py
  - src/omnifocus_operator/contracts/use_cases/list/folders.py
  - src/omnifocus_operator/contracts/use_cases/list/perspectives.py
  - src/omnifocus_operator/contracts/use_cases/list/projects.py
  - src/omnifocus_operator/contracts/use_cases/list/tags.py
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
  - src/omnifocus_operator/service/service.py
  - tests/test_default_pagination.py
  - tests/test_descriptions.py
  - tests/test_list_contracts.py
  - tests/test_list_pipelines.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 44: Code Review Report

**Reviewed:** 2026-04-07
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

This phase migrates list query filter fields from nullable semantics to Patch semantics (UNSET = omit, null = validation error). The contract layer, service pipelines, and test suite were all updated together.

The implementation is solid. The Patch pattern is applied consistently across all five query models, the `reject_null_filters` mechanism works correctly (both snake_case and camelCase variants), and the service correctly uses `unset_to_none()` at the boundary. No critical issues found.

Two warnings: one is a real logic risk in `_expand_review_due` (silent fallthrough to years branch), the other is a type annotation mismatch on the `tags` field validator that could mislead future editors.

---

## Warnings

### WR-01: Silent fallthrough to YEARS branch in `_expand_review_due`

**File:** `src/omnifocus_operator/service/service.py:480-494`

**Issue:** `_expand_review_due` uses a chain of `if` guards for DAYS, WEEKS, MONTHS, and then a comment-only guard for YEARS. If a new `DurationUnit` value is ever added and this method is not updated, it silently falls into the YEARS branch and produces an incorrect datetime with no error. The comment `# unit == DurationUnit.YEARS` is documentation, not enforcement.

**Fix:** Add an explicit final branch with a guard, or use `match`/`case` exhaustively:

```python
if unit == DurationUnit.DAYS:
    return now + timedelta(days=amount)
if unit == DurationUnit.WEEKS:
    return now + timedelta(weeks=amount)
if unit == DurationUnit.MONTHS:
    month = now.month + amount
    year = now.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = min(now.day, calendar.monthrange(year, month)[1])
    return now.replace(year=year, month=month, day=day)
if unit == DurationUnit.YEARS:
    year = now.year + amount
    day = min(now.day, calendar.monthrange(year, now.month)[1])
    return now.replace(year=year, day=day)
raise ValueError(f"Unhandled DurationUnit: {unit!r}")
```

---

### WR-02: `_reject_empty_tags` field validator type annotation is misleading

**File:** `src/omnifocus_operator/contracts/use_cases/list/tasks.py:54-58`

**Issue:** The `_reject_empty_tags` validator declares `v: list[str]` but the field type is `Patch[list[str]]` (i.e., `list[str] | _Unset`). When `tags=UNSET` (the default), Pydantic v2 does not invoke the validator, so there's no runtime crash. However, the annotation is a lie — it would break if Pydantic's behavior around default-skipping changes, and it misleads future editors into thinking the validator always receives a `list[str]`.

**Fix:** Use the correct union type in the annotation and add an UNSET guard:

```python
@field_validator("tags", mode="after")
@classmethod
def _reject_empty_tags(cls, v: list[str] | _Unset) -> list[str] | _Unset:
    if isinstance(v, _Unset):
        return v
    validate_non_empty_list(v, "tags")
    return v
```

---

## Info

### IN-01: Test assertions use `Availability` (core enum) instead of `AvailabilityFilter` (filter enum)

**File:** `tests/test_list_contracts.py:134-135`

**Issue:** `ListTasksQuery().availability` returns `list[AvailabilityFilter]`, but the assertion compares against `[Availability.AVAILABLE, Availability.BLOCKED]` (the core enum). This works today because both are `StrEnum` with identical string values. But it expresses the wrong invariant — if `AvailabilityFilter` and `Availability` diverge, the test could give a false pass.

**Fix:**
```python
from omnifocus_operator.contracts.use_cases.list._enums import AvailabilityFilter

def test_list_tasks_query_default_availability(self) -> None:
    query = ListTasksQuery()
    assert query.availability == [AvailabilityFilter.AVAILABLE, AvailabilityFilter.BLOCKED]
```

---

### IN-02: `ListFoldersQuery` offset field default asymmetry with repo model

**File:** `src/omnifocus_operator/contracts/use_cases/list/folders.py:34` and `63`

**Issue:** `ListFoldersQuery.offset` is `int` (default `0`), while `ListFoldersRepoQuery.offset` is `int | None` (default `None`). The service passes `query.offset` directly (always `int`) to `ListFoldersRepoQuery`. This is not a bug — `int` is assignable to `int | None` — but the asymmetry is inconsistent with `ListTasksQuery` and `ListProjectsQuery`, and could cause confusion about what `offset=0` means at the repo level vs. "no offset specified". The same pattern exists for tags, perspectives, and projects.

This is a design decision, not a defect, but worth noting if the repo layer ever needs to distinguish "not set" from "set to 0".

**Fix:** No immediate action required. If the repo layer needs to distinguish the two states, standardize on `offset: int | None = None` in all query models.

---

### IN-03: Commented-out indicator in `_expand_review_due` could be a `match` statement

**File:** `src/omnifocus_operator/service/service.py:491`

**Issue:** The comment `# unit == DurationUnit.YEARS` at line 491 is a code smell noted in WR-01. This info item is a separate observation: the four-branch if/comment pattern is a natural fit for `match unit:` which would give Python's exhaustiveness tooling a chance to catch missing cases with `mypy --strict`.

**Fix:** (Low priority, optional refactor)
```python
match unit:
    case DurationUnit.DAYS:
        return now + timedelta(days=amount)
    case DurationUnit.WEEKS:
        return now + timedelta(weeks=amount)
    case DurationUnit.MONTHS:
        ...
    case DurationUnit.YEARS:
        ...
    case _:
        raise ValueError(f"Unhandled DurationUnit: {unit!r}")
```

---

_Reviewed: 2026-04-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
