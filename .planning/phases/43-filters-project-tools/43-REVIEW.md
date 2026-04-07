---
phase: 43-filters-project-tools
reviewed: 2026-04-07T12:28:01Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/repository/bridge_only/adapter.py
  - src/omnifocus_operator/service/resolve.py
  - src/omnifocus_operator/service/service.py
  - tests/test_adapter.py
  - tests/test_bridge_only_repository.py
  - tests/test_list_pipelines.py
  - tests/test_service_resolve.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 43: Code Review Report

**Reviewed:** 2026-04-07T12:28:01Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Ten files reviewed covering agent-message string constants, bridge adapter, `Resolver`, `OperatorService` list pipelines, and all corresponding test suites. No security issues or critical logic bugs found. The bridge-only project root task filtering work (`adapt_snapshot`) is correct and well-tested.

The most significant issue is WR-01: `matches_inbox_name` has an inverted substring check that the test suite masks (every test input is a strict substring of "inbox", so all tests pass). The bug means `search="inbox tasks"` would not warn, contradicting the intended contract. This finding was noted in the prior review (WR-01 there described the same root cause from the `_check_inbox_search_warning` call site) but the underlying helper is where the fix should land.

---

## Warnings

### WR-01: `matches_inbox_name` substring direction is inverted — tests mask the bug

**File:** `src/omnifocus_operator/service/service.py:93`

**Issue:** The check `value.lower() in "Inbox".lower()` tests whether the user's input is a substring of `"inbox"`. Only values that are strict substrings of the 5-character word "inbox" (`"i"`, `"in"`, `"inb"`, `"inbo"`, `"inbox"`) trigger the warning. A value like `"inbox tasks"` or `"my inbox"` would not trigger it, even though they clearly contain "inbox". The intended contract (per the docstring and how the function is tested) is the reverse: warn when `"inbox"` is a substring of the input.

All existing tests pass because every test input (`"inbox"`, `"INBOX"`, `"inb"`) happens to be a substring of `"inbox"`. A test with `project="inbox tasks"` would fail against the current implementation.

**Fix:**
```python
def matches_inbox_name(value: str | None) -> bool:
    """Check if 'inbox' appears as a substring of the value (case-insensitive)."""
    if value is None:
        return False
    return "inbox" in value.lower()
```

The `test_search_in_substring_warns` test (line 474 in `test_list_pipelines.py`) verifies `search="in"` triggers the warning. Under the corrected implementation, `"in"` would no longer match — that test should be updated to use `search="inbox"` or removed if the intent was to demonstrate short substrings that coincidentally start with "in".

---

### WR-02: `_adapt_project` unconditional `pop("taskStatus")` can raise `KeyError` on malformed input

**File:** `src/omnifocus_operator/repository/bridge_only/adapter.py:234`

**Issue:** Every other field access in the adapter uses `.pop(key, None)` or `.get(key)` with explicit error handling. `_adapt_project` guards against double-adaptation by checking `"status" not in raw` (line 225), then proceeds to call `raw.pop("taskStatus")` without a default on line 234. If the bridge sends a project with `status` but without `taskStatus` (malformed payload), this raises an unhandled `KeyError` instead of a descriptive `ValueError`, breaking the error-handling contract established by the rest of the adapter.

**Fix:**
```python
old_task_status = raw.pop("taskStatus", None)
if old_task_status is None:
    msg = f"Project '{raw.get('id', '?')}' missing taskStatus field"
    raise ValueError(msg)
```

---

### WR-03: `Resolver` has two incompatible resolution contracts with no documented boundary

**File:** `src/omnifocus_operator/service/resolve.py:50-52`

**Issue:** `Resolver` exposes two fundamentally different contracts on the same class:

- **Write-side (async):** `_resolve`, `resolve_container`, `resolve_anchor`, `resolve_tags` — fetch entity data internally via `_fetch_all_by_type`.
- **Read-side (sync):** `resolve_filter`, `resolve_filter_list`, `find_unresolved` — operate on a pre-fetched `entities: Sequence[_HasIdAndName]` passed by the caller.

A developer adding a new caller could easily mistake the sync read-side methods as equivalent to the async write-side, or call `resolve_filter(value, [])` with an empty list and get silent no-match behaviour. The class docstring currently says only: "Resolves user-facing identifiers against the repository."

**Fix:** Update the class docstring:
```python
class Resolver:
    """Resolves user-facing identifiers against the repository.

    Two resolution contracts:
    - Write-side (async): resolve_container / resolve_anchor / resolve_tags
      fetch entity data from the repository internally.
    - Read-side (sync): resolve_filter / resolve_filter_list / find_unresolved
      operate on pre-fetched entity lists passed by the caller. Used by list
      pipelines that already hold fetched data to avoid redundant repo calls.
    """
```

---

## Info

### IN-01: `TAG_NOT_FOUND` uses `{name}` placeholder but `lookup_tag` passes a tag ID

**File:** `src/omnifocus_operator/agent_messages/errors.py:16` and `src/omnifocus_operator/service/resolve.py:211`

**Issue:** `TAG_NOT_FOUND = "Tag not found: {name}"` uses `{name}`, while `TASK_NOT_FOUND` and `PROJECT_NOT_FOUND` both use `{id}`. `lookup_tag` is a lookup-by-ID method and calls `.format(name=tag_id)`, emitting a tag ID labelled as if it were a name. Minor inconsistency but could confuse agents parsing error messages.

**Fix:**
```python
# errors.py line 16
TAG_NOT_FOUND = "Tag not found: {id}"

# resolve.py line 211
msg = TAG_NOT_FOUND.format(id=tag_id)
```

---

### IN-02: `_ListTasksPipeline._resolve_tags` skip-filter behaviour is undocumented

**File:** `src/omnifocus_operator/service/service.py:347-348`

**Issue:** When all tag values fail to resolve, `all_resolved` stays empty and `self._tag_ids` is never assigned (stays `None`), silently dropping the tag filter and returning all tasks. This is correct ("skip filter on miss") but neither this block nor the parallel `_resolve_project` block has a comment naming that contract. A future reader could introduce an early-return that breaks the semantics.

**Fix:**
```python
if all_resolved:
    # At least one tag resolved — apply as filter.
    # If none resolved, tag_ids stays None (filter skipped; warnings emitted above).
    self._tag_ids = all_resolved
```

---

### IN-03: `TestNoNotImplementedError` assertions are trivially true

**File:** `tests/test_list_pipelines.py:639-657`

**Issue:** All five tests in this class assert `result is not None`. Every list method returns a `ListResult` dataclass (never `None`), so these assertions can never fail regardless of what the method returns. They add to the test count without guarding real behaviour.

**Fix:** Either remove the class (callability is already covered by the snapshot-decorated tests above) or replace with a structural check:
```python
async def test_list_tasks_callable(self, service: OperatorService) -> None:
    result = await service.list_tasks(ListTasksQuery())
    assert isinstance(result.items, list)
```

---

### IN-04: `test_failed_refresh_preserves_none_cache` directly mutates `bridge._tasks` private state

**File:** `tests/test_bridge_only_repository.py:255-261` and `299-307`

**Issue:** Two tests (`test_failed_refresh_preserves_none_cache`, `test_failed_first_load_allows_retry`) bypass `InMemoryBridge`'s public API and directly assign to `bridge._tasks`, `bridge._projects`, etc. to re-populate the bridge after an error. This couples the tests to `InMemoryBridge`'s internal implementation. If the double's field names change, these tests will break with an `AttributeError` rather than a meaningful assertion failure.

**Fix:** Add a `set_data(data: dict)` method on `InMemoryBridge` (or expose `reset_data`) to allow tests to repopulate the bridge without touching private attributes:
```python
bridge.set_data(make_snapshot_dict())
```

---

_Reviewed: 2026-04-07T12:28:01Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
