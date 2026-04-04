# Quick Task 260404-rzf: Document edit_tasks action combinability and null-inbox semantics - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Task Boundary

Two documentation fixes in `src/omnifocus_operator/agent_messages/descriptions.py`:
1. Add cross-group combinability statement for edit_tasks actions
2. Clarify null-inbox semantics in move action description

</domain>

<decisions>
## Implementation Decisions

### Combinability scope
- Cross-group only. Intra-group constraints (replace vs add/remove, complete vs drop) are already documented per-group — no need to repeat.

### Null-inbox wording
- Reframe as clearing the project assignment — aligns with patch-null semantics used everywhere else in edit_tasks.
- Long term, inbox will become a first-class value (todo #16), but this is the right bridge for now.

### Placement
- Combinability statement goes in `EDIT_TASK_ACTIONS_DOC` (line 215), NOT in `EDIT_TASKS_TOOL_DOC`.
- Move wording change goes in `EDIT_TASKS_TOOL_DOC` (line 474).

</decisions>

<specifics>
## Exact Wording (locked)

**EDIT_TASK_ACTIONS_DOC** — replace current:
```
"Lifecycle changes (complete/drop), tag edits, and task movement."
```
With:
```
"Lifecycle changes (complete/drop), tag edits, and task movement. All three can be combined freely in one call."
```

**EDIT_TASKS_TOOL_DOC move line** — replace current:
```
"actions.move: exactly one key must be set. ending/beginning with null moves to inbox."
```
With:
```
"actions.move: exactly one key must be set. ending/beginning with null clears the project (moves task to inbox)."
```

</specifics>
