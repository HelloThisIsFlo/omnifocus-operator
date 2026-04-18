# Interview Notes — MILESTONE-v1.4.1.md

**Status:** Paused after deep dive on filter unification. Spec file unmodified.
**Last activity:** 2026-04-18 (session 2)

## Where to pick up

Three things outstanding:
1. **Implementation strategy for filter unification** — service-layer (Claude rec) vs repo-layer Python filtering (Flo's proposal) vs copy-paste sibling. Performance benchmark TBD by Flo.
2. **Thread 6 explicit confirmations** — `parent: "$inbox"`, parent-matching-project warning, multi-parent (verbal alignment but not explicitly locked).
3. **Thread 8 (write-path contract)** — completely untouched. Patch semantics for new fields, defaults on creation, UNSET handling.
4. **`hasAttachments` placement** — Claude recommended default field (same as hasNote/hasRepetition); user did NOT explicitly confirm in either session.

## Locked decisions (in order they were settled)

### Round 1 — Presence-flag pattern vs spike reality

- **Decision rule** (already in arch doc, reaffirmed): rare signal → default field (strip-when-false); common signal → include group.
- **`hasNote`** ✅ default field, strip-when-false. Pairs with `notes` include group.
- **`hasRepetition`** ✅ default field, strip-when-false. Pairs with `time` include group.
- **`hasAttachments`** ⚠️ Claude recommends default field same pattern; **NOT explicitly confirmed by user**.

### Round 2 — Naming + placement for new fields

- **`completesWithChildren`** ✅ replaces OmniJS `completedByChildren`. Reasoning: closest to OmniFocus UI's "Complete with last action" without borrowing "actions" jargon. Self-documents the mechanism.
- **`actionOrder`** ✅ string enum, per-type members. Lives in `hierarchy` include group.
- **Flat layout in hierarchy** ✅ no nested `asActionGroup` sub-object. NEVER_STRIP solves the "false disappears" problem more cheaply than nesting.
- **`hasChildren` stays** ✅ no rename to `hasSubtasks`. User's reasoning: rename ripples to projects where "subtasks" doesn't make sense. Same vocabulary-survives-both-types test that drives all naming here.

### Round 3 — Default-response signals

- **`isSequential: true`** ✅ presence flag in default response, strip-when-false. Rarity is workflow-grounded (dependency chains are rare regardless of user defaults).
- **`actionOrder` enum in hierarchy** ✅ full detail. Option (a) — no suppression when hierarchy is included (predictable shape over de-duplication).
- **`dependsOnChildren: true`** ✅ derived presence flag in default response. Emit rule: `hasChildren AND NOT completesWithChildren`. Workflow-neutral signal that the user explicitly disabled auto-complete (deviation from OF factory default carries information). **Tasks-only** (per Flo).
- **`completesWithChildren` added to NEVER_STRIP** ✅ so false survives in hierarchy include. Verified via Explorer: `NEVER_STRIP` is the right mechanism (existing pattern, only `availability` currently in it).

### Cleanup todo (file written)

- `.planning/todos/pending/2026-04-18-remove-availability-from-never-strip.md` — `availability` is in NEVER_STRIP as defensive code with no actual purpose. StrEnum values can't hit the strip set, so the membership doesn't protect anything. Remove + add docstring explaining what NEVER_STRIP is actually for (booleans where false carries meaning). Coordinate with v1.4.1 implementation.

### Thread 4 — Project scope and version timing

- **Reads on both tasks AND projects** ✅ for `completesWithChildren`, `isSequential`, `actionOrder`.
- **`dependsOnChildren` is tasks-only** ✅ per Flo.
- **Per-type ActionOrder enum** ✅:
  - `TaskActionOrder = "parallel" | "sequential"`
  - `ProjectActionOrder = "parallel" | "sequential" | "singleActions"`
  - Defined separately on Task and Project (can't live on `ActionableEntity` due to type asymmetry).
  - Justification: matches existing `availability` per-type precedent. Schema honesty (agent never told a task can be `singleActions`). Write-path validation comes free in v1.7.
- **All writes deferred to v1.7** ✅ consistent with README roadmap. No partial project-write surface in v1.4.1.

### Thread 5 — `parent` filter behavioral semantics

- **All descendants, any depth** ✅ (locked by spec).
- **Three-step resolver** ✅ (`$` prefix → exact ID → name substring). Same as every other reference.
- **AND-composed with other filters** ✅ (locked by spec).
- **Resolved parent task always included as anchor** ✅ — but only when resolved entity is a TASK. Projects can't appear as rows in `list_tasks` (Hole 1 reframed).
- **No intermediate parent anchors** ✅ Option 1 (strict filter). Verified consistent with `project` filter behavior today (Explorer 1).
- **Standard pagination** ✅ `limit` + cursor over flat result set, outline order preserved by existing CTE.
- **Filtered-subtree warning** ✅ fires when filter (parent or project) + at least one other filter combined. Pedagogical (teach the rule) over precise (detect dangling refs). Lives in domain layer, not projection.

**Verbatim warning text** (locked):
> *"Filtered subtree: resolved parent tasks are always included, but intermediate and descendant tasks not matching your other filters (tags, dates, etc.) are excluded. Each returned task's `parent` field still references its true parent — fetch separately if you need data for an excluded intermediate."*

### Filter unification (NEW IN SESSION 2)

**Behavioral unification** ✅ `project` and `parent` filters share core logic. Two surface filters, ONE shared mechanism. Differ by entity-type-set: `project` accepts `{project}`, `parent` accepts `{project, task}`.

**Conditional anchor injection** ✅ inside the shared function: if resolved entity is a task, inject as anchor; if project, don't (because list_tasks doesn't return projects). One function, one branch, handles both surface filters.

**Identical results when same entity** ✅ `parent: "X"` and `project: "X"` produce identical results when X resolves to the same project.

**`parent: "$inbox"` works** ✅ (verbally aligned, not explicitly locked) — inbox is a project, parent accepts projects.

**Substring multi-match returns all matches** ✅ existing behavior, extended to parent for free.

**Single reference per filter** ✅ no array-of-references support. Substring matching naturally handles multi-entity cases.

**Warnings inventory under unification:**
1. ✅ Filtered-subtree warning (above) — NEW, fires for both filters when combined with siblings.
2. ✅ Multi-match warning — EXISTS at `service/domain.py:450-460` and `warnings.py:156-158`. Reused for parent.
3. ✅ Inbox-name-substring warning — EXISTS at `service.py:_check_inbox_project_warning()` and `warnings.py:170-176`. Reusable AS-IS for parent (Claude initially overstated the issue; walked back).
4. ⚠️ **NEW warning when `parent` + `project` filters used together** — soft hint, rare combination. Verbally aligned, not explicitly locked.
5. ⚠️ **NEW warning when `parent` substring resolves to a project** — soft hint suggesting `project` filter. Verbally aligned (Flo's "I'm a bit soft and call it 'consider using'"), not explicitly locked.

## Open threads (paused at this checkpoint)

| # | Thread | Status |
|---|--------|--------|
| Impl A | Service-layer vs repo-layer unification | 🟡 Claude rec service-layer; Flo proposes repo-layer with Python filtering. Flo to benchmark Python filter on 10K tasks separately. Real concern: read-path perf (current 30-60x speedup comes from SQL filtering). |
| 6.1 | `parent: "$inbox"` accepted | 🟢 verbally aligned, needs explicit lock |
| 6.2 | parent substring matches project → soft warning | 🟢 verbally aligned, needs explicit lock |
| 6.3 | Multi-parent (array of refs) — no, substring handles multi | 🟢 verbally aligned, needs explicit lock |
| 8 | Write-path contract for new fields | ⏳ completely untouched |
| 1.* | `hasAttachments` placement (default field) | 🟡 Claude rec, user never explicitly confirmed across both sessions |
| Impl B | Anchor task ordering — fit into outline-order CTE | 🟡 implementation detail Flo flagged; tackle when implementing |
| Impl C | Inbox warning context-awareness | ✅ resolved — warning text reusable as-is for parent filter |

## New angles surfaced in session 2

- **Three vocabularies for `completedByChildren`** — OmniJS API, OmniFocus UI ("Complete with last action"), spec working name ("auto-complete"). Important learning: when 3 vocabularies exist, agent-facing one matters most because that's what the LLM reads in tool docs.
- **Project type third state** (`singleActions`) — projects have parallel/sequential/singleActions, not a boolean. Broke the original `sequential: bool` framing. Resolved via per-type enums.
- **Inverted polarity insight** — `dependsOnChildren` works as workflow-neutral signal because OF factory default is "complete with last action ON." `false` is the "user explicitly considered this" state (information-carrying), `true` is the "didn't think about it" state (noise).
- **`NEVER_STRIP` is currently dead protection for `availability`** — captured as cleanup todo. Real load-bearing use comes when `completesWithChildren` (boolean) joins it in v1.4.1.
- **Domain logic vs projection logic distinction** (Flo correction) — warnings about filter semantics are domain logic, not projection. Projection = field formatting/stripping. Place new warnings in domain layer.
- **Filter unification as architectural pattern** — one mechanism, two surface variants differing by entity-type-set. Anchor injection conditional on entity type. Future scope filters (e.g., `folder`) slot in for free.
- **Verified existing behavior** (Explorers 1+2):
  - Today's `project` filter ALREADY behaves exactly like the rule we locked for `parent` (strict filter, no intermediate anchors, no project-as-row).
  - Multi-match and inbox-name warnings already exist; reusable for parent.

## Codebase grounding (added in session 2)

Existing references confirmed by explorers:

- **Filter resolver:** `service/resolve.py:243-269` — exact ID → substring → empty. Lightweight utility, not a shared abstraction.
- **Pipeline composition:** `service/service.py:363-458` (`_ListTasksPipeline`). Has `_resolve_project()`, `_resolve_tags()` — copy-paste candidates.
- **Repo query builder:** `repository/hybrid/query_builder.py:233-318` (`build_list_tasks_sql`). Strict AND composition at line 296. Project filter SQL at 258-265 (subquery on `containingProjectInfo`).
- **Bridge-only filter:** `repository/bridge_only/bridge_only.py:227-229` — Python filter `t.project.id in pid_set`.
- **Multi-match warning:** `service/domain.py:450-460` + `warnings.py:156-158`. Test at `tests/test_service_domain.py::test_multi_match_warning`.
- **Inbox-name warning:** `service.py:_check_inbox_project_warning()` + `warnings.py:170-176`. Test at `tests/test_list_pipelines.py::test_bare_inbox_matches_project_name_not_system`.
- **Tasks-only result enforcement:** `query_builder.py:113, 165` — `WHERE pi.task IS NULL` excludes project-root tasks.

## Implementation cost estimate (Explorer 3)

- **Minimal copy-paste:** 2-3 hours. Sibling implementation, no abstraction. Risk: drift over time.
- **Service-layer unification (Claude rec):** ~6-10 hours. Extract `EntityTypeFilter` helper, route both filters through it. Repo implementations stay independent (Hybrid keeps SQL, BridgeOnly keeps Python).
- **Repo-layer unification (Flo proposal):** TBD by perf benchmark. If Python filtering is acceptable for 10K tasks, ALL filtering moves to domain layer; both repos serve raw fetch + Python applies filter. Cleaner but forfeits SQL filtering speedup.
- **Refactor scope:** 5-6 files touched, ~30 existing tests need updates, 40-60 new tests.
- Files: `contracts/use_cases/list/tasks.py`, `service/service.py`, `repository/hybrid/query_builder.py`, `repository/bridge_only/bridge_only.py`, possibly `service/resolve.py`.

## Skill feedback (for end-of-session, per Flo's request)

Captured during session 2 — Flo wants feedback on `/spec-interview` skill itself, NOT project memory:

1. **Sub-decision confirmation gap.** Skill's "explicit approval" guidance applies to file write-back at the end. It does NOT cover sub-decisions DURING the interview. Real failure mode this session: Claude wrote a "LOCKED: X" task containing an unsettled sub-rule (warning timing) without asking. Flo flagged as red flag; later partially retracted, but the underlying gap is real. Suggested skill addition: "Insight boxes can present tradeoffs; they cannot make decisions. 'I recommend X' still requires explicit confirmation before locking."
2. **LOCKED naming convention.** Skill doesn't address task list discipline — when to use `LOCKED:` vs `OPEN:` vs other markers. Worth documenting since Claude naturally adopts the convention but bundles open items inside locked-named tasks.
3. **Re-locking when downstream questions reveal tension.** Thread 5 was locked (Option 1, no intermediate anchors), then partially reopened when filter-unification discussion surfaced edge cases (anchor-as-row asymmetry). Skill could acknowledge: locks are provisional until adjacent threads are explored.
4. **Spawning explorers mid-interview.** Worked well this session — three parallel explorers verified assumptions before locking. Skill mentions "explorers aren't only for step 4" but worth strengthening: spawn when a decision depends on unverified codebase facts, especially before multi-file architectural locks.
5. **Pause checkpoint discipline.** This file. Skill prescribes the structure well; in practice the most useful sections are "where to pick up" + "verbally aligned but not locked" (so resumed session knows what's settled vs what's pending explicit approval).

## To resume

1. Confirm thread 6 outstanding items: `parent: "$inbox"` (yes), parent-matching-project warning text, no multi-parent.
2. Decide implementation strategy: service-layer vs repo-layer unification (after Flo benchmark).
3. Tackle thread 8 (write-path contract) — completely untouched.
4. Confirm `hasAttachments` placement (still unconfirmed across two sessions).
5. **Then** propose write-back to spec file with explicit Flo approval.
