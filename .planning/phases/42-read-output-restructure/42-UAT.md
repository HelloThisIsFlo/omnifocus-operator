---
status: complete
phase: 42-read-output-restructure
source: [42-01-SUMMARY.md, 42-02-SUMMARY.md, 42-03-SUMMARY.md]
started: 2026-04-06T20:00:00Z
updated: 2026-04-06T20:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Task parent field — tagged wrapper shape
expected: Call `get_task` for a task inside a project. `parent` should be a tagged object with exactly one branch: `{"project": {"id": "...", "name": "..."}}` or `{"task": {"id": "...", "name": "..."}}`. Old shape `{"type", "id", "name"}` must not appear.
result: issue
reported: "Two issues: (1) Both branches serialized — unset branch shows as null (e.g. {task: {id, name}, project: null}). (2) Top-level task in a project has parent type wrong — shows {project: null, task: {id: projectId, name: projectName}} instead of {project: {id, name}}. The project is misclassified as a task in the parent ref."
severity: major

### 2. Task project field — containing project ref
expected: Call `get_task` for a task nested inside a project (even a subtask). The output should have a top-level `project` field with `{"id": "...", "name": "..."}` pointing to the containing project (at any depth). Inbox tasks should show `{"id": "$inbox", "name": "Inbox"}`.
result: pass

### 3. Task inInbox field removed
expected: Call `get_task` for any task. The output should NOT contain an `inInbox` field at all. Inbox membership is now conveyed via `project.id == "$inbox"`.
result: pass

### 4. Project folder and nextTask — enriched refs
expected: Call `get_project` for a project inside a folder. `folder` should be `{"id": "...", "name": "..."}` (not a bare ID string). If the project has a next task, `nextTask` should also be `{"id": "...", "name": "..."}`. Projects without a folder should show `folder: null`.
result: issue
reported: "folder ref works correctly. nextTask self-references the project when it has no children (e.g. project gux8zqHgGas returns nextTask: {id: gux8zqHgGas, name: GM-TestProject2} — same as the project itself). Should be null when no child tasks exist. Correctly points to a real task when children exist. Also: hasChildren was transiently true on an empty project (likely OmniFocus-side caching, not our bug)."
severity: major

### 5. Tag parent — enriched ref
expected: Call `get_tag` for a nested tag (one that has a parent tag). `parent` should be `{"id": "...", "name": "..."}`. Top-level tags should show `parent: null`.
result: pass

### 6. Folder parent — enriched ref
expected: Call `get_tag` for a nested folder. `parent` should be `{"id": "...", "name": "..."}`. Top-level folders should show `parent: null`.
result: pass

### 7. Tool descriptions — {id, name} notation
expected: Check the tool descriptions (e.g. via MCP tool listing or `list_tools`). Descriptions should reference `{id, name}` notation for cross-entity references and should not mention `camelCase` field references from the old format.
result: pass

## Summary

total: 7
passed: 5
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "ParentRef should serialize only the set branch, and correctly identify project vs task parent type"
  status: failed
  reason: "User reported: (1) Both branches serialized with null for unset branch. (2) Top-level task in a project has parent type wrong — project misclassified as task in parent ref: {project: null, task: {id: projectId, name: projectName}}"
  severity: major
  test: 1
  artifacts: []
  missing: []

- truth: "nextTask should be null when a project has no child tasks"
  status: failed
  reason: "User reported: nextTask self-references the project when it has no children (e.g. project gux8zqHgGas returns nextTask with the project's own ID/name). Should be null. Works correctly when real children exist. Likely cause: OmniFocus stores the project's own ID as next_task internally (projects share the task table), mapper should detect this and return null."
  severity: major
  test: 4
  artifacts: []
  missing: []
