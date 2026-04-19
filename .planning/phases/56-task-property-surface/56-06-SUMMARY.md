---
phase: 56-task-property-surface
plan: 06
subsystem: write-path
tags: [add-task, edit-task, write-surface, patch-semantics, prop-01, prop-02, prop-05, prop-06, bridge-contract]

requires:
  - phase: 56-task-property-surface
    plan: 01
    provides: "OmniFocusPreferences.get_complete_with_children_default() + get_task_type_default()"
  - phase: 56-task-property-surface
    plan: 02
    provides: "TaskType + ProjectType StrEnums; Task.type / Task.completes_with_children on the read side"
  - phase: 56-task-property-surface
    plan: 05
    provides: "FLAG-08 extra='forbid' proof + 2 Wave-3 boundary guards marked `# REMOVE IN 56-06`"

provides:
  - "Agent-writable completesWithChildren: Patch[bool] + type: Patch[TaskType] on AddTaskCommand and EditTaskCommand"
  - "Null rejection on both new fields (ADD_COMPLETES_WITH_CHILDREN_NULL / ADD_TASK_TYPE_NULL / EDIT_TYPE_FIELD_NULL)"
  - "`\"singleActions\"` rejection NATURAL via the TaskType enum — no custom messaging (PROP-03 lock)"
  - "AddTaskRepoPayload carries `completes_with_children: bool` + `type: str` as REQUIRED — service MUST resolve"
  - "EditTaskRepoPayload carries both as optional (None = no change)"
  - "`_AddTaskPipeline._resolve_type_defaults` — reads OmniFocus preferences when agent omits, writes explicit value"
  - "bridge.js:handleAddTask + handleEditTask write `task.completedByChildren` + `task.sequential` via hasOwnProperty gate"
  - "InMemoryBridge round-trips both raw fields on add/edit"
  - "DomainLogic.no-op detection extended so a single-field patch on completes_with_children/type doesn't short-circuit"

affects:
  - "56-07 (PROP-07 + round-trip) consumes the write surface these fields provide"

tech-stack:
  added: []
  patterns:
    - "Required-on-add, Patch-on-edit repo payload fields for service-resolved defaults"
    - "Explicit-resolution step in the add pipeline (read preferences before building payload; never rely on downstream implicit defaulting)"
    - "Enum-in-Patch wire conversion: `Patch[TaskType]` on command, `str` on repo payload; boundary conversion in PayloadBuilder"

key-files:
  created: []
  modified:
    - "src/omnifocus_operator/contracts/use_cases/add/tasks.py — AddTaskCommand gains Patch[bool] + Patch[TaskType] with null validators; AddTaskRepoPayload gets REQUIRED bool + str"
    - "src/omnifocus_operator/contracts/use_cases/edit/tasks.py — EditTaskCommand gains the Patch fields; EditTaskRepoPayload gets optional bool + str"
    - "src/omnifocus_operator/agent_messages/descriptions.py — COMPLETES_WITH_CHILDREN_WRITE + TASK_TYPE_WRITE description constants"
    - "src/omnifocus_operator/agent_messages/errors.py — 3 new error constants for null rejection"
    - "src/omnifocus_operator/service/service.py — `_resolve_type_defaults` pipeline step + wiring in _AddTaskPipeline.execute"
    - "src/omnifocus_operator/service/payload.py — build_add signature extended with keyword-only resolved params; build_edit handles both fields via _add_if_set + TaskType->str conversion"
    - "src/omnifocus_operator/service/domain.py — `_all_fields_match` field_comparisons extended to include completes_with_children + type"
    - "src/omnifocus_operator/bridge/bridge.js — handleAddTask + handleEditTask wire both fields with hasOwnProperty gates"
    - "tests/doubles/bridge.py — InMemoryBridge round-trips completedByChildren + sequential on add/edit"
    - "tests/test_contracts_field_constraints.py — 2 Wave-3 boundary guards DELETED; 18 new positive-acceptance + repo-payload tests added"
    - "tests/test_service_payload.py — 13 new tests across TestBuildAddTaskPropertySurface + TestBuildEditTaskPropertySurface"
    - "tests/test_service.py — 11 new integration tests across TestAddTaskResolvesTypeDefaults + TestEditTaskTaskPropertySurface"
    - "tests/test_hybrid_repository.py — 6 call sites updated to pass the two new required AddTaskRepoPayload fields (Rule-1)"
    - "tests/test_contracts_repetition_rule.py — 1 call site updated (Rule-1)"
    - "bridge/tests/bridge.test.js — 4 new Vitest cases on handleAddTask"
    - "bridge/tests/handleEditTask.test.js — 6 new Vitest cases on handleEditTask"

key-decisions:
  - "AddTaskRepoPayload carries completes_with_children + type as REQUIRED (no default). The service pipeline is responsible for resolving both before building the payload; this makes PROP-05/06 structurally enforced — the contract itself refuses to serialise without explicit values."
  - "EditTaskRepoPayload keeps both fields optional (None = no change). Patch semantics differ from add: edit never consults preferences; a missing value means `no change`, not `factory default`."
  - "TaskType enum on commands converts to raw str at the repo payload boundary. Bridge serialisation stays simple; the enum only lives in the agent-facing validation layer. This mirrors the 56-02 decision to keep repo payloads as pure bridge-ready data."
  - "PayloadBuilder.build_add keyword-only args for the two resolved values. Keeps the call site self-documenting — service passes `resolved_completes_with_children=True, resolved_type=\"parallel\"` by name, impossible to swap accidentally."
  - "`_resolve_type_defaults` step placed BETWEEN `_process_repetition_rule` and `_build_payload`. Independent of the other pipeline steps (no shared state), but the position makes the intent explicit: resolve the last bit of domain state, then build."
  - "Null-rejection error messages live in `agent_messages.errors` (not inline). Error-consolidation AST check (test_errors.py) enforces this convention; reusing the pattern established by ADD_PARENT_NULL."
  - "`DomainLogic._all_fields_match` extended to include both new fields. Without this, a single-field patch like `completes_with_children=False` on a task with True would short-circuit as no-op (since no other payload fields are set). Rule-2 auto-fix caught during integration testing."

patterns-established:
  - "Required-on-add / optional-on-edit pattern for service-resolved fields. When the contract demands explicit resolution (PROP-05/06), the add-side repo payload makes the field required — the type system prevents building a payload without resolution. The edit-side keeps Patch semantics because edits don't consult preferences."
  - "Enum-at-command, str-at-payload boundary conversion. Keeps bridge payloads as pure flat data while agent-facing validation uses rich types."

requirements-completed: [PROP-01, PROP-02, PROP-03, PROP-04, PROP-05, PROP-06]

duration: ~15min
completed: 2026-04-19
---

# Phase 56 Plan 06: Task-Property Write Surface Summary

**Opened the write surface for `completesWithChildren: Patch[bool]` + `type: Patch[TaskType]` on both `add_tasks` and `edit_tasks`. Service `_AddTaskPipeline._resolve_type_defaults` reads OmniFocus preferences when agent omits either field and writes the resolved value EXPLICITLY onto the repo payload — the server never relies on OmniFocus's implicit defaulting. `"singleActions"` rejected naturally via the `TaskType` enum (PROP-03 lock, no custom messaging).**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-19T17:50:00Z (approximate — initial file reading)
- **Completed:** 2026-04-19T18:06:00Z
- **Tasks:** 2 (Task 1 = contracts + rejection tests; Task 2 = service pipeline + bridge + integration tests)
- **Files modified:** 16

## Accomplishments

- **Contracts:** `AddTaskCommand` / `EditTaskCommand` gain `completes_with_children: Patch[bool]` and `type: Patch[TaskType]`. Null rejected on both (educational messages via `ADD_COMPLETES_WITH_CHILDREN_NULL` / `ADD_TASK_TYPE_NULL` / `EDIT_TYPE_FIELD_NULL`). `"singleActions"` rejected NATURALLY via the `TaskType` enum — generic Pydantic `enum`/`literal_error` with no custom messaging (PROP-03 lock, T-56-17 mitigation).
- **Repo payloads:** `AddTaskRepoPayload` carries both fields as REQUIRED (`bool` + `str`); the service pipeline must resolve them before the payload can be built. `EditTaskRepoPayload` carries both as optional (`bool | None` + `str | None`, default `None` = no change).
- **Service pipeline:** New `_resolve_type_defaults` step on `_AddTaskPipeline`, placed between `_process_repetition_rule` and `_build_payload`. Reads `OmniFocusPreferences.get_complete_with_children_default()` / `get_task_type_default()` when agent omits the field; agent value wins when present. Drains late preferences warnings. `PayloadBuilder.build_add` accepts both resolved values as required keyword-only args and writes them unconditionally.
- **Bridge:** `handleAddTask` + `handleEditTask` wire `task.completedByChildren = params.completesWithChildren` and `task.sequential = (params.type === "sequential")` under `hasOwnProperty` gates. On add the params always include both (service resolves); on edit they're gated by patch semantics. `InMemoryBridge` round-trips both raw fields so integration tests can assert stored state.
- **Domain no-op detection:** `_all_fields_match` field_comparisons extended to include both new fields. Without this, a single-field patch like `completes_with_children=False` would short-circuit as no-op. Rule-2 auto-fix, caught during integration test development.
- **Wave-2 sanity guards removed:** The two `# REMOVE IN 56-06` tests in `test_contracts_field_constraints.py` (that asserted `completesWithChildren` / `type` were rejected pre-Wave-3) are deleted. Replaced by the positive-acceptance suite in `TestAddTaskCommandAcceptsNewTypeFields` / `TestEditTaskCommandAcceptsNewTypeFields`.
- **FLAG-08 regression-free:** The 12 parametrized rejection tests for the six derived read-only flags (`hasNote`, `hasRepetition`, `hasAttachments`, `hasChildren`, `dependsOnChildren`, `isSequential`) still pass — the new writable fields don't share names with any of those, and `extra='forbid'` remains active via `CommandModel` → `StrictModel`.

## Task Commits

1. **Task 1: contracts + null-rejection + positive-acceptance tests** — `b7791a53` (feat)
   - `AddTaskCommand` / `EditTaskCommand` gain the two Patch fields with null validators.
   - `AddTaskRepoPayload` gains REQUIRED `bool` + `str`; `EditTaskRepoPayload` gains optional counterparts.
   - `COMPLETES_WITH_CHILDREN_WRITE` / `TASK_TYPE_WRITE` description constants added.
   - Wave-2 sanity guards deleted; replaced with 18 positive-acceptance + repo-payload tests.

2. **Task 2: service pipeline + bridge.js + integration tests** — `abf1f4be` (feat)
   - `_AddTaskPipeline._resolve_type_defaults` + wiring.
   - `PayloadBuilder.build_add` takes `resolved_completes_with_children` + `resolved_type` as required keyword-only args.
   - `PayloadBuilder.build_edit` passes both new fields through `_add_if_set` with TaskType→str conversion.
   - `DomainLogic._all_fields_match` extended to include both fields (Rule-2 auto-fix).
   - `bridge.js:handleAddTask` + `handleEditTask` write the raw OmniFocus fields.
   - `InMemoryBridge` round-trips both fields on add/edit.
   - Null-rejection error messages moved to `agent_messages.errors` (Rule-1 auto-fix for inline-error-string AST check).
   - 13 new payload builder tests + 11 new service integration tests + 10 new Vitest cases.
   - 7 call sites in existing tests updated to pass the new required AddTaskRepoPayload fields.

_Plan metadata commit is owned by the orchestrator per this plan's objective._

## Files Created/Modified

**Source:**
- `src/omnifocus_operator/contracts/use_cases/add/tasks.py` — Patch fields + null validators; REQUIRED repo-payload fields.
- `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` — Patch fields + combined null validator; optional repo-payload fields.
- `src/omnifocus_operator/agent_messages/descriptions.py` — `COMPLETES_WITH_CHILDREN_WRITE` + `TASK_TYPE_WRITE`.
- `src/omnifocus_operator/agent_messages/errors.py` — `ADD_COMPLETES_WITH_CHILDREN_NULL`, `ADD_TASK_TYPE_NULL`, `EDIT_TYPE_FIELD_NULL`.
- `src/omnifocus_operator/service/service.py` — `_resolve_type_defaults` step + `_build_payload` passes resolved values.
- `src/omnifocus_operator/service/payload.py` — `build_add` keyword-only resolved params; `build_edit` handles new fields via `_add_if_set` + TaskType→str conversion.
- `src/omnifocus_operator/service/domain.py` — `_all_fields_match` field_comparisons extended.
- `src/omnifocus_operator/bridge/bridge.js` — `handleAddTask` + `handleEditTask` write `task.completedByChildren` + `task.sequential`.

**Tests:**
- `tests/doubles/bridge.py` — `InMemoryBridge._handle_add_task` / `_handle_edit_task` round-trip both fields.
- `tests/test_contracts_field_constraints.py` — 2 Wave-3 boundary guards DELETED; 18 new tests (TestAddTaskCommandAcceptsNewTypeFields × 8, TestEditTaskCommandAcceptsNewTypeFields × 7, TestAddTaskRepoPayloadRequiresBothNewFields × 4, TestEditTaskRepoPayloadNewFieldsOptional × 3).
- `tests/test_service_payload.py` — 13 new tests across TestBuildAddTaskPropertySurface × 6 + TestBuildEditTaskPropertySurface × 6 + shared helpers.
- `tests/test_service.py` — 11 new integration tests (TestAddTaskResolvesTypeDefaults × 7 + TestEditTaskTaskPropertySurface × 4).
- `tests/test_hybrid_repository.py` — 6 existing call sites updated to pass the new required `AddTaskRepoPayload` fields (Rule-1).
- `tests/test_contracts_repetition_rule.py` — 1 call site updated (Rule-1).
- `bridge/tests/bridge.test.js` — 4 new Vitest cases on `handleAddTask`.
- `bridge/tests/handleEditTask.test.js` — 6 new Vitest cases on `handleEditTask`.

## Test Counts Added

- `tests/test_contracts_field_constraints.py`: **−2 deleted** (Wave-3 boundary guards), **+18 new** → net **+16**. File: 49 → 65 tests.
- `tests/test_service_payload.py`: **+13** tests. File: 17 → 30 tests.
- `tests/test_service.py`: **+11** tests. File: 174 → 185 tests.
- `bridge/tests/bridge.test.js` + `handleEditTask.test.js`: **+10** Vitest cases (75 → 85 total).

Overall pytest suite: **2 405 passed, 1 skipped** (was 2 343 at 56-05 close; +62 net).

## Decisions Made

- **Required-on-add, optional-on-edit for repo-payload task-property fields.** Add-side REQUIRES both fields so the type system rejects any payload missing them — structurally enforces PROP-05/06 (service must resolve explicitly; server never relies on OmniFocus's implicit defaulting). Edit-side keeps `bool | None` / `str | None` because edits don't consult preferences; `None` means "no change".
- **TaskType enum at the command layer, raw str at the repo payload layer.** The enum is an agent-facing validation concern (rejects `"singleActions"` naturally). The bridge operates on raw JSON — passing the enum's `.value` as `str` keeps `_dump_payload` / bridge-wire serialisation simple. Mirrors the 56-02 decision to keep repo payloads as pure bridge-ready data.
- **`_resolve_type_defaults` as a discrete pipeline step (not inlined in `_build_payload`).** Makes the "resolve then build" intent explicit. Independent of other pipeline steps (no shared state) but grouped with preference-drain behaviour so late warnings surface uniformly.
- **Null-rejection error messages in `agent_messages.errors`.** Reuses the `ADD_PARENT_NULL` pattern — constants live in one place, the AST check in `test_errors.py:TestErrorConsolidation::test_no_inline_error_strings_in_consumers` enforces the convention. Inline `msg = "…"` would fail that check; factoring out satisfies it without rewriting the AST rule.
- **No-op detection extended at the domain layer, not the pipeline layer.** `_all_fields_match` is the right surface: it already compares every edit-relevant field on the payload against the current task; adding two more entries keeps the logic in one place and the single-field patch semantics stay correct.
- **No custom messaging for `"singleActions"` rejection.** Pydantic's enum validator emits `literal_error`/`enum` with the list of allowed values. PROP-03 + T-56-20 lock this behaviour — a custom message would leak the task-vs-project derivation into error text and break FLAG-07's explicit no-message guarantee.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical functionality] `DomainLogic._all_fields_match` extended to include the two new fields**
- **Found during:** Task 2 integration testing (`TestEditTaskTaskPropertySurface::test_edit_task_updates_completes_with_children`).
- **Issue:** A single-field patch like `EditTaskCommand(id="t", completes_with_children=False)` produced a payload whose `model_fields_set` was `{"id", "completes_with_children"}`. The existing `_all_fields_match` field_comparisons dict didn't include either new field, so the comparison returned True (no mismatch detected). `detect_early_return` then short-circuited the edit as a no-op — the bridge was never called, and the stored task retained its prior value.
- **Fix:** Extended the field_comparisons dict with `"completes_with_children": task.completes_with_children` and `"type": task.type.value`. StrEnum `.value` produces the raw str the payload carries.
- **Files modified:** `src/omnifocus_operator/service/domain.py`.
- **Verification:** `uv run pytest tests/test_service.py::TestEditTaskTaskPropertySurface -x -q` — 4 tests pass (was failing).
- **Committed in:** `abf1f4be` (Task 2 commit).

**2. [Rule 1 — Inline error-string convention] Null-rejection messages moved to `agent_messages.errors`**
- **Found during:** Task 2 verification run (`uv run pytest tests/test_errors.py`).
- **Issue:** `test_errors.py:test_no_inline_error_strings_in_consumers` does an AST walk rejecting any `raise ValueError(msg)` where `msg` was just assigned from an inline string literal in the same function. My initial validators on `AddTaskCommand` (`_reject_null_completes_with_children`, `_reject_null_task_type`) and `EditTaskCommand` (`_reject_null_type_fields`) used inline strings, triggering the check.
- **Fix:** Added `ADD_COMPLETES_WITH_CHILDREN_NULL`, `ADD_TASK_TYPE_NULL`, `EDIT_TYPE_FIELD_NULL` constants to `agent_messages/errors.py`; validators now assign from the constants.
- **Files modified:** `src/omnifocus_operator/agent_messages/errors.py`, `src/omnifocus_operator/contracts/use_cases/add/tasks.py`, `src/omnifocus_operator/contracts/use_cases/edit/tasks.py`.
- **Verification:** `uv run pytest tests/test_errors.py --no-cov -x -q` — passes.
- **Committed in:** `abf1f4be` (Task 2 commit).

**3. [Rule 1 — Bug] Existing tests instantiating `AddTaskRepoPayload(name="Test")` directly**
- **Found during:** Task 2 full-suite verification.
- **Issue:** Making `completes_with_children` + `type` REQUIRED on `AddTaskRepoPayload` broke 6 existing tests in `test_hybrid_repository.py` (various `TestAddTask` cases + `TestFreshness`) and 1 test in `test_contracts_repetition_rule.py`. All built the payload manually without the new fields (they pre-dated the contract change).
- **Fix:** Updated all 7 call sites to pass `completes_with_children=True, type="parallel"` (the factory defaults — neutral values that don't affect the tests' purposes). The one that asserts `assert "dueDate" not in params` also gained two positive assertions: `params["completesWithChildren"] is True` and `params["type"] == "parallel"` (these are now always present on add — PROP-05/06 invariant).
- **Files modified:** `tests/test_hybrid_repository.py`, `tests/test_contracts_repetition_rule.py`.
- **Verification:** Both files pass in the full suite (2 405 passed).
- **Committed in:** `abf1f4be` (Task 2 commit).

---

**Total deviations:** 3 auto-fixed (1 missing critical functionality, 2 Rule-1 bugs). All were direct knock-on consequences of the plan's contract changes. No scope creep.

**Impact on plan:** None altered contracts. The `_all_fields_match` fix was essential — without it, single-field patches on the two new writable fields would silently no-op and agents would see phantom "no changes detected" warnings despite having set a real value.

## Issues Encountered

- No design-level issues. The plan's interfaces section was precise enough that implementation was mostly mechanical. The three deviations were caught immediately by the existing test suite, which validates the "Sufficient test coverage catches convention drift" pattern the codebase already invests in.

## User Setup Required

None. Pure code change. No environment, credentials, or database migration involved.

## Next Phase Readiness

- **56-07 (PROP-07 project-write rejection + end-to-end round-trip + golden master scaffolding)** can consume the full write surface this plan delivers. The domain-level rule (projects reject writes of these two fields) is independent of the contract surface opened here.
- No blockers introduced. No `RealBridge` usage anywhere (SAFE-01). No `plistlib` imports (PREFS-05). No `@model_serializer` in `contracts/` (pure data).
- FLAG-08 rejection suite (the six derived read-only flags) passes unchanged — the new writable fields don't share names with any of them.

## Threat Flags

No new security-relevant surface beyond what the plan's threat register already tracks. The two new writable fields extend the existing agent → command trust boundary; the mitigations listed in `<threat_model>` are all in place:

- **T-56-17 (Tampering — `singleActions` on tasks):** Confirmed. `TaskType` enum rejects naturally; `test_rejects_type_single_actions_via_enum_no_custom_message` asserts the `enum`/`literal_error` shape AND the absence of custom messaging.
- **T-56-18 (Elevation of Privilege — derived flags re-accepted):** Confirmed. FLAG-08 parametrized test still runs and passes (12 tests × 2 commands).
- **T-56-19 (Repudiation — implicit defaulting):** Confirmed. `TestAddTaskResolvesTypeDefaults::test_add_task_resolves_completes_with_children_from_preferences_when_omitted` / `test_add_task_resolves_type_from_preferences_when_omitted` assert the stored bridge task carries the preference value (not the OF factory default). `test_add_task_both_fields_always_present_in_bridge_params` asserts the invariant: every `add_task` bridge call carries both fields.
- **T-56-20 (Information Disclosure via custom messaging):** Confirmed. Negative-assertion test checks for forbidden phrases (`"project only"`, `"use projects instead"`, etc.) in the rejection error text.
- **T-56-21 (DoS via preference lookup):** Accepted (no change). `OmniFocusPreferences._ensure_loaded` continues to use lazy-load-once + cache; no per-task lookup cost beyond the first call.

## Self-Check: PASSED

- FOUND: `src/omnifocus_operator/contracts/use_cases/add/tasks.py` (modified)
- FOUND: `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` (modified)
- FOUND: `src/omnifocus_operator/agent_messages/descriptions.py` (modified)
- FOUND: `src/omnifocus_operator/agent_messages/errors.py` (modified)
- FOUND: `src/omnifocus_operator/service/service.py` (modified)
- FOUND: `src/omnifocus_operator/service/payload.py` (modified)
- FOUND: `src/omnifocus_operator/service/domain.py` (modified)
- FOUND: `src/omnifocus_operator/bridge/bridge.js` (modified)
- FOUND: `tests/doubles/bridge.py` (modified)
- FOUND: `tests/test_contracts_field_constraints.py` (modified)
- FOUND: `tests/test_service_payload.py` (modified)
- FOUND: `tests/test_service.py` (modified)
- FOUND: `tests/test_hybrid_repository.py` (modified)
- FOUND: `tests/test_contracts_repetition_rule.py` (modified)
- FOUND: `bridge/tests/bridge.test.js` (modified)
- FOUND: `bridge/tests/handleEditTask.test.js` (modified)
- FOUND: commit `b7791a53` (Task 1)
- FOUND: commit `abf1f4be` (Task 2)
- VERIFIED: `grep "completes_with_children: Patch\[bool\]" src/omnifocus_operator/contracts/use_cases/add/tasks.py src/omnifocus_operator/contracts/use_cases/edit/tasks.py` — 2 matches (one per file).
- VERIFIED: `grep "type: Patch\[TaskType\]" src/omnifocus_operator/contracts/use_cases/add/tasks.py src/omnifocus_operator/contracts/use_cases/edit/tasks.py` — 2 matches.
- VERIFIED: `grep "completes_with_children: bool" src/omnifocus_operator/contracts/use_cases/add/tasks.py` — the RepoPayload line shows it REQUIRED (no default).
- VERIFIED: `grep "completes_with_children: bool | None" src/omnifocus_operator/contracts/use_cases/edit/tasks.py` — the EditTaskRepoPayload line.
- VERIFIED: `grep "REMOVE IN 56-06" tests/test_contracts_field_constraints.py` — no results (sanity guards deleted).
- VERIFIED: `grep "_resolve_type_defaults" src/omnifocus_operator/service/service.py` — 2 matches (method definition + call site).
- VERIFIED: `grep "get_complete_with_children_default\|get_task_type_default" src/omnifocus_operator/service/service.py` — both names present.
- VERIFIED: `grep "resolved_completes_with_children\|resolved_type" src/omnifocus_operator/service/payload.py` — 3 matches (signature + 2 kwarg writes).
- VERIFIED: `grep "completedByChildren\|task.sequential\s*=" src/omnifocus_operator/bridge/bridge.js` — both camelCase key and `task.sequential = (params.type === "sequential")` present in handleAddTask AND handleEditTask.
- VERIFIED: `grep "params.type === \"sequential\"" src/omnifocus_operator/bridge/bridge.js` — 2 matches (add + edit).
- VERIFIED: `grep "RealBridge" tests/test_service.py tests/test_service_payload.py tests/test_contracts_field_constraints.py tests/test_hybrid_repository.py` — no results (SAFE-01).
- VERIFIED: `grep "@model_serializer" src/omnifocus_operator/contracts/` — no results (contracts are pure data).
- VERIFIED: `uv run pytest tests/ --no-cov -q` — 2 405 passed, 1 skipped.
- VERIFIED: `just test-js` (Vitest) — 85 passed (46 in bridge.test.js + 39 in handleEditTask.test.js).
- VERIFIED: `uv run mypy src/omnifocus_operator/` — Success: no issues found in 79 source files.
- VERIFIED: `just safety` — exit 0 (SAFE-01 clean).

---
*Phase: 56-task-property-surface*
*Completed: 2026-04-19*
