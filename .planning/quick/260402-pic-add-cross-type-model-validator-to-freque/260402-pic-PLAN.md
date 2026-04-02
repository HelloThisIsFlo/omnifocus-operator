---
phase: quick-260402-pic
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/omnifocus_operator/contracts/shared/repetition_rule.py
  - tests/test_contracts_repetition_rule.py
autonomous: true
requirements: [QUICK-260402-PIC]
must_haves:
  truths:
    - "FrequencyEditSpec rejects on_days when type is set and not 'weekly'"
    - "FrequencyEditSpec rejects on/on_dates when type is set and not 'monthly'"
    - "FrequencyEditSpec rejects on + on_dates together when both are set"
    - "FrequencyEditSpec allows on_days without type (type UNSET) -- service validates after merge"
    - "FrequencyEditSpec allows on + on_dates when type is UNSET -- service validates after merge"
  artifacts:
    - path: "src/omnifocus_operator/contracts/shared/repetition_rule.py"
      provides: "model_validator on FrequencyEditSpec"
      contains: "_check_cross_type_fields"
    - path: "tests/test_contracts_repetition_rule.py"
      provides: "Cross-type validation tests for edit spec"
  key_links:
    - from: "FrequencyEditSpec._check_cross_type_fields"
      to: "check_frequency_cross_type_fields()"
      via: "is_set() guards converting UNSET to None"
      pattern: "is_set.*check_frequency_cross_type_fields"
---

<objective>
Add a @model_validator to FrequencyEditSpec that calls check_frequency_cross_type_fields() with is_set() guards, mirroring FrequencyAddSpec but respecting patch semantics (UNSET fields skip validation).

Purpose: Catch obviously contradictory patches (e.g., type="daily" + on_days=["MO"]) at the contract boundary instead of waiting for service-layer merge.
Output: Validator on FrequencyEditSpec, updated tests proving both rejection and pass-through behavior.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/omnifocus_operator/contracts/shared/repetition_rule.py
@src/omnifocus_operator/models/repetition_rule.py (check_frequency_cross_type_fields at line 149)
@src/omnifocus_operator/contracts/shared/actions.py (TagAction is_set() pattern at line 44)
@tests/test_contracts_repetition_rule.py

<interfaces>
<!-- From contracts/base.py -->
from omnifocus_operator.contracts.base import UNSET, CommandModel, Patch, PatchOrClear, is_set

<!-- check_frequency_cross_type_fields signature from models/repetition_rule.py:149 -->
def check_frequency_cross_type_fields(
    type_: str,
    on_days: Sequence[str] | None,
    on: OrdinalWeekday | None,
    on_dates: list[int] | None,
) -> None: ...

<!-- TagAction pattern from actions.py:44 -->
@model_validator(mode="after")
def _validate_incompatible_tag_edit_modes(self) -> TagAction:
    has_replace = is_set(self.replace)
    has_add = is_set(self.add)
    ...
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add model_validator to FrequencyEditSpec and update tests</name>
  <files>src/omnifocus_operator/contracts/shared/repetition_rule.py, tests/test_contracts_repetition_rule.py</files>
  <behavior>
    - When type IS set: pass type value to check_frequency_cross_type_fields; pass field value if set, None if UNSET
    - FrequencyEditSpec(type="daily", on_days=["MO"]) raises ValidationError matching "on_days is not valid"
    - FrequencyEditSpec(type="weekly", on={"first": "monday"}) raises ValidationError matching "on is not valid"
    - FrequencyEditSpec(type="monthly", on={"first": "monday"}, on_dates=[1]) raises ValidationError matching "mutually exclusive"
    - When type is UNSET: skip check entirely -- FrequencyEditSpec(on_days=["MO"]) remains valid (existing test_no_cross_type_validation)
    - When type is UNSET but on + on_dates both set: skip check -- both present without type is deferred to service layer
    - FrequencyEditSpec(type="weekly", on_days=["MO"]) remains valid (compatible combo)
    - FrequencyEditSpec(type="monthly", on={"first": "monday"}) remains valid (compatible combo)
    - FrequencyEditSpec(type="monthly", on_dates=[1, 15]) remains valid (compatible combo)
  </behavior>
  <action>
    1. In repetition_rule.py, add `is_set` to the existing import from `contracts.base` (line 28-33).

    2. Add a `@model_validator(mode="after")` to FrequencyEditSpec (after line 193, before the closing of the class). Pattern follows TagAction._validate_incompatible_tag_edit_modes:
       - If `not is_set(self.type)`: return self immediately (can't validate cross-type without knowing the type)
       - Otherwise: call `check_frequency_cross_type_fields(self.type, on_days_val, on_val, on_dates_val)` where each val is `self.field if is_set(self.field) else None`
       - Return self

    3. In tests/test_contracts_repetition_rule.py, update TestFrequencyEditSpec:
       - **Remove** `test_no_cross_type_validation` (line 248) -- replaced by more specific tests below
       - **Update** `test_no_mutual_exclusion_validation` (line 254) -- this should now ONLY pass when type is UNSET (which it already is in the test). Update the docstring to clarify this tests the "type UNSET skips check" behavior.
       - **Add** rejection tests:
         - `test_cross_type_on_days_with_daily_raises` -- type="daily", on_days=["MO"] -> ValidationError
         - `test_cross_type_on_with_weekly_raises` -- type="weekly", on={"first": "monday"} -> ValidationError
         - `test_cross_type_on_dates_with_daily_raises` -- type="daily", on_dates=[1] -> ValidationError
         - `test_mutual_exclusion_when_type_set_raises` -- type="monthly", on + on_dates -> ValidationError
       - **Add** pass-through tests:
         - `test_cross_type_skipped_when_type_unset` -- on_days=["MO"] without type -> valid
         - `test_compatible_type_and_on_days` -- type="weekly", on_days=["MO"] -> valid
         - `test_compatible_type_and_on` -- type="monthly", on={"first": "monday"} -> valid
         - `test_compatible_type_and_on_dates` -- type="monthly", on_dates=[1, 15] -> valid
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator/.claude/worktrees/agent-a603fe3e && uv run pytest tests/test_contracts_repetition_rule.py -x -q && uv run pytest tests/test_output_schema.py -x -q</automated>
  </verify>
  <done>FrequencyEditSpec rejects contradictory type+field combos when type is set, passes through when type is UNSET. All existing tests still pass. Output schema unchanged.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_contracts_repetition_rule.py -x -q` -- all tests pass including new cross-type tests
- `uv run pytest tests/test_output_schema.py -x -q` -- output schema unchanged (FrequencyEditSpec is input-only but verify anyway)
- `uv run pytest tests/ -x -q` -- full suite green
</verification>

<success_criteria>
- FrequencyEditSpec has @model_validator calling check_frequency_cross_type_fields with is_set() guards
- Contradictory patches (type set + incompatible field set) rejected at contract boundary
- UNSET type skips validation entirely (service layer handles after merge)
- All 534+ tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/260402-pic-add-cross-type-model-validator-to-freque/260402-pic-SUMMARY.md`
</output>
