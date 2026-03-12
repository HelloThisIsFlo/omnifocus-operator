---
status: complete
phase: 17-task-lifecycle
source: [17-03-SUMMARY.md]
started: 2026-03-12T19:00:00Z
updated: 2026-03-12T19:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Spurious Generic Warning Suppressed on Lifecycle No-Op
expected: Call edit_tasks with lifecycle "complete" on an already-completed task. You should see ONLY the lifecycle-specific no-op warning. No generic "No changes specified" or "No changes detected" warning alongside it.
result: pass

### 2. Repeating Task Drop Warning Text
expected: Call edit_tasks with lifecycle "drop" on a repeating task. The warning should say "this occurrence was skipped, next occurrence created" and mention that dropping the entire sequence must be done in the OmniFocus UI, with a prompt to confirm user intent.
result: pass

### 3. Same-Container Move Warning Text
expected: Call edit_tasks with moveTo beginning/ending targeting the container the task is already in. The warning should explain the OmniFocus API limitation and suggest using "before" or "after" with a sibling task ID as a workaround.
result: pass

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
