---
phase: 53-response-shaping
reviewed: 2026-04-14T00:00:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/contracts/use_cases/list/projects.py
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
  - src/omnifocus_operator/models/common.py
  - src/omnifocus_operator/models/task.py
  - src/omnifocus_operator/repository/bridge_only/adapter.py
  - src/omnifocus_operator/repository/bridge_only/bridge_only.py
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/server/__init__.py
  - src/omnifocus_operator/server/handlers.py
  - src/omnifocus_operator/server/lifespan.py
  - src/omnifocus_operator/server/projection.py
  - tests/conftest.py
  - tests/test_descriptions.py
  - tests/test_errors.py
  - tests/test_hybrid_repository.py
  - tests/test_list_contracts.py
  - tests/test_models.py
  - tests/test_projection.py
  - tests/test_server.py
  - tests/test_warnings.py
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 53: Code Review Report

**Reviewed:** 2026-04-14
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

This phase adds response shaping (field projection, stripping, list envelope assembly) plus centralised description and error strings for the new list contract fields. The architecture is clean and well-layered. The stripping and projection logic is correct and well-tested, with thorough enforcement tests.

Two warnings and four info items follow.

## Warnings

### WR-01: Stale `pending_consumer_constants` allowlist silently voids enforcement

**File:** `tests/test_descriptions.py:122-134`

**Issue:** The `pending_consumer_constants` set was added in Phase 45/46 to exempt seven date-filter description constants that had not yet been wired into `ListTasksQuery` or `ListProjectsQuery`. Those constants are now fully wired (both files import and use all seven). The allowlist is therefore stale: `test_all_description_constants_referenced_in_consumers` silently passes even if any of those seven constants were accidentally removed from the consumer modules, because the exemption set would hide the regression. The test is no longer enforcing what it claims to enforce.

**Fix:** Remove the `pending_consumer_constants` set and the TODO comment entirely. The `unreferenced` calculation simplifies to:

```python
unreferenced = {c for c in constants if c not in source}
assert unreferenced == set(), (
    f"Description constants not referenced in consumer modules: {unreferenced}"
)
```

---

### WR-02: `assert include is not None` is silently skipped in optimised builds

**File:** `src/omnifocus_operator/server/projection.py:107`

**Issue:** The assertion at line 107 is the sole guard ensuring the `_resolve_include` branch is only reached when `include` is not `None`. With Python's `-O` or `-OO` flags, all `assert` statements are stripped at compile time, turning this into an unconditional fall-through that passes `None` into `_resolve_include`. `_resolve_include` would then immediately fail on `"*" in include` with `TypeError: argument of type 'NoneType' is not iterable`. MCP servers are not typically run with `-O`, but the guard should be unconditional.

**Fix:** Replace the `assert` with an explicit `if` guard (or simply rely on the logic being correct — the `assert` is only reachable when `include is not None` given the preceding `if only is not None: return` path, so it is logically dead). The cleanest fix is to invert the conditional and return early:

```python
# include handling (only is None, include is not None at this point)
if include is None:
    # Should never happen given control flow, but be explicit
    return None, warnings
return _resolve_include(include, default_fields, field_groups, all_fields, warnings)
```

Or simply remove the assertion if the type checker is already narrowing correctly via `# type: ignore` or similar. The simplest safe fix:

```python
# include handling — control flow guarantees include is not None here
return _resolve_include(include, default_fields, field_groups, all_fields, warnings)
```

---

## Info

### IN-01: `_check_review_due_within` validator type annotation is incorrect

**File:** `src/omnifocus_operator/contracts/use_cases/list/projects.py:99`

**Issue:** The validator is declared as `def _check_review_due_within(cls, v: str) -> str:` but the field type is `Patch[str]` (i.e., `str | _Unset`). When the field holds its default `UNSET`, Pydantic does not invoke the validator (field validators are skipped for unchanged defaults), so this causes no runtime error. However the annotation is technically wrong — a type checker running strict mode would flag callers that pass `_Unset` and expect `str` back.

**Fix:** Add an `is_set` guard or use the correct annotation:

```python
@field_validator("review_due_within", mode="after")
@classmethod
def _check_review_due_within(cls, v: str | _Unset) -> str | _Unset:
    if not is_set(v):
        return v
    if v == "now":
        return v
    ...
```

---

### IN-02: Stale TODO comment referencing Phase 46

**File:** `tests/test_descriptions.py:123-124`

**Issue:** The comment `# TODO(Phase 46): Remove pending_consumer_constants...` references a phase that has since been completed (the date filter fields are now wired). This is a dead TODO that will never be acted on unless explicitly hunted down. Closely related to WR-01 — resolving WR-01 eliminates this comment entirely.

**Fix:** Remove as part of the WR-01 fix.

---

### IN-03: `_parse_timestamp` timezone heuristic is fragile for short strings

**File:** `src/omnifocus_operator/repository/hybrid/hybrid.py:151`

**Issue:** The check `"-" not in value[10:]` appends `+00:00` to strings without an explicit timezone offset. If `value` is shorter than 10 characters (e.g. a truncated or malformed timestamp), `value[10:]` is an empty string, `"-" not in ""` is `True`, and `+00:00` is appended to a malformed string. This would then propagate as an invalid ISO string into Pydantic validation, producing a `ValidationError` rather than a clear error message.

In practice OmniFocus never produces sub-10-character timestamps, so this is very low risk. Still, a length guard would make the intent clearer:

**Fix:**

```python
if len(value) >= 10 and "+" not in value and "-" not in value[10:]:
    return value + "+00:00"
```

---

### IN-04: Duplicate `_paginate` functions across repository implementations

**File:** `src/omnifocus_operator/repository/bridge_only/bridge_only.py:119` and `src/omnifocus_operator/repository/hybrid/hybrid.py:65`

**Issue:** Both `BridgeOnlyRepository` and `HybridRepository` define a module-level `_paginate` function with identical signatures and identical logic. This is code duplication — if the pagination semantics need to change (e.g. to fix an off-by-one), it must be updated in two places. The functions are truly identical (both compute `total = len(items)`, slice by `offset`, check `has_more` as `len(items) > limit`).

Note: `BridgeOnlyRepository.list_tasks` and `list_projects` do NOT use `_paginate` — they implement their own `has_more` calculation inline (lines 272 and 314). This is a third, slightly different implementation of the same logic. While all three give the same result, the proliferation makes future changes error-prone.

**Fix:** Extract `_paginate` to a shared utility module (e.g. `src/omnifocus_operator/repository/_pagination.py`) and import from both repositories. This is a refactoring change; the current code is functionally correct.

---

_Reviewed: 2026-04-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
