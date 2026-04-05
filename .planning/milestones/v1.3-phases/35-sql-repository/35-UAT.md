---
status: complete
phase: 35-sql-repository
source: 35-01-SUMMARY.md, 35-02-SUMMARY.md
started: 2026-03-30T12:00:00Z
updated: 2026-03-30T11:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Task status/availability filters
expected: Default query excludes completed/dropped, returns available+blocked. Explicit availability=[COMPLETED] returns only completed.
result: pass

### 2. Task simple filters (flagged, inbox, estimated_minutes)
expected: flagged=True/False, in_inbox=True, estimated_minutes_max inclusive, combined AND logic.
result: pass

### 3. Task join-based filters (project, tags)
expected: Project filter case-insensitive partial match on project name. Tags filter OR logic. SQL subquery joins.
result: pass
notes: Added test_list_tasks_project_filter_case_insensitive (committed 58e1eb1) to verify multi-project case-insensitive matching. Tag ID-vs-name contract inconsistency captured as todo + INFRA-07 requirement.

### 4. Task search (name + notes)
expected: Case-insensitive substring match on task name and plainTextNote.
result: pass

### 5. Task pagination & edge cases
expected: limit, offset, has_more, no results, all fit. total reflects filtered count.
result: pass

### 6. Project filters (availability, folder, review, flagged, pagination)
expected: Default remaining, completed, folder name match, review_due_within, flagged, pagination.
result: pass
notes: Clarified folder filter test to use distinct ID vs name (committed f18cf7c). Tag contract inconsistency discussion led to todo (migrate tag filter to repo) and new requirement (INFRA-07 did-you-mean suggestions).

### 7. Tag availability filters
expected: Default excludes dropped, available-only, dropped-only, all, result shape. Uses allowsNextAction + dateHidden.
result: pass

### 8. Folder availability filters
expected: Default excludes dropped, dropped-only, all, result shape. Uses dateHidden.
result: pass

### 9. Perspectives (no filter, builtin flag)
expected: Returns all, builtin=True when persistentIdentifier=None, result shape.
result: pass

### 10. Performance comparison
expected: Filtered SQL query faster than full get_all() snapshot with realistic seed data.
result: pass

### 11. Run the test suite
expected: Full test suite passes with no regressions.
result: pass

## Summary

total: 11
passed: 11
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none — design concerns captured as todos and requirements during review]
