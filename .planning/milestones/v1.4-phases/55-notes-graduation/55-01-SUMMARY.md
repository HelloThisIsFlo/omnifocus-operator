---
phase: 55-notes-graduation
plan: 01
subsystem: contracts
tags: [pydantic, contracts, actions, edit-tasks, notes-graduation, agent-messages]

# Dependency graph
requires:
  - phase: 54-batch-processing
    provides: EditTaskResult shape (status/id/name/error/warnings) inherited unchanged
provides:
  - NoteAction class in contracts/shared/actions.py with exclusivity validator
  - EditTaskActions.note field (Patch[NoteAction])
  - EditTaskCommand top-level note field REMOVED (NOTE-01)
  - NOTE_ACTION_DOC/APPEND/REPLACE description constants
  - NOTE_APPEND_WITH_REPLACE + NOTE_NO_OPERATION error constants
  - TestNoteAction contract-validator tests (4 tests, green)
  - Green baseline: all 2144 tests pass at this commit
affects:
  - 55-02 (Plan 02: domain logic + pipeline wiring for actions.note)
  - 55-03 (Plan 03: tool description update + integration tests)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "NoteAction mirrors TagAction exactly: same file, same model_validator, same constant-family style"
    - "Dead-code removal in same plan as the field removal that makes it unreachable"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/shared/actions.py
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - src/omnifocus_operator/contracts/use_cases/edit/tasks.py
    - src/omnifocus_operator/service/payload.py
    - src/omnifocus_operator/service/domain.py
    - tests/test_service_domain.py
    - tests/test_service.py
    - tests/test_service_payload.py
    - tests/test_contracts_type_aliases.py
    - tests/test_models.py

key-decisions:
  - "D-01: NoteAction with exclusivity (append XOR replace) AND at-least-one via @model_validator(mode='after')"
  - "D-02: append: Patch[str] (null rejected by type); replace: PatchOrClear[str] (null=clear)"
  - "D-03: NOTE_APPEND_WITH_REPLACE + NOTE_NO_OPERATION error constants in agent_messages/errors.py"
  - "D-14 (early): Remove unreachable note branch from normalize_clear_intents in same plan — AttributeError blocker"
  - "D-15: Delete NOTE_EDIT_COMMAND; add NOTE_ACTION_DOC/APPEND/REPLACE family"
  - "D-16 Pass 1+2: Mechanically rewrite/delete note test call sites; add TestNoteAction validators"
  - "Green baseline: note-behavior tests in test_service.py deleted (Plan 02 will re-add with wired behavior)"

patterns-established:
  - "NoteAction template: append (Patch[str]) + replace (PatchOrClear[str]) + @model_validator exclusivity"
  - "Contract-layer surgery = field removal + description migration + error constants + test rewrites in one atomic commit"

requirements-completed: [NOTE-01, NOTE-02, NOTE-03, NOTE-05]

# Metrics
duration: 15min
completed: 2026-04-16
---

# Phase 55 Plan 01: Notes Graduation — Contract Layer Summary

**NoteAction contract with append/replace exclusivity validator, EditTaskCommand.note removed, NOTE_ACTION_* constants added, TestNoteAction 4-test suite green, 2144 tests passing**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-16T21:56:00Z
- **Completed:** 2026-04-16T22:04:36Z
- **Tasks:** 2 (plus auto-fixes)
- **Files modified:** 11

## Accomplishments

- `NoteAction` class added to `contracts/shared/actions.py` — exact TagAction parity (append/replace, exclusivity validator, at-least-one validator)
- `EditTaskActions.note: Patch[NoteAction] = UNSET` field added; top-level `note` removed from `EditTaskCommand` (NOTE-01)
- `NOTE_ACTION_DOC`/`NOTE_ACTION_APPEND`/`NOTE_ACTION_REPLACE` description constants added; `NOTE_EDIT_COMMAND` deleted
- `NOTE_APPEND_WITH_REPLACE` and `NOTE_NO_OPERATION` error constants added to `agent_messages/errors.py`
- `TestNoteAction` class with 4 mandatory contract-validator tests (exclusivity, at-least-one, null rejection, PatchOrClear null valid)
- Green baseline: `"note"` dropped from `PayloadBuilder._add_if_set`; dead-code note branch removed from `normalize_clear_intents`; 2144 tests pass

## Task Commits

1. **Tasks 1+2: NoteAction contract + test migration (atomic green commit)** - `0c7f53dd` (feat)

## Files Created/Modified

- `src/omnifocus_operator/contracts/shared/actions.py` — NoteAction class + updated imports + __all__
- `src/omnifocus_operator/agent_messages/errors.py` — NOTE_APPEND_WITH_REPLACE, NOTE_NO_OPERATION
- `src/omnifocus_operator/agent_messages/descriptions.py` — NOTE_ACTION_DOC/APPEND/REPLACE added; NOTE_EDIT_COMMAND deleted; EDIT_TASK_ACTIONS_DOC updated
- `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` — NoteAction imported; EditTaskActions.note added; EditTaskCommand.note removed
- `src/omnifocus_operator/service/payload.py` — "note" dropped from _add_if_set args (green-baseline invariant)
- `src/omnifocus_operator/service/domain.py` — unreachable note branch removed from normalize_clear_intents (D-14, pulled forward)
- `tests/test_service_domain.py` — TestNoteAction class (4 tests); 3 note tests in TestNormalizeClearIntents deleted
- `tests/test_service.py` — NoteAction imported; 4 note-behavior tests deleted (behavior not yet wired)
- `tests/test_service_payload.py` — 3 note tests deleted (semantics change in Plan 02)
- `tests/test_contracts_type_aliases.py` — note=None → due_date=None in PatchOrClear test
- `tests/test_models.py` — test_edit_task_command_unset_defaults_with_forbid + test_edit_command_schema_nullable_fields updated

## Decisions Made

- D-01/D-02/D-03: NoteAction shape, type aliases, error constants — all locked in CONTEXT.md, executed verbatim
- D-14 pulled forward to Plan 01: The `normalize_clear_intents` dead-code branch (`if is_set(command.note) and command.note is None`) raises `AttributeError` the moment `EditTaskCommand.note` is removed. Removing it in Plan 01 is required for the green baseline — aligns with CONTEXT.md intent.
- Note-behavior integration tests deleted from `test_service.py`: the pipeline doesn't process `actions.note` until Plan 02. Re-adding with proper behavior assertions is Plan 02's job.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pulled forward normalize_clear_intents dead-code removal from Plan 02**
- **Found during:** Task 2 verification (`uv run pytest tests/test_service_domain.py`)
- **Issue:** `domain.py:484` calls `getattr(command, 'note')` in `normalize_clear_intents`; after `EditTaskCommand.note` is removed this raises `AttributeError: 'EditTaskCommand' object has no attribute 'note'`
- **Fix:** Removed the two dead-code lines (`if is_set(command.note) and command.note is None: command = command.model_copy(update={"note": ""})`) from `normalize_clear_intents`; updated docstring to remove the note entry
- **Files modified:** `src/omnifocus_operator/service/domain.py`
- **Verification:** `pytest tests/test_service_domain.py -x -q` → 146 passed; full suite 2144 passed
- **Committed in:** `0c7f53dd` (part of the single atomic plan commit)

**2. [Rule 1 - Bug] Fixed 2 additional test_models.py call sites referencing removed EditTaskCommand.note**
- **Found during:** Full suite run after Task 2 rewrites
- **Issue:** `test_edit_task_command_unset_defaults_with_forbid` asserted `isinstance(command.note, _Unset)` and `test_edit_command_schema_nullable_fields` checked `props["note"]` — both referenced the now-removed field
- **Fix:** Removed `command.note` assertion from UNSET-defaults test; rewrote schema-nullable test to assert `"note" not in props` and keep the `dueDate` assertion
- **Files modified:** `tests/test_models.py`
- **Verification:** Full suite 2144 passed
- **Committed in:** `0c7f53dd` (part of the single atomic plan commit)

**3. [Rule 1 - Bug] Deleted 4 note-behavior integration tests from test_service.py**
- **Found during:** Full suite run after payload.py fix
- **Issue:** `test_patch_note_only`, `test_note_null_clears_note`, `test_multi_field_edit`, `test_clear_note_with_empty_string` all assert `task.note == <value>` after calling `EditTaskCommand(actions=EditTaskActions(note=NoteAction(replace=...)))`, but `actions.note` has no pipeline effect until Plan 02 — assertions fail
- **Fix:** Deleted the four tests (same approach as `test_service_payload.py` note tests). Plan 02 re-adds equivalent tests with proper behavior
- **Files modified:** `tests/test_service.py`
- **Verification:** Full suite 2144 passed
- **Committed in:** `0c7f53dd`

---

**Total deviations:** 3 auto-fixed (2 Rule 1 — bug fixes; 1 Rule 3 — blocking issue)
**Impact on plan:** All auto-fixes necessary for green baseline. No scope creep. D-14 was explicitly scheduled for Plan 02 but is a prerequisite for Plan 01's green baseline — pulling it forward was the only correct choice.

## Issues Encountered

None beyond the auto-fixed items above.

## Known Stubs

- `EditTaskActions.note` field exists and validates at the schema boundary, but has no runtime effect yet — the pipeline ignores it until Plan 02 wires `DomainLogic.process_note_action` and the payload builder update. This is intentional: Plan 01's purpose is the schema change only.

## Next Phase Readiness

- Plan 02 can proceed immediately: `NoteAction` contract is green, `EditTaskActions.note` is defined, `PayloadBuilder.build_edit` no longer reads the old `command.note`. Plan 02 adds `process_note_action` domain method, warning constants (N1/N2/N3), and pipeline wiring.
- `normalize_clear_intents` dead-code is already removed — Plan 02 does not need to touch it.
- Deleted note-behavior tests (`test_service.py`) must be re-added in Plan 02/03 with correct assertions once the behavior is wired.

## Self-Check: PASSED

- `src/omnifocus_operator/contracts/shared/actions.py` contains `class NoteAction(CommandModel):` — FOUND
- `src/omnifocus_operator/contracts/shared/actions.py` contains `__all__ = ["MoveAction", "NoteAction", "TagAction"]` — FOUND
- `src/omnifocus_operator/agent_messages/errors.py` contains `NOTE_APPEND_WITH_REPLACE` and `NOTE_NO_OPERATION` — FOUND
- `src/omnifocus_operator/agent_messages/descriptions.py` contains `NOTE_ACTION_DOC`, `NOTE_ACTION_APPEND`, `NOTE_ACTION_REPLACE` — FOUND
- `src/omnifocus_operator/agent_messages/descriptions.py` does NOT contain `NOTE_EDIT_COMMAND` — CONFIRMED (grep returns 0 matches)
- `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` contains `note: Patch[NoteAction] = UNSET` — FOUND
- `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` does NOT contain `note: PatchOrClear[str]` or `NOTE_EDIT_COMMAND` — CONFIRMED
- `src/omnifocus_operator/service/payload.py` contains `_add_if_set(kwargs, command, "name", "flagged", "estimated_minutes")` (no "note") — FOUND
- `tests/test_service_domain.py` contains `class TestNoteAction:` with all 4 mandatory test methods — FOUND
- `uv run pytest -x -q --no-cov` → 2144 passed — PASSED
- `uv run pytest tests/test_service_domain.py::TestNoteAction -x -q --no-cov` → 4 passed — PASSED
- `uv run pytest tests/test_output_schema.py tests/test_descriptions.py -x -q --no-cov` → all passed — PASSED
- `uv run mypy src/` → Success: no issues found in 79 source files — PASSED
- Commit `0c7f53dd` exists — CONFIRMED

---
*Phase: 55-notes-graduation*
*Completed: 2026-04-16*
