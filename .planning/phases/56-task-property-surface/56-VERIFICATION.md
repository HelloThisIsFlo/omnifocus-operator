---
phase: 56-task-property-surface
verified: 2026-04-20T12:00:00Z
status: human_needed
score: 9/9 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 7/7
  gaps_closed:
    - "G1: FLAG-04 is_sequential now surfaces on both tasks AND projects (hoisted to ActionableEntity; enrich_project_presence_flags wired)"
    - "G2 (scaffolding): 56-07 wrong-pattern artifacts deleted; canonical 09-task-property-surface/ subfolder + capture script scenarios in place"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Open Claude Desktop or Claude Code and inspect the list_tasks tool description"
    expected: "The tool description mentions 'isSequential: only the next-in-line child is available' and 'dependsOnChildren: real task waiting on children' with behavioral meaning. Also confirm isSequential now appears in list_projects descriptions."
    why_human: "FLAG-07 verified verbatim in source, but agent-visible rendering requires live MCP client inspection; the tool doc was rewritten and only a real client confirms the behavioral message reaches the agent"
  - test: "Add a task omitting completesWithChildren and type, then read it back via get_task"
    expected: "completesWithChildren and type reflect the user's actual OmniFocus preference values (OFMCompleteWhenLastItemComplete / OFMTaskDefaultSequential), NOT OmniFocus's implicit defaults"
    why_human: "PROP-05/06 explicit-write semantics require an actual OmniFocus environment to confirm the bridge writes the preference-resolved value (not the OF implicit default); InMemoryBridge proves the pipeline logic but can't exercise the live bridge."
  - test: "Issue list_tasks with include=['hierarchy'] for a sequential task that has children and does NOT completesWithChildren"
    expected: "Response contains BOTH the default-response derived flags (isSequential: true, dependsOnChildren: true) AND the hierarchy group fields (type: 'sequential', hasChildren: true, completesWithChildren: false) independently"
    why_human: "No-suppression invariant is tested at the unit and integration level, but a live round-trip via the MCP client is the contract-visible confirmation agents would experience"
  - test: "Add a task with type='singleActions' and verify the rejection error"
    expected: "Generic Pydantic enum error (not a custom message), no mention of 'project only' or custom educational text"
    why_human: "PROP-03 tested in contract tests but agent-side error rendering in Claude Desktop may differ; the client pre-validation layer can mask or alter error messages"
  - test: "Capture the golden master baseline for the Phase 56 task-property-surface read shape"
    expected: "Run: uv run python uat/capture_golden_master.py — pre-seed the four required entities in OmniFocus (GM-Phase56-ParallelProj, GM-Phase56-SequentialProj, GM-Phase56-SingleActionsProj, GM-Phase56-Attached with a drag-dropped attachment). The harness writes 8 JSON fixtures into tests/golden_master/snapshots/09-task-property-surface/. Commit the fixtures. Re-run pytest tests/test_bridge_contract.py to confirm the new scenarios pass."
    why_human: "Golden master capture is explicitly human-only per SAFE-01/02. The scaffolding (8 scenarios in uat/capture_golden_master.py, _phase_2b_phase56_setup helper, 09-task-property-surface/ subfolder) is committed and the replay loop picks up fixtures automatically. Only the actual capture against live OmniFocus is pending."
---

# Phase 56: Task Property Surface — Re-Verification Report (Post Gap-Closure)

**Phase Goal:** Surface task properties (completesWithChildren, type, hasAttachments, hasNote, hasRepetition, isSequential, dependsOnChildren) across both repositories with cache-backed reads, correct projection, and agent-facing contracts. Open write paths for completesWithChildren and type on tasks only (not projects, per PROP-07 deferral to v1.7).

**Verified:** 2026-04-20T12:00:00Z
**Status:** human_needed (G1 and G2 scaffolding gaps closed; 5 items remain human-only by design)
**Re-verification:** Yes — after gap closure via plans 56-08 (FLAG-04 hoist) and 56-09 (golden master scaffolding)

---

## Gap Closure Summary

Two gaps were identified in the prior Human UAT (`56-HUMAN-UAT.md`) and confirmed by the previous VERIFICATION.md:

**G1 (FLAG-04 tasks-only scope error) — CLOSED by plan 56-08:**
- `is_sequential` hoisted from `Task` to `ActionableEntity` — one declaration, inherited by both `Task` and `Project`
- `DomainLogic.enrich_project_presence_flags` added (mirrors `enrich_task_presence_flags`)
- Three project read pipelines wired: `get_all_data`, `get_project`, `_ListProjectsPipeline._delegate`
- `PROJECT_DEFAULT_FIELDS` gains `"isSequential"` (strip-when-false, same projection as tasks)
- `IS_SEQUENTIAL_DESC` drops the "Tasks-only." prefix
- `LIST_PROJECTS_TOOL_DOC` + `GET_PROJECT_TOOL_DOC` surface `isSequential` with behavioral notes
- REQUIREMENTS.md FLAG-04 revised to cover both tasks and projects
- 4 negative assertions flipped positive; +20 tests (2405 → 2425 baseline)

**G2 (wrong golden-master pattern) — CLOSED (scaffolding half) by plan 56-09:**
- `tests/golden_master/test_task_property_surface_golden.py` deleted in full (56-07 self-referential InMemoryBridge → InMemoryBridge pattern)
- `GOLDEN_MASTER_CAPTURE` env-var gate died with the file; zero references remain in `src/`, `tests/`, `uat/`
- `tests/golden_master/snapshots/README.md` reduced to canonical pointer + 09-task-property-surface/ status note
- `tests/golden_master/snapshots/09-task-property-surface/` committed with README.md placeholder
- `uat/capture_golden_master.py` extended with 8 scenarios + `_phase_2b_phase56_setup()` helper
- Full suite green at 2424 passing (−2 from deletion of 56-07 wrong-pattern tests)
- Capture against live OmniFocus is pending human UAT (see human_verification item 5 above)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Cross-path equivalence for completesWithChildren/type/hasAttachments on both repos, no per-row bridge fallback | ✓ VERIFIED | Single `SELECT task FROM Attachment` batched query; `completedByChildren`/`sequential` in OmniJS enumeration; 18 parametrized cross-path tests pass |
| 2 | OmniFocusPreferences surfaces OFMCompleteWhenLastItemComplete + OFMTaskDefaultSequential via bridge-based lazy-load-once | ✓ VERIFIED | Both keys in `handleGetSettings`; `get_complete_with_children_default()` + `get_task_type_default()` in preferences.py sharing `_ensure_loaded` |
| 3 | Default task response emits hasNote/hasRepetition/hasAttachments/isSequential/dependsOnChildren (strip-when-false); projects emit hasNote/hasRepetition/hasAttachments/isSequential; hierarchy group adds hasChildren+type+completesWithChildren | ✓ VERIFIED | `TASK_DEFAULT_FIELDS` has all 5; `PROJECT_DEFAULT_FIELDS` has 4 (gained isSequential in 56-08); hierarchy frozensets confirmed; full test suite 2424 passing |
| 4 | No-suppression invariant (hierarchy + default emit independently); hasChildren name preserved; FLAG-07 tool descriptions surface behavioral meaning | ✓ VERIFIED | `TestNoSuppressionInvariant` 5 tests pass; `TestHierarchyIncludeNoSuppression` 3 integration tests pass; no `hasSubtasks` anywhere; FLAG-07 phrases verbatim in descriptions.py |
| 5 | add_tasks/edit_tasks accept Patch[bool]/Patch[TaskType] on tasks; null rejected; "singleActions" rejected via enum; create-default resolution writes preference value explicitly; project writes rejected at tool surface | ✓ VERIFIED | `completes_with_children: Patch[bool]` + `type: Patch[TaskType]` on both commands; null validators present; `TaskType` enum rejects "singleActions"; `_resolve_type_defaults` wired; 3-test PROP-07 structural guardrail confirms no project write tools |
| 6 | Derived read-only flags rejected by extra="forbid"; availability removed from NEVER_STRIP | ✓ VERIFIED | `NEVER_STRIP = frozenset({"completesWithChildren"})`; 12 parametrized FLAG-08 tests pass on both commands; no `availability` in projection.py |
| 7 | Round-trip tests on both repos (agent-value + create-default paths) | ✓ VERIFIED | `TestTaskPropertySurfaceRoundTrip` 7 methods × 2 repos = 14 passing parametrized runs |
| 8 | FLAG-04: `is_sequential` declared EXACTLY ONCE on `ActionableEntity`, not on `Task` or `Project`; `get_task`, `get_project`, `list_tasks`, `list_projects`, `get_all_data` all return entities with `is_sequential` correctly populated | ✓ VERIFIED | `grep is_sequential models/common.py` → line 135 (one declaration); `grep is_sequential models/task.py` → comment only, no Field() declaration; `grep enrich_project_presence_flags service.py` → 3 callsites (lines 154, 175, 546) + 1 definition in domain.py |
| 9 | GOLD-01: 56-07 wrong-pattern artifacts FULLY REMOVED; `09-task-property-surface/` subfolder committed; 8 capture scenarios in `uat/capture_golden_master.py`; `test_bridge_contract.py` discovers subfolder via sorted-iterdir; full suite green with empty subfolder | ✓ VERIFIED | `ls tests/golden_master/test_task_property_surface_golden.py` → no such file; `grep -rn GOLDEN_MASTER_CAPTURE tests/ src/ uat/` → 0 matches; `ls tests/golden_master/snapshots/09-task-property-surface/` → README.md; `grep -c 09-task-property-surface uat/capture_golden_master.py` → 21 matches; 2424 passing |

**Score: 9/9 truths verified**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/models/common.py` | `ActionableEntity.is_sequential` — single declaration, inherited by Task and Project | ✓ VERIFIED | Line 135: `is_sequential: bool = Field(default=False, description=IS_SEQUENTIAL_DESC)` |
| `src/omnifocus_operator/models/task.py` | `is_sequential` removed (now inherited from ActionableEntity); `depends_on_children` stays task-only | ✓ VERIFIED | Only comment reference at line 45; no `Field(...)` declaration |
| `src/omnifocus_operator/models/project.py` | `Project` inherits `is_sequential` via `ActionableEntity` — no explicit declaration | ✓ VERIFIED | `class Project(ActionableEntity)` — no `is_sequential` field body |
| `src/omnifocus_operator/service/domain.py` | `DomainLogic.enrich_project_presence_flags` defined | ✓ VERIFIED | Line 339 |
| `src/omnifocus_operator/service/service.py` | `get_all_data` + `get_project` + `_ListProjectsPipeline._delegate` wire `enrich_project_presence_flags` | ✓ VERIFIED | Lines 154, 175, 546 |
| `src/omnifocus_operator/config.py` | `PROJECT_DEFAULT_FIELDS` includes `"isSequential"` | ✓ VERIFIED | Line 145: `"isSequential"` in `PROJECT_DEFAULT_FIELDS` |
| `src/omnifocus_operator/agent_messages/descriptions.py` | `IS_SEQUENTIAL_DESC` drops tasks-only prefix; `LIST_PROJECTS_TOOL_DOC` + `GET_PROJECT_TOOL_DOC` surface `isSequential`; `_PROJECT_BEHAVIORAL_FLAGS_NOTE` introduced | ✓ VERIFIED | Line 158: `IS_SEQUENTIAL_DESC = f"True when type == 'sequential'. ..."` — no "Tasks-only." prefix; `isSequential` present on lines 82, 486, 588 |
| `.planning/REQUIREMENTS.md` | FLAG-04 wording covers both tasks and projects; `[x]` checkbox | ✓ VERIFIED | Line 28: `[x] **FLAG-04**: Default response on **tasks and projects**...` |
| `tests/golden_master/test_task_property_surface_golden.py` | DELETED | ✓ VERIFIED | File does not exist; zero `GOLDEN_MASTER_CAPTURE` references in executable source |
| `tests/golden_master/snapshots/09-task-property-surface/` | Directory present; README.md placeholder; zero JSON fixtures (capture pending) | ✓ VERIFIED | `ls` returns `README.md`; no `*.json` files |
| `uat/capture_golden_master.py` | 8 scenarios for `09-task-property-surface/`; `_phase_2b_phase56_setup()` helper | ✓ VERIFIED | 21 matches for `09-task-property-surface`; helper defined |
| `tests/golden_master/snapshots/README.md` | Wrong-pattern section removed; no `GOLDEN_MASTER_CAPTURE` or `task_property_surface_baseline` references | ✓ VERIFIED | Grep returns 0 matches for both patterns |
| `tests/test_bridge_contract.py` | Sorted-iterdir discovers 09-task-property-surface automatically; skips cleanly when empty | ✓ VERIFIED | No code change needed; existing `sorted(SNAPSHOTS_DIR.iterdir())` loop picks up the new subfolder |
| `tests/golden_master/normalize.py` | No new normalization entries needed (all Phase 56 raw fields are deterministic booleans on both bridges) | ✓ VERIFIED | Audit in 56-09-SUMMARY.md confirms no changes; plan 56-09 normalization audit documented per-field rationale |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `Project.is_sequential` | `ActionableEntity.is_sequential` | Inheritance — field declared once on shared base | ✓ WIRED | `Task.model_fields` and `Project.model_fields` both contain `is_sequential` via Pydantic inheritance |
| `OperatorService.get_project / list_projects / get_all_data` | `DomainLogic.enrich_project_presence_flags` | Service read pipelines call the new domain method analogous to `enrich_task_presence_flags` | ✓ WIRED | 3 callsites in service.py at lines 154, 175, 546 |
| `PROJECT_DEFAULT_FIELDS` | Response projection | Projection reads the frozenset and emits `isSequential` with strip-when-false behavior | ✓ WIRED | `"isSequential"` in `PROJECT_DEFAULT_FIELDS`; existing projection logic handles strip-when-false uniformly |
| `uat/capture_golden_master.py` scenarios | `tests/golden_master/snapshots/09-task-property-surface/` | Human runs capture script → fixtures written into subfolder → committed | SCAFFOLDED (capture pending human) | 8 scenarios declared; subfolder exists; no fixtures yet |
| `tests/test_bridge_contract.py::_load_scenarios` | Subfolder discovery loop | `sorted(SNAPSHOTS_DIR.iterdir())` picks up `09-task-property-surface/` automatically after human capture | ✓ WIRED | No code change needed; existing loop is sufficient |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `enrich_project_presence_flags` | `is_sequential` | `project.type == ProjectType.SEQUENTIAL` — computed from already-assembled `ProjectType` (HIER-05 precedence applied upstream) | Yes — derived from real model field | ✓ FLOWING |
| `_ListProjectsPipeline._delegate` | `enriched_items` | List comprehension of `enrich_project_presence_flags(p)` over `repo_result.items` | Yes — repo result flows through enrichment | ✓ FLOWING |
| `HybridRepository._map_task_row` | `has_attachments` | `_build_attachment_presence_set` (single `SELECT task FROM Attachment`) | Yes — set[str] of task IDs with attachments | ✓ FLOWING |
| `Service enrich_task_presence_flags` | `is_sequential`, `depends_on_children` | `task.type` + `task.has_children` + `task.completes_with_children` | Yes — computed from real model fields | ✓ FLOWING |
| `_AddTaskPipeline._resolve_type_defaults` | `_resolved_completes_with_children` | `OmniFocusPreferences.get_complete_with_children_default()` | Yes — reads from bridge/cache | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `uv run pytest tests/ --no-cov -q` | 2424 passed | ✓ PASS |
| Test coverage | `uv run pytest tests/ --cov=... -q` | 97.54% | ✓ PASS (≥97%) |
| Round-trip tests both repos | `uv run pytest tests/test_cross_path_equivalence.py::TestTaskPropertySurfaceRoundTrip --no-cov -q` | 14 passed | ✓ PASS |
| PROP-07 structural guardrail | `uv run pytest tests/test_server.py::TestPROP07ProjectWritesNotYetAvailable --no-cov -q` | 3 passed | ✓ PASS |
| No-suppression invariant | `uv run pytest tests/test_projection.py::TestNoSuppressionInvariant --no-cov -q` | 5 passed | ✓ PASS |
| Golden master skip-when-absent | `tests/test_bridge_contract.py` with empty 09-task-property-surface/ | 0 scenarios loaded from new subfolder; suite passes | ✓ PASS |
| Wrong-pattern artifacts deleted | `ls tests/golden_master/test_task_property_surface_golden.py` | No such file | ✓ PASS |
| No GOLDEN_MASTER_CAPTURE in source | `grep -rn GOLDEN_MASTER_CAPTURE tests/ src/ uat/` | 0 matches | ✓ PASS |
| is_sequential single declaration | `grep "is_sequential.*Field" models/common.py models/task.py models/project.py` | One match: common.py line 135 only | ✓ PASS |
| enrich_project_presence_flags wired | `grep enrich_project_presence_flags service.py` | 3 callsites (154, 175, 546) | ✓ PASS |
| isSequential in PROJECT_DEFAULT_FIELDS | `grep '"isSequential"' config.py` | Present in both TASK_DEFAULT_FIELDS and PROJECT_DEFAULT_FIELDS | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| PREFS-01 | 56-01 | bridge.js handleGetSettings returns 2 new pref keys | ✓ SATISFIED | bridge.js lines 407-408 |
| PREFS-02 | 56-01 | OmniFocusPreferences lazy-load-once for new keys | ✓ SATISFIED | preferences.py getters at lines 198, 208 |
| PREFS-03 | 56-01 | Absence-as-factory-default semantic | ✓ SATISFIED | `_apply` guard; 9 tests in `TestPreferencesNewTaskPropertyKeys` |
| PREFS-04 | 56-01 | Single get_settings call per server lifetime | ✓ SATISFIED | `_ensure_loaded` shared across all getters |
| PREFS-05 | 56-01 | No plistlib in service layer | ✓ SATISFIED | Grep returns no results |
| CACHE-01 | 56-02 | completesWithChildren read on both repos | ✓ SATISFIED | Hybrid: `completeWhenChildrenComplete` column; Bridge: `completedByChildren` |
| CACHE-02 | 56-02 | type parallel/sequential on both repos | ✓ SATISFIED | Hybrid: `sequential` column; Bridge: `sequential` property |
| CACHE-03 | 56-02 | type singleActions from ProjectInfo.containsSingletonActions | ✓ SATISFIED | hybrid.py line 474; adapter.py HIER-05 precedence |
| CACHE-04 | 56-02 | hasAttachments amortized O(1) per row | ✓ SATISFIED | Single `SELECT task FROM Attachment`; CACHE-04 batching test passes |
| FLAG-01 | 56-04 | hasNote in default response (tasks + projects) | ✓ SATISFIED | `TASK_DEFAULT_FIELDS` + `PROJECT_DEFAULT_FIELDS` include `hasNote` |
| FLAG-02 | 56-04 | hasRepetition in default response | ✓ SATISFIED | Same |
| FLAG-03 | 56-04 | hasAttachments in default response | ✓ SATISFIED | Same |
| FLAG-04 | 56-03/04 + 56-08 (G1 closure) | isSequential on **tasks and projects**, strip-when-false | ✓ SATISFIED | `TASK_DEFAULT_FIELDS` + `PROJECT_DEFAULT_FIELDS` both have `isSequential`; `is_sequential` on `ActionableEntity`; `enrich_project_presence_flags` wired; REQUIREMENTS.md `[x]` |
| FLAG-05 | 56-03/04 | dependsOnChildren tasks-only, strip-when-false | ✓ SATISFIED | Tasks only; `PROJECT_DEFAULT_FIELDS` does not include `dependsOnChildren` by design |
| FLAG-06 | 56-04 | No-suppression invariant | ✓ SATISFIED | `TestNoSuppressionInvariant` (5 tests) + integration (3 tests) |
| FLAG-07 | 56-05 | Tool descriptions surface behavioral meaning for dependsOnChildren + isSequential | ✓ SATISFIED (needs live client) | Verbatim phrases in descriptions.py; human verification for rendered experience |
| FLAG-08 | 56-05 | Derived read-only flags rejected by extra="forbid" | ✓ SATISFIED | 12 parametrized tests on 6 flags × 2 commands |
| HIER-01 | 56-04 | hierarchy group on tasks includes type + completesWithChildren | ✓ SATISFIED | config.py line 119 |
| HIER-02 | 56-04 | hierarchy group on projects includes type + completesWithChildren | ✓ SATISFIED | config.py line 158 |
| HIER-03 | 56-02 | hasChildren name preserved | ✓ SATISFIED | No `hasSubtasks` anywhere in codebase |
| HIER-04 | 56-04 | No-suppression invariant (same as FLAG-06) | ✓ SATISFIED | Same evidence as FLAG-06 |
| HIER-05 | 56-02/03 | ProjectType singleActions takes precedence over sequential | ✓ SATISFIED | hybrid.py line 474; adapter.py; `DomainLogic.assemble_project_type`; cross-path test |
| PROP-01 | 56-06 | add_tasks accepts completesWithChildren: Patch[bool] | ✓ SATISFIED | contracts/add/tasks.py line 95 |
| PROP-02 | 56-06 | edit_tasks accepts same | ✓ SATISFIED | contracts/edit/tasks.py line 71 |
| PROP-03 | 56-06 | type: Patch[TaskType]; singleActions rejected via enum; no custom message | ✓ SATISFIED | `TaskType` enum; contract test asserts literal_error type + no custom phrase |
| PROP-04 | 56-06 | edit_tasks accepts type with same constraints | ✓ SATISFIED | contracts/edit/tasks.py line 74 |
| PROP-05 | 56-06 | Omitted completesWithChildren on add → write preference explicitly | ✓ SATISFIED | `_resolve_type_defaults` in service.py; 7 integration tests in `TestAddTaskResolvesTypeDefaults` |
| PROP-06 | 56-06 | Omitted type on add → write preference explicitly | ✓ SATISFIED | Same pipeline step as PROP-05 |
| PROP-07 | 56-07 | Project writes rejected structurally (no tools exist) | ✓ SATISFIED | `TestPROP07ProjectWritesNotYetAvailable` (3 tests) confirm no `add_projects*` / `edit_projects*` tools |
| PROP-08 | 56-04 | completesWithChildren in NEVER_STRIP | ✓ SATISFIED | projection.py line 23 |
| STRIP-11 | 56-04 | availability removed from NEVER_STRIP | ✓ SATISFIED | projection.py has no mention of `availability` in `NEVER_STRIP` |
| GOLD-01 | 56-09 (G2 closure) | Canonical golden-master scaffolding for Phase 56 field surface | ✓ SATISFIED (scaffolding; capture pending) | 8 scenarios in uat/capture_golden_master.py; 09-task-property-surface/ subfolder committed; wrong-pattern 56-07 artifacts fully removed; capture against live OmniFocus is human-only per SAFE-01/02 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/omnifocus_operator/service/service.py` | 584, 597 | Preferences warnings drained twice in `_AddTaskPipeline.execute` — `_resolve_type_defaults` and `_normalize_dates` both call `await self._preferences.get_warnings()`. On bridge failure, `AddTaskResult.warnings` contains duplicate `SETTINGS_FALLBACK_WARNING`. | ⚠️ Warning | Cosmetic: agents see duplicate warning strings on bridge failure during add_tasks. Tasks still create correctly. Documented in 56-REVIEW.md as WR-01. |
| `src/omnifocus_operator/repository/hybrid/hybrid.py` + `bridge_only/adapter.py` + `service/domain.py` | 474, 253, 337 | HIER-05 ProjectType truth table open-coded in 3 locations (two repos + DomainLogic.assemble_project_type). The domain method is not called by either repo. Documented in 56-REVIEW.md as IN-01. | ℹ️ Info | Technical debt: coordinated drift would not be caught by existing tests. Does not affect current correctness. |
| `src/omnifocus_operator/repository/bridge_only/adapter.py` | 228-263 | `_adapt_task_property_surface` and `_adapt_project_property_surface` share 4 of 5 lines. | ℹ️ Info | Duplication acknowledged in 56-REVIEW.md as IN-03. No bug. |

### Human Verification Required

#### 1. FLAG-07 Behavioral Meaning in Live MCP Client

**Test:** Connect to the MCP server via Claude Desktop or Claude Code CLI. Inspect the `list_tasks`, `get_task`, and `list_projects` tool descriptions visible to the agent.
**Expected:** Agent sees `dependsOnChildren`: "real task waiting on children, not just a container"; `isSequential`: "only the next-in-line child is available"; AND `list_projects` now surfaces `isSequential` in its default fields with the project-scoped behavioral note.
**Why human:** Tool doc byte-budget compression required rewriting tool docs. Verbatim phrases are in source but the rendered experience in a live client is the true signal.

#### 2. PROP-05/06 Explicit Preference Resolution on Live Bridge

**Test:** With a live OmniFocus connection, issue `add_tasks(name="pref-test")` omitting `completesWithChildren` and `type`. Read back the created task via `get_task`.
**Expected:** `completesWithChildren` and `type` reflect the user's actual OF preference values — not OmniFocus's silent defaults.
**Why human:** PROP-05/06 prove the service writes the preference value explicitly (not relying on OF's implicit default). InMemoryBridge tests confirm the pipeline logic but only a live bridge interaction with a real OmniFocus instance verifies the end-to-end explicit write.

#### 3. No-Suppression Invariant on Live Wire

**Test:** Create a sequential task with children that does NOT completesWithChildren. Issue `list_tasks(include=["hierarchy"])` for that task.
**Expected:** Response JSON contains ALL of: `isSequential: true`, `dependsOnChildren: true` (default-response flags), AND `type: "sequential"`, `hasChildren: true`, `completesWithChildren: false` (hierarchy group).
**Why human:** Unit tests confirm the projection logic; the live MCP response is the contract artifact agents consume.

#### 4. PROP-03 singleActions Rejection Error Shape in Client

**Test:** Issue `add_tasks({"name": "test", "type": "singleActions"})` via Claude Desktop.
**Expected:** Pydantic validation error with generic `literal_error`/`enum` error type. No custom messaging.
**Why human:** Claude Desktop pre-validates against JSON Schema before sending to the server.

#### 5. Capture the Golden Master Baseline (G2 — Capture Half)

**Test:** Pre-seed four entities in OmniFocus (per `56-09-SUMMARY.md` Human UAT Follow-up). Then run `uv run python uat/capture_golden_master.py`. The harness creates `GM-Phase56-*` tasks in OmniFocus and writes 8 JSON fixtures to `tests/golden_master/snapshots/09-task-property-surface/`. Commit the fixtures. Re-run `pytest tests/test_bridge_contract.py -x -v`.
**Expected:** 8 new scenario files committed; bridge contract test passes with all new scenarios exercising the Phase 56 field surface against InMemoryBridge for parity with the real Bridge.
**Why human:** SAFE-01/02 — golden master capture is explicitly human-only. The scaffolding (scenarios, subfolder, replay loop wiring) is complete. The executor MUST NOT run the capture script.

### Known Issue — Not Blocking Goal Achievement

**WR-01: Duplicate preferences warning in AddTaskResult** (from 56-REVIEW.md)

When the bridge fails during `add_tasks`, `SETTINGS_FALLBACK_WARNING` appears twice in `AddTaskResult.warnings`. Root cause: both `_normalize_dates` and `_resolve_type_defaults` call `await self._preferences.get_warnings()` and append to `_preferences_warnings`. Fix: remove the warning drain from `_resolve_type_defaults`. Documented for next plan cycle.

---

## Summary

Phase 56 achieves its goal. The full task property surface (read + write) is implemented end-to-end across both repositories with no per-row bridge fallback. All 9 observable truths are verified in the codebase with 2424 passing tests at 97.54% coverage.

The two gaps identified in Human UAT are now closed:
- G1 (FLAG-04 tasks-only scope) — `is_sequential` hoisted to `ActionableEntity`; projects now surface the flag correctly on all read paths.
- G2 (wrong golden-master pattern) — 56-07's self-referential artifacts deleted; canonical 09-task-property-surface/ scaffolding committed and ready for human capture.

The 5 human verification items are not gaps — they cover: (a) live agent-facing rendering of tool descriptions, (b) live bridge preference resolution on real OmniFocus, (c) live wire observation of the no-suppression invariant, (d) client-side error rendering, and (e) the human-only golden master capture that is by design not automated (SAFE-01/02).

---

_Verified: 2026-04-20T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
