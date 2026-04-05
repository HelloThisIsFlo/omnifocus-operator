---
phase: quick-260402-phi
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - src/omnifocus_operator/models/repetition_rule.py
  - tests/test_type_boundary.py
autonomous: true
requirements: [sync-tests, frequency-type-validator]
must_haves:
  truths:
    - "Adding a value to a Literal alias without updating the validation set causes a test failure"
    - "Adding a value to a validation set without updating the Literal alias causes a test failure"
    - "Frequency model rejects invalid type strings with REPETITION_INVALID_FREQUENCY_TYPE error"
  artifacts:
    - path: "tests/test_type_boundary.py"
      provides: "TestValidationSetSync class with 3 sync tests"
      contains: "TestValidationSetSync"
    - path: "src/omnifocus_operator/models/repetition_rule.py"
      provides: "_VALID_FREQUENCY_TYPES set and Frequency.type field_validator"
      contains: "_VALID_FREQUENCY_TYPES"
  key_links:
    - from: "tests/test_type_boundary.py"
      to: "models/repetition_rule.py + contracts/shared/repetition_rule.py"
      via: "get_args(Literal) == validation set"
      pattern: "get_args.*==.*_VALID_"
---

<objective>
Add validation set sync tests between models and contracts, and a runtime validator for Frequency.type.

Purpose: Prevent silent drift between Literal type aliases (contract boundary) and plain validation sets (core models). Also close the gap where Frequency.type has no runtime validation on the core model.
Output: 3 sync tests in TestValidationSetSync, _VALID_FREQUENCY_TYPES set, Frequency.type validator
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/omnifocus_operator/models/repetition_rule.py
@src/omnifocus_operator/contracts/shared/repetition_rule.py
@tests/test_type_boundary.py

<interfaces>
From src/omnifocus_operator/models/repetition_rule.py:
```python
_VALID_DAY_CODES = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
_VALID_DAY_NAMES = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "weekday", "weekend_day"}

def normalize_day_codes(value: list[str] | None) -> list[str] | None: ...
def normalize_day_name(value: str) -> str: ...
```

From src/omnifocus_operator/contracts/shared/repetition_rule.py:
```python
FrequencyType = Literal["minutely", "hourly", "daily", "weekly", "monthly", "yearly"]
DayCode = Literal["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
DayName = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "weekday", "weekend_day"]
```

From src/omnifocus_operator/agent_messages/errors.py:
```python
REPETITION_INVALID_FREQUENCY_TYPE = "Invalid frequency type '{freq_type}' -- valid types: minutely, hourly, daily, weekly, monthly, yearly"
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add _VALID_FREQUENCY_TYPES set and Frequency.type validator</name>
  <files>src/omnifocus_operator/models/repetition_rule.py, tests/test_type_boundary.py</files>
  <behavior>
    - RED: TestValidationSetSync.test_day_codes_in_sync: set(get_args(DayCode)) == _VALID_DAY_CODES
    - RED: TestValidationSetSync.test_day_names_in_sync: set(get_args(DayName)) == _VALID_DAY_NAMES
    - RED: TestValidationSetSync.test_frequency_types_in_sync: set(get_args(FrequencyType)) == _VALID_FREQUENCY_TYPES (fails because _VALID_FREQUENCY_TYPES doesn't exist yet)
    - RED: test Frequency(type="bogus", ...) raises ValueError matching REPETITION_INVALID_FREQUENCY_TYPE (fails because no validator exists yet)
    - GREEN: Add _VALID_FREQUENCY_TYPES = {"minutely", "hourly", "daily", "weekly", "monthly", "yearly"} to models/repetition_rule.py validation sets section
    - GREEN: Add validate_frequency_type(v: str) -> str shared function (matches normalize_day_codes/normalize_day_name pattern) that checks against _VALID_FREQUENCY_TYPES, raises ValueError(REPETITION_INVALID_FREQUENCY_TYPE.format(freq_type=v))
    - GREEN: Add @field_validator("type", mode="before") on Frequency class delegating to validate_frequency_type
    - GREEN: Add REPETITION_INVALID_FREQUENCY_TYPE to imports in models/repetition_rule.py
    - GREEN: Export validate_frequency_type in __all__
    - GREEN: All 3 sync tests + frequency type validation test pass
  </behavior>
  <action>
    TDD RED phase:
    1. In tests/test_type_boundary.py, add a new TestValidationSetSync class after TestTypeBoundaryEnforcement
    2. Import get_args from typing, _VALID_DAY_CODES/_VALID_DAY_NAMES/_VALID_FREQUENCY_TYPES from models.repetition_rule, DayCode/DayName/FrequencyType from contracts.shared.repetition_rule
    3. Write 3 tests: test_day_codes_in_sync, test_day_names_in_sync, test_frequency_types_in_sync -- each asserts set(get_args(LiteralAlias)) == validation_set
    4. Write test_frequency_rejects_invalid_type: Frequency(type="bogus") raises ValueError with "Invalid frequency type"
    5. Run tests -- sync tests for DayCode/DayName pass, FrequencyType fails (no _VALID_FREQUENCY_TYPES yet), validation test fails (no validator)

    TDD GREEN phase:
    6. In models/repetition_rule.py, add _VALID_FREQUENCY_TYPES = {"minutely", "hourly", "daily", "weekly", "monthly", "yearly"} in the validation sets section (after _VALID_DAY_NAMES)
    7. Add REPETITION_INVALID_FREQUENCY_TYPE to the imports from agent_messages.errors
    8. Add shared function validate_frequency_type(v: str) -> str that checks v.lower() against _VALID_FREQUENCY_TYPES (no lowering needed -- frequency types are already lowercase, just check directly), raises ValueError if not found
    9. Add @field_validator("type", mode="before") on Frequency delegating to validate_frequency_type
    10. Add validate_frequency_type to __all__
    11. Run tests -- all pass
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator/.claude/worktrees/agent-45b8ced5 && uv run pytest tests/test_type_boundary.py -x -q</automated>
  </verify>
  <done>
    - 3 sync tests pass: DayCode/DayName/FrequencyType Literal args match their validation sets
    - Frequency(type="bogus") raises ValueError with REPETITION_INVALID_FREQUENCY_TYPE message
    - _VALID_FREQUENCY_TYPES exported from models/repetition_rule.py
    - validate_frequency_type shared function available for contract reuse
  </done>
</task>

<task type="auto">
  <name>Task 2: Verify no regressions</name>
  <files></files>
  <action>
    Run the full test suite to verify no regressions. Also run ruff to check lint. Also run the output schema test specifically since repetition models affect tool output.
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator/.claude/worktrees/agent-45b8ced5 && uv run pytest tests/test_output_schema.py -x -q && uv run pytest -x -q && uv run ruff check src/ tests/</automated>
  </verify>
  <done>All tests pass, no lint violations, output schema unchanged</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_type_boundary.py::TestValidationSetSync -v` shows 3 sync tests + 1 validation test passing
- `uv run pytest -x -q` full suite green
- `uv run ruff check src/ tests/` clean
</verification>

<success_criteria>
- Sync tests catch drift: if someone adds a value to FrequencyType Literal but not _VALID_FREQUENCY_TYPES (or vice versa), test fails
- Same protection for DayCode/_VALID_DAY_CODES and DayName/_VALID_DAY_NAMES
- Frequency.type has runtime validation matching the pattern of other repetition rule validators
</success_criteria>

<output>
After completion, create `.planning/quick/260402-phi-add-validation-set-sync-tests-between-mo/260402-phi-SUMMARY.md`
</output>
