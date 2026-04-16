---
phase: 55-notes-graduation
plan: 02
subsystem: service-layer
tags: [domain-logic, method-object, notes-graduation, warnings, pipeline, tdd]

# Dependency graph
requires:
  - phase: 55-notes-graduation
    plan: 01
    provides: NoteAction contract, EditTaskActions.note field, NOTE_APPEND_WITH_REPLACE/NOTE_NO_OPERATION error constants, PayloadBuilder with "note" already dropped from _add_if_set
provides:
  - NOTE_APPEND_EMPTY, NOTE_REPLACE_ALREADY_CONTENT, NOTE_ALREADY_EMPTY warning constants in warnings.py
  - DomainLogic.process_note_action method (tuple[str | _Unset, bool, list[str]])
  - _EditTaskPipeline._apply_note_action step wired into execute sequence
  - PayloadBuilder.build_edit note_value kwarg (explicit, not via _add_if_set)
  - TestProcessNoteAction 15-test class covering all decision-tree branches
  - Full NOTE-02, NOTE-03, NOTE-04 behavior end-to-end
affects:
  - 55-03 (Plan 03: integration tests re-added to test_service.py, tool description update)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "process_note_action mirrors process_lifecycle shape: (value_or_UNSET, skip, warnings) 3-tuple"
    - "_apply_note_action step mirrors _apply_lifecycle: stores self._note_value + self._note_warns"
    - "N3 (clear-already-empty) checked before N2 (identical-content) to avoid dual-warning on empty+empty"
    - "PayloadBuilder note injection: explicit kwarg note_value vs _add_if_set passthrough — decouples payload from command shape"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/agent_messages/warnings.py
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/service/payload.py
    - src/omnifocus_operator/service/service.py
    - tests/test_service_domain.py

key-decisions:
  - "D-04 N1: empty append is no-op with NOTE_APPEND_EMPTY warning"
  - "D-05 N2: identical-content replace is no-op with NOTE_REPLACE_ALREADY_CONTENT warning"
  - "D-06 N3: clear on already-empty note is no-op with NOTE_ALREADY_EMPTY warning; N3 checked before N2 (Pitfall 3)"
  - "D-07: whitespace-only append text (e.g. '   ') is a real change, NOT a no-op"
  - "D-08/D-09: strip-and-check: whitespace-only existing note treated as empty for both N3 detection and append-on-empty direct-set"
  - "D-13: process_note_action returns 3-tuple (new_value_or_UNSET, should_skip_bridge, warnings)"
  - "D-14: dead normalize_clear_intents note branch already removed by Plan 01"
  - "D-16 Pass 2 (domain-unit): TestProcessNoteAction 15 tests covering all branches"
  - "Task.note is str not Optional[str] — tests branch 3 + 12 use '' instead of None"

patterns-established:
  - "process_note_action: 3-tuple return (new_note_or_UNSET, should_skip, warnings) — extendable pattern for future action types"
  - "Pipeline note wiring: _resolve_actions tracks _note_action, _apply_note_action stores _note_value/_note_warns, _build_payload aggregates"

requirements-completed:
  - NOTE-02
  - NOTE-03
  - NOTE-04

# Metrics
duration: 5min
completed: 2026-04-16
---

# Phase 55 Plan 02: Notes Graduation — Domain Logic + Pipeline Wiring Summary

**process_note_action with all 3 no-op warnings (N1/N2/N3), strip-and-check semantics, wired into _EditTaskPipeline via note_value kwarg to PayloadBuilder — NOTE-02/03/04 fully functional**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-16T22:07:00Z
- **Completed:** 2026-04-16T22:13:47Z
- **Tasks:** 3 (TDD RED + GREEN + pipeline wiring)
- **Files modified:** 5

## Accomplishments

- `NOTE_APPEND_EMPTY`, `NOTE_REPLACE_ALREADY_CONTENT`, `NOTE_ALREADY_EMPTY` warning constants added to `warnings.py`
- `DomainLogic.process_note_action` implements full decision tree: UNSET passthrough, append paths (empty/whitespace-only/normal), replace paths (new/identical/clear on empty/clear on non-empty)
- N3 (clear-already-empty) correctly wins over N2 (identical-content) when both conditions match
- `_EditTaskPipeline` extended with `_apply_note_action` step and `_note_warns` aggregated into `_all_warnings`
- `PayloadBuilder.build_edit` accepts `note_value: str | _Unset = UNSET` kwarg; note injected iff `is_set(note_value)`
- `TestProcessNoteAction`: 15 tests covering every branch of the decision tree (including pitfall 4 whitespace-only non-noop)
- Full suite: 2159 tests passing; output schema regression green; mypy clean

## Task Commits

1. **Task 1: Add no-op warning constants + write failing TestProcessNoteAction (RED)** - `8cba74dc` (test)
2. **Task 2: Implement DomainLogic.process_note_action (GREEN)** - `c5c65955` (feat)
3. **Task 3: Wire note action through _EditTaskPipeline + reshape PayloadBuilder** - `51cd4596` (feat)

## Files Created/Modified

- `src/omnifocus_operator/agent_messages/warnings.py` — NOTE_APPEND_EMPTY, NOTE_REPLACE_ALREADY_CONTENT, NOTE_ALREADY_EMPTY added after TAG_NOT_ON_TASK block
- `src/omnifocus_operator/service/domain.py` — process_note_action method added after process_lifecycle; NOTE_* warning imports + UNSET/_Unset added
- `src/omnifocus_operator/service/payload.py` — build_edit signature: note_value kwarg added (keyword-only via *); UNSET/_Unset imported; note injection block added
- `src/omnifocus_operator/service/service.py` — _resolve_actions extended with _note_action; _apply_note_action method added; execute wired; _build_payload passes note_value= and aggregates _note_warns; UNSET/_Unset imported
- `tests/test_service_domain.py` — NOTE_ALREADY_EMPTY/NOTE_APPEND_EMPTY/NOTE_REPLACE_ALREADY_CONTENT imported; TestProcessNoteAction class (15 tests) appended

## Decisions Made

- **D-14 status:** The dead `normalize_clear_intents` note branch was already removed by Plan 01 (pulled forward as a blocking fix). Task 3 had nothing to delete — confirmed via grep returning 0 matches.
- **Task.note is str:** The `Task` model (`models/common.py`) declares `note: str` (not `Optional[str]`). Test branches 3 and 12 used `None` in the plan spec but were adapted to use `""` (empty string), which is semantically identical for the strip-and-check logic.
- **15 tests, not 14:** Added `test_actions_without_note_returns_unset` (actions present but note UNSET inside) as a second UNSET branch test alongside `test_no_actions_returns_unset`. This covers an extra edge case from the branch table (row 1b).
- **`*` separator in build_edit:** Made `note_value`, `repetition_rule_payload`, and `repetition_rule_clear` all keyword-only (via `*`) for clarity. Existing callers already use keyword syntax so no call-site changes needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task.note is str, not Optional[str] — two test fixtures needed `""` not `None`**
- **Found during:** Task 2 (GREEN phase, first test run)
- **Issue:** `_task_with_note(None)` raised `ValidationError: note — Input should be a valid string`. The plan spec's branch table listed `None` as "no note" but the Task model enforces `str`.
- **Fix:** Branches 3 and 12 updated to use `""` instead of `None`. Added comment explaining the model constraint and semantic equivalence. `process_note_action` code uses `task.note or ""` so both paths are safe.
- **Files modified:** `tests/test_service_domain.py`
- **Verification:** All 15 TestProcessNoteAction tests pass green
- **Committed in:** `c5c65955` (Task 2 feat commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — test fixture type mismatch)
**Impact on plan:** Minor — semantics unchanged, branch coverage identical. No scope creep.

## Issues Encountered

None beyond the auto-fixed item above.

## Known Stubs

None — `process_note_action` is fully implemented and wired. `actions.note` now has complete runtime effect through the pipeline.

## Next Phase Readiness

- Plan 03 can proceed immediately: note behavior is fully wired end-to-end
- Plan 03 scope: re-add integration tests to `test_service.py` (test_patch_note_only, test_note_null_clears_note, test_clear_note_with_empty_string, test_multi_field_edit — deleted by Plan 01), add new integration tests (note-alone, note-with-other-actions, no-op warning propagation), update `edit_tasks` tool description

## Self-Check: PASSED

- `src/omnifocus_operator/agent_messages/warnings.py` contains `NOTE_APPEND_EMPTY`, `NOTE_REPLACE_ALREADY_CONTENT`, `NOTE_ALREADY_EMPTY` — FOUND
- `src/omnifocus_operator/service/domain.py` contains `def process_note_action(` — FOUND
- `src/omnifocus_operator/service/payload.py` contains `note_value: str | _Unset = UNSET` — FOUND
- `src/omnifocus_operator/service/service.py` contains `def _apply_note_action(` — FOUND
- `src/omnifocus_operator/service/service.py` contains `self._apply_note_action()` — FOUND
- `src/omnifocus_operator/service/service.py` contains `note_value=self._note_value` — FOUND
- `src/omnifocus_operator/service/service.py` contains `+ self._note_warns` — FOUND
- `tests/test_service_domain.py` contains `class TestProcessNoteAction:` — FOUND
- `grep "is_set(command.note)" src/` returns 0 matches — CONFIRMED
- `uv run pytest -x -q --no-cov` → 2159 passed — PASSED
- `uv run pytest tests/test_service_domain.py::TestProcessNoteAction -x -q --no-cov` → 15 passed — PASSED
- `uv run pytest tests/test_output_schema.py -x -q --no-cov` → 34 passed — PASSED
- `uv run mypy src/` → Success: no issues found in 79 source files — PASSED
- Commits `8cba74dc`, `c5c65955`, `51cd4596` exist — CONFIRMED

---
*Phase: 55-notes-graduation*
*Completed: 2026-04-16*
