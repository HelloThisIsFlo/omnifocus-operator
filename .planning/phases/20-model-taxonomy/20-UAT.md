---
status: complete
phase: 20-model-taxonomy
source: 20-01-SUMMARY.md, 20-02-SUMMARY.md
started: 2026-03-18T16:00:00Z
updated: 2026-03-18T16:02:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Test Suite Green
expected: Run `uv run pytest` — all 517+ tests pass, zero failures, zero errors.
result: pass

### 2. Null-Means-Clear Semantics
expected: In the test suite, edit_task tests that set a field to `null` (e.g., clearing dueDate) still pass. Specifically `test_edit_tasks_clear_field` or equivalent should confirm that `None` values are preserved through the pipeline (not stripped). This validates the exclude_unset fix from the migration.
result: pass

### 3. Old Files Deleted
expected: The following files should NOT exist: `src/omnifocus_operator/models/write.py`, `src/omnifocus_operator/bridge/protocol.py`, `src/omnifocus_operator/repository/protocol.py`. All three were replaced by contracts/ and should be gone.
result: pass

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
