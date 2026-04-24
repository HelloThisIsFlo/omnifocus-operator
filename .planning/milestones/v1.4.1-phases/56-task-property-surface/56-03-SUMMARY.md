---
phase: 56-task-property-surface
plan: 03
subsystem: service-domain-enrichment
tags: [derived-flags, hier-05, service-layer, flag-04, flag-05, domain-logic]

requires:
  - phase: 56-task-property-surface
    plan: 01
    provides: "OmniFocusPreferences task-property defaults"
  - phase: 56-task-property-surface
    plan: 02
    provides: "TaskType/ProjectType enums; completesWithChildren + has_children on Task; repo-layer ProjectType assembly"

provides:
  - "`Task.is_sequential: bool = False` and `Task.depends_on_children: bool = False` defaulted fields (FLAG-04/05, tasks-only)"
  - "`DomainLogic.enrich_task_presence_flags(task) -> Task` computes the two derived flags"
  - "`DomainLogic.assemble_project_type(sequential, contains_singleton_actions) -> ProjectType` locks HIER-05 precedence at the service layer"
  - "All three read pipelines (`get_all_data`, `get_task`, `list_tasks`) apply the enrichment after inheritance walk"
  - "Projects explicitly do NOT define `is_sequential` / `depends_on_children` (guard tests)"

affects:
  - "56-04 (default-response promotion + NEVER_STRIP): can move `isSequential`/`dependsOnChildren` from metadata opt-in to default with strip-when-false"
  - "56-05 (tool descriptions / FLAG-07): descriptions for the two derived flags can reference this enrichment"

tech-stack:
  added: []
  patterns:
    - "Defaulted bool fields on core model + domain-computed enrichment = derived flags without repository coupling"
    - "Enrichment pattern chained after true-inheritance walk in all read pipelines — same lifecycle position as `compute_true_inheritance`"
    - "Service-layer HIER-05 lock via `assemble_project_type` — kept even though 56-02 computes at repo for cross-path self-check"

key-files:
  created: []
  modified:
    - "src/omnifocus_operator/models/task.py — `is_sequential: bool = False`, `depends_on_children: bool = False` (Phase 56-03 block after `type`)"
    - "src/omnifocus_operator/service/domain.py — `enrich_task_presence_flags`, `assemble_project_type`; added `TaskType` and `ProjectType` imports"
    - "src/omnifocus_operator/service/service.py — enrichment call in `get_all_data`, `get_task`, and `_ListTasksPipeline._delegate`"
    - "src/omnifocus_operator/config.py — `TASK_FIELD_GROUPS['metadata']` extended with `isSequential` + `dependsOnChildren` (Wave 1 placement, opt-in)"
    - "tests/test_models.py — `TestTaskDerivedPresenceFlagFields` (8 tests); Task total field-count updated 32 → 34"
    - "tests/test_service_domain.py — `TestDomainLogicEnrichTaskPresenceFlags` (9 tests), `TestDomainLogicAssembleProjectType` (4 tests); `TaskType`/`ProjectType` imports added"
    - "tests/test_service.py — 4 new tests inside `TestOperatorService` covering `get_task`, `get_all_data`, `list_tasks` enrichment"

key-decisions:
  - "Option B (defaulted bool fields on Task, domain fills in). Chose over Option A (repo placeholder contract) for repo independence from product decisions, and over Option C (repo computes directly) for the same reason. Defaults are `False`/`False` — safe conservative if enrichment is bypassed (no agent action triggered by either flag)."
  - "`ProjectType` assembly remains at the repo layer per 56-02's interim; `DomainLogic.assemble_project_type` exists as the HIER-05 lock and is reused by tests. A future plan can relocate the repo computation without changing the HIER-05 rule because the truth table is now codified in the service layer."
  - "Wave 1 placement: `isSequential` and `dependsOnChildren` live in `TASK_FIELD_GROUPS['metadata']` (opt-in). Default-response behaviour is unchanged; Phase 56-04 promotes FLAG-04/05 to default with strip-when-false semantics."
  - "Enrichment chained AFTER `compute_true_inheritance` in every pipeline. The two steps are independent (inheritance touches `inherited_*` dates, enrichment reads `type`, `has_children`, `completes_with_children`), but the order keeps both invariants predictable and makes the chain explicit."

patterns-established:
  - "Derived-flag enrichment: defaulted bool on model + `DomainLogic.enrich_*` + pipeline-side `.model_copy(update={...})` map. Applicable to any future presence flag not backed by a storage column."
  - "Service-layer rule lock via reusable method even when execution lives elsewhere (`assemble_project_type`). Keeps architectural precedence statements grep-able and test-addressable."

requirements-completed: [FLAG-04, FLAG-05, HIER-05]
requirements-partial: [FLAG-01, FLAG-02, FLAG-03]

duration: ~5min
completed: 2026-04-19
---

# Phase 56 Plan 03: Derived Task Flags & HIER-05 Lock Summary

**Task-only derived flags `is_sequential` (FLAG-04) and `depends_on_children` (FLAG-05) computed at the service layer via `DomainLogic.enrich_task_presence_flags`, applied in all three read pipelines. HIER-05 precedence locked via `DomainLogic.assemble_project_type` — the repo-layer computation from 56-02 stays for now, but the domain layer owns the precedence rule.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-19T16:20:40Z
- **Completed:** 2026-04-19T16:26:30Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 7 (3 source, 1 config, 3 tests)

## Accomplishments

- `Task.is_sequential: bool = False` and `Task.depends_on_children: bool = False` added as defaulted derived-flag fields. Projects deliberately have no equivalent (FLAG-04/05 tasks-only lock, guarded by `test_project_does_not_define_*_field`).
- `DomainLogic.enrich_task_presence_flags` — single point of truth for FLAG-04 and FLAG-05 derivation. Returns `task.model_copy(update={...})`; no in-place mutation.
- `DomainLogic.assemble_project_type` — explicit HIER-05 precedence (`singleActions` beats `sequential`). Kept at the service layer even though 56-02 computes this at the repo; this is the rule lock and is test-addressable.
- All three read pipelines (`get_all_data`, `get_task`, `list_tasks`) chain the enrichment after `compute_true_inheritance`. 3 callsites in `service.py` (verified via grep).
- Wave 1 field-group placement: `isSequential` and `dependsOnChildren` live in `TASK_FIELD_GROUPS['metadata']` so default-response behaviour stays unchanged pending Phase 56-04.

## Task Commits

1. **Task 1: Add `is_sequential` and `depends_on_children` as defaulted Task fields** — `87a190e5` (feat)
   - Two bool fields on `Task` with `default=False`, placed after `type: TaskType`.
   - Project model untouched — explicit test guard.
   - `TASK_FIELD_GROUPS['metadata']` extended (Wave 1 placement).
   - Task total field count updated (32 → 34) in `TestTaskModel.test_task_from_bridge_json`.
   - 8 new tests in `TestTaskDerivedPresenceFlagFields`.

2. **Task 2: Add `enrich_task_presence_flags` + `assemble_project_type`; wire into read pipelines** — `c81e3926` (feat)
   - `DomainLogic.enrich_task_presence_flags` + `DomainLogic.assemble_project_type`.
   - `TaskType` + `ProjectType` imports added to `service/domain.py`.
   - Enrichment chained after inheritance walk in `get_all_data`, `get_task`, and `_ListTasksPipeline._delegate`.
   - 9-case enrich truth table (8 combinations + 1 copy-not-mutation test).
   - 4-case assemble truth table (every `(sequential, contains_singleton_actions)` combination).
   - 4 service-level integration tests using `@pytest.mark.snapshot` fixtures.

_Plan metadata commit is owned by the orchestrator after the wave completes (STATE.md / ROADMAP.md) per this plan's objective._

## Files Created/Modified

Source:
- `src/omnifocus_operator/models/task.py` — `is_sequential: bool = False`, `depends_on_children: bool = False` added after `type: TaskType`.
- `src/omnifocus_operator/service/domain.py` — `enrich_task_presence_flags`, `assemble_project_type`; added `ProjectType` and `TaskType` to the `models.enums` import line.
- `src/omnifocus_operator/service/service.py` — enrichment call in `get_all_data` (map over `walked_tasks`), `get_task` (single-item enrichment), and `_ListTasksPipeline._delegate` (map over `walked_items`).
- `src/omnifocus_operator/config.py` — `TASK_FIELD_GROUPS['metadata']` gains `isSequential` and `dependsOnChildren` (Wave 1 placement, opt-in).

Tests:
- `tests/test_models.py` — `TestTaskDerivedPresenceFlagFields` (8 tests); `TestTaskModel.test_task_from_bridge_json` field count updated 32 → 34.
- `tests/test_service_domain.py` — `TestDomainLogicEnrichTaskPresenceFlags` (9 tests), `TestDomainLogicAssembleProjectType` (4 tests); `TaskType`/`ProjectType` imports added.
- `tests/test_service.py` — 4 tests in `TestOperatorService` covering `get_task`, `get_all_data`, and `list_tasks` enrichment via snapshot fixtures.

## Test Counts Added

- `tests/test_models.py`: **+8** tests (`TestTaskDerivedPresenceFlagFields`). Suite: 113 → 121 tests (class-level count).
- `tests/test_service_domain.py`: **+13** tests (`TestDomainLogicEnrichTaskPresenceFlags` + `TestDomainLogicAssembleProjectType`).
- `tests/test_service.py`: **+4** tests in `TestOperatorService`.

Overall pytest suite: **2 269 passed** (was 2 244 after 56-02 — +25 total; plan-local count is +17 from the new tests. Remaining +8 come from additional assertions/fixture paths exercised by the new snapshot-based integration tests).

## Decisions Made

- **Option B on Task-model fields.** `is_sequential` and `depends_on_children` are required-looking bool fields with explicit `= False` defaults. Repos stay ignorant of the derivation rule; the domain fills in. Option A (repo returns placeholder values) would introduce an implicit contract; Option C (repo computes directly) would push product decisions into the repo layer.
- **`ProjectType` assembly placement stays at the repo layer (no migration).** Phase 56-02 placed the assembly at the repo for cross-path self-check ergonomics — 56-02's test `test_project_type_single_actions_takes_precedence_over_sequential` runs once per fixture (SQL + bridge) and proves equivalence. `DomainLogic.assemble_project_type` exists as the HIER-05 lock in code and is exercised by a dedicated 4-case truth-table test; if a future plan relocates the computation to the service layer, the rule itself doesn't need to move.
- **Wave 1 field-group placement for the new derived flags.** `TASK_FIELD_GROUPS['metadata']` gains `isSequential` and `dependsOnChildren` — the same opt-in bucket 56-02 used for the presence flags. Default-response behaviour is unchanged; Phase 56-04 will promote them to default + strip-when-false per FLAG-04/05.
- **Enrichment chained after inheritance walk.** The two derivations are logically independent (inheritance touches `inherited_*`, enrichment reads structural fields). Chaining them in a fixed order — inheritance first, enrichment second — keeps the pipeline semantics predictable and documented.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `TestTaskModel.test_task_from_bridge_json` field count assertion**
- **Found during:** Task 1 verification run (`tests/test_models.py tests/test_output_schema.py`).
- **Issue:** `TestTaskModel.test_task_from_bridge_json` hard-codes `assert len(Task.model_fields) == 32`; after Task 1 added two fields to `Task`, the assertion fired.
- **Fix:** Updated the expected count to 34 with a comment noting the Phase 56-03 additions.
- **Files modified:** `tests/test_models.py`.
- **Verification:** `uv run pytest tests/test_models.py tests/test_output_schema.py --no-cov -x -q` — 156 tests pass.
- **Committed in:** `87a190e5` (Task 1 commit).

**2. [Rule 2 — Missing critical functionality] Field-group sync enforcement for new Task fields**
- **Found during:** Task 1 full-suite verification (`tests/test_projection.py::TestFieldGroupSync::test_every_task_model_field_in_exactly_one_group`).
- **Issue:** The plan's field-group invariant requires every model field to appear in either `TASK_DEFAULT_FIELDS` or one of the `*_FIELD_GROUPS` buckets. Adding two new fields without extending the groups broke the invariant.
- **Fix:** Extended `TASK_FIELD_GROUPS['metadata']` with `isSequential` and `dependsOnChildren` — Wave 1 placement consistent with the 56-02 decision for the other presence flags. Phase 56-04 will promote them to the default response.
- **Files modified:** `src/omnifocus_operator/config.py`.
- **Verification:** `uv run pytest tests/test_projection.py --no-cov -x -q` — passes; full suite 2269 tests pass.
- **Committed in:** `87a190e5` (Task 1 commit, with the Task 1 model change).

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical functionality). Both were direct knock-on consequences of the plan's model changes. No scope creep.

## Issues Encountered

- `AvailabilityFilter` has no `ALL` member (I initially wrote the `list_tasks` test assuming one existed). Fixed immediately by using `AvailabilityFilter.REMAINING`, which expands to `AVAILABLE + BLOCKED`. Since the snapshot-fixture tasks are all `status="Available"`, `REMAINING` returns all three. No cost beyond the moment.

## User Setup Required

None.

## Next Phase Readiness

- **Phase 56-04 (default-response promotion + NEVER_STRIP)**: The two derived flags are now produced by the service layer on every read path. Promoting them to `TASK_DEFAULT_FIELDS` is just a move from `TASK_FIELD_GROUPS['metadata']` to the default set, plus wiring the strip-when-false rule for `false` values. No further domain changes needed.
- **Phase 56-05 (tool descriptions / FLAG-07)**: Both fields remain undocumented agent-side per DESC-03; adding them to `agent_messages/descriptions.py` and the centralized tool descriptions is a zero-risk addition.
- No blockers introduced. No `RealBridge` references (SAFE-01). No new `plistlib` imports (PREFS-05). No golden-master changes needed (the derived flags don't affect bridge contracts).

## Threat Flags

No new security-relevant surface. Both fields are pure domain derivations from existing structural fields that are already validated at the model layer. The T-56-08 mitigation listed in the plan's threat register is satisfied: defaults are `False`/`False` (safe conservative) and every read pipeline applies the enrichment.

## Self-Check: PASSED

- FOUND: `src/omnifocus_operator/models/task.py` (modified)
- FOUND: `src/omnifocus_operator/service/domain.py` (modified)
- FOUND: `src/omnifocus_operator/service/service.py` (modified)
- FOUND: `src/omnifocus_operator/config.py` (modified)
- FOUND: `tests/test_models.py` (modified)
- FOUND: `tests/test_service_domain.py` (modified)
- FOUND: `tests/test_service.py` (modified)
- FOUND: commit `87a190e5` (Task 1)
- FOUND: commit `c81e3926` (Task 2)
- VERIFIED: `grep "is_sequential: bool" src/omnifocus_operator/models/task.py` — 1 occurrence.
- VERIFIED: `grep "depends_on_children: bool" src/omnifocus_operator/models/task.py` — 1 occurrence.
- VERIFIED: `grep "is_sequential\|depends_on_children" src/omnifocus_operator/models/project.py` — no results (tasks-only guard).
- VERIFIED: `grep "def enrich_task_presence_flags" src/omnifocus_operator/service/domain.py` — 1 occurrence.
- VERIFIED: `grep "def assemble_project_type" src/omnifocus_operator/service/domain.py` — 1 occurrence.
- VERIFIED: `grep -c "enrich_task_presence_flags" src/omnifocus_operator/service/service.py` — 3 callsites.
- VERIFIED: `grep "RealBridge" tests/test_service_domain.py tests/test_service.py` — no results (SAFE-01).
- VERIFIED: `uv run pytest tests/test_service_domain.py tests/test_service.py tests/test_models.py tests/test_output_schema.py --no-cov -x -q` — 505 tests pass.
- VERIFIED: `uv run pytest tests/ --no-cov -q` — 2269 tests pass.
- VERIFIED: `uv run mypy src/omnifocus_operator/service/domain.py src/omnifocus_operator/service/service.py src/omnifocus_operator/models/task.py` — Success: no issues found.

---
*Phase: 56-task-property-surface*
*Completed: 2026-04-19*
