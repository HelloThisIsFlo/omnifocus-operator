---
status: investigating
trigger: "note: null rejected by OmniFocus (ISSUE-2)"
created: 2026-03-08T00:00:00Z
updated: 2026-03-08T00:00:00Z
---

## Current Focus

hypothesis: Bridge passes null directly to OmniFocus for note field; OmniFocus requires string (empty string = no note)
test: Trace note:null flow through service -> bridge
expecting: null is passed verbatim without mapping to ""
next_action: confirm flow in service.py and bridge.js

## Symptoms

expected: Setting note:null in edit_tasks clears the note
actual: OmniFocus error "The property 'note' must be set to a non-null value"
errors: "The property 'note' must be set to a non-null value"
reproduction: Call edit_tasks with note: null
started: First use of edit_tasks with note clearing

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-03-08T00:01:00Z
  checked: service.py edit_task method (lines 119-132)
  found: Simple fields including "note" are passed directly to payload without transformation. `payload[key] = value` where value can be None.
  implication: Service layer does NOT map null -> "" for note. Passes None directly.

- timestamp: 2026-03-08T00:02:00Z
  checked: bridge.js handleEditTask (line 258)
  found: `if (params.hasOwnProperty("note")) task.note = params.note;` -- sets note directly from params, no null-to-empty mapping
  implication: When service sends note:null, bridge sets task.note = null, which OmniFocus rejects.

- timestamp: 2026-03-08T00:03:00Z
  checked: bridge.js handleAddTask (line 235)
  found: Same pattern: `if (params.hasOwnProperty("note")) task.note = params.note;` -- also vulnerable if null passed
  implication: add_task has same potential issue, though TaskCreateSpec.note defaults to None (only sent if explicitly set)

- timestamp: 2026-03-08T00:04:00Z
  checked: models/write.py TaskEditSpec (line 159)
  found: `note: str | None | _Unset = UNSET` -- None is a valid value, meaning "clear the note"
  implication: The model correctly allows None to mean "clear". The bug is that null isn't mapped to "" before reaching OmniFocus.

## Resolution

root_cause: OmniFocus API requires note to be a string (empty string = no note). When user sets note:null (meaning "clear the note"), the service passes None to the bridge payload, and the bridge sets task.note = null directly. OmniFocus rejects this with "The property 'note' must be set to a non-null value."
fix: Map null -> "" for the note field. Best location: bridge.js (line 258), since the bridge is the OmniFocus API boundary.
verification:
files_changed: []
