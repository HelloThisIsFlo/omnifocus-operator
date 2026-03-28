# Move Operations Test Suite

Tests task movement including all 5 move modes, cross-level moves, circular reference detection, completed/dropped task movement, cross-parent moves, and known same-parent limitations.

## Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **Tags by ID.** For test 1f, discover tags first via `get_all` and use IDs where the name might be ambiguous.
- **Inbox move syntax.** To move a task to inbox, use `{"actions": {"move": {"ending": null}}}` — NOT `actions: null` (that means "no actions").
- **1-item limit.** `edit_tasks` currently accepts exactly 1 item per call.

**Known issue — spurious "no changes" warning:** When a move action results in a no-op (e.g., same-parent move) AND no field edits are in the request, a spurious "No changes specified/detected" warning fires alongside the specific move warning. Document in the report's Observations section if encountered.

## Setup

### Task Hierarchy

Create this structure in the inbox using `add_tasks`:

```
UAT-MoveOps (parent)
+-- T1-MoveTarget
+-- T2-MoveChild
|   +-- T2a-Grandchild
+-- T3-CompletedMove
+-- T4-DroppedMove
+-- T5-CrossParent
+-- T6-SameParentA
+-- T7-SameParentB
+-- T8-Errors
```

Also create a second parent for cross-parent testing:

```
UAT-MoveOps-Alt (second parent, in inbox, no children)
```

Create parents first, then level-1 children (can be parallel), then T2a (needs T2 to exist first). Store all IDs.

### Automated Setup Actions

After creating all tasks, run these lifecycle actions:
1. `edit_tasks` on T3-CompletedMove: `actions: { lifecycle: "complete" }`
2. `edit_tasks` on T4-DroppedMove: `actions: { lifecycle: "drop" }`

Verify T3 shows `availability: "completed"` and T4 shows `availability: "dropped"` via `get_task`.

Then tell the user: "Setup complete. Running all tests now. I'll report results when done."

## Tests

### 1. Core Movement

#### Test 1a: All 5 move modes
Run sequentially on T1:
1. `actions: { move: {"after": "<T2-id>"} }` — PASS if success
2. `actions: { move: {"before": "<T2-id>"} }` — PASS if success
3. `actions: { move: {"beginning": "<UAT-id>"} }` — PASS if success
4. `actions: { move: {"ending": "<UAT-id>"} }` — PASS if success
5. `actions: { move: {"ending": null} }` — PASS if success (moves to inbox)
6. `get_task` T1 and verify `inInbox: true`
7. `actions: { move: {"beginning": "<UAT-id>"} }` — restore
8. `get_task` T1 and verify `inInbox: false`
9. PASS if: all move calls succeed, `inInbox` flips correctly (true after move to inbox, false after move to parent)

#### Test 1b: Move carries children
1. `actions: { move: {"ending": null} }` on T2 (to inbox)
2. `get_task` T2, verify `hasChildren: true` and `inInbox: true`
3. `actions: { move: {"beginning": "<UAT-id>"} }` (move back)
4. PASS if: children preserved, `hasChildren: true` confirmed

#### Test 1c: Cross-level move
1. `actions: { move: {"ending": "<UAT-id>"} }` on T2a (grandchild → direct child of root)
2. Verify success
3. `actions: { move: {"ending": "<T2-id>"} }` on T2a (move back)
4. PASS if: both succeed

#### Test 1d: Circular reference detection (3 cases)
Run each INDIVIDUALLY (they will error):
1. Move UAT-MoveOps inside T2: `actions: { move: {"beginning": "<T2-id>"} }` on UAT-MoveOps
   - PASS if: error about circular reference
2. Move T2 inside T2a (multi-level): `actions: { move: {"beginning": "<T2a-id>"} }` on T2
   - PASS if: error about circular reference
3. Move T2 inside itself: `actions: { move: {"beginning": "<T2-id>"} }` on T2
   - PASS if: error about circular reference

#### Test 1e: Move + edit combo
1. `name: "T1-Moved", actions: { move: {"ending": "<UAT-MoveOps-Alt-id>"} }` on T1
2. `get_task` T1 to verify name changed AND parent is now UAT-MoveOps-Alt
3. PASS if: both name and parent changed
4. Restore: `name: "T1-MoveTarget", actions: { move: {"ending": "<UAT-id>"} }` on T1

#### Test 1f: Tags survive movement
1. Discover tag IDs from `get_all` if not already available — pick one unambiguous tag
2. `actions: { tags: { add: [<tag>] } }` on T1
3. `actions: { move: {"ending": null} }` on T1 (move to inbox)
4. `get_task` T1 and verify tag is still present
5. `actions: { move: {"beginning": "<UAT-id>"} }` on T1 (move back)
6. Clean up: `actions: { tags: { remove: [<tag>] } }` on T1
7. PASS if: tag preserved through move

### 2. Error: Multi-Key Move

Run INDIVIDUALLY (will error):

#### Test 2: Clean error — move multi-key
1. `actions: { move: {"beginning": "x", "ending": "y"} }` on T8
2. PASS if: error message does NOT contain "type=", "pydantic", "input_value", or "_Unset"

### 3. Error: Nonexistent Target

Run INDIVIDUALLY (will error):

#### Test 3: Nonexistent move target
1. `actions: { move: {"after": "nonexistent-id-12345"} }` on T8
2. PASS if: error about task/anchor not found

### 4. Combo: Edit + Move

#### Test 4: Edit + move in same call
1. `flagged: true, actions: { move: {"ending": "<UAT-MoveOps-Alt-id>"} }` on T8
2. `get_task` T8 to verify flagged is true AND parent is now UAT-MoveOps-Alt
3. PASS if: both flagged and parent changed
4. Restore: `flagged: false, actions: { move: {"ending": "<UAT-id>"} }` on T8

### 5. Completed/Dropped Task Movement

#### Test 5a: Move completed task
1. `actions: { move: {"ending": "<UAT-MoveOps-Alt-id>"} }` on T3 (completed)
2. PASS if: success, task moved despite being completed
3. Restore: `actions: { move: {"ending": "<UAT-id>"} }` on T3

#### Test 5b: Move dropped task
1. `actions: { move: {"ending": "<UAT-MoveOps-Alt-id>"} }` on T4 (dropped)
2. PASS if: success, task moved despite being dropped
3. Restore: `actions: { move: {"ending": "<UAT-id>"} }` on T4

### 6. Anchor on Completed/Dropped Tasks

#### Test 6a: Anchor on completed task
1. `actions: { move: {"after": "<T3-id>"} }` on T1
2. PASS if: success, T1 positioned after the completed T3
3. Restore: `actions: { move: {"beginning": "<UAT-id>"} }` on T1

#### Test 6b: Anchor on dropped task
1. `actions: { move: {"after": "<T4-id>"} }` on T1
2. PASS if: success, T1 positioned after the dropped T4
3. Restore: `actions: { move: {"beginning": "<UAT-id>"} }` on T1

### 7. Cross-Parent Move

#### Test 7: Cross-parent move
1. `actions: { move: {"ending": "<UAT-MoveOps-Alt-id>"} }` on T5
2. `get_task` T5 to verify it's under UAT-MoveOps-Alt
3. Restore: `actions: { move: {"ending": "<UAT-id>"} }` on T5
4. PASS if: task successfully moved between different parents

### 8. Same-Parent Reposition (KNOWN BUG)

**Known limitation:** When a task is already a child of a parent, `beginning`/`ending` moves within that same parent do NOT reposition the task. The API returns success with a warning "Task is already a child of this parent" but the task stays in its original position. Workaround: use `before`/`after` with a specific sibling.

#### Test 8a: Same-parent beginning (known no-op)
1. `actions: { move: {"beginning": "<UAT-id>"} }` on T6 (already a child, not at beginning)
2. PASS if: success with warning about task already being a child
3. Note: task will NOT actually move to the beginning — this is the known bug

#### Test 8b: Same-parent ending (known no-op)
1. `actions: { move: {"ending": "<UAT-id>"} }` on T7 (already a child, not at ending)
2. PASS if: success with warning about task already being a child
3. Note: task will NOT actually move to the ending — this is the known bug

### Position Verification Trick

For tests that need order verification, assign `estimatedMinutes` = 1, 2, 3... to all siblings in expected order, then ask the user to confirm the numbers read 1, 2, 3... in OmniFocus. This compensates for the lack of sibling-order info in the API response.

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Move: all 5 modes | after, before, beginning, ending, inbox — all succeed; `inInbox` flips | |
| 1b | Move: carries children | Parent move preserves children; `hasChildren: true` confirmed | |
| 1c | Move: cross-level | Grandchild to direct child and back | |
| 1d | Move: circular ref (3) | Parent into child, ancestor into descendant, self — all blocked | |
| 1e | Move: + edit combo | Name change and move in same call | |
| 1f | Move: tags survive | Tags preserved through move | |
| 2 | Clean error: multi-key | Multiple keys in move returns clean error | |
| 3 | Error: nonexistent target | Fake anchor ID returns "not found" | |
| 4 | Combo: edit + move | Flagged change and move in same call | |
| 5a | Move: completed task | Moving a completed task succeeds | |
| 5b | Move: dropped task | Moving a dropped task succeeds | |
| 6a | Anchor: completed task | Using completed task as before/after anchor | |
| 6b | Anchor: dropped task | Using dropped task as before/after anchor | |
| 7 | Cross-parent move | Move task between different parent tasks | |
| 8a | Same-parent beginning | Known bug: beginning in same parent is no-op | |
| 8b | Same-parent ending | Known bug: ending in same parent is no-op | |
