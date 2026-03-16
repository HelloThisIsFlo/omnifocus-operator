# Phase 17: Task Lifecycle - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Agents can change task lifecycle state -- completing and dropping tasks via `edit_tasks`. Uses the `actions.lifecycle` slot reserved in Phase 16.1. Two lifecycle values: `complete` and `drop`. Reactivation (reopen) is deferred -- no practical use case for agents.

</domain>

<decisions>
## Implementation Decisions

### Lifecycle values
- Two string values: `"complete"` and `"drop"` -- imperative verbs (commands, not state descriptions)
- `"reopen"` deferred entirely -- `markIncomplete()` is too niche; user can Cmd+Z in OmniFocus
- The reserved `lifecycle: str` field on `ActionsSpec` becomes a validated enum of these two values
- `lifecycle` field type changes from `str` to a constrained type (Literal or enum) during implementation

### Drop behavior
- Always call `drop(false)` regardless of task type -- for non-repeating tasks, `drop(false)` is identical to `drop(true)`
- Non-repeating task: permanently dropped, no special warning
- Repeating task: skips this occurrence only, warning: "Repeating task -- this occurrence was skipped"
- No `"skip"` value -- `drop` handles both cases contextually
- Detection: check `task.repetition_rule` before bridge call to determine if warning is needed

### Repeating task handling
- `"complete"` on repeating task: completes this occurrence, next occurrence created automatically by OmniFocus
- Warning on complete: "Repeating task -- this occurrence completed, next occurrence created"
- `"drop"` on repeating task: skips this occurrence via `drop(false)`, next occurrence created
- Warning on drop: "Repeating task -- this occurrence was skipped"
- Detection via `repetition_rule` field on task snapshot, checked before bridge call

### No-op detection
- Check task availability before calling bridge -- if already in target state, skip bridge call entirely
- Completing an already-completed task: no-op warning, e.g. "Task is already complete -- nothing changed. Omit actions.lifecycle to skip"
- Dropping an already-dropped task: no-op warning, e.g. "Task is already dropped -- nothing changed. Omit actions.lifecycle to skip"
- No-op warnings skip the bridge call entirely (consistent with field/tag/move no-ops)

### Cross-state transitions
- Completing a dropped task: allowed (OmniJS supports it), but with warning
- Dropping a completed task: allowed (OmniJS supports it), but with warning
- Cross-state warning format: "Task was already [prior state] -- lifecycle action applied, task is now [new state]. Confirm with user that this was intended"
- Key: warning must clearly distinguish prior state from new state to avoid ambiguity

### Warning clarity principles
- No-op warnings: "nothing changed" + hint to omit the field
- Cross-state warnings: "was already X, now Y" + "confirm with user"
- Repeating task warnings: describe what happened to this occurrence + mention next occurrence
- Warnings can stack (e.g., cross-state + repeating task)

### Bridge interface
- New bridge.js handler for lifecycle actions (complete and drop)
- Bridge receives: `{ lifecycle: "complete" | "drop" }` in the edit payload
- Bridge calls `task.markComplete()` or `task.drop(false)` accordingly
- No new bridge command -- lifecycle is part of edit_task, not a separate operation

### Claude's Discretion
- Exact bridge payload shape for lifecycle (inline with existing edit payload vs separate field)
- Whether lifecycle enum is a Python `Literal["complete", "drop"]` or a dedicated `LifecycleAction` enum
- Exact warning message wording (principles above, but final copy is flexible)
- How to structure the service layer lifecycle logic (inline in edit_task vs helper method)
- Test organization for lifecycle tests

</decisions>

<specifics>
## Specific Ideas

- Lifecycle values are imperative verbs (commands) while read model uses state adjectives (completed, dropped) -- deliberate CQRS distinction
- `drop(false)` universally simplifies the bridge -- one code path, not two
- Warning pattern mirrors the educational approach from Phase 16: teach agents correct usage through response feedback

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ActionsSpec` (`models/write.py`): already has `lifecycle: str | _Unset = UNSET` -- needs type narrowing to enum/Literal
- `UNSET` sentinel pattern: reused for lifecycle field (omit = no lifecycle change)
- `_compute_tag_diff` (`service.py`): pattern for pre-bridge computation and warning generation
- Existing status warning in service: warns when editing completed/dropped tasks (line ~155-156) -- keep as-is

### Established Patterns
- No-op detection before bridge call (field comparisons, tag diff, same-container move)
- Warning stacking via `warnings.append()` (fixed in Phase 16.2)
- `task.repetition_rule` available on snapshot for repeating task detection
- `task.availability` available on snapshot for current lifecycle state check

### Integration Points
- `models/write.py`: narrow `lifecycle` type on `ActionsSpec` from `str` to enum/Literal
- `service.py`: replace "not yet implemented" rejection with actual lifecycle logic
- `bridge/bridge.js`: add lifecycle handling to `handleEditTask`
- `repository/`: pass lifecycle field through to bridge in edit payload
- Tests: lifecycle-specific test cases for service, bridge, server layers

</code_context>

<deferred>
## Deferred Ideas

- `"reopen"` / `"reactivate"` lifecycle action -- deferred, no practical agent use case
- `"skip"` as explicit value for repeating tasks -- deferred, `drop` handles contextually
- `delete_tasks` tool -- v1.4, separate from lifecycle
- Repeating task "drop all occurrences" -- philosophically, permanent deletion belongs to user discretion

</deferred>

---

*Phase: 17-task-lifecycle*
*Context gathered: 2026-03-11*
