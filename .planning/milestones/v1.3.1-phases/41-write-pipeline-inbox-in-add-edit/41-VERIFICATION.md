---
phase: 41-write-pipeline-inbox-in-add-edit
verified: 2026-04-06T14:00:00Z
status: passed
score: 12/12 must-haves verified
gaps: []
---

# Phase 41: Write Pipeline — $inbox in Add/Edit Verification Report

**Phase Goal:** Agents can explicitly target inbox in all write operations using `$inbox`, with clear errors for invalid null usage
**Verified:** 2026-04-06
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `add_tasks` with `parent: "$inbox"` creates task in inbox; omitted parent defaults to inbox; `parent: null` returns error | ✓ VERIFIED | `AddTaskCommand.parent: Patch[str] = UNSET`; `_reject_null_parent` validator; `_resolve_parent` uses `is_set()` guard; 4 contract tests + 3 service pipeline tests |
| 2 | `edit_tasks` with `ending: "$inbox"` or `beginning: "$inbox"` moves task to inbox | ✓ VERIFIED | `MoveAction` fields are `Patch[str]`; `resolve_container("$inbox")` returns None; `test_ending_inbox_moves_to_inbox` and `test_beginning_inbox_moves_to_inbox` in test_service.py |
| 3 | `ending: null` and `beginning: null` return errors (not silently accepted) | ✓ VERIFIED | `_reject_null_container` field_validator on both fields; `test_beginning_null_rejected` / `test_ending_null_rejected` in test_contracts_field_constraints.py |
| 4 | `before`/`after` with a container ID or `$inbox` returns targeted error suggesting `beginning`/`ending` | ✓ VERIFIED | `_reject_null_anchor` on before/after; `test_before_inbox_rejected` confirms `$inbox` as anchor raises "is a project" cross-type error |
| 5 | `PatchOrNone` type alias deleted; `MoveAction.beginning`/`ending` use `Patch[str]` | ✓ VERIFIED | Zero matches for `PatchOrNone` in src/ and tests/; `contracts/base.py` __all__ contains only `Patch`, `PatchOrClear`; both MoveAction container fields are `Patch[str]` |

**Score:** 5/5 roadmap success criteria verified

### Plan-level Truths (from PLAN frontmatter)

| # | Truth (Plan 01) | Status | Evidence |
|---|-----------------|--------|----------|
| P1-1 | PatchOrNone no longer exists anywhere in codebase | ✓ VERIFIED | `grep -r "PatchOrNone" src/` → no matches; `grep -r "PatchOrNone" tests/` → no matches |
| P1-2 | TagAction.replace uses PatchOrClear[list[str]] with zero behavioral change | ✓ VERIFIED | `replace: PatchOrClear[list[str]] = Field(default=UNSET, ...)` in actions.py; output schema tests pass (32 passed) |
| P1-3 | MoveAction.beginning and ending use Patch[str] — null rejected with educational error | ✓ VERIFIED | Fields confirmed; validator `_reject_null_container` present; error text matches D-14 verbatim |
| P1-4 | MoveAction.before and after reject null with educational error | ✓ VERIFIED | Validator `_reject_null_anchor` present; message references before/after and suggests beginning/ending |
| P1-5 | MoveAction fields have per-field descriptions in JSON schema | ✓ VERIFIED | `MOVE_BEGINNING`, `MOVE_ENDING`, `MOVE_BEFORE`, `MOVE_AFTER` constants in descriptions.py; all four fields use `Field(description=...)` |
| P1-6 | All existing tests still pass | ✓ VERIFIED | Full suite: 1593 passed |

| # | Truth (Plan 02) | Status | Evidence |
|---|-----------------|--------|----------|
| P2-1 | add_tasks with parent omitted creates task in inbox (UNSET → inbox) | ✓ VERIFIED | `if not is_set(self._command.parent): return` in `_resolve_parent`; `test_parent_omitted_creates_inbox_task` passes |
| P2-2 | add_tasks with parent '$inbox' creates task in inbox | ✓ VERIFIED | `resolve_container("$inbox")` returns None; `test_parent_inbox_resolves_to_inbox` passes |
| P2-3 | add_tasks with parent null returns educational error | ✓ VERIFIED | `_reject_null_parent` raises ValueError(ADD_PARENT_NULL); `test_parent_null_rejected` confirms message "parent cannot be null" |
| P2-4 | edit_tasks with ending '$inbox' moves task to inbox | ✓ VERIFIED | `test_ending_inbox_moves_to_inbox` passes |
| P2-5 | edit_tasks with beginning '$inbox' moves task to inbox | ✓ VERIFIED | `test_beginning_inbox_moves_to_inbox` passes |
| P2-6 | before/after with container ID or $inbox returns targeted error suggesting beginning/ending | ✓ VERIFIED | `test_before_inbox_rejected` passes; ENTITY_TYPE_MISMATCH_ANCHOR error template contains "use 'ending' or 'beginning' instead" |
| P2-7 | REQUIREMENTS.md WRIT-03 reflects revised wording (error, not warning) | ✓ VERIFIED | Line contains "returns error (null not accepted; omit field for inbox or use `$inbox`)" |

**Score:** 12/12 plan-level must-haves verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/contracts/base.py` | PatchOrNone removed; PatchOrClear present | ✓ VERIFIED | `__all__` has `Patch`, `PatchOrClear`; no PatchOrNone anywhere |
| `src/omnifocus_operator/contracts/shared/actions.py` | Updated TagAction.replace and MoveAction with null validators | ✓ VERIFIED | Contains `PatchOrClear`, `Patch[str]`, `_reject_null_container`, `_reject_null_anchor`, `MOVE_NULL_CONTAINER`, `MOVE_NULL_ANCHOR` |
| `src/omnifocus_operator/agent_messages/errors.py` | Error templates for null container/anchor/parent | ✓ VERIFIED | `MOVE_NULL_CONTAINER`, `MOVE_NULL_ANCHOR`, `ADD_PARENT_NULL` all present with verbatim wording |
| `src/omnifocus_operator/contracts/use_cases/add/tasks.py` | AddTaskCommand.parent as Patch[str] with null rejection | ✓ VERIFIED | `parent: Patch[str] = Field(default=UNSET, ...)`, `_reject_null_parent` validator, `ADD_PARENT_NULL` imported |
| `src/omnifocus_operator/service/service.py` | UNSET-aware `_resolve_parent` in `_AddTaskPipeline` | ✓ VERIFIED | `if not is_set(self._command.parent): return` (old `is None` check confirmed absent) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `contracts/shared/actions.py` | `agent_messages/errors.py` | field_validator raises ValueError with MOVE_NULL_CONTAINER / MOVE_NULL_ANCHOR | ✓ WIRED | Both validators import and use the templates with `.format(field=info.field_name)` |
| `contracts/shared/actions.py` | `middleware.py` | ValidationReformatterMiddleware catches Pydantic ValidationError | ✓ WIRED | Pattern already established from Phase 40; full test suite passes confirming middleware integration |
| `contracts/use_cases/add/tasks.py` | `service/service.py` | `_AddTaskPipeline` reads `command.parent` with `is_set()` guard | ✓ WIRED | `if not is_set(self._command.parent): return` at line 449 |
| `service/service.py` | `service/resolve.py` | `resolve_container("$inbox")` returns None → inbox | ✓ WIRED | Service calls `self._resolver.resolve_container(self._command.parent)` when parent is_set; resolver handles `$inbox` returning None |

### Data-Flow Trace (Level 4)

Not applicable — this phase modifies contract validation and service pipeline logic, not data-rendering components. The "data" here is Pydantic ValidationErrors and bridge payloads, verified through test assertions rather than render inspection.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| MoveAction null rejection works | `uv run pytest tests/test_contracts_field_constraints.py -x -q` | 36 passed | ✓ PASS |
| AddTaskCommand null rejection works | included above | 36 passed | ✓ PASS |
| Inbox pipeline integration | `uv run pytest tests/test_service.py -x -q -k "inbox or Inbox"` | 9 passed | ✓ PASS |
| Full test suite | `uv run pytest tests/ -x -q --timeout=120` | 1593 passed, 98.30% coverage | ✓ PASS |
| Output schema unchanged | `uv run pytest tests/test_output_schema.py -x -q` | 32 passed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MODL-09 | Plan 01 | `PatchOrNone` type alias eliminated from `contracts/base.py` | ✓ SATISFIED | No PatchOrNone in src/ or tests/; not in __all__ |
| MODL-10 | Plan 01 | `MoveAction.beginning`/`ending` use `Patch[str]` (not `PatchOrNone[str]`) | ✓ SATISFIED | Both fields confirmed as `Patch[str]` with `Field(description=...)` |
| WRIT-01 | Plan 02 | `add_tasks` with `parent: "$inbox"` creates task in inbox | ✓ SATISFIED | Pipeline + integration test |
| WRIT-02 | Plan 02 | `add_tasks` with `parent` omitted creates task in inbox | ✓ SATISFIED | UNSET guard in `_resolve_parent` + integration test |
| WRIT-03 | Plan 02 | `add_tasks` with `parent: null` returns error (null not accepted) | ✓ SATISFIED | `_reject_null_parent` validator + contract test |
| WRIT-04 | Plan 02 | `edit_tasks` with `ending: "$inbox"` moves task to inbox | ✓ SATISFIED | Integration test `test_ending_inbox_moves_to_inbox` |
| WRIT-05 | Plan 02 | `edit_tasks` with `beginning: "$inbox"` moves task to inbox | ✓ SATISFIED | Integration test `test_beginning_inbox_moves_to_inbox` |
| WRIT-06 | Plan 01 | `edit_tasks` with `ending: null` returns error | ✓ SATISFIED | `_reject_null_container` on `ending`; `test_ending_null_rejected` |
| WRIT-07 | Plan 01 | `edit_tasks` with `beginning: null` returns error | ✓ SATISFIED | `_reject_null_container` on `beginning`; `test_beginning_null_rejected` |
| WRIT-08 | Plan 01 + 02 | `before`/`after` with container ID or `$inbox` returns targeted error | ✓ SATISFIED | `_reject_null_anchor` + cross-type resolver error; `test_before_inbox_rejected` |

Note: REQUIREMENTS.md traceability table shows all Phase 41 requirements as "Pending" (checkbox not marked `[x]`). This is a documentation state, not an implementation gap — the requirements are fully implemented in code. REQUIREMENTS.md checkbox update is not in scope for this phase.

### Anti-Patterns Found

None. No TODOs, FIXMEs, placeholder returns, or stubs found in modified files.

### Human Verification Required

None. All observable behaviors are verified programmatically through the test suite.

### Gaps Summary

No gaps. All 12 must-haves verified, 10/10 requirements satisfied, 1593 tests pass.

---

_Verified: 2026-04-06_
_Verifier: Claude (gsd-verifier)_
