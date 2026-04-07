---
phase: 43-filters-project-tools
reviewed: 2026-04-07T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/service/resolve.py
  - src/omnifocus_operator/service/service.py
  - tests/test_list_pipelines.py
  - tests/test_service_resolve.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 43: Code Review Report

**Reviewed:** 2026-04-07
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Seven files reviewed covering the new filter/list plumbing: agent-message string constants, the `Resolver` class, `OperatorService` and its list pipelines, and the corresponding test suites. No security issues found. No logic bugs found. The code is well-structured and the test coverage is solid.

Two warnings (one a likely unintentional behaviour, one a maintainability hazard) and three info items. Test files are clean.

---

## Warnings

### WR-01: `_check_inbox_search_warning` fires on any substring of "Inbox", including single characters

**File:** `src/omnifocus_operator/service/service.py:376-378`

**Issue:** The containment check is reversed:

```python
if self._query.search.lower() in SYSTEM_LOCATIONS["inbox"].name.lower()
```

This reads: "if the search string is contained within 'Inbox'". So `search="i"`, `search="in"`, `search="b"`, `search="ox"` all trigger the warning. `test_search_in_substring_warns` (line 474 in `test_list_pipelines.py`) confirms `search="in"` triggers the warning and passes as expected behaviour.

A user running `list_projects(search="in")` to find projects with "in" in their name will receive a spurious inbox warning. The direction that makes intuitive sense is: warn when the search term could plausibly be looking for inbox — i.e., when "inbox" is a substring of the search term, not the reverse. For example, `search="inbox tasks"` would correctly warn; `search="in"` would not.

**Fix:** Reverse the check:

```python
# Warn when the search term contains "inbox" (e.g. "inbox tasks", "my inbox")
if SYSTEM_LOCATIONS["inbox"].name.lower() in self._query.search.lower()
```

If the current reversed direction is intentional per a specific spec requirement, add a comment explaining the rationale. The test `test_search_in_substring_warns` would need to be updated or removed.

---

### WR-02: `Resolver` has two incompatible resolution contracts with no documented boundary

**File:** `src/omnifocus_operator/service/resolve.py:50-52`

**Issue:** `Resolver` exposes two fundamentally different contracts on the same class with no documentation separating them:

- **Write-side (async):** `_resolve`, `resolve_container`, `resolve_anchor`, `resolve_tags` — each fetches entity data from the repository internally via `_fetch_all_by_type`.
- **Read-side (sync):** `resolve_filter`, `resolve_filter_list`, `find_unresolved` — operate on a pre-fetched `entities: Sequence[_HasIdAndName]` passed by the caller.

A developer adding a new caller who sees `Resolver.resolve_filter(value, entities)` might assume the same "pass a string, get an ID" semantics as `resolve_container(value)` — and be confused by the required pre-fetched argument, or might accidentally call it with an empty list and get silent no-match behaviour.

The class docstring currently says only: "Resolves user-facing identifiers against the repository."

**Fix:** Update the class docstring to document both contracts:

```python
class Resolver:
    """Resolves user-facing identifiers against the repository.

    Two resolution contracts:
    - Write-side (async): resolve_container / resolve_anchor / resolve_tags
      fetch entity data from the repository internally.
    - Read-side (sync): resolve_filter / resolve_filter_list / find_unresolved
      operate on pre-fetched entity lists passed by the caller. These are used
      by list pipelines that already hold fetched data.
    """
```

---

## Info

### IN-01: `TAG_NOT_FOUND` uses `{name}` placeholder but is called with a tag ID

**File:** `src/omnifocus_operator/agent_messages/errors.py:16` and `src/omnifocus_operator/service/resolve.py:211`

**Issue:** `TAG_NOT_FOUND = "Tag not found: {name}"` uses `{name}` as the placeholder, while `TASK_NOT_FOUND` and `PROJECT_NOT_FOUND` both use `{id}`. `lookup_tag` is a lookup-by-ID method and passes `tag_id` to `.format(name=tag_id)`, so the error message emits a tag ID labelled as if it were a name. The inconsistency is minor but could confuse an agent trying to parse error messages programmatically.

**Fix:** Align with the other two error templates:

```python
# errors.py line 16
TAG_NOT_FOUND = "Tag not found: {id}"

# resolve.py line 211
msg = TAG_NOT_FOUND.format(id=tag_id)
```

---

### IN-02: `_ListTasksPipeline._resolve_tags` skip-filter behaviour lacks a comment

**File:** `src/omnifocus_operator/service/service.py:334-335`

**Issue:** When all tag values fail to resolve, `all_resolved` stays empty and `self._tag_ids` is never assigned (remains `None`). This silently drops the tag filter entirely, returning all tasks. The parallel code in `_resolve_project` (line 307-310) is structured identically. Both implement the "skip filter on miss" contract, but neither has a comment naming that contract. A future reader editing one branch might add early-return logic that breaks the other.

**Fix:** One-line comment at the assignment site:

```python
if all_resolved:
    # One or more tags resolved — apply as filter.
    # If none resolved, tag_ids stays None (filter skipped; warnings emitted above).
    self._tag_ids = all_resolved
```

Same comment can be added to the `_resolve_project` equivalent at line 308-309.

---

### IN-03: `TestNoNotImplementedError` assertions are trivially true and provide no coverage value

**File:** `tests/test_list_pipelines.py:547-568`

**Issue:** All five tests in this class assert `result is not None`. Since every list method returns a `ListResult` dataclass (never `None`), these assertions can never fail regardless of what the method returns. The tests run against the default (likely empty) service fixture with no `@pytest.mark.snapshot` decorator. They add noise to the test count without guarding any real behaviour — a method could return `ListResult(items=[], total=0, has_more=False)` for completely broken logic and all five tests would still pass.

**Fix:** Either remove the class (callability is already covered by the snapshot-decorated tests above) or replace the assertions with a minimal structural check:

```python
async def test_list_tasks_callable(self, service: OperatorService) -> None:
    result = await service.list_tasks(ListTasksQuery())
    assert isinstance(result.items, list)
```

---

_Reviewed: 2026-04-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
