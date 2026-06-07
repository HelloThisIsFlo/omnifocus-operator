---
suite: move-operations
display: Move Operations
test_count: 23

setup: |
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

  ### Post-Create

  1. `edit_tasks` on T3-CompletedMove: `actions: { lifecycle: "complete" }`
  2. `edit_tasks` on T4-DroppedMove: `actions: { lifecycle: "drop" }`

  ### Verify

  T3: availability=completed
  T4: availability=dropped
---

# Move Operations Test Suite

Tests task movement including all 5 move modes, cross-level moves, circular reference detection, completed/dropped task movement, cross-parent moves, and same-parent repositioning.

## Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **Tags by ID.** For test 1f, discover tags first via `get_all` and use IDs where the name might be ambiguous.
- **Inbox move syntax.** To move a task to inbox, use `$inbox` as the container — e.g., `{"actions": {"move": {"ending": "$inbox"}}}`. Setting `ending` or `beginning` to `null` is an error (use `"$inbox"` instead).
- **1-item limit.** `edit_tasks` currently accepts exactly 1 item per call.

**Regression note — same-parent repositioning:** `beginning`/`ending` moves within the same parent should reorder the task. They should NOT return "already a child" or "no changes" warnings for a valid same-parent reposition.

## Tests

### 1. Core Movement

#### Test 1a: All 5 move modes
Run sequentially on T1:
1. `actions: { move: {"after": "<T2-id>"} }` — PASS if success
2. `actions: { move: {"before": "<T2-id>"} }` — PASS if success
3. `actions: { move: {"beginning": "<UAT-id>"} }` — PASS if success
4. `actions: { move: {"ending": "<UAT-id>"} }` — PASS if success
5. `actions: { move: {"ending": "$inbox"} }` — PASS if success (moves to inbox)
6. `get_task` T1 and verify `project.id == "$inbox"`
7. `actions: { move: {"beginning": "<UAT-id>"} }` — restore
8. `get_task` T1 and verify `parent.task.id == "<UAT-id>"` and `project.id == "$inbox"` (task is nested under an inbox task)
9. PASS if: all move calls succeed, the direct parent flips from `$inbox` back to UAT-MoveOps, and `project.id` remains `"$inbox"` throughout the inbox hierarchy

#### Test 1b: Move carries children
1. `actions: { move: {"ending": "$inbox"} }` on T2 (to inbox)
2. `get_task` T2, verify `hasChildren: true` and `project.id == "$inbox"`
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
3. `actions: { move: {"ending": "$inbox"} }` on T1 (move to inbox)
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

### 8. Same-Parent Reposition

Regression coverage for the old same-parent no-op bug. When a task is already a child of the target parent, `beginning`/`ending` should reposition it within that parent, not warn that it is already a child.

#### Test 8a: Same-parent beginning
1. `get_task` T6; record its `order`
2. `actions: { move: {"beginning": "<UAT-id>"} }` on T6 (already a child, not at beginning)
3. `list_tasks` with `parent: "<UAT-id>"` and `include: ["hierarchy"]`
4. From the results, compare direct children only (`parent.task.id == "<UAT-id>"`)
5. PASS if: success, T6's `order` changed and T6 is now the first direct child under UAT-MoveOps, and no same-parent/no-change warning was returned

#### Test 8b: Same-parent ending
1. `get_task` T7; record its `order`
2. `actions: { move: {"ending": "<UAT-id>"} }` on T7 (already a child, not at ending)
3. `list_tasks` with `parent: "<UAT-id>"` and `include: ["hierarchy"]`
4. From the results, compare direct children only (`parent.task.id == "<UAT-id>"`)
5. PASS if: success, T7's `order` changed and T7 is now the last direct child under UAT-MoveOps, and no same-parent/no-change warning was returned

### 9. $inbox Move

#### Test 9a: beginning: "$inbox"
1. `actions: { move: {"beginning": "$inbox"} }` on T1
2. `get_task` T1 and verify `project.id == "$inbox"`
3. PASS if: task moved to inbox
4. Restore: `actions: { move: {"beginning": "<UAT-id>"} }` on T1

### 10. Null & $inbox Errors

Run each INDIVIDUALLY (they will error):

#### Test 10a: ending: null
1. `actions: { move: {"ending": null} }` on T8
2. PASS if: error contains "ending cannot be null" and mentions "$inbox"

#### Test 10b: beginning: null
1. `actions: { move: {"beginning": null} }` on T8
2. PASS if: error contains "beginning cannot be null" and mentions "$inbox"

#### Test 10c: before: null
1. `actions: { move: {"before": null} }` on T8
2. PASS if: error contains "before cannot be null" and mentions "task reference"

#### Test 10d: after: null
1. `actions: { move: {"after": null} }` on T8
2. PASS if: error contains "after cannot be null" and mentions "task reference"

#### Test 10e: before: "$inbox" — type mismatch
1. `actions: { move: {"before": "$inbox"} }` on T8
2. PASS if: error mentions "'$inbox' is a project" and suggests using "ending" or "beginning" instead

#### Test 10f: after: "$inbox" — type mismatch
1. `actions: { move: {"after": "$inbox"} }` on T8
2. PASS if: error mentions "'$inbox' is a project" and suggests using "ending" or "beginning" instead

### Position Verification Trick

For tests that need order verification, assign `estimatedMinutes` = 1, 2, 3... to all siblings in expected order, then ask the user to confirm the numbers read 1, 2, 3... in OmniFocus. This compensates for the lack of sibling-order info in the API response.

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Move: all 5 modes | after, before, beginning, ending, $inbox — all succeed; direct parent flips while inbox hierarchy stays in `$inbox` | |
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
| 8a | Same-parent beginning | `beginning` within same parent repositions to first child without stale no-op warning | |
| 8b | Same-parent ending | `ending` within same parent repositions to last child without stale no-op warning | |
| 9a | $inbox: beginning | `beginning: "$inbox"` moves task to inbox; `project.id == "$inbox"` | |
| 10a | Error: ending null | `ending: null` returns error mentioning $inbox | |
| 10b | Error: beginning null | `beginning: null` returns error mentioning $inbox | |
| 10c | Error: before null | `before: null` returns error about task references | |
| 10d | Error: after null | `after: null` returns error about task references | |
| 10e | Error: before $inbox | `before: "$inbox"` returns type-mismatch suggesting beginning/ending | |
| 10f | Error: after $inbox | `after: "$inbox"` returns type-mismatch suggesting beginning/ending | |
