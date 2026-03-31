---
status: resolved
trigger: "No-op repetition rule warning doesn't fire when other field changes are present in edit_tasks"
created: 2026-03-28T00:00:00Z
updated: 2026-03-28T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - repetition rule no-op warning only generated inside _all_fields_match, which short-circuits when other fields differ
test: traced full pipeline flow for both cases
expecting: n/a - root cause confirmed
next_action: return diagnosis

## Symptoms

expected: When editing a task with an identical repetition rule AND other field changes (like renaming), the no-op repetition rule warning should fire
actual: warnings is null when identical rule is sent WITH other field changes; warning fires correctly when identical rule is sent WITHOUT other changes
errors: no error - silent warning suppression
reproduction: edit_tasks with identical repetition rule + name change => no warning; edit_tasks with identical repetition rule alone => warning fires
started: unknown

## Eliminated

## Evidence

- timestamp: 2026-03-28T00:01:00Z
  checked: _EditTaskPipeline.execute flow in service.py (line 230-246)
  found: _apply_repetition_rule (step 6) does NOT do no-op detection. It only adds on_dates and check_repetition_warnings.
  implication: The REPETITION_NO_OP warning is never generated during rule processing itself.

- timestamp: 2026-03-28T00:02:00Z
  checked: _all_fields_match in domain.py (line 462-527)
  found: Field comparisons at lines 489-496 return False immediately when any field differs (e.g., name change). The repetition_rule check at line 507-511 is ONLY reached if ALL preceding field checks pass.
  implication: When other fields genuinely change, _all_fields_match returns False before reaching the repetition rule no-op check. The REPETITION_NO_OP warning (line 511) is never appended.

- timestamp: 2026-03-28T00:03:00Z
  checked: _delegate in service.py (line 455-463)
  found: warnings=self._all_warnings or None. self._all_warnings is built in _build_payload from lifecycle_warns + status_warns + repetition_warns + tag_warns. But repetition_warns only contains on_dates and check_repetition_warnings -- never REPETITION_NO_OP.
  implication: Even when the edit proceeds to _delegate (non-noop path), the repetition no-op warning is absent from the result.

- timestamp: 2026-03-28T00:04:00Z
  checked: test_noop_same_rule in test_service.py (line 1944)
  found: Test only sends identical repetition_rule WITHOUT other field changes. No test combines identical rule + different name.
  implication: Missing test coverage for this case.

## Resolution

root_cause: REPETITION_NO_OP warning is only generated inside _all_fields_match (domain.py line 511), which is the whole-edit no-op detection path. When other fields genuinely change (e.g., name), _all_fields_match returns False at line 496 before ever reaching the repetition_rule check at line 507. The warning is never appended, so it's absent from the result. The _apply_repetition_rule step (service.py line 290) does NOT perform its own no-op detection -- it processes the rule unconditionally and sends it to the repo even when identical.
fix: Move repetition rule no-op detection into _apply_repetition_rule itself. After building the payload (line 377), compare it against the existing rule (reuse _repetition_rule_matches logic). If it matches, append REPETITION_NO_OP to self._repetition_warns and skip setting the payload (set self._repetition_rule_payload = None). This way the warning fires regardless of whether other fields change, AND the redundant bridge call is avoided. The _all_fields_match check at line 507-511 can then be simplified or kept as a fallback.
verification:
files_changed: []
