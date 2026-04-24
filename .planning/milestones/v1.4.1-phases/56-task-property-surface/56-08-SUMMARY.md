---
phase: 56-task-property-surface
plan: 08
subsystem: models

tags: [pydantic, actionable-entity, flag-04, gap-closure, is-sequential, projection]

# Dependency graph
requires:
  - phase: 56-task-property-surface
    provides: FLAG-04 on Task (is_sequential derived from task.type); DomainLogic.enrich_task_presence_flags; PROJECT_DEFAULT_FIELDS with shared presence flags; LIST_PROJECTS_TOOL_DOC tasks-only caveat
provides:
  - is_sequential hoisted to ActionableEntity (inherited by Task and Project, declared once)
  - DomainLogic.enrich_project_presence_flags (mirror of enrich_task_presence_flags, is_sequential only)
  - get_all_data / get_project / _ListProjectsPipeline._delegate apply project-side enrichment
  - PROJECT_DEFAULT_FIELDS includes isSequential (strip-when-false)
  - _PROJECT_BEHAVIORAL_FLAGS_NOTE fragment in descriptions.py
  - LIST_PROJECTS_TOOL_DOC + GET_PROJECT_TOOL_DOC surface isSequential with behavioral semantics
  - REQUIREMENTS.md FLAG-04 covers both tasks and projects
affects: [phase-57-parent-filter, v1.5-UI-perspectives]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inherited-field hoist: base-class declaration + per-subclass enrichment method (mirrors how has_note/has_repetition/has_attachments sit on ActionableEntity while enrich_task_presence_flags/enrich_project_presence_flags branch per type)"
    - "Project-scoped tool-doc fragment: _PROJECT_BEHAVIORAL_FLAGS_NOTE is a subset of _BEHAVIORAL_FLAGS_NOTE (tasks carry both isSequential + dependsOnChildren; projects carry isSequential only)"

key-files:
  created: []
  modified:
    - "src/omnifocus_operator/models/common.py (ActionableEntity gains is_sequential)"
    - "src/omnifocus_operator/models/task.py (is_sequential declaration removed; depends_on_children stays)"
    - "src/omnifocus_operator/service/domain.py (enrich_project_presence_flags defined)"
    - "src/omnifocus_operator/service/service.py (3 callsites wired: get_all_data, get_project, _ListProjectsPipeline._delegate)"
    - "src/omnifocus_operator/config.py (PROJECT_DEFAULT_FIELDS += isSequential)"
    - "src/omnifocus_operator/agent_messages/descriptions.py (IS_SEQUENTIAL_DESC reworded; _PROJECT_BEHAVIORAL_FLAGS_NOTE introduced; LIST_PROJECTS_TOOL_DOC + GET_PROJECT_TOOL_DOC surface isSequential)"
    - ".planning/REQUIREMENTS.md (FLAG-04 revised)"
    - "tests/test_models.py (project is_sequential assertion flipped + field count +1)"
    - "tests/test_service_domain.py (TestDomainLogicEnrichProjectPresenceFlags added)"
    - "tests/test_service.py (get_project/list_projects/get_all_data enrichment integration tests)"
    - "tests/test_cross_path_equivalence.py (project is_sequential cross-path tests via service stack)"
    - "tests/test_projection.py (project strip/emit assertions flipped; _build_phase5604_project_dict gains is_sequential)"
    - "tests/test_descriptions.py (LIST_PROJECTS_TOOL_DOC + GET_PROJECT_TOOL_DOC assertions; IS_SEQUENTIAL_DESC drops tasks-only; GET_PROJECT_TOOL_DOC import added)"

key-decisions:
  - "FLAG-04 applies uniformly to tasks AND projects: the next-in-line semantic holds on both (locked to ProjectType.SEQUENTIAL only — singleActions does NOT flip is_sequential even though the raw sequential bit may be set, per HIER-05 precedence)."
  - "FLAG-05 (dependsOnChildren) stays tasks-only by explicit design — projects are always containers, so there is no 'real unit of work waiting on children' distinction to draw."
  - "Field hoisted to ActionableEntity (single declaration) rather than duplicated on Task and Project — inheritance is the natural expression of 'this semantic applies to both'."
  - "Existing Method Object convention preserved: enrichment stays INLINE in _ListProjectsPipeline._delegate; no new pipeline class introduced."
  - "get_project grows from a one-liner pass-through to applying enrichment — matches how 56-03 extended get_task. The service-layer-convention 'read delegations stay inline' still holds (this is still a one-liner-plus-one at the service level; enrichment is a product decision that must not live in the repository)."

patterns-established:
  - "Cross-entity derived flag: one declaration on a shared base class + per-subclass enrichment method lets the same flag carry the same JSON shape while computing from different inputs (Task.type vs Project.type — with HIER-05 precedence baked into how Project.type got assembled earlier in the pipeline)."

requirements-completed: [FLAG-04]

# Metrics
duration: ~50min
completed: 2026-04-20
---

# Phase 56 Plan 08: is_sequential Hoist to ActionableEntity Summary

**FLAG-04 applied to both tasks and projects via ActionableEntity hoist + sibling project enrichment — closes Human UAT gap G1 so agents reasoning about sequential projects see the same next-in-line signal they get on sequential tasks.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 2 (both TDD: RED + GREEN)
- **Files modified:** 12 (6 source + 6 tests + 1 requirements doc — counted separately)
- **Net test delta:** +20 (2425 passed after — was ~2405 pre-plan)

## Accomplishments

- `is_sequential` declared once on `ActionableEntity` — both `Task` and `Project` inherit it with the same semantic.
- `DomainLogic.enrich_project_presence_flags` mirrors `enrich_task_presence_flags` and wires into all three project read paths (`get_all_data`, `get_project`, `_ListProjectsPipeline._delegate`).
- `isSequential` surfaces on the project default response (`PROJECT_DEFAULT_FIELDS`) with strip-when-false inherited from existing projection logic.
- Tool docs teach the semantic on the project surface too (`LIST_PROJECTS_TOOL_DOC`, `GET_PROJECT_TOOL_DOC`) with a project-scoped `_PROJECT_BEHAVIORAL_FLAGS_NOTE` fragment (isSequential only — `dependsOnChildren` stays tasks-only).
- `REQUIREMENTS.md` FLAG-04 wording revised to the cross-entity scope; checkbox marked complete.

## Task Commits

Each task executed via the RED → GREEN TDD cycle:

1. **Task 1 RED: failing tests for is_sequential hoist** — `4793fc54` (test)
2. **Task 1 GREEN: hoist + enrichment + service wiring** — `58fdfca6` (feat)
3. **Task 2 RED: failing tests for project default + tool docs** — `f0dc16d6` (test)
4. **Task 2 GREEN: config + descriptions + REQUIREMENTS** — `0dec0005` (feat)

## Files Created/Modified

### Source code

- `src/omnifocus_operator/models/common.py` — ActionableEntity.is_sequential (single declaration, inherited by Task and Project).
- `src/omnifocus_operator/models/task.py` — Task.is_sequential declaration removed (inherited); `depends_on_children` stays task-only.
- `src/omnifocus_operator/service/domain.py` — `DomainLogic.enrich_project_presence_flags` added below `enrich_task_presence_flags`; identical shape, sets `is_sequential` only.
- `src/omnifocus_operator/service/service.py` — three wires:
  - `get_all_data`: `raw.model_copy(update={"tasks": ..., "projects": enriched_projects})`.
  - `get_project`: grew from pass-through to `project = lookup; return enrich_project_presence_flags(project)`.
  - `_ListProjectsPipeline._delegate`: insert enrichment between repo call and `_result_from_repo`, mirroring `_ListTasksPipeline._delegate`.
- `src/omnifocus_operator/config.py` — `PROJECT_DEFAULT_FIELDS += {"isSequential"}`.
- `src/omnifocus_operator/agent_messages/descriptions.py` — `IS_SEQUENTIAL_DESC` drops the `"Tasks-only."` prefix; `_PROJECT_BEHAVIORAL_FLAGS_NOTE` introduced; `LIST_PROJECTS_TOOL_DOC` default-fields list + behavioral note + scoped tasks-only caveat (to `dependsOnChildren` only); `GET_PROJECT_TOOL_DOC` fields list + behavioral note.

### Requirements

- `.planning/REQUIREMENTS.md` — FLAG-04 wording rewritten to cover both tasks and projects; checkbox flipped to `[x]`.

### Tests

- `tests/test_models.py` — flipped `is_sequential not in Project.model_fields` → positive; `Project.model_fields` count 28 → 29.
- `tests/test_service_domain.py` — `TestDomainLogicEnrichProjectPresenceFlags` (3 truth-table cases + copy-vs-mutation case).
- `tests/test_service.py` — 5 new integration tests (get_project ×3, get_all_data ×1, list_projects ×1) each with a seeded `@pytest.mark.snapshot`.
- `tests/test_cross_path_equivalence.py` — 3 cross-path tests (get_all_data, list_projects, get_project) each builds an `OperatorService` around `cross_repo` to prove enrichment applies equivalently on both `HybridRepository` and `BridgeOnlyRepository`.
- `tests/test_projection.py` — `_build_phase5604_project_dict` gains `is_sequential`; two flipped project-side assertions; two new assertions (strip-when-false + emit-when-true + depends_on_children-absent-even-with-hierarchy).
- `tests/test_descriptions.py` — `test_list_projects_tool_doc_surfaces_is_sequential` (renamed + inverted); `test_is_sequential_desc_drops_tasks_only_prefix_after_phase_5608`; `test_get_project_tool_doc_surfaces_is_sequential`; `GET_PROJECT_TOOL_DOC` added to imports.

## Surface-area diff (exact)

### Field-declaration move

| Before                                                             | After                                                       |
| ------------------------------------------------------------------ | ----------------------------------------------------------- |
| `Task.is_sequential: bool = Field(default=False, description=...)` | (removed — inherited via ActionableEntity)                  |
| (no declaration)                                                   | `ActionableEntity.is_sequential: bool = Field(default=False, description=IS_SEQUENTIAL_DESC)` |

`Task.model_fields` still contains `"is_sequential"` (inherited). `Project.model_fields` gains `"is_sequential"` for the first time.

### Pipeline wiring

`enrich_project_presence_flags` is called from:

1. `OperatorService.get_all_data` (service.py ~line 154) — list comprehension over `raw.projects` in the existing `model_copy(update={...})`.
2. `OperatorService.get_project` (service.py ~line 175) — applied to the result of `lookup_project`.
3. `_ListProjectsPipeline._delegate` (service.py ~line 544) — list comprehension over `repo_result.items`, then `model_copy(update={"items": enriched_items})`.

### PROJECT_DEFAULT_FIELDS diff

```diff
 PROJECT_DEFAULT_FIELDS: frozenset[str] = frozenset(
     {
         "id", "name", "availability",
         "dueDate", "deferDate", "plannedDate",
         "flagged", "urgency", "tags",
         "hasNote", "hasRepetition", "hasAttachments",
+        "isSequential",
     }
 )
```

### IS_SEQUENTIAL_DESC diff

```diff
-IS_SEQUENTIAL_DESC = f"Tasks-only. True when type == 'sequential'. {_IS_SEQUENTIAL_SEMANTIC}"
+IS_SEQUENTIAL_DESC = f"True when type == 'sequential'. {_IS_SEQUENTIAL_SEMANTIC}"
```

### LIST_PROJECTS_TOOL_DOC diff

```diff
-Default fields (always returned): id, name, availability, dueDate, deferDate, plannedDate, flagged, urgency, tags, hasNote, hasRepetition, hasAttachments.
-
-isSequential and dependsOnChildren are tasks-only; projects expose the full type enum via include=['hierarchy'].
+Default fields (always returned): id, name, availability, dueDate, deferDate, plannedDate, flagged, urgency, tags, hasNote, hasRepetition, hasAttachments, isSequential.
+
+{_PROJECT_BEHAVIORAL_FLAGS_NOTE}
+
+dependsOnChildren is tasks-only (projects are always containers); projects expose the full type enum (incl. singleActions) via include=['hierarchy'].
```

### GET_PROJECT_TOOL_DOC diff

```diff
-Fields: urgency, availability, dueDate, deferDate, plannedDate, flagged, tags [{id, name}], nextTask {id, name}, folder {id, name}, reviewInterval, nextReviewDate.
+Fields: urgency, availability, dueDate, deferDate, plannedDate, flagged, tags [{id, name}], isSequential, nextTask {id, name}, folder {id, name}, reviewInterval, nextReviewDate.
+
+{_PROJECT_BEHAVIORAL_FLAGS_NOTE}
```

### Flipped negative assertions (4 → positive)

| File                         | Test                                                                                         | Before                                   | After                                              |
| ---------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------- | -------------------------------------------------- |
| `tests/test_models.py:784`   | `test_project_defines_is_sequential_field_with_false_default` (renamed from `...does_not_define...`) | `"is_sequential" not in Project.model_fields` | `"is_sequential" in Project.model_fields` + default check |
| `tests/test_projection.py:584` | `test_project_default_fields_include_is_sequential` (renamed from `...exclude_tasks_only_flags`; separate `dependsOnChildren` assertion retained) | `"isSequential" not in PROJECT_DEFAULT_FIELDS` | `"isSequential" in PROJECT_DEFAULT_FIELDS`         |
| `tests/test_projection.py` (TestNoSuppressionInvariantForProjects) | `test_default_response_strips_is_sequential_when_false` + `test_default_response_emits_is_sequential_when_true` + `test_project_depends_on_children_absent_even_with_hierarchy` | (one class-scoped assertion of “isSequential not in projected”) | positive assertions for strip-when-false, emit-when-true; `dependsOnChildren` stays out |
| `tests/test_descriptions.py:535` | `test_list_projects_tool_doc_surfaces_is_sequential` (renamed from `...does_not_claim...`) | conditional "if isSequential in doc → require tasks-only" | positive: `isSequential in doc` + behavioral phrase + `dependsOnChildren` tasks-only caveat still present |

### REQUIREMENTS.md FLAG-04 diff

```diff
-- [ ] **FLAG-04**: Task default response includes `isSequential: true` when `type == "sequential"`; stripped when false (**tasks-only** — projects use full `type` enum via `hierarchy` include)
+- [x] **FLAG-04**: Default response on **tasks and projects** includes `isSequential: true` when `type == "sequential"`; stripped when false. On tasks the semantic is about the next-in-line subtask; on projects it's about the next-in-line child task within the project. `dependsOnChildren` (FLAG-05) stays tasks-only — projects are always containers. (Phase 56-08 hoisted the field from `Task` to `ActionableEntity` to close Human UAT gap G1.)
```

## Decisions Made

- **FLAG-04 is a cross-entity semantic, not a tasks-only bookkeeping flag.** Hoisted `is_sequential` to `ActionableEntity` (single declaration) rather than duplicating on `Project`; inheritance is the natural expression.
- **FLAG-05 stays tasks-only.** Projects are always containers; the "real unit of work waiting on children" semantic has no analog. No `depends_on_children` field introduced on projects; the tool doc was updated to scope the tasks-only caveat to `dependsOnChildren` only.
- **HIER-05 precedence is honored by the derivation.** `is_sequential` is computed from the final assembled `ProjectType` (SEQUENTIAL → True; PARALLEL or SINGLE_ACTIONS → False). A project with both `sequential=True` and `containsSingletonActions=True` resolves to `type == singleActions` (HIER-05) and therefore `is_sequential == False` — the cross-path equivalence tests exercise this exact case on `proj-1`.
- **Method Object convention preserved.** No new pipeline class; enrichment stays INLINE inside `_ListProjectsPipeline._delegate`, mirroring the existing task-side pattern.
- **Service-layer-convention nuance on `get_project`.** Read-delegation pass-throughs normally stay one-liners. `get_project` now applies enrichment — this is identical to how 56-03 extended `get_task`, and the precedent is the right guide: enrichment is a product decision that must live at the service layer, not in the repository.

## Deviations from Plan

None — plan executed exactly as written. The plan explicitly anticipated every step (interfaces, exact lines, test files, and REQUIREMENTS.md wording). No auto-fixes were needed.

**Note on test-count assertion update:** `test_project_from_bridge_json` asserts `len(Project.model_fields) == 28`. Hoisting `is_sequential` to `ActionableEntity` adds exactly one field to `Project`, so the assertion was updated to `29` with a comment annotating the Phase 56-08 delta. This is a mechanical tracking update (not a deviation) — the plan listed `tests/test_models.py` as modified.

## Issues Encountered

None — the plan's `<interfaces>` section was precise enough that no re-exploration was needed. The only two surprises were mechanical and expected:

1. The `test_project_from_bridge_json` field-count assertion needed bumping 28 → 29 (noted above).
2. The `test_every_project_model_field_in_exactly_one_group` invariant fired in the Task 2 RED phase because Project now has `is_sequential` in `model_fields` but `PROJECT_DEFAULT_FIELDS` didn't yet — adding `"isSequential"` to the frozenset closed the invariant as intended.

## Verification Results

| Check | Result |
| ----- | ------ |
| `uv run pytest tests/ --no-cov -q` | 2425 passed, 1 skipped |
| `uv run mypy src/omnifocus_operator/` | Success — no issues in 79 source files |
| `uv run pytest tests/test_output_schema.py -x -q --no-cov` | 35 passed |
| Golden master invariant (`test_golden_master*`) | 19 passed, 1 skipped — 56-07's GOLDEN_MASTER_CAPTURE guard still holds |
| `grep -n "RealBridge" tests/test_service_domain.py tests/test_service.py tests/test_cross_path_equivalence.py tests/test_models.py tests/test_projection.py tests/test_descriptions.py` | No matches (SAFE-01 preserved) |
| `is_sequential` source locations | Exactly one field declaration in `src/omnifocus_operator/models/common.py` |
| `enrich_project_presence_flags` callsites | 4 matches across `domain.py` + `service.py` (1 def + 3 wires) |

## Confirmations

- **SAFE-01/02 preserved:** zero RealBridge usage introduced. All new tests use InMemoryBridge via the existing `service`/`cross_repo`/`cross_service` fixtures.
- **Method Object convention preserved:** no new pipeline class; `_ListProjectsPipeline._delegate` gains an inline enrichment step matching `_ListTasksPipeline._delegate`.
- **FLAG-05 remains tasks-only by design:** the `dependsOnChildren` field was not added to projects; the tool doc now scopes the tasks-only caveat to it only.
- **No RRULE-boundary, warning-path, or write-path changes:** this plan was a pure read-surface hoist.
- **WR-01 (duplicate preferences warning) NOT addressed:** out of scope for this gap-closure plan per the plan's scope-discipline note. Separately tracked in `56-REVIEW.md`.

## Test Count Delta

- Before: 2405-test baseline (per plan verification).
- After: 2425 passed + 1 skipped. Net delta: **+20 tests** across:
  - `test_service_domain.py` (+4: `TestDomainLogicEnrichProjectPresenceFlags`)
  - `test_service.py` (+5: project-side enrichment integration tests)
  - `test_cross_path_equivalence.py` (+6: 3 service-layer cross-path tests × bridge+sqlite parametrization = 6 test cases at runtime)
  - `test_projection.py` (+3 net: flipped one negative, added two positives and one dependsOnChildren-stays-tasks-only)
  - `test_descriptions.py` (+2: GET_PROJECT_TOOL_DOC surface + IS_SEQUENTIAL_DESC drops tasks-only)

## Next Phase Readiness

- **Phase 57 (Subtree retrieval)** unaffected by this plan — the hoist is strictly additive on the read surface.
- **v1.7 (project writes)** will inherit the hoist naturally — when project writes land, `is_sequential` will be derived from the write-side `type` field just like it is on tasks today.
- Human UAT **G2** (golden master via `uat/capture_golden_master.py`) is **NOT** addressed by this plan and remains pending in `56-HUMAN-UAT.md`.

## Self-Check: PASSED

Files verified to exist:

- `.planning/phases/56-task-property-surface/56-08-SUMMARY.md` — this document.
- `src/omnifocus_operator/models/common.py` — `is_sequential` declaration present.
- `src/omnifocus_operator/service/domain.py` — `enrich_project_presence_flags` defined.
- `src/omnifocus_operator/service/service.py` — three callsites wired.
- `src/omnifocus_operator/config.py` — `isSequential` in `PROJECT_DEFAULT_FIELDS`.
- `src/omnifocus_operator/agent_messages/descriptions.py` — `_PROJECT_BEHAVIORAL_FLAGS_NOTE` + reworded `IS_SEQUENTIAL_DESC` + updated `LIST_PROJECTS_TOOL_DOC` + updated `GET_PROJECT_TOOL_DOC`.
- `.planning/REQUIREMENTS.md` — FLAG-04 revised.

Commits verified present in `git log`:

- `4793fc54` — RED Task 1
- `58fdfca6` — GREEN Task 1
- `f0dc16d6` — RED Task 2
- `0dec0005` — GREEN Task 2

---

*Phase: 56-task-property-surface*
*Plan: 08*
*Completed: 2026-04-20*
