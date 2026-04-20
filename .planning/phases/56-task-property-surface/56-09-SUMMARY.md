---
phase: 56-task-property-surface
plan: 09
subsystem: testing

tags: [golden-master, bridge-contract, gap-closure, scaffolding, safe-01, safe-02]

# Dependency graph
requires:
  - phase: 56-task-property-surface
    provides: Phase 56 field surface (completesWithChildren, type, hasNote, hasRepetition, hasAttachments, isSequential, dependsOnChildren, expanded hierarchy include); is_sequential hoisted to ActionableEntity (56-08)
provides:
  - Canonical-pattern golden-master scaffolding for the Phase 56 read surface
  - 8 new scenarios in uat/capture_golden_master.py targeting 09-task-property-surface/
  - tests/golden_master/snapshots/09-task-property-surface/ subfolder present in version control, empty until human capture
  - Phase 2b manual-setup helper (3 projects + 1 attached task pre-seed, Inspector validation)
  - _preserved_task_ids mechanism (attached task survives Phase 5 cleanup across captures)
affects: [phase-57-parent-filter, v1.5-UI-perspectives]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pre-seeded manual-UAT entity with Inspector-only flags: three projects (parallel / sequential / singleActions) exercise HIER-05 project-type precedence; the capture harness validates the raw bridge flags (`sequential`, `containsSingletonActions`) before running scenarios — same shape as the existing `_validate_dated_project` check."
    - "Pre-seeded task with drag-dropped attachment + preserved-task-ID set: the script registers the pre-seeded task in known_task_ids BEFORE the leftover check, and excludes it from Phase 5 consolidation. Enables attachment coverage despite OmniJS being unable to create attachments."
    - "Raw-bridge-state comparison is sufficient for Phase 56: bridge_contract replay compares raw fields (completedByChildren, sequential, hasAttachments, containsSingletonActions), which are deterministic booleans on both bridges. Derived model-layer flags (hasNote, hasRepetition, completesWithChildren, type, isSequential, dependsOnChildren) are adapter-layer only and never appear in raw state_after — no normalization needed for them."

key-files:
  created:
    - "tests/golden_master/snapshots/09-task-property-surface/README.md (placeholder — subfolder present in VCS pre-capture)"
  modified:
    - "uat/capture_golden_master.py (+8 scenario blocks; new _phase_2b_phase56_setup() helper; _preserved_task_ids set; Phase 1/3 output updated to reflect 9 categories / ~92 scenarios; leftover check + Phase 5 consolidation guard against preserved tasks)"
    - "tests/golden_master/snapshots/README.md (reduced to pointer at parent tests/golden_master/README.md + 09-task-property-surface/ status note; removed task_property_surface_baseline.json section and all GOLDEN_MASTER_CAPTURE env-var references)"
  deleted:
    - "tests/golden_master/test_task_property_surface_golden.py (56-07 wrong-pattern self-referential InMemoryBridge→InMemoryBridge baseline; GOLDEN_MASTER_CAPTURE env-var gate died with the file)"

key-decisions:
  - "56-07 artifacts DELETED (not renamed/repurposed). The self-referential pattern proved only serialization-roundtrip stability, not parity with the real Bridge. Rename+reduce would have left dormant infrastructure that future maintainers could mistake for canonical-pattern scaffolding. Clean delete is the best signal."
  - "No normalize.py changes needed. Every Phase 56 raw bridge field (completedByChildren, sequential, hasAttachments, containsSingletonActions, hasChildren) is a deterministic boolean emitted identically by both bridges when params are explicit. Derived model-layer flags don't appear in raw state_after and are out of scope for replay."
  - "Placeholder is a README.md, not a .gitkeep. The README explains what the subfolder is for and when fixtures will land; future maintainers don't have to re-discover the story from git archaeology."
  - "Attachment scenario covered via pre-seeded task + manual drag-drop setup (not omitted). OmniJS cannot create attachments, so the scenario is `edit_task` with a no-op-ish note touch on a pre-seeded task; state_after captures the raw `hasAttachments=true` field."
  - "Repetition-rule scenario omitted as its own 09 entry. 08-repetition/ already has 38 scenarios that exercise `repetitionRule` on raw state_after extensively; adding a duplicate here would be redundant. The derived `hasRepetition` flag is an adapter-layer projection and doesn't appear in the raw comparison surface."
  - "Project-type matrix uses three pre-seeded projects validated against Inspector-only flags. The validation loop in `_phase_2b_phase56_setup` polls the real Bridge after each human fix attempt — same shape as the existing `_validate_dated_project` loop for GM-TestProject-Dated."
  - "Phase 3 preview numbers bumped to '~92 scenarios across 9 categories' (was ~84 / 8) so the human's confirmation prompt reflects the new scope."

patterns-established:
  - "Gap-closure via canonical-pattern re-scaffolding: when a prior plan builds the wrong shape, delete cleanly and add the correct scaffolding rather than retrofitting. Leaves less ambiguity for future maintainers."
  - "SAFE-01/02 discipline at scaffolding time: build the capture script, create the subfolder, ensure the replay loop discovers it, leave the actual capture as human UAT. No agent touches the real Bridge at any point."

requirements-completed: [GOLD-01]

# Metrics
duration: ~35 min
completed: 2026-04-20
---

# Phase 56 Plan 09: Golden-Master Scaffolding for Task Property Surface Summary

**56-07's wrong-pattern artifacts replaced with canonical scaffolding: 8 new scenarios in uat/capture_golden_master.py + 09-task-property-surface/ subfolder ready for human capture; no normalization changes needed.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2 (both auto — disposal + scaffolding)
- **Files modified:** 3 (1 deleted, 1 modified, 1 new file in new subfolder)
- **Net test delta:** -2 (2425 passed + 1 skipped → 2424 passed; both deleted tests lived in `test_task_property_surface_golden.py`)

## Accomplishments

- 56-07 wrong-pattern artifacts disposed of cleanly — no stale references, no env-var residue.
- `uat/capture_golden_master.py` carries 8 new scenarios for `09-task-property-surface/` following the exact dict schema the existing 01-add…08-repetition blocks use.
- New manual-setup helper (`_phase_2b_phase56_setup`) discovers and validates pre-seeded entities (project-type matrix + attached task), with Inspector-flag validation polling identical to the existing `_validate_dated_project` pattern.
- `_preserved_task_ids` set + Phase 5 consolidation guard keeps the pre-seeded attached task in place across captures (no re-attaching per run).
- `tests/golden_master/snapshots/09-task-property-surface/` committed with a README placeholder; `test_bridge_contract.py::_load_scenarios` discovers the subfolder via its existing `sorted(SNAPSHOTS_DIR.iterdir())` loop and skips cleanly when empty.
- Full suite stays green: 2424 passed, 0 skipped (consistent with -2 test delta from deletion).

## Task Commits

1. **Task 1: Dispose of 56-07 artifacts + normalize.py audit** — `37c1a6fb` (chore)
2. **Task 2: Add Phase 56 scenarios + 09-task-property-surface subfolder** — `558e573c` (test)

## Files Created/Modified

### Deleted

- `tests/golden_master/test_task_property_surface_golden.py` — 170 lines removed. Self-referential InMemoryBridge → InMemoryBridge baseline + `GOLDEN_MASTER_CAPTURE` env-var gate. No replacement: the canonical `uat/capture_golden_master.py` harness does not need a CI-level env var because it's human-invoked end-to-end.

### Modified

- `tests/golden_master/snapshots/README.md` — reduced from 70 lines to 40 lines. Removed the `task_property_surface_baseline.json` row from the "Available baselines" table, the "Capture procedure — task_property_surface_baseline.json" section, and every reference to `GOLDEN_MASTER_CAPTURE`. Retained the human-only preamble + subfolder layout block with a new `09-task-property-surface/` entry.
- `uat/capture_golden_master.py` — +432 lines, -6 lines. Changes:
  - Module-level placeholders: `GM_PHASE56_{PARALLEL,SEQUENTIAL,SINGLE_ACTIONS}_PROJECT_ID`, `GM_PHASE56_ATTACHED_TASK_ID`, `_preserved_task_ids: set[str]`.
  - New scenario block in `_build_scenarios()` (scenarios 01–08 listed below).
  - New async helper `_phase_2b_phase56_setup()` called from `main()` right after `_phase_2_manual_setup()` and before `_check_leftover_tasks()`. Discovers three pre-seeded projects + one pre-seeded attached task, validates Inspector-only flags (`sequential`, `containsSingletonActions`, `hasAttachments`), registers IDs + symbolic refs, and adds the attached task to `_preserved_task_ids`.
  - `_check_leftover_tasks()` excludes `known_task_ids` (was only `known_project_ids` — incomplete guard).
  - `_phase_5_consolidation()` iterates `known_task_ids - _preserved_task_ids` when moving tasks under the cleanup container.
  - `_phase_1_introduction()` + `_phase_3_confirmation()` output updated to reflect 9 categories / ~92 scenarios (was 8 / ~84).

### Created

- `tests/golden_master/snapshots/09-task-property-surface/README.md` — 11 lines. Placeholder explaining the subfolder's purpose and pointing at `uat/capture_golden_master.py`. Chosen over `.gitkeep` so future maintainers can discover intent without git archaeology.

## Scenarios Added (09-task-property-surface/)

All eight scenarios prefix task/project names with `GM-Phase56-` for easy cleanup.

| # | File | Shape | Raw-bridge fields exercised |
|---|------|-------|-----------------------------|
| 01 | `01_sequential_no_autocomplete_parent.json` | add sequential parent (completesWithChildren=false), followup add child | `completedByChildren=false`, `sequential=true`, `hasChildren=true` on parent |
| 02 | `02_parallel_autocomplete_parent.json` | add parallel parent (completesWithChildren=true), followup add child | `completedByChildren=true`, `sequential=false`, `hasChildren=true` on parent |
| 03 | `03_task_with_note.json` | add task with non-empty `note` | Raw `note` string (derived `hasNote=true` is model-layer) |
| 04 | `04_task_with_attachment.json` | edit_task touch (set note) on pre-seeded attached task | `hasAttachments=true` on the pre-seeded task |
| 05 | `05_project_type_parallel.json` | add child under pre-seeded parallel project | project `sequential=false`, `containsSingletonActions=false` |
| 06 | `06_project_type_sequential.json` | add child under pre-seeded sequential project | project `sequential=true`, `containsSingletonActions=false` |
| 07 | `07_project_type_single_actions.json` | add child under pre-seeded singleActions project | project `containsSingletonActions=true` |
| 08 | `08_edit_type_and_completes_flip.json` | add sequential/!autoComplete task, followup edit_task flip to parallel/autoComplete | Patch semantics for `type` + `completesWithChildren` on edit |

### Omitted

- **Dedicated repetition scenario.** 08-repetition/ already covers `repetitionRule` on raw state_after across 38 scenarios. Adding a single scoped "hasRepetition" entry in 09 would duplicate existing coverage since derived `hasRepetition` is adapter-layer and doesn't appear in the raw comparison.

## Normalization Audit (normalize.py)

**Verdict: no changes needed.** Reviewed the bridge-contract comparison surface against the Phase 56 field set:

| Field (raw bridge) | Entity | Both bridges emit? | Deterministic? | Normalization? |
|--------------------|--------|-------------------|----------------|----------------|
| `completedByChildren` | task | Yes (bridge.js L163, bridge.py L402/456) | Yes (bool) | No |
| `sequential` | task | Yes (bridge.js L164, bridge.py L403/458) | Yes (bool) | No |
| `hasAttachments` | task | Yes (bridge.js L165, conftest.py L65 default) | Yes (bool) | No |
| `hasChildren` | task | Yes (already covered pre-Phase-56) | Yes (bool) | No |
| `completedByChildren` | project | Yes (bridge.js L203) | Yes (bool) | No |
| `sequential` | project | Yes (bridge.js L204) | Yes (bool) | No |
| `containsSingletonActions` | project | Yes (bridge.js L205) | Yes (bool) | No |
| `hasAttachments` | project | Yes (bridge.js L206) | Yes (bool) | No |

Derived model-layer flags (`hasNote`, `hasRepetition`, `completesWithChildren`, `type`, `isSequential`, `dependsOnChildren`) are computed by the adapter in `repository/bridge_only/adapter.py` + `repository/hybrid/hybrid.py`; they never appear in the raw `get_all` state_after snapshot that `test_bridge_contract.py` compares. The `_restrict_to_expected_keys` backward-compat layer also means any unexpected extra fields from InMemoryBridge are filtered out before comparison.

If a human capture surfaces a discrepancy the audit missed, extending `VOLATILE_*` / `PRESENCE_CHECK_*` / `UNCOMPUTED_*` is the follow-up path — same way existing entries document field-by-field rationale.

## Decisions Made

See `key-decisions` in frontmatter. Highlights:

- Clean delete over rename+reduce for 56-07's wrong-pattern test file.
- No normalize.py changes (raw bridge fields are all deterministic booleans).
- README.md placeholder over `.gitkeep` (self-documenting).
- Attachment scenario included via manual pre-seed (not omitted).
- Repetition scenario omitted (redundant with 08-repetition/).

## Deviations from Plan

None — plan executed exactly as written. The plan's `<interfaces>` section was precise enough to not need re-exploration; both tasks lined up 1:1 with the plan's `<action>` blocks.

**Minor scope additions** (all driven by Rule 2 — necessary for correctness):

1. `_preserved_task_ids` set + Phase 5 consolidation guard. The plan called for a pre-seeded attached task but didn't specify what happens during Phase 5 consolidation, which moves every `known_task_id` into a cleanup container. Without the guard, the next capture would find the attached task in `🧪 GM-Cleanup (capture …)` instead of its original location, forcing the human to re-attach the file every run. The guard keeps the task where it belongs across captures.

2. `_check_leftover_tasks` now excludes `known_task_ids` in addition to `known_project_ids`. The original check was incorrect even before my changes (it compared task IDs against `known_project_ids`, which is a disjoint set — the check never matched anything task-shaped). Without this fix the pre-seeded `GM-Phase56-Attached` task would have been flagged as "leftover" on every capture run, requiring the human to manually confirm it's OK each time.

Both fixes are documented in commit 558e573c's message as infrastructure changes to the capture harness.

## Issues Encountered

**Post-Task-1 pytest count fluctuation.** Immediately after deleting `test_task_property_surface_golden.py` I saw `2425 passed, 1 skipped` — same as pre-delete baseline — which was surprising since two tests had been removed. Root cause was a stale `.pyc` cache for the deleted file that pytest was still loading via bytecode. After subsequent runs the cache invalidated and the count stabilized at 2424 passed (no skips), matching the expected -2 delta. No functional issue; documented here so the fluctuation isn't misread later.

## Verification Results

| Check | Result |
|-------|--------|
| `uv run pytest tests/ --no-cov -q` | 2424 passed, 0 skipped |
| `ls tests/golden_master/test_task_property_surface_golden.py` | `No such file or directory` |
| `grep "task_property_surface_baseline" tests/golden_master/snapshots/README.md` | 0 matches |
| `grep -rn "test_task_property_surface_golden\|task_property_surface_baseline\|GOLDEN_MASTER_CAPTURE" tests/ src/ uat/ docs/` | 0 matches (executable source clean; `.planning/` still has historical refs in prior plans/summaries, expected) |
| `python3 -c "import ast; ast.parse(open('uat/capture_golden_master.py').read())"` | exits 0 (syntax valid) |
| `grep -c "09-task-property-surface" uat/capture_golden_master.py` | 21 matches (8 scenario blocks × multiple lines each) |
| `ls tests/golden_master/snapshots/09-task-property-surface/` | `README.md` (no `*.json` — executor did NOT run capture) |
| `git log --oneline HEAD~2..HEAD` | `558e573c test(56-09): …`, `37c1a6fb chore(56-09): …` |

## Confirmations

- **SAFE-01 / SAFE-02 preserved:** executor did NOT run `uv run python uat/capture_golden_master.py`. No `.json` fixtures exist in `tests/golden_master/snapshots/09-task-property-surface/`. All test suite runs used InMemoryBridge via the existing fixtures.
- **No new `RealBridge` literals in comments/docstrings:** the only new occurrence of the literal is a type annotation on `async def _phase_2b_phase56_setup(bridge: RealBridge) -> None:` which matches the existing `_phase_2_manual_setup(bridge: RealBridge)` pattern in the same file. CLAUDE.md's guidance ("write `the real Bridge` in comments and docstrings") is respected in all new comments and docstrings.
- **Canonical-pattern alignment:** new scenarios use the exact same dict schema (`folder`, `file`, `scenario`, `description`, `operation`, `params`|`params_fn`, `capture_id_as`, `followup`) as every existing 01-add…08-repetition entry. Replay by `test_bridge_contract.py` requires zero code changes to pick up the new subfolder.
- **Write-side coverage of PROP-05 / PROP-06:** scenarios 01, 02, and 08 exercise the `completesWithChildren` + `type` write path against the real Bridge — the first fixtures to lock that contract after the Phase 56 write surface landed in plan 56-06.

## Test Count Delta

- Before plan 56-09: 2426 total (2425 passed + 1 skipped in `test_task_property_surface_golden.py`).
- After plan 56-09: 2424 total (2424 passed, 0 skipped). Net delta: **−2 tests** (both deleted from `test_task_property_surface_golden.py`). No tests added in this plan — scaffolding is exercised by the existing `test_bridge_contract.py` loop once fixtures land.

## Human UAT Follow-up (REQUIRED to fully close G2)

This plan produces scaffolding only. G2 is CLOSED for the scaffolding half; the capture half remains human-only work. Procedure (copied from plan 56-09's `<human_uat_followup>`):

1. Ensure the following entities exist in OmniFocus (the harness validates and prompts if any are missing or misconfigured):
   - 🧪 GM-TestProject, 🧪 GM-TestProject2, 🧪 GM-TestProject-Dated (pre-existing)
   - 🧪 GM-Tag1, 🧪 GM-Tag2 (pre-existing)
   - 🧪 GM-Phase56-ParallelProj (Inspector: type=parallel, containsSingletonActions=false) — **NEW**
   - 🧪 GM-Phase56-SequentialProj (Inspector: type=sequential, containsSingletonActions=false) — **NEW**
   - 🧪 GM-Phase56-SingleActionsProj (Inspector: containsSingletonActions=true) — **NEW**
   - 🧪 GM-Phase56-Attached (task anywhere — inbox or sandbox; drag-drop any small file as an attachment) — **NEW**
2. Run `uv run python uat/capture_golden_master.py`. The harness creates `GM-Phase56-*` tasks in OmniFocus, records responses + state snapshots, and writes JSON fixtures to `tests/golden_master/snapshots/09-task-property-surface/*.json`.
3. Review the generated fixtures — confirm no private data, consistent naming, expected scenario coverage (8 new files plus any fixture drift on re-captured 01-add…08-repetition scenarios).
4. Commit the fixtures:
   ```bash
   git add tests/golden_master/snapshots/09-task-property-surface/ tests/golden_master/snapshots/initial_state.json
   git commit -m "test(golden): capture 09-task-property-surface scenarios against the real Bridge"
   ```
5. Re-run `uv run pytest tests/test_bridge_contract.py -x -v` — the new scenarios now execute against InMemoryBridge and assert parity.
6. Clean up: delete `🧪 GM-Cleanup (capture …)` from the inbox. Pre-seeded projects + `GM-Phase56-Attached` stay in place for future re-captures.

If the capture surfaces a Phase 56 field discrepancy between InMemoryBridge and the real Bridge, the fix is either (a) a normalize.py entry (`PRESENCE_CHECK` / `UNCOMPUTED`) or (b) an InMemoryBridge adjustment to match real-Bridge behavior. Both are follow-up work, not part of this plan's scope.

**The executor MUST NOT perform step 2. SAFE-01 and SAFE-02 are absolute.**

## Next Phase Readiness

- **Phase 57 (Parent filter + filter unification)** unaffected — scaffolding is purely additive and isolated to `uat/` + `tests/golden_master/`.
- **v1.5 (UI & Perspectives)** unaffected.
- **G2 closure status:** scaffolding half CLOSED; capture half pending human UAT. The phase's Human UAT document should be updated to reflect "G2 scaffolding complete, capture pending next human UAT session" when the orchestrator merges.

## Self-Check: PASSED

Files verified to exist (or not exist, where deletion was the goal):

- `.planning/phases/56-task-property-surface/56-09-SUMMARY.md` — this document.
- `tests/golden_master/test_task_property_surface_golden.py` — MISSING (deletion target — correct).
- `tests/golden_master/snapshots/README.md` — present, no `task_property_surface_baseline` or `GOLDEN_MASTER_CAPTURE` references.
- `tests/golden_master/snapshots/09-task-property-surface/README.md` — present.
- `tests/golden_master/snapshots/09-task-property-surface/*.json` — none (executor did not capture).
- `uat/capture_golden_master.py` — parses cleanly; 21 matches for `09-task-property-surface`; `_phase_2b_phase56_setup` defined; `_preserved_task_ids` set present.

Commits verified present in `git log`:

- `37c1a6fb` — Task 1 disposal commit.
- `558e573c` — Task 2 scaffolding commit.

---

*Phase: 56-task-property-surface*
*Plan: 09*
*Completed: 2026-04-20*
