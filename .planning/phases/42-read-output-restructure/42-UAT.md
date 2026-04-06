---
status: complete
phase: 42-read-output-restructure
source: [42-01-SUMMARY.md, 42-02-SUMMARY.md, 42-03-SUMMARY.md]
started: 2026-04-06T20:00:00Z
updated: 2026-04-06T23:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Task parent field — tagged wrapper shape
expected: Call `get_task` for a task inside a project. `parent` should be a tagged object with exactly one branch: `{"project": {"id": "...", "name": "..."}}` or `{"task": {"id": "...", "name": "..."}}`. Old shape `{"type", "id", "name"}` must not appear.
result: pass
note: Re-verified after fix (field_serializer on Task.parent with exclude_none). Only set branch appears in output.

### 2. Task project field — containing project ref
expected: Call `get_task` for a task nested inside a project (even a subtask). The output should have a top-level `project` field with `{"id": "...", "name": "..."}` pointing to the containing project (at any depth). Inbox tasks should show `{"id": "$inbox", "name": "Inbox"}`.
result: pass

### 3. Task inInbox field removed
expected: Call `get_task` for any task. The output should NOT contain an `inInbox` field at all. Inbox membership is now conveyed via `project.id == "$inbox"`.
result: pass

### 4. Project folder and nextTask — enriched refs
expected: Call `get_project` for a project inside a folder. `folder` should be `{"id": "...", "name": "..."}` (not a bare ID string). If the project has a next task, `nextTask` should also be `{"id": "...", "name": "..."}`. Projects without a folder should show `folder: null`.
result: pass
note: Re-verified after fix (nextTask self-reference guard). Empty projects correctly show nextTask: null.

### 5. Tag parent — enriched ref
expected: Call `get_tag` for a nested tag (one that has a parent tag). `parent` should be `{"id": "...", "name": "..."}`. Top-level tags should show `parent: null`.
result: pass

### 6. Folder parent — enriched ref
expected: Call `get_tag` for a nested folder. `parent` should be `{"id": "...", "name": "..."}`. Top-level folders should show `parent: null`.
result: pass

### 7. Tool descriptions — {id, name} notation
expected: Check the tool descriptions (e.g. via MCP tool listing or `list_tools`). Descriptions should reference `{id, name}` notation for cross-entity references and should not mention `camelCase` field references from the old format.
result: pass

### 8. Bridge-only: parent/project ref names populated
expected: In bridge-only (fallback) mode, create tasks in a project and subtasks. `parent.task.name`, `parent.project.name`, and `project.name` should all be populated (not empty strings). IDs should be correct.
result: pass
note: New test added during re-verification. Fixed by _enrich_task in adapter.py.

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none — all original gaps closed, bridge-only name enrichment fixed]
