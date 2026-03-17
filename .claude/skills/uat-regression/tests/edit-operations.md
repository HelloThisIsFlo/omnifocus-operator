# Edit Operations Test Suite

Tests field editing, patch semantics, no-op warnings, status warnings, error handling, and combo scenarios for `edit_tasks`.

## Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **Timezone required.** Date fields need timezone info in ISO 8601 (e.g., `+01:00` or `Z`). Without it, Pydantic rejects the value.
- **1-item limit.** `edit_tasks` currently accepts exactly 1 item per call.

## Setup

### Task Hierarchy

Create this structure in the inbox using `add_tasks`:

```
UAT-EditOps (parent)
+-- T1-NoteOps
+-- T2-FieldEditing
+-- T3-NoopWarnings
+-- T4-StatusComplete
+-- T5-StatusDrop
+-- T6-Errors
```

Create the parent first, then all children (can be parallel). Store all IDs.

### Manual Actions

Ask the user to:
1. **Complete** T4-StatusComplete (check it off in OmniFocus)
2. **Drop** T5-StatusDrop (right-click > Drop)

Tell them: "Please complete T4-StatusComplete and drop T5-StatusDrop in OmniFocus. Let me know when done."

Wait for confirmation before proceeding to tests. Then tell them: "Running all tests now. I'll report results when done."

## Tests

### 1. Note Operations

#### Test 1a: note: null clears the note
1. `note: "hello"` on T1
2. `note: null` on T1
3. PASS if: success, no error

#### Test 1b: note: "" clears the note
1. `note: "some text"` on T1
2. `note: ""` on T1
3. `get_task` T1 and verify note is empty
4. PASS if: success, note cleared

### 2. Field Editing

#### Test 2a: Patch semantics
1. Set `name: "T2-Updated", flagged: true, note: "test note", estimatedMinutes: 30` on T2
2. Edit only `flagged: false` on T2
3. `get_task` T2 and verify: name still "T2-Updated", note still "test note", estimatedMinutes still 30
4. PASS if: untouched fields preserved

#### Test 2b: Date fields set + clear
1. `dueDate: "2026-03-15T17:00:00+01:00", deferDate: "2026-03-10T09:00:00+01:00"` on T2
2. Verify success
3. `dueDate: null, deferDate: null` on T2
4. PASS if: both set and clear succeed

#### Test 2c: estimatedMinutes set + clear
1. `estimatedMinutes: 45` on T2
2. `estimatedMinutes: null` on T2
3. PASS if: both succeed

#### Test 2d: Name change
1. `name: "T2-Renamed"` on T2
2. Verify response shows new name
3. `name: "T2-FieldEditing"` (rename back)
4. PASS if: both succeed, response reflects new name

#### Test 2e: Multi-field single call
1. `flagged: true, note: "multi", estimatedMinutes: 60, dueDate: "2026-03-20T12:00:00+01:00"` on T2
2. `get_task` to verify all four fields
3. PASS if: all four applied in one call

#### Test 2f: plannedDate set + clear
1. `plannedDate: "2026-03-12T10:00:00+01:00"` on T2
2. Verify success
3. `plannedDate: null` on T2
4. PASS if: both set and clear succeed

### 3. No-Op Warnings

#### Test 3a: No-op — empty edit
1. Edit T3 with only `id`, no other fields
2. PASS if: success with warning about no changes specified

#### Test 3b: No-op — same flagged
1. `flagged: true` on T3
2. `flagged: true` again on T3
3. PASS if: second call returns warning about no changes detected

#### Test 3c: No-op — same name
1. `name: "T3-NoopWarnings"` on T3 (its current name)
2. PASS if: warning about no changes detected

#### Test 3d: No-op — same dueDate
1. `dueDate: "2026-04-01T12:00:00+01:00"` on T3
2. `dueDate: "2026-04-01T12:00:00+01:00"` again on T3
3. PASS if: second call returns warning about no changes detected
4. Clean up: `dueDate: null` on T3

#### Test 3e: No-op — same estimatedMinutes
1. `estimatedMinutes: 15` on T3
2. `estimatedMinutes: 15` again on T3
3. PASS if: second call returns warning about no changes detected
4. Clean up: `estimatedMinutes: null` on T3

#### Test 3f: No-op — same deferDate
1. `deferDate: "2026-04-01T09:00:00+01:00"` on T3
2. `deferDate: "2026-04-01T09:00:00+01:00"` again on T3
3. PASS if: second call returns warning about no changes detected
4. Clean up: `deferDate: null` on T3

#### Test 3g: No-op — same plannedDate
1. `plannedDate: "2026-04-01T10:00:00+01:00"` on T3
2. `plannedDate: "2026-04-01T10:00:00+01:00"` again on T3
3. PASS if: second call returns warning about no changes detected
4. Clean up: `plannedDate: null` on T3

#### Test 3h: No-op — note null on already-empty note
1. Ensure T3 has no note (`note: null` first if needed)
2. `note: null` on T3
3. PASS if: warning about no changes detected

### 4. Status Warnings

#### Test 4a: Editing a completed task
1. `flagged: true` on T4 (completed by user in setup)
2. PASS if: success with warning mentioning "completed"

#### Test 4b: Editing a dropped task
1. `name: "T5-Dropped"` on T5 (dropped by user in setup)
2. PASS if: success with warning mentioning "dropped"

### 5. Error Handling

Run each INDIVIDUALLY (they will error):

#### Test 5a: Nonexistent task ID
1. `edit_tasks` with `id: "nonexistent-id-12345", name: "nope"`
2. PASS if: clean error mentioning "not found"

#### Test 5b: Empty name
1. `name: ""` on T6
2. PASS if: error about name cannot be empty

### 6. Combinations

#### Test 6a: note null + field change
1. `note: "will be cleared", flagged: false` on T1
2. `note: null, flagged: true` on T1
3. PASS if: success, both applied, no error

#### Test 6b: No-op on completed task — status warning suppressed
1. `flagged: true` on T4 (already completed, already flagged from Test 4a)
2. PASS if: only "no changes detected" warning — the status warning ("your changes were applied") must NOT appear since nothing changed

#### Test 6c: Multi-task batch (known limitation)
1. Send 3 items in one `edit_tasks` call
2. PASS if: error about 1-item limit (expected limitation, confirms guard works)

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | note: null | Setting note to null clears the note without error | |
| 1b | note: "" | Setting note to empty string also clears the note | |
| 2a | Patch semantics | Editing one field preserves all other fields unchanged | |
| 2b | Date set + clear | Setting dueDate and deferDate, then clearing both with null | |
| 2c | estimatedMinutes set + clear | Setting estimatedMinutes, then clearing with null | |
| 2d | Name change | Renaming a task; response reflects the new name | |
| 2e | Multi-field single call | Setting 4 fields in one call; all applied | |
| 2f | plannedDate set + clear | Setting plannedDate, then clearing with null | |
| 3a | No-op: empty edit | Sending only an ID with no fields returns "no changes specified" | |
| 3b | No-op: same flagged | Setting flagged to its current value returns "no changes detected" | |
| 3c | No-op: same name | Setting name to its current value returns a warning | |
| 3d | No-op: same dueDate | Setting dueDate to the same value returns a warning | |
| 3e | No-op: same estimatedMinutes | Setting estimatedMinutes to its current value returns a warning | |
| 3f | No-op: same deferDate | Setting deferDate to the same value returns a warning | |
| 3g | No-op: same plannedDate | Setting plannedDate to the same value returns a warning | |
| 3h | No-op: note null on empty | Setting note to null when already empty returns a warning | |
| 4a | Status: completed task | Editing a completed task succeeds with "completed" warning | |
| 4b | Status: dropped task | Editing a dropped task succeeds with "dropped" warning | |
| 5a | Error: nonexistent task | Editing a fake task ID returns "not found" | |
| 5b | Error: empty name | Setting name to "" returns a validation error | |
| 6a | Combo: note null + field | Clearing note and changing flagged in one call; both applied | |
| 6b | No-op on completed | No-op suppresses status warning, shows only "no changes" | |
| 6c | Combo: batch limit | Sending 3 items returns 1-item limit error | |
