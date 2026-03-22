---
gsd_state_version: 1.0
milestone: v1.2.1
milestone_name: Architectural Cleanup
status: Ready to execute
stopped_at: Completed 28-01-PLAN.md
last_updated: "2026-03-22T18:05:11.229Z"
last_activity: 2026-03-22
progress:
  total_phases: 11
  completed_phases: 10
  total_plans: 27
  completed_plans: 24
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-21)

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.
**Current focus:** Phase 28 — expand-golden-master-coverage-and-improve-field-normalization

## Current Position

Phase: 28 (expand-golden-master-coverage-and-improve-field-normalization) — EXECUTING
Plan: 3 of 4

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

## Accumulated Context

| Phase 18 P02 | 5min | 2 tasks | 3 files |
| Phase 18 P01 | 6min | 2 tasks | 6 files |
| Phase 19 P01 | 7min | 3 tasks | 10 files |
| Phase 20 P01 | 5min | 2 tasks | 7 files |
| Phase 20 P02 | 21min | 2 tasks | 15 files |
| Phase 21 P01 | 3min | 2 tasks | 1 files |
| Phase 21 P02 | 3min | 1 tasks | 5 files |
| Phase 22 P01 | 12min | 2 tasks | 6 files |
| Phase 22 P02 | 4min | 2 tasks | 3 files |
| Phase 22 P03 | 3min | 2 tasks | 6 files |
| Phase 22-04 P04 | 3min | 1 tasks | 5 files |
| Phase 23 P01 | 6min | 2 tasks | 10 files |
| Phase 24 P01 | 5min | 2 tasks | 15 files |
| Phase 25 P01 | 5min | 1 tasks | 5 files |
| Phase 26 P01 | 5min | 1 tasks | 2 files |
| Phase 26 P02 | 12min | 2 tasks | 10 files |
| Phase 26 P04 | 5min | 2 tasks | 3 files |
| Phase 26 P05 | 8min | 1 tasks | 1 files |
| Phase 26 P03 | 7min | 2 tasks | 7 files |
| Phase 27 P01 | 4min | 2 tasks | 5 files |
| Phase 27 P03 | 6min | 2 tasks | 3 files |
| Phase 27 P04 | multi-session | 3 tasks | 35 files |
| Phase 28 P02 | 4min | 2 tasks | 2 files |
| Phase 28 P01 | 7min | 3 tasks | 3 files |

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: STRCT before MODL (validate Pydantic extra="forbid" + sentinel in isolation before model renames)
- Roadmap: MODL before PIPE (typed payloads must exist before unifying pipeline around them)
- Roadmap: SVCR merged into single Phase 22 (package conversion + all extractions in one phase)
- [Phase 18]: Warning constants use {placeholder} syntax with .format() for parameterized messages
- [Phase 18]: AST-based integrity test ensures no inline warning strings regress into service.py
- [Phase 18]: WriteModel base with extra=forbid for strict write-side validation
- [Phase 18]: Result models stay on OmniFocusBaseModel (permissive) -- server output, not agent input
- [Phase 19]: Tool-calling server tests use monkeypatched InMemoryRepository instead of factory path
- [Phase 19]: Test doubles imported via direct module paths, not package re-exports
- [Phase quick-260317-lgu]: Filter status warnings by content match rather than clearing all, preserving action-specific no-op warnings
- [Phase 20]: Tasks 1+2 committed together due to mypy requiring use_cases modules for protocols.py TYPE_CHECKING imports
- [Phase 20]: MoveAction/TagAction imports in edit_task.py under TYPE_CHECKING per ruff TC001, resolved by model_rebuild
- [Phase 20]: edit_task repos use exclude_unset=True to preserve null-means-clear semantics
- [Phase 20]: Service builds EditTaskRepoPayload via model_validate with dynamic kwargs dict
- [Phase 21]: add_task uses kwargs dict with only populated fields instead of passing all fields to constructor
- [Phase 21]: edit_task builds snake_case payload dict from the start, eliminating _payload_to_repo mapping
- [Phase 21]: Mixin uses TYPE_CHECKING guard for Bridge and OmniFocusBaseModel imports (no runtime circular deps)
- [Phase 22]: Used model_fields_set for no-op detection (null-means-clear correctness)
- [Phase 22]: DomainLogic tests use StubResolver/StubRepo instead of InMemoryRepository -- future-proofs for Phase 26
- [Phase 22]: service.py import update pulled into Task 1 commit (pre-commit mypy requires consistent imports)
- [Phase 22]: Container move type-check stays as direct repo access (not resolution, verified by plan)
- [Phase 22]: Fail-fast assert in _apply_replace instead of defensive fallback -- bypassing normalization is a bug
- [Phase 22]: normalize_clear_intents returns new command via model_copy (immutable normalization pattern)
- [Phase 23]: PYTEST guard uses type(self) is RealBridge so subclasses bypass automatically
- [Phase 23]: Repository factory creates RealBridge directly -- no OMNIFOCUS_BRIDGE env var or bridge factory
- [Phase 23]: Bridge factory deleted, SimulatorBridge/create_bridge removed from package exports
- [Phase 24]: ConstantMtimeSource and FileMtimeSource explicitly inherit MtimeSource protocol (was structural)
- [Phase 24]: tests/doubles/ established as canonical location for all test doubles
- [Phase 25]: TypeVar+Union approach for Patch/PatchOrClear/PatchOrNone aliases (clean JSON schema + mypy pass)
- [Phase 25]: PatchOrNone[T] as distinct alias from PatchOrClear[T] for domain-meaningful None values (e.g., inbox)
- [Phase 25]: changed_fields() on CommandModel base class, complementing is_set() TypeGuard for per-field branching
- [Phase 26]: Backward-compatible stub mode: auto-detect snapshot vs stub data to avoid breaking existing tests
- [Phase 26]: Inline BridgeRepository construction for custom-snapshot tests; fixture injection for defaults (per D-11/D-12/D-13)
- [Phase 26]: Late imports in conftest.py fixtures to break circular dependency with tests.doubles.bridge
- [Phase 26]: Removed InMemoryBridge/make_snapshot_dict imports from test_service.py after full fixture migration; BridgeRepository moved to TYPE_CHECKING
- [Phase 26]: StubBridge extracted as separate canned-response test double; InMemoryBridge cleaned of dual-mode _stateful logic
- [Phase 27]: Extracted _resolve_parent as shared helper reused by both add_task and edit_task moveTo
- [Phase 27]: Pre-compute containing_project_map before task conversion to avoid iteration-order bug in raw format conversion
- [Phase 27]: test_move_to_project_ending asserts parent.type=='task' matching golden master scenario_16 (OmniFocus real behavior)
- [Phase 27]: VOLATILE/UNCOMPUTED field split: removing a field from UNCOMPUTED auto-enables contract verification
- [Phase 27]: status/taskStatus excluded as UNCOMPUTED (OmniFocus status computation intentionally out of scope for InMemoryBridge)
- [Phase 27]: hasChildren computed by InMemoryBridge on add_task and moveTo (required for contract test correctness)
- [Phase 28]: 43 scenarios total (6+11+7+5+4+3+7) in 7 numbered subfolder categories
- [Phase 28]: Followup add_task support in _capture_scenario for inheritance chain ID tracking
- [Phase 28]: Backward-compatible key restriction (_restrict_to_expected_keys) for golden master transition during field graduation
- [Phase 28]: effectiveCompletionDate/effectiveDropDate set directly during lifecycle (not via inheritance)

### Pending Todos

Carried from v1.0:

1. Add retry logic for OmniFocus bridge timeouts (v1.6)
2. Investigate macOS App Nap impact on OmniFocus responsiveness (v1.6)
3. Make UAT folder discoverable for verification agents
4. Investigate `replace: []` bug in production (may not be staleness-related)

### Roadmap Evolution

- Phase 23 added: SimulatorBridge and factory cleanup (deferred from Phase 19 discussion)
- Phase 25 added: Patch/PatchOrClear type aliases for command models (from sentinel pattern deep dive)
- Phase 26 added: Replace InMemoryRepository with stateful InMemoryBridge (from phase 21 UAT discussion)
- Phase 27 added: Repository contract tests for behavioral equivalence (from todo — proves InMemory/Real equivalence after Phase 26 merge)
- Phase 28 added: Expand golden master coverage and normalize lifecycle date fields

### Blockers/Concerns

None currently.

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260317-j2x | Fix F-6: Echo invalid lifecycle value in error message | 2026-03-17 | 89ba983 |  | [260317-j2x-fix-f-6-echo-invalid-lifecycle-value-in-](./quick/260317-j2x-fix-f-6-echo-invalid-lifecycle-value-in-/) |
| 260317-lgu | Fix D-6b: Suppress status warning on no-op edit of completed/dropped tasks | 2026-03-17 | 0f852a3 | Verified | [260317-lgu-fix-d-6b-suppress-status-warning-when-ed](./quick/260317-lgu-fix-d-6b-suppress-status-warning-when-ed/) |
| 260319-tlz | Make Bridge protocol explicitly implemented by all bridge classes | 2026-03-20 | 347c168 |  | [260319-tlz-make-bridge-protocol-explicitly-implemen](./quick/260319-tlz-make-bridge-protocol-explicitly-implemen/) |
| 260320-jd6 | Add is_set TypeGuard helper to replace isinstance Unset checks | 2026-03-20 | 2661e2e | Verified | [260320-jd6-add-is-set-typeguard-helper-to-replace-i](./quick/260320-jd6-add-is-set-typeguard-helper-to-replace-i/) |
| 260320-k6u | Centralize agent-facing messages into agent_messages/ package | 2026-03-20 | 1ccd86d | Verified | [260320-k6u-centralize-agent-facing-messages-into-me](./quick/260320-k6u-centralize-agent-facing-messages-into-me/) |
| 260320-ut2 | Fix CI SAFE-01 grep check that falsely flags legitimate RealBridge references | 2026-03-20 | 8871f03 |  | [260320-ut2-fix-ci-safe-01-grep-check-that-falsely-f](./quick/260320-ut2-fix-ci-safe-01-grep-check-that-falsely-f/) |
| 260320-v9f | Eliminate all SAFE-01 violations: replace delenv with monkeypatch in 12 tests | 2026-03-20 | 45e1b1a |  | [260320-v9f-eliminate-all-safe-01-violations-remove-](./quick/260320-v9f-eliminate-all-safe-01-violations-remove-/) |

## Session Continuity

Last activity: 2026-03-22
Stopped at: Completed 28-01-PLAN.md
Resume file: None
