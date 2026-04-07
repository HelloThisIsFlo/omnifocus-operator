---
status: complete
phase: 43-filters-project-tools
source: 43-03-SUMMARY.md
started: 2026-04-07T14:00:00Z
updated: 2026-04-07T14:05:00Z
prior_session: diagnosed (4/4 passed, gap identified and fixed)
---

## Current Test

[testing complete]

## Tests

### 1. Bridge-only list_tasks excludes project root tasks
expected: Set OPERATOR_REPOSITORY=bridge-only and restart the server. Call list_tasks (no filters). Scan the results — no task should have a self-referencing parent (where parent.project.id === task.id). Projects should only appear in the projects section, never as tasks.
result: pass
notes: 1,619 tasks returned. Zero self-referencing parents. Cross-referenced all task IDs against 363 project IDs — zero overlap.

### 2. Bridge-only get_all excludes project root tasks
expected: Still in bridge-only mode. Call get_all. The tasks array should not contain entries that are actually projects. Compare task count against hybrid mode — they should be roughly equal (bridge-only was previously inflated by project ghost entries).
result: pass
notes: 2,893 tasks, 375 projects in get_all. Zero task/project ID overlap. Zero self-referencing parents. Higher count than list_tasks is expected (includes completed/dropped).

### 3. Bridge-only project-scoped list_tasks is clean
expected: Still in bridge-only mode. Call list_tasks with a project filter (pick any project you have). Results should contain only real tasks in that project — no phantom entry for the project itself.
result: pass
notes: Tested with project="GM-" (matched 3 GM-TestProject variants). 4 tasks returned, all real tasks. Project bW2BCrF4TAz appears only as parent reference, never as task entry.

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
