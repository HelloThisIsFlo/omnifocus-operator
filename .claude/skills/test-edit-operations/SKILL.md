---
name: test-edit-operations
description: Run comprehensive UAT regression tests for the OmniFocus Operator edit_tasks MCP tool against the live OmniFocus database. Tests field editing, tag operations, task movement, error handling, no-op warnings, status warnings, and edge cases. Trigger when the user says "test edit operations", "UAT edit", "regression test edit_tasks", "run edit tests", or wants to verify edit_tasks behavior after code changes. This skill requires the omnifocus-operator MCP server to be running.
---

# Test Edit Operations

Run a full regression suite for the `edit_tasks` MCP tool against live OmniFocus. All tests use only inbox tasks that are created at the start and cleaned up at the end.

The session has three phases:
1. **Interactive setup** (~2 minutes): Create test tasks, then ask the user to complete and drop specific tasks in OmniFocus (these are manual OmniFocus actions the MCP server intentionally doesn't expose)
2. **Autonomous testing** (runs to completion): Execute all test cases, collect results, report
3. **Cleanup**: User manually deletes test tasks (`delete_tasks` is not yet implemented — remind the user to delete UAT-Regression and its children in OmniFocus when they're ready)

## Important Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **Tags by ID.** Some tag names are ambiguous (multiple tags share a name). Always discover tags first via `get_all`, then use IDs for tags where the name might be ambiguous. Pick 3 distinct, unambiguous tags for testing. If all tag names risk ambiguity, use IDs exclusively.
- **No parallel error calls.** Claude Code cancels all sibling calls when one errors. Never mix calls that might fail (nonexistent IDs, validation errors) with calls that must succeed. Run error-expecting calls individually.
- **Timezone required.** Date fields need timezone info in ISO 8601 (e.g., `+01:00` or `Z`). Without it, Pydantic rejects the value.
- **Inbox move syntax.** To move a task to inbox, use `{"actions": {"move": {"ending": null}}}` or `{"actions": {"move": {"beginning": null}}}` — NOT `actions: null` (that means "no actions").
- **1-item limit.** `edit_tasks` currently accepts exactly 1 item per call. Batch tests should expect this limitation.

## Phase 1: Interactive Setup

### Step 1.1 — Discover Tags

Call `get_all` and extract the tags list. Pick 3 tags that:
- Have unique names (no ambiguity)
- Are simple/safe to add and remove

Store their IDs and names. Also check if any tag name maps to 2+ tag IDs (for test 8g). Store the ambiguous name if found.

### Step 1.2 — Create Test Hierarchy

Use `add_tasks` to create this structure in the inbox:

```
UAT-Regression (parent)
+-- T1-RemoveTags
+-- T2-NoteNull
+-- T3-ValidationNoise
+-- T4-NoopWarnings
+-- T5-StatusWarning
+-- T6-Movement
|   +-- T6a-Child1
|   +-- T6b-Child2
|       +-- T6b1-Grandchild
+-- T7-FieldEditing
+-- T8-TagOps
+-- T9-Errors
+-- T10-LifecycleA
+-- T10-LifecycleB
```

Create the parent first, then all level-1 children (can be parallel), then T6's children sequentially (T6b needs to exist before T6b1).

Store all IDs in a reference table — you'll need them for every subsequent step.

### Step 1.3 — User Interaction

Ask the user to perform these manual actions in OmniFocus:

1. **Complete** T5-StatusWarning (check it off)
2. **Drop** T6a-Child1 (right-click > Drop, or however they prefer) — T6a is reused in Test 12e (cross-state lifecycle)
3. **If no ambiguous tag name was found in Step 1.1**: Ask the user to create two tags with the same name (e.g., create a tag named "TestDupe" under two different parent tags in OmniFocus). This enables test 8g (ambiguous tag resolution). If the user declines, test 8g will be SKIPPED.

Tell them: "Please complete T5-StatusWarning and drop T6a-Child1 in OmniFocus. Also, if you'd like to test ambiguous tag handling (test 8g), create two tags with the same name (e.g., 'TestDupe') under different parent tags. Otherwise that test will be skipped. Let me know when done."

**Wait for user confirmation before proceeding to Phase 2.** If user created the duplicate tag, re-fetch tags via `get_all` and store the ambiguous name.

Once confirmed, tell them: "Running all tests now. I'll report results when done."

---

## Phase 2: Autonomous Testing

Run every test section below. For each test, record:
- **PASS**: Expected behavior observed
- **FAIL**: Unexpected behavior — note what happened
- **SKIP**: Test couldn't run (missing precondition)

After a test that modifies state, clean up if the task is reused later (e.g., rename back, remove tags).

### Section A — Fix Regressions

These verify that specific bugs from Phase 16 UAT are fixed.

#### Test 1: remove tags alone (no crash)
1. `actions: { tags: { add: [<tag-a>] } }` on T1
2. `actions: { tags: { remove: [<tag-a>] } }` on T1 — NO add in the call
3. PASS if: success, no crash, tag removed

#### Test 2a: note: null clears the note
1. `note: "hello"` on T2
2. `note: null` on T2
3. PASS if: success, no error (note becomes empty string internally)

#### Test 2b: note: "" (empty string) clears the note
1. `note: "some text"` on T2
2. `note: ""` on T2
3. `get_task` T2 and verify note is empty
4. PASS if: success, note cleared (empty string accepted as a way to clear notes)

#### Test 3a: Clean error — replace + add
1. `actions: { tags: { replace: [<tag-a>], add: [<tag-b>] } }` on T3
2. PASS if: error message does NOT contain "type=", "pydantic", or "input_value"

#### Test 3b: Clean error — move multi-key
1. `actions: { move: {"beginning": "x", "ending": "y"} }` on T3
2. PASS if: error message does NOT contain "type=", "pydantic", "input_value", or "_Unset"

#### Test 4a: No-op warning — add duplicate tag
1. `actions: { tags: { add: [<tag-a>] } }` on T4
2. `actions: { tags: { add: [<tag-a>] } }` again on T4
3. PASS if: second call returns success with a warning about tag already on task

#### Test 4b: No-op warning — remove absent tag
1. `actions: { tags: { remove: [<tag-b>] } }` on T4 (T4 doesn't have tag-b)
2. PASS if: success with warning about tag not on task

#### Test 4c: No-op warning — empty edit
1. Edit T4 with only `id`, no other fields
2. PASS if: success with warning about no changes specified

#### Test 4d: No-op warning — same field value
1. `flagged: true` on T4
2. `flagged: true` again on T4
3. PASS if: second call returns warning about no changes detected

#### Test 4e: No-op warning — same name
1. `name: "T4-NoopWarnings"` on T4 (its current name)
2. PASS if: warning about no changes detected

#### Test 4f: No-op warning — same date
1. `dueDate: "2026-04-01T12:00:00+01:00"` on T4
2. `dueDate: "2026-04-01T12:00:00+01:00"` again on T4
3. PASS if: second call returns warning about no changes detected
4. Clean up: `dueDate: null` on T4

#### Test 4g: No-op warning — same estimatedMinutes
1. `estimatedMinutes: 15` on T4
2. `estimatedMinutes: 15` again on T4
3. PASS if: second call returns warning about no changes detected
4. Clean up: `estimatedMinutes: null` on T4

#### Test 4h: No-op warning — same deferDate
1. `deferDate: "2026-04-01T09:00:00+01:00"` on T4
2. `deferDate: "2026-04-01T09:00:00+01:00"` again on T4
3. PASS if: second call returns warning about no changes detected
4. Clean up: `deferDate: null` on T4

#### Test 4i: No-op warning — same plannedDate
1. `plannedDate: "2026-04-01T10:00:00+01:00"` on T4
2. `plannedDate: "2026-04-01T10:00:00+01:00"` again on T4
3. PASS if: second call returns warning about no changes detected
4. Clean up: `plannedDate: null` on T4

#### Test 4j: No-op warning — note null on already-empty note
1. Ensure T4 has no note (it shouldn't at this point, but `note: null` first if needed)
2. `note: null` on T4
3. PASS if: warning about no changes detected (note is already empty)

#### Test 5a: Status warning — completed task
1. `flagged: true` on T5 (which user completed in Step 1.3)
2. PASS if: success with warning mentioning "completed"

#### Test 5b: Status warning — dropped task
1. `name: "T6a-Dropped"` on T6a (which user dropped in Step 1.3)
2. PASS if: success with warning mentioning "dropped"

### Section B — Field Editing

#### Test 7a: Patch semantics
1. Set `name: "T7-Updated", flagged: true, note: "test note", estimatedMinutes: 30` on T7
2. Edit only `flagged: false` on T7
3. `get_task` T7 and verify: name still "T7-Updated", note still "test note", estimatedMinutes still 30
4. PASS if: untouched fields preserved

#### Test 7b: Date fields set + clear
1. `dueDate: "2026-03-15T17:00:00+01:00", deferDate: "2026-03-10T09:00:00+01:00"` on T7
2. Verify success
3. `dueDate: null, deferDate: null` on T7
4. PASS if: both set and clear succeed

#### Test 7c: estimatedMinutes set + clear
1. `estimatedMinutes: 45` on T7
2. `estimatedMinutes: null` on T7
3. PASS if: both succeed

#### Test 7d: Name change
1. `name: "T7-Renamed"` on T7
2. Verify response shows new name
3. `name: "T7-FieldEditing"` (rename back)
4. PASS if: both succeed, response reflects new name

#### Test 7e: Multi-field single call
1. `flagged: true, note: "multi", estimatedMinutes: 60, dueDate: "2026-03-20T12:00:00+01:00"` on T7
2. `get_task` to verify all four fields
3. PASS if: all four applied in one call

#### Test 7f: plannedDate set + clear
1. `plannedDate: "2026-03-12T10:00:00+01:00"` on T7
2. Verify success
3. `plannedDate: null` on T7
4. PASS if: both set and clear succeed

### Section C — Tag Operations

Use tag IDs from Step 1.1. Call them tag-a, tag-b, tag-c below.

#### Test 8a: Replace tags
1. `actions: { tags: { replace: [<tag-a>, <tag-b>] } }` on T8
2. `get_task` to verify tag-a and tag-b are present
3. PASS if: success, both tags confirmed via get_task

#### Test 8b: Replace with different
1. `actions: { tags: { replace: [<tag-c>] } }` on T8
2. `get_task` to verify only tag-c remains
3. PASS if: tag-a and tag-b gone, only tag-c

#### Test 8c: Clear all tags
1. `actions: { tags: { replace: [] } }` on T8
2. PASS if: success, task has no tags

#### Test 8d: Add incremental
1. `actions: { tags: { add: [<tag-a>] } }` on T8
2. `actions: { tags: { add: [<tag-b>] } }` on T8
3. `get_task` to verify both tag-a and tag-b are present
4. PASS if: both succeed, both tags confirmed via get_task

#### Test 8e: Remove selective
1. `actions: { tags: { remove: [<tag-a>] } }` on T8
2. `get_task` to verify tag-a is gone and tag-b remains
3. PASS if: success, correct tags confirmed via get_task

#### Test 8f: Mixed ID and name
1. `actions: { tags: { add: [<tag-a-id>, <tag-c-name>] } }` on T8 (one by ID, one by name)
2. PASS if: both resolved and added

#### Test 8g: Ambiguous tag name
1. Use the ambiguous tag name found in Step 1.1, or the one the user created in Step 1.3
2. `actions: { tags: { add: ["<ambiguous-name>"] } }` on T8
3. PASS if: error mentioning "ambiguous" with multiple IDs
4. SKIP if: no ambiguous tag exists (user declined in Step 1.3)

#### Test 8h: add + remove combo
1. Clean T8 tags first, then `actions: { tags: { add: [<tag-b>] } }`
2. `actions: { tags: { add: [<tag-a>], remove: [<tag-b>] } }` on T8
3. `get_task` to verify tag-a present and tag-b gone
4. PASS if: success, correct tags confirmed via get_task

#### Test 8i: Multi-tag remove
1. Ensure T8 has tag-a and tag-b (add both if needed, one at a time)
2. `actions: { tags: { remove: [<tag-a>, <tag-b>] } }` on T8 (both in one call)
3. `get_task` to verify both tags are gone
4. PASS if: success, both tags removed in a single call

### Section D — Movement

#### Test 9a: All 5 move modes
Run these sequentially on T6:
1. `actions: { move: {"after": "<T7-id>"} }` — PASS if success
2. `actions: { move: {"before": "<T7-id>"} }` — PASS if success
3. `actions: { move: {"beginning": "<UAT-id>"} }` — PASS if success
4. `actions: { move: {"ending": "<UAT-id>"} }` — PASS if success
5. `actions: { move: {"ending": null} }` — PASS if success (moves to inbox)
6. `actions: { move: {"beginning": "<UAT-id>"} }` — move back (restore)
7. PASS if: all 6 calls succeed

#### Test 9b: Move carries children
1. `actions: { move: {"ending": null} }` on T6 (to inbox)
2. `get_task` T6, verify `hasChildren: true`
3. `actions: { move: {"beginning": "<UAT-id>"} }` (move back)
4. PASS if: children preserved

#### Test 9c: Cross-level move
1. `actions: { move: {"ending": "<UAT-id>"} }` on T6b1 (grandchild -> direct child of root)
2. Verify success
3. `actions: { move: {"ending": "<T6b-id>"} }` on T6b1 (move back)
4. PASS if: both succeed

#### Test 9d: Circular reference detection (3 cases)
Run each INDIVIDUALLY (they will error):
1. Move UAT-Regression inside T6: `actions: { move: {"beginning": "<T6-id>"} }` on UAT-Regression
   - PASS if: error about circular reference
2. Move T6 inside T6b1 (multi-level): `actions: { move: {"beginning": "<T6b1-id>"} }` on T6
   - PASS if: error about circular reference
3. Move T6 inside itself: `actions: { move: {"beginning": "<T6-id>"} }` on T6
   - PASS if: error about circular reference

#### Test 9e: Move + edit combo
1. `name: "T6-Moved", actions: { move: {"ending": "<UAT-id>"} }` on T6
2. PASS if: success, name changed AND movement applied
3. Restore: `name: "T6-Movement"` on T6

#### Test 9f: Tags survive movement
1. `actions: { tags: { add: [<tag-a>] } }` on T6
2. `actions: { move: {"ending": null} }` on T6 (move to inbox)
3. `get_task` T6 and verify tag-a is still present
4. `actions: { move: {"beginning": "<UAT-id>"} }` on T6 (move back)
5. Clean up: `actions: { tags: { remove: [<tag-a>] } }` on T6
6. PASS if: tag preserved through move

#### Test 9g: No-op move — same position
1. Ensure T6 is the last child of UAT-Regression (it should be after previous tests restored it)
2. `actions: { move: {"ending": "<UAT-id>"} }` on T6 (already the last child)
3. PASS if: success with warning about no change in position (task is already there)

### Section E — Error Handling

Run each INDIVIDUALLY (they will error):

#### Test 10a: Nonexistent task ID
1. `edit_tasks` with `id: "nonexistent-id-12345", name: "nope"`
2. PASS if: clean error mentioning "not found"

#### Test 10b: Empty name
1. `name: ""` on T9
2. PASS if: error about name cannot be empty

#### Test 10c: Nonexistent tag
1. `actions: { tags: { add: ["definitely-not-a-real-tag-xyz"] } }` on T9
2. PASS if: error about tag not found

#### Test 10d: Nonexistent move target
1. `actions: { move: {"after": "nonexistent-id-12345"} }` on T9
2. PASS if: error about task/anchor not found

### Section F — Combinations & Edge Cases

#### Test 11a: add duplicate + remove absent warnings
1. Ensure T1 has tag-a (re-add if needed)
2. `actions: { tags: { add: [<tag-a>], remove: [<tag-b>] } }` on T1
3. PASS if: success with warnings for BOTH (duplicate add AND absent remove)

#### Test 11b: note null + field change
1. `note: "will be cleared", flagged: false` on T2
2. `note: null, flagged: true` on T2
3. PASS if: success, both applied, no error

#### Test 11c: Stacked warnings (no-op + completed)
1. `flagged: true` on T5 (already completed, already flagged from Test 5a)
2. PASS if: TWO warnings — one about "completed", one about "no changes"

#### Test 11d: Multi-task batch (known limitation)
1. Send 3 items in one `edit_tasks` call
2. PASS if: error about 1-item limit (expected limitation, confirms guard works)

#### Test 11e: Edit + move in same call
1. `flagged: true, actions: { move: {"ending": "<UAT-id>"} }` on T9
2. PASS if: success, both applied

### Section G — Lifecycle

These tests verify the `actions.lifecycle` field for completing and dropping tasks.

#### Test 12a: Complete a task
1. `actions: { lifecycle: "complete" }` on T10-LifecycleA
2. PASS if: success, `get_task` shows `availability: "completed"`

#### Test 12b: Drop a task
1. `actions: { lifecycle: "drop" }` on T10-LifecycleB
2. PASS if: success, `get_task` shows `availability: "dropped"`

#### Test 12c: No-op complete
1. `actions: { lifecycle: "complete" }` on T10-LifecycleA (already completed from 12a)
2. PASS if: success with warning about "already complete"

#### Test 12d: No-op drop
1. `actions: { lifecycle: "drop" }` on T10-LifecycleB (already dropped from 12b)
2. PASS if: success with warning about "already dropped"

#### Test 12e: Cross-state (complete a dropped task)
1. `actions: { lifecycle: "complete" }` on T6a-Child1 (dropped in Step 1.3)
2. PASS if: success with warning about prior state (was dropped)

#### Test 12f: Lifecycle + field edit
1. `name: "T10-Lifecycle-Renamed", actions: { lifecycle: "complete" }` on T10-LifecycleB (currently dropped)
2. PASS if: both applied — name changed AND lifecycle action executed

#### Test 12g: Invalid lifecycle
1. `actions: { lifecycle: "reopen" }` on T10-LifecycleA
2. PASS if: clean error (no Pydantic internals like "type=", "input_value", "pydantic")

#### Test 12h: Repeating task lifecycle (SKIP)
SKIP unless the user has a repeating test task available. Repeating tasks have special lifecycle behavior (completing creates next occurrence). This test requires manual setup that goes beyond the standard UAT regression scope.

---

## Phase 3: Report

After all tests complete, output TWO clearly separated sections. Each section MUST be inside a markdown code block (triple backticks) so the user can easily copy-paste them independently.

### Section 1: UAT Report (inside a code block)

Output the entire UAT report inside a single code block. The table must include a "Description" column that briefly explains what each test verifies — the test name alone is not enough for someone unfamiliar with the codebase.

Every test gets its own row (no grouping like "8a-8h"). Use this format:

````
```
## UAT Regression Results — edit_tasks

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1 | remove tags alone | Calling actions.tags.remove without add doesn't crash the server | PASS/FAIL |
| 2a | note: null | Setting note to null clears the note without error | PASS/FAIL |
| 2b | note: "" | Setting note to empty string also clears the note | PASS/FAIL |
| 3a | Clean error: replace + add | Using replace and add together in actions.tags returns a clean error, not Pydantic internals | PASS/FAIL |
| 3b | Clean error: move multi-key | Providing multiple keys in actions.move returns a clean error, not Pydantic internals or _Unset | PASS/FAIL |
| 4a | No-op: add duplicate tag | Adding a tag that's already on the task returns a warning | PASS/FAIL |
| 4b | No-op: remove absent tag | Removing a tag that's not on the task returns a warning | PASS/FAIL |
| 4c | No-op: empty edit | Sending only an ID with no fields returns a "no changes specified" warning | PASS/FAIL |
| 4d | No-op: same flagged | Setting flagged to its current value returns a "no changes detected" warning | PASS/FAIL |
| 4e | No-op: same name | Setting name to its current value returns a "no changes detected" warning | PASS/FAIL |
| 4f | No-op: same dueDate | Setting dueDate to the same value (possibly different timezone repr) returns a warning | PASS/FAIL |
| 4g | No-op: same estimatedMinutes | Setting estimatedMinutes to its current value returns a warning | PASS/FAIL |
| 4h | No-op: same deferDate | Setting deferDate to the same value returns a warning | PASS/FAIL |
| 4i | No-op: same plannedDate | Setting plannedDate to the same value returns a warning | PASS/FAIL |
| 4j | No-op: note null on empty | Setting note to null when note is already empty returns a warning | PASS/FAIL |
| 5a | Status: completed task | Editing a completed task succeeds but returns a warning mentioning "completed" | PASS/FAIL |
| 5b | Status: dropped task | Editing a dropped task succeeds but returns a warning mentioning "dropped" | PASS/FAIL |
| 7a | Patch semantics | Editing one field preserves all other fields (name, note, estimatedMinutes unchanged) | PASS/FAIL |
| 7b | Date set + clear | Setting dueDate and deferDate, then clearing both with null | PASS/FAIL |
| 7c | estimatedMinutes set + clear | Setting estimatedMinutes, then clearing with null | PASS/FAIL |
| 7d | Name change | Renaming a task and verifying the response reflects the new name | PASS/FAIL |
| 7e | Multi-field single call | Setting flagged, note, estimatedMinutes, and dueDate in one call; all applied | PASS/FAIL |
| 7f | plannedDate set + clear | Setting plannedDate, then clearing with null | PASS/FAIL |
| 8a | Tags: replace | Replace all tags using actions.tags.replace; verify via get_task | PASS/FAIL |
| 8b | Tags: replace with different | Replace tags with a different set; verify old tags gone | PASS/FAIL |
| 8c | Tags: clear all | Set actions.tags.replace to [] to remove all tags | PASS/FAIL |
| 8d | Tags: add incremental | Add tags one at a time with actions.tags.add; verify via get_task | PASS/FAIL |
| 8e | Tags: remove selective | Remove one tag with actions.tags.remove; verify via get_task | PASS/FAIL |
| 8f | Tags: mixed ID and name | Add tags using a mix of tag IDs and tag names in one call | PASS/FAIL |
| 8g | Tags: ambiguous name | Adding a tag by name when multiple tags share that name returns an ambiguity error | PASS/FAIL/SKIP |
| 8h | Tags: add + remove combo | actions.tags.add and actions.tags.remove in the same call; verify via get_task | PASS/FAIL |
| 8i | Tags: multi-tag remove | Remove 2 tags in one call with actions.tags.remove; verify via get_task | PASS/FAIL |
| 9a | Move: all 5 modes | Test after, before, beginning, ending, and ending:null (inbox) movements | PASS/FAIL |
| 9b | Move: carries children | Moving a parent task preserves its children (hasChildren still true) | PASS/FAIL |
| 9c | Move: cross-level | Moving a grandchild to a different nesting level and back | PASS/FAIL |
| 9d | Move: circular ref (3 cases) | Parent into child, ancestor into descendant, self into self — all blocked | PASS/FAIL |
| 9e | Move: + edit combo | Renaming and moving a task in the same call; both applied | PASS/FAIL |
| 9f | Move: tags survive | Tags are preserved when a task is moved to a different location | PASS/FAIL |
| 9g | Move: no-op same position | Moving a task to its current position returns a no-op warning | PASS/FAIL |
| 10a | Error: nonexistent task | Editing a fake task ID returns "not found" | PASS/FAIL |
| 10b | Error: empty name | Setting name to "" returns a validation error | PASS/FAIL |
| 10c | Error: nonexistent tag | Adding a fake tag name returns "tag not found" | PASS/FAIL |
| 10d | Error: nonexistent move target | Moving to a fake anchor ID returns "anchor not found" | PASS/FAIL |
| 11a | Combo: dup add + absent remove | actions.tags.add duplicate + actions.tags.remove absent in one call; both warnings present | PASS/FAIL |
| 11b | Combo: note null + field | Clearing note and changing flagged in one call; both applied | PASS/FAIL |
| 11c | Combo: stacked warnings | Editing a completed task with no actual changes; TWO warnings (completed + no-op) | PASS/FAIL |
| 11d | Combo: batch limit | Sending 3 items returns the 1-item limit error (expected) | PASS/FAIL |
| 11e | Combo: edit + move | Changing flagged and moving in one call; both applied | PASS/FAIL |
| 12a | Lifecycle: complete | Completing a task via actions.lifecycle sets availability to "completed" | PASS/FAIL |
| 12b | Lifecycle: drop | Dropping a task via actions.lifecycle sets availability to "dropped" | PASS/FAIL |
| 12c | Lifecycle: no-op complete | Completing an already-completed task returns a warning | PASS/FAIL |
| 12d | Lifecycle: no-op drop | Dropping an already-dropped task returns a warning | PASS/FAIL |
| 12e | Lifecycle: cross-state | Completing a previously-dropped task succeeds with warning about prior state | PASS/FAIL |
| 12f | Lifecycle: + field edit | Combining lifecycle action with a name change; both applied | PASS/FAIL |
| 12g | Lifecycle: invalid value | Invalid lifecycle value ("reopen") returns clean error, no Pydantic internals | PASS/FAIL |
| 12h | Lifecycle: repeating task | Completing a repeating task creates next occurrence | SKIP |

**Total: X PASS, Y FAIL, Z SKIP**

### Failures
- (What happened vs what was expected, for each failure)

### Skipped Tests
- (Why they were skipped)

### Observations
- (Warning tone, error message quality, anything noteworthy)

Cleanup: Please manually delete UAT-Regression and all its children in OmniFocus when ready. (delete_tasks is not yet implemented.)
```
````

### Separator

After the UAT code block, output this visual separator (NOT inside any code block):

```
⠀
⠀
⠀
═══════════════════════════════════════════════════════════════
═══════════════════════════════════════════════════════════════
⠀
  ▲ UAT REPORT (above) — copy-paste to share with reviewer
⠀
  ▼ NICE-TO-HAVES (below) — internal improvement notes
⠀
═══════════════════════════════════════════════════════════════
═══════════════════════════════════════════════════════════════
⠀
⠀
⠀
```

### Section 2: Nice-to-Haves (inside a separate code block)

Output improvement suggestions in a SEPARATE code block. This is for the user's own consumption (not part of the UAT report they may forward).

````
```
## Nice-to-Haves

### Tool / Server Improvements
- (Bugs, error message quality, API design, missing validations, etc.)

### Skill / Test Coverage Improvements
- (Missing test cases, edge cases not covered, skill instructions that could be clearer, etc.)

### Other Observations
- (UX patterns, warning message tone, anything else noteworthy)
```
````

Only include items you actually observed during the run — don't pad with generic suggestions. If a section would be empty, omit it.

**IMPORTANT:** Do NOT repeat bugs or issues already captured in the UAT Failures section. The Nice-to-Haves are for observations that go beyond what the test suite covers — wording improvements, UX polish, missing test coverage, architectural suggestions, etc. If something already has a FAIL row in the UAT table, it belongs there, not here.
