# Validation & Error Formatting Test Suite

Tests that validation errors across all tools produce clean, agent-friendly messages — no Pydantic internals, correct field casing, proper "Task N:" prefixing. Covers `add_tasks`, `edit_tasks`, and all v1.3 list tools.

## Conventions

- **Error format checks on every test.** Every PASS criteria includes: error message must NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`. This is the suite's raison d'etre.
- **Run each test INDIVIDUALLY.** Claude Code cancels sibling MCP calls when one errors. Never batch error-expecting calls.
- **Minimal setup.** Most tests are error-path — they don't need pre-existing tasks. One temp task is created for edit_tasks tests that need a valid ID.
- **No overlap with domain suites.** Task-creation, edit-operations, move-operations, and lifecycle suites already test domain logic (tag mutual exclusion, circular moves, etc.). This suite tests the *formatting* of errors that cross tool boundaries or exercise the middleware layer specifically.

## Setup

### Task Hierarchy

Create one task in the inbox using `add_tasks`:

```
UAT-ValidationErrors (inbox parent)
+-- VE-TempTask
```

Create parent first, then child. Store the child's ID as **temp-id** — used by edit_tasks tests.

### Manual Actions

None.

Then tell the user: "Setup complete. Running all tests now. I'll report results when done."

## Tests

### 1. add_tasks Validation

Run each test INDIVIDUALLY (will error):

#### Test 1a: Unknown field
1. `add_tasks` with `items: [{ name: "VE-1a", priority: "high" }]`
2. PASS if: error mentions "Unknown field" and "priority"; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 1b: Invalid date format (no timezone)
1. `add_tasks` with `items: [{ name: "VE-1b", dueDate: "2026-03-15" }]`
2. PASS if: error about date/datetime format; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 1c: Empty items array
1. `add_tasks` with `items: []`
2. PASS if: error about item count or empty array; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 1d: Missing name
1. `add_tasks` with `items: [{ flagged: true }]`
2. PASS if: error about name being required; message uses "Task 1:" prefix (1-indexed); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

### 2. edit_tasks Validation

Run each test INDIVIDUALLY (will error):

#### Test 2a: Unknown field
1. `edit_tasks` with `items: [{ id: "<temp-id>", bogusField: true }]`
2. PASS if: error mentions "Unknown field" and "bogusField"; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 2b: Invalid lifecycle value
1. `edit_tasks` with `items: [{ id: "<temp-id>", actions: { lifecycle: "restart" } }]`
2. PASS if: error mentions "must be 'complete' or 'drop'" (or similar); does NOT contain raw enum list, `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 2c: Empty name
1. `edit_tasks` with `items: [{ id: "<temp-id>", name: "" }]`
2. PASS if: error about name being empty; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 2d: Batch limit
1. `edit_tasks` with `items: [{ id: "<temp-id>", name: "A" }, { id: "<temp-id>", name: "B" }]`
2. PASS if: error about "currently accepts exactly 1 item, got 2"; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

### 3. List Tool Validation

Run each test INDIVIDUALLY (will error):

#### Test 3a: Offset without limit (list_tasks)
1. `list_tasks` with `offset: 5`
2. PASS if: error mentions "offset requires limit"; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 3b: Invalid availability value (list_tasks)
1. `list_tasks` with `availability: ["INVALID"]`
2. PASS if: error about invalid availability value; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 3c: Invalid review_due_within (list_projects)
1. `list_projects` with `reviewDueWithin: "abc"`
2. PASS if: error mentions valid formats (e.g., "1w", "2m", "30d", "now"); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 3d: Unknown filter field (list_tasks)
1. `list_tasks` with `bogusFilter: true`
2. PASS if: error mentions "Unknown field" and "bogusFilter"; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 3e: Offset without limit (list_projects)
1. `list_projects` with `offset: 3`
2. PASS if: error mentions "offset requires limit"; message identical in spirit to test 3a (cross-tool consistency)

#### Test 3f: Unknown filter field (list_tags)
1. `list_tags` with `bogusFilter: true`
2. PASS if: error mentions "Unknown field"; confirms middleware catches validation errors on simple list tools too

### 4. Edge Cases

Run each test INDIVIDUALLY (will error):

#### Test 4a: Structural type mismatch
1. `add_tasks` with `items: "not an array"`
2. PASS if: error about expected type (list/array); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 4b: _Unset sentinel never visible
1. `edit_tasks` with `items: [{ id: "<temp-id>", flagged: "yes" }]`
2. PASS if: error about boolean type or invalid value; the string `_Unset` does NOT appear anywhere in the error message

#### Test 4c: camelCase field names in errors
1. `edit_tasks` with `items: [{ id: "<temp-id>", dueDate: "not-a-date", deferDate: "also-bad" }]`
2. PASS if: error references field names in camelCase (`dueDate`, `deferDate` — NOT `due_date`, `defer_date`); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | add_tasks: unknown field | Unknown field → clean "Unknown field" error | |
| 1b | add_tasks: invalid date | Date without timezone → clean format error | |
| 1c | add_tasks: empty items | Empty items array → clean error | |
| 1d | add_tasks: missing name | No name field → "Task 1:" prefixed error | |
| 2a | edit_tasks: unknown field | Unknown field → clean "Unknown field" error | |
| 2b | edit_tasks: invalid lifecycle | Invalid lifecycle → clean error, no enum internals | |
| 2c | edit_tasks: empty name | Empty string name → clean error | |
| 2d | edit_tasks: batch limit | 2 items → clean "exactly 1 item" error | |
| 3a | list_tasks: offset w/o limit | Offset without limit → "offset requires limit" | |
| 3b | list_tasks: invalid availability | Bad enum value → clean error | |
| 3c | list_projects: invalid review_due_within | Bad format → error with valid examples | |
| 3d | list_tasks: unknown filter | Unknown field → clean error | |
| 3e | list_projects: offset w/o limit | Cross-tool: same error as 3a | |
| 3f | list_tags: unknown filter | Cross-tool: middleware catches on simple list tools | |
| 4a | Structural type mismatch | String instead of array → clean error | |
| 4b | _Unset sentinel hidden | Invalid union type → no "_Unset" visible | |
| 4c | camelCase in errors | Bad dates → field names in camelCase, not snake_case | |
