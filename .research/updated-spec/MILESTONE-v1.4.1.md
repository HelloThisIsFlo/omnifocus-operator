# Milestone v1.4.1 — Task Property Surface & Subtree Retrieval

## Status: Design Locked — Pending Pre-Implementation Spikes

Three-session design interview completed 2026-04-18. All semantic design decisions locked. Two pre-implementation spikes remain before planning — outcomes may narrow v1.4.1 scope (see Pre-Implementation Spikes).

## Goal

Close two categories of friction left after v1.4:

1. **Task property exposure** — expose OmniFocus properties the server currently hides (auto-complete, parallel/sequential, presence of notes / repetition / attachments).
2. **Subtree retrieval** — `parent` filter on `list_tasks` so agents can fetch a task's descendants in a single call, mirroring the existing `project` filter.

## Why a Point Release

Same pattern as v1.3.1 / v1.3.2 / v1.3.3 after v1.3. Narrow field additions and one filter extension — not a new tool or architectural change. Strictly additive.

---

## What to Build

### New Writable Fields (tasks)

Two new fields are writable on tasks via `add_tasks` and `edit_tasks`. Both are read-only on projects in v1.4.1 (project writes stay deferred to v1.7, consistent with the existing write surface).

#### `completesWithChildren: bool`

Maps to OmniJS `completedByChildren`. The name mirrors OmniFocus UI's "Complete with last action" without borrowing "actions" jargon.

- **Read**: tasks AND projects.
- **Write**: tasks only.
- **Edit patch semantics**: `Patch[bool]` — omit = no change, `null` rejected (booleans can't be "cleared"), value = update. Same treatment as `flagged`.
- **Create default**: honors user's OF preference (`OFMCompleteWhenLastItemComplete`), with OF factory default `true` as fallback.

#### `actionOrder: enum` (per-type)

Per-type enum reflecting the asymmetry between tasks (parallel/sequential) and projects (+ singleActions). Precedent: matches existing per-type `availability` enum.

- `TaskActionOrder: "parallel" | "sequential"`
- `ProjectActionOrder: "parallel" | "sequential" | "singleActions"`

Placement:
- **Read**: tasks AND projects.
- **Write**: tasks only. `"singleActions"` rejected at type level on tasks.
- **Edit patch semantics**: `Patch[TaskActionOrder]` — omit = no change, `null` rejected, value = update.
- **Create default**: honors user's OF preference (`OFMTaskDefaultSequential`), with OF factory default `"parallel"` as fallback.
- **Naming note (soft spot)**: `actionOrder` is a revisit candidate before write implementation — Flo is not firmly committed to the name.

### New Derived Fields (read-only)

Computed from other state. Not independently writable. Passing them on `add_tasks`/`edit_tasks` is rejected by Pydantic `extra="forbid"` (generic schema error — no custom educational errors).

| Field | Derived from | Placement |
|---|---|---|
| `hasNote: true` | `note` field non-empty | Default response (strip-when-false) |
| `hasRepetition: true` | Repetition rule exists | Default response (strip-when-false) |
| `hasChildren: true` | Has child tasks | `hierarchy` include group (strip-when-false). **Kept as `hasChildren`**, not renamed to `hasSubtasks` — rename ripples to projects where "subtasks" doesn't apply. |
| `dependsOnChildren: true` | `hasChildren AND NOT completesWithChildren` | Default response (tasks-only, strip-when-false). Workflow-neutral signal: user explicitly disabled auto-complete (deviation from factory default carries information). |
| `hasAttachments: true` | Attachments array non-empty | **Conditional** — see Pre-Implementation Spike #1 |

#### `isSequential: true` (tasks-only)

Derived presence flag on the task default response. Tasks only; projects use the full `actionOrder` enum exposed via the `hierarchy` include group.

- **Emit rule**: `actionOrder == "sequential"` → `isSequential: true`, else stripped.
- **Rationale**: dependency chains are rare regardless of user workflow. Workflow-neutral rarity signal.

### Expanded `hierarchy` Include Group

Full structural detail on both tasks and projects. No suppression when the group is requested — predictable shape over de-duplication.

- `hasChildren: true` (strip-when-false)
- `actionOrder`: full enum value, always present when group included
- `completesWithChildren: bool`: always present when group included. Added to `NEVER_STRIP` so `false` survives the default stripping pipeline.

### `parent` Filter on `list_tasks`

New filter mirroring the existing `project` filter. Resolves a task or project reference; returns all descendants at any depth, with the resolved task as anchor when applicable.

**Contract:**
- Accepts name (case-insensitive substring) or ID — same three-step resolver as every other entity reference (`$` prefix → exact ID → name substring).
- Returns all descendants of the resolved reference at any depth.
- The resolved task itself is included as an anchor in the result set. Projects can't be rows in `list_tasks`, so project resolutions add no anchor.
- AND-composed with all other filters (project, tags, dates, etc.). No special precedence.
- Standard pagination (limit + cursor) over the flat result set. Outline order preserved.
- **Single reference only.** No array of references. Substring matching handles multi-entity cases when matches share a substring. Array support left as an explicit future extension — driven by real agent pain (parent filter missing), not imagined flexibility.

**`$inbox` handling:** `parent: "$inbox"` is accepted and produces the identical result to `project: "$inbox"` — both surface inbox tasks. Same contradiction rules apply as `project: "$inbox"` today (e.g., `parent: "$inbox"` + `inInbox=false` → error).

**Alternatives considered and rejected:**
- Auto-expand children in search results — bloats every query; confuses "find a task" intent.
- Mitigate bloat with warnings — cognitive overhead without solving the underlying problem.

### Filter Unification (architectural pattern)

`project` and `parent` share the same core mechanism. Two surface filters, one shared function, differing only by accepted entity-type-set:

- `project` accepts projects only.
- `parent` accepts projects AND tasks.

Identical results when the same entity is resolved. Conditional anchor injection: task-as-anchor if the resolved entity is a task, no anchor if it's a project. Future scope filters (e.g., `folder`) slot in for free.

Implementation strategy (service-layer vs repo-layer with Python filtering) is pending the Python-filter benchmark — see Pre-Implementation Spike #2.

---

## Default Response Shape (task)

Gains from this milestone, all strip-when-false:

- `hasNote`
- `hasRepetition`
- `hasAttachments` *(conditional on SQLite cache spike)*
- `isSequential` (tasks-only)
- `dependsOnChildren` (tasks-only)

`completesWithChildren` does NOT appear in the default response. It lives in the `hierarchy` include group (common field; would clutter default payload if always emitted).

---

## Write-Path Contract

Tasks only. Projects are read-only in v1.4.1.

### Edit semantics (patch)

| Input | Meaning |
|---|---|
| Field omitted | No change |
| Field set to a value | Update |
| Field set to `null` | Rejected for booleans and enum fields (no "cleared" state in OmniFocus) |

Applies uniformly to `completesWithChildren` and `actionOrder`.

### Create defaults (runtime-resolved)

When the agent omits one of these fields on `add_tasks`, the service layer writes the user's OmniFocus preference explicitly:

- `completesWithChildren` → `OFMCompleteWhenLastItemComplete` setting (factory default: `true`)
- `actionOrder` → `OFMTaskDefaultSequential` setting (factory default: `"parallel"`)

Settings are read once per server lifetime and cached. The MCP server writes the resolved value explicitly to OmniFocus — same philosophy as dates. We control the write; we don't rely on OmniFocus's implicit defaulting behavior. This makes the behavior testable and predictable.

### Non-writable fields

`hasNote`, `hasRepetition`, `hasAttachments`, `hasChildren`, `dependsOnChildren` are all derived and read-only. Pydantic `extra="forbid"` rejects them at validation time with a generic schema error — no custom educational messaging, because the JSON Schema already tells agents which fields are writable.

---

## Warnings

| Warning | Trigger | Status |
|---|---|---|
| Filtered-subtree | `project` or `parent` filter + any other filter | New — domain layer |
| Multi-match | Substring matches multiple entities | Existing — reused for parent |
| Inbox-name substring | Non-`$inbox` substring matches the inbox name | Existing — reusable as-is |
| `parent` + `project` used together | Both specified | New — soft hint, rare combination |
| `parent` resolves to a project | ALL matches are projects (not mixed) | New — soft "consider using `project`" hint |

Warnings live in the domain layer (filter-semantics advice), not projection (field formatting/stripping).

**Filtered-subtree warning text (locked verbatim):**

> *"Filtered subtree: resolved parent tasks are always included, but intermediate and descendant tasks not matching your other filters (tags, dates, etc.) are excluded. Each returned task's `parent` field still references its true parent — fetch separately if you need data for an excluded intermediate."*

---

## Pre-Implementation Spikes

Design intent is locked, but two implementation-affecting verifications remain before planning. Both are Flo-run; both may narrow v1.4.1 scope.

### 1. SQLite cache coverage for new read fields

**Question**: Does OmniFocus's SQLite cache expose the properties underlying each new read field? Per-row bridge fallback would erase the 30–60× read-path speedup and is not acceptable.

**Fields to verify** (tasks AND projects):
- `completedByChildren` (→ `completesWithChildren`)
- `sequential` (→ `actionOrder`)
- `attachments` presence (→ `hasAttachments`)

**Decision per field**: cache supports it → lock as designed. Cache doesn't support it → scope that field out of v1.4.1 (defer to a later milestone that handles cache extension or the broader attachment story).

### 2. Python-filter benchmark

**Question**: What is the cost of Python-side filtering over ~10K tasks?

**Decision triggered**:
- Fast enough → filter unification can move to the repo layer (cleaner abstraction; forfeits some SQL filtering).
- Too slow → service-layer unification with repos keeping their SQL implementations is the default.

Outcome shapes the filter-unification implementation strategy. The contract is unchanged either way.

---

## OmniJS Spike Results (2026-04-18)

All properties needed for this milestone are confirmed available in OmniJS. Spike ran against a live OmniFocus database; write tests used scratch tasks/projects created and deleted within the script.

### `completedByChildren` (spec: `completesWithChildren`)

- **OmniJS property**: `task.completedByChildren` / `project.completedByChildren`
- **Type**: Boolean, read/write on both Task and Project
- **Empirical**: appeared `true` on the vast majority of sampled tasks including leaves — factory default genuinely `true`, independent of hierarchy.

### `sequential` (spec: `actionOrder`)

- **OmniJS property**: `task.sequential` / `project.sequential`
- **Type**: Boolean, read/write on both Task and Project
- **Semantic**: `sequential: true` → ordered; `sequential: false` → parallel.
- **Projects third state (`singleActions`)**: handled at the project level via the per-type `ProjectActionOrder` enum.

### `attachments` (spec: `hasAttachments`)

- **OmniJS property**: `task.attachments` / `project.attachments`
- **Type**: `Array<FileWrapper>`, read-only on both Task and Project
- **Presence test**: `t.attachments.length > 0`
- **Implementation**: bridge reads `t.attachments.length`, emits `hasAttachments: true` only when non-zero.
- **Cache coverage unverified** — see Pre-Implementation Spike #1.

### OF Settings API (session 3 finding)

OmniJS exposes user preferences via `settings.objectForKey(key)`. Two keys relevant to this milestone:

- `OFMCompleteWhenLastItemComplete` — user default for `completedByChildren`
- `OFMTaskDefaultSequential` — user default for `sequential`

Both confirmed readable. Read once per server lifetime (cached), used by the service layer to populate create-time defaults when the agent omits these fields.

---

## Naming Revisit Candidates (before write implementation)

- **`actionOrder`**: soft lock. Flo not firmly committed. Worth a naming pass before the write path is implemented.

---

## Spike Results (2026-04-18)

Both pre-implementation spikes defined above are complete. **Design fully unblocked — no fields scoped out, no contract changes required.** This section summarises findings so the milestone is self-contained; full evidence tables, query plans, and benchmark data live in the linked FINDINGS docs.

### Spike 1 — SQLite Cache Coverage: ✅ all three fields cache-backed

Confirms that `completesWithChildren`, `actionOrder` (including the `singleActions` third state), and `hasAttachments` all read cleanly from the SQLite cache — no per-row OmniJS bridge fallback needed for any of them.

**Read source per field (tasks + projects):**

| Field | Task read source | Project read source | Verdict |
|---|---|---|---|
| `completesWithChildren` | `Task.completeWhenChildrenComplete` (INTEGER 0/1) | same column, via the project's Task row | ✅ Locked |
| `actionOrder` parallel / sequential | `Task.sequential` (INTEGER 0/1) | same column, via the project's Task row | ✅ Locked |
| `actionOrder` `singleActions` (projects only) | — (not applicable on tasks) | `ProjectInfo.containsSingletonActions` (INTEGER 0/1) | ✅ Locked |
| `hasAttachments` | `EXISTS (SELECT 1 FROM Attachment WHERE task = ?)` with indexed `Attachment_task` | same shape — `Attachment.task` FK points at the project's Task row | ✅ Locked (default-response field) |

**Project-level access model:** in OmniFocus's SQLite schema, every project is two rows — one in `Task` (the generic node) and one in `ProjectInfo` (project metadata). They join via `ProjectInfo.task = Task.persistentIdentifier`. So all `Task`-level columns (`completeWhenChildrenComplete`, `sequential`, and the Attachment FK pattern) apply automatically to projects. The only project-specific column is `ProjectInfo.containsSingletonActions`, which encodes the `singleActions` third state. Service layer collapses `(sequential, containsSingletonActions)` into the `ProjectActionOrder` enum.

**Key evidence:**

- **Attachment presence performance** — median **2.1 ms** over the full 3,426-row corpus using `EXISTS (SELECT 1 FROM Attachment WHERE task = ?)`. The `Attachment_task` index makes each lookup O(log n); growth at 25K is ~15 ms worst case. Well under any response-time budget.
- **Population distribution** — `completeWhenChildrenComplete` is 62% true / 38% false on tasks (17.9% true on projects); `sequential` is 99% false on tasks, 88% false on projects; `containsSingletonActions` is 22% true on projects. Columns are populated, not schema-present-but-empty.
- **OmniJS per-row cross-check** — 20 sampled task IDs × 3 fields = **60/60 matches** between the OmniFocus bridge and the SQLite cache. No identity drift between the two views.

**Bonus — user-default settings:**

- `OFMCompleteWhenLastItemComplete` lives in the `Setting` table as a 42-byte plist blob. Decoded via `plistlib.loads(valueData)` → native Python `bool`. Read once at server startup, cached for the process lifetime.
- `OFMTaskDefaultSequential` is **not present in the cache** when the user hasn't changed it from the OF factory default. OmniFocus only materialises settings when explicitly set — absence = "user kept the documented default" (a valid signal, not an error). Service layer must implement: "row present → decode; row absent → use OF factory default".

**Decisions unblocked:**

- `hasAttachments` ships as a **default-response field** (not gated behind `include`).
- Service layer reads app-level defaults cheaply from cache — no OmniJS round-trip at startup.
- No v1.4.1 fields scoped out. The full design as specified above stands.

→ Full details: [`.research/deep-dives/v1.4.1-cache-coverage/FINDINGS.md`](../deep-dives/v1.4.1-cache-coverage/FINDINGS.md)

### Spike 2 — Python-Filter Benchmark: ✅ repo-layer unification viable

Measures Python-side filtering cost for the new `parent` subtree filter across a 1K / 5K / 10K / 25K synthetic corpus sweep plus a live-DB cross-check.

**Verdict:** Python warm-path p95 at 10K is **≤ 1.30 ms across all three scenarios** — 77× under the pre-declared 100 ms "viable" threshold. **Filter unification moves to the repo layer** (the "Fast enough" branch of the original decision framing).

**Numbers at the 10K target scale:**

| Scenario | SQL p95 | Python warm p95 | Python cold p95 |
|---|---:|---:|---:|
| parent only | 2.10 ms | **1.21 ms** | 27.90 ms |
| parent + tag | 0.24 ms | 1.29 ms | 27.79 ms |
| parent + date | 0.88 ms (median) | **1.30 ms** | 26.53 ms |

"Warm" = pre-loaded snapshot (matches `BridgeOnlyRepository`'s amortised path — dominant case in production). "Cold" = snapshot load + children-map build + filter in one call (paid on `get_all()` cache-miss only).

**Decisions unblocked:**

- `HybridRepository` and `BridgeOnlyRepository` share a **Python-based filter pipeline** at the repo layer. Contract stays unchanged — this decision is purely about *where* the filter logic lives.
- `HybridRepository` retains the option to push specific filters down to SQL as an opportunistic optimisation (the spike's recursive-CTE prototype at `.research/deep-dives/v1.4.1-filter-benchmark/experiments/sql_parent_filter.py` shows the shape).
- `ListTasksRepoQuery` gets a new `parent_ids: list[str] | None` field. Filter logic lives at the repo layer, not service.
- `collect_subtree(parent_id, snapshot) -> list[Task]` extracted as a shared helper (both repos use it).

**Caveat (noted, but orthogonal):**

- Cold-path on the live DB (3,426 rows, full ~60-column Task schema) is **50 ms** — higher than the synthetic 10K cold (24 ms) because real row width is ~4× larger. Extrapolating to 10K real-schema rows: cold ≈ 150 ms; at 25K, ≈ 375 ms.
- Cold cost is **shared between SQL and Python paths** (both materialise via `get_all()`), so it doesn't affect the filter-unification choice. If cold ever becomes a concern, the response is snapshot optimisation (projection / lazy deserialisation) — not a change to the filter strategy.

→ Full details: [`.research/deep-dives/v1.4.1-filter-benchmark/FINDINGS.md`](../deep-dives/v1.4.1-filter-benchmark/FINDINGS.md)

### Combined status

- **All pre-implementation blockers cleared.** v1.4.1 is ready for planning.
- No changes to the scope defined in the sections above.
- Two implementation pointers added by the spikes: (a) service layer reads user-default settings from `Setting` table with plist decode + absence-as-default fallback, (b) filter logic unifies at the repo layer with a shared `collect_subtree` helper.
