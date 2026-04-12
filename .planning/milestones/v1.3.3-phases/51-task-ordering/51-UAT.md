---
status: complete
phase: 51-task-ordering
source: [51-01-SUMMARY.md, 51-02-SUMMARY.md]
started: 2026-04-12T14:30:00Z
updated: 2026-04-12T16:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Order field appears in task output
expected: Call `get_task` for any task. Response includes `order` field with dotted notation string (e.g., "1", "1.2", "3.1.4"). Value reflects outline position.
result: pass

### 2. Outline ordering in list_tasks
expected: Call `list_tasks` (no filters or with filters). Tasks are returned in OmniFocus outline order — parent tasks before their children, siblings in rank order. The `order` field values are sequential within their hierarchy level.
result: pass

### 3. Dotted notation hierarchy
expected: For a project with nested tasks, the order values show hierarchy: "1" for first root task, "1.1" for its first child, "1.2" for second child, "2" for second root task, etc. Compare against actual OmniFocus outline to verify.
result: pass

### 4. ~~Inbox tasks sort after projects~~ → Inbox tasks sort before projects
expected: ~~Inbox tasks appear after all project tasks.~~ → Call `get_all` or `list_tasks` with inbox tasks included. Inbox tasks appear **before** all project tasks, with order values starting at 1. Project tasks follow with their own order numbering.
result: pass (original: after — verified 2026-04-12)
result: pass (revised: before — verified 2026-04-12, ORDER-05 revised)

### 5. Filtered results preserve sparse ordinals
expected: Call `list_tasks` with a filter that removes some siblings (e.g., flagged filter). The remaining tasks keep their original outline ordinals — if tasks 1 and 3 remain but task 2 is filtered out, you see "1" and "3", not "1" and "2".
result: pass

### 6. Bridge degraded mode returns null order
expected: If using the bridge-only path (no SQLite cache), task `order` field should be `null` — this is expected degraded behavior. (May be skipped if hybrid path is always active.)
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
