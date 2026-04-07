---
status: complete
phase: 41-write-pipeline-inbox-in-add-edit
source: [41-01-SUMMARY.md, 41-02-SUMMARY.md]
started: 2026-04-06T14:00:00Z
updated: 2026-04-06T14:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. MoveAction Null Rejection
expected: Constructing a MoveAction with any positional field set to null (ending=None, beginning=None, etc.) raises a ValidationError with a clear per-field error message like "ending cannot be null".
result: pass

### 2. AddTaskCommand Parent Null Rejection
expected: Constructing an AddTaskCommand with parent=None raises a ValidationError with message "parent cannot be null". Agents must omit the field (inbox default) or pass an explicit value like "$inbox".
result: pass

### 3. AddTaskCommand Parent Omitted Defaults to Inbox
expected: When parent is omitted from AddTaskCommand, the task is created in the inbox. The service pipeline detects UNSET via is_set() and routes to inbox — same behavior as before, but now using Patch[str] instead of None.
result: pass

### 4. $inbox Sentinel in add_tasks
expected: Calling add_tasks with parent="$inbox" creates the task in the inbox. The resolver recognizes "$inbox" and resolves it to the inbox container, same as omitting parent entirely.
result: pass

### 5. $inbox Sentinel in edit_tasks (ending/beginning)
expected: Calling edit_tasks with moveTo ending="$inbox" or beginning="$inbox" moves the task to the inbox. The resolver handles "$inbox" in move operations.
result: pass

### 6. Cross-Type Error for before/after=$inbox
expected: Calling edit_tasks with moveTo before="$inbox" or after="$inbox" raises a cross-type error. The inbox is a container, not a task — before/after require task IDs, so "$inbox" is rejected with a clear error message.
result: pass

### 7. PatchOrNone Fully Eliminated
expected: No references to PatchOrNone exist anywhere in the src/ directory. The type alias has been completely removed from contracts/base.py and __init__.py. grep -r "PatchOrNone" src/ returns zero matches.
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
