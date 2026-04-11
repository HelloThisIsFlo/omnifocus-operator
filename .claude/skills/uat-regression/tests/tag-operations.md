---
suite: tag-operations
display: Tag Operations
test_count: 15

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
  UAT-TagOps (inbox parent)
    T1-TagRegression
    T2-TagOps

manual_actions:
  - "If no ambiguous tag name found in discovery, ask user to create two tags with the same name (e.g., 'TestDupe') under different parent tags for test 2g. Otherwise test 2g will be skipped."
---

# Tag Operations Test Suite

Tests tag add/remove/replace, ambiguity handling, no-op warnings, and error cases for `edit_tasks`.

## Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **Tags by ID.** Some tag names are ambiguous (multiple tags share a name). Always discover tags first via `get_all`, then use IDs for tags where the name might be ambiguous. Pick distinct, unambiguous tags for testing.
- **1-item limit.** `edit_tasks` currently accepts exactly 1 item per call.

**Known issue — spurious "no changes" warning:** When a tag action results in a no-op AND no field edits are in the request, a spurious "No changes specified/detected" warning fires alongside the specific tag warning. This is because the field-level no-op check doesn't account for actions being present. Document in the report's Observations section if encountered.

## Tests

### 1. Regression

#### Test 1: Remove tags alone (no crash)
1. `actions: { tags: { add: [<tag-a>] } }` on T1
2. `actions: { tags: { remove: [<tag-a>] } }` on T1 — NO add in the call
3. PASS if: success, no crash, tag removed

### 2. Tag Operations

#### Test 2a: Replace tags
1. `actions: { tags: { replace: [<tag-a>, <tag-b>] } }` on T2
2. `get_task` to verify tag-a and tag-b are present
3. PASS if: success, both tags confirmed via get_task

#### Test 2b: Replace with different set
1. `actions: { tags: { replace: [<tag-c>] } }` on T2
2. `get_task` to verify only tag-c remains
3. PASS if: tag-a and tag-b gone, only tag-c

#### Test 2c: Clear all tags
1. `actions: { tags: { replace: [] } }` on T2
2. `get_task` to verify `tags` is `[]` (empty array, not `null` or missing)
3. PASS if: success, `tags` is `[]`

#### Test 2d: Add incremental
1. `actions: { tags: { add: [<tag-a>] } }` on T2
2. `actions: { tags: { add: [<tag-b>] } }` on T2
3. `get_task` to verify both tag-a and tag-b are present
4. PASS if: both succeed, both tags confirmed via get_task

#### Test 2e: Remove selective
1. `actions: { tags: { remove: [<tag-a>] } }` on T2
2. `get_task` to verify tag-a is gone and tag-b remains
3. PASS if: success, correct tags confirmed via get_task

#### Test 2f: Mixed ID and name
1. `actions: { tags: { add: [<tag-a-id>, <tag-c-name>] } }` on T2 (one by ID, one by name)
2. PASS if: both resolved and added

#### Test 2g: Ambiguous tag name
1. Use the ambiguous tag name found in setup
2. `actions: { tags: { add: ["<ambiguous-name>"] } }` on T2
3. PASS if: error mentioning "ambiguous" with multiple IDs
4. SKIP if: no ambiguous tag exists (user declined in setup)

#### Test 2h: Add + remove combo
1. Clean T2 tags first, then `actions: { tags: { add: [<tag-b>] } }`
2. `actions: { tags: { add: [<tag-a>], remove: [<tag-b>] } }` on T2
3. `get_task` to verify tag-a present and tag-b gone
4. PASS if: success, correct tags confirmed via get_task

#### Test 2i: Multi-tag remove
1. Ensure T2 has tag-a and tag-b (add both if needed, one at a time)
2. `actions: { tags: { remove: [<tag-a>, <tag-b>] } }` on T2 (both in one call)
3. `get_task` to verify both tags are gone
4. PASS if: success, both tags removed in a single call

### 3. No-Op Warnings

#### Test 3a: No-op — add duplicate tag
1. `actions: { tags: { add: [<tag-a>] } }` on T1
2. `actions: { tags: { add: [<tag-a>] } }` again on T1
3. PASS if: second call returns success with a warning about tag already on task

#### Test 3b: No-op — remove absent tag
1. `actions: { tags: { remove: [<tag-b>] } }` on T1 (T1 doesn't have tag-b)
2. PASS if: success with warning about tag not on task

### 4. Error Handling

Run INDIVIDUALLY (will error):

#### Test 4: Nonexistent tag
1. `actions: { tags: { add: ["definitely-not-a-real-tag-xyz"] } }` on T2
2. PASS if: error about tag not found

### 5. Validation & Combos

#### Test 5a: Clean error — replace + add
1. `actions: { tags: { replace: [<tag-a>], add: [<tag-b>] } }` on T2
2. PASS if: error message does NOT contain "type=", "pydantic", or "input_value"

#### Test 5b: Combo — dup add + absent remove
1. Ensure T1 has tag-a (re-add if needed)
2. `actions: { tags: { add: [<tag-a>], remove: [<tag-b>] } }` on T1
3. PASS if: success with warnings for BOTH (duplicate add AND absent remove)

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1 | Remove tags alone | Calling tags.remove without add doesn't crash | |
| 2a | Tags: replace | Replace all tags using tags.replace; verify via get_task | |
| 2b | Tags: replace different | Replace with different set; old tags gone | |
| 2c | Tags: clear all | replace: [] returns `tags: []` (not null) | |
| 2d | Tags: add incremental | Add tags one at a time; both confirmed via get_task | |
| 2e | Tags: remove selective | Remove one tag; other remains | |
| 2f | Tags: mixed ID and name | Add using mix of ID and name in one call | |
| 2g | Tags: ambiguous name | Ambiguous tag name returns error with IDs | SKIP? |
| 2h | Tags: add + remove combo | Add one, remove another in same call | |
| 2i | Tags: multi-tag remove | Remove 2 tags in one call | |
| 3a | No-op: add duplicate | Adding existing tag returns warning | |
| 3b | No-op: remove absent | Removing absent tag returns warning | |
| 4 | Error: nonexistent tag | Adding fake tag name returns "not found" | |
| 5a | Clean error: replace + add | replace + add together returns clean error | |
| 5b | Combo: dup add + absent remove | Both warnings present in one call | |
