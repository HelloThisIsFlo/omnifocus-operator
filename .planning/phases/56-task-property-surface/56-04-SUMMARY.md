---
phase: 56-task-property-surface
plan: 04
subsystem: response-shaping
tags: [projection, never-strip, default-fields, hierarchy-include, flag-06, hier-04, strip-11, prop-08]

requires:
  - phase: 56-task-property-surface
    plan: 02
    provides: "TaskType/ProjectType + ActionableEntity.has_* + Task/Project.type + completes_with_children on models"
  - phase: 56-task-property-surface
    plan: 03
    provides: "Task.is_sequential + Task.depends_on_children derived flags, DomainLogic enrichment on all read pipelines"

provides:
  - "`NEVER_STRIP = {\"completesWithChildren\"}` -- `availability` removed (STRIP-11), `completesWithChildren` added (PROP-08)"
  - "`TASK_DEFAULT_FIELDS` gains {hasNote, hasRepetition, hasAttachments, isSequential, dependsOnChildren} (FLAG-01..05)"
  - "`PROJECT_DEFAULT_FIELDS` gains {hasNote, hasRepetition, hasAttachments} (FLAG-01..03 only -- tasks-only FLAG-04/05 excluded)"
  - "`TASK_FIELD_GROUPS['hierarchy']` = {parent, hasChildren, type, completesWithChildren} (HIER-01)"
  - "`PROJECT_FIELD_GROUPS['hierarchy']` = {folder, hasChildren, type, completesWithChildren} (HIER-02)"
  - "No-suppression invariant contract tests (FLAG-06 / HIER-04): default + hierarchy pipelines emit INDEPENDENTLY"

affects:
  - "56-05 (agent-facing descriptions / FLAG-07): projection is locked, agent docs can now reference the stable surface without further shaping changes"

tech-stack:
  added: []
  patterns:
    - "Strip-when-false via existing `_is_strip_value` -- zero new stripping logic for five new derived flags (they participate automatically because `False` is already in `_STRIP_HASHABLE`)"
    - "Field-group sync invariant (`test_every_*_model_field_in_exactly_one_group`) enforced: moving a field from `metadata` to defaults requires removing it from the group -- the test catches any drift"

key-files:
  created: []
  modified:
    - "src/omnifocus_operator/server/projection.py -- `NEVER_STRIP` reshuffled + expanded docstring"
    - "src/omnifocus_operator/config.py -- `TASK_DEFAULT_FIELDS` / `PROJECT_DEFAULT_FIELDS` promoted five / three new members; `TASK_FIELD_GROUPS['metadata']` / `PROJECT_FIELD_GROUPS['metadata']` no longer carry the promoted flags"
    - "tests/test_projection.py -- `TestPhase5604StripRules` (15 tests), `TestPhase5604DefaultFieldsAndHierarchy` (6 tests), `TestNoSuppressionInvariant` (5 tests), `TestNoSuppressionInvariantForProjects` (3 tests) -- 29 new tests"
    - "tests/test_server.py -- `TestHierarchyIncludeNoSuppression` (3 integration tests through full MCP handler path)"

key-decisions:
  - "Splitting Task 1 + Task 2 commits atomically. Task 1 ships the NEVER_STRIP reshuffle, default-field promotion, hierarchy group expansion, and strip-rule coverage. Task 2 adds the contract tests proving the no-suppression invariant. Each commit builds cleanly on its own."
  - "Redundancy IS the requirement (FLAG-06 / HIER-04). When `include=['hierarchy']` is requested, the default-response derived flags (`isSequential`, `dependsOnChildren`) AND the hierarchy group (`type`, `hasChildren`, `completesWithChildren`) emit INDEPENDENTLY. No de-duplication, no suppression. Tests explicitly assert BOTH pipelines."
  - "The field-group sync invariant forced removal from `metadata` when promoting to defaults. Originally the plan hinted `metadata` could still carry the flags, but the test `test_no_field_in_multiple_groups_*` prohibits that. This is correct -- defaults == opt-out of metadata, not co-membership."
  - "Integration test covers `list_tasks` + `get_task` (the two most visible agent-facing paths) with a dedicated `_HIERARCHY_INCLUDE_SEED` fixture that shapes tasks specifically for the no-suppression assertions. This guards against any future handler-wiring change that accidentally short-circuits projection."

patterns-established:
  - "Promotion pattern: fields graduating from opt-in groups to defaults must be removed from the original group (field-group sync invariant enforces this). Applied cleanly to 5 fields on tasks + 3 on projects."

requirements-completed: [HIER-01, HIER-02, HIER-04, FLAG-01, FLAG-02, FLAG-03, FLAG-04, FLAG-05, FLAG-06, PROP-08, STRIP-11]

duration: ~7min
completed: 2026-04-19
---

# Phase 56 Plan 04: Default-Response Shaping & No-Suppression Invariant Summary

**Promoted the five presence/derived flags to the default response (strip-when-false), reshuffled `NEVER_STRIP` (out: `availability`, in: `completesWithChildren`), expanded the `hierarchy` include group on tasks and projects, and locked the no-suppression invariant (FLAG-06 / HIER-04) via 8 contract tests + 3 integration tests.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-04-19T16:29:34Z
- **Completed:** 2026-04-19T16:36:50Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 4 (2 source, 2 tests)

## Accomplishments

- `NEVER_STRIP` carries `completesWithChildren` (PROP-08). `False` survives stripping so hierarchy-include responses keep the `dependsOnChildren` counterpart signal visible. The defensive `availability` entry is gone (STRIP-11) -- enum strings are truthy, so they pass normal strip rules unprotected.
- The five derived flags (`hasNote`, `hasRepetition`, `hasAttachments`, `isSequential`, `dependsOnChildren`) are promoted to `TASK_DEFAULT_FIELDS`. Stripped-when-false via the existing `_is_strip_value` pipeline -- no new stripping logic needed.
- `PROJECT_DEFAULT_FIELDS` gains the three shared presence flags only. `isSequential` and `dependsOnChildren` remain tasks-only and are explicitly guarded (FLAG-04/FLAG-05 tasks-only invariant, tested in `test_project_default_fields_exclude_tasks_only_flags`).
- `TASK_FIELD_GROUPS['hierarchy']` and `PROJECT_FIELD_GROUPS['hierarchy']` both hold `{..., hasChildren, type, completesWithChildren}`. `hasChildren` name preserved (HIER-03); `hasSubtasks` forbidden end-to-end.
- No-suppression invariant (FLAG-06 / HIER-04) proven by `TestNoSuppressionInvariant` (5 unit tests) + `TestNoSuppressionInvariantForProjects` (3 unit tests) + `TestHierarchyIncludeNoSuppression` (3 server-integration tests).

## Task Commits

1. **Task 1: Reshape NEVER_STRIP + promote derived flags + expand hierarchy group** -- `c0325f9f` (feat)
   - `NEVER_STRIP: frozenset[str] = frozenset({"completesWithChildren"})` (docstring expanded with PROP-08 rationale + STRIP-11 removal note).
   - `TASK_DEFAULT_FIELDS`: +5 members (FLAG-01..05).
   - `PROJECT_DEFAULT_FIELDS`: +3 members (FLAG-01..03 shared presence flags only).
   - `TASK_FIELD_GROUPS['metadata']` / `PROJECT_FIELD_GROUPS['metadata']`: removed the promoted flags (field-group sync invariant requires exactly-one-group membership).
   - `TASK_FIELD_GROUPS['hierarchy']` / `PROJECT_FIELD_GROUPS['hierarchy']`: unchanged content but comments updated to reflect Wave 2 semantics (HIER-01/HIER-02 + redundancy-is-the-requirement).
   - 21 new projection-unit tests: strip-when-false per flag, NEVER_STRIP preservation, default-field/hierarchy-group membership, HIER-03 name-preservation guard.

2. **Task 2: No-suppression invariant contract tests (FLAG-06 / HIER-04)** -- `0c50db7c` (test)
   - `tests/test_projection.py`: `TestNoSuppressionInvariant` (5 tests, tasks), `TestNoSuppressionInvariantForProjects` (3 tests, projects) with helper builders.
   - `tests/test_server.py`: `TestHierarchyIncludeNoSuppression` (3 tests) using `_HIERARCHY_INCLUDE_SEED` fixture -- exercises `list_tasks` default + `include=['hierarchy']` + `get_task` through the full MCP handler pipeline.

_Plan metadata commit is owned by the orchestrator (STATE.md / ROADMAP.md) per this plan's objective._

## Files Created/Modified

Source:
- `src/omnifocus_operator/server/projection.py` -- `NEVER_STRIP` membership + docstring.
- `src/omnifocus_operator/config.py` -- `TASK_DEFAULT_FIELDS`, `PROJECT_DEFAULT_FIELDS`, `TASK_FIELD_GROUPS['metadata']`, `PROJECT_FIELD_GROUPS['metadata']`, `TASK_FIELD_GROUPS['hierarchy']` / `PROJECT_FIELD_GROUPS['hierarchy']` comments.

Tests:
- `tests/test_projection.py` -- 29 new tests across 4 classes.
- `tests/test_server.py` -- 3 new integration tests in `TestHierarchyIncludeNoSuppression` with dedicated `_HIERARCHY_INCLUDE_SEED` fixture.

## Test Counts Added

- `tests/test_projection.py`: **+29** tests (34 -> 63 tests in file).
- `tests/test_server.py`: **+3** tests (132 -> 135 tests in file).

Overall pytest suite: **2 301 passed** (was 2 269 after Plan 56-03 -- +32 net; plan-local is +32 straight, no drift).

## Decisions Made

- **`metadata` vs defaults is mutually exclusive.** The field-group sync invariant (`test_no_field_in_multiple_groups_task` / `_project`) prohibits a field from appearing in both `*_DEFAULT_FIELDS` and any `*_FIELD_GROUPS` member. Promoting a field to defaults requires removing it from `metadata`. This is the correct interpretation: defaults behave as an opt-out-of-metadata, not a co-membership.
- **Redundancy by design.** `resolve_fields` is additive by construction (`result = set(default_fields); for group_name in include: result |= group`). The no-suppression invariant is therefore a CONSEQUENCE of the existing implementation -- but the contract tests lock the behavior so no future refactor can introduce de-duplication silently.
- **Integration tests over pure unit.** Task 2 could have stayed fully inside `test_projection.py`, but adding three tests in `test_server.py` that exercise `list_tasks` + `get_task` through the full MCP handler path pays off: any future handler-wiring change that accidentally calls a custom `project_entity` variant (e.g. stripping default flags before hierarchy resolution) would be caught end-to-end.
- **PROP-08 test leverages NEVER_STRIP explicitly.** `test_hierarchy_request_emits_hierarchy_group_AND_keeps_default_derived_flags` uses a task with `completesWithChildren=False` AND asserts `projected.get("completesWithChildren") is False`. Without NEVER_STRIP, the `False` would be stripped before projection; the test doubles as a PROP-08 regression guard.

## Deviations from Plan

None. The plan matched the codebase exactly: five flags needed promotion, hierarchy groups already contained the right fields (placed by 56-02), and the field-group sync invariant forced removal from `metadata` (which the plan's action steps implicitly required but didn't spell out). No auto-fixes, no scope creep, no architectural questions.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- **Phase 56-05 (agent-facing descriptions / FLAG-07)**: projection surface is now locked. `isSequential`, `dependsOnChildren`, `hasNote`, `hasRepetition`, `hasAttachments`, `completesWithChildren`, and `type` are all stable member names with clear strip semantics. DESC-03 additions in `agent_messages/descriptions.py` are zero-risk.
- **Phase 57 (parent filter + subtree retrieval)**: independent subsystem (repo-layer filter), no coupling to the projection changes made here.
- No blockers introduced. No `RealBridge` references anywhere (SAFE-01). No new `plistlib` usage (PREFS-05). HIER-03 `hasChildren` name preserved end-to-end.

## Threat Flags

No new security-relevant surface. The projection module is a pure dict transform over `model_dump(by_alias=True)` output with no user-controlled input reaching the NEVER_STRIP set or the field-group dictionaries. T-56-11 mitigation confirmed: explicit no-suppression tests in both unit and integration suites. T-56-13 mitigation confirmed: `test_hierarchy_request_completes_with_children_false_survives_never_strip` locks the PROP-08 survival behavior.

## Self-Check: PASSED

- FOUND: `src/omnifocus_operator/server/projection.py` (modified)
- FOUND: `src/omnifocus_operator/config.py` (modified)
- FOUND: `tests/test_projection.py` (modified)
- FOUND: `tests/test_server.py` (modified)
- FOUND: commit `c0325f9f` (Task 1)
- FOUND: commit `0c50db7c` (Task 2)
- VERIFIED: `grep "NEVER_STRIP.*=.*frozenset" src/omnifocus_operator/server/projection.py` -- 1 match containing `"completesWithChildren"`; no `"availability"` present anywhere in the file.
- VERIFIED: `grep "hasNote\|hasRepetition\|hasAttachments" src/omnifocus_operator/config.py` -- present in both TASK_DEFAULT_FIELDS and PROJECT_DEFAULT_FIELDS blocks.
- VERIFIED: `grep "isSequential\|dependsOnChildren" src/omnifocus_operator/config.py` -- present in TASK_DEFAULT_FIELDS only; PROJECT_DEFAULT_FIELDS comment explicitly excludes them.
- VERIFIED: `grep "hasSubtasks" src/omnifocus_operator/` -- no results (HIER-03 preserved).
- VERIFIED: `grep "RealBridge" tests/test_projection.py tests/test_server.py` -- no results (SAFE-01 satisfied).
- VERIFIED: `uv run pytest tests/test_projection.py --no-cov -q` -- 63 passed (34 baseline + 29 new).
- VERIFIED: `uv run pytest tests/test_server.py --no-cov -q` -- 135 passed (132 baseline + 3 new).
- VERIFIED: `uv run pytest tests/ --no-cov -q` -- 2 301 passed, 0 failed (was 2 269; +32 net).
- VERIFIED: `uv run pytest tests/test_output_schema.py --no-cov -x -q` -- 35 passed (no `@model_serializer` / `@field_serializer` JSON Schema drift).
- VERIFIED: `uv run mypy src/omnifocus_operator/server/projection.py src/omnifocus_operator/config.py` -- Success: no issues found.

---
*Phase: 56-task-property-surface*
*Completed: 2026-04-19*
