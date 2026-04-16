---
status: resolved
trigger: "repetition-end-date-past-warning-missing-on-add"
created: 2026-04-16T00:00:00Z
updated: 2026-04-16T00:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: CONFIRMED — _AddTaskPipeline._process_repetition_rule does not call check_repetition_warnings (which fires REPETITION_END_DATE_PAST), unlike _EditTaskPipeline._normalize_and_warn_repetition which does.
test: code reading — traced both pipelines completely
expecting: adding one call to check_repetition_warnings (or equivalent inline check) in _process_repetition_rule will fix the issue
next_action: await human verification that the warning appears in real add_tasks call

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: When adding a task with a repetition rule whose end date is in the past (e.g., 2020-01-01), the response should include a warning: "The end date {date} is in the past -- the repetition rule was set, but no future occurrences will be generated. Was this intentional?"
actual: Task is created successfully with status "success" but warnings is null — no REPETITION_END_DATE_PAST warning returned.
errors: No errors — the task creates fine, the warning is simply missing.
reproduction: Call add_tasks with payload containing repetitionRule with end.date set to a past date like "2020-01-01". The task gets created but no warning is emitted.
started: Discovered during UAT Test 2 of the current milestone. The warning logic exists in warnings.py but appears to not be called from the add path.

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-16
  checked: service/domain.py:548-564 — check_repetition_warnings method
  found: Method checks only the end condition (isinstance(end, EndByDate) and end.date < today). The `task` parameter is declared but unused in current impl.
  implication: The warning logic is correct and available — just not called from add path.

- timestamp: 2026-04-16
  checked: service/service.py:592-629 — _AddTaskPipeline._process_repetition_rule
  found: Calls normalize_empty_specialization_fields, check_anchor_date_warning, check_from_completion_byday_warning — but NOT check_repetition_warnings.
  implication: This is the exact gap causing the bug.

- timestamp: 2026-04-16
  checked: service/service.py:837-869 — _EditTaskPipeline._normalize_and_warn_repetition
  found: Calls check_repetition_warnings(end=self._rr_end, task=self._task) at line 847.
  implication: Edit path is correct. Add path is missing the symmetric call.

- timestamp: 2026-04-16
  checked: tests/test_service.py — search for PAST/end_date_past in add test section
  found: No existing test for REPETITION_END_DATE_PAST in add_task tests.
  implication: The gap was never caught because there's no regression test for this case on add.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: _AddTaskPipeline._process_repetition_rule does not call self._domain.check_repetition_warnings() after converting the end condition. The edit path (_EditTaskPipeline._normalize_and_warn_repetition) does call it. The omission means no REPETITION_END_DATE_PAST warning is ever emitted when creating a task with a past end date.
fix: In _process_repetition_rule, after all other warning checks, add a call to self._domain.check_repetition_warnings(end=self._end_condition). The `task` parameter on check_repetition_warnings is unused for the end-date check, so we need to either make it optional or call the check inline. Making `task` optional (default None) is cleaner and keeps the API symmetric.
verification: 2 new regression tests pass (test_end_date_in_past_warns, test_end_date_in_future_no_past_warn). Full suite: 2151 passed, 97% coverage. Output schema tests: 34 passed.
files_changed: [src/omnifocus_operator/service/service.py, src/omnifocus_operator/service/domain.py, tests/test_service.py]
