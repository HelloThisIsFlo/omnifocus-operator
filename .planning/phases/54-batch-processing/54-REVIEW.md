---
phase: 54-batch-processing
reviewed: 2026-04-15T12:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/contracts/use_cases/add/tasks.py
  - src/omnifocus_operator/contracts/use_cases/edit/tasks.py
  - src/omnifocus_operator/server/handlers.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/service/service.py
  - tests/test_models.py
  - tests/test_output_schema.py
  - tests/test_preferences_warnings_surfacing.py
  - tests/test_server.py
  - tests/test_service.py
  - tests/test_service_domain.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 54: Code Review Report

**Reviewed:** 2026-04-15
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Phase 54 introduces batch processing for `add_tasks` and `edit_tasks` — best-effort (add) and fail-fast (edit) semantics, progress reporting, and the supporting batch-limit infrastructure in `config.py` and `descriptions.py`. The core logic is clean and the tests are thorough.

Three warnings and three info items. No critical issues.

The most substantive warning is a stale comment in `descriptions.py` that documents incorrect inheritance semantics to agents. The other two warnings are correctness gaps: a mismatched `_MAX_BATCH_SIZE` constant (decoupled from `config.MAX_BATCH_SIZE`) and a subtle inconsistency in `add_tasks` error attribution.

---

## Warnings

### WR-01: Stale Agent-Facing Inheritance Comment Is Factually Wrong

**File:** `src/omnifocus_operator/agent_messages/descriptions.py:44-51`

**Issue:** The `FIXME` on line 44 flags exactly this — the `_INHERITED_TASKS_EXPLANATION` string visible to agents says "the sooner date applies" for _all_ inherited fields. This is incorrect: `inheritedDeferDate` uses max (later wins), and `inheritedPlannedDate` / `inheritedDropDate` / `inheritedCompletionDate` use first-found. The comment is agent-facing text embedded in the MCP tool description (`GET_TASK_TOOL_DOC` and `LIST_TASKS_TOOL_DOC`), so it actively misleads agents about how inherited values work. The actual code in `domain.py` is correct (`_MIN_FIELDS`, `_MAX_FIELDS`, `_FIRST_FOUND_FIELDS`); only the agent description is wrong.

**Fix:** Update `_INHERITED_TASKS_EXPLANATION` to reflect the per-field semantics:

```python
_INHERITED_TASKS_EXPLANATION = """\
inherited* fields: value inherited from the hierarchy \
(parent task, project, folder). Both direct and inherited can coexist. \
inherited fields are read-only; \
to edit, use the direct field (dueDate, not inheritedDueDate). \
Aggregation: inheritedDueDate = min (earliest deadline); \
inheritedDeferDate = max (latest block); \
inheritedPlannedDate/dropDate/completionDate = nearest ancestor."""
```

Remove or resolve the FIXME comment at line 44 once updated.

---

### WR-02: `_MAX_BATCH_SIZE` Mirror in `descriptions.py` Can Silently Drift

**File:** `src/omnifocus_operator/agent_messages/descriptions.py:8-11`

**Issue:** `_MAX_BATCH_SIZE = 50` is a copy of `config.MAX_BATCH_SIZE`, introduced explicitly to avoid a circular import. The comment says "if `MAX_BATCH_SIZE` changes in `config.py`, update this value too" — but there is no automated guard preventing them from drifting. This is a latent bug: if someone bumps the config value, the tool description will lie to agents about the actual limit enforced by `Field(max_length=MAX_BATCH_SIZE)` in `handlers.py`.

**Fix:** Add a test that asserts the two values are equal:

```python
# In tests/test_output_schema.py or a dedicated config test
from omnifocus_operator.config import MAX_BATCH_SIZE
from omnifocus_operator.agent_messages.descriptions import _MAX_BATCH_SIZE

def test_batch_size_mirror_matches_config() -> None:
    """descriptions._MAX_BATCH_SIZE must mirror config.MAX_BATCH_SIZE."""
    assert _MAX_BATCH_SIZE == MAX_BATCH_SIZE, (
        f"descriptions._MAX_BATCH_SIZE ({_MAX_BATCH_SIZE}) != "
        f"config.MAX_BATCH_SIZE ({MAX_BATCH_SIZE}). Update the mirror."
    )
```

This makes any drift a CI failure rather than a silent contract lie.

---

### WR-03: `add_tasks` Error Message Prefix Doesn't Match `edit_tasks` — Agent Confusion Risk

**File:** `src/omnifocus_operator/server/handlers.py:144`

**Issue:** In `add_tasks`, errors are formatted as `f"Task {i + 1}: {e}"`. In `edit_tasks` (line 184), errors follow the same pattern: `f"Task {i + 1}: {e}"`. This is consistent. However, `AddTaskResult` has no `id` field in the error case — the handler constructs `AddTaskResult(status="error", error=f"Task {i + 1}: {e}")` with no `id`. Meanwhile `EditTaskResult` on error _does_ include `id=command.id` (line 182). This asymmetry means agents can't reliably identify which input item failed in `add_tasks` errors unless they reconstruct by position — a usability gap and a contract inconsistency.

The `_BATCH_RETURNS` description (line 71) says "id (success + edit errors/skips)" — correctly documenting that `id` is only present on `add_tasks` success. But agents working with batches may not notice the divergence without reading the description carefully.

**Fix:** Either document this asymmetry explicitly in the `AddTaskResult` docstring / description, or populate `name` (the input name) on error results so agents have a human-readable anchor:

```python
results.append(
    AddTaskResult(
        status="error",
        name=command.name,  # surface the attempted name for traceability
        error=f"Task {i + 1}: {e}",
    )
)
```

The `AddTaskResult` model already has `name: str | None = None`, so no contract change is needed.

---

## Info

### IN-01: `FIXME` Comment in Agent-Facing Description File

**File:** `src/omnifocus_operator/agent_messages/descriptions.py:44`

**Issue:** A `FIXME` comment marks known inaccurate agent-facing text (see WR-01). It references an internal research file (`.research/deep-dives/omnifocus-inheritance-semantics/FINDINGS.md`) that agents and users never see. The presence of acknowledged-wrong text in a production description file is a maintenance hazard.

**Fix:** Resolve after applying the fix in WR-01. No separate action needed once the description is corrected.

---

### IN-02: `TODO` Comment for a v1.5 Feature in Production Description

**File:** `src/omnifocus_operator/agent_messages/descriptions.py:449`

**Issue:** `# TODO(v1.5): Remove when built-in perspectives are supported` tags a note that's baked into the `list_perspectives` tool description. This is acceptable tracking, but the TODO milestone format is informal — there's no CI check that will catch it if v1.5 lands without removing it.

**Fix:** Either track it in `.planning/todos/pending/` (the project's canonical todo location) and remove the source comment, or leave it and accept the manual review burden at v1.5.

---

### IN-03: Unused `_EditTaskPipeline._all_warnings` List Attribute — Subtle Ordering Assumption

**File:** `src/omnifocus_operator/service/service.py:961-967`

**Issue:** `self._all_warnings` is assembled in `_build_payload` (line 961) but also used in `_detect_noop` (line 973) _and_ `_delegate` (line 983). The mutation inside `_all_fields_match` (which appends `REPETITION_NO_OP` and `MOVE_ALREADY_AT_POSITION` to `self._all_warnings` via the `warnings` list reference) creates an implicit ordering requirement: `_detect_noop` must be called after `_build_payload`, and the warnings list passed to `detect_early_return` is the same object as `self._all_warnings`.

This isn't a bug — the ordering is correct — but `detect_early_return` modifies its `warnings` parameter in place (via `warnings.append(...)` in `_all_fields_match`). This side-effect on a caller-owned list is easy to miss and could cause a double-append if the function is ever called twice or if `self._all_warnings` is reused elsewhere.

**Fix:** Low priority. Consider having `detect_early_return` return the final warning list rather than mutating the input, or at minimum add a comment noting the side-effect contract:

```python
# Note: detect_early_return may append to warnings (REPETITION_NO_OP,
# MOVE_ALREADY_AT_POSITION). self._all_warnings is intentionally shared.
if (early := self._detect_noop()) is not None:
```

---

_Reviewed: 2026-04-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
