---
status: diagnosed
phase: 16-task-editing
source: [16-01-SUMMARY.md, 16-02-SUMMARY.md, 16-03-SUMMARY.md]
started: 2026-03-08T04:00:00Z
updated: 2026-03-08T04:45:00Z
---

## Current Test

[testing complete]

## Tests

### --- Field Editing ---

### 1. Rename task
expected: Call edit_tasks with a new name. Task name changes in OmniFocus.
result: pass

### 2. Update note
expected: Call edit_tasks with a new note. Task note updates in OmniFocus.
result: pass

### 3. Set estimate + flag
expected: Set estimatedMinutes and flagged in one call. Both apply.
result: pass

### 4. Set all 3 dates (due, defer, planned)
expected: Set dueDate, deferDate, and plannedDate. All three appear on task.
result: pass

### 5. Multi-field edit in one call
expected: Edit multiple fields simultaneously. All changes apply atomically.
result: pass

### 6. Unflag (set false)
expected: Set flagged: false on a flagged task. Flag removed.
result: pass

### 7. Clear dates with null
expected: Set dueDate/deferDate/plannedDate to null. Dates removed from task.
result: pass

### 8. Clear note with null
expected: Set note: null. Note cleared from task.
result: issue
reported: "OmniFocus rejects null notes — error: The property 'note' must be set to a non-null value."
severity: major

### 9. Clear note with empty string
expected: Set note: "" as workaround for clearing note.
result: pass

### 10. Clear estimate with null
expected: Set estimatedMinutes: null. Estimate removed.
result: pass

### 11. Patch semantics (untouched fields preserved)
expected: Edit one field, verify all other fields remain unchanged.
result: pass

### 12. Effective field inheritance updates on move
expected: Move task to project with inherited fields. Effective values update.
result: pass

### --- Tag Editing ---

### 13. addTags (by name)
expected: addTags with tag names. Tags added to task.
result: pass

### 14. addTags incremental (preserves existing)
expected: addTags adds new tags without removing existing ones.
result: pass

### 15. addTags mixed ID + name in same call
expected: Mix tag IDs and names in addTags array. All resolve and apply.
result: pass

### 16. tags — replace all
expected: tags: ["A", "B"] replaces all existing tags with A and B.
result: pass

### 17. tags — replace with completely different set
expected: Replace tags with an entirely new set. Old tags gone, new tags present.
result: pass

### 18. tags: [] — clear all
expected: tags: [] removes all tags from task.
result: pass

### 19. removeTags alone
expected: removeTags: ["X"] removes tag X from task.
result: issue
reported: "Bridge bug: params.tagIds is undefined — crashes with 'undefined is not an object (evaluating params.tagIds.map)'"
severity: blocker

### 20. addTags + removeTags combo
expected: addTags and removeTags in same call. Additions and removals both apply.
result: pass

### 21. removeTags no-op warning (tag not on task)
expected: removeTags with tag not on task. Warning returned, no error.
result: pass

### 22. Tag not found error
expected: Reference nonexistent tag name. Clean error message.
result: pass

### 23. Ambiguous tag (addTags)
expected: Reference ambiguous tag name in addTags. Clean error with candidate IDs.
result: pass

### 24. Ambiguous tag (tags replace)
expected: Reference ambiguous tag name in tags replace mode. Same clean error.
result: pass

### 25. Ambiguous tag (removeTags via combo)
expected: Reference ambiguous tag name in removeTags. Same clean error.
result: pass

### 26. tags + addTags mutual exclusion
expected: Provide both tags and addTags. Clean validation error.
result: issue
reported: "Validation caught correctly, but raw Pydantic error noise leaks — full type=value_error, input_value, input_type, and pydantic.dev URL"
severity: minor

### 27. Duplicate/no-op addTags
expected: addTags with tag already on task. Warning that tag is already present.
result: issue
reported: "Silent no-op — tag already present but no warning returned"
severity: minor

### --- Task Movement ---

### 28. after sibling
expected: moveTo after: siblingId. Task moves after specified sibling.
result: pass

### 29. before sibling
expected: moveTo before: siblingId. Task moves before specified sibling.
result: pass

### 30. beginning of parent
expected: moveTo beginning: parentId. Task moves to first child position.
result: pass

### 31. ending of parent
expected: moveTo ending: parentId. Task moves to last child position.
result: pass

### 32. Cross-level move (pop up via before)
expected: Move nested task up a level using before on a higher-level sibling.
result: pass

### 33. Move to inbox (ending: null)
expected: moveTo ending: null. Task moves to inbox.
result: pass

### 34. Cross-branch move (Alpha → Sandbox project)
expected: Move task from one project to a completely different project.
result: pass

### 35. Subtree moves with children
expected: Move task with children. Entire subtree moves together.
result: pass

### 36. Circular reference (direct parent→child)
expected: Move parent into its own child. Clean cycle detection error.
result: pass

### 37. Circular reference (4 levels deep)
expected: Move ancestor 4 levels up into descendant. Clean cycle detection error.
result: pass

### 38. Circular reference (task → itself)
expected: Move task into itself. Clean cycle detection error.
result: pass

### 39. Move + edit fields in same call
expected: Combine moveTo with field edits. Both movement and edits apply.
result: pass

### 40. Complex multi-move (6 parallel moves)
expected: 6 parallel edit_tasks calls moving different tasks. All succeed.
result: pass

### 41. Full hierarchy restore (10 sequential moves)
expected: 10 sequential moves to rebuild a task hierarchy. Final order verified.
result: pass

### 42. Parallel moves on independent targets
expected: Parallel edit_tasks on independent tasks. No interference.
result: pass

### 43. Race condition test (3 groups, dependent moves, 3s delay)
expected: Dependent moves with delays. Serial execution observed — correct ordering.
result: pass

### --- Error Handling ---

### 44. Nonexistent task ID
expected: Edit with invalid task ID. Clean "Task not found: ..." error.
result: pass

### 45. Empty name
expected: Edit with name: "". Clean "Task name cannot be empty" error.
result: pass

### 46. Nonexistent moveTo target
expected: moveTo with invalid anchor ID. Clean "Anchor task not found: ..." error.
result: pass

### 47. moveTo with multiple keys
expected: moveTo with e.g. both beginning and ending. Clean validation error.
result: issue
reported: "Validation caught correctly, but raw Pydantic error noise leaks — same issue as test 26"
severity: minor

### 48. Deleted task
expected: Edit a deleted task. Clean "Task not found: ..." error.
result: pass

### --- Edge Cases ---

### 49. Edit completed task
expected: Edit a completed task. Success with warning that task is completed.
result: issue
reported: "Succeeds silently — no warning that task is completed. Agent may unknowingly modify resolved tasks."
severity: minor

### 50. Edit dropped task
expected: Edit a dropped task. Success with warning that task is dropped.
result: issue
reported: "Succeeds silently — no warning that task is dropped. Agent may unknowingly modify resolved tasks."
severity: minor

### 51. Empty edit (just ID, no fields)
expected: Edit with only task ID and no fields. Warning that no changes were specified.
result: issue
reported: "Silent no-op — no warning that nothing was changed"
severity: minor

### 52. No-op move (already in position)
expected: Move task to where it already is. Warning that task is already there.
result: issue
reported: "Silent no-op — no warning that task is already in position"
severity: minor

### 53. Parallel edits on same task (different fields)
expected: Two parallel edits on same task with different fields. Both apply.
result: pass

### --- Bridge vs Hybrid Consistency ---

### 54. Circular reference in bridge mode
expected: Same cycle detection error as hybrid mode.
result: pass

### 55. removeTags alone in bridge mode
expected: removeTags alone works in bridge mode.
result: issue
reported: "Same bridge bug as test 19 — params.tagIds undefined"
severity: blocker

### 56. No-op in bridge mode
expected: Same silent no-op behavior as hybrid mode.
result: pass

### 57. removeTags no-op warning in bridge mode
expected: Same warning behavior as hybrid mode.
result: pass

## Summary

total: 57
passed: 45
issues: 12
pending: 0
skipped: 0

## Gaps

- truth: "removeTags alone removes specified tags from task"
  status: failed
  reason: "User reported: Bridge bug — params.tagIds is undefined when only removeTags provided, crashes with 'undefined is not an object (evaluating params.tagIds.map)'"
  severity: blocker
  test: 19
  root_cause: "Key mismatch: bridge.js 'remove' handler reads params.tagIds but service sends params.removeTagIds. Test masks bug by passing tagIds directly."
  artifacts:
    - path: "src/omnifocus_operator/bridge/bridge.js"
      issue: "Line 291: reads params.tagIds instead of params.removeTagIds in 'remove' mode"
    - path: "bridge/tests/handleEditTask.test.js"
      issue: "Line 289: test passes tagIds instead of removeTagIds, masking the real contract"
  missing:
    - "Change bridge.js remove handler to read params.removeTagIds"
    - "Fix test to pass removeTagIds matching actual service-to-bridge contract"
  debug_session: ".planning/debug/removetags-crash.md"

- truth: "note: null clears the note field"
  status: failed
  reason: "User reported: OmniFocus rejects null notes — error: The property 'note' must be set to a non-null value."
  severity: major
  test: 8
  root_cause: "OmniFocus API treats note as always-present string (empty string = no note). Service passes None verbatim, bridge sets task.note = null, OmniFocus rejects."
  artifacts:
    - path: "src/omnifocus_operator/bridge/bridge.js"
      issue: "Line 258: task.note = params.note — no null-to-empty mapping"
    - path: "src/omnifocus_operator/service.py"
      issue: "Lines 129-132: passes None through without transformation"
  missing:
    - "Map null → '' for note at bridge boundary (bridge.js)"
    - "Consider same fix in handleAddTask (line 235) for consistency"
  debug_session: ".planning/debug/note-null-rejected.md"

- truth: "Pydantic validation errors show clean human-readable messages"
  status: failed
  reason: "User reported: tags+addTags mutual exclusion and moveTo multiple keys return raw Pydantic noise with type=value_error, input_value, input_type, and pydantic.dev URL"
  severity: minor
  test: 26
  root_cause: "server.py model_validate() calls have no try/except for pydantic.ValidationError. Model validators raise clean ValueError messages but Pydantic wraps them with noisy metadata."
  artifacts:
    - path: "src/omnifocus_operator/server.py"
      issue: "Line 232: TaskEditSpec.model_validate() uncaught; Line 181: TaskCreateSpec.model_validate() same pattern"
  missing:
    - "Catch ValidationError at both model_validate sites in server.py"
    - "Extract human-readable messages via e.errors() and re-raise as ValueError"
  debug_session: ".planning/debug/pydantic-validation-leak.md"

- truth: "addTags with tag already present returns a warning"
  status: failed
  reason: "User reported: Silent no-op — tag already present but no warning returned"
  severity: minor
  test: 27
  root_cause: "Warning logic only implemented for removeTags no-ops. addTags path does not check current_tag_ids before adding."
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "addTags branches (lines 158, 175) don't check if tag is already present"
  missing:
    - "Build current_tag_ids set, check add_ids against it, append warning for duplicates"
  debug_session: ".planning/debug/missing-noop-warnings.md"

- truth: "Editing completed/dropped tasks returns a warning"
  status: failed
  reason: "User reported: Succeeds silently — no warning that task is completed/dropped. Agent may unknowingly modify resolved tasks."
  severity: minor
  test: 49
  root_cause: "No status check after task existence validation. Task object has availability field (COMPLETED/DROPPED) but it's never inspected."
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "After line 112 (task existence check): no availability check before proceeding"
  missing:
    - "Check task.availability for COMPLETED/DROPPED after existence check, append warning"
  debug_session: ".planning/debug/missing-noop-warnings.md"

- truth: "Empty edit or no-op operations return a warning"
  status: failed
  reason: "User reported: Silent no-op for empty edits (no fields) and no-op moves (already in position) — no warning returned"
  severity: minor
  test: 51
  root_cause: "No empty-payload detection. After field processing, payload with only 'id' key means nothing to change but proceeds to bridge anyway."
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "After line 228 (moveTo handling): no check for len(payload) == 1 (only id)"
  missing:
    - "Check len(payload) == 1 after all field processing, return early with no-op warning"
    - "No-op move detection partially feasible (same container) but position-within-container not available"
  debug_session: ".planning/debug/missing-noop-warnings.md"
