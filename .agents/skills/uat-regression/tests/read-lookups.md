---
suite: read-lookups
display: Read Lookups
test_count: 9

discovery:
  needs:
    - type: project
      label: proj-a
      filters: [active]
    - type: tag
      label: tag-a
      filters: [available, unambiguous]

setup: |
  ### Tasks
  UAT-ReadLookups (inbox parent)
    T1-LookupTarget    (note: "phase-56 parity fixture")
---

# Read Lookups Test Suite

Tests `get_task`, `get_project`, and `get_tag` tools — happy-path lookups and not-found error handling.

## Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **Discover real entities first.** Use `get_all` to find existing projects, tags, and tasks to look up.

## Tests

### 1. get_task

#### Test 1a: get_task — existing task
1. `get_task` with T1's ID
2. Verify: returns object with correct `id`, `name: "T1-LookupTarget"`, `parent: {"task": {"id": "<UAT-id>", "name": "UAT-ReadLookups"}}`, and `project: {"id": "$inbox", "name": "Inbox"}`
3. PASS if: full task object returned with correct fields, enriched parent (tagged wrapper) and project (id+name ref)

#### Test 1b: get_task — verify field richness
1. Using the result from 1a (or re-fetch T1)
2. Verify the response includes at minimum: `id`, `name`, `url`, `added`, `modified`, `flagged`, `note`, `availability`, `hasChildren`, `tags`, `parent`, `project`
3. Verify: `parent` is an object (tagged wrapper, not a string), `project` is an object with `id` and `name`, there is NO `inInbox` field
4. PASS if: all listed fields present, parent/project are enriched objects, no inInbox field

#### Test 1c: get_task — not found
Run INDIVIDUALLY (will error):
1. `get_task` with ID `"nonexistent-id-99999"`
2. PASS if: error mentioning "not found"

### 2. get_project

#### Test 2a: get_project — existing project
1. `get_project` with proj-a's ID
2. Verify: returns object with correct `id` and `name` matching the stored project
3. Verify: `folder` is either `null` or an enriched `{id, name}` object (not a bare string); `nextTask` is either `null` or `{id, name}`
4. PASS if: project object returned with correct fields, enriched folder/nextTask references

#### Test 2b: get_project — not found
Run INDIVIDUALLY (will error):
1. `get_project` with ID `"nonexistent-id-99999"`
2. PASS if: error mentioning "not found"

### 3. get_tag

#### Test 3a: get_tag — existing tag
1. `get_tag` with tag-a's ID
2. Verify: returns object with correct `id` and `name` matching the stored tag
3. Verify: `parent` is either `null` or an enriched `{id, name}` object (not a bare string)
4. PASS if: tag object returned with correct fields, enriched parent reference

#### Test 3b: get_tag — not found
Run INDIVIDUALLY (will error):
1. `get_tag` with ID `"nonexistent-id-99999"`
2. PASS if: error mentioning "not found"

### 4. $inbox Guard

#### Test 4a: get_project("$inbox") — error
Run INDIVIDUALLY (will error):
1. `get_project` with ID `"$inbox"`
2. PASS if: error mentions "The '$inbox' appears as a project on tasks but is not a real OmniFocus project" and suggests using `list_tasks` with `inInbox=true`

### 5. Phase 56 Property Surface

#### Test 5a: get_task parity with list_tasks — presence flags agree (L-GetTaskNewFlags)
1. `list_tasks` with `search: "T1-LookupTarget"` — capture the matching item from the response
2. `get_task` with T1's ID
3. PASS if: the Phase 56 presence flags (`hasNote`, `hasRepetition`, `hasAttachments`, `isSequential`, `dependsOnChildren`) agree between both responses for the same task:
   - Any flag present in the `list_tasks` item with value `true` is also present in the `get_task` response with value `true`
   - Any flag absent from the `list_tasks` item (stripped because `false`) is also absent from `get_task` (not present as `false` either — strip-when-false must apply to both surfaces)
4. Given the setup note on T1-LookupTarget, at minimum `hasNote: true` should appear identically on both surfaces.
5. Notes: `list_tasks` and `get_task` are separate code paths through the projection pipeline. This test protects against one surface drifting from the other on the Phase 56 flag set. For this session the hierarchy include group is NOT part of this parity check — it's exercised in list-tasks.md tests 9f/9g/9h.

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | get_task: existing | Task by ID returns enriched parent (tagged wrapper) and project ({id, name}) | |
| 1b | get_task: field richness | All fields present; parent/project are objects not strings; no inInbox field | |
| 1c | get_task: not found | Fake task ID returns "not found" error | |
| 2a | get_project: existing | Project by ID returns enriched folder and nextTask ({id, name} or null) | |
| 2b | get_project: not found | Fake project ID returns "not found" error | |
| 3a | get_tag: existing | Tag by ID returns enriched parent ({id, name} or null) | |
| 3b | get_tag: not found | Fake tag ID returns "not found" error | |
| 4a | get_project: $inbox | `get_project("$inbox")` returns educational error about virtual location | |
| 5a | get_task parity: Phase 56 flags | Phase 56 presence flags agree between `list_tasks` and `get_task` on the same task — no surface drift | |
