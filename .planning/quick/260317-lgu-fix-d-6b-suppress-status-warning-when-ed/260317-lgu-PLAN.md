---
phase: quick-260317-lgu
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/omnifocus_operator/service.py
  - tests/test_service.py
autonomous: true
requirements: [D-6b]

must_haves:
  truths:
    - "No-op edit on a completed task returns only EDIT_NO_CHANGES_DETECTED, not the status warning"
    - "No-op edit on a dropped task returns only EDIT_NO_CHANGES_DETECTED, not the status warning"
    - "Non-no-op edit on a completed/dropped task still returns the status warning as before"
  artifacts:
    - path: "src/omnifocus_operator/service.py"
      provides: "No-op detection that clears status warning"
      contains: "EDIT_NO_CHANGES_DETECTED"
    - path: "tests/test_service.py"
      provides: "Updated tests asserting no-op priority over status warning"
      contains: "test_noop_priority_completed"
  key_links:
    - from: "src/omnifocus_operator/service.py"
      to: "warnings.EDIT_NO_CHANGES_DETECTED"
      via: "is_noop branch clears warnings before appending no-op warning"
      pattern: "warnings\\.clear.*EDIT_NO_CHANGES_DETECTED|warnings = \\[EDIT_NO_CHANGES_DETECTED\\]"
---

<objective>
Fix D-6b: When edit_tasks receives a no-op field edit on a completed/dropped task, suppress the status warning and return only the no-op warning.

Purpose: The status warning says "your changes were applied" which is misleading when no changes were actually applied. The no-op warning is the correct signal.
Output: Updated service.py no-op branch + updated tests
</objective>

<execution_context>
@/Users/flo/.claude/get-shit-done/workflows/execute-plan.md
@/Users/flo/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/omnifocus_operator/service.py
@src/omnifocus_operator/warnings.py
@tests/test_service.py

<interfaces>
From src/omnifocus_operator/warnings.py:
```python
EDIT_COMPLETED_TASK = (
    "This task is {status} -- your changes were applied, "
    "but please confirm with the user that they intended to edit a {status} task."
)
EDIT_NO_CHANGES_DETECTED = (
    "No changes detected -- the task already has these values. "
    "If you don't want to change a field, omit it from the request."
)
```

From src/omnifocus_operator/service.py (lines 364-377, current no-op branch):
```python
if is_noop:
    if not warnings:
        # Genuine field-level no-op -- add generic warning
        warnings.append(EDIT_NO_CHANGES_DETECTED)
    # Return early -- action-specific warnings already present, or generic added
    logger.debug(...)
    return TaskEditResult(success=True, id=spec.id, name=task.name, warnings=warnings)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Update tests to assert no-op priority, then fix service.py</name>
  <files>tests/test_service.py, src/omnifocus_operator/service.py</files>
  <behavior>
    - test_noop_priority_completed: Editing a completed task with same values returns ONLY EDIT_NO_CHANGES_DETECTED (no status warning)
    - test_noop_priority_dropped: Editing a dropped task with same values returns ONLY EDIT_NO_CHANGES_DETECTED (no status warning)
    - Existing test_edit_completed_task_warning (non-no-op edit on completed task) still passes with status warning present
  </behavior>
  <action>
**Tests (RED):**
1. In `tests/test_service.py`, rename `test_stacked_warnings_completed_noop` to `test_noop_priority_completed` and update:
   - Docstring: "No-op edit on completed task returns only no-op warning, not status warning."
   - Assert `EDIT_NO_CHANGES_DETECTED` IS in warnings (flip the current assertion)
   - Assert NO "completed" status warning in warnings
   - Assert `len(result.warnings) == 1`
2. Rename `test_stacked_warnings_dropped_noop` to `test_noop_priority_dropped` and update similarly:
   - Docstring: "No-op edit on dropped task returns only no-op warning, not status warning."
   - Assert `EDIT_NO_CHANGES_DETECTED` IS in warnings
   - Assert NO "dropped" status warning in warnings
   - Assert `len(result.warnings) == 1`
3. Run tests -- both MUST fail (RED).

**Service fix (GREEN):**
4. In `src/omnifocus_operator/service.py`, change the `if is_noop:` block (around line 364) to always clear warnings and add the no-op warning:
   ```python
   if is_noop:
       # No-op takes priority -- clear any status warnings since "changes were applied" is misleading
       warnings.clear()
       warnings.append(EDIT_NO_CHANGES_DETECTED)
       logger.debug(...)
       return TaskEditResult(...)
   ```
5. Run tests -- both MUST pass (GREEN), and all other edit tests must still pass.
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && python -m pytest tests/test_service.py -x -q -k "test_noop_priority or test_edit_completed_task_warning or test_edit_dropped_task_warning" 2>&1 | tail -20</automated>
  </verify>
  <done>No-op edits on completed/dropped tasks return only EDIT_NO_CHANGES_DETECTED. Non-no-op edits on completed/dropped tasks still return the status warning. All existing tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Full test suite verification</name>
  <files></files>
  <action>
Run the full test suite to confirm no regressions. Also run mypy for type checking.
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && python -m pytest tests/ -x -q 2>&1 | tail -10 && python -m mypy src/ --no-error-summary 2>&1 | tail -5</automated>
  </verify>
  <done>All 534+ tests pass. mypy reports no errors.</done>
</task>

</tasks>

<verification>
- No-op edit on completed task: only "No changes detected" warning, no "your changes were applied"
- No-op edit on dropped task: only "No changes detected" warning, no "your changes were applied"
- Non-no-op edit on completed/dropped task: status warning still present
- Full test suite passes with no regressions
</verification>

<success_criteria>
- `test_noop_priority_completed` and `test_noop_priority_dropped` pass with correct assertions
- All existing edit_tasks tests pass unchanged
- Full test suite green, mypy clean
</success_criteria>

<output>
After completion, create `.planning/quick/260317-lgu-fix-d-6b-suppress-status-warning-when-ed/260317-lgu-SUMMARY.md`
</output>
