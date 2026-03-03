---
status: resolved
trigger: "repetition-rule-validation-failure — DatabaseSnapshot Pydantic model requires scheduleType in repetitionRule but OmniFocus only returns ruleString"
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T00:02:00Z
---

## Current Focus

hypothesis: CONFIRMED -- bridge.js rr() accesses v.scheduleType.name which produces undefined in OmniFocus runtime, JSON.stringify silently drops undefined values, so scheduleType is absent from the JSON response. The Pydantic model requires it as mandatory, causing 361 validation errors.
test: Fix applied and all automated tests pass (168 Python, 18 JS)
expecting: UAT test_read_only.py should now parse the snapshot successfully
next_action: Closed — temporary fix shipped. Full RepetitionRule redesign deferred to follow-up phase.

## Symptoms

expected: UAT test `uat/test_read_only.py` should successfully parse the OmniFocus database snapshot and pass validation.
actual: Pydantic validation fails with 361 errors because `scheduleType` is missing from every `repetitionRule` object in the OmniFocus response.
errors: ValidationError on `DatabaseSnapshot` — every `repetitionRule` object has `ruleString` (valid iCal RRULE strings like FREQ=DAILY, FREQ=WEEKLY, etc.) but is missing the required `scheduleType` field.
reproduction: Run `uat/test_read_only.py` — it connects to OmniFocus via the IPC bridge (which now works after recent fix), receives the snapshot, but fails at Pydantic validation.
started: Just started appearing after fixing the IPC bridge communication bug (commit 63a86e8). The communication works now, but the schema doesn't match what OmniFocus actually returns.

## Eliminated

## Evidence

- timestamp: 2026-03-03T00:00:30Z
  checked: bridge.js rr() function (line 26-29)
  found: Function accesses v.scheduleType.name -- if OmniFocus's Task.RepetitionRule.scheduleType is undefined or its .name is undefined, the result is undefined. JSON.stringify silently drops keys with undefined values.
  implication: The bridge script IS attempting to extract scheduleType, but the OmniFocus runtime doesn't provide it (or provides it in a form where .name is undefined).

- timestamp: 2026-03-03T00:00:35Z
  checked: Pydantic RepetitionRule model (src/omnifocus_operator/models/_common.py)
  found: schedule_type: str -- a required field with no default. This means any RepetitionRule JSON without scheduleType will fail Pydantic validation.
  implication: The model is too strict for what OmniFocus actually returns.

- timestamp: 2026-03-03T00:00:40Z
  checked: OmniFocus Omni Automation API docs (web search)
  found: scheduleType (Task.RepetitionScheduleType) was added in OmniFocus v4.7+. Values: FromCompletion, None, Regularly. May not be available in older versions.
  implication: scheduleType availability depends on OmniFocus version. The model must be defensive.

- timestamp: 2026-03-03T00:00:45Z
  checked: All 361 errors are for missing scheduleType (not some other field)
  found: Every single repetitionRule object fails the same way -- scheduleType is consistently absent.
  implication: This is not intermittent. Either scheduleType.name always returns undefined in the OmniFocus runtime, or the user's OmniFocus version predates v4.7.

- timestamp: 2026-03-03T00:01:30Z
  checked: Fix applied -- automated test suite
  found: 168 Python tests pass (including 2 new tests for optional schedule_type). 18 JS bridge tests pass (including 2 new tests for defensive rr()). Zero regressions.
  implication: Fix is correct and backward-compatible.

## Resolution

root_cause: The bridge.js rr() function accesses v.scheduleType.name, which evaluates to undefined in the OmniFocus runtime (either scheduleType is not available on the user's OmniFocus version, or .name returns undefined for the enum). JSON.stringify silently drops undefined values, so the serialized JSON only contains ruleString. The Pydantic RepetitionRule model requires schedule_type as mandatory (no default), causing validation failure for every task/project with a repetition rule.
fix: (1) Made schedule_type optional (str | None = None) in the Pydantic RepetitionRule model. (2) Made bridge.js rr() defensive -- extracts scheduleType.name with a fallback to null instead of passing through undefined.
verification: All 168 Python tests + 18 JS bridge tests pass. New tests added for both the optional field and the defensive bridge extraction. Awaiting human UAT verification.
files_changed:
  - src/omnifocus_operator/models/_common.py
  - src/omnifocus_operator/bridge/bridge.js
  - tests/test_models.py
  - bridge/tests/bridge.test.js
