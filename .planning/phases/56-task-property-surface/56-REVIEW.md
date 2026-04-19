---
phase: 56-task-property-surface
reviewed: 2026-04-19T22:00:00Z
depth: standard
files_reviewed: 38
files_reviewed_list:
  - bridge/tests/bridge.test.js
  - bridge/tests/handleEditTask.test.js
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/bridge/bridge.js
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/contracts/use_cases/add/tasks.py
  - src/omnifocus_operator/contracts/use_cases/edit/tasks.py
  - src/omnifocus_operator/models/__init__.py
  - src/omnifocus_operator/models/common.py
  - src/omnifocus_operator/models/enums.py
  - src/omnifocus_operator/models/project.py
  - src/omnifocus_operator/models/task.py
  - src/omnifocus_operator/repository/bridge_only/adapter.py
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/repository/hybrid/query_builder.py
  - src/omnifocus_operator/server/projection.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/service/payload.py
  - src/omnifocus_operator/service/preferences.py
  - src/omnifocus_operator/service/service.py
  - src/omnifocus_operator/simulator/data.py
  - tests/conftest.py
  - tests/doubles/bridge.py
  - tests/golden_master/snapshots/README.md
  - tests/golden_master/test_task_property_surface_golden.py
  - tests/test_adapter.py
  - tests/test_bridge.py
  - tests/test_contracts_field_constraints.py
  - tests/test_contracts_repetition_rule.py
  - tests/test_cross_path_equivalence.py
  - tests/test_descriptions.py
  - tests/test_hybrid_repository.py
  - tests/test_models.py
  - tests/test_preferences.py
  - tests/test_projection.py
  - tests/test_server.py
  - tests/test_service.py
  - tests/test_service_domain.py
  - tests/test_service_payload.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 56: Code Review Report

**Reviewed:** 2026-04-19T22:00:00Z
**Depth:** standard
**Files Reviewed:** 38
**Status:** issues_found

## Summary

Phase 56 delivers the task property surface end-to-end: bridge preference extension, cache-backed reads on both repos, derived presence flags, expanded `hierarchy` include group, and writable `completesWithChildren` / `type` on tasks. Implementation quality is high — SAFE-01/02 preserved across all new tests, FLAG-08 rejection is strict without leaking custom messaging, HIER-05 precedence is proven cross-path, and the PROP-07 guardrail is structural rather than behavioural (clean signal for v1.7).

One correctness issue: preferences warnings are drained twice in `_AddTaskPipeline.execute`, producing duplicate `SETTINGS_FALLBACK_WARNING` / `SETTINGS_UNKNOWN_DUE_SOON_PAIR` in `AddTaskResult.warnings` when the bridge fails or returns an unknown DueSoon pair. Three Info items cover acknowledged duplication and minor consistency notes.

No security issues found. All SQL is parameterised, no `eval`, no injection surfaces introduced. No hardcoded secrets. JS bridge uses `console.error` only (intentional error reporting path). Phase 56 does not broaden the security surface beyond what v1.3/v1.4 already accepted.

## Warnings

### WR-01: Preferences warnings duplicated in `_AddTaskPipeline` output

**File:** `src/omnifocus_operator/service/service.py:584,597`
**Issue:** Both `_normalize_dates` (line 597) and `_resolve_type_defaults` (line 584) call `await self._preferences.get_warnings()` and extend `self._preferences_warnings` with the result. Because `OmniFocusPreferences` caches warnings for the server lifetime (populated once during `_ensure_loaded`) and `get_warnings()` returns a copy of the full accumulated list, the second call re-appends the same warning strings. `AddTaskResult.warnings` then contains duplicates when the bridge fails (`SETTINGS_FALLBACK_WARNING`) or returns an unknown DueSoon pair (`SETTINGS_UNKNOWN_DUE_SOON_PAIR`).

Concrete reproduction:
- `add_task(name="x", due_date="2026-07-15")` with a bridge that fails `get_settings`.
- `_normalize_dates` triggers `_ensure_loaded`; preferences populate `_warnings = [SETTINGS_FALLBACK_WARNING]`; pipeline's `_preferences_warnings = [SETTINGS_FALLBACK_WARNING]`.
- `_resolve_type_defaults` runs; preferences already loaded (no-op); `get_warnings()` returns the same single-item list; pipeline's `_preferences_warnings = [SETTINGS_FALLBACK_WARNING, SETTINGS_FALLBACK_WARNING]`.
- `AddTaskResult.warnings` emitted with the duplicate.

Existing tests (`tests/test_preferences_warnings_surfacing.py`) assert membership (`in result.warnings`), not count, so the bug passes under current coverage. `_EditTaskPipeline` is unaffected — it drains warnings once in its `_normalize_dates` (line 747). `_ReadPipeline._resolve_date_filters` (line 340) also drains once.

**Fix:** Drain preferences warnings exactly once per pipeline run. Remove the redundant line-584 drain from `_resolve_type_defaults`, since `_normalize_dates` always runs before it in `execute` (line 551 before line 555) and the warnings list is stable once loaded:

```python
async def _resolve_type_defaults(self) -> None:
    """PROP-05 / PROP-06: resolve completes_with_children and type explicitly. ..."""
    if is_set(self._command.completes_with_children):
        self._resolved_completes_with_children: bool = self._command.completes_with_children
    else:
        self._resolved_completes_with_children = (
            await self._preferences.get_complete_with_children_default()
        )

    if is_set(self._command.type):
        self._resolved_type: str = self._command.type.value
    else:
        self._resolved_type = await self._preferences.get_task_type_default()
    # Warnings already drained by _normalize_dates — preferences is lazy-load-once,
    # so there is nothing new to surface here.
```

Add a regression test asserting exact count (not just membership):

```python
async def test_fallback_warning_appears_exactly_once_in_add_task_result(self) -> None:
    bridge = FailingSettingsBridge()
    service = _make_service(bridge)
    result = await service.add_task(AddTaskCommand(name="Test task", due_date="2026-07-15"))
    assert result.warnings.count(SETTINGS_FALLBACK_WARNING) == 1
```

## Info

### IN-01: HIER-05 project-type precedence duplicated across three layers

**File:**
- `src/omnifocus_operator/repository/hybrid/hybrid.py:474-479` (`_map_project_row`)
- `src/omnifocus_operator/repository/bridge_only/adapter.py:253-260` (`_adapt_project_property_surface`)
- `src/omnifocus_operator/service/domain.py:337-362` (`DomainLogic.assemble_project_type`)

**Issue:** The `(sequential, containsSingletonActions) -> ProjectType` truth table is open-coded in each repository adapter and again in the domain layer. The domain method (`assemble_project_type`) is not currently called by either repository; it exists as "the lock" per its docstring, but that lock is advisory — a change in one location wouldn't trip any test that calls the other two. `TestDomainLogicAssembleProjectType` covers the domain copy only. Cross-path equivalence tests (`TestPropertySurfaceCrossPath`) catch same-seed drift between the two repos but wouldn't catch a coordinated drift in the same direction on both.

The duplication is explicitly called out in the `assemble_project_type` docstring, so this is acknowledged technical debt rather than a new finding. Flagging for visibility ahead of any v1.5+ consolidation.

**Fix:** Either (a) wire both repositories through `DomainLogic.assemble_project_type` so there is one source of truth, or (b) add a unit test that asserts the three implementations agree on all four input permutations, catching coordinated drift. Lowest-cost step: a single parametrised test in `tests/test_cross_path_equivalence.py` or `tests/test_adapter.py` that exercises the four-row truth table against all three code paths.

### IN-02: Bridge description `COMPLETES_WITH_CHILDREN_DESC` names only one derivation surface

**File:** `src/omnifocus_operator/agent_messages/descriptions.py:151-157`
**Issue:** The description reads "the task surface exposes the derivation via `dependsOnChildren` on tasks with children." That wording is correct for tasks, but the field is also surfaced on projects through the `hierarchy` include group (HIER-02), where `dependsOnChildren` does not exist (FLAG-04/05 are tasks-only). An agent reading the project-side schema entry could infer that a project-level `dependsOnChildren` analogue exists.

**Fix:** Tighten the wording, for example: "Always present on the `hierarchy` include group; on tasks, the related derivation surface is `dependsOnChildren`. Projects expose the value only through `hierarchy`."

### IN-03: `_adapt_task_property_surface` and `_adapt_project_property_surface` duplicate four of five lines

**File:** `src/omnifocus_operator/repository/bridge_only/adapter.py:228-263`
**Issue:** The three presence-flag lines (`hasNote`, `hasRepetition`, `hasAttachments`) and the `completesWithChildren` pop are identical across both helpers; only the `type` resolution differs (two-state for tasks, three-state HIER-05 for projects). Not a bug — readability at the current size is fine. Flagging as a candidate refactor if the property surface grows (e.g., v1.5 adds another shared derived field).

**Fix:** Optional. If a future shared flag lands, extract a `_adapt_shared_property_surface(raw)` helper that handles `hasNote` / `hasRepetition` / `hasAttachments` / `completesWithChildren`, then call it from both task and project adapters before the type-resolution branch.

---

_Reviewed: 2026-04-19T22:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
