---
status: diagnosed
phase: 15-write-pipeline-task-creation
source: 15-01-SUMMARY.md, 15-02-SUMMARY.md, 15-03-SUMMARY.md
started: 2026-03-08T01:00:00Z
updated: 2026-03-08T01:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Create Task — Name Only
expected: `add_tasks` with `[{"name": "..."}]` creates task in OmniFocus Inbox, returns ID.
result: pass

### 2. Create Task — All Optional Fields
expected: Setting note, dueDate, deferDate, plannedDate, flagged, estimatedMinutes all persist correctly.
result: issue
reported: "Notes read via SQLite/hybrid path contain .AppleSystemUIFont artifacts, swallowed newlines, HTML-encoded & and >. Bridge path returns clean plain text."
severity: major

### 3. Create Task Under a Project
expected: parentId pointing to project nests task under that project, not Inbox.
result: pass

### 4. Create Nested Child Under Project Task
expected: Task created under another task that's under a project (3 levels deep).
result: pass

### 5. Create Task Hierarchy in Inbox
expected: Parent task with subtasks, multiple levels deep, all in Inbox.
result: pass

### 6. Tags — Single Tag by Name
expected: Tag assigned by exact name.
result: pass

### 7. Tags — Multiple Tags
expected: Multiple tags assigned in one call.
result: pass

### 8. Tags — By ID
expected: Tag assigned using OmniFocus tag ID instead of name.
result: pass

### 9. Tags — Nonexistent Tag
expected: Clear error when tag doesn't exist.
result: pass

### 10. Tags — Mutually Exclusive
expected: Assigning two mutually exclusive sibling tags — behavior unclear.
result: issue
reported: "OmniJS allows assigning multiple mutually exclusive tags. OmniFocus only enforces exclusivity via UI. Agents can create tasks in states the UI wouldn't allow."
severity: minor

### 11. Dates — plannedDate Only
expected: plannedDate sets the forecast/planned date.
result: pass

### 12. Dates — All Three Dates Combined
expected: deferDate, dueDate, plannedDate all set independently.
result: pass

### 13. Dates — Timezone Requirement
expected: Naive datetime (no timezone) rejected.
result: pass

### 14. Flagged — Effective Inheritance
expected: Child with flagged:false under flagged parent shows effectiveFlagged:true.
result: pass

### 15. Urgency — Overdue
expected: Task with past due date shows urgency:"overdue".
result: pass

### 16. Urgency — Due Soon
expected: Task due later today shows urgency:"due_soon".
result: pass

### 17. Availability — Blocked by Defer Date
expected: Task deferred to future shows availability:"blocked".
result: issue
reported: "Sent deferDate 09:00Z, got back 10:00Z (+1h DST shift) while effectiveDeferDate was correct at 09:00Z. Inconsistent timezone handling between deferDate and effectiveDeferDate."
severity: minor

### 18. Edge Cases — Emoji, Special Chars, Long Names
expected: Unicode, quotes, angle brackets, long names all handled.
result: pass

### 19. Edge Cases — Fractional Estimate
expected: estimatedMinutes:150.5 accepted.
result: pass

### 20. Edge Cases — Extra Unknown Fields
expected: Unknown fields like priority, color, assignee silently ignored.
result: issue
reported: "Tool description doesn't declare field boundaries. Agent can't know which fields are unsupported (repetition rules, notifications, sequential/parallel) without probing or reading source."
severity: minor

### 21. Validation Error — Empty Name
expected: name:"" returns clear error, no task created.
result: pass

### 22. Validation Error — Invalid Parent
expected: Fake parentId returns clear error, no task created.
result: pass

### 23. Post-Write Freshness
expected: After add_tasks, immediately calling get_all/get_task returns the new task.
result: pass

### 24. Parallel Performance — 10 Concurrent Calls
expected: 10 simultaneous add_tasks calls all succeed.
result: pass

### 25. Parallel Performance — 32 Concurrent Calls
expected: Large fan-out of sibling tasks in one wave.
result: pass

## Summary

total: 25
passed: 21
issues: 4
pending: 0
skipped: 0

## Observations

- Parallel cancellation: Claude Code client cancels sibling calls on error — argues against lifting 1-item limit
- Single-item constraint validated as sufficient for real-world agent workflows
- ~1s/task throughput including all overhead; 50-task hierarchy in ~50 seconds
- Error messages clear and actionable: "Tag not found: X", "Parent not found: X", "Task name is required"

## Gaps

- truth: "Notes round-trip correctly through hybrid/SQLite read path"
  status: failed
  reason: "User reported: Notes via SQLite contain .AppleSystemUIFont artifacts, swallowed newlines, HTML-encoded & and >. Bridge path returns clean plain text."
  severity: major
  test: 2
  root_cause: "HybridRepository reads noteXMLData (BLOB with NSAttributedString XML) instead of plainTextNote (TEXT column). Regex tag-strip fails on font metadata, paragraph boundaries, and HTML entities."
  artifacts:
    - path: "src/omnifocus_operator/repository/hybrid.py"
      issue: "Lines 104-114, 269, 312: reads row['noteXMLData'] instead of row['plainTextNote']"
  missing:
    - "Replace row['noteXMLData'] with row['plainTextNote'] in _map_task_row() and _map_project_row()"
    - "Remove or repurpose _extract_note_text() regex function"
  debug_session: ".planning/debug/note-field-encoding.md"

- truth: "Mutually exclusive tags are enforced when assigned via API"
  status: deferred
  reason: "User reported: OmniJS allows assigning multiple mutually exclusive tags. UI-only enforcement. Agents can create invalid tag states."
  severity: minor
  test: 10
  deferred_to: "milestone gap — needs tag hierarchy awareness and exclusivity metadata"

- truth: "deferDate round-trips without timezone shift"
  status: failed
  reason: "User reported: Sent deferDate 09:00Z, got back 10:00Z (+1h DST shift). effectiveDeferDate was correct."
  severity: minor
  test: 17
  root_cause: "_parse_timestamp() appends +00:00 to timezone-naive ISO strings, treating local-time text as UTC. SQLite datetime columns (dateToStart, dateDue, datePlanned) store local time; timestamp columns (effective*) store CF epoch integers in UTC. Bug affects ALL three user-settable date fields."
  artifacts:
    - path: "src/omnifocus_operator/repository/hybrid.py"
      issue: "Lines 74-98: _parse_timestamp() wrongly assumes timezone-naive ISO strings are UTC"
  missing:
    - "Split _parse_timestamp into two paths: local-time ISO text (datetime columns) and CF epoch integer (timestamp columns)"
    - "Local-to-UTC conversion must use timezone offset at the stored date, not current time, to handle DST"
  debug_session: ".planning/debug/deferdate-timezone.md"

- truth: "Tool description declares which fields are supported and which are not"
  status: failed
  reason: "User reported: Agent can't know repetition rules, notifications, sequential/parallel aren't available without probing."
  severity: minor
  test: 20
  root_cause: "Docstring uses 'Each item accepts:' with 9 fields but no boundary language. OmniFocusBaseModel has no extra='forbid', so Pydantic silently drops unknown fields."
  artifacts:
    - path: "src/omnifocus_operator/server.py"
      issue: "Lines 152-168: missing boundary declaration in docstring"
    - path: "src/omnifocus_operator/models/base.py"
      issue: "Lines 29-33: no extra='forbid' on base model (extra='forbid' discussion deferred to todo)"
  missing:
    - "Add boundary language to add_tasks docstring: 'These are the only supported fields. Repetition rules, notifications, and sequential/parallel settings are not yet available.'"
  debug_session: ".planning/debug/tool-description-boundaries.md"
