---
created: 2026-03-22T14:24:25.129Z
title: Expand golden master with 18 additional scenarios
area: testing
files:
  - tests/golden_master/snapshots
  - tests/golden_master/normalize.py
  - tests/test_bridge_contract.py
  - uat/capture_golden_master.py
---

## Problem

Current golden master has 17 scenarios (4 add, 13 edit). Several important code paths in bridge.js have zero coverage:

- **Null/clear semantics**: Scenarios set fields but never clear them (note, flagged, estimatedMinutes, plannedDate). Null-means-clear is untested at the bridge contract level.
- **note: null vs note: ""**: OmniFocus may treat these differently. UAT edit-ops tests both, golden master doesn't.
- **Move positions**: All moves use `"ending"`. `"beginning"`, `"before"`, `"after"` are completely different bridge.js code paths (anchor-based moves use `Task.byIdentifier`).
- **Project-to-project move**: Only inbox-to-project and project-to-inbox are covered. Requires second test project in setup.
- **Task-as-parent in moveTo**: All moveTo scenarios target a project or inbox, never a task container.
- **Combined operations**: No scenario combines field edits + move, or field edits + lifecycle, in a single call.
- **Add task max payload**: No scenario combines parent + tags + all fields in one add_task.
- **Tag edge cases**: No coverage for adding already-present tags or removing absent tags (dedup/no-op behavior).
- **Status transitions via deferDate**: No scenario transitions Available→Blocked or Blocked→Available via deferDate edit on an existing task.

## Proposed Scenarios

### Clearing/unsetting fields (21-25)
- 21: Clear note (note: null)
- 22: Clear note with empty string (note: "")
- 23: Unflag a task (flagged: false on a flagged task)
- 24: Clear estimated minutes (estimatedMinutes: null)
- 25: Set/clear plannedDate independently

### Move operations (26-30)
- 26: Move to beginning (position: "beginning")
- 27: Move after anchor task (position: "after", anchorId)
- 28: Move before anchor task (position: "before", anchorId)
- 29: Move between projects (project A → project B) — needs second test project
- 30: Move task to become sub-task of another task

### Combined operations (31-32)
- 31: Edit fields + move in same call
- 32: Edit fields + lifecycle in same call

### Add task combinations (33-34)
- 33: Add task with tags AND parent
- 34: Add task maximum payload (parent + tags + all dates + flagged + note + estimatedMinutes)

### Tag edge cases (35-36)
- 35: Add duplicate tag (already-present tag)
- 36: Remove absent tag (tag not on task)

### Status transitions (37-38)
- 37: Set future deferDate on available task (→ Blocked)
- 38: Clear deferDate on blocked task (→ Available)

## Solution

1. Add scenarios 21-38 to `uat/capture_golden_master.py`
2. Re-run capture against live OmniFocus
3. Contract test (`test_bridge_contract.py`) picks up new snapshots automatically
4. May need second test project in setup for scenario 29
5. Anchor-based moves (27-28) need careful ID tracking for the anchor task
