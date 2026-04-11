---
suite: task-creation
display: Task Creation
test_count: 17

discovery:
  needs:
    - type: tag
      label: tag-a
      filters: [available, unambiguous]
    - type: tag
      label: tag-b
      filters: [available, unambiguous]
    - type: tag
      label: tag-c
      filters: [available, unambiguous]
  ambiguous:
    tags: 3

setup: |
  ### Tasks
  UAT-TaskCreation (inbox parent)

manual_actions:
  - "If no ambiguous tag name found in discovery, ask user to create two tags with the same name (e.g., 'TestDupe') under different parent tags for test 5c. Otherwise test 5c will be skipped."
---

# Task Creation Test Suite

Tests `add_tasks` — inbox creation, parent assignment, all fields, tag resolution, error handling, and batch constraints.

## Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **Timezone required.** Date fields need timezone info in ISO 8601 (e.g., `+01:00` or `Z`). Without it, Pydantic rejects the value.
- **Tags by ID.** Some tag names are ambiguous. Discover tags via `get_all` first, then use IDs where names might collide.
- **1-item limit.** `add_tasks` currently accepts exactly 1 item per call.

## Tests

### 1. Basic Creation

#### Test 1a: Create basic inbox task
1. `add_tasks` with `name: "T1a-InboxTask"` (no parent)
2. `get_task` on the returned ID
3. PASS if: task exists, `project: {"id": "$inbox", "name": "Inbox"}`

#### Test 1b: Create task with parent
1. `add_tasks` with `name: "T1b-ChildTask", parent: "<UAT-TaskCreation-id>"`
2. `get_task` on the returned ID
3. PASS if: `parent` is `{"task": {"id": "<UAT-id>", "name": "UAT-TaskCreation"}}`, `project` is `{"id": "$inbox", "name": "Inbox"}`

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
2. PASS if: result contains `success: true`, `id` (non-empty string), `name: "T2-ResultShape"`, enriched `parent` (tagged wrapper with `project` or `task` key), enriched `project` (`{id, name}` reference)

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

### 6. $inbox & System Locations

#### Test 6a: parent: "$inbox" creates in inbox
1. `add_tasks` with `name: "T6a-InboxExplicit", parent: "$inbox"`
2. `get_task` on returned ID
3. PASS if: task exists, `project: {"id": "$inbox", "name": "Inbox"}` — same behavior as omitting parent

#### Test 6b: parent: null — error
Run INDIVIDUALLY (will error):
1. `add_tasks` with `name: "T6b-NullParent", parent: null`
2. PASS if: error contains "parent cannot be null"

#### Test 6c: parent: "$trash" — reserved prefix error
Run INDIVIDUALLY (will error):
1. `add_tasks` with `name: "T6c-BadSystem", parent: "$trash"`
2. PASS if: error contains "'$trash' starts with '$' which is reserved for system locations" and mentions "$inbox" as valid

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Create: basic inbox | Task created in inbox; project is `{id: "$inbox", name: "Inbox"}` | |
| 1b | Create: with parent | Task created under parent; `parent` is tagged wrapper, `project` is enriched ref | |
| 1c | Create: all fields | All fields set; verified via get_task | |
| 2 | Create: result shape | Result has success, id, name, enriched parent (tagged wrapper), enriched project | |
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
| 6a | $inbox parent | `parent: "$inbox"` creates task in inbox, same as omitting parent | |
| 6b | Error: null parent | `parent: null` returns educational error about inbox syntax | |
| 6c | Error: system location | `parent: "$trash"` returns reserved prefix error listing valid locations | |
