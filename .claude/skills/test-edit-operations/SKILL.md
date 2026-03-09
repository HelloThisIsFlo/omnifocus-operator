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
- **Inbox move syntax.** To move a task to inbox, use `{"ending": null}` or `{"beginning": null}` — NOT `moveTo: null` (that means "don't move").
- **1-item limit.** `edit_tasks` currently accepts exactly 1 item per call. Batch tests should expect this limitation.

## Phase 1: Interactive Setup

### Step 1.1 — Discover Tags

Call `get_all` and extract the tags list. Pick 3 tags that:
- Have unique names (no ambiguity)
- Are simple/safe to add and remove

Store their IDs and names. Also identify one tag name that IS ambiguous (maps to multiple IDs) for the ambiguity test. If none are ambiguous, skip test 8g.

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
```

Create the parent first, then all level-1 children (can be parallel), then T6's children sequentially (T6b needs to exist before T6b1).

Store all IDs in a reference table — you'll need them for every subsequent step.

### Step 1.3 — User Interaction

Ask the user to perform these manual actions in OmniFocus:

1. **Complete** T5-StatusWarning (check it off)
2. **Drop** T6a-Child1 (right-click > Drop, or however they prefer)

Tell them: "Please complete T5-StatusWarning and drop T6a-Child1 in OmniFocus, then let me know when done."

**Wait for user confirmation before proceeding to Phase 2.**

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

#### Test 1: removeTags alone (no crash)
1. `addTags: [<tag-a>]` on T1
2. `removeTags: [<tag-a>]` on T1 — NO addTags in the call
3. PASS if: success, no crash, tag removed

#### Test 2: note: null clears the note
1. `note: "hello"` on T2
2. `note: null` on T2
3. PASS if: success, no error (note becomes empty string internally)

#### Test 3a: Clean error — tags + addTags
1. `tags: [<tag-a>], addTags: [<tag-b>]` on T3
2. PASS if: error message does NOT contain "type=", "pydantic", or "input_value"

#### Test 3b: Clean error — moveTo multi-key
1. `moveTo: {"beginning": "x", "ending": "y"}` on T3
2. PASS if: error message does NOT contain "type=", "pydantic", "input_value", or "_Unset"

#### Test 4a: No-op warning — addTags duplicate
1. `addTags: [<tag-a>]` on T4
2. `addTags: [<tag-a>]` again on T4
3. PASS if: second call returns success with a warning about tag already on task

#### Test 4b: No-op warning — removeTags absent
1. `removeTags: [<tag-b>]` on T4 (T4 doesn't have tag-b). Use `addTags: [], removeTags: [<tag-b>]` if removeTags-alone is broken.
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

#### Test 8a: Replace (tags field)
1. `tags: [<tag-a>, <tag-b>]` on T8
2. PASS if: success

#### Test 8b: Replace with different
1. `tags: [<tag-c>]` on T8
2. `get_task` to verify only tag-c remains
3. PASS if: tag-a and tag-b gone, only tag-c

#### Test 8c: Clear all tags
1. `tags: []` on T8
2. PASS if: success, task has no tags

#### Test 8d: Add incremental
1. `addTags: [<tag-a>]` on T8
2. `addTags: [<tag-b>]` on T8
3. PASS if: both succeed

#### Test 8e: Remove selective
1. `removeTags: [<tag-a>]` on T8
2. PASS if: success (also confirms Fix 1 works in this context)

#### Test 8f: Mixed ID and name
1. `addTags: [<tag-a-id>, <tag-c-name>]` on T8 (one by ID, one by name)
2. PASS if: both resolved and added

#### Test 8g: Ambiguous tag name
1. Check if any tag name maps to 2+ tag IDs in the database
2. If none found: ask the user to create two tags with the same name (e.g., create a tag named "TestDupe" under two different parent tags in OmniFocus), then re-fetch tags via `get_all`. If the user declines, SKIP.
3. `addTags: ["<ambiguous-name>"]` on T8
4. PASS if: error mentioning "ambiguous" with multiple IDs
5. SKIP if: user declined to create duplicate tags

#### Test 8h: add + remove combo
1. Clean T8 tags first, then `addTags: [<tag-b>]`
2. `addTags: [<tag-a>], removeTags: [<tag-b>]` on T8
3. PASS if: success, tag-a added, tag-b removed

### Section D — Movement

#### Test 9a: All 5 moveTo modes
Run these sequentially on T6:
1. `moveTo: {"after": "<T7-id>"}` — PASS if success
2. `moveTo: {"before": "<T7-id>"}` — PASS if success
3. `moveTo: {"beginning": "<UAT-id>"}` — PASS if success
4. `moveTo: {"ending": "<UAT-id>"}` — PASS if success
5. `moveTo: {"ending": null}` — PASS if success (moves to inbox)
6. `moveTo: {"beginning": "<UAT-id>"}` — move back (restore)
7. PASS if: all 6 calls succeed

#### Test 9b: Move carries children
1. `moveTo: {"ending": null}` on T6 (to inbox)
2. `get_task` T6, verify `hasChildren: true`
3. `moveTo: {"beginning": "<UAT-id>"}` (move back)
4. PASS if: children preserved

#### Test 9c: Cross-level move
1. `moveTo: {"ending": "<UAT-id>"}` on T6b1 (grandchild → direct child of root)
2. Verify success
3. `moveTo: {"ending": "<T6b-id>"}` on T6b1 (move back)
4. PASS if: both succeed

#### Test 9d: Circular reference detection (3 cases)
Run each INDIVIDUALLY (they will error):
1. Move UAT-Regression inside T6: `moveTo: {"beginning": "<T6-id>"}` on UAT-Regression
   - PASS if: error about circular reference
2. Move T6 inside T6b1 (multi-level): `moveTo: {"beginning": "<T6b1-id>"}` on T6
   - PASS if: error about circular reference
3. Move T6 inside itself: `moveTo: {"beginning": "<T6-id>"}` on T6
   - PASS if: error about circular reference

#### Test 9e: Move + edit combo
1. `name: "T6-Moved", moveTo: {"ending": "<UAT-id>"}` on T6
2. PASS if: success, name changed AND movement applied
3. Restore: `name: "T6-Movement"` on T6

#### Test 9f: Tags survive movement
1. `addTags: [<tag-a>]` on T6
2. `moveTo: {"ending": null}` on T6 (move to inbox)
3. `get_task` T6 and verify tag-a is still present
4. `moveTo: {"beginning": "<UAT-id>"}` on T6 (move back)
5. Clean up: `removeTags: [<tag-a>]` on T6
6. PASS if: tag preserved through move

### Section E — Error Handling

Run each INDIVIDUALLY (they will error):

#### Test 10a: Nonexistent task ID
1. `edit_tasks` with `id: "nonexistent-id-12345", name: "nope"`
2. PASS if: clean error mentioning "not found"

#### Test 10b: Empty name
1. `name: ""` on T9
2. PASS if: error about name cannot be empty

#### Test 10c: Nonexistent tag
1. `addTags: ["definitely-not-a-real-tag-xyz"]` on T9
2. PASS if: error about tag not found

#### Test 10d: Nonexistent moveTo target
1. `moveTo: {"after": "nonexistent-id-12345"}` on T9
2. PASS if: error about task/anchor not found

### Section F — Combinations & Edge Cases

#### Test 11a: addTags duplicate + removeTags warnings
1. Ensure T1 has tag-a (re-add if needed)
2. `addTags: [<tag-a>], removeTags: [<tag-b>]` on T1
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
1. `flagged: true, moveTo: {"ending": "<UAT-id>"}` on T9
2. PASS if: success, both applied

---

## Phase 3: Report

After all tests complete, present a summary table:

```
## UAT Regression Results — edit_tasks

| # | Category | Test | Result |
|---|----------|------|--------|
| 1 | Fix | removeTags alone | PASS/FAIL |
| 2 | Fix | note: null | PASS/FAIL |
| 3a | Fix | Clean error — tags + addTags | PASS/FAIL |
| 3b | Fix | Clean error — moveTo multi-key | PASS/FAIL |
| 4a | No-op | addTags duplicate | PASS/FAIL |
| 4b | No-op | removeTags absent | PASS/FAIL |
| 4c | No-op | empty edit | PASS/FAIL |
| 4d | No-op | same field value | PASS/FAIL |
| 4e | No-op | same name | PASS/FAIL |
| 4f | No-op | same date | PASS/FAIL |
| 4g | No-op | same estimatedMinutes | PASS/FAIL |
| 5a | Status | completed task | PASS/FAIL |
| 5b | Status | dropped task | PASS/FAIL |
| 7a | Field | patch semantics | PASS/FAIL |
| 7b | Field | date set + clear | PASS/FAIL |
| 7c | Field | estimatedMinutes set + clear | PASS/FAIL |
| 7d | Field | name change | PASS/FAIL |
| 7e | Field | multi-field single call | PASS/FAIL |
| 7f | Field | plannedDate set + clear | PASS/FAIL |
| 8a-8h | Tags | (8 tag operation tests) | PASS/FAIL |
| 9a | Move | all 5 moveTo modes | PASS/FAIL |
| 9b | Move | move carries children | PASS/FAIL |
| 9c | Move | cross-level move | PASS/FAIL |
| 9d | Move | circular reference (3 cases) | PASS/FAIL |
| 9e | Move | move + edit combo | PASS/FAIL |
| 9f | Move | tags survive movement | PASS/FAIL |
| 10a-d | Error | (4 error handling tests) | PASS/FAIL |
| 11a-e | Combo | (5 combination tests) | PASS/FAIL |
...
```

Below the table, list:
- **Failures**: What happened vs what was expected
- **Observations**: Any interesting behaviors noticed (warning tone inconsistencies, error message quality, etc.)
- **Skipped tests**: Why they were skipped

Then remind the user to manually delete UAT-Regression and all its children in OmniFocus when they're ready. (`delete_tasks` is not yet implemented — this step will be automated once it is.)

---

## Phase 4: Nice-to-Haves

After the UAT report, present a **separate** section with improvement suggestions. This is for the user's own consumption (not part of the UAT report they may forward).

Structure it as:

```
## Nice-to-Haves

### Tool / Server Improvements
- (Bugs, error message quality, API design, missing validations, etc.)

### Skill / Test Coverage Improvements
- (Missing test cases, edge cases not covered, skill instructions that could be clearer, etc.)

### Other Observations
- (UX patterns, warning message tone, anything else noteworthy)
```

Only include items you actually observed during the run — don't pad with generic suggestions. If a section would be empty, omit it.
