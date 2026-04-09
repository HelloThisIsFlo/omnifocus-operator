---
status: complete
phase: 47-cross-path-equivalence-breaking-changes
source: 47-01-SUMMARY.md, 47-02-SUMMARY.md, 47-03-SUMMARY.md
started: 2026-04-09T14:00:00Z
updated: 2026-04-09T15:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Due: overdue
expected: Overdue tasks returned; no-due and future excluded; inherited overdue included
result: pass
source: live-regression

### 2. Due: soon
expected: Tasks within threshold returned; overdue included (soon includes overdue); future excluded
result: issue
reported: "Server returned SQL error 'no such column: key'. The 'soon' shortcut is completely broken."
severity: blocker
source: live-regression

### 3. Due: today
expected: Tasks due today returned; future and no-due excluded
result: pass
source: live-regression

### 4. Lifecycle: completed all
expected: All completed tasks appear alongside active; dropped excluded
result: pass
source: live-regression

### 5. Lifecycle: dropped all
expected: All dropped tasks appear alongside active; completed excluded
result: pass
source: live-regression

### 6. Lifecycle: completed today
expected: Today's completions returned alongside remaining tasks. Auto-includes completed availability.
result: issue
reported: "Only DF-Completed returned (1 item). Expected 10 items (9 remaining + 1 completed today). completed: 'today' does not auto-include remaining tasks — acts as restrictive filter instead of additive."
severity: major
source: live-regression

### 7. Lifecycle: completed {last: 1w}
expected: Tasks completed within last week returned alongside remaining tasks.
result: issue
reported: "Same behavior as completed 'today'. Only DF-Completed returned (1 item). Expected 10 items. DateFilter-based lifecycle filters do not auto-include remaining tasks."
severity: major
source: live-regression

### 8. Lifecycle: auto-inclusion
expected: completed filter adds COMPLETED to availability without explicit setting
result: pass
source: live-regression

### 9. Lifecycle: available + completed
expected: Explicit available-only + lifecycle auto-include; blocked excluded
result: pass
source: live-regression

### 10. Shorthand: this week
expected: Calendar week; today's tasks included, 30-day future excluded
result: pass
source: live-regression

### 11. Shorthand: last 3 days
expected: Rolling past [midnight-3d, now]; overdue included, future-today excluded
result: pass
source: live-regression

### 12. Shorthand: next week
expected: Rolling future [now, midnight+8d]; near-future included, 30-day excluded
result: pass
source: live-regression

### 13. Non-due: defer today
expected: Tasks with today's defer date only; others excluded
result: issue
reported: "Server returned 'str' object has no attribute 'this'. The 'today' string shortcut is not handled for the defer field."
severity: blocker
source: live-regression

### 14. Non-due: added today
expected: All today's tasks returned; no lifecycle auto-include for added
result: issue
reported: "Same error as defer today: 'str' object has no attribute 'this'. The 'today' shortcut broken for added as well."
severity: blocker
source: live-regression

### 15. Soon includes overdue
expected: Overdue task explicitly found in "soon" results
result: issue
reported: "Blocked by test 2 — 'soon' shortcut is completely broken with SQL error."
severity: blocker
source: live-regression

### 16. Inherited: overdue
expected: No direct dueDate; found by overdue filter via inherited effective date
result: pass
source: live-regression

### 17. Inherited: absolute
expected: Inherited effective date caught by absolute {before} filter
result: pass
source: live-regression

### 18. availability=[] Returns Zero Items (Gap 2 Closure)
expected: After Plan 03 fix: list_tasks(availability=[]) returns 0 tasks (not 2958). Combined: availability=[], completed="all" returns ONLY completed tasks (no remaining mixed in).
result: pass
notes: Live MCP test confirmed. availability=[] returned 0 items. availability=[] + completed="all" returned 582 items, all with availability=completed — zero remaining tasks mixed in.

## Summary

total: 18
passed: 12
issues: 6
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "due: 'soon' returns tasks within threshold including overdue"
  status: failed
  reason: "User reported: Server returned SQL error 'no such column: key'. Completely broken — server crash, not incorrect results."
  severity: blocker
  tests: [2, 15]
  root_cause: "hybrid.py _read_due_soon_setting_sync() uses wrong column names (key/value) for OmniFocus Setting table. Correct columns: persistentIdentifier/valueData. Also valueData is plist-encoded, needs plistlib.loads()."
  artifacts:
    - path: "src/omnifocus_operator/repository/hybrid/hybrid.py"
      issue: "Lines 1015-1018: SELECT key, value FROM Setting — columns don't exist"
  missing:
    - "Use correct columns: persistentIdentifier, valueData"
    - "Deserialize plist-encoded valueData with plistlib.loads()"

- truth: "'today' shortcut works for non-due date fields (defer, added)"
  status: failed
  reason: "User reported: Server returned 'str' object has no attribute 'this'. The 'today' shortcut is not handled for non-due fields."
  severity: blocker
  tests: [13, 14]
  root_cause: "Non-due fields use Literal['today'] (raw string) while due uses DueDateShortcut (StrEnum). resolve_date_filter checks isinstance(value, StrEnum) which catches enums but not strings. String falls through to _resolve_date_filter_obj which tries .this on it."
  artifacts:
    - path: "src/omnifocus_operator/service/resolve_dates.py"
      issue: "Line 61: isinstance(value, StrEnum) check skips plain string 'today'"
    - path: "src/omnifocus_operator/contracts/use_cases/list/"
      issue: "defer/added/modified/planned use Literal['today'] instead of StrEnum"
  missing:
    - "Create DateFieldShortcut(StrEnum) with TODAY='today' for non-due/non-lifecycle fields"
    - "Update contract type annotations from Literal['today'] to DateFieldShortcut | DateFilter"

- truth: "Lifecycle date-based filters (completed: 'today', completed: {last: '1w'}) auto-include remaining tasks"
  status: failed
  reason: "User reported: Only lifecycle items returned (1 item). Expected remaining + lifecycle items. completed: 'all' works correctly but date-based lifecycle filters silently drop remaining tasks."
  severity: major
  tests: [6, 7]
  root_cause: "Semantic category error: lifecycle date filters (completed, dropped) are additive — 'also show these lifecycle items, scoped by date.' But the code treats them as restrictive — 'only show tasks matching this date' — same as due/defer/added. Remaining tasks have NULL completion dates; NULL fails SQL comparison (NULL >= ? is FALSE) and Python is-not-None check, silently excluding all remaining tasks. Both repo paths affected identically."
  artifacts:
    - path: "src/omnifocus_operator/repository/hybrid/query_builder.py"
      issue: "Lines 48-53: _add_date_conditions applies lifecycle fields identically to regular fields — global AND excludes NULL rows"
    - path: "src/omnifocus_operator/repository/bridge_only/bridge_only.py"
      issue: "Lines 208-218: same logic — completion_date is not None check filters out remaining tasks"
  missing:
    - "Split _add_date_conditions: regular fields (due, defer, planned, added, modified) stay as global AND. Lifecycle fields (completed, dropped) use IS NULL OR pattern: (column IS NULL OR column >= ?) — lets remaining tasks through while scoping lifecycle items by date."
    - "Bridge path: flip 'is not None and' to 'is None or' for lifecycle fields"
    - "Cross-path equivalence tests for lifecycle date filtering with remaining tasks"
