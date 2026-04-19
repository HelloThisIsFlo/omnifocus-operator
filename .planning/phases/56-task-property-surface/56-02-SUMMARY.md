---
phase: 56-task-property-surface
plan: 02
subsystem: repository-read-path
tags: [cache-read, bridge-enumeration, cross-path-equivalence, property-surface, hier-05]

requires:
  - phase: 56-task-property-surface
    plan: 01
    provides: "OmniFocusPreferences task-property defaults"

provides:
  - "`TaskType` (parallel|sequential) + `ProjectType` (parallel|sequential|singleActions) StrEnums in models/enums.py"
  - "`ActionableEntity.has_note`, `has_repetition`, `has_attachments`, `completes_with_children` required bool fields"
  - "`Task.type: TaskType` and `Project.type: ProjectType` required per-type enum fields"
  - "HybridRepository reads all 5 new fields from cache: Task.completeWhenChildrenComplete, Task.sequential, ProjectInfo.containsSingletonActions, Attachment.task (batched)"
  - "BridgeOnlyRepository emits + adapts the 5 new fields via the single existing flattenedTasks/flattenedProjects enumeration -- no extra round-trip"
  - "Cross-path equivalence: identical values on both repos for every new field, including HIER-05 precedence"
  - "`_build_attachment_presence_set` helper: single `SELECT task FROM Attachment` per snapshot for O(1) per-row has_attachments emission"

affects:
  - "56-03 (ProjectType service assembly) may relocate repo-level enum computation to service layer"
  - "56-04 (response shaping / default-response flags) consumes the model surface these fields provide"
  - "56-05 (write surface + create-defaults) consumes `TaskType`/`ProjectType` + preference getters from 56-01"

tech-stack:
  added: []
  patterns:
    - "Batched presence-set helper: one `SELECT <fk> FROM <table>` per snapshot -> Python `set[str]` for O(1) per-row lookup (CACHE-04 amortisation)"
    - "Scoped EXISTS probe for single-entity reads: `SELECT 1 FROM Attachment WHERE task = ? LIMIT 1` (O(log n) on indexed FK)"
    - "Per-entity property-surface helper on the adapter: transforms raw bridge keys into model-shape fields alongside other per-entity transforms"

key-files:
  created: []
  modified:
    - "src/omnifocus_operator/models/enums.py -- TaskType + ProjectType StrEnums"
    - "src/omnifocus_operator/models/common.py -- ActionableEntity gains has_note/has_repetition/has_attachments/completes_with_children"
    - "src/omnifocus_operator/models/task.py -- Task gains `type: TaskType`"
    - "src/omnifocus_operator/models/project.py -- Project gains `type: ProjectType`"
    - "src/omnifocus_operator/models/__init__.py -- export new enums + namespace rebuild"
    - "src/omnifocus_operator/repository/hybrid/hybrid.py -- _build_attachment_presence_set; _map_task_row / _map_project_row extended; _PROJECTS_SQL pulls pi.containsSingletonActions"
    - "src/omnifocus_operator/repository/hybrid/query_builder.py -- _PROJECTS_BASE pulls pi.containsSingletonActions"
    - "src/omnifocus_operator/repository/bridge_only/adapter.py -- dead-field tuples trimmed; _adapt_task_property_surface / _adapt_project_property_surface helpers"
    - "src/omnifocus_operator/bridge/bridge.js -- handleGetAll emits new raw fields on tasks + projects"
    - "src/omnifocus_operator/config.py -- TASK_FIELD_GROUPS / PROJECT_FIELD_GROUPS cover the 5 new fields (Wave 1 placement in opt-in groups)"
    - "src/omnifocus_operator/simulator/data.py -- 13 entity dicts extended with the 5 required new fields"
    - "tests/conftest.py -- factories gain defaults for raw bridge + model shapes"
    - "tests/test_models.py -- TestTaskType / TestProjectType / TestTaskPropertySurfaceFields / TestProjectPropertySurfaceFields"
    - "tests/test_hybrid_repository.py -- TestTaskPropertySurface (10 tests; HIER-05 + CACHE-04 batched-query count)"
    - "tests/test_adapter.py -- TestAdaptTaskPropertySurface / TestAdaptProjectPropertySurface + dead-field regression updates"
    - "tests/test_cross_path_equivalence.py -- TestPropertySurfaceCrossPath (9 tests x 2 params)"
    - "bridge/tests/bridge.test.js -- 2 Vitest cases asserting new raw-field emission"
    - "tests/test_server.py -- TOOL01 fixture extended with required new fields"

key-decisions:
  - "ProjectType enum assembly lives at the repo layer for Wave 1 to keep cross-path contract self-checkable; Phase 56-03 owns the final decision on whether to move it to the service layer"
  - "Single-entity reads use a scoped `EXISTS (SELECT 1 ... LIMIT 1)` probe on the indexed Attachment_task FK -- the one place per-row attachment lookup IS the right choice (no batch to amortise)"
  - "Wave 1 placement of the 5 new fields in opt-in field groups (metadata + hierarchy) -- default-response behaviour is unchanged pending Wave 2 FLAG-01..04 promotion"
  - "Inline docstrings converted to `#` comments on TaskType/ProjectType -- DESC-03 compliance without pre-empting Phase 56-05's FLAG-07 description constants"
  - "HybridRepository `_map_task_row` / `_map_project_row` take `attachment_presence: set[str]` as a positional-ish parameter; callers (batch + single-entity) pass either the full batched set or a scoped `{task_id}` set for uniform signatures"

patterns-established:
  - "Batched presence-set pattern (applicable to future 'presence of X for entity Y' checks)"
  - "Property-surface adapter helper convention on the bridge-only path: transform raw keys in-place alongside the existing `_adapt_repetition_rule` / `_adapt_parent_ref` calls"

requirements-completed: [CACHE-01, CACHE-02, CACHE-03, CACHE-04, HIER-03]

duration: ~24min
completed: 2026-04-19
---

# Phase 56 Plan 02: Cache-Backed Task Property Surface Summary

**Cache-backed read path for `completesWithChildren`, per-type `type` enum, `hasAttachments`/`hasNote`/`hasRepetition` on both HybridRepository (SQLite) and BridgeOnlyRepository (amortised OmniJS enumeration), with cross-path equivalence proven including HIER-05 precedence.**

## Performance

- **Duration:** ~24 min
- **Started:** 2026-04-19T15:51:59Z
- **Completed:** 2026-04-19T16:16:16Z
- **Tasks:** 4 (all TDD)
- **Files modified:** 18

## Accomplishments

- Introduced two per-type enums (`TaskType`, `ProjectType`) with exact HIER-05-compliant member sets and the full `ActionableEntity` property surface (`has_note`, `has_repetition`, `has_attachments`, `completes_with_children`).
- HybridRepository now reads all five fields cache-only: `Task.completeWhenChildrenComplete` and `Task.sequential` via the existing `SELECT t.*`, `ProjectInfo.containsSingletonActions` via an extended `_PROJECTS_SQL` projection, and attachment presence via a single batched `SELECT task FROM Attachment` per snapshot (CACHE-04 amortisation; zero per-row EXISTS on the batch path).
- Single-entity reads use a scoped `EXISTS (... LIMIT 1)` on the indexed `Attachment_task` FK — the one place per-row lookup IS correct.
- BridgeOnlyRepository adapter stops stripping `completedByChildren` / `sequential` / `containsSingletonActions`; two new helpers transform raw bridge keys into model-shape fields alongside the existing `_adapt_repetition_rule` / `_adapt_parent_ref` invocations. `bridge.js:handleGetAll` emits the new raw fields inline in the same `flattenedTasks` / `flattenedProjects` enumeration — no extra round-trip.
- Cross-path equivalence suite extended with one dedicated class (18 parametrized runs) that includes the HIER-05 cross-path precedence test (project with both `sequential=True` AND `containsSingletonActions=True` → `singleActions` on BOTH repos).
- Wave 2 surface-area placement fulfilled just enough to keep the projection-group sync enforcement passing: new presence flags in `metadata` opt-in group, `type`/`completesWithChildren` in `hierarchy` opt-in group. Default-response behaviour is unchanged until Wave 2 promotes them.

## Task Commits

1. **Task 1: Add TaskType/ProjectType enums and five read-only fields** — `3664a53f` (feat)
   - Enum additions in `models/enums.py` (no agent-facing descriptions — deferred to 56-05).
   - Four new required bool fields on `ActionableEntity`; `type` required on `Task` and `Project`.
   - Conftest factories (bridge-format + model-format) gain defaults for all new fields, preserving 2 178 prior-phase tests.
   - 15 new tests: enum member lists, field requirements, HIER-03 name preservation (`has_children` NOT renamed), TaskType rejection of `"singleActions"`.

2. **Task 2: HybridRepository cache-backed property surface** — `614174f0` (feat)
   - `_build_attachment_presence_set` helper; `_PROJECTS_SQL` + `_PROJECTS_BASE` updated.
   - `_map_task_row` / `_map_project_row` signatures take `attachment_presence: set[str]`; HIER-05 precedence applied in `_map_project_row`.
   - `_read_task` / `_read_project` use scoped `EXISTS (... LIMIT 1)`; `_list_tasks_sync` / `_list_projects_sync` use the batched helper.
   - 10 new `TestTaskPropertySurface` tests — including explicit HIER-05 precedence test and an `_build_attachment_presence_set` call-count assertion that proves the CACHE-04 contract (exactly 1 batched query per `get_all()`).
   - Test DB schema extended with new Task/ProjectInfo columns and the full `Attachment` table with indexed FK.

3. **Task 3: BridgeOnlyRepository amortised enumeration** — `435b6f27` (feat)
   - `bridge.js:handleGetAll` emits `completedByChildren` / `sequential` / `hasAttachments` per task plus `containsSingletonActions` per project.
   - `adapter.py` dead-field tuples trimmed; `_adapt_task_property_surface` and `_adapt_project_property_surface` (the latter with HIER-05 precedence assembly).
   - Field-group mapping in `config.py` extended so the enforcement tests stay green with the five new fields placed in opt-in groups (Wave 1 placement; Wave 2 will promote presence flags to defaults).
   - 15 new pytest cases + 2 new Vitest cases asserting the raw-field emission on both entity kinds.

4. **Task 4: Cross-path equivalence** — `253af88a` (feat)
   - Neutral test data extended: `task-1` is sequential w/ attachments + note, `task-2` is default-parallel, `proj-1` is the HIER-05 case (BOTH underlying flags set → `singleActions`), `proj-2` is pure sequential.
   - SQLite seed helper schema gains the three new columns and the `Attachment` table; bridge seed helper passes through new raw fields.
   - `_project_sequential_bit` helper + `_sequential_underlying` dict key support the HIER-05 test case where both underlying flags are set simultaneously.
   - 9 new `TestPropertySurfaceCrossPath` tests × 2 fixture params = 18 runs, plus cleanup of simulator + `test_server` fixtures for the new required model fields.

_Plan metadata commit will be created by the orchestrator after the wave completes (STATE.md / ROADMAP.md are owned by the orchestrator per this plan's objective)._

## Files Created/Modified

Source:
- `src/omnifocus_operator/models/enums.py` — TaskType + ProjectType StrEnums (inline comments, not docstrings — DESC-03 deferred to 56-05).
- `src/omnifocus_operator/models/common.py` — four new required fields on `ActionableEntity`.
- `src/omnifocus_operator/models/task.py` — `type: TaskType`.
- `src/omnifocus_operator/models/project.py` — `type: ProjectType`.
- `src/omnifocus_operator/models/__init__.py` — exports + rebuild namespace.
- `src/omnifocus_operator/repository/hybrid/hybrid.py` — `_build_attachment_presence_set`, mapper signatures, single-entity EXISTS probes, `_PROJECTS_SQL` extended.
- `src/omnifocus_operator/repository/hybrid/query_builder.py` — `_PROJECTS_BASE` extended.
- `src/omnifocus_operator/repository/bridge_only/adapter.py` — dead-field tuples trimmed, two new property-surface helpers.
- `src/omnifocus_operator/bridge/bridge.js` — new raw-field emission in `handleGetAll`.
- `src/omnifocus_operator/config.py` — field groups cover new fields (Wave 1 placement).
- `src/omnifocus_operator/simulator/data.py` — 13 entity dicts updated with new required fields.

Tests:
- `tests/conftest.py` — factories (bridge + model format) gain defaults.
- `tests/test_models.py` — 4 new test classes + count constants updated.
- `tests/test_hybrid_repository.py` — test DB schema updated; `TestTaskPropertySurface` class (10 tests).
- `tests/test_adapter.py` — `_old_task` / `_old_project` fixtures updated; dead-field tests updated; 2 new test classes (15 tests).
- `tests/test_cross_path_equivalence.py` — schema + seed helpers updated; `TestPropertySurfaceCrossPath` class (9 tests × 2 params = 18 runs).
- `bridge/tests/bridge.test.js` — mocks updated; 2 new Vitest cases.
- `tests/test_server.py` — TOOL01 fixture extended.

## Test Counts Added

- `tests/test_models.py`: **+22** tests (TaskType + ProjectType + Task/Project property-surface classes). Suite: 91 → 113 tests.
- `tests/test_hybrid_repository.py`: **+10** tests (`TestTaskPropertySurface`). Suite: 140 → 150 tests.
- `tests/test_adapter.py`: **+15** tests (parametrized × 2 classes). Suite: 81 → 96 tests.
- `tests/test_cross_path_equivalence.py`: **+18** parametrized runs. Suite: 86 → 104 tests.
- `bridge/tests/bridge.test.js`: **+2** Vitest cases (40 → 42 in this file; 73 → 75 overall).

Overall pytest suite: **2 244 passed** (was 2 177 after Plan 56-01 — +67 net).

## Decisions Made

- **Repo-layer ProjectType assembly (Wave 1).** The repository computes `type` directly from `(sequential, containsSingletonActions)` so the cross-path test is self-contained. 56-03 may relocate the assembly to the service layer; if so, the repo-level computation becomes pass-through and cross-path parity is preserved either way.
- **Scoped EXISTS vs batched set.** Single-entity reads use `SELECT 1 FROM Attachment WHERE task = ? LIMIT 1` (O(log n) via `Attachment_task` index). Batch reads build one `SELECT task FROM Attachment` set per snapshot. This split is justified by amortisation: batched EXISTS would cost N queries; batched set costs 1. Per-row EXISTS on single lookup costs 1 — same as the batched set built for one row.
- **Wave 1 field-group placement.** Presence flags live in `metadata` (opt-in) and `type`/`completesWithChildren` live in `hierarchy` (opt-in). Default-response behaviour is unchanged; Wave 2 will promote presence flags to the default response (FLAG-01..04) and add `completesWithChildren` to `NEVER_STRIP` so `false` survives stripping.
- **Inline comments, not docstrings, on the new enums.** DESC-03 requires `__doc__ = CONSTANT` on agent-facing classes; adding descriptions here would pre-empt 56-05's FLAG-07. Comments preserve developer intent without introducing inline docstrings.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical functionality] Field-group sync enforcement**
- **Found during:** Task 3 verification run (full pytest suite).
- **Issue:** `tests/test_projection.py:test_every_task_model_field_in_exactly_one_group` and `test_every_project_model_field_in_exactly_one_group` require every model field to appear in either `TASK_DEFAULT_FIELDS`/`PROJECT_DEFAULT_FIELDS` or one of the `*_FIELD_GROUPS`. Adding 5 new fields to the models without extending the groups breaks this invariant.
- **Fix:** Extended `TASK_FIELD_GROUPS` and `PROJECT_FIELD_GROUPS` in `config.py` to cover all 5 new fields. Wave 1 placement keeps default-response behaviour unchanged (all 5 in opt-in groups); Wave 2 will reorganise per FLAG-01..04 + HIER-01/02.
- **Files modified:** `src/omnifocus_operator/config.py`.
- **Verification:** `uv run pytest tests/test_projection.py --no-cov -x -q` — 34 tests pass.
- **Committed in:** `435b6f27` (part of Task 3 commit).

**2. [Rule 1 — Bug] Simulator snapshot missing required fields**
- **Found during:** Task 4 full-suite verification.
- **Issue:** `src/omnifocus_operator/simulator/data.py:SIMULATOR_SNAPSHOT` constructs 9 tasks + 4 projects as literal dicts; after Task 1 made the 5 new fields required, every simulator entity raised `ValidationError` during MCP round-trip tests.
- **Fix:** Patched all 13 entity dicts with the 5 new required fields using a script (idempotent injection before each `"tags":` line).
- **Files modified:** `src/omnifocus_operator/simulator/data.py`.
- **Verification:** `uv run pytest tests/test_simulator_integration.py --no-cov -x -q` — all passed.
- **Committed in:** `253af88a` (part of Task 4 commit).

**3. [Rule 1 — Bug] test_server TOOL01 fixture missing required fields**
- **Found during:** Task 4 full-suite verification.
- **Issue:** `tests/test_server.py:test_get_all_structured_content_is_camelcase` constructs task + project dicts inline without the 5 new required fields.
- **Fix:** Added the 5 fields to both literal dicts.
- **Files modified:** `tests/test_server.py`.
- **Verification:** `uv run pytest tests/test_server.py --no-cov -q` — all passed.
- **Committed in:** `253af88a` (part of Task 4 commit).

**4. [Rule 2 — Missing critical functionality] DESC-03 convention compliance**
- **Found during:** Task 4 full-suite verification (`tests/test_descriptions.py`).
- **Issue:** The new `TaskType` / `ProjectType` enums had inline docstrings, which DESC-03 forbids on agent-facing classes (they must use `__doc__ = CONSTANT`). Adding centralised description constants now would pre-empt Phase 56-05 (FLAG-07).
- **Fix:** Converted both inline docstrings to `#` comments. Developer intent preserved; agent-facing documentation deferred to Phase 56-05 per plan.
- **Files modified:** `src/omnifocus_operator/models/enums.py`.
- **Verification:** `uv run pytest tests/test_descriptions.py --no-cov -x -q` — 9 tests pass.
- **Committed in:** `253af88a` (part of Task 4 commit).

---

**Total deviations:** 4 auto-fixed (2 bugs, 2 missing critical functionality).
**Impact on plan:** None of these altered contracts; all were knock-on consequences of newly-required model fields. No scope creep.

## Issues Encountered

None with core design. Two test-infrastructure surprises:
- `sqlite3.Connection.execute` is immutable on Python 3.12 (`TypeError: cannot set 'execute' attribute of immutable type`). Worked around by patching the module-level `_build_attachment_presence_set` helper with a call-count spy instead of mocking `Connection.execute` — arguably a *better* signal anyway (counts the right level of abstraction).
- Eight test files depend on `make_task_dict` / `make_project_dict` or `make_model_task_dict` / `make_model_project_dict`. Adding new required fields to the models forced additions to these factories; defaults chosen (`completes_with_children=True`, `type="parallel"`, all presence flags `False`) are the "neutral" values and kept all prior-phase tests green.

## User Setup Required

None. Pure code change. No environment, credentials, or database migration involved.

## Next Phase Readiness

- **Phase 56-03 (ProjectType service assembly)** can consume the repo-layer assembly pattern already in place; the choice to keep it at the repo or move it to the service boundary is an architectural preference, not a contract change — cross-path tests will continue to pass either way.
- **Phase 56-04 (read surface: default flags + NEVER_STRIP)** can consume the model surface this plan provides. FLAG-01..04 promotion just means moving the three presence flags from `metadata` into `TASK_DEFAULT_FIELDS` / `PROJECT_DEFAULT_FIELDS`; `completesWithChildren` adds to `NEVER_STRIP` so `false` survives.
- **Phase 56-05 (write surface + create-defaults)** gets the `TaskType` / `ProjectType` enums plus preference getters already delivered in 56-01.
- No blockers introduced; no `RealBridge` used anywhere in tests (SAFE-01 satisfied); no new `plistlib` usage (PREFS-05 remains satisfied at the service layer); HIER-03 `has_children` name preserved.

## Threat Flags

No new security-relevant surface. The new batched `SELECT task FROM Attachment` query is pure-read on the existing trust boundary (OmniFocus SQLite → Python repository) with no user input (no parameters, no interpolation). The T-56-04 mitigation listed in the plan's threat register is confirmed: parameterised internal SQL, no injection surface.

## Self-Check: PASSED

- FOUND: `src/omnifocus_operator/models/enums.py` (modified)
- FOUND: `src/omnifocus_operator/models/common.py` (modified)
- FOUND: `src/omnifocus_operator/models/task.py` (modified)
- FOUND: `src/omnifocus_operator/models/project.py` (modified)
- FOUND: `src/omnifocus_operator/models/__init__.py` (modified)
- FOUND: `src/omnifocus_operator/repository/hybrid/hybrid.py` (modified)
- FOUND: `src/omnifocus_operator/repository/hybrid/query_builder.py` (modified)
- FOUND: `src/omnifocus_operator/repository/bridge_only/adapter.py` (modified)
- FOUND: `src/omnifocus_operator/bridge/bridge.js` (modified)
- FOUND: `src/omnifocus_operator/config.py` (modified)
- FOUND: `src/omnifocus_operator/simulator/data.py` (modified)
- FOUND: `tests/conftest.py` (modified)
- FOUND: `tests/test_models.py` (modified)
- FOUND: `tests/test_hybrid_repository.py` (modified)
- FOUND: `tests/test_adapter.py` (modified)
- FOUND: `tests/test_cross_path_equivalence.py` (modified)
- FOUND: `tests/test_server.py` (modified)
- FOUND: `bridge/tests/bridge.test.js` (modified)
- FOUND: commit `3664a53f` (Task 1)
- FOUND: commit `614174f0` (Task 2)
- FOUND: commit `435b6f27` (Task 3)
- FOUND: commit `253af88a` (Task 4)
- VERIFIED: `grep "class TaskType" src/omnifocus_operator/models/enums.py` -- 1 match.
- VERIFIED: `grep "class ProjectType" src/omnifocus_operator/models/enums.py` -- 1 match.
- VERIFIED: `grep "has_note: bool\|has_repetition: bool\|has_attachments: bool\|completes_with_children: bool" src/omnifocus_operator/models/common.py` -- 4 matches inside `ActionableEntity`.
- VERIFIED: `grep "type: TaskType" src/omnifocus_operator/models/task.py` -- 1 match.
- VERIFIED: `grep "type: ProjectType" src/omnifocus_operator/models/project.py` -- 1 match.
- VERIFIED: `grep "has_subtasks\|hasSubtasks" src/omnifocus_operator/models/` -- no results (HIER-03).
- VERIFIED: `grep "SELECT task FROM Attachment" src/omnifocus_operator/repository/hybrid/hybrid.py` -- 1 occurrence inside `_build_attachment_presence_set`.
- VERIFIED: `grep "completeWhenChildrenComplete" src/omnifocus_operator/repository/hybrid/hybrid.py` -- 2 matches (`_map_task_row` and `_map_project_row`).
- VERIFIED: `grep "containsSingletonActions" src/omnifocus_operator/repository/hybrid/hybrid.py` -- 3 matches inside `_map_project_row` and `_PROJECTS_SQL`.
- VERIFIED: `grep "completedByChildren" src/omnifocus_operator/bridge/bridge.js` -- 2 matches (tasks + projects).
- VERIFIED: `grep "attachments.length > 0" src/omnifocus_operator/bridge/bridge.js` -- 2 matches (tasks + projects).
- VERIFIED: `grep "containsSingletonActions" src/omnifocus_operator/bridge/bridge.js` -- 1 match in `flattenedProjects.map`.
- VERIFIED: `grep "RealBridge" tests/test_cross_path_equivalence.py tests/test_hybrid_repository.py tests/test_adapter.py tests/test_models.py` -- no results (SAFE-01).
- VERIFIED: `uv run pytest tests/test_models.py tests/test_hybrid_repository.py tests/test_bridge_only_repository.py tests/test_adapter.py tests/test_cross_path_equivalence.py tests/test_output_schema.py tests/test_bridge_contract.py --no-cov -q` -- 611 tests pass.
- VERIFIED: `uv run pytest tests/ --no-cov -q` -- 2 244 tests pass.
- VERIFIED: `uv run mypy src/omnifocus_operator/` -- Success: no issues found in 79 source files.
- VERIFIED: `cd bridge && npm test` -- 75 Vitest tests pass.
- VERIFIED: HIER-05 precedence: `uv run pytest tests/test_hybrid_repository.py::TestTaskPropertySurface::test_map_project_row_singleactions_takes_precedence_over_sequential tests/test_adapter.py::TestAdaptProjectPropertySurface::test_project_type_single_actions_takes_precedence_over_sequential tests/test_cross_path_equivalence.py::TestPropertySurfaceCrossPath::test_project_type_single_actions_takes_precedence_over_sequential --no-cov -q` -- all pass.
- VERIFIED: CACHE-04 amortisation: `uv run pytest tests/test_hybrid_repository.py::TestTaskPropertySurface::test_attachment_presence_single_batched_query --no-cov -q` -- passes (exactly 1 batched call per `get_all()` regardless of task count).

---
*Phase: 56-task-property-surface*
*Completed: 2026-04-19*
