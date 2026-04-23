---
suite: validation-errors
display: Validation & Errors
test_count: 42

setup: |
  ### Task Hierarchy

  Create one task in the inbox using `add_tasks`:

  ```
  UAT-ValidationErrors (inbox parent)
  +-- VE-TempTask
  ```

  Create parent first, then child. Store the child's ID as **temp-id** — used by edit_tasks tests.
---

# Validation & Error Formatting Test Suite

Tests that validation errors across all tools produce clean, agent-friendly messages — no Pydantic internals, correct field casing, proper "Task N:" prefixing. Covers `add_tasks`, `edit_tasks`, all v1.3 list tools, v1.3.1 null/system-location errors, v1.3.2 DateFilter validation, and v1.3.2 breaking change rejections.

## Conventions

- **Error format checks on every test.** Every PASS criteria includes: error message must NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`. This is the suite's raison d'etre.
- **Run each test INDIVIDUALLY.** Claude Code cancels sibling MCP calls when one errors. Never batch error-expecting calls.
- **Minimal setup.** Most tests are error-path — they don't need pre-existing tasks. One temp task is created for edit_tasks tests that need a valid ID.
- **No overlap with domain suites.** Task-creation, edit-operations, move-operations, and lifecycle suites already test domain logic (tag mutual exclusion, circular moves, etc.). This suite tests the *formatting* of errors that cross tool boundaries or exercise the middleware layer specifically.

## Tests

### 1. add_tasks Validation

Run each test INDIVIDUALLY (will error):

#### Test 1a: Unknown field
1. `add_tasks` with `items: [{ name: "VE-1a", priority: "high" }]`
2. PASS if: error mentions "Unknown field" and "priority"; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 1b: Invalid date format (unparseable)
1. `add_tasks` with `items: [{ name: "VE-1b", dueDate: "March 15, 2026" }]`
2. PASS if: error about invalid date format mentioning accepted formats (ISO date, ISO datetime, or datetime with timezone); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

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

#### Test 2d: Note action — append and replace both set
1. `edit_tasks` with `items: [{ id: "<temp-id>", actions: { note: { append: "foo", replace: "bar" } } }]`
2. PASS if: error mentions the two note operations are mutually exclusive (fluent from an agent's perspective — names both `append` and `replace` and explains only one may be set); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 2e: Note action — neither operation set
1. `edit_tasks` with `items: [{ id: "<temp-id>", actions: { note: {} } }]`
2. PASS if: error mentions the note action requires at least one operation (fluent; mentions `append` or `replace` as the valid operations); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

### 3. List Tool Validation

Run each test INDIVIDUALLY (will error):

#### Test 3a: Offset without limit (list_tasks)
1. `list_tasks` with `offset: 5`
2. PASS if: error mentions "offset requires limit"; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 3b: Invalid availability value (list_tasks)
1. `list_tasks` with `availability: ["INVALID"]`
2. PASS if: error about invalid availability value; valid values shown are `available`, `blocked`, `remaining`; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

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

### 5. v1.3.1 Filter Null/Empty Errors

Run each test INDIVIDUALLY (will error):

#### Test 5a: Null filter — string field (list_tasks)
1. `list_tasks` with `project: null`
2. PASS if: error contains "cannot be null" and mentions omitting the field; field name appears as `project` (not snake_case); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 5b: Null filter — cross-tool (list_projects)
1. `list_projects` with `folder: null`
2. PASS if: error contains "cannot be null" and mentions omitting the field; same shape as test 5a (cross-tool consistency); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 5c: Empty tags array
1. `list_tasks` with `tags: []`
2. PASS if: error contains "cannot be empty" and mentions omitting the field; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

### 6. v1.3.1 Write-Side Null Errors

Run each test INDIVIDUALLY (will error):

#### Test 6a: Null moveTo container
1. `edit_tasks` with `items: [{ id: "<temp-id>", moveTo: { ending: null } }]`
2. PASS if: error contains "cannot be null" and mentions `$inbox` as the way to move to inbox; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 6b: Null parent on add
1. `add_tasks` with `items: [{ name: "VE-6b", parent: null }]`
2. PASS if: error contains "cannot be null" and mentions omitting the field to create in inbox; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

### 7. v1.3.1 System Location Errors

Run each test INDIVIDUALLY (will error):

#### Test 7a: $inbox is not a real project
1. `get_project` with `projectId: "$inbox"`
2. PASS if: error explains that $inbox is not a real OmniFocus project and suggests `list_tasks` with `inInbox` instead; message is educational and actionable; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 7b: Reserved prefix — plausible system name
1. `add_tasks` with `items: [{ name: "VE-7b", parent: "$trash" }]`
2. PASS if: error mentions `$` is reserved for system locations and lists valid ones (should include `$inbox`); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 7c: Reserved prefix — arbitrary name
1. `add_tasks` with `items: [{ name: "VE-7c", parent: "$foo" }]`
2. PASS if: same error shape as 7b — confirms dynamic value interpolation is clean; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 7d: Reserved prefix — read-side (list_tasks)
1. `list_tasks` with `project: "$trash"`
2. PASS if: error mentions `$` is reserved for system locations; same shape as 7b/7c but triggered from a list tool (cross-context consistency); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

### 8. v1.3.2 DateFilter Validation

Run each test INDIVIDUALLY (will error):

#### Test 8a: DateFilter — invalid "this" unit
1. `list_tasks` with `due: {this: "2w"}`
2. PASS if: error mentions that `this` only accepts single calendar units (d, w, m, y) and does NOT accept count+unit; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 8b: DateFilter — zero/negative count
1. `list_tasks` with `due: {next: "0d"}`
2. PASS if: error mentions zero or negative count; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 8c: DateFilter — invalid duration unit
1. `list_tasks` with `due: {last: "3x"}`
2. PASS if: error mentions invalid unit `x` and lists valid units (d, w, m, y); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 8d: DateFilter — after > before ordering
1. `list_tasks` with `due: {after: "2026-03-15T12:00:00Z", before: "2026-03-10T12:00:00Z"}`
2. PASS if: error mentions 'after' must be before or equal to 'before' and shows the actual values; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 8e: DateFilter — mixed shorthand and absolute
1. `list_tasks` with `due: {this: "w", after: "2026-03-01T00:00:00Z"}`
2. PASS if: error mentions "Unknown field" and "after" (discriminated union routes to ThisPeriodFilter which rejects extra keys via `extra="forbid"`); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 8f: DateFilter — empty object
1. `list_tasks` with `due: {}`
2. PASS if: error mentions "Date range filter requires at least one of: before or after" and lists accepted formats (ISO date, ISO datetime, datetime with offset, or 'now'); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

### 9. v1.3.2 Breaking Change Validation

Run each test INDIVIDUALLY (will error):

#### Test 9a: Removed availability value — "all"
1. `list_tasks` with `availability: ["all"]`
2. PASS if: error rejects "all" as invalid; valid values shown are `available`, `blocked`, `remaining`; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 9b: Removed availability value — "completed"
1. `list_tasks` with `availability: ["completed"]`
2. PASS if: error rejects "completed" as invalid; valid values shown are `available`, `blocked`, `remaining`; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 9c: Boolean completed — removed
1. `list_tasks` with `completed: true`
2. PASS if: error rejects boolean; the `completed` field expects a string shortcut or DateFilter object, not a boolean; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

### 10. v1.4.1 Phase 56 Derived-Field Rejection

Phase 56 introduced six derived read-only flags on the read side: `hasNote`, `hasRepetition`, `hasAttachments`, `hasChildren`, `isSequential`, `dependsOnChildren`. The write-side contracts (`add_tasks` / `edit_tasks`) reject all six via Pydantic `extra="forbid"` — generic schema error, no custom educational message (FLAG-08 lock). These tests spot-check that the structural guarantee holds on both tools.

Run each test INDIVIDUALLY (will error):

#### Test 10a: add_tasks rejects hasNote
1. `add_tasks` with `items: [{ name: "VE-10a", hasNote: true }]`
2. PASS if: error rejects `hasNote` as an unknown/forbidden field (generic Pydantic schema error — no custom message expected); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 10b: add_tasks rejects isSequential
1. `add_tasks` with `items: [{ name: "VE-10b", isSequential: true }]`
2. PASS if: error rejects `isSequential` as an unknown/forbidden field; same shape as 10a (cross-field consistency); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 10c: add_tasks rejects dependsOnChildren
1. `add_tasks` with `items: [{ name: "VE-10c", dependsOnChildren: true }]`
2. PASS if: error rejects `dependsOnChildren` as an unknown/forbidden field; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 10d: edit_tasks rejects derived field (hasChildren)
1. `edit_tasks` with `items: [{ id: "<temp-id>", hasChildren: true }]`
2. PASS if: error rejects `hasChildren` as an unknown/forbidden field (same `extra="forbid"` mechanism on edit-side — one representative is sufficient since the rejection is shared infra); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

### 11. v1.4 Phase 54 Batch Limit

Phase 54 lifted the 1-item constraint on `add_tasks` and `edit_tasks` and set a new ceiling of 50 items per call, enforced via Pydantic `max_length` on the `items` list. Exceeding the ceiling produces a generic schema-level error — no custom educational message. These tests spot-check the limit on both write tools.

Run each test INDIVIDUALLY (will error):

#### Test 11a: add_tasks rejects 51-item batch
1. `add_tasks` with 51 items (each a minimal valid task, e.g., `{ name: "VE-11a-N" }` for N = 1..51)
2. PASS if: error rejects the batch at schema level (generic Pydantic `max_length` message — no custom constant); mentions the items array length or maximum; does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 11b: edit_tasks rejects 51-item batch
1. `edit_tasks` with 51 items (each `{ id: "<temp-id>", name: "VE-11b-N" }` for N = 1..51 — reusing the same id is fine since the validation error fires before any items are dispatched to the service layer)
2. PASS if: error rejects the batch at schema level (generic Pydantic `max_length` message — cross-tool consistency with 11a); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | add_tasks: unknown field | Unknown field → clean "Unknown field" error | |
| 1b | add_tasks: invalid date | Unparseable date format → clean error listing accepted formats | |
| 1c | add_tasks: empty items | Empty items array → clean error | |
| 1d | add_tasks: missing name | No name field → "Task 1:" prefixed error | |
| 2a | edit_tasks: unknown field | Unknown field → clean "Unknown field" error | |
| 2b | edit_tasks: invalid lifecycle | Invalid lifecycle → clean error, no enum internals | |
| 2c | edit_tasks: empty name | Empty string name → clean error | |
| 2d | Note action: append + replace | Both `append` and `replace` set → mutually-exclusive error, fluent | |
| 2e | Note action: no operation | Empty `actions.note: {}` → "at least one operation required" error, fluent | |
| 3a | list_tasks: offset w/o limit | Offset without limit → "offset requires limit" | |
| 3b | list_tasks: invalid availability | Bad enum value → clean error listing available/blocked/remaining | |
| 3c | list_projects: invalid review_due_within | Bad format → error with valid examples | |
| 3d | list_tasks: unknown filter | Unknown field → clean error | |
| 3e | list_projects: offset w/o limit | Cross-tool: same error as 3a | |
| 3f | list_tags: unknown filter | Cross-tool: middleware catches on simple list tools | |
| 4a | Structural type mismatch | String instead of array → clean error | |
| 4b | _Unset sentinel hidden | Invalid union type → no "_Unset" visible | |
| 4c | camelCase in errors | Bad dates → field names in camelCase, not snake_case | |
| 5a | Null filter: string field | `project: null` → clean "cannot be null" with omit guidance | |
| 5b | Null filter: cross-tool | `folder: null` → same shape as 5a from list_projects | |
| 5c | Empty tags array | `tags: []` → clean "cannot be empty" with omit guidance | |
| 6a | Null moveTo container | `ending: null` → clean error mentioning `$inbox` | |
| 6b | Null parent on add | `parent: null` → clean error with omit-for-inbox guidance | |
| 7a | $inbox not a project | `get_project("$inbox")` → educational error, suggests list_tasks | |
| 7b | Reserved prefix: $trash | `parent: "$trash"` → lists valid system locations | |
| 7c | Reserved prefix: $foo | `parent: "$foo"` → same shape as 7b, clean interpolation | |
| 7d | Reserved prefix: read-side | `project: "$trash"` → same error from list_tasks context | |
| 8a | DateFilter: invalid "this" unit | `due: {this: "2w"}` → error about single calendar units only | |
| 8b | DateFilter: zero/negative count | `due: {next: "0d"}` → error about zero/negative count | |
| 8c | DateFilter: invalid duration unit | `due: {last: "3x"}` → error listing valid units (d, w, m, y) | |
| 8d | DateFilter: after > before | Inverted date range → error with actual values shown | |
| 8e | DateFilter: mixed shorthand+absolute | `due: {this: "w", after: "..."}` → "Unknown field: after" (extra="forbid") | |
| 8f | DateFilter: empty object | `due: {}` → "Date range filter requires at least one of: before or after" | |
| 9a | Breaking: availability "all" | Removed value → error listing available/blocked/remaining | |
| 9b | Breaking: availability "completed" | Removed value → same guidance as 9a | |
| 9c | Breaking: boolean completed | `completed: true` → expects string shortcut or DateFilter | |
| 10a | add_tasks: rejects hasNote | Derived read-only flag rejected via `extra="forbid"`; generic schema error; no pydantic internals | |
| 10b | add_tasks: rejects isSequential | Derived read-only flag rejected; same shape as 10a; no pydantic internals | |
| 10c | add_tasks: rejects dependsOnChildren | Derived read-only flag rejected; no pydantic internals | |
| 10d | edit_tasks: rejects hasChildren | Edit-side representative — same `extra="forbid"` mechanism rejects derived fields; no pydantic internals | |
| 11a | add_tasks: 51-item batch | Pydantic `max_length` rejects 51-item `add_tasks`; generic schema error; no pydantic internals | |
| 11b | edit_tasks: 51-item batch | Pydantic `max_length` rejects 51-item `edit_tasks`; cross-tool consistency with 11a; no pydantic internals | |
