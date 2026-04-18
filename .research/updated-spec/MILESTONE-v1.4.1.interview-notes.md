# Interview Notes — MILESTONE-v1.4.1.md

**Status:** Interview complete. Spec written back 2026-04-18 (session 3). Remaining open items are pre-planning spikes (Flo-run), not interview questions.
**Last activity:** 2026-04-18 (session 3)

## Where we ended

Three sessions. Design surface substantially locked:
- Session 1: presence-flag pattern, naming, default-response signals, project scope, per-type enums
- Session 2: parent filter semantics, filter unification, filtered-subtree warning text
- Session 3: thread 6 confirmations, hasAttachments (conditional), write-path contract (Q1/Q2/Q3)

Two open items remain — both Flo-run pre-implementation spikes (design-gates, not interview questions).

## Locked decisions (aggregate)

### Round 1 — Presence-flag pattern vs spike reality

- **Decision rule** (already in arch doc): rare signal → default field (strip-when-false); common signal → include group.
- **`hasNote`** ✅ default field, strip-when-false. Pairs with `notes` include group.
- **`hasRepetition`** ✅ default field, strip-when-false. Pairs with `time` include group.
- **`hasAttachments`** ⚠️ locked as default field (strip-when-false) CONDITIONAL on SQLite cache coverage — see session 3 below.

### Round 2 — Naming + placement for new fields

- **`completesWithChildren`** ✅ replaces OmniJS `completedByChildren`. Closest to OmniFocus UI's "Complete with last action" without borrowing "actions" jargon.
- **`actionOrder`** ✅ string enum, per-type members. Lives in `hierarchy` include group. **Soft spot** — Flo "not super set" on the name; revisit candidate before write implementation.
- **Flat layout in hierarchy** ✅ no nested `asActionGroup` sub-object. NEVER_STRIP solves the "false disappears" problem more cheaply than nesting.
- **`hasChildren` stays** ✅ no rename to `hasSubtasks`. Rename would ripple to projects where "subtasks" doesn't make sense.

### Round 3 — Default-response signals

- **`isSequential: true`** ✅ presence flag in default response, strip-when-false, tasks-only. Rarity is workflow-grounded.
- **`actionOrder` enum in hierarchy** ✅ full detail. No suppression when hierarchy is included (predictable shape over de-duplication).
- **`dependsOnChildren: true`** ✅ derived presence flag in default response. Emit rule: `hasChildren AND NOT completesWithChildren`. Tasks-only. Workflow-neutral signal (deviation from OF factory default carries information).
- **`completesWithChildren` added to NEVER_STRIP** ✅ so false survives in hierarchy include.

### Cleanup todo (file written)

- `.planning/todos/pending/2026-04-18-remove-availability-from-never-strip.md` — `availability` is in NEVER_STRIP as defensive code with no actual purpose. Coordinate with v1.4.1 implementation.

### Thread 4 — Project scope and version timing

- **Reads on both tasks AND projects** ✅ for `completesWithChildren`, `isSequential`, `actionOrder`.
- **`dependsOnChildren` is tasks-only** ✅.
- **Per-type ActionOrder enum** ✅:
  - `TaskActionOrder = "parallel" | "sequential"`
  - `ProjectActionOrder = "parallel" | "sequential" | "singleActions"`
  - Defined separately on Task and Project (type asymmetry).
  - Matches existing `availability` per-type precedent. Write-path validation comes free.
- **All writes deferred to v1.7** ✅ consistent with README roadmap. No partial project-write surface in v1.4.1.

### Thread 5 — `parent` filter behavioral semantics

- **All descendants, any depth** ✅
- **Three-step resolver** ✅ (`$` prefix → exact ID → name substring)
- **AND-composed with other filters** ✅
- **Resolved parent task always included as anchor** ✅ — when resolved entity is a TASK. Projects can't appear as rows in `list_tasks`.
- **No intermediate parent anchors** ✅ (strict filter). Consistent with today's `project` filter behavior.
- **Standard pagination** ✅ `limit` + cursor over flat result set.
- **Filtered-subtree warning** ✅ fires when filter (parent or project) + at least one other filter combined. Domain layer, not projection.

**Verbatim warning text** (locked):
> *"Filtered subtree: resolved parent tasks are always included, but intermediate and descendant tasks not matching your other filters (tags, dates, etc.) are excluded. Each returned task's `parent` field still references its true parent — fetch separately if you need data for an excluded intermediate."*

### Filter unification (session 2)

- **Behavioral unification** ✅ `project` and `parent` share core logic. Two surface filters, ONE shared mechanism. Differ by entity-type-set.
- **Conditional anchor injection** ✅ inside the shared function: task-as-anchor if task, no-anchor if project.
- **Identical results when same entity** ✅ `parent: "X"` and `project: "X"` produce identical results when X resolves to the same project.
- **Substring multi-match returns all matches** ✅ extended to parent for free.
- **Single reference per filter** ✅ no array-of-references support.

### Session 3 locks (new)

#### Thread 6 — parent filter confirmations

- **`parent: "$inbox"` works** ✅ same result as `project: "$inbox"` today. Whatever mechanism `project` uses for `$inbox`, `parent` mirrors it. Filtered-subtree warning text unchanged (literal "resolved parent tasks are always included" — zero tasks included when reference resolves to a project is a subset of "always").
- **`parent` substring → project → soft warning** ✅ option (a): fires only when EVERY match is a project. Resolver knows each match's type; trivial `all(...)` check. Pedagogical tone ("consider using `project`"), not punitive.
- **Single reference only, no array of refs** ✅ symmetric with today's `project` filter. Substring handles multi-entity cases when matches share a substring. Array-of-refs left as explicit future extension — driven by observed agent pain (parent filter missing), not imagined flexibility.

#### hasAttachments placement (conditional lock)

- **Design intent**: default field, strip-when-false, pattern consistent with `hasNote`/`hasRepetition`.
- **Precondition**: SQLite cache exposes attachment presence cheaply. Per-row bridge fallback would erase the 30-60x read-path speedup — unacceptable.
- **Fallback**: scope `hasAttachments` out of v1.4.1 if the spike reveals no cache support; defer with the rest of the attachment story.

#### Thread 8 — write-path contract (tasks only; projects deferred to v1.7)

**Q1 — edit semantics:**
- `completesWithChildren: Patch[bool]` — omit = no change, `null` rejected, value = update. Same treatment as `flagged`.
- `actionOrder: Patch[TaskActionOrder]` — omit = no change, `null` rejected, value = update. `"singleActions"` rejected at type level on tasks.

**Q2 — create defaults:**
- Design intent: honor user's OF preferences as default when agent omits the field.
- Service layer reads `OFMCompleteWhenLastItemComplete` and `OFMTaskDefaultSequential` via bridge (one-time per server lifetime, cached).
- Writes the user-preferred value explicitly to OF — same philosophy as dates. We control the write, don't rely on OF auto-apply. Testable, predictable.
- Fallback: factory defaults (`completesWithChildren=true`, `actionOrder="parallel"`) if settings can't be read.

**Q3 — derived field rejection:**
- Generic Pydantic `extra="forbid"` rejection. No custom educational errors.
- Reasoning: passing a derived field is a schema violation, not semantic misuse. Educational errors are reserved for cases the schema can't express (contradictory combos, ambiguous resolutions). JSON Schema already teaches which fields are writable.

## Soft spots flagged (open for revisit)

- **`actionOrder` naming** — Flo "not super set." Revisit before write implementation.

## Pre-Implementation Spikes (Flo-run; blocking planning)

1. **SQLite cache coverage for new read fields** (task #5). Verify `completesWithChildren`, `sequential`/`actionOrder`, attachments presence are all in the SQLite cache. Any field that requires per-row bridge fallback gets scoped out of v1.4.1.
2. **Python-filter benchmark** (task #4). Measure Python-side filter cost over ~10K tasks. Result decides the filter-unification strategy (repo-layer vs service-layer).

## New angles surfaced in session 2

- **Three vocabularies for `completedByChildren`** — OmniJS API, OmniFocus UI ("Complete with last action"), spec working name ("auto-complete"). Agent-facing one matters most (tool docs).
- **Project type third state** (`singleActions`) — broke the original `sequential: bool` framing. Resolved via per-type enums.
- **Inverted polarity insight** — `dependsOnChildren` works as workflow-neutral signal because OF factory default is "complete with last action ON." `false` is information-carrying.
- **`NEVER_STRIP` is currently dead protection for `availability`** — captured as cleanup todo. Real load-bearing use comes when `completesWithChildren` joins it in v1.4.1.
- **Domain logic vs projection logic distinction** — warnings about filter semantics are domain logic. Projection = field formatting/stripping.
- **Filter unification as architectural pattern** — one mechanism, two surface variants differing by entity-type-set.

## New angles surfaced in session 3

- **`$inbox` is a sentinel, not a project row** — `resolve_inbox()` short-circuits `project: "$inbox"` to `inInbox=True` *before* the project-row resolver runs. Design-level implication: unification works (same result), but the shared filter entry needs a `$`-prefix pre-pass that serves both `project` and `parent`. Implementation plumbing; doesn't change contract.
- **OmniJS settings API exposes user preferences** — `settings.objectForKey(key)` returns user-configured values. Two keys relevant: `OFMCompleteWhenLastItemComplete`, `OFMTaskDefaultSequential`. Both confirmed via explorer.
- **Explicit write over implicit OF apply** — Flo's principle: we control the write, always. Same philosophy as dates. Testability > relying on OF's auto-apply behavior (even if it's correct).
- **Schema violation vs semantic misuse** — Flo's principle for when to invest in custom educational errors. Schema violations (extra fields, wrong types) get generic Pydantic errors. Semantic misuse (contradictory combos, ambiguous refs) gets custom teaching.

## Codebase grounding (sessions 2-3)

- **Filter resolver:** `service/resolve.py:243-269` — exact ID → substring → empty.
- **Inbox short-circuit:** `service/resolve.py:217-239` (`resolve_inbox()`) — runs BEFORE project resolver; consumes `$inbox` → `(inInbox=True, project=None)`.
- **Pipeline composition:** `service/service.py:363-458` (`_ListTasksPipeline`).
- **Repo query builder:** `repository/hybrid/query_builder.py:233-318` (`build_list_tasks_sql`). Strict AND at line 296. Project filter subquery 258-265.
- **Bridge-only filter:** `repository/bridge_only/bridge_only.py:227-229` — Python filter.
- **Multi-match warning:** `service/domain.py:450-460` + `warnings.py:156-158`.
- **Inbox-name warning:** `service.py:_check_inbox_project_warning()` + `warnings.py:170-176`.
- **Patch types:** `contracts/base.py:51-64`:
  - `Patch[T]` — value-only (no `null` clear). Used for `name`, `flagged`.
  - `PatchOrClear[T]` — clearable (`null` = clear). Used for dates, estimates.
  - `extra="forbid"` at `base.py:83`.
- **Create precedent:** `contracts/use_cases/add/tasks.py:79` — `flagged: bool = Field(default=False)`.

## Implementation cost estimate (session 2 Explorer 3)

- **Minimal copy-paste:** 2-3 hours. Sibling implementation, no abstraction. Risk: drift over time.
- **Service-layer unification:** ~6-10 hours. Extract shared filter helper; repo implementations stay independent.
- **Repo-layer unification:** TBD by perf benchmark. If Python filtering is acceptable for 10K tasks, all filtering moves to domain layer.
- **Refactor scope:** 5-6 files touched, ~30 existing tests updated, 40-60 new tests.

## Skill feedback captured (session 3; for skill improvement, NOT project memory)

1. **Design vs implementation plumbing conflation (repeat offense).** Flagged twice this session. Pattern: surface a codebase-level mechanism detail and escalate it into a structured design question when the real design was already clear. Heuristic proposed: "if a 'sub-decision' references a specific file, function, or code path, it's probably implementation plumbing; design locks should be expressible as 'the contract behaves like X' without naming a code site."
2. **Over-structuring with AskUserQuestion.** Using the tool for confirmation (yes/no on a preceding synthesis) felt like busywork. Reserve for genuine multi-option design decisions. Plain-text confirmation is often cleaner.
3. **Value of codebase exploration mid-interview (reconfirmed).** Two explorers this session surfaced findings that reframed or verified locks: (a) the `$inbox` sentinel short-circuit in `resolve_inbox`, (b) OmniJS settings API exposes both target preference keys. Continue normalizing mid-interview explorers for factual verification.
4. **Summary over pure acknowledgment.** When Flo pushed back on implementation-plumbing escalation, the recovery that worked was restating his position in my own words and confirming I understood, not just apologizing and moving on.

## Resumption notes (if ever needed)

Spec has been written back. If resuming:
1. Check outcomes of the two pre-implementation spikes (SQLite cache, Python-filter benchmark).
2. If SQLite cache doesn't support a field → remove that field from v1.4.1 scope in the spec.
3. Based on benchmark → lock filter-unification strategy (service-layer vs repo-layer).
4. Revisit `actionOrder` naming if desired.
5. Proceed to `/gsd-plan-phase` for implementation planning.
