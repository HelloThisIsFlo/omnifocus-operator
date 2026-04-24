# Phase 57: Parent Filter & Filter Unification — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `57-CONTEXT.md` — this log preserves the alternatives considered and the reasoning trail.

**Date:** 2026-04-20
**Phase:** 57 — Parent Filter & Filter Unification
**Areas discussed:** Repo query shape → Helper placement (auto-resolved) → `$inbox` consumption → project_ids unification → plan decomposition (deferred)

---

## Discussion Opening

**Claude's recommended starting framing:** "PRD Express Path" (skip discussion, mirror Phase 56's approach), OR discuss 5 implementation gray areas.

**User's choice:** Discuss all 5 gray areas.

---

## Area 1 — Repo query shape for parent refs

**Underlying question:** How should the resolved parent ref(s) be carried in `ListTasksRepoQuery`? PARENT-04 requires conditional anchor injection (task → anchor, project → no anchor), but UNIFY-06 specifies `parent_ids: list[str] | None` (flat). The repo has to distinguish somehow.

### Initial options presented

| Option | Description | Claude's first-pass recommendation |
|---|---|---|
| A: Flat `parent_ids` + snapshot introspection | Single field on RepoQuery. `collect_subtree(id, snapshot)` looks up `parent_id` in `snapshot.tasks` vs `snapshot.projects` to classify. | Initially recommended (spec-literal reading) |
| B: Dual fields — `parent_task_ids` + `parent_project_ids` | Service pre-classifies at resolution. Two clean paths at the repo. | Runner-up |
| C: Rich `ParentRef(id, kind)` | Single field, `kind` tag per ref. Service classifies; new Pydantic model. | Middle ground |

### User's ask

Requested code sketches for all three options. Wanted to see how each would actually look in practice. Asked why the spec locked flat form — noted that the interview-notes reasoning might not be captured cleanly in the final spec.

### Iteration 1 — Claude re-reads the spec

- Re-read `MILESTONE-v1.4.1.md:318` ("`ListTasksRepoQuery` gets a new `parent_ids: list[str] | None`") and UNIFY-06.
- Acknowledged the spec's "flat parent_ids" wording was the default naming pattern (mirror `project_ids`, `tag_ids`, `folder_ids`) rather than an explicit architectural choice.
- Revised recommendation to **Option B (dual fields)** on the grounds that:
  - Option B is more debuggable — `parent_task_ids=["X"]` vs `parent_project_ids=["Y"]` is unambiguous.
  - Option A hides classification in dict lookups; task-id / project-id collision (which shouldn't happen but isn't enforced) would silently prefer task path.
  - Option C adds a new Pydantic model for a 2-field dict — YAGNI.

### User's decision (intermediate)

**Locked Option B — dual fields.** "violates spec's 'parent_ids' literal wording, but wins on explicitness, debuggability, and type-level collision safety."

---

## Area 2 — `collect_subtree` helper placement

Presented options: `repository/subtree.py`, `repository/_filters.py`, or append to existing `pagination.py`.

### User interruption — architectural question

User asked Claude to take a step back and do real architectural research before continuing. Requested reading `docs/architecture.md` and `docs/model-taxonomy.md` fully. Raised the possibility that the spike's "repo-layer" verdict was misremembered and that service-layer unification had been their actual pitch.

### Claude reads the docs

Found the following load-bearing principles:
1. **Service-layer split principle** (architecture.md line 210-239): "Would another OmniFocus tool make this same choice?" — opinionated goes in `domain.py`, mechanical goes in `pipeline/resolve/convert/payload`. Filter resolution is explicitly called out as pipeline/resolve work — the existing pattern is "service resolves, repo filters."
2. **`<noun>Filter` → primitive pattern** (model-taxonomy.md line 131-133): "The service resolves the filter into concrete repo query fields — the filter object itself doesn't appear on the repo query." `DateFilter` is the canonical precedent.
3. **Repository vs DataSource** (architecture.md line 957-961): Repository is chosen to be the rich, filter-aware abstraction, not a thin data source — but "rich" doesn't require it to own domain-level expansion logic.
4. **Structure Over Discipline**: Prefer uniform code paths. Duplication only when paths will GENUINELY diverge.

### Claude's recalibrated recommendation

Reopened the earlier decision. Presented a new option:

- **D1: Service-layer full expansion** — service pre-expands scope refs (project, parent, future folder) into a flat `allowed_task_ids` set on RepoQuery. Repo becomes dumber (just ID set membership). One pattern across all scope filters.

### User's guiding principle

> "Milliseconds don't matter. Single code paths beat divergent implementations. Maintainability is the real concern."

Claude saved this as memory: `feedback_maintainability-over-micro-perf.md`.

### Claude's DDD-informed analysis

Concluded D1 is cleanest by the architecture's own criteria:
- Matches the `<noun>Filter` → primitive resolution pattern that every other filter dimension uses.
- Keeps domain concepts (parent-child relationships) in the domain layer (service), not infrastructure (repo).
- Minimizes contract surface growth on `ListTasksRepoQuery`.
- Extension story is clean: future `folder` filter is 10 lines in service, zero in repos.

### User's ask — honest recommendation first

User asked Claude for its independent recommendation on `project_ids` unification (2a full unification vs 2b parent-only D1) BEFORE revealing their own instinct. Wanted to see if Claude's honest answer matched theirs.

### Claude commits: 2a (full unification)

Reasons:
1. User's "single code path" principle points directly at 2a.
2. 2b puts two similar fields on `ListTasksRepoQuery` — exactly the divergence the principle forbids.
3. UNIFY-01 ("same core mechanism") reads more literally under 2a.
4. Fix divergence when new capability reveals it — cheapest moment to touch the code.
5. Scope cost is bounded (refactor, not rewrite; no golden master churn).

### User's confirmation + deeper framing

User confirmed 2a was their instinct and added a critical framing:

> "The perf budget from Spike 2 was spent intentionally to buy one code path. 2b pays the cost without collecting the benefit."

Cited interview-notes evidence that may or may not be documented. Claude read the interview notes and confirmed:

- **Session 2 line 69-70**: "ONE shared mechanism... conditional anchor injection **inside the shared function**: task-as-anchor if task, no-anchor if project."
- **Session 3 line 161**: "the **shared filter entry**... serves both `project` and `parent`."
- **Session 2 line 185**: "all filtering moves to **domain layer**" (= `service/domain.py`).
- **Session 4 line 116**: "architectural consistency beats micro-optimization" — principle locked on the preferences-path decision.

The interview record unambiguously supports 2a. The final spec's `parent_ids: list[str] | None` wording under-specified the unification intent; the service-layer D1 + full unification realizes that intent more faithfully.

### Final decision for Area 1 (revised from initial B) + Area 2 (auto-resolved)

**Locked: D1 + 2a full unification.** Service-layer expansion, single `task_id_scope: list[str] | None` on `ListTasksRepoQuery`. Replaces `project_ids`. Shared `expand_scope` function lives at service layer (exact module TBD — Claude's discretion).

**Helper placement question becomes trivial:** helper lives in service layer, specific module is a planner-level detail.

---

## Area 3 — `$inbox` consumption path

Straightforward after the architectural decision.

| Option | Description | Selected |
|---|---|---|
| A: Extend `resolve_inbox` to 3-arg | `resolve_inbox(in_inbox, project, parent)`. Single consolidation site. | ✓ |
| B: Generalize to N refs | `resolve_inbox_refs(in_inbox, {...})`. Scales abstractly. | |
| C: Sibling method | `resolve_inbox_for_parent` runs before `resolve_inbox`. | |

**User's choice:** Option A.

**Reasoning:** Matches the "single code path" principle just locked. Minimal signature change. Contradiction rules centralized.

---

## Area 4 — project_ids unification (the pivotal follow-on)

Already resolved above via the 2a decision. Recap:

| Option | Description | Selected |
|---|---|---|
| 2a: Full unification | Rewrite `_resolve_project` to produce `task_id_scope`; retire `project_ids`. One scope primitive. | ✓ |
| 2b: Parent-only D1 | Add `task_id_scope` for parent only. Keep `project_ids` as-is. | |
| 2c: Let me think | Dig further before committing. | |

**User's choice:** 2a (confirmed independent of Claude's reasoning).

**User's framing:** "The perf cost was spent to buy unification. 2b completely goes against the whole idea."

---

## Area 5 — Plan-wave decomposition

**Claude's framing:** 3 plans (unification / filter surface / warnings) vs 2 plans vs 1 plan.

**User's correction:** Out of scope for discuss-phase. Plan decomposition is `/gsd-plan-phase`'s job.

**Action taken:** Saved to memory (`feedback_discuss-vs-plan-scope.md`) to avoid this conflation in future sessions. Deferred to the next workflow phase.

---

## Claude's Discretion (deferred to planner)

- Exact module path for the shared expansion function.
- Final field name for the unified scope primitive.
- How `resolve_inbox` encodes its 3-arg return tuple.
- Type of `accept_entity_types` parameter (set vs enum vs boolean).
- Test file organization.

---

## Deferred Ideas

- Plan-wave decomposition (Area 5) → `/gsd-plan-phase`.
- `folder` scope filter (natural future extension of D1 unification) → v1.5+.
- SQL recursive-CTE push-down for HybridRepository → future perf optimization only if needed.
- Array-of-references on `parent` → future extension driven by real agent pain.
- REQUIREMENTS.md UNIFY-06 wording update → planner's call on when.

---

## Principles saved to memory during this discussion

1. **`feedback_maintainability-over-micro-perf.md`** — single code paths > millisecond wins; divergent implementations are the real pain.
2. **`feedback_discuss-vs-plan-scope.md`** — `/gsd-discuss-phase` captures design decisions only; task decomposition is `/gsd-plan-phase` territory.

---

*End of discussion log.*
