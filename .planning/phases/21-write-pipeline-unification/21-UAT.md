---
status: complete
phase: 21-write-pipeline-unification
source: [21-01-SUMMARY.md, 21-02-SUMMARY.md]
started: 2026-03-19T18:30:00Z
updated: 2026-03-19T18:34:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. Service payload symmetry
expected: Both add_task and edit_task use the same kwargs dict → model_validate() pattern. No _payload_to_repo mapping dict remains. add_task builds a sparse kwargs dict (only populated fields), not a full constructor call.
result: issue
reported: "Pattern is correct but variable naming is inconsistent: add_task uses `repo_kwargs` while edit_task uses `payload` for the same concept"
severity: minor

### 2. Snake_case throughout edit_task
expected: edit_task builds its payload dict using snake_case keys from the start (e.g., `due_date`, `estimated_minutes`, `add_tag_ids`). No camelCase intermediate dict. No camelCase-to-snake_case mapping step. The comment at line ~413 should confirm this: "payload dict already uses snake_case keys matching EditTaskRepoPayload fields."
result: pass

### 3. BridgeWriteMixin boundary clarity
expected: Open `src/omnifocus_operator/repository/bridge_write_mixin.py`. The mixin should be small (~30 lines), with a single `_send_to_bridge(command, payload)` method that centralizes `model_dump(by_alias=True, exclude_unset=True)` + `send_command`. It expects `_bridge: Bridge` on the concrete class. Does this boundary feel right — mixin handles serialization, repos handle caching/freshness?
result: pass

### 4. Mixin inheritance consistency
expected: Open `bridge.py` and `hybrid.py`. Both should inherit from `BridgeWriteMixin, Repository` (in that order). Their `add_task` and `edit_task` methods should call `self._send_to_bridge(command, payload)` instead of manually doing `payload.model_dump(...) + self._bridge.send_command(...)`. `in_memory.py` should inherit `Repository` only (no mixin — it doesn't use a bridge).
result: pass

### 5. Serialization standardization
expected: All write paths now use `exclude_unset=True` (not `exclude_none=True`). This is centralized in BridgeWriteMixin._send_to_bridge. No `exclude_none` should appear in any repo write method. The distinction matters: `exclude_unset` omits fields not set by the caller, while `exclude_none` would strip intentional null-clears.
result: pass

## Summary

total: 5
passed: 4
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Both add_task and edit_task use consistent variable naming for the kwargs dict passed to model_validate()"
  status: failed
  reason: "User reported: Pattern is correct but variable naming is inconsistent: add_task uses `repo_kwargs` while edit_task uses `payload` for the same concept"
  severity: minor
  test: 1
  root_cause: "Two atomic tasks in plan 01 each chose their own variable name without cross-harmonization. Task 1 introduced `repo_kwargs` in add_task, Task 2 kept the pre-existing `payload` in edit_task."
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "add_task line 144 uses `repo_kwargs`, edit_task line 213 uses `payload`"
  missing:
    - "Rename `repo_kwargs` to `payload` in add_task (3 occurrences: declaration, field assignments, model_validate call)"
  debug_session: ""
