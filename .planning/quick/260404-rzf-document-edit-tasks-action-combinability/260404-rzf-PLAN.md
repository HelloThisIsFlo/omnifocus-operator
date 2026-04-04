---
phase: quick-260404-rzf
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/omnifocus_operator/agent_messages/descriptions.py
autonomous: true
requirements: [TODO-23]
must_haves:
  truths:
    - "EDIT_TASK_ACTIONS_DOC states that lifecycle, tag, and move actions can be combined freely"
    - "EDIT_TASKS_TOOL_DOC move line explains null clears the project (moves to inbox)"
  artifacts:
    - path: "src/omnifocus_operator/agent_messages/descriptions.py"
      provides: "Updated docstrings for combinability and null-inbox semantics"
      contains: "All three can be combined freely"
  key_links: []
---

<objective>
Update two docstrings in descriptions.py to document edit_tasks action combinability
and clarify null-inbox semantics for move actions.

Purpose: Agents currently lack guidance that lifecycle/tag/move actions can be combined
in a single call, and the null-inbox wording is inconsistent with patch-null semantics
used elsewhere.

Output: Two string literal changes in descriptions.py.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260404-rzf-document-edit-tasks-action-combinability/260404-rzf-CONTEXT.md
@src/omnifocus_operator/agent_messages/descriptions.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update combinability and null-inbox docstrings</name>
  <files>src/omnifocus_operator/agent_messages/descriptions.py</files>
  <action>
Two exact string replacements in descriptions.py:

1. Line 215 — EDIT_TASK_ACTIONS_DOC: Replace:
   "Lifecycle changes (complete/drop), tag edits, and task movement."
   With:
   "Lifecycle changes (complete/drop), tag edits, and task movement. All three can be combined freely in one call."

2. Lines 474-475 — EDIT_TASKS_TOOL_DOC move description: Replace:
   "actions.move: exactly one key must be set. ending/beginning with\nnull moves to inbox.\n"
   With:
   "actions.move: exactly one key must be set. ending/beginning with\nnull clears the project (moves task to inbox).\n"

No other changes. These are documentation-only edits to string constants.
  </action>
  <verify>
    <automated>uv run pytest tests/test_output_schema.py -x -q && uv run python -c "from omnifocus_operator.agent_messages.descriptions import EDIT_TASK_ACTIONS_DOC, EDIT_TASKS_TOOL_DOC; assert 'All three can be combined freely in one call' in EDIT_TASK_ACTIONS_DOC; assert 'null clears the project (moves task to inbox)' in EDIT_TASKS_TOOL_DOC; print('OK')"</automated>
  </verify>
  <done>
    - EDIT_TASK_ACTIONS_DOC contains combinability statement
    - EDIT_TASKS_TOOL_DOC move line uses "clears the project" wording
    - Output schema tests still pass
  </done>
</task>

</tasks>

<threat_model>
No trust boundaries crossed. Documentation-only change to string constants.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| (none) | — | — | — | No security-relevant changes |
</threat_model>

<verification>
- `uv run pytest tests/test_output_schema.py -x -q` passes (schema unchanged)
- Both strings contain the exact updated wording from CONTEXT.md
</verification>

<success_criteria>
- Two string literals updated with exact wording from locked decisions
- No functional code changes
- All existing tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/260404-rzf-document-edit-tasks-action-combinability/260404-rzf-01-SUMMARY.md`
</output>
