---
created: 2026-04-14T18:10:03.401Z
title: Compute true inherited fields by walking parent hierarchy
area: service, models
scope: phase (not quick task — model surgery + multi-layer changes)
files:
  - src/omnifocus_operator/models/common.py
  - src/omnifocus_operator/models/task.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/repository/bridge_only/adapter.py
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
  - src/omnifocus_operator/contracts/use_cases/list/projects.py
  - .planning/phases/53-response-shaping/53-UAT.md
---

## Problem

After renaming `effective*` to `inherited*` (Phase 53), OmniFocus's self-echo behavior is semantically wrong: a task with `plannedDate` shows `inheritedPlannedDate` with the same value even when no parent sets a planned date. "Inherited" implies "came from above" but OmniFocus always fills `effectiveX` with the resolved value regardless of source.

A heuristic approach (strip `inheritedX` when equal to `X`) was considered but rejected: booleans like `flagged` have high coincidental equality between parent and child, making the heuristic unreliable.

## Solution

Two parts:

### Part A: Task-side — parent hierarchy walk

Add a method in `DomainLogic` (service layer) that computes true inheritance for tasks:

1. Calls `get_all()` internally to build a `task_map: dict[id, Task]` (cached, so cheap)
2. Takes the tasks to process as input (full list, filtered list, or single task)
3. For each task, walks `parent.task.id` up the chain checking whether any ancestor sets the corresponding direct field
4. If NO ancestor sets the field → strip the `inherited*` field (it's a self-echo)
5. If any ancestor sets it → keep (truly inherited)

**Field pairs checked:**
- `flagged` ↔ `inheritedFlagged` — ancestor sets it = ancestor has `flagged=True`
- `dueDate` ↔ `inheritedDueDate` — ancestor sets it = ancestor has `dueDate` not null
- `deferDate` ↔ `inheritedDeferDate` — same pattern
- `plannedDate` ↔ `inheritedPlannedDate` — same pattern
- `dropDate` ↔ `inheritedDropDate` — same pattern
- `completionDate` ↔ `inheritedCompletionDate` — same pattern

**Performance**: Build task_map once O(n), walk per task O(depth). OmniFocus hierarchies are shallow (2-5 levels), so total is O(n × avg_depth) ≈ O(n).

**Call sites**: Service layer calls this for `get_all_data()`, `get_task()`, `list_tasks()`. The DomainLogic method owns the `get_all()` call — callers just pass their tasks.

### Part B: Project-side — remove inherited fields entirely

Folders (project parents) have no dates or flags. Therefore `inherited*` fields on projects are structurally always self-echoes — no hierarchy walk can ever find a parent that sets them.

**Decision: move all inherited fields from `ActionableEntity` to `Task` only.**

This means:
- Model change: move `inherited_flagged`, `inherited_due_date`, `inherited_defer_date`, `inherited_planned_date`, `inherited_drop_date` from `ActionableEntity` to `Task` (alongside existing `inherited_completion_date`)
- Hybrid path (`_map_project_row`): stop mapping `effective*` → `inherited_*` for projects
- Bridge adapter: stop renaming `effective*` → `inherited*` for projects in `adapt_snapshot`
- Field groups / default fields for `list_projects`: remove inherited fields
- Tool descriptions for `list_projects`: remove inherited field references
- Output schema tests: update for new project shape

**Golden master snapshots will NOT change** — the bridge still returns `effective*` values; we just stop consuming them for projects.

## Decisions log (from discussion)

- **Architecture**: Service layer (DomainLogic), following cycle detection precedent
- **Performance**: Single `get_all()` + task_map, not per-task `get_all()`
- **Projects**: Always strip (model surgery), not walk — folders can't set dates/flags
- **Scope**: Promoted from quick task to phase — model changes cascade through multiple layers

## Origin

Discovered during Phase 53 UAT (Gap 1, test 1). Documented in `.planning/phases/53-response-shaping/53-UAT.md`.
