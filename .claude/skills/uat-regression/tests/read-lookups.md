---
suite: read-lookups
display: Read Lookups
test_count: 8

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
    T1-LookupTarget
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
