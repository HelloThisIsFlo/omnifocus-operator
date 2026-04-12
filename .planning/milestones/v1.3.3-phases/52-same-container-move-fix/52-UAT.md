---
status: complete
phase: 52-same-container-move-fix
source: [52-01-SUMMARY.md, 52-02-SUMMARY.md]
started: 2026-04-12T17:00:00Z
updated: 2026-04-12T17:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Project beginning no-op warning
expected: Move first child of project to `beginning` of same project. Warning says "already at the beginning".
result: pass

### 2. Project ending no-op warning
expected: Move last child of project to `ending` of same project. Warning says "already at the ending".
result: pass

### 3. Cross-container beginning move
expected: Move task to `beginning` of a different project with existing children. Task lands at position 1.
result: pass

### 4. Cross-container ending move
expected: Move task to `ending` of a different project. Task lands at last position.
result: pass

### 5. Same-container ending reorder (project)
expected: Move task from bottom to `ending` after cross-container round-trip. Task lands at end of project.
result: pass

### 6. Same-container beginning reorder (project)
expected: Move last task to `beginning` of same project. Task moves to position 1, siblings shift down.
result: pass

### 7. Subtask beginning no-op warning
expected: Move first subtask to `beginning` of parent task. Warning says "already at the beginning".
result: pass

### 8. Subtask ending no-op warning
expected: Move last subtask to `ending` of parent task. Warning says "already at the ending".
result: pass

### 9. Same-container beginning reorder (subtask)
expected: Move last subtask to `beginning` of parent task. Task moves to first position.
result: pass

### 10. Same-container ending reorder (subtask)
expected: Move subtask back to `ending` of parent task. Task moves to last position.
result: pass

### 11. Single-child beginning no-op
expected: Move only child to `beginning` of its parent. Warning says "already at the beginning".
result: pass

### 12. Single-child ending no-op
expected: Move only child to `ending` of its parent. Warning says "already at the ending".
result: pass

### 13. Bridge-only: all 10 tests repeated
expected: All tests (no-op warnings, reorders, single-child) produce identical results on bridge-only mode as on hybrid mode.
result: pass

## Summary

total: 13
passed: 13
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
