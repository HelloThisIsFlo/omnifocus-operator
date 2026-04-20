# Phase 57: Parent Filter & Filter Unification — Context

**Gathered:** 2026-04-20
**Status:** Ready for planning
**Source:** Interactive discuss-phase against `.research/updated-spec/MILESTONE-v1.4.1.md` + `MILESTONE-v1.4.1.interview-notes.md`. Four of five planned gray areas explored; plan-wave decomposition deferred to `/gsd-plan-phase` per workflow boundary.

<domain>
## Phase Boundary

**In scope (20 REQs)** — the full scope-filter unification + new parent filter surface:

- `parent` filter on `list_tasks` (PARENT-01..09) — single-reference name/ID filter, same three-step resolver as every other entity reference, subtree retrieval with conditional anchor injection.
- Filter unification architecture (UNIFY-01..06) — `project` and `parent` share ONE expansion function, parameterized by accepted entity-type-set. Both surface filters converge on the same repo-query primitive.
- Warnings (WARN-01..05) — filtered-subtree (locked verbatim text), parent-resolves-to-project, parent+project combined; multi-match and inbox-name-substring reused from existing infrastructure.

**Explicitly out of scope** — everything Phase 56 closed (task property surface, preferences, cache read paths, hierarchy include group expansion). Not mentioned in this discussion.

**Scope expansion beyond spec's "additive" framing** — this phase refactors the existing `project` filter on `ListTasksRepoQuery` to converge with the new `parent` filter on a unified primitive. This is broader than "strictly additive" but is load-bearing for UNIFY-01 ("same core mechanism"). Rationale captured under Decisions below.

</domain>

<decisions>
## Implementation Decisions

> Every item below is **locked** in this discussion. Planner MUST NOT re-derive these.

### Architectural placement — D1: service-layer full expansion

**D-01**: Subtree/scope-expansion logic lives at the **service layer**, not the repo layer. The repo receives flat, fully-resolved primitive filter parameters and applies them with simple set-membership semantics.

**D-02**: A single expansion function — parametrized by `accept_entity_types` — serves both `project` and `parent` filters. Differences between the two surface filters are captured as function parameters:
  - **Accepted entity types:** `project` accepts only projects; `parent` accepts projects AND tasks.
  - **Anchor inclusion:** when the resolved ref is a task, the task itself is included in the result set; when the ref is a project, no anchor is emitted (projects are not `list_tasks` rows).
  - Both behaviors live **inside** the shared function, gated on the resolved entity's type — not in separate wrappers.

**D-03**: Service-layer placement is justified on architectural-consistency grounds, not perf-convenience:
  - Matches the existing `<noun>Filter` → primitive resolution pattern (model-taxonomy.md line 131-133 — "the filter object itself doesn't appear on the repo query"). `DateFilter` is the canonical precedent.
  - Matches "Repository returns data by primitive criteria; service does domain logic" DDD separation.
  - Keeps the repo ignorant of OmniFocus parent-child hierarchy semantics — storage layer shouldn't need to know what a subtree is.
  - Honors the `Maintainability over micro-perf` principle — single code path for all scope filters, no divergent implementations across repos.

### Spec deviations — reconciliation with interview intent

**D-04**: UNIFY-04 wording ("filter logic lives at the repo layer") is **reinterpreted**. The interview notes explicitly framed unification as "ONE shared mechanism" with conditional anchor injection "inside the shared function" (session 2 line 69-70) and "the shared filter entry... serves both `project` and `parent`" (session 3 line 161). Session 2's cost estimate (line 185) framed the fast-path verdict as "all filtering moves to domain layer" (= `service/domain.py`). The final spec drifted to "repo layer" wording which under-specified the unification intent; the service-layer expansion realizes the interview intent more faithfully.

**D-05**: UNIFY-06 wording (`ListTasksRepoQuery` gains `parent_ids: list[str] | None`) is **superseded**. The new primitive unifies both scope filters:
  - **Field name (provisional):** `task_id_scope: list[str] | None`. Final name is a planner choice; the contract is "flat ID set that tasks must be a member of."
  - The existing `project_ids: list[str] | None` field is **retired** from `ListTasksRepoQuery`. `_resolve_project()` is rewritten to produce the expanded scope set and merge into `task_id_scope`.
  - **When both filters present:** service intersects the two scope sets before dispatch (`scope_from_project & scope_from_parent`) — correct AND-composition semantics. Repo applies a single set-membership filter.
  - `WARN-03` (parent+project combined) still fires as a soft hint at the service layer independent of the mechanical intersection.

**D-06**: The perf budget from Spike 2 (p95 ≤ 1.30ms at 10K — 77× under threshold) was spent intentionally to buy the one-code-path unification. Accepting service-layer Python expansion without also collecting the unification benefit (2b) is not acceptable — it pays the cost without cashing the return. This principle was locked in session 4 on the preferences-path decision (interview notes line 116: "architectural consistency beats micro-optimization") and applies identically here.

### Repo query shape

**D-07**: `ListTasksRepoQuery` adds ONE new primitive field for scope filtering. Existing `project_ids` is retired. No `parent_task_ids`/`parent_project_ids` split — rejected as it would introduce the exact cross-repo divergence the maintainability principle forbids.

**D-08**: The repo's filter application is trivial set membership:
  - `HybridRepository`: `WHERE t.persistentIdentifier IN (?, ?, ...)` — indexed, AND-composes with all other WHERE clauses naturally.
  - `BridgeOnlyRepository`: `items = [t for t in items if t.id in scope_set]` — identical shape to existing `project_ids` Python filter, just with the new field name.

### `$inbox` consumption

**D-09**: `Resolver.resolve_inbox()` extends to 3-arg: `resolve_inbox(in_inbox, project, parent)`. Single consolidation site for all `$inbox` semantics and contradiction rules. Returns a tuple conveying (effective_in_inbox, remaining_project_to_resolve, remaining_parent_to_resolve). `parent: "$inbox"` is consumed identically to `project: "$inbox"`; `parent: "$inbox" + inInbox=false` raises the same contradiction error as the project equivalent. Mirrors the one-code-path principle at the inbox resolution layer.

### Parent filter surface contract

**D-10**: `ListTasksQuery` gains `parent: Patch[str]` (single-reference, name substring or ID). Array-of-references explicitly rejected at validation time (PARENT-09) — deferred as future extension driven by real agent pain, not speculative flexibility.

**D-11**: Resolution cascade for `parent` reuses the existing `Resolver._resolve(value, accept=[EntityType.PROJECT, EntityType.TASK])` — already implemented and used by `resolve_container`. Three-step cascade (`$` prefix → exact ID → substring name match) works unmodified.

**D-12**: Anchor injection behavior:
  - Resolved ref is a task → task itself is included in the scope set (`scope_set.add(task_id)` then `scope_set |= descendants`).
  - Resolved ref is a project → only project's task descendants are added (the project is not a row in `list_tasks`).
  - Both behaviors live inside the shared expansion function, branching on the resolved entity's type.

### Warnings

**D-13**: Three new warnings land in the domain layer (`service/domain.py`), constants defined in `agent_messages/warnings.py`:
  - **Filtered-subtree warning (WARN-01)** — locked verbatim text (see canonical refs). Fires when `project` or `parent` is combined with any other filter.
  - **Parent-resolves-to-project warning (WARN-02)** — soft "consider using `project`" hint. Fires only when ALL matches of a `parent` reference resolve to projects (not when mixed). Pedagogical tone, not punitive.
  - **Parent+project combined warning (WARN-03)** — soft hint for the rare case of both filters specified together. Fires independent of whether the scope-set intersection is empty or not.

**D-14**: Two existing warnings are reused without new code paths:
  - **Multi-match (WARN-05)** — existing `DomainLogic.check_filter_resolution()` already emits `FILTER_MULTI_MATCH` for any entity-type substring match. Works for `parent` with no modification.
  - **Inbox-name-substring (WARN-05)** — existing `LIST_TASKS_INBOX_PROJECT_WARNING` triggered via `_check_inbox_project_warning()`. Parallel check needed for `parent` matching the inbox name; one new method call in the pipeline, no new warning constant.

### Anchor-semantics invariant (cross-filter equivalence)

**D-15**: UNIFY-02 ("same entity resolved via either filter produces identical results") must be proven by contract test. Under D1 this is trivially satisfied because both `project` and `parent` route through the same expansion function, but the test still locks the contract: `list_tasks(project: "X")` and `list_tasks(parent: "X")` where X resolves to the same project must return byte-identical task lists (anchors differ: project resolution injects no anchor, so the lists collapse identically when the only difference is a would-be-anchor that doesn't exist).

### Naming

**D-16**: Field naming finalization is a planner-level choice. Provisional names used in this context:
  - `task_id_scope: list[str] | None` on `ListTasksRepoQuery` — the unified scope primitive.
  - `expand_scope(ref_id, snapshot, accept_entity_types) -> set[str]` — the shared expansion function (provisional signature).
  - `_resolve_parent()` — the service pipeline step mirroring `_resolve_project()`.
  - The `expand_scope` function may live in `service/subtree.py`, `service/scope.py`, or as a method on `DomainLogic` — planner's call.

### Claude's Discretion

- Exact module path for the shared expansion function (new `service/subtree.py` vs `service/scope.py` vs method on `DomainLogic`). Dedicated module slightly preferred for testability, but method-on-DomainLogic is acceptable given the scope-resolution neighborhood in `domain.py`.
- Final field name for the unified scope primitive (`task_id_scope` is provisional).
- Test file organization for the cross-filter equivalence test (tests/service/ vs tests/contracts/).
- How `resolve_inbox` returns its 3-arg tuple (positional vs named tuple vs small dataclass). Planner chooses based on readability.
- Whether to introduce the `accept_entity_types` parameter as a typed enum/set vs a positional boolean flag. Contract is "accept only projects" vs "accept projects and tasks."

### Scope creep routed to deferred

- Plan-wave decomposition surfaced as a candidate gray area; deferred to `/gsd-plan-phase` per workflow boundary (see Deferred Ideas).

</decisions>

<specifics>
## Specific Ideas

- **Interview intent precedence rule.** When the milestone spec's wording diverges from interview-notes intent and the spec wording is ambiguous, the interview notes win as the higher-fidelity design record. Applied twice in this discussion: UNIFY-04 "repo layer" → reinterpreted per session 2 notes; UNIFY-06 `parent_ids` → superseded per "ONE shared mechanism" framing. CONTEXT.md elevates `MILESTONE-v1.4.1.interview-notes.md` to a canonical ref alongside the milestone spec so downstream agents (planner, researcher) have access to both records.
- **"The perf cost was spent to buy unification."** The user's framing of Spike 2's verdict: accepting Python-filter cost at the service layer was justified *by* the unification goal. Retaining divergent repo implementations (option 2b) would spend the cost without collecting the benefit. This framing is canonical and will inform future scope-filter decisions (e.g., if a `folder` filter ever lands in v1.5+).
- **`compute_true_inheritance()` precedent.** Service-layer ancestor-chain walking already exists in `DomainLogic` (lines 484-620 of `docs/architecture.md`). The new `expand_scope` function has a natural neighbor there — parent-chain walking is an existing service-layer capability; subtree-descending is its symmetric counterpart.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.** Paths are relative to repo root; group by topic.

### Full design spec + intent record (source of truth — BOTH docs required)

- `.research/updated-spec/MILESTONE-v1.4.1.md` — full design contract for v1.4.1. Phase 57 is the parent-filter + unification half. Notable deviations from literal spec wording captured in decisions D-04 / D-05 above.
- `.research/updated-spec/MILESTONE-v1.4.1.interview-notes.md` — higher-fidelity design-intent record. Session 2 (line 67-73): filter unification as "ONE shared mechanism" with anchor injection "inside the shared function." Session 3 (line 161): "shared filter entry... serves both `project` and `parent`." Session 4 (line 116): "architectural consistency beats micro-optimization" — locked principle applied again in Phase 57. **Read this before the main spec when there is any ambiguity about filter-unification architecture.**
- `.research/deep-dives/v1.4.1-filter-benchmark/FINDINGS.md` — Spike 2 evidence: p95 ≤ 1.30ms at 10K. Confirms perf is a non-factor; Python-filter pipeline at service layer is comfortably under all viability thresholds.

### Architecture & conventions (MANDATORY reading before implementation)

- `docs/architecture.md` — especially:
  - "Service Layer: Product Decisions vs Plumbing" (lines 210-239). Filter resolution warnings are domain; `Building ListTasksRepoQuery from resolved values` and `Name → ID resolution with fuzzy matching` are pipeline/resolve — mechanical plumbing.
  - "Structure Over Discipline" (lines 657-669). Prefer uniform code paths; make module boundaries self-documenting.
  - "True Inheritance Principle" (lines 484-620). Precedent for service-layer ancestor-chain walking in `DomainLogic`.
  - "Dumb Bridge, Smart Python" (lines 364-404). Clarifies that smart-Python *service* layer ≠ smart-*bridge* layer; service is where domain logic belongs.
- `docs/model-taxonomy.md` — especially:
  - "Read-side models" (lines 102-142). `<noun>Filter` → primitive pattern ("the filter object itself doesn't appear on the repo query").
  - `DateFilter` is the canonical precedent for service-resolves-into-primitives.
- `CLAUDE.md` — safety rules (SAFE-01/02: no RealBridge in automated tests), service-layer Method Object pattern.

### Service layer (primary implementation target)

- `src/omnifocus_operator/service/resolve.py` — extend `resolve_inbox()` to 3-arg (D-09). `Resolver._resolve(value, accept=[...])` at line 72-111 is the existing three-step cascade that `parent` reuses unmodified (D-11). `resolve_filter()` at line 243-269 is the substring cascade used by the existing `_resolve_project` and reused for parent resolution.
- `src/omnifocus_operator/service/service.py` — `_ListTasksPipeline` at line 372-473 is the pipeline to extend. `_resolve_project()` at line 408-419 is the method to rewrite (D-05). New `_resolve_parent()` method mirrors its shape. `_build_repo_query()` at line 440-464 is where the new `task_id_scope` field assembly lands.
- `src/omnifocus_operator/service/domain.py` — `DomainLogic.check_filter_resolution()` at line 500-538 already handles multi-match / no-match warnings for any entity type; works for `parent` unmodified (D-14). New warnings (WARN-01, WARN-02, WARN-03) land here as new methods or in the pipeline directly.
- New home for the shared expansion function: `service/subtree.py` or `service/scope.py` (provisional — D-16 Claude's Discretion).

### Repository layer (touched minimally — just field rename + simple WHERE clause)

- `src/omnifocus_operator/repository/hybrid/query_builder.py` — `build_list_tasks_sql()` at line 233-318. The existing `project_ids` block at line 258-265 gets rewritten to use the new `task_id_scope` field with a simpler `WHERE persistentIdentifier IN (...)` clause. AND-composition with other filters unchanged.
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` — `list_tasks()` at line 214-256. The existing `project_ids` block at line 227-229 gets rewritten to filter by `task_id_scope` with the same shape (set-membership on `t.id`).

### Contracts (input models)

- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` — `ListTasksQuery` at line 69-119 (add `parent: Patch[str]` — D-10). `ListTasksRepoQuery` at line 122-148 (add `task_id_scope: list[str] | None`, retire `project_ids` — D-05/D-07). `_PATCH_FIELDS` list at line 52-66 needs `parent` added.
- `src/omnifocus_operator/agent_messages/descriptions.py` — new `PARENT_FILTER_DESC` constant for the agent-facing field description.
- `src/omnifocus_operator/agent_messages/warnings.py` — new `FILTERED_SUBTREE_WARNING` (locked verbatim text from spec), `PARENT_RESOLVES_TO_PROJECT_WARNING`, `PARENT_PROJECT_COMBINED_WARNING` constants.

### Filtered-subtree warning — locked verbatim text

From `MILESTONE-v1.4.1.md` line 180:

> "Filtered subtree: resolved parent tasks are always included, but intermediate and descendant tasks not matching your other filters (tags, dates, etc.) are excluded. Each returned task's `parent` field still references its true parent — fetch separately if you need data for an excluded intermediate."

Text is locked — do not paraphrase or adjust wording.

### Tests

- `tests/test_output_schema.py` — MUST run after any contract model change (per project `CLAUDE.md`).
- `tests/service/` — new tests for `_resolve_parent()`, `resolve_inbox()` 3-arg signature, cross-filter equivalence (UNIFY-02, D-15).
- `tests/contracts/use_cases/list/` — tests for `ListTasksQuery` new `parent` field validation (single-reference only, PARENT-09).
- `tests/repository/hybrid/` + `tests/repository/bridge_only/` — existing `project_ids` tests migrate to `task_id_scope` (mechanical rename + new expected SQL shape).
- Golden master captures do NOT need re-take — results are invariant under D1 (UNIFY-02 guarantees byte-identical results for same-entity resolutions; the refactor is internal query shape only).

### REQUIREMENTS.md traceability

- `.planning/REQUIREMENTS.md` lines 44-61 (PARENT-01..09, UNIFY-01..06). **Wording note**: UNIFY-06 ("`ListTasksRepoQuery` gains `parent_ids: list[str] | None`") is superseded by this phase's D-05 decision. Planner should decide whether to rewrite REQUIREMENTS.md UNIFY-06 now or leave the spec-vs-implementation delta until the phase ships.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets

- **`Resolver._resolve(value, accept=[EntityType.PROJECT, EntityType.TASK])`** — three-step cascade for `$`-prefix / exact ID / substring name match. Already accepts project+task (used by `resolve_container`). `parent` filter uses it unmodified.
- **`Resolver.resolve_filter(value, entities)`** — substring/ID cascade returning list of matching IDs. Existing use: `_resolve_project`. Parent uses it with a combined `[*projects, *tasks]` collection — the classification of resolved IDs as task-vs-project happens by set membership against the snapshot's task IDs.
- **`Resolver.resolve_inbox(in_inbox, project)`** at line 217-239 — existing 2-arg signature consuming `$inbox` from the project filter. Extends to 3-arg for parent (D-09).
- **`DomainLogic.check_filter_resolution(value, resolved_ids, entities, entity_type)`** at line 500-538 — existing multi-match / no-match / did-you-mean warning generator. Entity-type-agnostic; works for `parent` unmodified (D-14).
- **`LIST_TASKS_INBOX_PROJECT_WARNING`** constant at `agent_messages/warnings.py` line 171-175 — existing inbox-name-substring warning. Parent equivalent adds one pipeline method call, no new constant.
- **`paginate()`** helper at `repository/pagination.py` — unchanged, handles the flat result set after scope filtering.

### Established patterns

- **`<noun>Filter` → primitive resolution pattern** — service resolves complex nested inputs (e.g., `DateFilter` → `due_after`/`due_before`) into flat primitive repo query fields. Parent filter follows this exactly: agent-facing `parent: str` → service-resolved `task_id_scope: list[str]`.
- **Method Object pattern** for service use cases (`docs/architecture.md` lines 177-208). `_ListTasksPipeline` already follows this; new `_resolve_parent` and `expand_scope` steps attach as additional private methods.
- **Strip-when-false for output, not input** — no change here; scope filter is input-only.
- **AND-composition of filter dimensions** — every filter in `ListTasksRepoQuery` today AND-composes naturally (strict AND at `query_builder.py:296`). `task_id_scope` slots in as one more AND-ed condition. `parent` + `project` both specified produces an intersection of scope sets at the service layer, then a single AND clause at the repo.

### Integration points

- **FastMCP tool registration** — `server.py`: `list_tasks` tool. Adding `parent` field doesn't require new registration; Pydantic/FastMCP picks up the new field from `ListTasksQuery`.
- **Outline ordering** — existing SQL data query at `query_builder.py:302` already `ORDER BY o.sort_path, t.persistentIdentifier`. Parent scope filtering doesn't change ordering; the subtree result comes back in outline order naturally because outline order is determined by the CTE, not the filter.
- **Pagination** — existing `limit` + `offset` mechanism (line 305-318 of query_builder.py). Unchanged; scope filter produces a flat result set that paginates like any other filter combination.

</code_context>

<deferred>
## Deferred Ideas

### Plan-wave decomposition

Surfaced as a candidate gray area in this discussion, then correctly deferred to `/gsd-plan-phase` per workflow boundary. The planner decides how to split this phase's work into plans (1/2/3 plans, in what order, what dependencies).

### `folder` scope filter

Mentioned during the architectural analysis as a natural future extension. Under the D1 unification, adding `folder` is ~10 lines in the service's shared expansion function (extend the accept-entity-types set) and zero lines in the repo. Not part of Phase 57 or v1.4.1.

### SQL recursive-CTE push-down for HybridRepository

Spike 2's findings (line 302) flagged a recursive-CTE prototype at `.research/deep-dives/v1.4.1-filter-benchmark/experiments/sql_parent_filter.py` as a future opportunistic optimization for HybridRepository. Under D1 this optimization gets harder (service pre-expands, so HybridRepository would have to bypass the expansion for parent specifically). **Not worth pursuing unless perf becomes a concern at larger scales** — per the maintainability principle, the uniform path wins.

### Array of references on `parent` filter

PARENT-09 rejects this explicitly. Future extension driven by real agent pain, not speculative flexibility. Not Phase 57, not v1.4.1.

### REQUIREMENTS.md UNIFY-06 wording update

D-05 supersedes UNIFY-06's literal wording (`parent_ids: list[str] | None`). Planner should decide whether to update REQUIREMENTS.md proactively or leave the delta visible until the phase ships. Either is defensible.

### Array-of-references, `folder` filter, recursive-CTE push-down

All captured under Future Requirements in `REQUIREMENTS.md` lines 155-160. No new deferrals added by this discussion.

</deferred>

---

*Phase: 57-parent-filter-filter-unification*
*Context gathered: 2026-04-20*
