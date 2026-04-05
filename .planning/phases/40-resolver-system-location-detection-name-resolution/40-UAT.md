---
status: complete
phase: 40-resolver-system-location-detection-name-resolution
source: [40-01-SUMMARY.md, 40-02-SUMMARY.md]
started: 2026-04-05T20:00:00Z
updated: 2026-04-05T20:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Add task with parent by name
expected: Using add_tasks, create a task with `parent` set to a project name (not ID). The task should be created inside that project. The response should show the resolved project ID, not the name you typed.
result: pass

### 2. Add task with parent by substring
expected: Using add_tasks, create a task with `parent` set to a partial/substring of a project name (e.g., just "Road" for "Roadmap Planning"). The task should resolve to the correct project via case-insensitive substring matching.
result: pass

### 3. Add task with $inbox as parent
expected: Using add_tasks, create a task with `parent` set to `$inbox`. The task should be created in the OmniFocus inbox (no project). The response should reflect inbox placement.
result: pass

### 4. Name not found shows fuzzy suggestions
expected: Using add_tasks, create a task with `parent` set to a misspelled or non-existent project name. The error message should include fuzzy suggestions of similar project names with their IDs.
result: pass

### 5. Ambiguous name match lists candidates
expected: Using add_tasks, create a task with `parent` set to a name substring that matches multiple projects. The error should list all matching candidates with their IDs so the agent can disambiguate.
result: pass

### 6. Edit task — move to project by name (ending field)
expected: Using edit_tasks with `moveTo.ending` set to a project name (not ID), the task should move to the end of that project. The response should show the resolved project ID.
result: pass

### 7. Edit task — move to inbox via $inbox (ending field)
expected: Using edit_tasks with `moveTo.ending` set to `$inbox`, the task should move to the OmniFocus inbox.
result: pass

### 8. Edit task — before/after by task name
expected: Using edit_tasks with `moveTo.before` or `moveTo.after` set to a task name, the task should be positioned relative to the named task. Only task names are accepted here (not project names or $-prefixed system locations).
result: pass

### 9. $inbox rejected in anchor (before/after) context
expected: Using edit_tasks with `moveTo.before` set to `$inbox`, the operation should fail with an error indicating that system locations ($-prefix) are not valid for anchor positioning.
result: issue
reported: "Error message says 'Anchor task not found: $inbox' which is technically correct but misleading. Should clearly explain that $-prefixed system locations aren't valid in before/after context."
severity: minor

## Summary

total: 9
passed: 8
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Error clearly explains that system locations ($-prefix) are not valid for anchor (before/after) positioning"
  status: failed
  reason: "User reported: Error message says 'Anchor task not found: $inbox' which is technically correct but misleading. Should clearly explain that $-prefixed system locations aren't valid in before/after context."
  severity: minor
  test: 9
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
