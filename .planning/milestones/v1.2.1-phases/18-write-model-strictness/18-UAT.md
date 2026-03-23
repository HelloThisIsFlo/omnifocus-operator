---
status: complete
phase: 18-write-model-strictness
source: 18-01-SUMMARY.md, 18-02-SUMMARY.md
started: 2026-03-16T23:30:00Z
updated: 2026-03-16T23:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Unknown field rejected on add_tasks
expected: Call add_tasks with an item containing an unknown field like `bogusField`. Server rejects with error naming the specific field: "Unknown field 'bogusField'"
result: pass

### 2. Unknown field rejected on edit_tasks
expected: Call edit_tasks with an item containing an unknown field (e.g. `{"items": [{"id": "<any task id>", "bogusField": "hello"}]}`). Server rejects with error naming the specific field.
result: pass

### 3. camelCase aliases still accepted on add_tasks
expected: Call add_tasks using camelCase fields like `dueDate`, `estimatedMinutes`, `flagged`. Task is created successfully — camelCase fields are NOT treated as unknown.
result: pass

### 4. camelCase aliases still accepted on edit_tasks
expected: Call edit_tasks using camelCase fields like `dueDate`. Edit succeeds — camelCase fields are NOT treated as unknown.
result: pass

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
