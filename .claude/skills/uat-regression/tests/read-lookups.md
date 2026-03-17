# Read Lookups Test Suite

Tests `get_task`, `get_project`, and `get_tag` tools — happy-path lookups and not-found error handling.

## Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **Discover real entities first.** Use `get_all` to find existing projects, tags, and tasks to look up.

## Setup

### Step 1 — Discover Entities

Call `get_all` and store:
- **1 project** — pick any real project. Store its ID and name as proj-a.
- **1 tag** — pick any tag with a unique name. Store its ID and name as tag-a.

### Step 2 — Create Test Hierarchy

Create this structure in the inbox using `add_tasks`:

```
UAT-ReadLookups (parent)
+-- T1-LookupTarget
```

Create the parent first, then the child. Store all IDs.

### Manual Actions

None required.

Tell the user: "Running all tests now. I'll report results when done."

## Tests

### 1. get_task

#### Test 1a: get_task — existing task
1. `get_task` with T1's ID
2. Verify: returns object with correct `id`, `name: "T1-LookupTarget"`, and `parent` referencing UAT-ReadLookups
3. PASS if: full task object returned with correct fields

#### Test 1b: get_task — verify field richness
1. Using the result from 1a (or re-fetch T1)
2. Verify the response includes at minimum: `id`, `name`, `url`, `added`, `modified`, `flagged`, `note`, `availability`, `hasChildren`, `tags`, `parent`
3. PASS if: all listed fields are present in the response

#### Test 1c: get_task — not found
Run INDIVIDUALLY (will error):
1. `get_task` with ID `"nonexistent-id-99999"`
2. PASS if: error mentioning "not found"

### 2. get_project

#### Test 2a: get_project — existing project
1. `get_project` with proj-a's ID
2. Verify: returns object with correct `id` and `name` matching the stored project
3. PASS if: project object returned with correct fields

#### Test 2b: get_project — not found
Run INDIVIDUALLY (will error):
1. `get_project` with ID `"nonexistent-id-99999"`
2. PASS if: error mentioning "not found"

### 3. get_tag

#### Test 3a: get_tag — existing tag
1. `get_tag` with tag-a's ID
2. Verify: returns object with correct `id` and `name` matching the stored tag
3. PASS if: tag object returned with correct fields

#### Test 3b: get_tag — not found
Run INDIVIDUALLY (will error):
1. `get_tag` with ID `"nonexistent-id-99999"`
2. PASS if: error mentioning "not found"

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | get_task: existing | Looking up a task by ID returns full object with correct name and parent | |
| 1b | get_task: field richness | Response includes all expected fields (id, name, url, dates, flags, etc.) | |
| 1c | get_task: not found | Fake task ID returns "not found" error | |
| 2a | get_project: existing | Looking up a project by ID returns correct object | |
| 2b | get_project: not found | Fake project ID returns "not found" error | |
| 3a | get_tag: existing | Looking up a tag by ID returns correct object | |
| 3b | get_tag: not found | Fake tag ID returns "not found" error | |
