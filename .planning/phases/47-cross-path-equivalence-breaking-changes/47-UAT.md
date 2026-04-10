---
status: complete
phase: 47-cross-path-equivalence-breaking-changes
source: 47-04-SUMMARY.md, 47-05-SUMMARY.md, 47-06-SUMMARY.md
started: 2026-04-10T09:00:00Z
updated: 2026-04-10T09:05:00Z
prior_round: 12 passed, 6 issues (all 6 re-tested below after gap closure plans 04-06)
---

## Current Test

[testing complete]

## Tests

### 1. Due: soon shortcut
expected: `list_tasks(due="soon")` returns tasks within the DueSoon threshold. Overdue tasks included. No SQL error — previously crashed with "no such column: key".
result: pass
fix: Plan 04 — corrected Setting table columns (persistentIdentifier/valueData) + plist decoding
verified: live MCP call returned 226 tasks, no error

### 2. Soon includes overdue
expected: Overdue tasks explicitly present in `due="soon"` results. Previously blocked by test 1's SQL crash.
result: pass
fix: Plan 04 — same root cause as test 1
verified: all returned tasks had urgency=overdue, confirming overdue inclusion

### 3. Non-due: defer today
expected: `list_tasks(defer="today")` returns tasks with today's defer date. No crash — previously errored with "'str' object has no attribute 'this'".
result: pass
fix: Plan 05 — DateFieldShortcut(StrEnum) replaces Literal["today"]
verified: live MCP call returned 0 tasks (none deferred to today), no error

### 4. Non-due: added today
expected: `list_tasks(added="today")` returns tasks added today. No crash — same error as test 3.
result: pass
fix: Plan 05 — same root cause as test 3
verified: live MCP call returned 0 tasks (none added today), no error

### 5. Lifecycle: completed today
expected: `list_tasks(completed="today")` returns today's completions AND remaining active tasks. Previously returned only the completed item, dropping all remaining tasks.
result: pass
fix: Plan 06 — additive IS NULL OR semantics for lifecycle date fields
verified: live MCP call returned 1664 tasks (remaining tasks preserved alongside lifecycle items)

### 6. Lifecycle: completed {last: 1w}
expected: `list_tasks(completed={"last": "1w"})` returns tasks completed in last week AND remaining active tasks. Previously same bug as test 5.
result: pass
fix: Plan 06 — same root cause as test 5
verified: live MCP call returned 1691 tasks (remaining tasks preserved alongside lifecycle items)

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
