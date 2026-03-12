---
created: 2026-03-12T14:29:12.581Z
title: Fix same-container move by translating to moveBefore/moveAfter
area: service
files:
  - src/omnifocus_operator/service/
  - src/omnifocus_operator/bridge/bridge.js
---

## How This Fits in the Plan

- **Current state (v1.2):** Add a temporary warning to the edit_tasks response when a same-container move is detected, informing the agent that "move to beginning/ending within the same container may not reorder the task due to an OmniFocus API limitation."
- **v1.3 (filtering milestone):** Implement the query infrastructure needed to look up children of a container (filtering, list operations). This provides the ability to cheaply query "first/last child of container X."
- **After filtering ships:** Add a phase in v1.3 (or v1.4) to implement the service-layer translation described below. The fix depends on being able to query a container's children in order — which the filtering milestone delivers naturally.
- **Sequencing rationale:** Implementing the fix now would require either pulling the entire database (get_all) just to find one child ID, or building ad-hoc query infrastructure that gets redone properly in v1.3. Neither is worth it. The warning buys time, and the fix lands when the infrastructure supports it.

## Problem

When a task is already in a container and you call `moveTo beginning/ending` on that same container, the OmniFocus API silently does nothing. The task stays in its current position — no error, no reordering.

This was manually verified: `moveBefore`/`moveAfter` within the same container DOES work (confirmed 2026-03-12).

Previously thought to subsume the "Move no-op warning" todo, but they're separate concerns: this fixes the operation; that fixes the warning accuracy.

## Solution

**Service-layer translation** — express the same intent through equivalent API calls that work:

- **"Move to beginning of X"** -> find X's first child -> call **"move before [first child]"**
- **"Move to ending of X"** -> find X's last child -> call **"move after [last child]"**

### Scope: always-when-children-exist (not just same-container)

Apply this translation whenever the target container has at least one child, regardless of whether the task is already in that container. Reasons:
- One code path instead of two (no need to detect "is this task already in the target?")
- Semantically identical from the caller's perspective
- No edge-case branches for same vs. different container

### Edge cases

- **Container has no children** -> no translation needed. `moveTo beginning/ending` on an empty container works fine (the task becomes the only child).
- **Batch moves** -> each sequential move needs a re-query to find the updated first/last child. Acceptable with SQLite cache (~46ms), but worth noting. Batch edit isn't the immediate concern.

### Implementation location

Service layer (`edit_tasks` flow). The bridge stays dumb — it receives `moveBefore`/`moveAfter` calls, which it already supports. No bridge changes needed.

## Related

- **[Add position field to expose child task ordering](2026-03-08-add-position-field-to-expose-child-task-ordering.md)** — the position feature and this fix share a dependency on ordering data. Position field is a read-side feature (agents see ordering); this is a write-side fix (moves actually reorder). Consider implementing in the same milestone phase since they touch similar infrastructure.
- **[Move no-op warning check ordinal position not just container](2026-03-09-move-no-op-warning-check-ordinal-position-not-just-container.md)** — separate concern: this todo fixes the move operation; that one fixes the warning accuracy (warns when it shouldn't). Both need ordering data.
