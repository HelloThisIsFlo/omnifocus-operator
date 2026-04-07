---
phase: 42-read-output-restructure
reviewed: 2026-04-06T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - src/omnifocus_operator/models/common.py
  - src/omnifocus_operator/repository/bridge_only/adapter.py
  - src/omnifocus_operator/repository/bridge_only/bridge_only.py
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/simulator/data.py
  - tests/conftest.py
  - tests/test_adapter.py
  - tests/test_cross_path_equivalence.py
  - tests/test_hybrid_repository.py
  - tests/test_models.py
  - tests/test_server.py
  - tests/test_service_domain.py
  - tests/test_service.py
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: issues_found
---

# Phase 42: Code Review Report

**Reviewed:** 2026-04-06
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

This phase restructures the read output of OmniFocus Operator: introducing a two-axis status model (urgency + availability), a tagged ParentRef, ProjectRef on tasks, and enriched TaskRef/FolderRef on projects. The adapter, hybrid repository, models, simulator, tests, and conftest were all updated.

The code is well-structured with clear separation between the bridge adapter path and the SQLite hybrid path. No critical (security, data-loss) issues were found. The findings below are correctness risks or logic gaps that could silently produce wrong output.

## Warnings

### WR-01: `_parse_local_datetime` ignores DST — naive `replace(tzinfo=...)` is wrong for ambiguous times

**File:** `src/omnifocus_operator/repository/hybrid/hybrid.py:168`
**Issue:** The function attaches `_LOCAL_TZ` to a naive ISO string using `replace(tzinfo=...)`. This gives the correct UTC offset only when the offset is unambiguous at that wall-clock time. For times that fall in a DST fold (clocks going back), `replace()` always picks the first occurrence; for times in a DST gap (clocks going forward), it silently shifts. The correct call is `datetime(...).astimezone(UTC)` after constructing the naive datetime *localized* via `_LOCAL_TZ.fromutc(...)`, or simply using `naive.replace(tzinfo=_LOCAL_TZ)` followed by `.astimezone(UTC)` — which is what the code already does — BUT this is only correct if `_LOCAL_TZ` is a `zoneinfo.ZoneInfo`. Since it is, the DST fold is handled by Python's fold disambiguation, which defaults to `fold=0` (pre-transition). This is fine for almost all practical inputs but is a latent edge case during DST transitions.

More concretely: if OmniFocus stores a time in the fold window (23:00–01:00 during fall-back), the parsed UTC offset will be one hour off. This affects `due_date`, `defer_date`, and `planned_date` for tasks/projects.

**Fix:** Document this limitation explicitly and add `fold=0` as an intentional choice (it already is, implicitly). Alternatively guard with:
```python
naive = datetime.fromisoformat(value)
# fold=0 is the default: pre-transition occurrence is chosen during DST folds.
local_dt = naive.replace(tzinfo=_LOCAL_TZ)
utc_dt = local_dt.astimezone(UTC)
return utc_dt.isoformat()
```
This is already the code — the real fix is to add a comment documenting the intentional fold=0 default so maintainers don't accidentally "fix" it.

---

### WR-02: `adapt_snapshot` builds `task_names` lookup from the *pre-adaptation* bridge task list

**File:** `src/omnifocus_operator/repository/bridge_only/adapter.py:346`
**Issue:** The `task_names` dict used for enriching project `nextTask` references is built from the raw (not yet adapted) task list. Tasks at this point still have their bridge-format keys (e.g., `status`, old parent fields). This works currently because task name is in a plain `name` key in both bridge and model format, but it's fragile: the lookup is built before `_adapt_task` runs, so any future restructuring of the task dict before this point could silently produce empty names.

Specifically, `_enrich_project` calls `task_names.get(next_task_val, "")` on the lookup built before task adaptation. The tasks loop (`for task in raw.get("tasks", [])`) runs the adaptation step immediately after building `task_names`, but the lookup is already locked in before adaptation.

**Fix:** Build the `task_names` lookup after the per-entity adaptation loops, not before them. Names don't change during adaptation so this is safe:
```python
# Per-entity adaptation first
for task in raw.get("tasks", []):
    _adapt_task(task)
for project in raw.get("projects", []):
    _adapt_project(project)
# ...then build lookups from adapted data
task_names = {t["id"]: t["name"] for t in raw.get("tasks", []) if "id" in t}
```

---

### WR-03: `_adapt_parent_ref` uses `parentName` / `projectName` without verifying task-name lookup is populated

**File:** `src/omnifocus_operator/repository/bridge_only/adapter.py:171-186`
**Issue:** When enriching parent/project names, `_adapt_parent_ref` uses `raw.get("parentName", "")` and `raw.get("projectName", "")` as fallbacks rather than the cross-entity `task_names` / `project_names` lookup tables. This means the name resolution for parent task refs depends solely on the per-task convenience fields that the bridge sends. If the bridge omits `parentName` (a defensible future change), parent refs silently get empty names, which is valid model data but misleading to agents.

The `adapt_snapshot` function does build a `task_names` lookup but passes it only to `_enrich_project`, not to `_adapt_parent_ref`. The inconsistency means two different name-resolution strategies coexist in the same function.

**Fix:** Thread `task_names` into `_adapt_parent_ref` or, at minimum, fall back to the lookup when the per-task field is absent:
```python
def _adapt_parent_ref(raw: dict[str, Any], task_names: dict[str, str] | None = None) -> None:
    ...
    parent_name = raw.get("parentName") or (task_names or {}).get(parent_task_id, "")
```
This is a defensive improvement; current behavior is not a crash, but the silent empty-name fallback can mislead agents.

---

### WR-04: `_all_fields_match` no-op detection ignores `move_to.anchor_id` (before/after positions always return False)

**File:** `src/omnifocus_operator/service/domain.py:700-718`
**Issue:** The move no-op check explicitly returns `False` for `before`/`after` positions (line 718: `return False`). The comment says "can't detect same position" — this is correct for the general case, but it means that every `edit_task` call with a `before`/`after` move will bypass the no-op path and incur a bridge round-trip, even if the task is already in that position. This is a known, deliberate limitation (the code comments it), but it is not documented at the API/service contract level.

More importantly: if an agent submits a move request for a task that is already before/after its current sibling, the bridge call succeeds with a no-op effect but returns a success result with no warning. The agent has no signal that nothing changed.

**Fix:** Either document this as a known limitation (add a `# noqa` comment referencing a todo, or a docstring note on `detect_early_return`), or emit a `MOVE_SAME_CONTAINER`-style warning for `before`/`after` moves when the task is already in the correct relative position by resolving the anchor's actual position. If the former path, make the intention explicit:
```python
else:
    # before/after: cannot detect same-position without anchor resolution
    # TODO: emit a warning once anchor position lookup is available
    return False
```

---

## Info

### IN-01: Duplicated `_paginate` function between `bridge_only.py` and `hybrid.py`

**File:** `src/omnifocus_operator/repository/bridge_only/bridge_only.py:49-60` and `src/omnifocus_operator/repository/hybrid/hybrid.py:63-74`
**Issue:** Both files define an identical `_paginate[T]` helper. This is pure code duplication — any change to pagination semantics must be applied in two places.
**Fix:** Extract to a shared `repository/_utils.py` or the existing `repository/` `__init__` and import from both.

---

### IN-02: `SIMULATOR_SNAPSHOT` includes `effectiveCompletionDate` on tasks but not on projects — inconsistency with model comments

**File:** `src/omnifocus_operator/simulator/data.py:40`
**Issue:** The simulator snapshot includes `"effectiveCompletionDate": None` on task entries (line 40, 70, 98, etc.) but the `conftest.py` `make_model_task_dict` also includes it (line 219). The `make_model_project_dict` comment at line 241 says "(Project does NOT have effectiveCompletionDate -- that's Task-only)". The simulator and conftest are consistent with each other, but the field appears as a raw string key in both — if the Task model drops or renames this field, the simulator snapshot silently stops exercising it (Pydantic ignores extra fields by default unless `extra="forbid"` is set). This is a testing gap rather than a production risk.
**Fix:** Consider adding an `extra="forbid"` test variant to catch schema drift in simulator/conftest data, or add a dedicated schema-validation test that round-trips the `SIMULATOR_SNAPSHOT` through Pydantic and asserts no fields are silently dropped.

---

### IN-03: `conftest.py` `make_task_dict` comment says "26 bridge fields" but the field count is 27

**File:** `tests/conftest.py:29`
**Issue:** The docstring says "Returns a complete task dict with all 26 bridge fields." Counting the `defaults` dict keys: `id, name, url, note, added, modified, status, flagged, effectiveFlagged, dueDate, deferDate, effectiveDueDate, effectiveDeferDate, completionDate, effectiveCompletionDate, plannedDate, effectivePlannedDate, dropDate, effectiveDropDate, estimatedMinutes, hasChildren, inInbox, repetitionRule, project, parent, tags` = 26. The test at line 456 asserts `len(d) == 26` for `make_model_task_dict`, not `make_task_dict`, so there's no assertion mismatch — but the comment should be verified against the actual count to avoid confusion.
**Fix:** Count and update the docstring. Low-risk but worth keeping accurate since `test_models.py` asserts exact field counts for the model factories.

---

### IN-04: `_ensure_write_through` decorator uses wall-clock `time.monotonic()` loop with `asyncio.sleep(0.05)` — blocks event loop briefly on each iteration

**File:** `src/omnifocus_operator/repository/hybrid/hybrid.py:568-575`
**Issue:** `await asyncio.sleep(0.05)` in a polling loop is fine for an infrequent operation (write path), but the loop has no early-exit on cancellation. If the caller is cancelled (e.g., timeout at the MCP layer), the `_wait_for_fresh_data` coroutine will not be cancelled until the next `asyncio.sleep` yields. This is a minor robustness gap rather than a current bug.
**Fix:** No immediate change required. If cancellation semantics become important, wrap with `asyncio.shield` or add a `CancelledError` handler. Consider noting this in the decorator docstring.

---

### IN-05: `test_cross_path_equivalence.py` — bridge seed uses `status="Blocked"` for tasks with `availability="blocked"`, but FALL-02 tests document that bridge never sends "Blocked"

**File:** `tests/test_cross_path_equivalence.py:277`
**Issue:** `seed_bridge_repo` maps `"blocked"` availability to `_BRIDGE_AVAILABILITY_MAP["blocked"]` which resolves to `"Blocked"` status. The `TestFall02BridgeAvailabilityLimitation` tests in `test_adapter.py` (lines 720-758) document that the real OmniJS bridge never sends `"Blocked"` for tasks (OmniJS can't detect blocking). The cross-path tests therefore exercise an adapter path that the real bridge will never produce, creating a false equivalence: the cross-path tests pass but the bridge path never produces `availability="blocked"` for tasks in practice.

This is a documentation/intent gap: the cross-path tests prove the *adapter* handles `"Blocked"` correctly (it does), but they don't prove that bridge and SQLite are equivalent in real usage (where bridge tasks are always `available/completed/dropped`).
**Fix:** Add a comment in `seed_bridge_repo` acknowledging this discrepancy. Optionally, split the cross-path tests into "shared-availability" cases (using only `available`) and "SQLite-only" cases (using `blocked`).

---

_Reviewed: 2026-04-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
