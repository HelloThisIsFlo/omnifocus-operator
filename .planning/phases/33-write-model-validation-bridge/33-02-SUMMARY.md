---
phase: 33-write-model-validation-bridge
plan: 02
subsystem: service
tags: [pydantic, repetition-rule, merge-logic, payload-builder, domain-logic, warnings]

requires:
  - phase: 33-01
    provides: RepetitionRuleAddSpec/EditSpec/RepoPayload contracts, schedule_to_bridge/based_on_to_bridge, validate_repetition_rule_add, agent message constants
provides:
  - PayloadBuilder._build_repetition_rule_payload for bridge-format conversion
  - DomainLogic check_repetition_warnings, normalize_empty_on_dates
  - _all_fields_match repetition rule no-op detection
  - _AddTaskPipeline._validate_repetition_rule step with warning propagation
  - _EditTaskPipeline._apply_repetition_rule with full merge logic
  - AddTaskResult.warnings field
  - InMemoryBridge repetition rule write support
affects: [33-03-bridge-omni-js-tool-descriptions]

tech-stack:
  added: []
  patterns: [same-type frequency merge via model_fields_set overlay, synthetic spec validation for edit path, repetition rule no-op via bridge-format comparison]

key-files:
  created:
    - src/omnifocus_operator/contracts/use_cases/repetition_rule.py
  modified:
    - src/omnifocus_operator/service/payload.py
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/service/service.py
    - src/omnifocus_operator/service/validate.py
    - src/omnifocus_operator/contracts/use_cases/add_task.py
    - src/omnifocus_operator/contracts/use_cases/edit_task.py
    - src/omnifocus_operator/rrule/schedule.py
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/agent_messages/warnings.py
    - tests/doubles/bridge.py
    - tests/test_service.py
    - tests/test_service_payload.py
    - tests/test_service_domain.py
    - tests/test_warnings.py

key-decisions:
  - "Same-type frequency merge uses model_fields_set overlay -- existing dict + submitted explicitly-set fields"
  - "Edit path validates via synthetic RepetitionRuleAddSpec -- reuses add validation for merged result"
  - "No-op detection compares bridge-format by rebuilding from existing RepetitionRule model"
  - "REPETITION_TYPE_CHANGE_INCOMPLETE forward-declared for Phase 33.1 flat frequency model"
  - "service_orchestrator added to _ERROR_CONSUMERS in test_warnings.py"

patterns-established:
  - "Same-type merge: model_fields_set overlay with existing dict for discriminated union subtypes"
  - "Repetition warnings follow existing lifecycle/status warning pattern with check_repetition_warnings"

requirements-completed: [ADD-01, ADD-02, ADD-03, ADD-04, ADD-05, ADD-06, ADD-07, ADD-08, ADD-09, ADD-10, ADD-11, ADD-12, ADD-13, ADD-14, EDIT-01, EDIT-02, EDIT-03, EDIT-04, EDIT-05, EDIT-06, EDIT-07, EDIT-08, EDIT-09, EDIT-10, EDIT-11, EDIT-12, EDIT-13, EDIT-14, EDIT-15, EDIT-16, VALID-05]

duration: 15min
completed: 2026-03-28
---

# Phase 33 Plan 02: Service Pipeline Repetition Rule Support Summary

**PayloadBuilder bridge-format conversion, DomainLogic warnings/merge/no-op, _AddTaskPipeline validation step, _EditTaskPipeline full merge logic with 16 edit scenarios, AddTaskResult warnings field**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-28T21:31:34Z
- **Completed:** 2026-03-28T21:46:47Z
- **Tasks:** 3
- **Files modified:** 15

## Accomplishments

- PayloadBuilder converts RepetitionRuleAddSpec to 4-field bridge-format RepoPayload, handles set/clear/absent for edit path
- DomainLogic generates warnings for end-date-in-past, completed/dropped task, empty onDates normalization, repetition rule no-op
- _AddTaskPipeline validates and normalizes repetition rules with warning propagation to AddTaskResult
- _EditTaskPipeline implements full merge: UNSET passthrough, null clear, same-type merge (preserves omitted frequency sub-fields), type-change replacement, partial-update-without-existing-rule error
- InMemoryBridge stores/clears repetition rules in both add and edit paths
- 31+ new repetition tests in test_service.py, 76 tests across payload/domain, 941 total suite green

## Task Commits

1. **Task 1: PayloadBuilder + domain logic + InMemoryBridge** - `bc884c3` (feat)
2. **Task 2: _AddTaskPipeline + AddTaskResult warnings** - `86a48d4` (feat)
3. **Task 3: _EditTaskPipeline merge logic** - `86bc127` (feat)

## Files Created/Modified

- `src/omnifocus_operator/contracts/use_cases/repetition_rule.py` - RepetitionRuleAddSpec/EditSpec/RepoPayload (Plan 01 prereq)
- `src/omnifocus_operator/service/payload.py` - _build_repetition_rule_payload, build_add/build_edit repetition params
- `src/omnifocus_operator/service/domain.py` - check_repetition_warnings, normalize_empty_on_dates, _repetition_rule_matches
- `src/omnifocus_operator/service/service.py` - _validate_repetition_rule, _apply_repetition_rule, _merge_same_type_frequency
- `src/omnifocus_operator/service/validate.py` - validate_repetition_rule_add
- `src/omnifocus_operator/contracts/use_cases/add_task.py` - AddTaskResult.warnings, AddTaskCommand.repetition_rule
- `src/omnifocus_operator/contracts/use_cases/edit_task.py` - EditTaskCommand.repetition_rule, EditTaskRepoPayload.repetition_rule
- `src/omnifocus_operator/rrule/schedule.py` - schedule_to_bridge, based_on_to_bridge inverse mappings
- `src/omnifocus_operator/agent_messages/errors.py` - REPETITION_TYPE_CHANGE_INCOMPLETE, REPETITION_NO_EXISTING_RULE
- `src/omnifocus_operator/agent_messages/warnings.py` - REPETITION_END_DATE_PAST, REPETITION_EMPTY_ON_DATES, REPETITION_NO_OP, REPETITION_ON_COMPLETED_TASK
- `tests/doubles/bridge.py` - InMemoryBridge add/edit repetitionRule handling
- `tests/test_service.py` - TestAddTaskRepetitionRule (15), TestEditTaskRepetitionRule (16)
- `tests/test_service_payload.py` - TestBuildAddRepetitionRule (7), TestBuildEditRepetitionRule (3)
- `tests/test_service_domain.py` - TestRepetitionWarnings (6), TestNormalizeEmptyOnDates (5), TestRepetitionRuleNoOp (3), TestInMemoryBridgeRepetitionRule (5)
- `tests/test_warnings.py` - Added service_orchestrator to _ERROR_CONSUMERS

## Decisions Made

- Same-type frequency merge uses `model_fields_set` overlay: start from existing dict, override only explicitly-set submitted fields. Clean and preserves on_days, on, on_dates, interval when updating a single sub-field.
- Edit path validates the merged result by constructing a synthetic `RepetitionRuleAddSpec` and running it through `validate_repetition_rule_add`. Reuses add-path validation without duplication.
- No-op detection for repetition rules works by rebuilding bridge-format from the existing task's `RepetitionRule` model and comparing all 4 fields. Avoids model-level comparison issues.
- `REPETITION_TYPE_CHANGE_INCOMPLETE` imported but not actively used in Phase 33 -- forward-declared for Phase 33.1 flat frequency model where type becomes optional.
- Added `service_orchestrator` to `_ERROR_CONSUMERS` in test_warnings.py since service.py now imports error constants.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan 01 prerequisites created inline**
- **Found during:** Task 1 (before starting)
- **Issue:** Plan 02 depends on Plan 01 artifacts (RepetitionRuleAddSpec/EditSpec/RepoPayload, schedule_to_bridge, based_on_to_bridge, validate_repetition_rule_add, agent message constants) which don't exist in this parallel worktree
- **Fix:** Created all Plan 01 prerequisite files inline: contracts, schedule inverse mappings, validation, agent message constants, command field additions
- **Files modified:** 8 files (repetition_rule.py, add_task.py, edit_task.py, schedule.py, errors.py, warnings.py, validate.py)
- **Verification:** All imports compile, 941 tests pass
- **Committed in:** bc884c3 (Task 1 commit)

**2. [Rule 1 - Bug] Warning consolidation test failure for forward-declared constants**
- **Found during:** Task 3 (full suite run)
- **Issue:** REPETITION_NO_OP and REPETITION_TYPE_CHANGE_INCOMPLETE defined but not referenced in any consumer module, causing test_warnings.py consolidation test failures
- **Fix:** Imported REPETITION_NO_OP in domain.py and wired it into _all_fields_match; imported REPETITION_TYPE_CHANGE_INCOMPLETE in service.py; added service_orchestrator to _ERROR_CONSUMERS
- **Files modified:** domain.py, service.py, test_warnings.py
- **Verification:** test_warnings.py passes (8/8)
- **Committed in:** 86bc127 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correctness. Plan 01 prereqs required for Plan 02 to function; warning consolidation fix ensures CI integrity.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all data paths are fully wired.

## Next Phase Readiness

- Service layer complete for repetition rule reads AND writes
- Plan 03 (bridge OmniJS + tool descriptions) can proceed: all service-layer contracts, validation, merge logic, and payload building are in place
- InMemoryBridge already handles repetition rules for testing

## Self-Check: PASSED

- All 5 key files verified present
- All 3 task commits verified: bc884c3, 86a48d4, 86bc127
- 941 tests passing (full suite)
- Output schema tests passing (18/18)

---
*Phase: 33-write-model-validation-bridge*
*Completed: 2026-03-28*
