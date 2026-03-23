# Lifecycle Test Suite

Tests task completion, dropping, cross-state transitions, repeating task behavior, and lifecycle validation for `edit_tasks`.

## Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **1-item limit.** `edit_tasks` currently accepts exactly 1 item per call.

**Known issue — spurious "no changes" warning:** When a lifecycle action results in a no-op (e.g., completing an already-completed task) AND no field edits are in the request, a spurious "No changes specified/detected" warning fires alongside the specific lifecycle warning. Document in the report's Observations section if encountered.

## Setup

### Task Hierarchy

Create this structure in the inbox using `add_tasks`:

```
UAT-Lifecycle (parent)
+-- T1-Complete
+-- T2-Drop
+-- T3-CrossStateA
+-- T4-CrossStateB
+-- T5-Repeating
+-- T6-Combo
+-- T7-InvalidLifecycle
+-- T8-DeferLifecycle
```

Create the parent first, then all children (can be parallel). Store all IDs.

### Manual Actions

Ask the user to:
1. **Drop** T3-CrossStateA (right-click > Drop)
2. **Complete** T4-CrossStateB (check it off)
3. **Add a repeat rule** to T5-Repeating (e.g., "Repeat every week" — any rule works)

Tell them: "Please drop T3-CrossStateA, complete T4-CrossStateB, and add any repeat rule to T5-Repeating in OmniFocus. Let me know when done."

Wait for confirmation before proceeding. Then tell them: "Running all tests now. I'll report results when done."

## Tests

### 1. Basic Lifecycle

#### Test 1a: Complete a task
1. `actions: { lifecycle: "complete" }` on T1
2. `get_task` T1 to verify `availability: "completed"` and `completionDate` is set
3. PASS if: task completed, fields confirmed

#### Test 1b: Drop a task
1. `actions: { lifecycle: "drop" }` on T2
2. `get_task` T2 to verify `availability: "dropped"` and `dropDate` is set
3. PASS if: task dropped, fields confirmed

### 2. No-Op Lifecycle

#### Test 2a: No-op — complete already-completed
1. `actions: { lifecycle: "complete" }` on T1 (already completed from 1a)
2. PASS if: warning about "already complete", no bridge call

#### Test 2b: No-op — drop already-dropped
1. `actions: { lifecycle: "drop" }` on T2 (already dropped from 1b)
2. PASS if: warning about "already dropped", no bridge call

### 3. Cross-State Transitions

#### Test 3a: Complete a dropped task
1. `actions: { lifecycle: "complete" }` on T3 (dropped by user in setup)
2. PASS if: success with cross-state warning mentioning task was "previously dropped"

#### Test 3b: Drop a completed task
1. `actions: { lifecycle: "drop" }` on T4 (completed by user in setup)
2. PASS if: success with cross-state warning mentioning task was "previously completed"

### 4. Repeating Task Lifecycle

#### Test 4a: Repeating — complete
1. `actions: { lifecycle: "complete" }` on T5 (has repeat rule from setup)
2. PASS if: success with warning about "this occurrence completed, next occurrence created"

#### Test 4b: Repeating — drop (skip occurrence)
1. Re-fetch T5 via `get_task` — it may have a new ID after the repeat rule created the next occurrence from test 4a. If the original ID no longer refers to an active task, look for the task with the same name under UAT-Lifecycle using `get_all` or `get_project`.
2. `actions: { lifecycle: "drop" }` on the current T5 occurrence
3. PASS if: success with warning about occurrence being skipped
4. **Known issue:** Current warning text may be incomplete — it says "this occurrence was skipped" but should also mention "next occurrence created" and that dropping the entire sequence requires the OmniFocus UI. Note the actual wording in the report.

### 5. Lifecycle + Field Edit

#### Test 5: Complete + name change combo
1. `name: "T6-Completed", actions: { lifecycle: "complete" }` on T6
2. PASS if: both applied — name changed AND task completed

### 6. Invalid Lifecycle

Run INDIVIDUALLY (will error):

#### Test 6: Invalid lifecycle value
1. `actions: { lifecycle: "reopen" }` on T7
2. PASS if: clean error (no "type=", "input_value", "pydantic" internals)

### 7. Defer Date Lifecycle

#### Test 7a: Defer date blocks task
1. `deferDate: "2036-01-01T09:00:00+01:00"` on T8 (far-future date)
2. `get_task` T8
3. PASS if: task availability is NOT "available" (should be blocked/deferred due to future defer date)

#### Test 7b: Clear defer date unblocks task
1. `deferDate: null` on T8
2. `get_task` T8
3. PASS if: task availability returns to "available"

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Lifecycle: complete | Completing a task sets availability to "completed" and completionDate | |
| 1b | Lifecycle: drop | Dropping a task sets availability to "dropped" and dropDate | |
| 2a | No-op: complete completed | Completing already-completed returns warning | |
| 2b | No-op: drop dropped | Dropping already-dropped returns warning | |
| 3a | Cross-state: complete dropped | Completing a dropped task with cross-state warning | |
| 3b | Cross-state: drop completed | Dropping a completed task with cross-state warning | |
| 4a | Repeating: complete | Completing repeating task occurrence; next created | |
| 4b | Repeating: drop | Dropping/skipping repeating occurrence | |
| 5 | Lifecycle + field edit | Complete + name change in one call; both applied | |
| 6 | Invalid lifecycle | "reopen" returns clean validation error | |
| 7a | Defer: blocks task | Future deferDate changes availability away from "available" | |
| 7b | Defer: unblocks task | Clearing deferDate restores availability to "available" | |
