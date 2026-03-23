---
phase: 27-repository-contract-tests-for-behavioral-equivalence
plan: 02
subsystem: testing
tags: [golden-master, bridge, contract-tests, uat, capture-script]

requires:
  - plan: 27-01
    provides: "tests/golden/ normalization helpers, InMemoryBridge gap fixes"
provides:
  - "uat/capture_golden_master.py interactive capture script (17 scenarios)"
  - "tests/test_bridge_contract.py CI contract tests (per-scenario parametrized)"
  - "Golden master fixtures in tests/golden/ (initial_state + 17 scenarios)"

key-files:
  created:
    - uat/capture_golden_master.py
    - tests/test_bridge_contract.py
    - tests/golden/initial_state.json
    - tests/golden/scenario_01_add_inbox_task.json
    - tests/golden/scenario_02_add_task_with_parent.json
    - tests/golden/scenario_03_add_task_all_fields.json
    - tests/golden/scenario_04_add_task_with_tags.json
    - tests/golden/scenario_05_edit_name.json
    - tests/golden/scenario_06_edit_note.json
    - tests/golden/scenario_07_edit_flagged.json
    - tests/golden/scenario_08_edit_dates.json
    - tests/golden/scenario_09_clear_dates.json
    - tests/golden/scenario_10_edit_estimated_minutes.json
    - tests/golden/scenario_11_add_tags.json
    - tests/golden/scenario_12_remove_tags.json
    - tests/golden/scenario_13_replace_tags.json
    - tests/golden/scenario_14_lifecycle_complete.json
    - tests/golden/scenario_15_lifecycle_drop.json
    - tests/golden/scenario_16_move_to_project.json
    - tests/golden/scenario_17_move_to_inbox.json
  modified:
    - tests/doubles/bridge.py
    - tests/golden/normalize.py
    - tests/test_stateful_bridge.py
    - uat/test_read_only.py
    - uat/README.md

requirements-completed: [INFRA-13, INFRA-14]
completed: 2026-03-21
---

# Phase 27 Plan 02: Golden Master Capture + CI Contract Tests

**17/17 contract scenarios pass. Two gaps in the golden master testing approach discovered during checkpoint.**

## Accomplishments

- Interactive capture script with 17 scenarios covering add_task and edit_task
- CI contract tests with per-scenario parametrized output and readable error diffs
- Golden master fixtures captured from live OmniFocus
- Multiple InMemoryBridge behavioral gaps discovered and fixed during checkpoint:
  - hasChildren not updated on add_task/move
  - availability not set to "blocked" for deferred tasks
  - completionDate/dropDate not set on lifecycle changes
  - moveTo missing position field at bridge level
  - Parent resolution matches OmniFocus (type: "task" for project root tasks)

## Commits

1. **Task 1: Capture script** - `7dd2172`
2. **Task 2: Contract tests** - `3432c7b`
3. **Checkpoint iteration** - `14312d4` (fixes from human verification)

## Gaps

### Gap 1: Golden master captures adapted data, not raw bridge output

The capture script applies `adapt_snapshot` before saving, which loses
information. For example, the raw bridge sends two separate fields for parent
info:
- `parent`: task ID (the parent task, or the project's root task)
- `project`: project ID

The adapter merges these into a single `parent` dict with a `type` field. This
means the golden master can't distinguish between a task whose parent is a
project root task (`parent=<id>, project=<id>`) vs a task directly under a
project with no parent task (`parent=None, project=<id>`). Both real patterns
exist in OmniFocus — confirmed by inspecting raw bridge output.

**Fix:** Remove `adapt_snapshot` from the capture script. Capture raw bridge
format. Update InMemoryBridge to return raw format. Update normalization
for raw fields.

### Gap 2: Scenarios don't cover all parent/project patterns

The 17 scenarios only exercise `add_task` and `edit_task`. All tasks created
via `add_task` get `parent=<root-task-id>, project=<id>` (both set). But
OmniFocus also has tasks where `parent=None, project=<id>` (the project's
root task itself). This pattern is never captured.

Additionally, the current scenarios don't test a combined multi-action edit
(e.g., rename + add tags + set dates + move in one call).

**Fix:** Add scenarios that cover additional parent/project patterns and
combined operations.

### Regression (consequence of Gap 1)

`test_service.py::TestEditTask::test_move_to_project_ending` — asserts
`parent.type == "project"` but InMemoryBridge now returns `type: "task"`
(matching the golden master). The adapter that would convert "task" → "project"
doesn't run on InMemoryBridge data because of Gap 1 (see seed SEED-004 for
the adapter silent no-op issue). Fixing Gap 1 fixes this regression.

## Self-Check: PARTIAL

- All golden master fixture files exist (18 files)
- Contract tests pass (17/17 scenarios)
- Capture script tested against live OmniFocus
- Full test suite has 1 regression (consequence of Gap 1)
