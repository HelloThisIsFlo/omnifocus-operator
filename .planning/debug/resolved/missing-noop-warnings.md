---
status: resolved
trigger: "Missing no-op warnings (ISSUE-4, ISSUE-5, ISSUE-6)"
created: 2026-03-08T00:00:00Z
updated: 2026-03-08T00:00:00Z
---

## Current Focus

hypothesis: All three issues are missing warning logic in service.py edit_task method
test: Code analysis -- locate insertion points relative to existing removeTags pattern
expecting: Straightforward additions following existing pattern
next_action: Return diagnosis

## Symptoms

expected: Warnings returned for no-op edits (addTags duplicate, completed/dropped task edit, empty edit, no-op move)
actual: Silent no-ops -- operation succeeds but user gets no indication nothing changed
errors: None (silent success is the problem)
reproduction: Call edit_task with any of the no-op scenarios
started: Always -- warnings never implemented for these cases

## Eliminated

(none -- code analysis was sufficient)

## Evidence

- timestamp: 2026-03-08
  checked: service.py lines 146-194 -- existing removeTags warning pattern
  found: Pattern is clear -- resolve tag IDs, compare against task.tags current set, append warning string to `warnings` list
  implication: Same pattern works for addTags (ISSUE-4)

- timestamp: 2026-03-08
  checked: service.py lines 108-109 -- task lookup at start of edit_task
  found: Task object is fetched and has `availability` field (from ActionableEntity). Availability enum has COMPLETED and DROPPED values.
  implication: ISSUE-5 is trivial -- check task.availability after fetch, before any processing

- timestamp: 2026-03-08
  checked: service.py lines 119-228 -- payload construction
  found: Payload starts as `{"id": spec.id}` and fields are added only when not UNSET. After all processing, if payload is still just `{"id": spec.id}`, that's an empty edit.
  implication: ISSUE-6 (empty edit) can be detected by checking `len(payload) == 1` after step 5, before delegation

- timestamp: 2026-03-08
  checked: service.py lines 196-228 -- moveTo handling
  found: moveTo resolves container/anchor but does NOT check if task is already in that position. The service layer doesn't know the task's current position siblings or ordering.
  implication: No-op move detection would require knowing current parent + sibling order. Task model has `parent` (ParentRef with type+id) so same-container is detectable, but same-position-within-container is NOT (no sibling order info).

## Resolution

root_cause: Warning logic was only implemented for removeTags. The addTags, completed/dropped status, and empty-edit checks were never added.

fix_direction: |
  All fixes go in `service.py` `edit_task` method. Here are the exact insertion points:

  **ISSUE-4 (addTags already present):**
  - In the `has_add and has_remove` branch (line 158-174): after resolving add_ids, check each against `current_tag_ids`. Already have `current_tag_ids` built on line 165.
  - In the `has_add` branch (line 175-179): same check but need to build `current_tag_ids` (currently not built in this branch).
  - Warning text pattern: `"Tag '{tag_name}' is already on this task -- to skip tag changes, omit addTags"`

  **ISSUE-5 (completed/dropped task edit):**
  - Insert after task existence check (line 112), before name validation (line 114).
  - Check: `if task.availability in (Availability.COMPLETED, Availability.DROPPED):`
  - Append warning like: `"Task is {task.availability.value} -- edits may not behave as expected"`
  - Need to import Availability or use string comparison.
  - NOTE: This should be a warning, not an error -- OmniFocus does allow editing completed tasks.

  **ISSUE-6 (empty edit):**
  - Insert after step 5 (moveTo handling, line 228), before step 6 (delegation, line 231).
  - Check: `if len(payload) == 1 and not warnings:` (payload only has "id")
  - But also need to account for tag operations (tagMode is in payload if tags were specified).
  - Better check: `if len(payload) == 1:` means truly nothing to change.
  - Return early with `TaskEditResult(success=True, id=task.id, name=task.name, warnings=["No fields to change -- edit was a no-op"])`

  **ISSUE-6 (no-op move):**
  - Partial detection possible: if moveTo uses beginning/ending with a containerId, can compare against `task.parent.id`.
  - Same-container but different position (beginning vs ending) is still a meaningful move, so only warn if container matches AND position type matches current placement.
  - Full sibling-order detection NOT feasible at service layer (no ordering info in Task model).
  - Recommendation: Skip no-op move warning for now, or limit to "task is already in this container" as a soft warning.

verification: N/A (diagnosis only)
files_changed: []
