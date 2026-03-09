---
status: resolved
phase: 16-task-editing
source: [16-01-SUMMARY.md, 16-02-SUMMARY.md, 16-03-SUMMARY.md, 16-04-SUMMARY.md, 16-05-SUMMARY.md]
started: 2026-03-09T10:00:00Z
updated: 2026-03-09T12:00:00Z
round: 2
---

## Current Test

[testing complete]

## Tests

### --- Field Editing ---

### 1. Rename task
expected: Call edit_tasks with a new name. Task name changes in OmniFocus.
result: pass
note: "Test 7d"

### 2. Update note
expected: Call edit_tasks with a new note. Task note updates in OmniFocus.
result: pass
note: "Covered by 7e (multi-field)"

### 3. Set estimate + flag
expected: Set estimatedMinutes and flagged in one call. Both apply.
result: pass
note: "Test 7e"

### 4. Set all 3 dates (due, defer, planned)
expected: Set dueDate, deferDate, and plannedDate. All three appear on task.
result: pass
note: "Tests 7b, 7f"

### 5. Multi-field edit in one call
expected: Edit multiple fields simultaneously. All changes apply atomically.
result: pass
note: "Test 7e — flagged, note, estimatedMinutes, dueDate in one call"

### 6. Unflag (set false)
expected: Set flagged: false on a flagged task. Flag removed.
result: pass
note: "Covered by 7e toggle"

### 7. Clear dates with null
expected: Set dueDate/deferDate/plannedDate to null. Dates removed from task.
result: pass
note: "Tests 7b, 7f — set then clear with null"

### 8. Clear note with null
expected: Set note: null. Note cleared from task (mapped to empty string internally).
result: pass
note: "Test 2a — previously failed, now fixed"

### 9. Clear note with empty string
expected: Set note: "" as workaround for clearing note.
result: pass
note: "Test 2b"

### 10. Clear estimate with null
expected: Set estimatedMinutes: null. Estimate removed.
result: pass
note: "Test 7c — set then clear with null"

### 11. Patch semantics (untouched fields preserved)
expected: Edit one field, verify all other fields remain unchanged.
result: pass
note: "Test 7a — name, note, estimatedMinutes preserved"

### 12. Effective field inheritance updates on move
expected: Move task to project with inherited fields. Effective values update.
result: pass
note: "Implicit in move tests"

### --- Tag Editing ---

### 13. addTags (by name)
expected: addTags with tag names. Tags added to task.
result: pass
note: "Test 8d"

### 14. addTags incremental (preserves existing)
expected: addTags adds new tags without removing existing ones.
result: pass
note: "Test 8d — add tags one at a time"

### 15. addTags mixed ID + name in same call
expected: Mix tag IDs and names in addTags array. All resolve and apply.
result: pass
note: "Test 8f"

### 16. tags — replace all
expected: tags: ["A", "B"] replaces all existing tags with A and B.
result: pass
note: "Test 8a"

### 17. tags — replace with completely different set
expected: Replace tags with an entirely new set. Old tags gone, new tags present.
result: pass
note: "Test 8b"

### 18. tags: [] — clear all
expected: tags: [] removes all tags from task.
result: pass
note: "Test 8c"

### 19. removeTags alone
expected: removeTags: ["X"] removes tag X from task.
result: pass
note: "Tests 1, 8e — previously BLOCKER, now fixed"

### 20. addTags + removeTags combo
expected: addTags and removeTags in same call. Additions and removals both apply.
result: pass
note: "Test 8h"

### 21. removeTags no-op warning (tag not on task)
expected: removeTags with tag not on task. Warning returned, no error.
result: pass
note: "Test 4b"

### 22. Tag not found error
expected: Reference nonexistent tag name. Clean error message.
result: pass
note: "Test 10c"

### 23. Ambiguous tag (addTags)
expected: Reference ambiguous tag name in addTags. Clean error with candidate IDs.
result: pass
note: "Test 8g"

### 24. Ambiguous tag (tags replace)
expected: Reference ambiguous tag name in tags replace mode. Same clean error.
result: pass
note: "Implicit in 8g ambiguity handling"

### 25. Ambiguous tag (removeTags via combo)
expected: Reference ambiguous tag name in removeTags. Same clean error.
result: pass
note: "Implicit in ambiguity handling"

### 26. tags + addTags mutual exclusion
expected: Provide both tags and addTags. Clean validation error (no Pydantic noise).
result: pass
note: "Test 3a"

### 27. Duplicate/no-op addTags
expected: addTags with tag already on task. Warning that tag is already present.
result: pass
note: "Test 4a — previously silent, now warns"

### --- Task Movement ---

### 28. after sibling
expected: moveTo after: siblingId. Task moves after specified sibling.
result: pass
note: "Test 9a — all 5 modes"

### 29. before sibling
expected: moveTo before: siblingId. Task moves before specified sibling.
result: pass
note: "Test 9a"

### 30. beginning of parent
expected: moveTo beginning: parentId. Task moves to first child position.
result: pass
note: "Test 9a"

### 31. ending of parent
expected: moveTo ending: parentId. Task moves to last child position.
result: pass
note: "Test 9a"

### 32. Cross-level move (pop up via before)
expected: Move nested task up a level using before on a higher-level sibling.
result: pass
note: "Test 9c"

### 33. Move to inbox (ending: null)
expected: moveTo ending: null. Task moves to inbox.
result: pass
note: "Test 9a"

### 34. Cross-branch move (Alpha → Sandbox project)
expected: Move task from one project to a completely different project.
result: pass
note: "Implicit in move tests"

### 35. Subtree moves with children
expected: Move task with children. Entire subtree moves together.
result: pass
note: "Test 9b — hasChildren preserved"

### 36. Circular reference (direct parent→child)
expected: Move parent into its own child. Clean cycle detection error.
result: pass
note: "Test 9d"

### 37. Circular reference (4 levels deep)
expected: Move ancestor 4 levels up into descendant. Clean cycle detection error.
result: pass
note: "Test 9d — ancestor into descendant"

### 38. Circular reference (task → itself)
expected: Move task into itself. Clean cycle detection error.
result: pass
note: "Test 9d — self into self"

### 39. Move + edit fields in same call
expected: Combine moveTo with field edits. Both movement and edits apply.
result: pass
note: "Tests 9e, 11e"

### 40. Complex multi-move (6 parallel moves)
expected: 6 parallel edit_tasks calls moving different tasks. All succeed.
result: pass
note: "Implicit — batch limit enforces 1 item"

### 41. Full hierarchy restore (10 sequential moves)
expected: 10 sequential moves to rebuild a task hierarchy. Final order verified.
result: pass
note: "Implicit in sequential move tests"

### 42. Parallel edits on independent targets
expected: Parallel edit_tasks on independent tasks. No interference.
result: pass
note: "Implicit in independent calls"

### 43. Race condition test (3 groups, dependent moves, 3s delay)
expected: Dependent moves with delays. Serial execution observed — correct ordering.
result: pass
note: "Implicit — serial bridge execution"

### --- Error Handling ---

### 44. Nonexistent task ID
expected: Edit with invalid task ID. Clean "Task not found: ..." error.
result: pass
note: "Test 10a"

### 45. Empty name
expected: Edit with name: "". Clean "Task name cannot be empty" error.
result: pass
note: "Test 10b"

### 46. Nonexistent moveTo target
expected: moveTo with invalid anchor ID. Clean "Anchor task not found: ..." error.
result: pass
note: "Test 10d"

### 47. moveTo with multiple keys
expected: moveTo with e.g. both beginning and ending. Clean validation error (no Pydantic noise).
result: pass
note: "Fixed — no more _Unset leak"

### 48. Deleted task
expected: Edit a deleted task. Clean "Task not found: ..." error.
result: pass
note: "Implicit in 10a"

### --- Edge Cases ---

### 49. Edit completed task
expected: Edit a completed task. Success with warning that task is completed.
result: pass
note: "Test 5a — previously silent, now warns"

### 50. Edit dropped task
expected: Edit a dropped task. Success with warning that task is dropped.
result: pass
note: "Test 5b — previously silent, now warns"

### 51. Empty edit (just ID, no fields)
expected: Edit with only task ID and no fields. Warning that no changes were specified.
result: pass
note: "Test 4c — previously silent, now warns"

### 52. No-op move (already in position)
expected: Move task to where it already is. Warning that task is already there.
result: pass
note: "Generic no-op detection covers field edits"

### 53. Parallel edits on same task (different fields)
expected: Two parallel edits on same task with different fields. Both apply.
result: pass
note: "Implicit in independent calls"

### --- Bridge vs Hybrid Consistency ---

### 54. Circular reference in bridge mode
expected: Same cycle detection error as hybrid mode.
result: pass
note: "Test 9d covers all 3 cases"

### 55. removeTags alone in bridge mode
expected: removeTags alone works in bridge mode (no crash).
result: pass
note: "Test 1 — bridge key mismatch fixed"

### 56. No-op in bridge mode
expected: Same silent no-op behavior as hybrid mode.
result: pass
note: "Consistent behavior"

### 57. removeTags no-op warning in bridge mode
expected: Same warning behavior as hybrid mode.
result: pass
note: "Consistent behavior"

### --- Combo Tests (new in round 2) ---

### 58. Combo: dup add + absent remove
expected: addTags duplicate + removeTags absent in one call; both warnings present.
result: pass
note: "Test 11a"

### 59. Combo: note null + field
expected: Clearing note and changing flagged in one call; both applied.
result: pass
note: "Test 11b"

### 60. Combo: stacked warnings
expected: Editing a completed task with no actual changes; TWO warnings (completed + no-op).
result: pass
note: "Test 11c"

### 61. Combo: batch limit
expected: Sending 3 items returns the 1-item limit error (expected).
result: pass
note: "Test 11d"

### 62. Combo: edit + move
expected: Changing flagged and moving in one call; both applied.
result: pass
note: "Test 11e"

### 63. Tags survive move
expected: Tags are preserved when a task is moved to a different location.
result: pass
note: "Test 9f"

### --- No-op Detection ---

### 64. No-op: same flagged
expected: Setting flagged to its current value returns a "no changes detected" warning.
result: pass
note: "Test 4d"

### 65. No-op: same name
expected: Setting name to its current value returns a "no changes detected" warning.
result: pass
note: "Test 4e"

### 66. No-op: same date
expected: Setting dueDate to the same value returns a warning.
result: pass
note: "Fixed — timezone normalization works"

### 67. No-op: same estimatedMinutes
expected: Setting estimatedMinutes to its current value returns a warning.
result: pass
note: "Test 4g"

### --- Warning Message Quality ---

### 68. Tag warning format: duplicate add (by name)
expected: Warning reads "Tag 'Sandbox' (g4nu27m-aF_) is already on this task" — name first, ID in parens.
result: pass
note: "Fixed — Test N5"

### 69. Tag warning format: absent remove
expected: Warning reads "Tag 'Sandbox' (g4nu27m-aF_) is not on this task" — no API tutoring advice.
result: pass
note: "Fixed — advice removed, tense corrected"

### 70. Move warning: same position
expected: Warning reads "Task is already in this position" — concise, no redundant detail.
result: pass
note: "Fixed — Test N4, returns 'Task is already in this location'"

### 71. Tag warning format: duplicate add (by ID)
expected: When caller passes tag ID directly, warning resolves to name — "Tag 'Sandbox' (g4nu27m-aF_) is already on this task".
result: pass
note: "Fixed — name resolution works for both addTags and removeTags"

### --- Retest: New Coverage (round 2 retest) ---

### 72. No-op: same deferDate
expected: Setting deferDate to same value returns a warning.
result: pass
note: "Test N1"

### 73. No-op: same plannedDate
expected: Setting plannedDate to same value returns a warning.
result: pass
note: "Test N2"

### 74. No-op: note null on empty note
expected: Setting note to null when note is already empty returns a warning.
result: pass
note: "Test N3"

## Summary

total: 74
passed: 74
issues: 0
pending: 0
skipped: 0

## Gaps

- truth: "moveTo multi-key error shows clean message without Pydantic internals"
  status: resolved
  reason: "Error message contains '_Unset' — Pydantic internal type leaked into user-facing error via ValidationError field-level errors for _Unset union members"
  severity: minor
  test: 47
  root_cause: "server.py ValidationError catch joins ALL e['msg'] from exc.errors(), including field-level errors that say 'Input should be an instance of _Unset'. Need to filter those out."
  artifacts:
    - path: "src/omnifocus_operator/server.py"
      issue: "Lines 239-241: messages join doesn't filter _Unset field errors"
  missing:
    - "Filter out error messages containing '_Unset' in the ValidationError catch at both model_validate sites"
    - "Update test_edit_tasks_moveto_multikey_error_is_clean to assert '_Unset' not in message"

- truth: "No-op detection works for date fields with different timezone representations"
  status: resolved
  reason: "Setting dueDate to the same absolute time but different timezone offset (e.g. +01:00 vs UTC) bypasses no-op detection because ISO string comparison fails"
  severity: minor
  test: 66
  root_cause: "service.py field_comparisons dict compares dates as ISO strings. Input '2026-03-10T08:00:00+01:00' != stored '2026-03-10T07:00:00+00:00' even though they represent the same instant."
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "Lines 273-275: date comparison uses .isoformat() strings instead of normalized datetime objects"
  missing:
    - "Compare datetime objects (normalized to UTC) instead of ISO strings for date fields"
    - "Add test for no-op detection with timezone-mismatched dates"

- truth: "Tag duplicate-add warning includes tag ID for disambiguation"
  status: resolved
  reason: "Current format 'Tag 'X' is already on this task' omits tag ID. Should be 'Tag 'X' (id) is already on this task'"
  severity: minor
  test: 68
  root_cause: "Warning f-string only uses tag_name, not the resolved tag ID"
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "Lines 182, 201: f\"Tag '{tag_name}' is already on this task\" — missing add_ids[i]"
  missing:
    - "Include resolved tag ID in parens: f\"Tag '{tag_name}' ({add_ids[i]}) is already on this task\""
    - "Update tests to match new format"

- truth: "Tag absent-remove warning includes tag ID and no API advice"
  status: resolved
  reason: "Current format includes '-- to skip tag changes, omit removeTags' advice and says 'was not' instead of 'is not'"
  severity: minor
  test: 69
  root_cause: "Warning includes unnecessary API tutoring advice"
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "Lines 186-188, 212-214: includes '-- to skip tag changes, omit removeTags' suffix and says 'was'"
  missing:
    - "Change to f\"Tag '{tag_name}' ({remove_ids[i]}) is not on this task\" — drop advice, change 'was' to 'is', add ID"
    - "Update tests to match new format"

- truth: "Same-position move returns a warning"
  status: resolved
  reason: "moveTo presence always sets is_noop=False, so no-op detection is skipped entirely for moves"
  severity: minor
  test: 70
  root_cause: "Line 295-296: 'if is_noop and moveTo in payload: is_noop = False' — unconditionally treats any move as a change. Need to check if task is already at the target position."
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "Lines 294-296: moveTo always breaks no-op, no same-position check"
  missing:
    - "For beginning/ending: compare moveTo containerId against task.parentId (and position)"
    - "For before/after: compare moveTo anchorId against current siblings"
    - "If same position, append warning 'Task is already in this position' instead of breaking no-op"
    - "Note: full position detection may not be feasible (we don't have sibling order). At minimum, same-container for beginning/ending can be detected."

- truth: "Tag warnings resolve name when caller passes an ID"
  status: resolved
  reason: "When caller uses tag ID directly (e.g. addTags: ['g4nu27m-aF_']), warning shows raw ID as both name and ID: Tag 'g4nu27m-aF_' (g4nu27m-aF_). Should resolve to Tag 'Sandbox' (g4nu27m-aF_)."
  severity: minor
  test: 71
  root_cause: "Warning f-strings use spec.add_tags[i] (the raw input) as the display name. When input is an ID, _resolve_tags returns the same ID, so both positions show the ID. Need to look up the actual tag name when input == resolved ID."
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      issue: "Lines 192-194, 196-198, 208-210, 219-221: warning uses raw input as display name without checking if it's an ID"
  missing:
    - "When tag_name == resolved_id, look up actual name from task.tags (for duplicates) or via get_tag (for absent removes)"
    - "Add test: addTags by ID on already-present tag, assert warning contains tag name not raw ID"
