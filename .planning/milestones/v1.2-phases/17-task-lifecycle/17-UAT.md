---
status: complete
phase: 17-task-lifecycle
source: [17-01-SUMMARY.md, 17-02-SUMMARY.md]
started: 2026-03-12T10:00:00Z
updated: 2026-03-12T19:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running omnifocus-operator server. Start it fresh. The server boots without errors and responds to a basic MCP tool call (e.g., get_all or get_task).
result: pass

### 2. Complete a Task
expected: Call edit_tasks with lifecycle "complete" on an active task. The task is marked complete in OmniFocus. Response confirms the action with no errors.
result: pass

### 3. Drop a Task
expected: Call edit_tasks with lifecycle "drop" on an active task. The task is dropped in OmniFocus. Response confirms the action with no errors.
result: pass

### 4. No-Op: Complete Already-Completed Task
expected: Call edit_tasks with lifecycle "complete" on a task that is already completed. Response returns a no-op warning indicating the task is already in the requested state. No bridge call made.
result: pass

### 5. No-Op: Drop Already-Dropped Task
expected: Call edit_tasks with lifecycle "drop" on a task that is already dropped. Response returns a no-op warning indicating the task is already in the requested state. No bridge call made.
result: pass

### 6. Cross-State: Complete a Dropped Task
expected: Call edit_tasks with lifecycle "complete" on a dropped task. The task is completed (state changes from dropped to complete). Response includes a cross-state warning noting the task was previously dropped.
result: pass

### 7. Cross-State: Drop a Completed Task
expected: Call edit_tasks with lifecycle "drop" on a completed task. The task is dropped (state changes from complete to dropped). Response includes a cross-state warning noting the task was previously completed.
result: pass

### 8a. Repeating Task: Complete
expected: Call edit_tasks with lifecycle "complete" on a repeating task. The task occurrence is completed (next occurrence created by OmniFocus). Response includes a warning about repeating task behavior.
result: pass

### 8b. Repeating Task: Drop
expected: Call edit_tasks with lifecycle "drop" on a repeating task. The occurrence is skipped.
result: pass
reported: "Drop warning says 'this occurrence was skipped' but should say 'this occurrence was skipped, next occurrence created. To drop the entire repeating sequence, this must be done in the OmniFocus UI. Confirm with user if this was their intent.'"
severity: minor

### 9. Lifecycle + Field Edit Combination
expected: Call edit_tasks with lifecycle "complete" AND a field change (e.g., flagged or name) on the same task. Both the lifecycle action and field edit are applied. Response confirms both changes.
result: pass

### 10. Invalid Lifecycle Value Rejected
expected: Call edit_tasks with lifecycle set to an invalid value (e.g., "reopen"). Response returns a validation error, task is unchanged.
result: pass

### 11. No-Op Action Triggers Spurious "No changes specified" Warning
expected: When an action (lifecycle, move, or tags) is processed but results in a no-op, only the action-specific no-op warning should appear. The generic "No changes specified" field warning should NOT also appear.
result: issue
reported: "Whenever an action generates a no-op (lifecycle no-op, same-container move, tag no-op), the generic 'No changes specified' field warning is also emitted. The bug is that both the action-specific no-op warning AND the generic field no-op warning fire together. Either show the action-specific warning or the generic one, never both."
severity: minor

### 12. Same-Container Move Warning (discovered during investigation)
expected: When moving a task to a container it's already in (beginning/ending), the warning should explain the OmniFocus API limitation and suggest using before/after with a sibling ID as a workaround.
result: issue
reported: "Same-container move silently does nothing. Warning needs to explain the API limitation and workaround: use 'before' or 'after' with a sibling task ID. Full fix deferred to post-v1.3 when filtering infrastructure exists. See todo: fix-same-container-move-by-translating-to-movebefore-moveafter.md"
severity: minor

## Summary

total: 12
passed: 10
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "When an action (lifecycle, move, tags) results in a no-op, only the action-specific warning should appear — not the generic field-level no-op warning"
  status: failed
  reason: "User reported: Whenever an action generates a no-op, the generic field-level warning also fires. Both the action-specific no-op and the generic no-op appear together. Either show the action-specific warning or the generic one, never both."
  severity: minor
  test: 11
  root_cause: |
    Two code paths produce generic no-op warnings that stack on top of action-specific warnings:
    1. service.py:285 `len(payload)==1` → "No changes specified" — fires for lifecycle no-op (lifecycle not added to payload when no-op) and tag no-op (empty diff → nothing added)
    2. service.py:351 `is_noop and len(payload)>=1` → "No changes detected" — fires for same-container move (moveTo IS in payload but is_noop stays True)
    Both paths blindly append their generic warning even when `warnings` already contains action-specific no-op messages.
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "Line 285: empty-edit guard fires even when actions were processed but no-oped"
    - path: "src/omnifocus_operator/service.py"
      issue: "Line 351: field no-op guard fires even when action-specific warnings already present"
  missing:
    - "Both no-op guards (lines 285 and 351) should suppress the generic warning when action-specific warnings are already present in `warnings`"
  debug_session: ""

- truth: "Drop warning on repeating tasks should inform about full sequence implications"
  status: failed
  reason: "User reported: Drop warning says 'this occurrence was skipped' but should say 'this occurrence was skipped, next occurrence created. To drop the entire repeating sequence, this must be done in the OmniFocus UI. Confirm with user if this was their intent.'"
  severity: minor
  test: 8b
  root_cause: "service.py:420 drop warning text is too terse — doesn't mention next occurrence creation or that dropping the full sequence requires the OmniFocus UI"
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "Line 420: drop warning text incomplete"
  missing:
    - "Update warning text to: 'Repeating task -- this occurrence was skipped, next occurrence created. To drop the entire repeating sequence, this must be done in the OmniFocus UI. Confirm with user if this was their intent.'"
  debug_session: ""

- truth: "Same-container move warning should explain API limitation and workaround"
  status: failed
  reason: "User reported: Same-container move silently does nothing. Warning needs to explain the API limitation and workaround: use 'before' or 'after' with a sibling task ID. Full fix deferred to post-v1.3. See todo: fix-same-container-move-by-translating-to-movebefore-moveafter.md"
  severity: minor
  test: 12
  root_cause: "OmniFocus API limitation: moveTo beginning/ending is a no-op when task is already in the target container"
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "Same-container move warning at lines 339-343 needs updated wording"
  missing:
    - "Update warning text to explain limitation and suggest before/after workaround"
  debug_session: ""
