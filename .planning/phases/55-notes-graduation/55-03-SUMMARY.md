---
phase: 55-notes-graduation
plan: 03
subsystem: agent-messages + integration-tests
tags: [agent-messages, integration-tests, regression, notes-graduation]

# Dependency graph
requires:
  - phase: 55-notes-graduation
    plan: 02
    provides: process_note_action wired, N1/N2/N3 warnings, PayloadBuilder note_value kwarg
provides:
  - EDIT_TASKS_TOOL_DOC updated with actions.note bullet (D-10, D-11)
  - test_note_action_alone integration test
  - test_note_with_other_actions integration test
  - test_note_noop_warning_surfaces_in_result integration test (N3 surfacing)
  - test_edit_task_command_has_no_top_level_note schema regression (NOTE-01)
  - NOTE-05 regression confirmed via full suite green
affects:
  - /gsd-verify-work (phase 55 now ready for verification)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "NOTE_ALREADY_EMPTY import in test_service.py — direct constant comparison in warning assertions"
    - "Schema regression: EditTaskCommand.model_json_schema() properties check in TestWriteSchemaNoDateTimeFormat"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/agent_messages/descriptions.py
    - tests/test_service.py
    - tests/test_output_schema.py

key-decisions:
  - "D-10/D-11 enacted: matter-of-fact actions.note bullet added after actions.tags in EDIT_TASKS_TOOL_DOC"
  - "D-16 Pass 2 integration: 3 new TestEditTask methods cover note-alone, note+tags, N3 warning surfacing"
  - "Byte-limit trim: removed 1 repetitionRule example line + 1 bullet line from EDIT_TASKS_TOOL_DOC to stay under 2048-byte Claude Code limit (DESC-08 enforcement)"
  - "NOTE-05 regression: confirmed via full suite — AddTaskCommand.note unchanged in payload.py build_add"

requirements-completed: [NOTE-01, NOTE-02, NOTE-03, NOTE-04, NOTE-05]

# Metrics
duration: 10min
completed: 2026-04-16
---

# Phase 55 Plan 03: Notes Graduation — Tool Description + Integration Tests Summary

**EDIT_TASKS_TOOL_DOC updated with actions.note bullet, 3 new integration tests (note-alone, note+tags, N3 warning), NOTE-01 schema regression — Phase 55 functionally complete**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-16T22:11:00Z
- **Completed:** 2026-04-16T22:21:33Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `EDIT_TASKS_TOOL_DOC` updated: `actions.note` bullet added after `actions.tags` with append/replace semantics; no "breaking change" / "was top-level" language per D-10
- `test_note_action_alone`: proves `actions.note` alone (no tags/move) is valid end-to-end; append on empty → set directly (NOTE-04)
- `test_note_with_other_actions`: proves `actions.note` composes with `actions.tags` in one call; both note and tag applied
- `test_note_noop_warning_surfaces_in_result`: proves N3 warning (`NOTE_ALREADY_EMPTY`) reaches `EditTaskResult.warnings` when clearing an already-empty note
- `test_edit_task_command_has_no_top_level_note`: schema regression in `TestWriteSchemaNoDateTimeFormat` asserting `EditTaskCommand` JSON schema has no top-level `note` property
- NOTE-05 regression confirmed: `TestAddTask` suite (19 tests) green; `AddTaskCommand.note` path unchanged
- Full suite: 2163 tests passing; mypy clean; output schema regression green; AST enforcement green

## Task Commits

1. **Task 1: Update EDIT_TASKS_TOOL_DOC for actions.note (D-10, D-11)** - `b9ce2b86` (feat)
2. **Task 2: Add note integration tests + NOTE-01 schema regression** - `6fab22fb` (test)

## Files Created/Modified

- `src/omnifocus_operator/agent_messages/descriptions.py` — `actions.note` bullet added to `EDIT_TASKS_TOOL_DOC`; two minor lines trimmed to stay within 2048-byte DESC-08 limit
- `tests/test_service.py` — `NOTE_ALREADY_EMPTY` import added; `test_note_action_alone`, `test_note_with_other_actions`, `test_note_noop_warning_surfaces_in_result` added to `TestEditTask`
- `tests/test_output_schema.py` — `test_edit_task_command_has_no_top_level_note` added to `TestWriteSchemaNoDateTimeFormat`

## Decisions Made

- **D-10/D-11:** Tool description updated matter-of-fact — no migration framing, no "was previously top-level" language. Bullet format matches `actions.tags` and `actions.lifecycle` lines.
- **Byte-limit trim:** The DESC-08 enforcement test (`test_tool_descriptions_within_client_byte_limit`) enforces a 2048-byte limit. Adding the `actions.note` bullet pushed the rendered string to 2133 bytes (+85 over). Trimmed: removed one `repetitionRule` example line (`Remove days`) and one redundant bullet (`frequency.type omittable`) to free 85+ bytes. Final rendered size: 2004 bytes. Content removed was lower-value redundant examples, not critical semantics.
- **N3 warning test:** Used `replace=None` on a task with `note=""` (the default in `make_task_dict`). This directly triggers the N3 (clear-already-empty) path without any setup complexity.
- **test_note_with_other_actions:** Required seeding a `Work` tag in the snapshot (`tags=[make_tag_dict(id="tag-work", name="Work")]`) to allow `TagAction(add=["Work"])` to resolve. Pattern follows existing `test_tag_add` in the same class.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] EDIT_TASKS_TOOL_DOC exceeded 2048-byte DESC-08 limit**
- **Found during:** Task 1 verification (`uv run pytest tests/test_descriptions.py`)
- **Issue:** Adding the `actions.note` bullet pushed `EDIT_TASKS_TOOL_DOC` to 2133 bytes (85 bytes over the enforced 2048-byte limit for Claude Code MCP tool descriptions)
- **Fix:** Removed one `repetitionRule` example line (`Remove days: {{frequency: {{onDays: null}}}}`) and one redundant bullet (`frequency.type omittable (inferred) unless changing type`). Neither is load-bearing — `onDays: null` semantics are implied by the "null clears" general rule, and `frequency.type` inference is edge-case guidance not needed in the primary description
- **Files modified:** `src/omnifocus_operator/agent_messages/descriptions.py`
- **Verification:** `uv run pytest tests/test_descriptions.py -x -q` → 9 passed; rendered string 2004 bytes
- **Committed in:** `b9ce2b86`

---

**Total deviations:** 1 auto-fixed (Rule 1 — byte limit exceeded)
**Impact on plan:** Minor trim of two repetitionRule description lines. Core semantics of `actions.note` bullet preserved exactly as designed. No scope creep.

## Issues Encountered

None beyond the auto-fixed item above.

## Known Stubs

None — all NOTE-XX requirements fully implemented and tested.

## Phase 55 Closure

All five NOTE requirements are closed:

| Req | Description | Closed by |
|-----|-------------|-----------|
| NOTE-01 | Top-level `note` removed from `EditTaskCommand` | Plan 01 (contract) + Plan 03 (schema regression) |
| NOTE-02 | `append` adds with `\n\n` separator; `""` is N1 no-op | Plan 02 (domain) + Plan 03 (integration) |
| NOTE-03 | `replace` sets/clears note; identical content is N2 no-op | Plan 02 (domain) + Plan 03 (integration) |
| NOTE-04 | Append on empty note sets directly (no separator) | Plan 02 (domain) + Plan 03 (integration test_note_action_alone) |
| NOTE-05 | `AddTaskCommand.note` unchanged | Plan 01 (preserved) + Plan 03 (regression confirmed) |

## Self-Check: PASSED

- `src/omnifocus_operator/agent_messages/descriptions.py` contains `actions.note` in `EDIT_TASKS_TOOL_DOC` — FOUND
- `EDIT_TASKS_TOOL_DOC` rendered size is 2004 bytes (under 2048 limit) — CONFIRMED
- `EDIT_TASKS_TOOL_DOC` does not contain "top-level", "breaking change", "was previously" — CONFIRMED
- `tests/test_service.py` contains `async def test_note_action_alone(` — FOUND
- `tests/test_service.py` contains `async def test_note_with_other_actions(` — FOUND
- `tests/test_service.py` contains `async def test_note_noop_warning_surfaces_in_result(` — FOUND
- `tests/test_service.py` imports `NOTE_ALREADY_EMPTY` — FOUND
- `tests/test_output_schema.py` contains `def test_edit_task_command_has_no_top_level_note` — FOUND
- `uv run pytest -x -q --no-cov` → 2163 passed — PASSED
- `uv run pytest tests/test_service.py::TestEditTask -x -q` → all pass — PASSED
- `uv run pytest tests/test_output_schema.py -x -q` → 35 passed — PASSED
- `uv run pytest tests/test_descriptions.py -x -q` → 9 passed — PASSED
- `uv run pytest tests/test_service.py::TestAddTask -x -q` → 19 passed (NOTE-05 regression) — PASSED
- `uv run pytest tests/test_service_domain.py::TestNoteAction -x -q` → 4 passed — PASSED
- `uv run mypy src/` → Success: no issues found in 79 source files — PASSED
- Commits `b9ce2b86`, `6fab22fb` exist — CONFIRMED

---
*Phase: 55-notes-graduation*
*Completed: 2026-04-16*
