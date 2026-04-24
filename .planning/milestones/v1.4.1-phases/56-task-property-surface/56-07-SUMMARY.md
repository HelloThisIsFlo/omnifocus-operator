---
phase: 56-task-property-surface
plan: 07
subsystem: wave-3-closure
tags: [prop-07, round-trip, golden-master, parallel-wave, scaffolding]

requires:
  - phase: 56-task-property-surface
    plan: 02
    provides: "TaskType enum + ActionableEntity.completes_with_children on models"
  - phase: 56-task-property-surface
    plan: 04
    provides: "projection + NEVER_STRIP (feeds the read shape this plan locks)"
  - phase: 56-task-property-surface
    plan: 06
    provides: "AddTask/EditTask Patch[bool] + Patch[TaskType] write surface + InMemoryBridge round-trip storage"

provides:
  - "PROP-07 structural guardrail: 3 tests in test_server.py asserting no `add_projects*` / `edit_projects*` tools registered on the MCP server in v1.4.1"
  - "End-to-end round-trip coverage: 7 test methods x 2 repos = 14 parametrized runs covering agent-value path + create-default path through the full OperatorService stack on both HybridRepository and BridgeOnlyRepository"
  - "Golden master scaffolding: `tests/golden_master/test_task_property_surface_golden.py` with opt-in-capture / skip-when-missing infrastructure; `tests/golden_master/snapshots/README.md` documenting the human-only capture procedure"
  - "A parametrized `cross_service` fixture yielding `{service, bridge, repo, preferences, rehydrate}` for Wave-3 integration tests on both repositories"
  - "A test-only SQLite rehydration helper `_rehydrate_sqlite_from_bridge` that mirrors OmniFocus's write-through to the cache (Hybrid round-trip tests call it between writes and reads)"

affects:
  - "v1.7 Phase 60 (project writes): PROP-07 tests WILL FAIL when `add_projects` / `edit_projects` tools land — that failure is the intended checkpoint forcing v1.7 authors to parallel-cover PROP-01..06 on the new surface."

tech-stack:
  added: []
  patterns:
    - "Feature-gate skip for parallel-wave dependency coupling: tests that need 56-06's write surface feature-detect `AddTaskCommand.model_fields` for `completes_with_children` and `type`, skipping cleanly when the fields aren't present yet. Safe execution order regardless of which Wave-3 plan lands first."
    - "Golden-master capture gate via env var + invariant test: capture branch behind `GOLDEN_MASTER_CAPTURE=1`; a dedicated invariant test asserts the env var is unset during regular runs, blocking accidental automated capture."
    - "Normalization-in-place helper for shape-contract golden masters: recursive volatile-key (`id`, `url`, `added`, `modified`) substitution with `\"<normalized>\"` sentinel (simpler than the entity-dispatch normalization used by bridge-contract snapshots)."
    - "SQLite rehydrate-from-bridge helper for HybridRepository round-trip tests: stands in for OmniFocus's live write-through to the cache. Writes go through the bridge, test code re-derives the SQLite fixture from the bridge snapshot, then reads pick up the change. Keeps the read path unmodified."

key-files:
  created:
    - "tests/golden_master/test_task_property_surface_golden.py -- comparison + opt-in capture; 2 tests (1 invariant + 1 gated comparison)"
    - "tests/golden_master/snapshots/README.md -- human-only capture/refresh/review/commit procedure"
  modified:
    - "tests/test_server.py -- `TestPROP07ProjectWritesNotYetAvailable` class, 3 tests"
    - "tests/test_cross_path_equivalence.py -- `TestTaskPropertySurfaceRoundTrip` class, 7 test methods (14 parametrized runs); new `cross_service` fixture + `_rehydrate_sqlite_from_bridge` helper + `_post_56_06_write_surface_present` feature detector"

key-decisions:
  - "PROP-07 via the FastMCP `Client(server).list_tools()` pattern (NOT source grep). The test inspects the actually-registered tools at runtime, so it catches registration bugs that a source-level grep would miss, and it's the same pattern already used elsewhere in test_server.py. The `client` fixture from conftest injects the full service stack, which matches the production startup sequence."
  - "Parallel-wave skip gate rather than hard failure. Since 56-06 and 56-07 both carry `wave: 3` and run in parallel worktrees, the round-trip tests feature-detect the post-56-06 `AddTaskCommand` surface and skip cleanly when absent. This keeps the plan executable in either merge order; once both have merged, the skip condition clears and the suite becomes the end-to-end Wave-3 proof."
  - "HybridRepository round-trip via test-only SQLite rehydration helper. HybridRepository in production reads from the OF SQLite cache (updated by OmniFocus via write-through) and writes via the bridge. In tests, OmniFocus isn't in the loop, so the SQLite fixture doesn't automatically reflect bridge writes. Rather than mock the read path or bypass SQLite entirely, the test calls `_rehydrate_sqlite_from_bridge` between writes and reads — cheap, explicit, and keeps the read path itself unmodified (so any SQL-layer regressions still surface)."
  - "Golden-master normalization via recursive volatile-key substitution, not the entity-dispatch pattern from `normalize.py`. The Phase-56 shape contract is service-level (OperatorService → serialized payload) rather than bridge-level. One generic normalizer is simpler than wiring per-entity volatile-field sets; the cost is a single `\"<normalized>\"` sentinel wherever an `id`/`url`/`added`/`modified` key appears at any depth. Acceptable for a shape contract."
  - "Capture gate requires BOTH env-var opt-in AND invariant test. Either check alone could be bypassed: env-var alone means a careless agent could unset the assertion and flip capture on; invariant-test alone doesn't prevent the capture branch from being reachable at all. Both together make capture explicit + noisy + documented. Agents cannot accidentally capture."

patterns-established:
  - "Parallel-wave skip gate: feature-detection on downstream plan's contract surface to avoid hard failures when parallel agents land in different orders. Apply to any cross-plan test suite that sits downstream of multiple parallel plans."
  - "HybridRepository write-through test rehydration: a test-only helper that re-derives the SQLite fixture from the InMemoryBridge snapshot after each write. Re-usable for any future Hybrid round-trip test."
  - "Dual-gate agent-safe capture: opt-in env var + invariant test together. Apply to any infrastructure an agent must not trigger by default."

requirements-completed: [PROP-07]

duration: ~12min
completed: 2026-04-19
---

# Phase 56 Plan 07: PROP-07 Structural Guardrail + Wave-3 Round-Trip + Golden Master Scaffolding Summary

**Closed Wave 3 with (a) structural enforcement that projects remain read-only for the new writable fields in v1.4.1 (no `add_projects*` or `edit_projects*` tools registered), (b) parametrized end-to-end round-trip coverage on both `HybridRepository` and `BridgeOnlyRepository` covering both the agent-value path and the preference-resolved create-default path, and (c) compare-and-skip-when-missing golden master scaffolding for the new task-property-surface read shape — baseline capture/refresh remains human-only per CLAUDE.md.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-19T17:55:00Z (approx.)
- **Tasks:** 3 (Task 1 structural; Tasks 2 and 3 TDD-style)
- **Files created:** 2
- **Files modified:** 2
- **Tests added:** 12 test methods / 19 executions (3 PROP-07 + 14 round-trip + 2 golden-master)

## Accomplishments

- **PROP-07 locked structurally.** Three tests in `tests/test_server.py::TestPROP07ProjectWritesNotYetAvailable` enumerate the registered MCP tools at runtime and assert no tool name starts with `add_projects` or `edit_projects`. The integration assertion locks the full v1.4.1 write surface (2 task tools, 0 project tools). A comment block above the class explicitly calls out v1.7 Phase 60 as the point at which these tests MUST be updated to parallel-cover PROP-01..06 on the new tools.
- **End-to-end round-trip coverage.** `tests/test_cross_path_equivalence.py::TestTaskPropertySurfaceRoundTrip` — 7 test methods parametrized across both repositories (`bridge` + `sqlite`) for 14 passing executions. Covers: PROP-01 agent-value (completes + type written explicitly), PROP-02 edit (patch flips both fields independently), PROP-05/06 create-default (preferences-resolved on both), PROP-03 factory-default fallback (absent preference keys), and `list_tasks` cache-backed read.
- **Golden master scaffolding.** `tests/golden_master/test_task_property_surface_golden.py` compares the normalized serialized `list_tasks` payload against a baseline file that the human captures manually. Opt-in `GOLDEN_MASTER_CAPTURE=1` env var triggers the capture branch; a sibling invariant test fails loudly if that env var is set during a regular run.
- **Parallel-wave-safe execution.** Both round-trip and golden-master tests feature-detect the post-56-06 `AddTaskCommand` surface and skip cleanly when it's absent, so 56-07 runs green regardless of which parallel Wave-3 plan lands first.
- **No RealBridge.** All new tests exercise `InMemoryBridge` + `BridgeOnlyRepository` or `HybridRepository` directly (SAFE-01 preserved).

## Task Commits

1. **Task 1: PROP-07 structural guardrail** — `3ddf9b01` (test)
   - `TestPROP07ProjectWritesNotYetAvailable` class (3 tests) in `tests/test_server.py`.
   - Uses the existing `client` fixture (FastMCP in-process) + `client.list_tools()` pattern.
   - Structural-checkpoint comment explicitly names Phase 60 / v1.7 as the update point.

2. **Task 2: Round-trip tests on both repositories** — `9c2bc0ec` (test)
   - Parametrized `cross_service` fixture yields full `OperatorService` stack for both repo types.
   - `_rehydrate_sqlite_from_bridge` helper stands in for OmniFocus's write-through so Hybrid reads see bridge writes.
   - `_post_56_06_write_surface_present` feature detector gates the suite on the 56-06 contract.
   - 7 test methods x 2 repos = 14 passing runs, zero `RealBridge`.

3. **Task 3: Golden master scaffolding** — `9b6b9060` (test)
   - New `tests/golden_master/test_task_property_surface_golden.py` with two tests (opt-in invariant + comparison).
   - New `tests/golden_master/snapshots/README.md` documenting the human-only capture / refresh / review / commit procedure.
   - Baseline file NOT captured by this plan — human runs the procedure manually.

_Plan metadata commit is owned by the orchestrator (STATE.md / ROADMAP.md)._

## Files Created/Modified

Created:
- `tests/golden_master/test_task_property_surface_golden.py` (170 lines, 2 tests)
- `tests/golden_master/snapshots/README.md` (70 lines, capture procedure)

Modified:
- `tests/test_server.py` (+64 lines, 1 class, 3 tests)
- `tests/test_cross_path_equivalence.py` (+450 lines, 1 class, 7 test methods / 14 runs, 1 parametrized fixture, 1 rehydration helper, 1 feature detector)

## Test Counts Added

- `tests/test_server.py`: **+3** tests (2343 -> 2346 — or the wave-3 aggregate including 56-06 — roughly +18 across the wave).
- `tests/test_cross_path_equivalence.py`: **+14** parametrized executions (7 methods x 2 repos).
- `tests/golden_master/test_task_property_surface_golden.py`: **+2** tests (1 always-run invariant + 1 baseline-gated comparison that skips until the human captures).

Full suite (including parallel-agent uncommitted working-tree changes from 56-06 follow-ups): **2405 passed, 1 skipped**.

## Decisions Made

- **Parallel-wave skip gate.** Both 56-06 and 56-07 run as `wave: 3` in parallel worktrees. Rather than hard-fail when 56-06's contract isn't yet present, the round-trip and golden-master tests feature-detect `AddTaskCommand.model_fields` and skip cleanly when the two new Patch fields are absent. This makes 56-07 safe to merge independently; once 56-06 lands, the skip condition clears and the suite becomes the end-to-end Wave-3 proof.
- **SQLite rehydration over bypass.** HybridRepository in production reads from SQLite that OmniFocus updates via write-through. In tests, that flow doesn't exist; the naive options are (a) mock the read path or (b) bypass SQLite. Both lose signal — the first hides SQL-layer regressions, the second changes the thing under test. Chose option (c): a small test-only helper (`_rehydrate_sqlite_from_bridge`) that re-derives the SQLite fixture from the `InMemoryBridge` snapshot between writes and reads. Keeps the read path under test, makes the test-only artifact explicit.
- **Dual-gate capture (env var + invariant test).** `GOLDEN_MASTER_CAPTURE=1` alone is too weak — an agent could unset the invariant test by accident. The invariant test alone is too weak — the capture branch would still be reachable in code. Dual gate: the env var must be set AND the invariant test must be unset-at-runtime (which fails loudly when the env var flips on). Explicit, noisy, and impossible to trigger by accident.
- **Normalization via recursive volatile-key substitution.** The existing `normalize.py` uses per-entity-type volatile sets (VOLATILE_TASK_FIELDS, VOLATILE_PROJECT_FIELDS, ...) because it was built for the bridge-contract snapshots that mix entity types. For this service-level shape contract, a single generic normalizer (substitute `"<normalized>"` wherever `id`/`url`/`added`/`modified` appears at any depth) is simpler and still deterministic. If future baselines introduce a field that requires per-entity handling, the normalizer extends; for now, generic is correct.

## Deviations from Plan

### Auto-fixed Issues

None. Task 1 and Task 3 matched the plan exactly. Task 2 used the feature-gate skip pattern rather than assuming 56-06 was already landed (the plan's action text implicitly assumed a sequential order; running as a parallel Wave-3 worktree required the skip gate). No scope creep — the gate is a strictly-additive robustness improvement, not a change in coverage.

### Parallel-Agent Side-Effects Observed (NOT auto-fixed — out of scope)

Other Wave-3 parallel agents had uncommitted modifications in the worktree (56-06 follow-up tasks: `src/omnifocus_operator/service/domain.py`, `src/omnifocus_operator/service/service.py`, `src/omnifocus_operator/service/payload.py`, `src/omnifocus_operator/bridge/bridge.js`, `tests/doubles/bridge.py`, etc.). Per project convention ("NEVER touch files you didn't change"), these were left untouched throughout and only the three files this plan OWNS were staged + committed. The parallel changes make the round-trip tests pass fully (e.g., the no-op detection in `DomainLogic._all_fields_match` now includes `completes_with_children` + `type`), but if a parallel agent reverts, the feature-gate skip will keep 56-07 green.

## Issues Encountered

- One transient: on the first standalone repro of the edit-flip round trip, `edit_task(completes_with_children=False)` appeared to short-circuit as a no-op. The cause was a stale `.pyc` cache from before a parallel agent's uncommitted `domain.py` change. After a fresh run, the round-trip worked end-to-end. Confirmed via inspection: `_all_fields_match` in the working tree includes both new fields in its `field_comparisons` dict.

## User Setup Required

None. The golden-master baseline IS a manual step — `tests/golden_master/snapshots/README.md` documents the procedure. Until a human runs it, the comparison test skips cleanly. The rest of the plan runs without any user action.

## UAT Readiness Assessment

Phase 56 is UAT-ready once the human performs the one-shot manual capture. UAT focus areas:

1. **FLAG-07 tool descriptions on a live MCP client** — verify that `list_tasks`, `get_task`, and `list_projects` tool docs surface the new behavioral flag meanings when the MCP client (Claude Desktop / Claude Code) renders them.
2. **Agent-value write paths** — issue `add_tasks` with and without `completesWithChildren` / `type`; read back via `get_task` and `list_tasks` and confirm values reflect as written.
3. **Create-default paths** — inspect the user's actual OmniFocus preferences for `OFMCompleteWhenLastItemComplete` and `OFMTaskDefaultSequential`; create a task omitting both fields; confirm the explicit write uses the preference values (NOT OmniFocus's implicit defaulting).
4. **No-suppression invariant visible on the wire** — `list_tasks(include=["hierarchy"])` should show BOTH the default-response derived flags (`isSequential`, `dependsOnChildren`) AND the hierarchy group (`type`, `hasChildren`, `completesWithChildren`) emitted independently, redundant-but-intentional.
5. **PROP-07 (cannot be UAT'd directly — no tool to call)** — manual tool discovery (e.g., `list_tools`) should not surface any `add_projects*` / `edit_projects*` entries.
6. **Golden master capture** — run the documented procedure, review the generated `task_property_surface_baseline.json`, commit.

## Safety / Invariant Confirmation

- **SAFE-01/02 preserved.** No `RealBridge` in any new test; golden master capture gated behind opt-in env var AND invariant test.
- **HIER-03 name preserved.** No `hasSubtasks` anywhere — new tests use `hasChildren`.
- **FLAG-08 regression-free.** The rejection tests for the 6 derived read-only flags remain green.
- **No plistlib in service layer.** This plan touches only test files and descriptions; service layer untouched.

## Threat Flags

No new security-relevant surface introduced. The threat register entries for this plan are all mitigated:

- **T-56-22 (Elevation of Privilege via accidental project-write tool exposure):** mitigated by `TestPROP07ProjectWritesNotYetAvailable` (enumerates registered tools, fails on any `add_projects*` / `edit_projects*` presence).
- **T-56-23 (Tampering via agent-written golden baseline masking regression):** mitigated by dual-gate capture — env-var opt-in + invariant test.
- **T-56-24 (Repudiation via per-repo test drift):** mitigated by the parametrized `cross_service` fixture forcing every round-trip test to run on both `HybridRepository` and `BridgeOnlyRepository`.
- **T-56-25 (DoS via per-call preference roundtrip):** already accepted in the plan (lazy-load-once in `OmniFocusPreferences`, verified by 56-01 tests). No new exposure.

## Self-Check: PASSED

- FOUND: `tests/test_server.py` (modified, committed in `3ddf9b01`)
- FOUND: `tests/test_cross_path_equivalence.py` (modified, committed in `9c2bc0ec`)
- FOUND: `tests/golden_master/test_task_property_surface_golden.py` (created, committed in `9b6b9060`)
- FOUND: `tests/golden_master/snapshots/README.md` (created, committed in `9b6b9060`)
- MISSING (EXPECTED): `tests/golden_master/snapshots/task_property_surface_baseline.json` — human captures it post-plan per the documented procedure. Correct default state.
- FOUND: commit `3ddf9b01` (Task 1 — PROP-07)
- FOUND: commit `9c2bc0ec` (Task 2 — round-trip)
- FOUND: commit `9b6b9060` (Task 3 — golden master scaffolding)
- VERIFIED: `grep "TestPROP07ProjectWritesNotYetAvailable\|test_no_add_projects_tool_registered\|test_no_edit_projects_tool_registered" tests/test_server.py` -- 3 matches (class + 2 test methods; third test lives under the integration-assertion name).
- VERIFIED: `grep "Phase 60\|v1.7" tests/test_server.py` -- 7 matches, all in the PROP-07 class comment + docstrings (structural-checkpoint signal).
- VERIFIED: `grep "TestTaskPropertySurfaceRoundTrip" tests/test_cross_path_equivalence.py` -- 1 class match.
- VERIFIED: `grep "test_round_trip_create_default_resolves_preference_values\|test_round_trip_factory_default_fallback" tests/test_cross_path_equivalence.py` -- 2 matches.
- VERIFIED: `uv run pytest tests/test_cross_path_equivalence.py::TestTaskPropertySurfaceRoundTrip --no-cov -q` -- 14 passed.
- VERIFIED: `grep "RealBridge" tests/test_cross_path_equivalence.py tests/test_server.py tests/golden_master/` -- no matches (SAFE-01).
- VERIFIED: `grep "pytest.skip\|GOLDEN_MASTER_CAPTURE" tests/golden_master/test_task_property_surface_golden.py` -- 6 matches (3 skip sites + 3 env-var references).
- VERIFIED: `grep "Agents MUST NOT\|human-only" tests/golden_master/snapshots/README.md` -- 3 matches.
- VERIFIED: `ls tests/golden_master/snapshots/task_property_surface_baseline.json` -- exits non-zero (baseline absent — expected default state).
- VERIFIED: `uv run pytest tests/golden_master/test_task_property_surface_golden.py --no-cov -q` -- 1 passed, 1 skipped (opt-in invariant passes; baseline-gated comparison skips cleanly).
- VERIFIED: `uv run pytest tests/ --no-cov -q` -- 2405 passed, 1 skipped. No regressions.

---
*Phase: 56-task-property-surface*
*Completed: 2026-04-19*
