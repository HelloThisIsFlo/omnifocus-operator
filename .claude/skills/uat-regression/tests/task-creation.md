# Task Creation Test Suite

Tests `add_tasks` — inbox creation, parent assignment, all fields, tag resolution, error handling, and batch constraints.

## Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **Timezone required.** Date fields need timezone info in ISO 8601 (e.g., `+01:00` or `Z`). Without it, Pydantic rejects the value.
- **Tags by ID.** Some tag names are ambiguous. Discover tags via `get_all` first, then use IDs where names might collide.
- **1-item limit.** `add_tasks` currently accepts exactly 1 item per call.

## Setup

### Step 1 — Discover Tags

Call `get_all` and extract the tags list. Pick 3 tags that:
- Have unique names (no ambiguity)
- Are simple/safe to use

Store their IDs and names as tag-a, tag-b, tag-c. Also check if any tag name maps to 2+ tag IDs (for ambiguity test). Store the ambiguous name if found.

### Step 2 — Create Test Parent

Create this structure in the inbox using `add_tasks`:

```
UAT-TaskCreation (parent)
```

Store the parent ID.

### Step 3 — Manual Actions

If no ambiguous tag name was found in Step 1, ask the user:
"If you'd like to test ambiguous tag handling (test 5c), create two tags with the same name (e.g., 'TestDupe') under different parent tags in OmniFocus. Otherwise that test will be skipped. Let me know when ready."

If the user created the duplicate tag, re-fetch tags via `get_all` and store the ambiguous name.

Wait for confirmation before proceeding. Then tell them: "Running all tests now. I'll report results when done."

## Tests

### 1. Basic Creation

#### Test 1a: Create basic inbox task
1. `add_tasks` with `name: "T1a-InboxTask"` (no parent)
2. `get_task` on the returned ID
3. PASS if: task exists, `inInbox: true` or parent is null

#### Test 1b: Create task with parent
1. `add_tasks` with `name: "T1b-ChildTask", parent: "<UAT-TaskCreation-id>"`
2. `get_task` on the returned ID
3. PASS if: parent type is "task" and parent id matches UAT-TaskCreation

#### Test 1c: Create task with all fields
1. `add_tasks` with:
   - `name: "T1c-FullTask"`
   - `parent: "<UAT-TaskCreation-id>"`
   - `tags: [<tag-a-name>]`
   - `dueDate: "2026-04-01T17:00:00+01:00"`
   - `deferDate: "2026-03-25T09:00:00+01:00"`
   - `plannedDate: "2026-03-28T10:00:00+01:00"`
   - `flagged: true`
   - `estimatedMinutes: 45`
   - `note: "Full field test"`
2. `get_task` on returned ID
3. PASS if: all fields match — name, parent, tag present, dates set, flagged true, estimatedMinutes 45, note present

### 2. Result Shape

#### Test 2: Result contains expected fields
1. `add_tasks` with `name: "T2-ResultShape"`
2. PASS if: result contains `success: true`, `id` (non-empty string), `name: "T2-ResultShape"`

### 3. Tag Resolution

#### Test 3a: Tag by name (case-insensitive)
1. `add_tasks` with `name: "T3a-TagByName", tags: [<tag-b-name-in-different-case>]`
   (e.g., if tag is "Work", use "work" or "WORK")
2. PASS if: success, tag resolved correctly

#### Test 3b: Tag by ID
1. `add_tasks` with `name: "T3b-TagById", tags: [<tag-c-id>]`
2. PASS if: success, tag resolved by ID

#### Test 3c: Multiple tags
1. `add_tasks` with `name: "T3c-MultiTag", tags: [<tag-a-name>, <tag-b-name>]`
2. `get_task` on returned ID
3. PASS if: both tags present

### 4. Read-Back Verification

#### Test 4: Create → get_task round-trip
1. `add_tasks` with `name: "T4-Readback", parent: "<UAT-TaskCreation-id>", flagged: true, estimatedMinutes: 30, note: "round-trip test"`
2. `get_task` on returned ID
3. PASS if: name, parent, flagged, estimatedMinutes, and note all match what was sent

### 5. Error Handling

Run each INDIVIDUALLY (they will error):

#### Test 5a: Empty name
1. `add_tasks` with `name: ""`
2. PASS if: error about name cannot be empty

#### Test 5b: Whitespace-only name
1. `add_tasks` with `name: "   "`
2. PASS if: error about name cannot be empty/whitespace

#### Test 5c: Ambiguous tag
1. `add_tasks` with `name: "T5c-AmbigTag", tags: ["<ambiguous-tag-name>"]`
2. PASS if: error mentioning "ambiguous" with multiple IDs
3. SKIP if: no ambiguous tag exists

#### Test 5d: Nonexistent parent
1. `add_tasks` with `name: "T5d-BadParent", parent: "nonexistent-id-99999"`
2. PASS if: error about parent not found

#### Test 5e: Nonexistent tag
1. `add_tasks` with `name: "T5e-BadTag", tags: ["definitely-not-a-real-tag-xyz"]`
2. PASS if: error about tag not found

#### Test 5f: Batch limit
1. `add_tasks` with 2 items: `[{name: "T5f-A"}, {name: "T5f-B"}]`
2. PASS if: error about 1-item limit

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Create: basic inbox | Task created in inbox with name only | |
| 1b | Create: with parent | Task created under a parent task | |
| 1c | Create: all fields | All fields set; verified via get_task | |
| 2 | Create: result shape | Result has success, id, name | |
| 3a | Create: tag by name | Case-insensitive tag resolution | |
| 3b | Create: tag by ID | Tag resolved by ID fallback | |
| 3c | Create: multiple tags | Two tags in one create call | |
| 4 | Create → read-back | Round-trip: all fields match after get_task | |
| 5a | Error: empty name | Empty name returns validation error | |
| 5b | Error: whitespace name | Whitespace-only name returns validation error | |
| 5c | Error: ambiguous tag | Ambiguous tag name returns error with IDs | SKIP? |
| 5d | Error: bad parent | Nonexistent parent returns "not found" | |
| 5e | Error: bad tag | Nonexistent tag returns "not found" | |
| 5f | Error: batch limit | 2-item array returns 1-item limit error | |
