# Requirements: OmniFocus Operator

**Defined:** 2026-04-19
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents — executive function infrastructure that works at 7:30am.

Full design spec: `.research/updated-spec/MILESTONE-v1.4.1.md` (design locked after 4-session interview + 2 pre-implementation spikes).

## v1.4.1 Requirements

Requirements for milestone v1.4.1: Task Property Surface & Subtree Retrieval. Strictly additive point release (same shape as v1.3.1/.2/.3). Projects stay read-only — writes deferred to v1.7.

### Writable Task Properties

- [ ] **PROP-01**: `add_tasks` accepts `completesWithChildren: bool` with `Patch[bool]` semantics (omit = no change, value = set, null rejected)
- [ ] **PROP-02**: `edit_tasks` accepts `completesWithChildren: bool` with same patch semantics
- [ ] **PROP-03**: `add_tasks` accepts `type` with `Patch[TaskType]` where `TaskType = "parallel" | "sequential"` — null rejected (enums have no cleared state); `"singleActions"` rejected naturally via TaskType enum validation (generic schema error, no custom messaging)
- [ ] **PROP-04**: `edit_tasks` accepts `type` with same constraints as PROP-03 (null rejected, `"singleActions"` rejected at type level)
- [ ] **PROP-05**: When agent omits `completesWithChildren` on `add_tasks`, server writes the user's `OFMCompleteWhenLastItemComplete` preference explicitly (factory default fallback: `true`) — server never relies on OmniFocus's implicit defaulting
- [ ] **PROP-06**: When agent omits `type` on `add_tasks`, server writes the user's `OFMTaskDefaultSequential` preference explicitly (factory default fallback: `"parallel"`)
- [ ] **PROP-07**: **Writes** to `completesWithChildren` and `type` on projects are rejected in v1.4.1 (project writes deferred to v1.7, consistent with existing write surface). Read path for projects covered by HIER-02.
- [ ] **PROP-08**: `completesWithChildren` added to `NEVER_STRIP` so `false` values survive the default stripping pipeline

### Read-only Derived Presence Flags (default response)

- [ ] **FLAG-01**: Default response on **tasks and projects** includes `hasNote: true` when the note field is non-empty; stripped when false
- [ ] **FLAG-02**: Default response on **tasks and projects** includes `hasRepetition: true` when a repetition rule exists; stripped when false
- [ ] **FLAG-03**: Default response on **tasks and projects** includes `hasAttachments: true` when the attachments array is non-empty; stripped when false
- [ ] **FLAG-04**: Task default response includes `isSequential: true` when `type == "sequential"`; stripped when false (**tasks-only** — projects use full `type` enum via `hierarchy` include)
- [ ] **FLAG-05**: Task default response includes `dependsOnChildren: true` when `hasChildren AND NOT completesWithChildren`; stripped when false (**tasks-only** — projects have no parent-completion notion)
- [ ] **FLAG-06**: `dependsOnChildren` and `isSequential` emit independent of include groups — they appear on default response even when `hierarchy` is also requested (default and include pipelines are independent; includes are additive)
- [ ] **FLAG-07**: Tool descriptions (`list_tasks`, `get_task`, `list_projects`) surface behavioral meaning of `dependsOnChildren` (real task waiting on children, not a container) and `isSequential` (only next-in-line child is available) so agents reason correctly about actionability
- [ ] **FLAG-08**: Derived read-only flags (`hasNote`, `hasRepetition`, `hasAttachments`, `hasChildren`, `dependsOnChildren`, `isSequential`) are rejected by Pydantic `extra="forbid"` when passed on `add_tasks` / `edit_tasks` — generic schema error (no custom educational messaging; JSON Schema already tells agents which fields are writable)

### Expanded `hierarchy` Include Group

- [ ] **HIER-01**: When `hierarchy` include group requested on tasks, response includes `hasChildren` (strip-when-false), `type` (full enum, always), `completesWithChildren` (bool, always)
- [ ] **HIER-02**: When `hierarchy` include group requested on projects, response includes the same three fields; `type` values include `"singleActions"`
- [ ] **HIER-03**: `hasChildren` name preserved (not renamed to `hasSubtasks`) — rename would ripple to projects where "subtasks" doesn't apply
- [ ] **HIER-04**: No-suppression invariant — when `hierarchy` is requested, all three fields emit per their strip rules even when a default-response derived flag (`dependsOnChildren`, `isSequential`) already conveys overlapping signal. Redundant emission between the default and hierarchy pipelines is intentional (low-cost redundancy, high-value predictability) — must not be de-duplicated
- [ ] **HIER-05**: `ProjectType` value constructed at the service layer from the `(sequential, containsSingletonActions)` tuple — `"singleActions"` takes precedence over the `sequential` flag when both are set on a project

### `parent` Filter on `list_tasks`

- [ ] **PARENT-01**: `list_tasks` accepts a `parent` filter with single reference — name (case-insensitive substring) or ID
- [ ] **PARENT-02**: `parent` filter resolves via the same three-step resolver as every other entity reference (`$` prefix → exact ID → name substring)
- [ ] **PARENT-03**: `parent` filter returns all descendants of the resolved reference at any depth. When the resolved entity is a project, descendant semantics match the existing `project` filter (all tasks within the project at any depth)
- [ ] **PARENT-04**: Resolved task is included as anchor in result set; projects produce no anchor (projects are not rows in `list_tasks`)
- [ ] **PARENT-05**: `parent` filter AND-composes with all other filters (project, tags, dates, etc.) — no special precedence
- [ ] **PARENT-06**: Standard pagination (limit + cursor) applies over the flat result set; outline order preserved
- [ ] **PARENT-07**: `parent: "$inbox"` is accepted and produces identical result to `project: "$inbox"` (both surface inbox tasks)
- [ ] **PARENT-08**: Same contradiction rules as `project: "$inbox"` apply to `parent: "$inbox"` (e.g., `parent: "$inbox"` + `inInbox=false` → error)
- [ ] **PARENT-09**: Array of references on `parent` is rejected at validation time — single reference only (multi-entity matching handled via substring semantics)

### Filter Unification Architecture

- [ ] **UNIFY-01**: `project` and `parent` filters share the same core mechanism — two surface filters, one shared function, differing only by accepted entity-type-set (`project` accepts projects only; `parent` accepts projects AND tasks)
- [ ] **UNIFY-02**: Same entity resolved via either filter produces identical results
- [ ] **UNIFY-03**: Conditional anchor injection — task-as-anchor if resolved entity is a task; no anchor if it's a project
- [ ] **UNIFY-04**: Filter logic lives at repo layer (Python-filter benchmark confirmed p95 ≤ 1.30 ms at 10K rows — 77× under the 100 ms viable threshold)
- [ ] **UNIFY-05**: `collect_subtree(parent_id, snapshot) -> list[Task]` extracted as shared helper used by both `HybridRepository` and `BridgeOnlyRepository`
- [ ] **UNIFY-06**: `ListTasksRepoQuery` gains `parent_ids: list[str] | None` field

### OmniFocusPreferences Extension

- [ ] **PREFS-01**: `bridge/bridge.js:handleGetSettings()` returns `OFMCompleteWhenLastItemComplete` and `OFMTaskDefaultSequential` alongside existing date preferences
- [ ] **PREFS-02**: `service/preferences.py` extended to surface the two new keys via `OmniFocusPreferences` with the same lazy-load-once pattern used for date preferences
- [ ] **PREFS-03**: Absence semantics — when a setting is not materialized in the OF Setting store (user kept factory default), service resolves to documented OF factory default and writes that explicitly on `add_tasks`. Applies symmetrically to both keys
- [ ] **PREFS-04**: Settings cached for server process lifetime (same staleness model as date preferences — reconfigurations picked up on next server start)
- [ ] **PREFS-05**: Works uniformly under both `HybridRepository` and `BridgeOnlyRepository` — no plistlib dependency in the service layer

### SQLite Cache Read Path

- [ ] **CACHE-01**: `completesWithChildren` read path covers both repos — `HybridRepository` via `Task.completeWhenChildrenComplete` (INTEGER 0/1) on tasks and projects (via project's `Task` row); `BridgeOnlyRepository` via OmniJS `task.completedByChildren` / `project.completedByChildren` during the existing snapshot enumeration. No per-row bridge fallback in either path
- [ ] **CACHE-02**: `type` parallel/sequential read path covers both repos — `HybridRepository` via `Task.sequential` (INTEGER 0/1) on tasks and projects; `BridgeOnlyRepository` via OmniJS `task.sequential` / `project.sequential` during the existing snapshot enumeration
- [ ] **CACHE-03**: `type` `"singleActions"` on projects reads from `ProjectInfo.containsSingletonActions` (INTEGER 0/1) in `HybridRepository`; `BridgeOnlyRepository` reads the equivalent OmniJS project property during snapshot enumeration. Enum assembly per HIER-05 lives at the service layer
- [ ] **CACHE-04**: `hasAttachments` emission is amortized O(1) per row — `HybridRepository` loads presence set once per snapshot via single `SELECT task FROM Attachment` query; `BridgeOnlyRepository` inline per-task `attachments.length` read during the existing OmniJS enumeration (~360 ms measured for 3427 tasks + 385 projects)

### Warnings

- [ ] **WARN-01**: Filtered-subtree warning fires when `project` or `parent` filter combined with any other filter; uses locked verbatim text (see MILESTONE-v1.4.1.md)
- [ ] **WARN-02**: parent-resolves-to-project warning fires when all matches from `parent` are projects (not mixed) — soft "consider using `project`" hint
- [ ] **WARN-03**: parent+project combined warning fires when both filters specified (soft hint, rare combination)
- [ ] **WARN-04**: Warnings live in the domain layer (filter-semantics advice), not projection (field formatting/stripping)
- [ ] **WARN-05**: Existing `multi-match` and `inbox-name-substring` warnings trigger on `parent` filter resolution, reusing the same warning infrastructure used by other substring-resolving filters (no new warning code paths for the existing cases)

### Incidental Cleanup

- [ ] **STRIP-11**: Remove `availability` from `NEVER_STRIP` — defensive code with no actual purpose (carry-over todo, tagged v1.4.1)

## Traceability

*(Filled by roadmapper — each REQ-ID mapped to exactly one phase.)*

## Future Requirements

Deferred but captured:

- Array of references on `parent` filter — future extension if real agent pain emerges
- Cache-direct plist decode for settings — optimization if bridge startup cost becomes meaningful
- SQL push-down for `parent` filter in `HybridRepository` — opportunistic optimization (recursive-CTE prototype exists at `.research/deep-dives/v1.4.1-filter-benchmark/experiments/sql_parent_filter.py`)
- Snapshot cold-path optimization (projection / lazy deserialization) — only if live-DB cold path becomes a concern (currently 50 ms at 3,426 rows)

## Out of Scope

- **Project writes for `completesWithChildren` / `type`** — deferred to v1.7 (consistent with existing write surface; project writes are their own milestone)
- **Array of references on `parent`** — single reference only; substring matching handles multi-entity cases when matches share a substring
- **Cache-direct settings access** — rejected in favor of architectural consistency (one settings pattern, no plistlib in service layer, uniform across repos)
- **Custom educational errors for derived read-only fields** — JSON Schema tells agents which fields are writable; Pydantic `extra="forbid"` generic error is sufficient
- **`hasChildren` rename to `hasSubtasks`** — rename would ripple to projects where "subtasks" doesn't apply
- **Auto-expand children in search results** — bloats every query; confuses "find a task" intent
- **Mitigate bloat with warnings** — cognitive overhead without solving the underlying problem

---

*Last updated: 2026-04-19 — initial draft for v1.4.1.*
