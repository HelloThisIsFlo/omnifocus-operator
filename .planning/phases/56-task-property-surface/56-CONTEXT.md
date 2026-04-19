# Phase 56: Task Property Surface — Context

**Gathered:** 2026-04-19
**Status:** Ready for planning
**Source:** PRD Express Path — `.research/updated-spec/MILESTONE-v1.4.1.md` (design locked after 4-session interview + 2 pre-implementation spikes)

<domain>
## Phase Boundary

**In scope (31 REQs)** — everything needed to expose the new task property surface end-to-end on the task surface, reads served from cache on both repos:

- Bridge-based preferences extension (PREFS-01..05)
- SQLite cache read paths + BridgeOnly amortized enumeration (CACHE-01..04)
- Default-response derived presence flags, tasks + projects (FLAG-01..08)
- Expanded `hierarchy` include group (HIER-01..05)
- Writable task fields `completesWithChildren` + `type` with create-default resolution (PROP-01..08)
- Incidental cleanup: remove `availability` from `NEVER_STRIP` (STRIP-11)

**Explicitly out of scope (Phase 57)** — `parent` filter, filter unification, new warnings, `collect_subtree` helper. Do NOT start any of PARENT-*, UNIFY-*, WARN-* in this phase.

**Explicitly deferred (v1.7)** — project writes for `completesWithChildren` / `type`. Projects stay read-only for the new writable fields in v1.4.1; writes on projects must be rejected at the tool surface.

**Additive-only** — no breaking changes to existing fields, tools, or contracts. Same shape as v1.3.1/.2/.3 point releases.

</domain>

<decisions>
## Implementation Decisions

> Every item below is **locked** from the milestone spec + spike findings. Planner MUST NOT re-derive these.

### Preferences (bridge path — no plistlib in service layer)

- **PREFS-01**: `src/omnifocus_operator/bridge/bridge.js:handleGetSettings()` returns two new keys alongside existing date preferences:
  - `OFMCompleteWhenLastItemComplete` (user default for `completedByChildren`)
  - `OFMTaskDefaultSequential` (user default for `sequential`)
- **PREFS-02**: `src/omnifocus_operator/service/preferences.py:OmniFocusPreferences` extended with the two new keys using the **existing lazy-load-once pattern** used by date preferences — no new pattern.
- **PREFS-03**: Absence semantics — `OFMTaskDefaultSequential` is typically **absent** from the OF Setting store (OmniFocus only materializes settings when the user changes them from factory default). When the bridge returns no value:
  - `OFMCompleteWhenLastItemComplete` absent → service resolves to `true`
  - `OFMTaskDefaultSequential` absent → service resolves to `"parallel"`
  - Service writes the resolved value **explicitly** on `add_tasks` — server never relies on OmniFocus's implicit defaulting.
- **PREFS-04**: Settings cached for server process lifetime (same staleness model as date preferences). Reconfiguration picks up on next server start.
- **PREFS-05**: Works uniformly under both `HybridRepository` and `BridgeOnlyRepository` via the bridge. **No plistlib dependency in the service layer.** Cache-direct plist decode was explicitly rejected for architectural consistency (future optimization only).

### Cache read paths (HybridRepository — no per-row bridge fallback)

All three fields cache-backed per Spike 1 (60/60 OmniJS cross-check match at 20 sampled task IDs × 3 fields):

- **CACHE-01** `completesWithChildren`:
  - Tasks: `Task.completeWhenChildrenComplete` (INTEGER 0/1)
  - Projects: same column, accessed via `ProjectInfo.task = Task.persistentIdentifier` join (every project is two rows in the OF SQLite schema — generic `Task` row + project metadata in `ProjectInfo`)
- **CACHE-02** `type` parallel/sequential:
  - Tasks: `Task.sequential` (INTEGER 0/1)
  - Projects: `Task.sequential` via the same join
- **CACHE-03** `type == "singleActions"` on projects: `ProjectInfo.containsSingletonActions` (INTEGER 0/1). Enum assembly (HIER-05) lives at the service layer.
- **CACHE-04** `hasAttachments`: **batched snapshot-load** — one `SELECT task FROM Attachment` query per snapshot feeds a Python `set` for O(1) per-row emission. **NOT per-row EXISTS probes.**

### Cache read paths (BridgeOnlyRepository — amortized snapshot enumeration)

- **CACHE-01/02/04 (bridge-only path)**: inline `completedByChildren` / `sequential` / `attachments.length` reads added to the **existing per-task/per-project OmniJS enumeration script** that builds the snapshot. Single script, no extra round-trip. Measured cost: ~362 ms combined for 3427 tasks + 385 projects, amortized per snapshot load.
- Cross-path equivalence must be proven (contract test).

### ProjectType assembly (service layer)

- **HIER-05**: `ProjectType` value constructed at the service layer from the `(sequential, containsSingletonActions)` tuple:
  - If `containsSingletonActions` → `"singleActions"` (takes precedence over `sequential`)
  - Else if `sequential` → `"sequential"`
  - Else → `"parallel"`

### Default response shape — strip-when-false flags

- **FLAG-01** `hasNote: true` — tasks AND projects, when note field non-empty.
- **FLAG-02** `hasRepetition: true` — tasks AND projects, when repetition rule exists.
- **FLAG-03** `hasAttachments: true` — tasks AND projects, when attachments array non-empty.
- **FLAG-04** `isSequential: true` — **tasks-only**, when `type == "sequential"`. Projects use the full `type` enum via `hierarchy` include group instead.
- **FLAG-05** `dependsOnChildren: true` — **tasks-only**, when `hasChildren AND NOT completesWithChildren`. Projects have no parent-completion notion.

All five strip-when-false. Stripped values MUST NOT appear in output.

### Expanded `hierarchy` include group — full structural detail

- **HIER-01 (tasks)**: when `hierarchy` requested on tasks, response includes:
  - `hasChildren` (strip-when-false)
  - `type` (full enum — always present)
  - `completesWithChildren` (bool — **always present**, even when `false`)
- **HIER-02 (projects)**: same three fields on projects. `type` enum includes `"singleActions"`.
- **PROP-08**: `completesWithChildren` added to `NEVER_STRIP` so `false` values survive the default stripping pipeline.

### Critical invariants

- **FLAG-06 / HIER-04 (no-suppression invariant)**: default-response flags and `hierarchy` include group emit **independently**. When both apply (`hierarchy` requested on a task that also triggers `dependsOnChildren` or `isSequential`), the agent sees BOTH the derived default flag AND the fuller hierarchy field. Redundancy is intentional — low-cost, high-value predictability. Must NOT be de-duplicated. Contract test proves this.
- **HIER-03**: `hasChildren` name preserved — do NOT rename to `hasSubtasks`. Rename would ripple to projects where "subtasks" doesn't apply.

### Tool descriptions (behavioral meaning — not cosmetic)

- **FLAG-07**: JSON Schema field docs on `list_tasks`, `get_task`, `list_projects` MUST describe the behavioral meaning of:
  - `dependsOnChildren` — "real task waiting on children, not a container; treat as discrete unit of work rather than collapsible grouping"
  - `isSequential` — "only the next-in-line child is available; agents reasoning about actionability must not over-count"
- These are load-bearing agent-behavior signals, not presence flags. Description text must surface that meaning.

### Write-path contract (tasks only; projects rejected)

- **PROP-01 / PROP-02** `completesWithChildren: bool` on `add_tasks` and `edit_tasks`:
  - Patch semantics: `Patch[bool]` — omit = no change, value = update, **null rejected** (booleans have no cleared state).
  - Same treatment as `flagged`.
- **PROP-03 / PROP-04** `type` on `add_tasks` and `edit_tasks`:
  - `Patch[TaskType]` where `TaskType = "parallel" | "sequential"`.
  - Null rejected. `"singleActions"` rejected **naturally via TaskType enum validation** — no custom messaging; generic schema error is sufficient.
- **PROP-07**: Writes to `completesWithChildren` / `type` on projects rejected at the tool surface. Read path for projects is covered (HIER-01/02); write path deferred to v1.7.

### Create-default resolution (add_tasks)

- **PROP-05**: When agent omits `completesWithChildren` on `add_tasks`, service resolves to `OFMCompleteWhenLastItemComplete` (factory default: `true`) and writes **explicitly**.
- **PROP-06**: When agent omits `type` on `add_tasks`, service resolves to `OFMTaskDefaultSequential` (factory default: `"parallel"`) and writes **explicitly**.
- Server never relies on OmniFocus's implicit defaulting. Same principle as dates.

### Extra="forbid" on derived read-only fields

- **FLAG-08**: All six derived read-only flags — `hasNote`, `hasRepetition`, `hasAttachments`, `hasChildren`, `dependsOnChildren`, `isSequential` — rejected by Pydantic `extra="forbid"` on `add_tasks` / `edit_tasks` input models.
- Generic schema error is the expected behavior. **No custom educational messaging** — JSON Schema already tells agents which fields are writable.

### Incidental cleanup

- **STRIP-11**: Remove `availability` from `NEVER_STRIP` in `src/omnifocus_operator/server/projection.py`. Pre-existing defensive entry with no actual purpose. Carry-over todo explicitly scheduled for Phase 56.

### Naming

- **`type`** is the canonical name for parallel/sequential (tasks) / parallel/sequential/singleActions (projects). Per-entity enums: `TaskType`, `ProjectType`. This supersedes earlier drafts that used `actionOrder`.
- No collision risk with nested `RepetitionRule.type` — different scope.
- Match OmniFocus UI terminology: "Project Type" on projects, "Group Type" on task groups.
- `completesWithChildren` mirrors OmniFocus UI "Complete with last action" without borrowing "actions" jargon.

### Claude's Discretion

The following are **implementation details** the planner/executor may choose, provided they honor the contracts above:

- Exact Pydantic model structure for `Patch[TaskType]` and `TaskType` / `ProjectType` enum models (follow existing patterns in `models/enums.py`, `contracts/use_cases/`).
- Ordering of plan waves within this phase (but the spec's 3-wave guidance — preferences+cache / read surface / write surface — is strongly suggestive and matches the natural dependency chain).
- Method-object pipeline structure for any new service use cases (per `docs/architecture.md` "Method Object Pattern").
- Exact SQL projection for `completeWhenChildrenComplete` / `sequential` — whether added to existing `query_builder.py` row projection or a dedicated projector. Either is fine if cross-path equivalence holds.
- Test organization (mirror existing `tests/` structure for the affected modules).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.** Group by topic; all paths relative to repo root.

### Full design spec + spike evidence (source of truth)

- `.research/updated-spec/MILESTONE-v1.4.1.md` — full design contract for v1.4.1 (both phases). Phase 56 spec is self-contained above but the milestone doc has additional rationale, "alternatives considered", and naming history.
- `.research/deep-dives/v1.4.1-cache-coverage/FINDINGS.md` — Spike 1 evidence: cache column existence, population distribution, OmniJS↔cache cross-check, attachment performance measurements. Justifies `hasAttachments` as default-response field.
- `.research/deep-dives/v1.4.1-filter-benchmark/FINDINGS.md` — Spike 2 (Phase 57 scope, but read for context on the snapshot-build path Phase 56's BridgeOnly enumeration extends).

### Architecture & conventions

- `CLAUDE.md` (project-level) — safety rules (SAFE-01/02: no RealBridge in automated tests), model conventions, UAT guidelines, service-layer method object pattern.
- `docs/architecture.md` — layer rules, Method Object Pattern (required for all service use cases).
- `docs/model-taxonomy.md` — Pydantic model naming: `models/` no suffix or `Read`; `contracts/` must use write-side suffixes. MANDATORY reading before creating any Pydantic model.
- `docs/omnifocus-concepts.md` — OF data model background (Task vs Project vs ProjectInfo, Attachment, Setting).

### Bridge + service (preferences path)

- `src/omnifocus_operator/bridge/bridge.js` — `handleGetSettings()` is the function to extend (PREFS-01). Existing handler already reads date preferences; mirror that pattern.
- `src/omnifocus_operator/service/preferences.py` — `OmniFocusPreferences` class to extend (PREFS-02). Date preference lazy-load-once pattern is the template.

### Repository layer (cache read paths)

- `src/omnifocus_operator/repository/hybrid/hybrid.py` — HybridRepository entry point.
- `src/omnifocus_operator/repository/hybrid/query_builder.py` — SQL query assembly (where new column reads attach for CACHE-01/02/03 and the batched attachment set for CACHE-04).
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` + `adapter.py` — BridgeOnlyRepository and its OmniJS-enumeration adapter (where inline `completedByChildren` / `sequential` / `attachments.length` attach).

### Server / projection (strip pipeline)

- `src/omnifocus_operator/server/projection.py` — `NEVER_STRIP` lives here (PROP-08 addition, STRIP-11 removal). Strip-when-false logic for the new derived flags also touches this file.
- `src/omnifocus_operator/server/handlers.py` — MCP tool handlers for `list_tasks`, `get_task`, `list_projects`, `add_tasks`, `edit_tasks`. Tool description docstrings (FLAG-07) live here or in the FastMCP tool registration.

### Models + contracts

- `src/omnifocus_operator/models/task.py` + `project.py` — `Task` / `Project` read model. Fields for derived flags, `type`, `completesWithChildren` go here (respecting model taxonomy).
- `src/omnifocus_operator/models/enums.py` — `TaskType`, `ProjectType` enums live here.
- `src/omnifocus_operator/contracts/use_cases/` — `add_tasks` / `edit_tasks` input contracts. `Patch[bool]` / `Patch[TaskType]` fields added here with `extra="forbid"` behavior inherited.

### Service convention

- `src/omnifocus_operator/service/service.py` + sibling modules — method-object pipelines for use cases. New write-side resolution (PROP-05/06 create-default resolution) attaches to the `add_tasks` pipeline as a new pipeline step.

### Tests

- `tests/test_output_schema.py` — MUST run after any model change (see project CLAUDE.md). Verifies serialized output validates against MCP outputSchema.
- `tests/contracts/` + `tests/repository/` + `tests/service/` + `tests/server/` — mirror source structure. New tests land in the matching folder.

</canonical_refs>

<specifics>
## Specific Ideas

### Suggested plan-wave decomposition (strong recommendation, not mandate)

Per the ROADMAP.md plan-wave guidance — these map cleanly to dependency chains:

1. **Wave 1 — Preferences + cache foundation**
   - PREFS-01..05: bridge/settings extension + `OmniFocusPreferences` extension
   - CACHE-01..04: cache read paths on both repos + cross-path equivalence test
   - Outcome: the server can **read** the new underlying OF properties and the user's defaults, with no behavior change yet.

2. **Wave 2 — Read surface**
   - FLAG-01..08: default-response derived flags + tool-description behavioral meaning
   - HIER-01..05: expanded `hierarchy` include group + `ProjectType` service-layer assembly
   - PROP-08: `completesWithChildren` to `NEVER_STRIP`
   - STRIP-11: remove `availability` from `NEVER_STRIP`
   - Outcome: agents see the new read shape. Writes still fail (no write-path support yet).

3. **Wave 3 — Write surface**
   - PROP-01..04: writable `completesWithChildren` + `type` on tasks (`Patch[bool]` / `Patch[TaskType]`)
   - PROP-05..06: create-default resolution via preferences
   - PROP-07: reject writes on projects at tool surface
   - Round-trip tests on both repos, golden master capture
   - Outcome: full end-to-end surface, phase complete.

Dependency flow: Wave 2 depends on Wave 1 (needs cache paths). Wave 3 depends on both (preferences for create-defaults, read surface for round-trip verification). Plan-checker should verify this wave ordering matches `depends_on` declarations.

### Test expectations (for plan task acceptance criteria)

- **Cross-path equivalence** (Wave 1): same entity IDs produce identical `completesWithChildren` / `type` / `hasAttachments` under `HybridRepository` vs `BridgeOnlyRepository` via `InMemoryBridge` / `SimulatorBridge` fixtures. Do **NOT** touch `RealBridge`.
- **No-suppression invariant** (Wave 2): contract test requests both default and `hierarchy` on a task with `type == "sequential"` AND `hasChildren AND NOT completesWithChildren` — assert `isSequential`, `dependsOnChildren` appear in default AND `type`, `hasChildren`, `completesWithChildren` appear in `hierarchy`. Redundancy is the requirement, not a bug.
- **Round-trip** (Wave 3): create task with `completesWithChildren=false, type="sequential"` → read back → edit both values → read back → verify. Plus omit-fields path → verify preference fallback values materialize.
- **extra="forbid"** (Wave 3): passing any of the six derived flags on `add_tasks`/`edit_tasks` input produces a Pydantic schema error. Test each field name.
- **Golden master** per project CLAUDE.md feedback memory: agents create test infrastructure; capture/refresh is human-only. Plans should note where a golden master capture is required, not execute it.

### Safety reminders for executor

- **SAFE-01/02**: Automated tests MUST use `InMemoryBridge` or `SimulatorBridge` only. No `RealBridge`. CI greps for the literal class name; prose uses "the real Bridge".
- **UAT is human-initiated only** — plans may specify UAT validation steps but must not auto-invoke UAT regression.
- Run `uv run pytest tests/test_output_schema.py -x -q` after any model change (per CLAUDE.md).

</specifics>

<deferred>
## Deferred Ideas

Explicitly out of scope for Phase 56; captured in REQUIREMENTS.md "Future Requirements" or routed to another phase/milestone:

- **`parent` filter + filter unification** (PARENT-*, UNIFY-*, WARN-*) → Phase 57.
- **Project writes for `completesWithChildren` / `type`** → v1.7 (consistent with existing write surface).
- **Cache-direct settings access** (plist decode in service layer) → rejected for architectural consistency; future optimization if bridge startup cost ever becomes meaningful.
- **Custom educational errors for derived-field rejection** → rejected; generic Pydantic schema error is sufficient.
- **`hasChildren` rename to `hasSubtasks`** → rejected; would ripple to projects where "subtasks" doesn't apply.
- **Array of references on `parent` filter** → future extension if real agent pain emerges (not Phase 56 OR Phase 57).

---

*Phase: 56-task-property-surface*
*Context gathered: 2026-04-19 via PRD Express Path from `.research/updated-spec/MILESTONE-v1.4.1.md`*
</deferred>
