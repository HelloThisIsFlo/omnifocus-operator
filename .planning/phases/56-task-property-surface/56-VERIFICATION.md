---
phase: 56-task-property-surface
verified: 2026-04-19T22:30:00Z
status: human_needed
score: 7/7 must-haves verified
overrides_applied: 0
gaps:
deferred:
human_verification:
  - test: "Open Claude Desktop or Claude Code and inspect the list_tasks tool description"
    expected: "The tool description mentions 'isSequential: only the next-in-line child is available' and 'dependsOnChildren: real task waiting on children' with behavioral meaning"
    why_human: "FLAG-07 verified verbatim in source, but agent-visible rendering requires live MCP client inspection; byte-budget compression means the tool doc was rewritten and only a real client confirms the behavioral message reaches the agent"
  - test: "Add a task omitting completesWithChildren and type, then read it back via get_task"
    expected: "completesWithChildren and type reflect the user's actual OmniFocus preference values (OFMCompleteWhenLastItemComplete / OFMTaskDefaultSequential), NOT OmniFocus's implicit defaults"
    why_human: "PROP-05/06 explicit-write semantics require an actual OmniFocus environment to confirm the bridge writes the preference-resolved value (not the OF implicit default); InMemoryBridge proves the pipeline logic but can't exercise the live bridge."
  - test: "Issue list_tasks with include=['hierarchy'] for a sequential task that has children and does NOT completesWithChildren"
    expected: "Response contains BOTH the default-response derived flags (isSequential: true, dependsOnChildren: true) AND the hierarchy group fields (type: 'sequential', hasChildren: true, completesWithChildren: false) independently — both pipelines emit, no de-duplication"
    why_human: "No-suppression invariant is tested at the unit and integration level, but a live round-trip via the MCP client is the contract-visible confirmation agents would experience"
  - test: "Add a task with type='singleActions' and verify the rejection error"
    expected: "Generic Pydantic enum error (not a custom message), no mention of 'project only' or custom educational text"
    why_human: "PROP-03 tested in contract tests but agent-side error rendering in Claude Desktop may differ; the client pre-validation layer can mask or alter error messages"
  - test: "Capture the golden master baseline for the task-property-surface read shape"
    expected: "tests/golden_master/snapshots/task_property_surface_baseline.json committed with the normalized serialized output of list_tasks(include=['hierarchy']) for a fully-loaded task"
    why_human: "Golden master capture is explicitly human-only per project CLAUDE.md (agents MUST NOT run GOLDEN_MASTER_CAPTURE=1). The snapshot scaffolding exists and skips cleanly; capture requires human to run the documented procedure in tests/golden_master/snapshots/README.md"
---

# Phase 56: Task Property Surface — Verification Report

**Phase Goal:** Agents can read and write the new task property surface (completesWithChildren, per-type type, presence flags, expanded hierarchy include group) end-to-end — reads served by SQLite cache on HybridRepository and amortized snapshot enumeration on BridgeOnlyRepository with no per-row bridge fallback; writes honor Patch[bool]/Patch[TaskType] semantics on tasks, and omitted create-values resolve to the user's explicit OmniFocus preference (never OF's implicit defaulting). Projects remain read-only for the new writable fields (project writes deferred to v1.7).

**Verified:** 2026-04-19T22:30:00Z
**Status:** human_needed (automated checks passed; 5 items require human/live-client verification)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Cross-path equivalence for completesWithChildren/type/hasAttachments on both repos, no per-row bridge fallback | ✓ VERIFIED | `SELECT task FROM Attachment` single batched query in `_build_attachment_presence_set`; `completedByChildren`/`sequential` removed from dead-fields; 18 parametrized cross-path tests pass |
| 2 | OmniFocusPreferences surfaces OFMCompleteWhenLastItemComplete + OFMTaskDefaultSequential via bridge-based lazy-load-once | ✓ VERIFIED | Both keys in `handleGetSettings` keys array; `get_complete_with_children_default()` + `get_task_type_default()` exist in preferences.py with `_ensure_loaded` sharing |
| 3 | Default task response emits hasNote/hasRepetition/hasAttachments/isSequential/dependsOnChildren (strip-when-false); projects emit has*; hierarchy group adds hasChildren+type+completesWithChildren | ✓ VERIFIED | `TASK_DEFAULT_FIELDS` has all 5; `PROJECT_DEFAULT_FIELDS` has 3 (not tasks-only); hierarchy frozensets confirmed; full test suite passes |
| 4 | No-suppression invariant (hierarchy + default emit independently); hasChildren name preserved; FLAG-07 tool descriptions surface behavioral meaning | ✓ VERIFIED | `TestNoSuppressionInvariant` 5 tests pass; `TestHierarchyIncludeNoSuppression` 3 integration tests pass; no `hasSubtasks` anywhere; FLAG-07 phrases verbatim in descriptions.py |
| 5 | add_tasks/edit_tasks accept Patch[bool]/Patch[TaskType] on tasks; null rejected; "singleActions" rejected via enum; create-default resolution writes preference value explicitly; project writes rejected at tool surface | ✓ VERIFIED | `completes_with_children: Patch[bool]` + `type: Patch[TaskType]` on both commands; null validators present; `TaskType` enum rejects "singleActions"; `_resolve_type_defaults` wired; PROP-07 structural guardrail (3 tests) confirms no project write tools registered |
| 6 | Derived read-only flags rejected by extra="forbid"; availability removed from NEVER_STRIP | ✓ VERIFIED | NEVER_STRIP = `frozenset({"completesWithChildren"})`; 12 parametrized FLAG-08 tests pass on both commands; no `availability` in projection.py |
| 7 | Round-trip tests on both repos (agent-value + create-default paths) | ✓ VERIFIED | `TestTaskPropertySurfaceRoundTrip` 7 methods × 2 repos = 14 passing parametrized runs; preference-key-absent fallback tested |

**Score: 7/7 truths verified**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/bridge/bridge.js` | handleGetSettings returns 2 new pref keys; handleGetAll emits completedByChildren/sequential/hasAttachments; handleAddTask/handleEditTask write both fields | ✓ VERIFIED | Lines 407-408 (pref keys); 163, 203 (flattenedTasks/Projects); 277, 317 (write path) |
| `src/omnifocus_operator/service/preferences.py` | get_complete_with_children_default() + get_task_type_default() with lazy-load-once | ✓ VERIFIED | Lines 198, 208 — both getters share `_ensure_loaded` |
| `src/omnifocus_operator/models/enums.py` | TaskType(parallel|sequential) + ProjectType(parallel|sequential|singleActions) | ✓ VERIFIED | Lines 130, 142 |
| `src/omnifocus_operator/models/common.py` | ActionableEntity gains has_note/has_repetition/has_attachments/completes_with_children | ✓ VERIFIED | Lines 123-126, Field(description=CONSTANT) pattern |
| `src/omnifocus_operator/models/task.py` | Task.type: TaskType, Task.is_sequential/depends_on_children defaulted bool | ✓ VERIFIED | type: TaskType present; lines 45-46 for derived flags |
| `src/omnifocus_operator/models/project.py` | Project.type: ProjectType; no is_sequential/depends_on_children | ✓ VERIFIED | ProjectType field exists; grep for derived flags returns nothing |
| `src/omnifocus_operator/repository/hybrid/hybrid.py` | _build_attachment_presence_set + extended mappers | ✓ VERIFIED | Line 642: batched query; HIER-05 precedence at line 474 |
| `src/omnifocus_operator/repository/bridge_only/adapter.py` | Dead-fields trimmed; property-surface helpers | ✓ VERIFIED | completedByChildren/sequential/containsSingletonActions not in dead-field tuples |
| `src/omnifocus_operator/server/projection.py` | NEVER_STRIP = {"completesWithChildren"} | ✓ VERIFIED | Line 23 |
| `src/omnifocus_operator/config.py` | TASK_DEFAULT_FIELDS +5; PROJECT_DEFAULT_FIELDS +3; hierarchy groups expanded | ✓ VERIFIED | Lines 93-98, 137-139, 119, 158 |
| `src/omnifocus_operator/service/domain.py` | enrich_task_presence_flags + assemble_project_type | ✓ VERIFIED | Lines 318, 337 |
| `src/omnifocus_operator/service/service.py` | _resolve_type_defaults; 3 enrichment callsites | ✓ VERIFIED | Line 555 (call); lines 152, 161, 461 (enrichment) |
| `src/omnifocus_operator/contracts/use_cases/add/tasks.py` | Patch[bool] + Patch[TaskType]; required RepoPayload fields | ✓ VERIFIED | Lines 95, 98 |
| `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` | Same Patch fields; optional RepoPayload fields | ✓ VERIFIED | Lines 71, 74 |
| `src/omnifocus_operator/agent_messages/descriptions.py` | 8 new constants; FLAG-07 behavioral phrases; tool doc updates | ✓ VERIFIED | IS_SEQUENTIAL_DESC line 133; DEPENDS_ON_CHILDREN_DESC line 142; phrases verbatim present |
| `tests/test_cross_path_equivalence.py` | TestPropertySurfaceCrossPath (18 runs) + TestTaskPropertySurfaceRoundTrip (14 runs) | ✓ VERIFIED | Both classes present and passing |
| `tests/test_server.py` | TestPROP07ProjectWritesNotYetAvailable (3 tests) + TestHierarchyIncludeNoSuppression (3 tests) | ✓ VERIFIED | Both classes found and passing |
| `tests/test_projection.py` | TestNoSuppressionInvariant + strip-when-false tests | ✓ VERIFIED | 63 total tests passing |
| `tests/test_contracts_field_constraints.py` | FLAG-08 parametrized rejection (12 cases + 1 no-custom-message) | ✓ VERIFIED | 2 Wave-3 boundary guards confirmed deleted |
| `tests/golden_master/test_task_property_surface_golden.py` | Compare-and-skip infrastructure; opt-in capture gate | ✓ VERIFIED | Skips cleanly (baseline absent = correct default); invariant test passes |
| `tests/golden_master/snapshots/README.md` | Human-only capture procedure documented | ✓ VERIFIED | "Agents MUST NOT" present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| OmniFocusPreferences._ensure_loaded | bridge.send_command('get_settings') | _apply reads OFMCompleteWhenLastItemComplete + OFMTaskDefaultSequential | ✓ WIRED | Both keys in bridge.js handleGetSettings keys array (lines 407-408); preferences.py _apply extended |
| HybridRepository._read_all | Attachment presence set | Single SELECT task FROM Attachment executed once | ✓ WIRED | Line 642 in hybrid.py; _build_attachment_presence_set helper |
| BridgeOnlyRepository adapter | raw bridge completedByChildren/sequential/attachments.length | Raw fields flow through via _adapt_task/project_property_surface helpers | ✓ WIRED | Dead-fields trimmed; helpers produce completesWithChildren/type/hasAttachments |
| service/service.py read pipelines | DomainLogic.enrich_task_presence_flags | Called after repo.get_task/get_all/list_tasks | ✓ WIRED | 3 callsites at lines 152, 161, 461 |
| _AddTaskPipeline.execute | OmniFocusPreferences.get_complete_with_children_default + get_task_type_default | _resolve_type_defaults step at line 555 | ✓ WIRED | Verified in service.py |
| AddTaskRepoPayload | bridge.js handleAddTask | task.completedByChildren + task.sequential written via hasOwnProperty gates | ✓ WIRED | Lines 277, 279 (handleAddTask); 317, 319 (handleEditTask) |
| TASK_FIELD_GROUPS['hierarchy'] | list_tasks include group resolution | resolve_fields → field_groups lookup | ✓ WIRED | frozenset({"parent", "hasChildren", "type", "completesWithChildren"}) at config.py line 119 |
| NEVER_STRIP | strip_entity | frozenset check bypasses strip filter | ✓ WIRED | projection.py line 59; completesWithChildren survives False stripping |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| HybridRepository._map_task_row | has_attachments | _build_attachment_presence_set (single SELECT) | Yes — set[str] of task IDs with attachments | ✓ FLOWING |
| HybridRepository._map_task_row | completes_with_children | row["completeWhenChildrenComplete"] INTEGER 0/1 | Yes — SQLite column | ✓ FLOWING |
| BridgeOnlyRepository adapter | completedByChildren | bridge.handleGetAll flattenedTasks.completedByChildren | Yes — OmniJS property | ✓ FLOWING |
| Service enrich_task_presence_flags | is_sequential, depends_on_children | task.type + task.has_children + task.completes_with_children | Yes — computed from real model fields | ✓ FLOWING |
| _AddTaskPipeline._resolve_type_defaults | _resolved_completes_with_children | OmniFocusPreferences.get_complete_with_children_default() | Yes — reads from bridge/cache | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `uv run pytest tests/ --no-cov -q` | 2405 passed, 1 skipped | ✓ PASS |
| Round-trip tests both repos | `uv run pytest tests/test_cross_path_equivalence.py::TestTaskPropertySurfaceRoundTrip --no-cov -q` | 14 passed | ✓ PASS |
| PROP-07 structural guardrail | `uv run pytest tests/test_server.py::TestPROP07ProjectWritesNotYetAvailable --no-cov -q` | 3 passed | ✓ PASS |
| No-suppression invariant | `uv run pytest tests/test_projection.py::TestNoSuppressionInvariant --no-cov -q` | 5 passed | ✓ PASS |
| Golden master skip-when-absent | `uv run pytest tests/golden_master/test_task_property_surface_golden.py --no-cov -q` | 1 passed, 1 skipped | ✓ PASS |
| mypy type check | `uv run mypy src/omnifocus_operator/` | Success: no issues in 79 source files | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| PREFS-01 | 56-01 | bridge.js handleGetSettings returns new pref keys | ✓ SATISFIED | bridge.js lines 407-408 |
| PREFS-02 | 56-01 | OmniFocusPreferences lazy-load-once for new keys | ✓ SATISFIED | preferences.py getters at lines 198, 208 |
| PREFS-03 | 56-01 | Absence-as-factory-default semantic | ✓ SATISFIED | _apply guard: `if key in raw and raw[key] is not None`; 9 tests in TestPreferencesNewTaskPropertyKeys |
| PREFS-04 | 56-01 | Single get_settings call per server lifetime | ✓ SATISFIED | `_ensure_loaded` shared across all getters; caching test exists |
| PREFS-05 | 56-01 | No plistlib in service layer | ✓ SATISFIED | grep returns no results |
| CACHE-01 | 56-02 | completesWithChildren read on both repos | ✓ SATISFIED | Hybrid: completeWhenChildrenComplete column; Bridge: completedByChildren |
| CACHE-02 | 56-02 | type parallel/sequential on both repos | ✓ SATISFIED | Hybrid: sequential column; Bridge: sequential property |
| CACHE-03 | 56-02 | type singleActions from ProjectInfo.containsSingletonActions | ✓ SATISFIED | hybrid.py line 474; adapter.py HIER-05 precedence |
| CACHE-04 | 56-02 | hasAttachments amortized O(1) per row | ✓ SATISFIED | Single SELECT task FROM Attachment; CACHE-04 batching test passes |
| FLAG-01 | 56-04 | hasNote in default response (tasks + projects) | ✓ SATISFIED | TASK_DEFAULT_FIELDS + PROJECT_DEFAULT_FIELDS include hasNote |
| FLAG-02 | 56-04 | hasRepetition in default response | ✓ SATISFIED | Same |
| FLAG-03 | 56-04 | hasAttachments in default response | ✓ SATISFIED | Same |
| FLAG-04 | 56-03/04 | isSequential tasks-only, strip-when-false | ✓ SATISFIED | TASK_DEFAULT_FIELDS has isSequential; PROJECT_DEFAULT_FIELDS does not |
| FLAG-05 | 56-03/04 | dependsOnChildren tasks-only, strip-when-false | ✓ SATISFIED | Same pattern |
| FLAG-06 | 56-04 | No-suppression invariant | ✓ SATISFIED | TestNoSuppressionInvariant (5 tests) + integration (3 tests) |
| FLAG-07 | 56-05 | Tool descriptions surface behavioral meaning | ✓ SATISFIED (needs live client) | Verbatim phrases in descriptions.py; human verification for rendered experience |
| FLAG-08 | 56-05 | Derived read-only flags rejected by extra='forbid' | ✓ SATISFIED | 12 parametrized tests on 6 flags × 2 commands |
| HIER-01 | 56-04 | hierarchy group on tasks includes type + completesWithChildren | ✓ SATISFIED | config.py line 119 |
| HIER-02 | 56-04 | hierarchy group on projects includes type + completesWithChildren | ✓ SATISFIED | config.py line 158 |
| HIER-03 | 56-02 | hasChildren name preserved | ✓ SATISFIED | No hasSubtasks anywhere in codebase |
| HIER-04 | 56-04 | No-suppression invariant (same as FLAG-06) | ✓ SATISFIED | Same evidence |
| HIER-05 | 56-02/03 | ProjectType singleActions takes precedence over sequential | ✓ SATISFIED | hybrid.py line 474; adapter.py; DomainLogic.assemble_project_type; cross-path test |
| PROP-01 | 56-06 | add_tasks accepts completesWithChildren: Patch[bool] | ✓ SATISFIED | contracts/add/tasks.py line 95 |
| PROP-02 | 56-06 | edit_tasks accepts same | ✓ SATISFIED | contracts/edit/tasks.py line 71 |
| PROP-03 | 56-06 | type: Patch[TaskType]; singleActions rejected via enum; no custom message | ✓ SATISFIED | TaskType enum; contract test asserts literal_error type + no custom phrase |
| PROP-04 | 56-06 | edit_tasks accepts type with same constraints | ✓ SATISFIED | contracts/edit/tasks.py line 74 |
| PROP-05 | 56-06 | Omitted completesWithChildren on add → write preference explicitly | ✓ SATISFIED | _resolve_type_defaults in service.py; 7 integration tests in TestAddTaskResolvesTypeDefaults |
| PROP-06 | 56-06 | Omitted type on add → write preference explicitly | ✓ SATISFIED | Same pipeline step |
| PROP-07 | 56-07 | Project writes rejected structurally (no tools exist) | ✓ SATISFIED | TestPROP07ProjectWritesNotYetAvailable (3 tests) confirm no add_projects*/edit_projects* tools |
| PROP-08 | 56-04 | completesWithChildren in NEVER_STRIP | ✓ SATISFIED | projection.py line 23 |
| STRIP-11 | 56-04 | availability removed from NEVER_STRIP | ✓ SATISFIED | projection.py has no mention of "availability" in NEVER_STRIP |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/omnifocus_operator/service/service.py` | 584, 597 | Preferences warnings drained twice in `_AddTaskPipeline.execute` — `_resolve_type_defaults` and `_normalize_dates` both call `await self._preferences.get_warnings()` and extend `_preferences_warnings`. On bridge failure, `AddTaskResult.warnings` contains duplicate `SETTINGS_FALLBACK_WARNING`. | ⚠️ Warning | Cosmetic: agents see duplicate warning strings on bridge failure during add_tasks. Tasks still create correctly. Documented in 56-REVIEW.md as WR-01. |
| `src/omnifocus_operator/repository/hybrid/hybrid.py` + `bridge_only/adapter.py` + `service/domain.py` | 474, 253, 337 | HIER-05 ProjectType truth table open-coded in 3 locations (two repos + DomainLogic.assemble_project_type). The domain method is not called by either repo (advisory lock only). Documented in 56-REVIEW.md as IN-01. | ℹ️ Info | Technical debt: coordinated drift in all three copies would not be caught by existing tests. Does not affect current correctness. |
| `src/omnifocus_operator/repository/bridge_only/adapter.py` | 228-263 | `_adapt_task_property_surface` and `_adapt_project_property_surface` share 4 of 5 lines (hasNote/hasRepetition/hasAttachments/completesWithChildren); only type-resolution differs. | ℹ️ Info | Duplication acknowledged in 56-REVIEW.md as IN-03. No bug. |

### Human Verification Required

#### 1. FLAG-07 Behavioral Meaning in Live MCP Client

**Test:** Connect to the MCP server via Claude Desktop or Claude Code CLI. Inspect the `list_tasks` and `get_task` tool descriptions visible to the agent.
**Expected:** Agent sees descriptions mentioning:
- `dependsOnChildren`: "real task waiting on children, not just a container" + "discrete unit of work"
- `isSequential`: "only the next-in-line child is available" + "agents must NOT over-count"
**Why human:** Tool doc byte-budget compression required rewriting the LIST_TASKS_TOOL_DOC (was 2522 bytes, reduced to 2034 for the 2048-byte Claude Code cap). The verbatim phrases are in source but the rendered experience in a live client is the true signal.

#### 2. PROP-05/06 Explicit Preference Resolution on Live Bridge

**Test:** With a live OmniFocus connection, check the user's actual `OFMCompleteWhenLastItemComplete` preference in OF settings. Then issue `add_tasks(name="pref-test")` omitting `completesWithChildren` and `type`. Read back the created task via `get_task`.
**Expected:** `completesWithChildren` and `type` reflect the user's actual OF preference values — not OmniFocus's silent defaults. If the user has `OFMCompleteWhenLastItemComplete = false` in OF prefs, the created task should show `completesWithChildren: false`.
**Why human:** PROP-05/06 prove the service writes the preference value explicitly (not relying on OF's implicit default). InMemoryBridge tests confirm the pipeline logic but only a live bridge interaction with a real OmniFocus instance verifies the end-to-end explicit write.

#### 3. No-Suppression Invariant on Live Wire

**Test:** Create a sequential task with children that does NOT completesWithChildren (e.g., edit an existing task). Issue `list_tasks(include=["hierarchy"])` for that task.
**Expected:** Response JSON contains ALL of: `isSequential: true`, `dependsOnChildren: true` (default-response flags), AND `type: "sequential"`, `hasChildren: true`, `completesWithChildren: false` (hierarchy group) — redundant but intentional.
**Why human:** Unit tests confirm the projection logic; the live MCP response is the contract artifact agents consume.

#### 4. PROP-03 singleActions Rejection Error Shape in Client

**Test:** Issue `add_tasks({"name": "test", "type": "singleActions"})` via Claude Desktop.
**Expected:** Pydantic validation error with generic `literal_error`/`enum` error type. No custom messaging like "project only", "use projects instead", etc.
**Why human:** Claude Desktop pre-validates against JSON Schema before sending to the server, which may show a different error than the Pydantic one. FLAG-08 and PROP-03 both tested in automated suites but the client-side rendering requires human observation.

#### 5. Golden Master Baseline Capture

**Test:** Run the human-only capture procedure from `tests/golden_master/snapshots/README.md`.
**Expected:** `tests/golden_master/snapshots/task_property_surface_baseline.json` created with normalized `list_tasks(include=["hierarchy"])` output for a fully-loaded task.
**Why human:** Golden master capture is explicitly human-only per project CLAUDE.md. The scaffolding exists, the opt-in gate (`GOLDEN_MASTER_CAPTURE=1`) is in place, and the invariant test verifies no auto-capture during regular runs. Human must run the documented procedure.

### Known Issue — Not Blocking Goal Achievement

**WR-01: Duplicate preferences warning in AddTaskResult** (from 56-REVIEW.md)

When the bridge fails during `add_tasks`, `SETTINGS_FALLBACK_WARNING` appears twice in `AddTaskResult.warnings`. Root cause: both `_normalize_dates` (line 597) and `_resolve_type_defaults` (line 584) call `await self._preferences.get_warnings()` and append to `_preferences_warnings`. Since `OmniFocusPreferences` caches warnings for server lifetime and `get_warnings()` returns the full accumulated list, the second drain re-appends the same items.

Fix: Remove the warning drain from `_resolve_type_defaults`. The test asserting exact duplicate count exists in the REVIEW as a recommended regression test.

This is a correctness bug (wrong output) but not a goal-blocker (tasks still create correctly, preferences are resolved correctly, no false behavior). Documented for the next plan cycle.

---

## Summary

Phase 56 achieves its goal. The full task property surface (read + write) is implemented end-to-end across both repositories with no per-row bridge fallback. All 7 observable success criteria are verified in the codebase with 2405 passing tests.

The 5 human verification items are not gaps — automated verification confirmed the underlying implementations are correct. The human items cover: (a) live agent-facing rendering of tool descriptions, (b) live bridge preference resolution on real OmniFocus, (c) live wire observation of the no-suppression invariant, (d) client-side error rendering, and (e) the human-only golden master capture procedure that is by design not automated.

One known bug (WR-01: duplicate warning strings on bridge failure in add_tasks) is documented in the code review and is not a goal blocker.

---

_Verified: 2026-04-19T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
