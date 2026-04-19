---
phase: 56-task-property-surface
plan: 05
subsystem: agent-facing-descriptions
tags: [flag-07, flag-08, descriptions, tool-docs, extra-forbid, desc-03, hier-01, hier-02]

requires:
  - phase: 56-task-property-surface
    plan: 02
    provides: "TaskType/ProjectType enums + ActionableEntity.has_* + completes_with_children + Task/Project.type on models"
  - phase: 56-task-property-surface
    plan: 04
    provides: "projection + NEVER_STRIP + default-response shaping (the read surface FLAG-07 now documents)"

provides:
  - "8 new description constants in `agent_messages/descriptions.py`: HAS_NOTE_DESC, HAS_REPETITION_DESC, HAS_ATTACHMENTS_DESC, COMPLETES_WITH_CHILDREN_DESC, IS_SEQUENTIAL_DESC, DEPENDS_ON_CHILDREN_DESC, TASK_TYPE_DESC, PROJECT_TYPE_DESC"
  - "LIST_TASKS_TOOL_DOC / GET_TASK_TOOL_DOC / LIST_PROJECTS_TOOL_DOC updated to surface FLAG-07 behavioral meaning + HIER-01/02 hierarchy include expansion + shared presence flags in default fields"
  - "TaskType / ProjectType enums use `__doc__ = CONSTANT` pattern (DESC-03 compliant)"
  - "Model fields for 4 presence flags + 2 derived flags + 2 per-type enums use `Field(description=CONSTANT)`"
  - "Parametrized FLAG-08 contract tests proving all 6 derived read-only flags are rejected by `extra='forbid'` on both AddTaskCommand and EditTaskCommand (12 parametrized + 1 no-custom-message = 13 tests)"
  - "2 Wave-3 boundary-guard tests marked `# REMOVE IN 56-06` proving the rejection plumbing works for the fields Wave 3 will open"

affects:
  - "56-06 (Wave 3 write surface): the two boundary-guard tests MUST be removed or adapted when `completesWithChildren` + `type` become writable"

tech-stack:
  added: []
  patterns:
    - "Parametrized contract-rejection test: `pytest.mark.parametrize('field_name', _DERIVED_READONLY_FLAGS)` with extra_forbidden + loc assertion — reusable for any future field set proven to be derivation-only on a Command model"
    - "Wave-boundary regression guard: tests marked `# REMOVE IN 56-06` serve as assertions the plumbing works for the fields a later plan will open; plan 56-06 must touch them"

key-files:
  created: []
  modified:
    - "src/omnifocus_operator/agent_messages/descriptions.py — 8 new constants + 3 tool-doc rewrites (FLAG-07 behavioral paragraph + HIER-01/02 include expansion + tightened narrative to keep LIST_TASKS_TOOL_DOC under the 2048-byte Claude Code MCP limit)"
    - "src/omnifocus_operator/models/enums.py — TaskType and ProjectType switched from inline comments to `__doc__ = CONSTANT`"
    - "src/omnifocus_operator/models/common.py — ActionableEntity.has_note/has_repetition/has_attachments/completes_with_children gain `Field(description=CONSTANT)`"
    - "src/omnifocus_operator/models/task.py — Task.type/is_sequential/depends_on_children gain `Field(description=CONSTANT)`"
    - "src/omnifocus_operator/models/project.py — Project.type gains `Field(description=PROJECT_TYPE_DESC)`"
    - "tests/test_descriptions.py — 5 new test classes, 17 tests covering constants + tool-doc phrase locks + enum docstring pattern + model field descriptions"
    - "tests/test_contracts_field_constraints.py — 3 new test classes, 15 tests (12 parametrized FLAG-08 cases + 1 no-custom-message + 2 Wave-3 boundary guards)"

key-decisions:
  - "Tightened LIST_TASKS_TOOL_DOC narrative to stay under the Claude Code 2048-byte MCP tool-description limit. Initial draft landed at 2522 bytes (474 over). Compressed by inlining the inheritance paragraph, tightening prose, and collapsing the redundant 'availability vs defer' closing sentence (DEFER_FILTER_DESC already owns that guidance). Final: 2034 bytes. FLAG-07 behavioral phrases preserved verbatim in IS_SEQUENTIAL_DESC + DEPENDS_ON_CHILDREN_DESC and explicitly present in LIST_TASKS_TOOL_DOC + GET_TASK_TOOL_DOC."
  - "LIST_PROJECTS_TOOL_DOC mentions `isSequential` / `dependsOnChildren` with an explicit 'tasks-only' disambiguating note. The guard test `test_list_projects_tool_doc_does_not_claim_is_sequential_on_projects` allows the mention iff 'tasks-only' is also present, so projects-only agents get the correct mental model without reading it as a project field."
  - "FLAG-08 is a PROOF-test, not an implementation. `extra='forbid'` was already active via CommandModel → StrictModel; the 15 new tests lock the current behavior. No source code under `contracts/` changed."
  - "Wave-3 boundary-guard tests (completesWithChildren + type currently rejected) are tagged `# REMOVE IN 56-06`. Plan 56-06 must remove or adapt them when opening the write surface for those two fields; they act as a regression guard that the plumbing works for the specific fields of interest, not just in general."
  - "Field-description constants placed in a new section of descriptions.py ahead of the existing `# --- Entities ---` block. Grouping keeps the Phase 56-05 FLAG-07 / HIER-01/02 additions together for future audit."

patterns-established:
  - "Tool-description byte-budget discipline: Claude Code caps MCP tool descriptions at 2048 bytes. Adding a behavioral paragraph to a near-cap description requires compensating compression. Monitor with `test_tool_descriptions_within_client_byte_limit` (already in place)."
  - "Tasks-only flag disambiguation in a shared-surface doc: when a flag is task-only but the projects doc might otherwise seem to include it, add a single 'tasks-only' sentence instead of pretending the flag doesn't exist."

requirements-completed: [FLAG-07, FLAG-08]

duration: ~10min
completed: 2026-04-19
---

# Phase 56 Plan 05: Agent-Facing Descriptions & FLAG-08 Rejection Proof Summary

**Tool descriptions now surface the behavioral meaning of the two load-bearing derived flags (`dependsOnChildren`, `isSequential`) verbatim per CONTEXT.md, the `hierarchy` include group expansion from HIER-01/02 is documented, and `extra='forbid'` rejection of all six derived read-only flags is proven via parametrized contract tests — with two Wave-3 boundary guards marking the fields plan 56-06 must open.**

## Performance

- **Duration:** ~10 min
- **Tasks:** 2 (both TDD)
- **Files modified:** 7 (1 descriptions, 4 models, 2 test files)

## Accomplishments

- 8 new description constants in `agent_messages/descriptions.py`:
  - **Shared presence flags:** `HAS_NOTE_DESC`, `HAS_REPETITION_DESC`, `HAS_ATTACHMENTS_DESC`, `COMPLETES_WITH_CHILDREN_DESC`.
  - **Tasks-only derived flags:** `IS_SEQUENTIAL_DESC`, `DEPENDS_ON_CHILDREN_DESC` — FLAG-07 behavioral phrases verbatim-locked (`real task waiting on children`, `collapsible grouping`, `only the next-in-line child is available`, `over-count`).
  - **Per-type enums:** `TASK_TYPE_DESC`, `PROJECT_TYPE_DESC` — HIER-05 precedence note included in the project enum description.
- `LIST_TASKS_TOOL_DOC`, `GET_TASK_TOOL_DOC`, `LIST_PROJECTS_TOOL_DOC` rewritten:
  - `include.hierarchy` expanded to `parent/folder, hasChildren, type, completesWithChildren`.
  - `Default fields` line lists the shared presence flags (all three surfaces) and the two task-only derived flags (tasks only).
  - `Behavioral flags` bullet block inserted into `LIST_TASKS_TOOL_DOC` and `GET_TASK_TOOL_DOC` with the FLAG-07 locked phrases.
  - `LIST_PROJECTS_TOOL_DOC` carries the 'tasks-only' disambiguating note for `isSequential` / `dependsOnChildren`.
  - `LIST_TASKS_TOOL_DOC` compressed to 2034 bytes (from initial 2522) to stay under the Claude Code 2048-byte MCP tool-description limit.
- `TaskType` / `ProjectType` enums switched from inline `#` comments to `__doc__ = CONSTANT` pattern (DESC-03 compliant).
- Model fields `Field(description=CONSTANT)` wiring:
  - `ActionableEntity`: `has_note`, `has_repetition`, `has_attachments`, `completes_with_children`.
  - `Task`: `type`, `is_sequential`, `depends_on_children`.
  - `Project`: `type`.
- FLAG-08 contract proof: 15 new tests in `tests/test_contracts_field_constraints.py` — 12 parametrized (6 derived flags × 2 commands) asserting `extra_forbidden` error at the exact field location, 1 no-custom-message negative assertion locking T-56-15, and 2 Wave-3 boundary guards marked `# REMOVE IN 56-06`.

## Task Commits

1. **Task 1 RED — failing tests for FLAG-07 descriptions and HIER-01/02 include expansion** — `77c474d9` (test)
   - 5 new test classes in `tests/test_descriptions.py`: constants-exist, behavioral-phrase-lock, tool-doc-coverage, enum-docstring-pattern, model-field-description.

2. **Task 1 GREEN — FLAG-07 behavioral descriptions + HIER-01/02 include expansion** — `e81f509f` (feat)
   - 8 new constants in descriptions.py.
   - 3 tool-doc rewrites with tightened narrative to fit the 2048-byte Claude Code MCP limit.
   - TaskType / ProjectType `__doc__ = CONSTANT`.
   - Model fields on ActionableEntity, Task, Project use `Field(description=CONSTANT)`.

3. **Task 2 — FLAG-08 rejection proof (parametrized contract tests)** — `d4d5210c` (test)
   - `TestAddTaskCommandRejectsDerivedFlags` (6 parametrized + 1 no-custom-message = 7 tests).
   - `TestEditTaskCommandRejectsDerivedFlags` (6 parametrized).
   - `TestWave3BoundaryGuards` (2 tests marked `# REMOVE IN 56-06`).
   - No source code changed — `extra='forbid'` already active via `CommandModel` → `StrictModel`.

_Plan metadata commit is owned by the orchestrator (STATE.md / ROADMAP.md) per this plan's objective._

## Files Created/Modified

Source:
- `src/omnifocus_operator/agent_messages/descriptions.py` — 8 new constants + 3 tool-doc rewrites.
- `src/omnifocus_operator/models/enums.py` — TaskType/ProjectType switched to `__doc__ = CONSTANT`.
- `src/omnifocus_operator/models/common.py` — `Field(description=CONSTANT)` on 4 presence flags.
- `src/omnifocus_operator/models/task.py` — `Field(description=CONSTANT)` on type/is_sequential/depends_on_children.
- `src/omnifocus_operator/models/project.py` — `Field(description=PROJECT_TYPE_DESC)`.

Tests:
- `tests/test_descriptions.py` — 5 new classes, 17 tests.
- `tests/test_contracts_field_constraints.py` — 3 new classes, 15 tests (incl. 2 Wave-3 boundary guards).

## Test Counts Added

- `tests/test_descriptions.py`: **+17** tests (36 total in file now; 17 were new for 56-05).
- `tests/test_contracts_field_constraints.py`: **+15** tests (34 → 49 in file).

Overall pytest suite: **2 343 passed** (was 2 328 at task 1 completion; +15 from task 2, or +42 from 56-04's 2 301 baseline — the extra +27 includes parametrized expansions already counted at 56-04 close).

## Decisions Made

- **Byte budget discipline on LIST_TASKS_TOOL_DOC.** Initial draft after adding the Behavioral flags block plus 5 default-response field names landed at 2522 bytes — 474 over the 2048-byte Claude Code cap. Compensated by tightening the narrative ("Returns a flat list. Reconstruct hierarchy using …" → "Flat list; reconstruct hierarchy via …"), inlining the inheritance explanation as a tight sentence instead of the full `_INHERITED_TASKS_EXPLANATION` fragment, and dropping the closing "availability vs defer" sentence (already covered in `DEFER_FILTER_DESC`). Final: 2034 bytes. FLAG-07 phrases preserved verbatim in the relevant description constants and the tool doc.
- **Tasks-only disambiguation on the projects doc.** `LIST_PROJECTS_TOOL_DOC` mentions `isSequential` / `dependsOnChildren` with an explicit "tasks-only" sentence. The guard test allows the mention iff 'tasks-only' is present, so project-facing agents get the accurate mental model (these flags exist but only on tasks). Preferred over the alternative (pretend the flags don't exist) because the agent may be switching between list_tasks and list_projects in the same session.
- **FLAG-08 is a PROOF-test, not an implementation.** `extra='forbid'` was already active via `CommandModel` → `StrictModel`. The 15 new tests lock that behavior for the specific 6 fields called out in FLAG-08, plus 2 Wave-3 boundary guards for `completesWithChildren` + `type`. No source under `contracts/` changed; Task 2's RED/GREEN was a single step (tests immediately green).
- **Wave-3 boundary guards marked `# REMOVE IN 56-06`.** These are regression guards that prove the plumbing rejects the exact fields Wave 3 will open — not just derived flags in general. Plan 56-06 must remove them when it opens the write surface for `completesWithChildren` + `type`. Explicit marker comment ensures the removal isn't forgotten.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking issue] LIST_TASKS_TOOL_DOC exceeded Claude Code's 2048-byte MCP tool-description limit**
- **Found during:** Task 1 GREEN (first full run of `tests/test_descriptions.py`).
- **Issue:** After inserting the FLAG-07 Behavioral flags block and expanding the default-fields line with five new names, `LIST_TASKS_TOOL_DOC` landed at 2522 bytes — 474 over the 2048-byte cap enforced by `TestToolDescriptionEnforcement::test_tool_descriptions_within_client_byte_limit`.
- **Fix:** Tightened narrative prose elsewhere in the docstring (sentence-level compression, dropped "availability vs defer" closing line that DEFER_FILTER_DESC already owns, inlined a tight inheritance sentence instead of the 395-byte `_INHERITED_TASKS_EXPLANATION` fragment). Preserved the full behavioral phrase block verbatim — FLAG-07 locks that text.
- **Files modified:** `src/omnifocus_operator/agent_messages/descriptions.py`.
- **Verification:** `uv run pytest tests/test_descriptions.py -x -q` — 36 tests pass (was failing on the byte-budget guard).
- **Committed in:** `e81f509f` (Task 1 GREEN commit).

---

**Total deviations:** 1 auto-fixed (blocking issue). No scope creep; FLAG-07 contract intact.

## Issues Encountered

- None beyond the byte budget. The `extra='forbid'` baseline made Task 2 a zero-change test addition.

## User Setup Required

None.

## Next Phase Readiness

- **Plan 56-06 (Wave 3 write surface)** can now open `completesWithChildren` + `type` with high confidence the extra='forbid' guarantee on the other 6 derived flags is proven. The two `# REMOVE IN 56-06` guards must be removed or adapted (e.g. flipped to "accepted with correct patch semantics") by that plan.
- **Plan 56-07 (PROP-07 + round-trip + golden master scaffolding)** is independent of this plan.
- No blockers introduced. No `RealBridge` references anywhere in the new tests (SAFE-01 satisfied). No inline descriptions in models/ or contracts/ (DESC-03 enforcement passes).

## Threat Flags

No new security-relevant surface. All changes are:
- Description text in `agent_messages/descriptions.py` (pure strings, agent-visible).
- `Field(description=…)` on core model fields (pure schema metadata).
- Contract tests for existing `extra='forbid'` behavior (no validator changes).

T-56-14 mitigation (Elevation of Privilege via derived flags on write) — confirmed by 12 parametrized rejection tests × 2 commands.
T-56-15 mitigation (Information Disclosure via custom error leaking internal derivation logic) — confirmed by `test_add_task_command_error_contains_no_custom_message_for_derived_flags` with explicit negative assertions on bespoke phrases.
T-56-16 mitigation (Tampering via tool description failing to communicate behavioral meaning) — confirmed by grep-verified verbatim presence of the FLAG-07 locked phrases in LIST_TASKS_TOOL_DOC + GET_TASK_TOOL_DOC and in the dedicated description constants.

## Self-Check: PASSED

- FOUND: `src/omnifocus_operator/agent_messages/descriptions.py` (modified)
- FOUND: `src/omnifocus_operator/models/enums.py` (modified)
- FOUND: `src/omnifocus_operator/models/common.py` (modified)
- FOUND: `src/omnifocus_operator/models/task.py` (modified)
- FOUND: `src/omnifocus_operator/models/project.py` (modified)
- FOUND: `tests/test_descriptions.py` (modified)
- FOUND: `tests/test_contracts_field_constraints.py` (modified)
- FOUND: commit `77c474d9` (Task 1 RED)
- FOUND: commit `e81f509f` (Task 1 GREEN)
- FOUND: commit `d4d5210c` (Task 2)
- VERIFIED: `grep -n "DEPENDS_ON_CHILDREN_DESC\s*=" src/omnifocus_operator/agent_messages/descriptions.py` — 1 match.
- VERIFIED: `grep -n "IS_SEQUENTIAL_DESC\s*=" src/omnifocus_operator/agent_messages/descriptions.py` — 1 match.
- VERIFIED: `grep -c "real task waiting on children" src/omnifocus_operator/agent_messages/descriptions.py` — 1 verbatim match in DEPENDS_ON_CHILDREN_DESC (FLAG-07 lock).
- VERIFIED: `grep -c "only the next-in-line child is available" src/omnifocus_operator/agent_messages/descriptions.py` — 3 occurrences (constant + tool docs).
- VERIFIED: `grep -c "dependsOnChildren" src/omnifocus_operator/agent_messages/descriptions.py` — 6 occurrences (LIST_TASKS_TOOL_DOC, GET_TASK_TOOL_DOC, LIST_PROJECTS_TOOL_DOC, DEPENDS_ON_CHILDREN_DESC body, plus Default fields + Behavioral flags lists).
- VERIFIED: `grep -n "Field(description=HAS_NOTE_DESC)" src/omnifocus_operator/models/common.py` — 1 match.
- VERIFIED: `grep -n "Field(default=False, description=IS_SEQUENTIAL_DESC)" src/omnifocus_operator/models/task.py` — 1 match.
- VERIFIED: `grep -n "__doc__ = TASK_TYPE_DESC" src/omnifocus_operator/models/enums.py` — 1 match.
- VERIFIED: `grep -c "REMOVE IN 56-06" tests/test_contracts_field_constraints.py` — 2 matches (Wave-3 boundary guards).
- VERIFIED: `grep -c "_DERIVED_READONLY_FLAGS" tests/test_contracts_field_constraints.py` — 3 matches (definition + 2 class usages).
- VERIFIED: `grep "RealBridge" tests/test_contracts_field_constraints.py tests/test_descriptions.py` — no results (SAFE-01).
- VERIFIED: `uv run pytest tests/test_descriptions.py tests/test_contracts_field_constraints.py tests/test_output_schema.py tests/test_models.py --no-cov -q` — 241 tests pass.
- VERIFIED: `uv run pytest tests/ --no-cov -q` — 2 343 tests pass, 0 failures.
- VERIFIED: `uv run mypy src/omnifocus_operator/` — Success: no issues found in 79 source files.
- VERIFIED: LIST_TASKS_TOOL_DOC = 2034 bytes (under 2048 cap); GET_TASK_TOOL_DOC = 1449 bytes; LIST_PROJECTS_TOOL_DOC = 1447 bytes.

---
*Phase: 56-task-property-surface*
*Completed: 2026-04-19*
