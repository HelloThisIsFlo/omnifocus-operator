# Roadmap: OmniFocus Operator

## Milestones

- ✅ **v1.0 Foundation** — Phases 1-9 (shipped 2026-03-07) — [archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 HUGE Performance Upgrade** — Phases 10-13 (shipped 2026-03-07) — [archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Writes & Lookups** — Phases 14-17 (shipped 2026-03-15) — [archive](milestones/v1.2-ROADMAP.md)
- ✅ **v1.2.1 Architectural Cleanup** — Phases 18-28 (shipped 2026-03-23) — [archive](milestones/v1.2.1-ROADMAP.md)
- ✅ **v1.2.2 FastMCP v3 Migration** — Phases 29-31 (shipped 2026-03-26) — [archive](milestones/v1.2.2-ROADMAP.md)
- ✅ **v1.2.3 Repetition Rule Write Support** — Phases 32-33 (shipped 2026-03-29) — [archive](milestones/v1.2.3-ROADMAP.md)
- ✅ **v1.3 Read Tools** — Phases 34-38 (shipped 2026-04-05) — [archive](milestones/v1.3-ROADMAP.md)
- ✅ **v1.3.1 First-Class References** — Phases 39-44 (shipped 2026-04-07) — [archive](milestones/v1.3.1-ROADMAP.md)
- ✅ **v1.3.2 Date Filtering** — Phases 45-50 (shipped 2026-04-11) — [archive](milestones/v1.3.2-ROADMAP.md)
- ✅ **v1.3.3 Ordering & Move Fix** — Phases 51-52 (shipped 2026-04-12) — [archive](milestones/v1.3.3-ROADMAP.md)
- ✅ **v1.4 Response Shaping & Batch Processing** — Phases 53-55 (shipped 2026-04-17) — [archive](milestones/v1.4-ROADMAP.md)
- 🚧 **v1.4.1 Task Property Surface & Subtree Retrieval** — Phases 56-58
- 📋 **v1.5 Project Writes** — see [MILESTONE-v1.5.md](../.research/updated-spec/MILESTONE-v1.5.md)
- 📋 **v1.6 UI & Perspectives** — see [MILESTONE-v1.6.md](../.research/updated-spec/MILESTONE-v1.6.md)
- 📋 **v1.7 Production Hardening** — see [MILESTONE-v1.7.md](../.research/updated-spec/MILESTONE-v1.7.md)

## Phases

### 🚧 v1.4.1 Task Property Surface & Subtree Retrieval (In progress)

- [x] **Phase 56: Task Property Surface** — Preferences, cache reads, presence flags, expanded `hierarchy` group, writable `completesWithChildren` + `type` with preference-driven create-defaults, strip-rules cleanup (completed 2026-04-19)
- [ ] **Phase 57: Parent Filter & Filter Unification** — `parent` filter on `list_tasks`, shared `get_tasks_subtree` helper, warnings (+ gap-closure plans 57-04 / 57-05 from UAT)

## Phase Details

### Phase 56: Task Property Surface

**Goal**: Agents can read and write the new task property surface (`completesWithChildren`, per-type `type`, presence flags, expanded `hierarchy` include group) end-to-end — reads served by the SQLite cache on `HybridRepository` and amortized snapshot enumeration on `BridgeOnlyRepository` with no per-row bridge fallback; writes honor `Patch[bool]` / `Patch[TaskType]` semantics on tasks, and omitted create-values resolve to the user's explicit OmniFocus preference (never OF's implicit defaulting). Projects remain read-only for the new writable fields (project writes deferred to v1.5).

**Depends on**: Nothing (v1.4 shipped)

**Requirements**: PREFS-01, PREFS-02, PREFS-03, PREFS-04, PREFS-05, CACHE-01, CACHE-02, CACHE-03, CACHE-04, FLAG-01, FLAG-02, FLAG-03, FLAG-04, FLAG-05, FLAG-06, FLAG-07, FLAG-08, HIER-01, HIER-02, HIER-03, HIER-04, HIER-05, PROP-01, PROP-02, PROP-03, PROP-04, PROP-05, PROP-06, PROP-07, PROP-08, STRIP-11

**Success Criteria** (what must be TRUE):

  1. Both repositories return identical values for `completesWithChildren`, `type`, and `hasAttachments` on tasks and projects via the SQLite cache (`HybridRepository`: `Task.completeWhenChildrenComplete`, `Task.sequential`, `ProjectInfo.containsSingletonActions`, batched `SELECT task FROM Attachment` once per snapshot) and amortized OmniJS enumeration (`BridgeOnlyRepository`: inline `completedByChildren`/`sequential`/`attachments.length` during the existing snapshot-build script) — cross-path equivalence proven, no per-row bridge fallback on either path
  2. `OmniFocusPreferences` surfaces `OFMCompleteWhenLastItemComplete` and `OFMTaskDefaultSequential` via the existing bridge-based lazy-load-once pattern (extended `bridge/bridge.js:handleGetSettings()` + extended `service/preferences.py`) — absence = user kept OF factory default (valid signal, not an error), service resolves to `true` / `"parallel"` respectively, works uniformly under both repos with no plistlib in the service layer, no new settings-access code path
  3. Default task response emits `hasNote`, `hasRepetition`, `hasAttachments`, `isSequential` (tasks-only, `type == "sequential"`), and `dependsOnChildren` (tasks-only, `hasChildren AND NOT completesWithChildren`) — all strip-when-false; default project response emits `hasNote`, `hasRepetition`, `hasAttachments`; `hierarchy` include group adds `hasChildren` (strip-when-false), `type` (full enum always — `ProjectType` constructed at the service layer from `(sequential, containsSingletonActions)` with `"singleActions"` taking precedence), and `completesWithChildren` (always; added to `NEVER_STRIP` so `false` survives)
  4. No-suppression invariant holds — when `hierarchy` is requested, all three fields still emit per their strip rules even when a default-response derived flag (`dependsOnChildren`, `isSequential`) already conveys overlapping signal; default and include pipelines remain independent (proven by contract test that requests both and verifies the intentional redundant emission); `hasChildren` name preserved (not renamed to `hasSubtasks`); tool descriptions on `list_tasks`/`get_task`/`list_projects` surface the behavioral meaning of `dependsOnChildren` (real task waiting on children) and `isSequential` (only next-in-line child is available)
  5. `add_tasks` and `edit_tasks` accept `completesWithChildren` (`Patch[bool]`) and `type` (`Patch[TaskType]` where `TaskType = "parallel" | "sequential"`) on tasks with null rejected and `"singleActions"` rejected naturally via enum validation; when omitted on `add_tasks`, the service writes the resolved preference value explicitly (factory default `true` / `"parallel"` when the OF Setting store has no value) — server never relies on OmniFocus's implicit defaulting; writes to these fields on projects are rejected at the tool surface (project writes deferred to v1.5)
  6. Derived read-only flags (`hasNote`, `hasRepetition`, `hasAttachments`, `hasChildren`, `dependsOnChildren`, `isSequential`) are rejected by Pydantic `extra="forbid"` on `add_tasks`/`edit_tasks` (generic schema error, no custom messaging); `availability` removed from `NEVER_STRIP` as pre-existing defensive entry with no actual purpose
  7. Round-trip test on both `HybridRepository` and `BridgeOnlyRepository`: creating a task with `completesWithChildren` / `type` set, reading back via `get_task` and `list_tasks`, editing to flip each value, and verifying the expected cache-backed values — plus create-default paths (omit both fields, read back) verified end-to-end against a captured golden master

**Plans:** 9/9 plans complete

Plans:

- [x] 56-01-PLAN.md — Preferences extension (bridge `handleGetSettings` + `OmniFocusPreferences` get_complete_with_children_default / get_task_type_default with lazy-load-once caching + fallback) [PREFS-01..05]
- [x] 56-02-PLAN.md — Cache read paths: TaskType/ProjectType enums + ActionableEntity presence fields + HybridRepository SQLite reads (batched attachment set) + BridgeOnlyRepository amortised enumeration + cross-path equivalence [CACHE-01..04, HIER-03]
- [x] 56-03-PLAN.md — Service-layer derived flags: `is_sequential` + `depends_on_children` fields on Task + `DomainLogic.enrich_task_presence_flags` + `assemble_project_type` with HIER-05 precedence wired into all three read pipelines [FLAG-01..05, HIER-05]
- [x] 56-04-PLAN.md — Projection reshape: `availability` out of NEVER_STRIP (STRIP-11), `completesWithChildren` in (PROP-08), hierarchy group expanded with `type`+`completesWithChildren`, TASK/PROJECT default fields include new flags, no-suppression invariant contract test [HIER-01, HIER-02, HIER-04, FLAG-06, PROP-08, STRIP-11]
- [x] 56-05-PLAN.md — Tool descriptions surface FLAG-07 behavioral meaning (`dependsOnChildren` = real task waiting on children; `isSequential` = only next-in-line available) + field-level Field(description=CONSTANT) wiring + FLAG-08 parametrized contract tests proving all 6 derived read-only flags are rejected by `extra="forbid"` [FLAG-07, FLAG-08]
- [x] 56-06-PLAN.md — Write surface: `Patch[bool]` / `Patch[TaskType]` on AddTask/EditTask commands + null rejection + natural `singleActions` enum rejection + `_resolve_type_defaults` service step reading preferences + bridge.js writes `completedByChildren` / `sequential` [PROP-01..06]
- [x] 56-07-PLAN.md — PROP-07 structural guardrail (no project-write tools registered) + round-trip tests on both repos for agent-value + create-default paths + golden master scaffolding (human-only capture) [PROP-07]

**Plan waves** (guidance for `/gsd-plan-phase 56`, not a hard split): given the phase breadth, consider decomposing internally as (1) preferences + cache foundation — bridge/settings extension, `OmniFocusPreferences` extension, cache read paths, cross-path equivalence; (2) read surface — default-response flags, expanded `hierarchy` group, `ProjectType` assembly, strip-rules cleanup (`NEVER_STRIP` additions + `availability` removal), `extra="forbid"` rejection of derived fields; (3) write surface — `Patch[bool]` / `Patch[TaskType]` on tasks, create-default resolution via preferences, project-write rejection, round-trip verification against golden master.

### Phase 57: Parent Filter & Filter Unification

**Goal**: Agents can fetch a task's full descendant subtree through `list_tasks` with a single call using the new `parent` filter — sharing one service-layer `get_tasks_subtree` helper and one repo-layer `candidate_task_ids` primitive with the existing `project` filter, with the full warning surface guiding correct usage.

**Depends on**: Phase 56 (stable cache read path for the children structure)

**Requirements**: PARENT-01, PARENT-02, PARENT-03, PARENT-04, PARENT-05, PARENT-06, PARENT-07, PARENT-08, PARENT-09, UNIFY-01, UNIFY-02, UNIFY-03, UNIFY-04, UNIFY-05, UNIFY-06, WARN-01, WARN-02, WARN-03, WARN-04, WARN-05

**Success Criteria** (what must be TRUE):

  1. `list_tasks` accepts a single `parent` reference (name substring or ID) resolved via the standard three-step resolver (`$` prefix → exact ID → name substring); array references rejected at validation time; `parent: "$inbox"` is accepted and produces the identical result set to `project: "$inbox"` with the same contradiction rules (e.g., `parent: "$inbox"` + `inInbox=false` → error)
  2. The `parent` filter returns all descendants of the resolved reference at any depth, AND-composes with every other filter (project, tags, dates, etc.) with no special precedence, preserves outline order, and paginates via the existing limit + cursor mechanism; resolved task is included as anchor; resolved project produces no anchor (projects are not rows in `list_tasks`)
  3. `project` and `parent` filters share one service-layer mechanism — `get_tasks_subtree(ref_id, snapshot, accept_entity_types) -> set[str]` shared helper in `service/subtree.py` used by both `_resolve_project()` and `_resolve_parent()` pipeline steps, `ListTasksRepoQuery.candidate_task_ids: list[str] | None` as the unified wire-level primitive (retiring the old `project_ids` field; renamed from `task_id_scope` in 57-04), conditional anchor injection inside `get_tasks_subtree` branching on the resolved entity's type; same entity resolved via either filter produces byte-identical results (proven by cross-filter equivalence contract test)
  4. Scope-expansion logic lives at the service layer; primitive set-membership filter application stays at the repo (Python-filter benchmark locked p95 ≤ 1.30 ms at 10K — 77× under the viable threshold); HybridRepository uses indexed `WHERE t.persistentIdentifier IN (?, ?, ...)`; BridgeOnlyRepository uses `items = [t for t in items if t.id in scope_set]`; single code path across both repos (no divergent subtree implementations)
  5. Five warnings surface correctly: new filtered-subtree warning (locked verbatim text) fires when `project` or `parent` is combined with any other dimensional filter; new `parent` + `project` combined warning fires when both are specified; new parent-resolves-to-project warning fires when all matches are projects; existing multi-match and inbox-name-substring warnings trigger on `parent` resolution via the same infrastructure used by other substring-resolving filters; all warnings live in the domain layer (filter-semantics advice), not projection

**Plans:** 5 plans (3 original + 2 gap-closure)

Plans:

- [x] 57-01-PLAN.md — Unify repo primitive: ship `service/subtree.py::get_tasks_subtree`, retire `ListTasksRepoQuery.project_ids`, add `task_id_scope`, rewrite both repos to set-membership on task PKs, rewrite `_resolve_project` through `get_tasks_subtree`, migrate all existing `project_ids` tests [UNIFY-01, UNIFY-03, UNIFY-04, UNIFY-05, UNIFY-06, PARENT-03, PARENT-04]
- [x] 57-02-PLAN.md — Parent filter surface: `ListTasksQuery.parent: Patch[str]`, `PARENT_FILTER_DESC`, 3-arg `resolve_inbox(in_inbox, project, parent)`, `_resolve_parent` + `_check_inbox_parent_warning` pipeline steps, `PARENT_RESOLVES_TO_PROJECT_WARNING`, scope-set intersection in `_build_repo_query`, cross-filter equivalence contract test (UNIFY-02 / D-15) [PARENT-01, PARENT-02, PARENT-05, PARENT-06, PARENT-07, PARENT-08, PARENT-09, UNIFY-02, WARN-02, WARN-05]
- [x] 57-03-PLAN.md — Pipeline-level warnings: `FILTERED_SUBTREE_WARNING` (verbatim locked text) via `DomainLogic.check_filtered_subtree`; `PARENT_PROJECT_COMBINED_WARNING` via `DomainLogic.check_parent_project_combined`; both emitted from `_ListTasksPipeline.execute` after all resolutions (WARN-04 domain-layer placement) [WARN-01, WARN-03, WARN-04]
- [x] 57-04-PLAN.md — Gap closure (G1 + G2 + G3): empty-scope short-circuit + no-match resolver flip (did-you-mean preserved, "skipped" wording dropped) + parent-anchor preservation via new `pinned_task_ids` primitive (Option A: repo-layer OR-with-pinned); rename `task_id_scope` → `candidate_task_ids`. Supersedes Phase 35.2 D-02e. [PARENT-04, PARENT-05, UNIFY-02, WARN-01, WARN-05]
- [x] 57-05-PLAN.md — Gap closure (G4): value-aware `is_non_default` helper + `availability` added to `_SUBTREE_PRUNING_FIELDS` + `check_filtered_subtree` switches to value-aware predicate for the pruning iteration (scope check keeps `is_set`). [WARN-01]

**Plan waves:** Plan 01 → 02 → 03 sequential (Wave 1→2→3) because each depends on the previous one's pipeline state. Gap-closure plans 57-04 and 57-05 run in parallel (Wave 4) — they modify disjoint file sets: 57-04 touches `service/service.py` + repos + `contracts/use_cases/list/tasks.py`; 57-05 touches `service/domain.py` + `contracts/base.py`. Both are `autonomous: true`.

**Gaps closed (from Phase 57 UAT)**:

1. **G1** — Anchor preservation under AND composition (closed by 57-04 via Option A: repo-layer OR-with-`pinned_task_ids`; existing xfail test promoted to pass)
2. **G2** — Empty `candidate_task_ids` cross-path divergence (closed by 57-04 via service-layer short-circuit; both repos never see empty scope)
3. **G3** — No-match resolver fallback (closed by 57-04; Phase 35.2 D-02e's bundled "skip filter + return all" fallback unbundled — did-you-mean stays, permissive fallback removed; applies to project, parent, tags uniformly)
4. **G4** — Non-default `availability` under-alerting (closed by 57-05 via value-aware `is_non_default` predicate)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 56. Task Property Surface | v1.4.1 | 9/9 | Complete    | 2026-04-20 |
| 57. Parent Filter & Filter Unification | v1.4.1 | 5/5 (3/3 + 2/2 gap-closure) | Complete    | 2026-04-24 |
