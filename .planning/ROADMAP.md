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
- 🚧 **v1.4.1 Task Property Surface & Subtree Retrieval** — Phases 56-57
- 📋 **v1.5 UI & Perspectives** — Planned
- 📋 **v1.6 Production Hardening** — Planned
- 📋 **v1.7 Project Writes** — Planned

## Phases

### 🚧 v1.4.1 Task Property Surface & Subtree Retrieval (In progress)

- [ ] **Phase 56: Task Property Surface** — Preferences, cache reads, presence flags, expanded `hierarchy` group, writable `completesWithChildren` + `type` with preference-driven create-defaults, strip-rules cleanup
- [ ] **Phase 57: Parent Filter & Filter Unification** — `parent` filter on `list_tasks`, shared `collect_subtree` helper, warnings

### 📋 v1.5 UI & Perspectives (Planned)

- [ ] Phase 58: Perspective Tools — `show_perspective`, `get_current_perspective`, `open_task` deep links

### 📋 v1.6 Production Hardening (Planned)

- [ ] Phase 59: Retry & Recovery — retry logic for bridge timeouts, crash recovery with persistent state, serial execution guarantee

### 📋 v1.7 Project Writes (Planned)

- [ ] Phase 60: Project Write Tools — `add_projects`, `edit_projects`

## Phase Details

### Phase 56: Task Property Surface

**Goal**: Agents can read and write the new task property surface (`completesWithChildren`, per-type `type`, presence flags, expanded `hierarchy` include group) end-to-end — reads served by the SQLite cache on `HybridRepository` and amortized snapshot enumeration on `BridgeOnlyRepository` with no per-row bridge fallback; writes honor `Patch[bool]` / `Patch[TaskType]` semantics on tasks, and omitted create-values resolve to the user's explicit OmniFocus preference (never OF's implicit defaulting). Projects remain read-only for the new writable fields (project writes deferred to v1.7).

**Depends on**: Nothing (v1.4 shipped)

**Requirements**: PREFS-01, PREFS-02, PREFS-03, PREFS-04, PREFS-05, CACHE-01, CACHE-02, CACHE-03, CACHE-04, FLAG-01, FLAG-02, FLAG-03, FLAG-04, FLAG-05, FLAG-06, FLAG-07, FLAG-08, HIER-01, HIER-02, HIER-03, HIER-04, HIER-05, PROP-01, PROP-02, PROP-03, PROP-04, PROP-05, PROP-06, PROP-07, PROP-08, STRIP-11

**Success Criteria** (what must be TRUE):
  1. Both repositories return identical values for `completesWithChildren`, `type`, and `hasAttachments` on tasks and projects via the SQLite cache (`HybridRepository`: `Task.completeWhenChildrenComplete`, `Task.sequential`, `ProjectInfo.containsSingletonActions`, batched `SELECT task FROM Attachment` once per snapshot) and amortized OmniJS enumeration (`BridgeOnlyRepository`: inline `completedByChildren`/`sequential`/`attachments.length` during the existing snapshot-build script) — cross-path equivalence proven, no per-row bridge fallback on either path
  2. `OmniFocusPreferences` surfaces `OFMCompleteWhenLastItemComplete` and `OFMTaskDefaultSequential` via the existing bridge-based lazy-load-once pattern (extended `bridge/bridge.js:handleGetSettings()` + extended `service/preferences.py`) — absence = user kept OF factory default (valid signal, not an error), service resolves to `true` / `"parallel"` respectively, works uniformly under both repos with no plistlib in the service layer, no new settings-access code path
  3. Default task response emits `hasNote`, `hasRepetition`, `hasAttachments`, `isSequential` (tasks-only, `type == "sequential"`), and `dependsOnChildren` (tasks-only, `hasChildren AND NOT completesWithChildren`) — all strip-when-false; default project response emits `hasNote`, `hasRepetition`, `hasAttachments`; `hierarchy` include group adds `hasChildren` (strip-when-false), `type` (full enum always — `ProjectType` constructed at the service layer from `(sequential, containsSingletonActions)` with `"singleActions"` taking precedence), and `completesWithChildren` (always; added to `NEVER_STRIP` so `false` survives)
  4. No-suppression invariant holds — when `hierarchy` is requested, all three fields still emit per their strip rules even when a default-response derived flag (`dependsOnChildren`, `isSequential`) already conveys overlapping signal; default and include pipelines remain independent (proven by contract test that requests both and verifies the intentional redundant emission); `hasChildren` name preserved (not renamed to `hasSubtasks`); tool descriptions on `list_tasks`/`get_task`/`list_projects` surface the behavioral meaning of `dependsOnChildren` (real task waiting on children) and `isSequential` (only next-in-line child is available)
  5. `add_tasks` and `edit_tasks` accept `completesWithChildren` (`Patch[bool]`) and `type` (`Patch[TaskType]` where `TaskType = "parallel" | "sequential"`) on tasks with null rejected and `"singleActions"` rejected naturally via enum validation; when omitted on `add_tasks`, the service writes the resolved preference value explicitly (factory default `true` / `"parallel"` when the OF Setting store has no value) — server never relies on OmniFocus's implicit defaulting; writes to these fields on projects are rejected at the tool surface (project writes deferred to v1.7)
  6. Derived read-only flags (`hasNote`, `hasRepetition`, `hasAttachments`, `hasChildren`, `dependsOnChildren`, `isSequential`) are rejected by Pydantic `extra="forbid"` on `add_tasks`/`edit_tasks` (generic schema error, no custom messaging); `availability` removed from `NEVER_STRIP` as pre-existing defensive entry with no actual purpose
  7. Round-trip test on both `HybridRepository` and `BridgeOnlyRepository`: creating a task with `completesWithChildren` / `type` set, reading back via `get_task` and `list_tasks`, editing to flip each value, and verifying the expected cache-backed values — plus create-default paths (omit both fields, read back) verified end-to-end against a captured golden master

**Plans**: TBD

**Plan waves** (guidance for `/gsd-plan-phase 56`, not a hard split): given the phase breadth, consider decomposing internally as (1) preferences + cache foundation — bridge/settings extension, `OmniFocusPreferences` extension, cache read paths, cross-path equivalence; (2) read surface — default-response flags, expanded `hierarchy` group, `ProjectType` assembly, strip-rules cleanup (`NEVER_STRIP` additions + `availability` removal), `extra="forbid"` rejection of derived fields; (3) write surface — `Patch[bool]` / `Patch[TaskType]` on tasks, create-default resolution via preferences, project-write rejection, round-trip verification against golden master.

### Phase 57: Parent Filter & Filter Unification

**Goal**: Agents can fetch a task's full descendant subtree through `list_tasks` with a single call using the new `parent` filter — sharing the same resolver and filter pipeline as `project` at the repo layer, with the full warning surface guiding correct usage.

**Depends on**: Phase 56 (stable cache read path for the children structure)

**Requirements**: PARENT-01, PARENT-02, PARENT-03, PARENT-04, PARENT-05, PARENT-06, PARENT-07, PARENT-08, PARENT-09, UNIFY-01, UNIFY-02, UNIFY-03, UNIFY-04, UNIFY-05, UNIFY-06, WARN-01, WARN-02, WARN-03, WARN-04, WARN-05

**Success Criteria** (what must be TRUE):
  1. `list_tasks` accepts a single `parent` reference (name substring or ID) resolved via the standard three-step resolver (`$` prefix → exact ID → name substring); array references rejected at validation time; `parent: "$inbox"` is accepted and produces the identical result set to `project: "$inbox"` with the same contradiction rules (e.g., `parent: "$inbox"` + `inInbox=false` → error)
  2. The `parent` filter returns all descendants of the resolved reference at any depth, AND-composes with every other filter (project, tags, dates, etc.) with no special precedence, preserves outline order, and paginates via the existing limit + cursor mechanism; resolved task is included as anchor; resolved project produces no anchor (projects are not rows in `list_tasks`)
  3. `project` and `parent` filters share one underlying mechanism — `collect_subtree(parent_id, snapshot) -> list[Task]` shared helper used by both `HybridRepository` and `BridgeOnlyRepository`, `ListTasksRepoQuery.parent_ids: list[str] | None` as the wire-level input, conditional anchor injection at the repo layer; same entity resolved via either filter produces byte-identical results (proven by cross-filter equivalence test)
  4. Filter logic lives at the repo layer (Python-filter benchmark locked p95 ≤ 1.30 ms at 10K — 77× under the viable threshold); contract unchanged whether `HybridRepository` later pushes the filter down to SQL opportunistically
  5. Five warnings surface correctly: new filtered-subtree warning (locked verbatim text) fires when `project` or `parent` is combined with any other filter; new `parent` + `project` combined warning fires when both are specified; new parent-resolves-to-project warning fires when all matches are projects; existing multi-match and inbox-name-substring warnings trigger on `parent` resolution via the same infrastructure used by other substring-resolving filters; all warnings live in the domain layer (filter-semantics advice), not projection

**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 56. Task Property Surface | v1.4.1 | 0/? | Not started | — |
| 57. Parent Filter & Filter Unification | v1.4.1 | 0/? | Not started | — |
| 58. Perspective Tools | v1.5 | 0/? | Not started | — |
| 59. Retry & Recovery | v1.6 | 0/? | Not started | — |
| 60. Project Write Tools | v1.7 | 0/? | Not started | — |
