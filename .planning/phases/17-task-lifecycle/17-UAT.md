---
status: diagnosed
phase: 17-task-lifecycle
source: [17-01-SUMMARY.md, 17-02-SUMMARY.md]
started: 2026-03-12T10:00:00Z
updated: 2026-03-12T10:15:00Z
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

### 11. No-Op Secondary Warning (observation)
expected: No-op lifecycle (e.g., complete an already-completed task) should only produce the no-op warning.
result: issue
reported: "No-op complete/drop also emits a secondary 'No changes specified' warning — slightly noisy since the user did specify a lifecycle action, it just happened to be redundant"
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

- truth: "No-op lifecycle should only produce the no-op warning, not an additional 'No changes specified' warning"
  status: failed
  reason: "User reported: No-op complete/drop also emits a secondary 'No changes specified' warning — slightly noisy since the user did specify a lifecycle action, it just happened to be redundant"
  severity: minor
  test: 11
  root_cause: "service.py:285 early-return check `len(payload) == 1` fires when lifecycle is no-op because no-op lifecycle doesn't add 'lifecycle' key to payload. The check doesn't account for lifecycle_handled=True meaning the user DID specify an action."
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "Line 285: empty-edit guard doesn't check lifecycle_handled flag"
  missing:
    - "Add `and not lifecycle_handled` condition to the len(payload)==1 check at line 285"
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
