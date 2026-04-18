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
