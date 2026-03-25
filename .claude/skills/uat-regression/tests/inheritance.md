# Inheritance Test Suite

Tests effective field inheritance — `effectiveDueDate`, `effectiveDeferDate`, `effectivePlannedDate`, `effectiveFlagged` — from parent projects through task chains, including multi-level nesting, move-induced changes, and own-value override behavior.

## Conventions

- **Project-based.** Unlike other suites, this one creates tasks under real projects (not inbox). The runner auto-discovers suitable projects via `get_all`.
- **1-item limit.** `edit_tasks` currently accepts exactly 1 item per call.
- **Read-back required.** Every test uses `get_task` to verify effective fields — inheritance is only observable through reads.

## Setup

### Step 1 — Discover Projects

Call `get_all` and scan the projects list. Look for `🧪 GM-` prefixed projects first — these are the existing golden master test infrastructure.

Find two projects:
- **Dated project**: has `dueDate`, `deferDate`, `plannedDate`, and `flagged=true` — all four required
- **Undated project**: `dueDate` null, `deferDate` null, `plannedDate` null, `flagged` false

Present what you found to the user in a table (project name, ID, and field values) and ask for confirmation before proceeding.

If the best candidate for the dated project is missing any required field, tell the user exactly which field(s) to set and wait for them to fix it.

### Step 2 — Verify Project Fields

Call `get_project` on both selected IDs (can be parallel) to confirm with fresh data. Store the dated project's `dueDate`, `deferDate`, `plannedDate` values — these are the expected inherited values for all assertions.

Verify:
- Dated project: `dueDate` is set, `deferDate` is set, `plannedDate` is set, `flagged` is true
- Undated project: `dueDate` is null, `deferDate` is null, `plannedDate` is null, `flagged` is false

If any precondition fails, tell the user which field is wrong and wait for them to fix it.

### Step 3 — Create Test Hierarchy

Create this structure using `add_tasks`:

```
Tasks under dated-project:
  T1-InheritDirect
  T2-ChainParent
    +-- T2a-ChainChild
  T3-L1
    +-- T3a-L2
        +-- T3b-L3
  T4-MoveAway
  T6-OwnOverride
  T7-ChainMoveParent
    +-- T7a-ChainMoveChild

Task in inbox (no parent):
  T5-MoveIn
```

Creation order:
1. T1, T2, T3, T4, T5, T6, T7 (can be parallel — T1/T2/T3/T4/T6/T7 under dated-project, T5 in inbox)
2. T2a under T2, T3a under T3 (can be parallel, need parents from step 1)
3. T3b under T3a (needs T3a from step 2)

Store all IDs.

Then tell the user: "Running all tests now. I'll report results when done."

## Tests

### 1. Direct Inheritance

#### Test 1: Direct inheritance (L1)
1. `get_task` on T1-InheritDirect
2. PASS if ALL of:
   - `effectiveDueDate` matches dated-project's dueDate
   - `effectiveDeferDate` matches dated-project's deferDate
   - `effectivePlannedDate` matches dated-project's plannedDate
   - `effectiveFlagged` = true
   - Task's own `dueDate` = null
   - Task's own `deferDate` = null
   - Task's own `plannedDate` = null
   - Task's own `flagged` = false

### 2. Chain Inheritance

#### Test 2: Inheritance through task chain (L2)
1. `get_task` on T2a-ChainChild
2. PASS if ALL of:
   - `effectiveDueDate` matches dated-project's dueDate
   - `effectiveDeferDate` matches dated-project's deferDate
   - `effectivePlannedDate` matches dated-project's plannedDate
   - `effectiveFlagged` = true
   - Task's own `flagged` = false

### 3. Deep Nesting

#### Test 3: Deep nesting (L3)
1. `get_task` on T3b-L3
2. PASS if ALL of:
   - `effectiveDueDate` matches dated-project's dueDate
   - `effectiveDeferDate` matches dated-project's deferDate
   - `effectivePlannedDate` matches dated-project's plannedDate
   - `effectiveFlagged` = true
   - Task's own `dueDate` = null
   - Task's own `deferDate` = null
   - Task's own `plannedDate` = null
   - Task's own `flagged` = false

### 4. Move Away — Clear Inheritance

#### Test 4: Clearing after move to undated project
1. `get_task` T4-MoveAway — sanity check: confirm effective fields are inherited (effectiveDueDate matches dated-project's)
2. `edit_tasks` on T4: `actions: { move: { "ending": "<undated-project-id>" } }`
3. `get_task` T4-MoveAway
4. PASS if ALL of:
   - `effectiveDueDate` = null
   - `effectiveDeferDate` = null
   - `effectivePlannedDate` = null
   - `effectiveFlagged` = false

### 5. Move In — Acquire Inheritance

#### Test 5: Move INTO dated project acquires inheritance
1. `get_task` T5-MoveIn — sanity check: confirm `effectiveDueDate` = null (task is in inbox)
2. `edit_tasks` on T5: `actions: { move: { "ending": "<dated-project-id>" } }`
3. `get_task` T5-MoveIn
4. PASS if ALL of:
   - `effectiveDueDate` matches dated-project's dueDate
   - `effectiveDeferDate` matches dated-project's deferDate
   - `effectivePlannedDate` matches dated-project's plannedDate
   - `effectiveFlagged` = true

### 6. Own Value Overrides Inherited

#### Test 6: Own dueDate takes priority
1. `edit_tasks` on T6-OwnOverride: `dueDate: "2026-06-15T12:00:00+01:00"`
2. `get_task` T6-OwnOverride
3. PASS if ALL of:
   - `effectiveDueDate` matches "2026-06-15T12:00:00+01:00" (task's own, NOT project's)
   - `dueDate` = "2026-06-15T12:00:00+01:00" (own value is set)
   - `effectiveDeferDate` still matches dated-project's deferDate (unchanged — still inherited)
   - `effectiveFlagged` = true (still inherited)

### 7. Clear Own Value — Reverts to Inherited

#### Test 7: Clear own dueDate reverts to project's
1. `edit_tasks` on T6-OwnOverride: `dueDate: null`
2. `get_task` T6-OwnOverride
3. PASS if ALL of:
   - `effectiveDueDate` matches dated-project's dueDate (reverted to inherited)
   - `dueDate` = null (own value cleared)

### 8. Chain Move — Children Inherit

#### Test 8: Move parent+child out of dated project; child's effective fields clear
1. `get_task` T7a-ChainMoveChild — sanity check: confirm effective fields are inherited
2. `edit_tasks` on T7-ChainMoveParent: `actions: { move: { "ending": "<undated-project-id>" } }`
3. `get_task` T7a-ChainMoveChild
4. PASS if ALL of:
   - `effectiveDueDate` = null
   - `effectiveDeferDate` = null
   - `effectivePlannedDate` = null
   - `effectiveFlagged` = false

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1 | Direct inheritance (L1) | Task under dated project inherits all 4 effective fields; own fields null/false | |
| 2 | Chain inheritance (L2) | Grandchild inherits through parent task within dated project | |
| 3 | Deep nesting (L3) | 3 levels deep; all 4 effective fields inherited; own fields null/false | |
| 4 | Move away: clear | Move from dated→undated project; all effective fields clear | |
| 5 | Move in: acquire | Move from inbox→dated project; all effective fields appear | |
| 6 | Own overrides inherited | Task's own dueDate takes priority; other fields still inherited | |
| 7 | Clear own: reverts | Clear own dueDate; effectiveDueDate reverts to project's | |
| 8 | Chain move: children | Move parent to undated project; child's effective fields also clear | |
