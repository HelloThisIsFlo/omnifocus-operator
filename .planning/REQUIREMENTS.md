# Requirements: OmniFocus Operator

**Defined:** 2026-04-19
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents — executive function infrastructure that works at 7:30am.

Full design spec: `.research/updated-spec/MILESTONE-v1.4.1.md` (design locked after 4-session interview + 2 pre-implementation spikes).

## v1.4.1 Requirements

Requirements for milestone v1.4.1: Task Property Surface & Subtree Retrieval. Strictly additive point release (same shape as v1.3.1/.2/.3). Projects stay read-only — writes deferred to v1.5.

### Writable Task Properties

- [x] **PROP-01**: `add_tasks` accepts `completesWithChildren: bool` with `Patch[bool]` semantics (omit = no change, value = set, null rejected)
- [x] **PROP-02**: `edit_tasks` accepts `completesWithChildren: bool` with same patch semantics
- [x] **PROP-03**: `add_tasks` accepts `type` with `Patch[TaskType]` where `TaskType = "parallel" | "sequential"` — null rejected (enums have no cleared state); `"singleActions"` rejected naturally via TaskType enum validation (generic schema error, no custom messaging)
- [x] **PROP-04**: `edit_tasks` accepts `type` with same constraints as PROP-03 (null rejected, `"singleActions"` rejected at type level)
- [x] **PROP-05**: When agent omits `completesWithChildren` on `add_tasks`, server writes the user's `OFMCompleteWhenLastItemComplete` preference explicitly (factory default fallback: `true`) — server never relies on OmniFocus's implicit defaulting
- [x] **PROP-06**: When agent omits `type` on `add_tasks`, server writes the user's `OFMTaskDefaultSequential` preference explicitly (factory default fallback: `"parallel"`)
- [x] **PROP-07**: **Writes** to `completesWithChildren` and `type` on projects are rejected in v1.4.1 (project writes deferred to v1.5, consistent with existing write surface). Read path for projects covered by HIER-02.
- [x] **PROP-08**: `completesWithChildren` added to `NEVER_STRIP` so `false` values survive the default stripping pipeline

### Read-only Derived Presence Flags (default response)

- [x] **FLAG-01**: Default response on **tasks and projects** includes `hasNote: true` when the note field is non-empty; stripped when false
- [x] **FLAG-02**: Default response on **tasks and projects** includes `hasRepetition: true` when a repetition rule exists; stripped when false
- [x] **FLAG-03**: Default response on **tasks and projects** includes `hasAttachments: true` when the attachments array is non-empty; stripped when false
- [x] **FLAG-04**: Default response on **tasks and projects** includes `isSequential: true` when `type == "sequential"`; stripped when false. On tasks the semantic is about the next-in-line subtask; on projects it's about the next-in-line child task within the project. `dependsOnChildren` (FLAG-05) stays tasks-only — projects are always containers. (Phase 56-08 hoisted the field from `Task` to `ActionableEntity` to close Human UAT gap G1.)
- [x] **FLAG-05**: Task default response includes `dependsOnChildren: true` when `hasChildren AND NOT completesWithChildren`; stripped when false (**tasks-only** — projects have no parent-completion notion)
- [x] **FLAG-06**: `dependsOnChildren` and `isSequential` emit independent of include groups — they appear on default response even when `hierarchy` is also requested (default and include pipelines are independent; includes are additive)
- [x] **FLAG-07**: Tool descriptions (`list_tasks`, `get_task`, `list_projects`) surface behavioral meaning of `dependsOnChildren` (real task waiting on children, not a container) and `isSequential` (only next-in-line child is available) so agents reason correctly about actionability
- [x] **FLAG-08**: Derived read-only flags (`hasNote`, `hasRepetition`, `hasAttachments`, `hasChildren`, `dependsOnChildren`, `isSequential`) are rejected by Pydantic `extra="forbid"` when passed on `add_tasks` / `edit_tasks` — generic schema error (no custom educational messaging; JSON Schema already tells agents which fields are writable)

### Expanded `hierarchy` Include Group

- [x] **HIER-01**: When `hierarchy` include group requested on tasks, response includes `hasChildren` (strip-when-false), `type` (full enum, always), `completesWithChildren` (bool, always)
- [x] **HIER-02**: When `hierarchy` include group requested on projects, response includes the same three fields; `type` values include `"singleActions"`
- [x] **HIER-03**: `hasChildren` name preserved (not renamed to `hasSubtasks`) — rename would ripple to projects where "subtasks" doesn't apply
- [x] **HIER-04**: No-suppression invariant — when `hierarchy` is requested, all three fields emit per their strip rules even when a default-response derived flag (`dependsOnChildren`, `isSequential`) already conveys overlapping signal. Redundant emission between the default and hierarchy pipelines is intentional (low-cost redundancy, high-value predictability) — must not be de-duplicated
- [x] **HIER-05**: `ProjectType` value constructed at the service layer from the `(sequential, containsSingletonActions)` tuple — `"singleActions"` takes precedence over the `sequential` flag when both are set on a project

### `parent` Filter on `list_tasks`

- [x] **PARENT-01**: `list_tasks` accepts a `parent` filter with single reference — name (case-insensitive substring) or ID
- [x] **PARENT-02**: `parent` filter resolves via the same three-step resolver as every other entity reference (`$` prefix → exact ID → name substring)
- [x] **PARENT-03**: `parent` filter returns all descendants of the resolved reference at any depth. When the resolved entity is a project, descendant semantics match the existing `project` filter (all tasks within the project at any depth)
- [x] **PARENT-04**: ~~Resolved task is included as anchor in result set; projects produce no anchor (projects are not rows in `list_tasks`)~~ **REVISED (Phase 57 UAT / G1):** Resolved task is included as anchor in result set **and preserved unconditionally — the anchor is NOT subject to AND-composition with subtree-pruning filters (it bypasses the pruning predicates)**. Projects produce no anchor (projects are not rows in `list_tasks`). Implemented via repo-layer `pinned_task_ids` primitive on `ListTasksRepoQuery` (Option A). Honors the promise in `FILTERED_SUBTREE_WARNING`'s text ("resolved parent tasks are always included").
- [x] **PARENT-05**: ~~`parent` filter AND-composes with all other filters (project, tags, dates, etc.) — no special precedence~~ **REVISED (Phase 57 UAT / G1):** `parent` filter's **non-anchor descendants** AND-compose with all other filters (project, tags, dates, etc.) — no special precedence among them. The resolved task **anchor** is the sole exception: preserved unconditionally per PARENT-04 (anchor bypass at the repo layer via `pinned_task_ids` OR-clause, not a precedence rule among AND-composed filters).
- [x] **PARENT-06**: Standard pagination (limit + cursor) applies over the flat result set; outline order preserved
- [x] **PARENT-07**: `parent: "$inbox"` is accepted and produces identical result to `project: "$inbox"` (both surface inbox tasks)
- [x] **PARENT-08**: Same contradiction rules as `project: "$inbox"` apply to `parent: "$inbox"` (e.g., `parent: "$inbox"` + `inInbox=false` → error)
- [x] **PARENT-09**: Array of references on `parent` is rejected at validation time — single reference only (multi-entity matching handled via substring semantics)

### Filter Unification Architecture

- [x] **UNIFY-01**: `project` and `parent` filters share the same core mechanism — two surface filters, one shared function, differing only by accepted entity-type-set (`project` accepts projects only; `parent` accepts projects AND tasks)
- [x] **UNIFY-02**: Same entity resolved via either filter produces identical results
- [x] **UNIFY-03**: Conditional anchor injection — task-as-anchor if resolved entity is a task; no anchor if it's a project
- [x] **UNIFY-04**: ~~Filter logic lives at repo layer~~ **Scope-expansion logic lives at service layer; primitive filter application (set-membership) stays at repo** (Python-filter benchmark confirmed p95 ≤ 1.30 ms at 10K rows — 77× under threshold). *Why: interview intent ("ONE shared mechanism", anchor injection "inside the shared function") + matches existing `<noun>Filter` → primitive pattern (model-taxonomy.md §131-133) + maintainability rule (single code path across all scope filters). See Phase 57 CONTEXT D-04.*
- [x] **UNIFY-05**: ~~`collect_subtree(parent_id, snapshot) -> list[Task]` extracted as shared helper used by both `HybridRepository` and `BridgeOnlyRepository`~~ **Shared `get_tasks_subtree(ref_id, snapshot, accept_entity_types) -> set[str]` helper at service layer; used by both `_resolve_project()` and `_resolve_parent()` pipeline steps. Repos consume only the resolved `task_id_scope` primitive.** *Why: helper follows UNIFY-04 to service layer; signature gains `accept_entity_types` so the same function serves both filters; returns ID set (not Task list) because repos filter by membership. See Phase 57 CONTEXT D-02.*
- [x] **UNIFY-06**: ~~`ListTasksRepoQuery` gains `parent_ids: list[str] | None` field~~ ~~`ListTasksRepoQuery` gains `task_id_scope: list[str] | None` unified scope primitive; existing `project_ids: list[str] | None` field is retired. Both `project` and `parent` surface filters route through the unified primitive.~~ **REVISED (Phase 57 UAT / G1+G2):** `ListTasksRepoQuery` has two disjoint task-ID primitives: **`candidate_task_ids: list[str] | None`** (filterable pool — set-membership narrowed by all other predicates) and **`pinned_task_ids: list[str] | None`** (unconditionally included — bypass all predicates; used for parent-filter anchor preservation per PARENT-04). The old `task_id_scope` name is renamed; the old `project_ids` field stays retired. Repo-level WHERE: `(t.id IN pinned_task_ids) OR (t.id IN candidate_task_ids AND <other predicates>)`. Both `project` and `parent` still route through `candidate_task_ids`; only `parent`'s resolved task anchors populate `pinned_task_ids`. *Why: field name `scope` was abstract; `candidate` communicates the repo-level semantic (filterable candidates) clearly. `pinned_task_ids` keeps the "anchor" concept at the service layer — the repo sees only "always include these" without a `parent`-specific coupling. See Phase 57 UAT G1 and 57-04 plan.*
- [x] **UNIFY-07** *(new, Phase 57 UAT / G3 — supersedes Phase 35.2 D-02e)*: Name-resolver filters (`project`, `parent`, `tags`) that resolve to **zero matches** return an **empty result set** + `FILTER_NO_MATCH` warning (optionally extended with "did you mean: X, Y, Z" suggestions when close matches exist via the fuzzy-suggest cascade). Applies uniformly across all three filters. Did-you-mean pedagogical hints are **preserved**; the historical "skip filter + return all tasks" fallback is **removed**. *Why: Phase 35.2 DISCUSSION-LOG bundled two UX choices ("did-you-mean" and "skip+return-all fallback") into one option; Flo's intent was only did-you-mean. Live UAT probes against disjoint scopes exposed the fallback as agent-confusing (e.g., `list_tasks(project="Nonexistent")` returning 1624 items made agents build wrong mental models of result cardinality).*
- [x] **UNIFY-08** *(new, Phase 57 UAT / G2)*: **Empty `candidate_task_ids`** (from either disjoint `project ∩ parent` intersection OR single-scope resolving to zero tasks, e.g., an empty project) short-circuits to an empty result set at the **service layer** — neither `HybridRepository` nor `BridgeOnlyRepository` sees an empty list. Cross-path equivalence (UNIFY-02) restored by construction rather than by patching individual repo guards. *Why: previous hybrid behavior `len > 0` guard silently skipped the filter on empty list (returning all tasks); bridge_only correctly returned 0. Live repro: `list_tasks(project="Migrate...", parent="Build...")` with disjoint scopes returned 1624 items. Fix: one service-layer rule, both repos uniformly correct.*

### OmniFocusPreferences Extension

- [x] **PREFS-01**: `bridge/bridge.js:handleGetSettings()` returns `OFMCompleteWhenLastItemComplete` and `OFMTaskDefaultSequential` alongside existing date preferences
- [x] **PREFS-02**: `service/preferences.py` extended to surface the two new keys via `OmniFocusPreferences` with the same lazy-load-once pattern used for date preferences
- [x] **PREFS-03**: Absence semantics — when a setting is not materialized in the OF Setting store (user kept factory default), service resolves to documented OF factory default and writes that explicitly on `add_tasks`. Applies symmetrically to both keys
- [x] **PREFS-04**: Settings cached for server process lifetime (same staleness model as date preferences — reconfigurations picked up on next server start)
- [x] **PREFS-05**: Works uniformly under both `HybridRepository` and `BridgeOnlyRepository` — no plistlib dependency in the service layer

### SQLite Cache Read Path

- [x] **CACHE-01**: `completesWithChildren` read path covers both repos — `HybridRepository` via `Task.completeWhenChildrenComplete` (INTEGER 0/1) on tasks and projects (via project's `Task` row); `BridgeOnlyRepository` via OmniJS `task.completedByChildren` / `project.completedByChildren` during the existing snapshot enumeration. No per-row bridge fallback in either path
- [x] **CACHE-02**: `type` parallel/sequential read path covers both repos — `HybridRepository` via `Task.sequential` (INTEGER 0/1) on tasks and projects; `BridgeOnlyRepository` via OmniJS `task.sequential` / `project.sequential` during the existing snapshot enumeration
- [x] **CACHE-03**: `type` `"singleActions"` on projects reads from `ProjectInfo.containsSingletonActions` (INTEGER 0/1) in `HybridRepository`; `BridgeOnlyRepository` reads the equivalent OmniJS project property during snapshot enumeration. Enum assembly per HIER-05 lives at the service layer
- [x] **CACHE-04**: `hasAttachments` emission is amortized O(1) per row — `HybridRepository` loads presence set once per snapshot via single `SELECT task FROM Attachment` query; `BridgeOnlyRepository` inline per-task `attachments.length` read during the existing OmniJS enumeration (~360 ms measured for 3427 tasks + 385 projects)

### Warnings

- [x] **WARN-01**: ~~Filtered-subtree warning fires when `project` or `parent` filter combined with any other filter; uses locked verbatim text (see MILESTONE-v1.4.1.md)~~ **REVISED (Phase 57 UAT / G4 + completed/dropped reclassification):** Filtered-subtree warning fires when `project` or `parent` filter is combined with any **subtree-pruning filter** — a task-attribute predicate that can exclude intermediate/descendant tasks from the scope's result set. Pruning filters: `flagged`, `in_inbox`, `tags`, `estimated_minutes_max`, `search`, `due`, `defer`, `planned`, `added`, `modified`, and `availability` **when set to a non-default value** (default `['remaining']` does NOT fire — preserves D-13's "don't spam on default"). Non-pruning filters that do NOT fire: `completed`, `dropped` (inclusion filters — they ADD lifecycle states to the result, never prune), pagination, and output-shape fields. Text is locked verbatim (see MILESTONE-v1.4.1.md line 180, currently uses ASCII `--` after intentional ruff cleanup; spec and code aligned per UAT Test 1).
- [x] **WARN-02**: parent-resolves-to-project warning fires when all matches from `parent` are projects (not mixed) — soft "consider using `project`" hint
- [x] **WARN-03**: parent+project combined warning fires when both filters specified (soft hint, rare combination)
- [x] **WARN-04**: Warnings live in the domain layer (filter-semantics advice), not projection (field formatting/stripping)
- [x] **WARN-05**: Existing `multi-match` and `inbox-name-substring` warnings trigger on `parent` filter resolution, reusing the same warning infrastructure used by other substring-resolving filters (no new warning code paths for the existing cases)
- [x] **WARN-06** *(new, Phase 57 UAT / G2)*: `EMPTY_SCOPE_INTERSECTION_WARNING` fires when **both** `project` and `parent` filters are set **AND** their scope-set intersection is empty (zero tasks in both scopes simultaneously). Pedagogical hint explaining why the result is empty. Distinct from `PARENT_PROJECT_COMBINED_WARNING` (WARN-03, presence-based — fires whenever both filters are set regardless of intersection cardinality): this warning is **emptiness-based** and specifically tells the agent that the two scopes don't overlap. Fires alongside WARN-03 in the disjoint-scope case.

### Incidental Cleanup

- [x] **STRIP-11**: Remove `availability` from `NEVER_STRIP` — defensive code with no actual purpose (carry-over todo, tagged v1.4.1)

### Golden Master (Project-Rule Compliance)

- [x] **GOLD-01**: Phase 56's new bridge-visible task property surface (`completesWithChildren`, `type` including `"singleActions"`, `hasAttachments`, plus edit round-trip) is covered by canonical golden-master scaffolding in `tests/golden_master/snapshots/09-task-property-surface/` — 8 committed fixtures capturing both repos' behavior against the new fields, 56-07 wrong-pattern artifacts fully removed, capture harness extended with 8 scenarios + `_phase_2b_phase56_setup()` helper in `uat/capture_golden_master.py`. Satisfies the project-wide GOLD-01 rule (PROJECT.md:186) for v1.4.1: any phase modifying bridge operations re-captures the golden master and adds contract test coverage. *(Added 2026-04-24 during milestone audit — missing from initial REQUIREMENTS.md enrollment despite being claimed by 56-09-SUMMARY.)*

## Traceability

Every v1.4.1 requirement maps to exactly one phase. Coverage: **55/55 ✓** (51 original + 3 added during Phase 57 UAT gap-closure: UNIFY-07, UNIFY-08, WARN-06; + 1 added during milestone audit: GOLD-01).

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROP-01 | Phase 56 | Satisfied |
| PROP-02 | Phase 56 | Satisfied |
| PROP-03 | Phase 56 | Satisfied |
| PROP-04 | Phase 56 | Satisfied |
| PROP-05 | Phase 56 | Satisfied |
| PROP-06 | Phase 56 | Satisfied |
| PROP-07 | Phase 56 | Satisfied |
| PROP-08 | Phase 56 | Satisfied |
| FLAG-01 | Phase 56 | Satisfied |
| FLAG-02 | Phase 56 | Satisfied |
| FLAG-03 | Phase 56 | Satisfied |
| FLAG-04 | Phase 56 | Satisfied |
| FLAG-05 | Phase 56 | Satisfied |
| FLAG-06 | Phase 56 | Satisfied |
| FLAG-07 | Phase 56 | Satisfied |
| FLAG-08 | Phase 56 | Satisfied |
| HIER-01 | Phase 56 | Satisfied |
| HIER-02 | Phase 56 | Satisfied |
| HIER-03 | Phase 56 | Satisfied |
| HIER-04 | Phase 56 | Satisfied |
| HIER-05 | Phase 56 | Satisfied |
| PARENT-01 | Phase 57 | Satisfied |
| PARENT-02 | Phase 57 | Satisfied |
| PARENT-03 | Phase 57 | Satisfied |
| PARENT-04 | Phase 57 | Satisfied |
| PARENT-05 | Phase 57 | Satisfied |
| PARENT-06 | Phase 57 | Satisfied |
| PARENT-07 | Phase 57 | Satisfied |
| PARENT-08 | Phase 57 | Satisfied |
| PARENT-09 | Phase 57 | Satisfied |
| UNIFY-01 | Phase 57 | Satisfied |
| UNIFY-02 | Phase 57 | Satisfied |
| UNIFY-03 | Phase 57 | Satisfied |
| UNIFY-04 | Phase 57 | Satisfied |
| UNIFY-05 | Phase 57 | Satisfied |
| UNIFY-06 | Phase 57 | Satisfied |
| UNIFY-07 | Phase 57 | Satisfied *(added 2026-04-24 from Phase 57 UAT / G3)* |
| UNIFY-08 | Phase 57 | Satisfied *(added 2026-04-24 from Phase 57 UAT / G2)* |
| PREFS-01 | Phase 56 | Satisfied |
| PREFS-02 | Phase 56 | Satisfied |
| PREFS-03 | Phase 56 | Satisfied |
| PREFS-04 | Phase 56 | Satisfied |
| PREFS-05 | Phase 56 | Satisfied |
| CACHE-01 | Phase 56 | Satisfied |
| CACHE-02 | Phase 56 | Satisfied |
| CACHE-03 | Phase 56 | Satisfied |
| CACHE-04 | Phase 56 | Satisfied |
| WARN-01 | Phase 57 | Satisfied |
| WARN-02 | Phase 57 | Satisfied |
| WARN-03 | Phase 57 | Satisfied |
| WARN-04 | Phase 57 | Satisfied |
| WARN-05 | Phase 57 | Satisfied |
| WARN-06 | Phase 57 | Satisfied *(added 2026-04-24 from Phase 57 UAT / G2)* |
| STRIP-11 | Phase 56 | Satisfied |
| GOLD-01 | Phase 56 | Satisfied *(added 2026-04-24 during milestone audit — project-rule compliance per PROJECT.md:186)* |

**Coverage by phase:**

- Phase 56 (Task Property Surface): 32 REQs — PREFS-01..05, CACHE-01..04, FLAG-01..08, HIER-01..05, PROP-01..08, STRIP-11, GOLD-01
- Phase 57 (Parent Filter & Filter Unification): 23 REQs — PARENT-01..09, UNIFY-01..08, WARN-01..06

## Future Requirements

Deferred but captured:

- Array of references on `parent` filter — future extension if real agent pain emerges
- Cache-direct plist decode for settings — optimization if bridge startup cost becomes meaningful
- SQL push-down for `parent` filter in `HybridRepository` — opportunistic optimization (recursive-CTE prototype exists at `.research/deep-dives/v1.4.1-filter-benchmark/experiments/sql_parent_filter.py`)
- Snapshot cold-path optimization (projection / lazy deserialization) — only if live-DB cold path becomes a concern (currently 50 ms at 3,426 rows)

## Out of Scope

- **Project writes for `completesWithChildren` / `type`** — deferred to v1.5 (consistent with existing write surface; project writes are their own milestone)
- **Array of references on `parent`** — single reference only; substring matching handles multi-entity cases when matches share a substring
- **Cache-direct settings access** — rejected in favor of architectural consistency (one settings pattern, no plistlib in service layer, uniform across repos)
- **Custom educational errors for derived read-only fields** — JSON Schema tells agents which fields are writable; Pydantic `extra="forbid"` generic error is sufficient
- **`hasChildren` rename to `hasSubtasks`** — rename would ripple to projects where "subtasks" doesn't apply
- **Auto-expand children in search results** — bloats every query; confuses "find a task" intent
- **Mitigate bloat with warnings** — cognitive overhead without solving the underlying problem

---

*Last updated: 2026-04-19 — Traceability revised after 2-phase roadmap reshape. 51/51 REQs mapped across Phases 56-57 (was Phases 56-59 in prior draft).*
