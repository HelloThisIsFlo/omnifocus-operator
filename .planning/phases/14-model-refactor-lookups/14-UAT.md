---
status: passed
phase: 14-model-refactor-lookups
source: 14-01-SUMMARY.md, 14-02-SUMMARY.md
started: 2026-03-07T23:30:00Z
updated: 2026-03-07T23:45:00Z
---

## Tests

### 1. Tool Rename (list_all -> get_all)
expected: Calling the MCP tool `get_all` returns tasks/projects/tags as before. The old name `list_all` no longer exists.
result: PASS

### 2. Task Parent as ParentRef
expected: Tasks returned by `get_all` show a unified `parent` field as an object with `type` ("project" or "task"), `id`, and `name` -- instead of separate `project` and `parent` string fields.
result: PASS

### 3. Get Task by ID
expected: Calling `get_task` with a valid task ID returns that single task with all fields (including ParentRef parent). Calling with a non-existent ID returns an error response.
result: PASS — valid ID returns full task with ParentRef parent; invalid ID returns "Task not found" error.

### 4. Get Project by ID
expected: Calling `get_project` with a valid project ID returns that single project with all fields. Calling with a non-existent ID returns an error response.
result: PASS — valid ID returns full project; invalid ID returns "Project not found" error.

### 5. Get Tag by ID
expected: Calling `get_tag` with a valid tag ID returns that single tag with all fields. Calling with a non-existent ID returns an error response.
result: PASS — valid ID returns full tag; invalid ID returns "Tag not found" error. Note: MCP SDK cancels sibling parallel tool calls when one returns isError, so error-case tests should run sequentially.

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
