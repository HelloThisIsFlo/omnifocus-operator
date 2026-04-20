# Phase 57: Parent Filter & Filter Unification — Research

**Researched:** 2026-04-20
**Domain:** `list_tasks` service pipeline + filter-unification refactor on `ListTasksRepoQuery`
**Confidence:** HIGH (architectural path fully locked in CONTEXT.md; research is codebase-grounded, not library-lookup)

## Summary

Phase 57 is a **refactor-plus-feature** phase. It adds a new `parent` surface filter to `list_tasks` (PARENT-01..09), then takes the opportunity to unify `project` and `parent` on a single repo-layer primitive (`task_id_scope`) by retiring the existing `project_ids` field (UNIFY-01..06). The mechanical expansion of subtrees runs at the **service layer** inside a shared `expand_scope()` helper — not at the repo layer — because Spike 2 confirmed Python filtering at 10K is 77× under the viability threshold (p95 ≤ 1.30ms), and the "shared mechanism" intent (interview notes session 2 line 67-73) is realized most faithfully by one service-layer code path instead of divergent repo implementations. Three new warnings land in the domain layer (FILTERED_SUBTREE, PARENT_RESOLVES_TO_PROJECT, PARENT_PROJECT_COMBINED). Two existing warnings (multi-match, inbox-name-substring) are reused verbatim.

The refactor touches **~9 production files** and **~5 test files**. All `project_ids` references in prod + tests migrate to `task_id_scope`; the contract-parity test (`test_list_contracts.py::TestRepoQueryFieldParity`) must be updated because its `repo_only` set currently hard-codes `project_ids`. No golden-master re-capture needed — the refactor is internal query shape only (UNIFY-02 guarantees byte-identical output for same-entity resolutions).

**Primary recommendation:** Split this phase into 3 plans executed sequentially:
1. **Contract + repo primitive rename** — `project_ids` → `task_id_scope` on `ListTasksRepoQuery`, mechanical repo + test migration, no behavior change yet (`project` filter still works end-to-end via rewritten `_resolve_project`).
2. **`expand_scope` helper + `parent` filter surface** — new `service/subtree.py` with `expand_scope(ref_id, snapshot, accept_entity_types) -> set[str]`, new `ListTasksQuery.parent` field, `_resolve_parent` pipeline step, `resolve_inbox` 3-arg extension, contradiction tests, cross-filter equivalence contract test.
3. **Warnings surface** — three new constants in `agent_messages/warnings.py`, three new `DomainLogic` methods (or pipeline-level sites), wire into `_ListTasksPipeline`, add agent-facing description, surface in tool docs.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Service-layer full expansion.** Subtree/scope-expansion lives at the service layer, not the repo layer. The repo receives flat, fully-resolved primitive filter parameters and applies them with simple set-membership semantics.

**D-02 — Single shared expansion function.** Parametrized by `accept_entity_types`, serves both `project` and `parent`. Differences captured as function parameters:
  - `project` accepts only projects; `parent` accepts projects AND tasks.
  - Anchor inclusion: resolved ref is a task → task itself included; resolved ref is a project → no anchor.
  - Both behaviors live **inside** the shared function, gated on the resolved entity's type.

**D-03 — Architectural-consistency justification.** Service-layer placement matches the existing `<noun>Filter` → primitive pattern (model-taxonomy.md:131-133), matches DDD "repository returns data by primitive criteria" separation, keeps the repo ignorant of parent-child hierarchy semantics, and honors `Maintainability over micro-perf`.

**D-04 — UNIFY-04 wording reinterpreted.** Spec text "filter logic lives at the repo layer" is superseded by interview intent ("ONE shared mechanism", anchor injection "inside the shared function"). Service-layer expansion realizes unification more faithfully.

**D-05 — Unified repo primitive.** `ListTasksRepoQuery` gains one new field: `task_id_scope: list[str] | None` (provisional name). Existing `project_ids: list[str] | None` is **retired**. `_resolve_project()` is rewritten to produce the expanded scope set and merge into `task_id_scope`. When both `project` + `parent` filters are present, service intersects scope sets before dispatch (AND semantics).

**D-06 — Perf budget was spent to buy unification.** Accepting service-layer Python cost without the unification benefit is not acceptable.

**D-07 — Exactly ONE new field on the repo query.** No `parent_task_ids` / `parent_project_ids` split — that would introduce the cross-repo divergence maintainability forbids.

**D-08 — Repo applies trivial set membership.**
  - `HybridRepository`: `WHERE t.persistentIdentifier IN (?, ?, ...)` — indexed, AND-composes naturally.
  - `BridgeOnlyRepository`: `items = [t for t in items if t.id in scope_set]`.

**D-09 — `resolve_inbox` extends to 3-arg.** `resolve_inbox(in_inbox, project, parent) -> (effective_in_inbox, remaining_project, remaining_parent)`. Single consolidation site for all `$inbox` semantics and contradiction rules. `parent: "$inbox"` consumed identically to `project: "$inbox"`; `parent: "$inbox" + inInbox=false` raises same contradiction.

**D-10 — `parent: Patch[str]` single reference.** Array-of-references rejected at validation (PARENT-09). Future extension driven by real agent pain.

**D-11 — Resolver reuse.** `parent` uses existing `Resolver._resolve(value, accept=[EntityType.PROJECT, EntityType.TASK])` — already used by `resolve_container`. Three-step cascade works unmodified.

**D-12 — Anchor injection behavior.**
  - Resolved ref is a task → `scope_set.add(task_id)` then `scope_set |= descendants`.
  - Resolved ref is a project → only project's task descendants are added.
  - Both behaviors live inside the shared function, branching on resolved entity's type.

**D-13 — Three new domain-layer warnings.**
  - FILTERED_SUBTREE (WARN-01) — locked verbatim text.
  - PARENT_RESOLVES_TO_PROJECT (WARN-02) — soft "consider using `project`" hint. Fires only when ALL matches are projects (not when mixed).
  - PARENT_PROJECT_COMBINED (WARN-03) — soft hint when both specified.

**D-14 — Two existing warnings reused.**
  - `DomainLogic.check_filter_resolution()` already handles multi-match for any entity type (WARN-05). Works for `parent` unmodified.
  - `LIST_TASKS_INBOX_PROJECT_WARNING` reused — parent equivalent needs one new pipeline method call, no new constant.

**D-15 — Cross-filter equivalence proven by contract test.** `list_tasks(project: X)` and `list_tasks(parent: X)` where X resolves to the same project must return byte-identical task lists.

**D-16 — Planner-level naming choices.**
  - `task_id_scope` field name is provisional.
  - `expand_scope()` signature is provisional.
  - `_resolve_parent()` method name mirrors `_resolve_project()`.
  - Module path (`service/subtree.py` vs `service/scope.py` vs `DomainLogic` method) is planner's call.

### Claude's Discretion

- Exact module path for the shared expansion function (`service/subtree.py` / `service/scope.py` / `DomainLogic` method).
- Final field name for the unified scope primitive.
- Test file organization for cross-filter equivalence.
- `resolve_inbox` 3-arg return shape (tuple vs namedtuple vs small dataclass).
- Whether `accept_entity_types` is a typed set/enum vs positional boolean.

### Deferred Ideas (OUT OF SCOPE)

- Plan-wave decomposition (routed to `/gsd-plan-phase`).
- `folder` scope filter (~10 lines in `expand_scope`, zero repo changes — not v1.4.1).
- SQL recursive-CTE push-down for HybridRepository (gets harder under D1, deferred per maintainability rule).
- Array of references on `parent` (PARENT-09 rejects).
- REQUIREMENTS.md UNIFY-06 wording update (defensible to update or leave).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PARENT-01 | `list_tasks` accepts `parent` filter (single reference, name or ID) | §Standard Stack → `Patch[str]` field on `ListTasksQuery`; §Architecture Patterns → Pattern 2 |
| PARENT-02 | Three-step resolver (`$` prefix → exact ID → name substring) | Reuses `Resolver._resolve(value, accept=[EntityType.PROJECT, EntityType.TASK])` unmodified (D-11) |
| PARENT-03 | Returns all descendants at any depth; project-case matches existing `project` filter | `expand_scope()` branches on entity type (D-12); project branch reuses existing project-members query shape |
| PARENT-04 | Resolved task = anchor; resolved project = no anchor | D-12 inside `expand_scope()`: `scope_set.add(task_id)` when task, skip when project |
| PARENT-05 | AND-composes with all other filters | Unified `task_id_scope` AND-composes naturally at repo layer (existing AND-chain at query_builder.py:296) |
| PARENT-06 | Standard pagination over flat set; outline order preserved | `paginate()` + existing CTE ordering — no changes needed |
| PARENT-07 | `parent: "$inbox"` ≡ `project: "$inbox"` | `resolve_inbox` 3-arg extension (D-09) consumes both identically |
| PARENT-08 | Same contradiction rules as `project: "$inbox"` | Consolidated in extended `resolve_inbox` (D-09) |
| PARENT-09 | Array references rejected at validation | `Patch[str]` type alias constrains to scalar; §Validation Architecture for enforcement detail |
| UNIFY-01 | One shared mechanism | `expand_scope()` per D-02 |
| UNIFY-02 | Byte-identical results cross-filter | Both filters route through `expand_scope()` → `task_id_scope`; §Validation Architecture for proof |
| UNIFY-03 | Conditional anchor injection | D-12 inside `expand_scope()` |
| UNIFY-04 | Scope-expansion at service layer; set-membership at repo | D-01/D-04 reinterpretation; Spike 2 evidence |
| UNIFY-05 | Shared `expand_scope()` used by both `_resolve_project` and `_resolve_parent` pipeline steps | Service layer, returns `set[str]` |
| UNIFY-06 | `task_id_scope` unified primitive; `project_ids` retired | D-05/D-07 |
| WARN-01 | Filtered-subtree warning (verbatim text) | New `FILTERED_SUBTREE_WARNING` constant, new `DomainLogic.check_filtered_subtree()` method |
| WARN-02 | Parent-resolves-to-project warning | New `PARENT_RESOLVES_TO_PROJECT_WARNING`, fires only when ALL parent matches are projects |
| WARN-03 | Parent + project combined warning | New `PARENT_PROJECT_COMBINED_WARNING`, fires when both specified regardless of intersection cardinality |
| WARN-04 | Warnings live in domain layer, not projection | All three new checks are `DomainLogic` methods (or pipeline sites with domain-level semantics) |
| WARN-05 | Multi-match + inbox-name-substring reused | Existing `check_filter_resolution()` works for any entity type unmodified; existing `LIST_TASKS_INBOX_PROJECT_WARNING` reused with one new pipeline call mirroring `_check_inbox_project_warning()` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **SAFE-01**: No automated test, CI, or agent execution may touch the real Bridge. Use `InMemoryBridge` or `SimulatorBridge` only. CI greps for `RealBridge` as a literal — write "the real Bridge" in comments/docstrings. Research tests targeting parent filter use `InMemoryBridge` exclusively.
- **SAFE-02**: `uat/` is excluded from pytest discovery + CI. Never invoke UAT scripts from plans.
- **Method Object pattern**: All service use cases use `_VerbNounPipeline` — `_ListTasksPipeline` already follows this; new `_resolve_parent` step attaches as additional private method.
- **Read delegations stay inline**: not applicable — `list_tasks` is not a read delegation.
- **Before creating any new Pydantic model**: Read `docs/model-taxonomy.md`. `ListTasksQuery` already exists; we add a field, not a new model. `<noun>Filter` → primitive pattern applies (parent filter is a simple `str`, not a nested `ParentFilter` object, so there's no new model to name).
- **After modifying any model that appears in tool output**: Run `uv run pytest tests/test_output_schema.py -x -q`. `ListTasksQuery` is an input model — the test still should pass (the `parent` field becomes part of `list_tasks` inputSchema but the outputSchema is unchanged). `ListTasksRepoQuery` never surfaces to MCP output, so no schema impact.
- **UAT is human-initiated only**: Phase 57 UAT comes after `/gsd-verify-work`; never preempt.
- **Golden master captures are human-only**: Do not touch golden master fixtures. CONTEXT.md confirms no re-take needed.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Agent-facing `parent` field validation | `contracts/` | — | Pydantic `Patch[str]` type + reject_null_filters pre-validator; shape-only rejection is a contract concern (model-taxonomy.md §102-142) |
| `$` prefix + contradiction checking | `service/resolve.py::Resolver.resolve_inbox` | — | Existing inbox normalization lives here; extending to 3-arg keeps consolidation site intact (D-09) |
| Name/ID → entity resolution | `service/resolve.py::Resolver.resolve_filter` | — | Existing substring+ID cascade — reused unmodified per D-11 |
| Subtree/scope expansion | `service/` (new `subtree.py` or `DomainLogic` method) | — | Domain knowledge about parent-child hierarchy belongs at service per D-01/D-03; keeps repo ignorant of OF structure |
| Scope-set intersection (project ∩ parent) | `service/service.py::_ListTasksPipeline._build_repo_query` | — | Pipeline orchestrates the two resolved sets before dispatch (D-05) |
| Multi-match / no-match / did-you-mean warnings | `service/domain.py::DomainLogic.check_filter_resolution` | — | Existing behavior; entity-type-agnostic; works for `parent` unmodified (D-14) |
| Filtered-subtree + parent-resolves-to-project + parent+project warnings | `service/domain.py::DomainLogic` | — | WARN-04 explicitly places all warnings in domain, not projection |
| Set-membership filtering | `repository/` (both repos) | — | Trivial mechanical filter — D-08 |
| Outline ordering + pagination | `repository/` | — | Unchanged — scope filtering is just one more WHERE predicate upstream of ORDER BY + LIMIT |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | Contract models, `Patch[T]` sentinel, field validation | [VERIFIED: `uv pip list`] — already the project's standard for all contracts |
| pytest | 9.0.2 | Test runner | [VERIFIED: `uv pip list`] |
| pytest-asyncio | 1.3.0 | Async pipeline/resolver tests | [VERIFIED: `uv pip list`] |
| fastmcp | ≥3.1.1 | Tool registration auto-picks up `parent` field from `ListTasksQuery` schema | [VERIFIED: `pyproject.toml`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jsonschema | (transitive via `mcp`) | Output-schema validation (`test_output_schema.py`) | Required run after any `ListTasksQuery`/`ListTasksRepoQuery` change per CLAUDE.md |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Service-layer `expand_scope` | Repo-layer `collect_subtree` (original MILESTONE-v1.4.1 UNIFY-05 wording) | REJECTED per D-01/D-04 — would require duplicate implementations in hybrid + bridge_only, violating maintainability; Spike 2 removed the perf argument for repo-layer placement |
| SQL recursive CTE in HybridRepository | Pure Python expansion in service | REJECTED per D-05 — would force a fork between hybrid (SQL CTE) and bridge_only (Python) code paths; defers opportunistic optimization as future work |
| `parent_task_ids` + `parent_project_ids` split on repo query | Single `task_id_scope` | REJECTED per D-07 — two similar scope fields defeat the unification point |
| Nested `ParentFilter` model | Plain `Patch[str]` | CORRECT: parent filter has only one dimension (the reference). No `<noun>Filter` class justification (model-taxonomy.md: filter classes exist for *multi-dimensional* inputs like `DateFilter`) |

**Installation:** No new packages. All dependencies already pinned.

**Version verification:** [VERIFIED: `uv pip list` on 2026-04-20] — no package upgrades needed.

## Architecture Patterns

### System Architecture Diagram

```
Agent JSON input (list_tasks with parent: "Work")
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│ Contracts Layer: ListTasksQuery (Pydantic)                  │
│   - extra="forbid" rejects unknown fields                   │
│   - Patch[str] type rejects arrays (PARENT-09)              │
│   - reject_null_filters rejects null                        │
└──────────────────────────────────────────────────────────────┘
      │ validated ListTasksQuery
      ▼
┌──────────────────────────────────────────────────────────────┐
│ Service Layer: _ListTasksPipeline.execute()                 │
│                                                              │
│   1. asyncio.gather(list_tags, list_projects)               │
│                                                              │
│   2. resolve_inbox(in_inbox, project, parent)               │
│      ─→ (effective_in_inbox, proj_remaining, parent_remain) │
│      ─→ `$inbox` consumed → in_inbox=True, that arg=None    │
│      ─→ contradictions raise                                │
│                                                              │
│   3. _check_inbox_project_warning()                         │
│   4. _check_inbox_parent_warning()  [NEW mirror]            │
│                                                              │
│   5. _resolve_project()                                     │
│      resolve_filter(proj, projects)   [existing 3-step]     │
│      ─→ resolved_project_ids: list[str]                     │
│      ─→ emit multi-match / did-you-mean warnings            │
│                                                              │
│   6. _resolve_parent()  [NEW]                               │
│      resolve_filter(par, [*projects, *tasks])               │
│      ─→ resolved_parent_ids: list[str]                      │
│      ─→ emit multi-match / did-you-mean warnings            │
│      ─→ emit PARENT_RESOLVES_TO_PROJECT if all-projects     │
│                                                              │
│   7. expand_scope()  [NEW — shared helper]                  │
│      ─→ project scope set (project_ids → descendants)       │
│      ─→ parent scope set (resolved IDs → per-type branch)   │
│      ─→ intersect when both present                         │
│                                                              │
│   8. _resolve_tags(), _resolve_date_filters()               │
│                                                              │
│   9. _build_repo_query() — assemble ListTasksRepoQuery with │
│      task_id_scope=list(intersected_set) [NEW]              │
│                                                              │
│  10. emit FILTERED_SUBTREE if (project|parent) + other filt │
│  11. emit PARENT_PROJECT_COMBINED if both set               │
└──────────────────────────────────────────────────────────────┘
      │ ListTasksRepoQuery (resolved primitives only)
      ▼
┌──────────────────────────────────────────────────────────────┐
│ Repository Layer                                             │
│                                                              │
│  HybridRepository.list_tasks:                               │
│    WHERE t.persistentIdentifier IN (?, ?, ...)              │
│    ─→ indexed, AND-composes with all other conditions       │
│                                                              │
│  BridgeOnlyRepository.list_tasks:                           │
│    items = [t for t in items if t.id in scope_set]          │
└──────────────────────────────────────────────────────────────┘
      │ ListRepoResult[Task]
      ▼
 Service enriches: compute_true_inheritance → enrich_presence_flags → ListResult[Task]
```

### Recommended Project Structure

The refactor is in-place — no new directory. Minor additions:

```
src/omnifocus_operator/
├── service/
│   ├── service.py           # _ListTasksPipeline extended (+_resolve_parent, +intersection step)
│   ├── resolve.py           # resolve_inbox → 3-arg
│   ├── domain.py            # +check_filtered_subtree, +check_parent_resolves_to_project,
│   │                        #  +check_parent_project_combined (or pipeline-level sites)
│   └── subtree.py           # NEW — expand_scope(ref_id, snapshot, accept_entity_types)
│                            # OR make it a method on DomainLogic (D-16 Claude's Discretion)
├── contracts/use_cases/list/
│   └── tasks.py             # ListTasksQuery +parent; ListTasksRepoQuery: -project_ids +task_id_scope
└── agent_messages/
    ├── descriptions.py      # +PARENT_FILTER_DESC
    └── warnings.py          # +FILTERED_SUBTREE_WARNING, +PARENT_RESOLVES_TO_PROJECT_WARNING,
                             #  +PARENT_PROJECT_COMBINED_WARNING
```

**Module placement recommendation (Claude's Discretion per D-16):** Create `service/subtree.py` as a dedicated module. Arguments for a dedicated module over a `DomainLogic` method:

- **Testability** — a free function is trivially unit-testable without a `DomainLogic` fixture.
- **Symmetry** — `compute_true_inheritance()` walks the ancestor chain (up); `expand_scope()` walks the descendant subtree (down). They're symmetric operations. The ancestor walk is already a method on `DomainLogic` because it needs `self._repo.get_all()` for snapshot loading. The descendant walk does NOT need `self._repo`: the caller (`_ListTasksPipeline`) already has the snapshot from the existing `gather(list_tags, list_projects)` and can pass task/project lists to `expand_scope` as arguments. No DI needed, no async, no repo reference — pure function.
- **Locality** — every pipeline consumer is in `service/`, and a dedicated module makes the function's public nature self-evident.
- **Future extension** — when a `folder` scope filter ever lands, it slots into the same module naturally.

Counter-argument for method-on-DomainLogic: `compute_true_inheritance` already lives there as a sibling hierarchy-walking helper. Either is defensible. **Recommendation: dedicated module** because the function is synchronous, snapshot-pure, and has no DI need — forcing it through a class adds ceremony without payoff.

### Pattern 1: `<noun>Filter` → primitive resolution

**What:** Complex agent-facing filter types resolve to flat primitives on the repo query. The filter class (if any) doesn't appear on `RepoQuery`.

**When to use:** Always — this is the standard pattern for list query filters.

**Canonical precedent — `DateFilter`:**
- `ListTasksQuery.due: Patch[DueDateFilter]` — complex nested input
- `ListTasksRepoQuery.due_after: datetime | None`, `due_before: datetime | None` — flat primitives
- Service (`_resolve_date_filters` + `DomainLogic.resolve_date_filters`) does the translation

**`parent` filter mirrors this:**
- `ListTasksQuery.parent: Patch[str]` — agent-facing (single ref; no nested model needed since it's scalar)
- `ListTasksRepoQuery.task_id_scope: list[str] | None` — flat primitive
- Service (`_resolve_parent` + `expand_scope`) does the translation

```python
# Source: .planning/phases/57-parent-filter-filter-unification/57-CONTEXT.md D-05/D-12
# (service/subtree.py — provisional)
from omnifocus_operator.models.enums import EntityType
from omnifocus_operator.models.snapshot import AllEntities

def expand_scope(
    ref_id: str,
    snapshot: AllEntities,
    accept_entity_types: frozenset[EntityType],
) -> set[str]:
    """Expand a resolved entity ID to the set of task IDs it scopes.

    - If `ref_id` resolves to a task AND EntityType.TASK is accepted:
      returns {ref_id} | {all descendant task ids}
    - If `ref_id` resolves to a project AND EntityType.PROJECT is accepted:
      returns {all task ids whose containing project is ref_id at any depth}
    - Caller is responsible for resolution — this function trusts `ref_id`
      and looks up type by set membership against snapshot.tasks / snapshot.projects.
    """
    task_ids = {t.id for t in snapshot.tasks}
    project_ids = {p.id for p in snapshot.projects}

    if ref_id in task_ids and EntityType.TASK in accept_entity_types:
        # Task-as-anchor + descendant collection
        result = {ref_id}
        result |= _collect_task_descendants(ref_id, snapshot.tasks)
        return result

    if ref_id in project_ids and EntityType.PROJECT in accept_entity_types:
        # No anchor (projects aren't list_tasks rows); collect all project members
        return {t.id for t in snapshot.tasks if t.project.id == ref_id}

    # Resolved to an accepted type but entity not in snapshot (rare), or
    # ref_id resolves to a type not in accept_entity_types (shouldn't happen
    # if the resolver did its job). Return empty — repo produces empty result.
    return set()
```

**Descendant collection implementation note:** iterate the snapshot's tasks building a children map once, then BFS/DFS. Spike 2 measured this path at p95 ≤ 1.30ms at 10K.

```python
def _collect_task_descendants(anchor_id: str, tasks: list[Task]) -> set[str]:
    """BFS over the parent.task.id edges. anchor_id is NOT included."""
    children_map: dict[str, list[str]] = {}
    for t in tasks:
        if t.parent.task is not None:
            children_map.setdefault(t.parent.task.id, []).append(t.id)
    result: set[str] = set()
    frontier = [anchor_id]
    while frontier:
        cid = frontier.pop()
        for child_id in children_map.get(cid, []):
            if child_id not in result:
                result.add(child_id)
                frontier.append(child_id)
    return result
```

### Pattern 2: Pipeline step mirroring (`_resolve_project` ≡ `_resolve_parent`)

**What:** Two pipeline steps with identical shape, differing only in `accept_entity_types` and the collection they resolve against.

**Example:**

```python
# Source: service/service.py current _resolve_project + D-11/D-14 for _resolve_parent
class _ListTasksPipeline(_ReadPipeline):
    def _resolve_project(self) -> None:
        self._project_scope: set[str] | None = None
        if self._project_to_resolve is None:
            return
        resolved = self._resolver.resolve_filter(self._project_to_resolve, self._projects)
        self._warnings.extend(
            self._domain.check_filter_resolution(
                self._project_to_resolve, resolved, self._projects, "project"
            )
        )
        if resolved:
            scope: set[str] = set()
            for pid in resolved:
                scope |= expand_scope(pid, self._snapshot, frozenset({EntityType.PROJECT}))
            self._project_scope = scope

    def _resolve_parent(self) -> None:
        self._parent_scope: set[str] | None = None
        if self._parent_to_resolve is None:
            return
        combined = [*self._projects, *self._tasks]
        resolved = self._resolver.resolve_filter(self._parent_to_resolve, combined)
        self._warnings.extend(
            self._domain.check_filter_resolution(
                self._parent_to_resolve, resolved, combined, "parent"
            )
        )
        # WARN-02: fires only when ALL matches are projects
        if resolved and all(rid in {p.id for p in self._projects} for rid in resolved):
            self._warnings.append(PARENT_RESOLVES_TO_PROJECT_WARNING.format(
                value=self._parent_to_resolve
            ))
        if resolved:
            scope: set[str] = set()
            for rid in resolved:
                scope |= expand_scope(
                    rid, self._snapshot,
                    frozenset({EntityType.PROJECT, EntityType.TASK}),
                )
            self._parent_scope = scope
```

**Intersection step in `_build_repo_query`:**
```python
def _build_repo_query(self) -> None:
    # Compose scope sets: AND semantics when both present (D-05)
    task_id_scope: list[str] | None = None
    if self._project_scope is not None and self._parent_scope is not None:
        intersected = self._project_scope & self._parent_scope
        task_id_scope = sorted(intersected)  # deterministic for SQL placeholders
    elif self._project_scope is not None:
        task_id_scope = sorted(self._project_scope)
    elif self._parent_scope is not None:
        task_id_scope = sorted(self._parent_scope)

    # ... other field assembly
    self._repo_query = ListTasksRepoQuery(
        ...,
        task_id_scope=task_id_scope,
        ...
    )
```

### Pattern 3: Warning emission sites

**What:** Warnings fire at distinct pipeline points based on trigger type.

**Emission-site mapping:**

| Warning | Trigger Condition | Emission Site | Why There |
|---------|-------------------|---------------|-----------|
| Multi-match (reused) | `len(resolved_ids) > 1` for any filter | `DomainLogic.check_filter_resolution()` (existing, unchanged) | Per-filter resolution outcome; called inside `_resolve_project`, `_resolve_parent`, `_resolve_tags` |
| No-match / did-you-mean (reused) | `len(resolved_ids) == 0` | Same as above | Same path |
| Inbox-name-substring (reused for parent) | `parent` value is a substring of "Inbox" but wasn't `$inbox` | New `_check_inbox_parent_warning()` in pipeline (mirror of existing `_check_inbox_project_warning`) | Per-filter, runs after `resolve_inbox` consumed any `$inbox` value |
| PARENT_RESOLVES_TO_PROJECT (WARN-02) | ALL resolved parent matches are project type | Inside `_resolve_parent` right after resolution | Entity-type introspection needs the `resolved` list + projects set; lives closest to that data |
| FILTERED_SUBTREE (WARN-01) | (`project` or `parent` scope applied) AND at least one other filter set | Pipeline-level, after all resolutions, before `_build_repo_query` returns | Needs visibility into ALL other filters — too wide for per-filter step |
| PARENT_PROJECT_COMBINED (WARN-03) | Both `project_to_resolve` and `parent_to_resolve` were non-None at pipeline entry | Pipeline-level, same location as WARN-01 | Presence-based; decoupled from whether scope sets intersect (D-13 explicit) |

**Domain-layer placement (WARN-04):** Even though WARN-01 and WARN-03 fire from the pipeline, the *condition-check logic* should live as methods on `DomainLogic` (e.g., `DomainLogic.check_filtered_subtree(query: ListTasksQuery) -> list[str]`) so the filter-semantics reasoning is co-located with `check_filter_resolution`. The pipeline calls those methods and extends `self._warnings`. This matches the WARN-04 requirement ("Warnings live in the domain layer (filter-semantics advice), not projection") without forcing the pipeline to pass 15 independent field values into a `DomainLogic` method — instead, the pipeline can pass the `ListTasksQuery` or a small derived subset.

### Anti-Patterns to Avoid

- **Don't hand-roll descendant traversal per repo.** Already rejected in CONTEXT.md D-08 — trivial set membership only. Repos must not grow parent-walking code paths.
- **Don't introduce a `ParentFilter` model.** The parent input is scalar (`str`). Filter classes exist for *multi-dimensional* agent inputs (`DateFilter` has relative + absolute + duration dimensions). A `ParentFilter` wrapping a single string is useless ceremony and breaks `<noun>Filter` semantics.
- **Don't emit FILTERED_SUBTREE from inside `_resolve_project` or `_resolve_parent`.** The condition requires knowing whether *any other filter* is set; per-filter steps don't have that visibility. Pipeline-level emission (post-all-resolutions) is the clean site.
- **Don't bypass `resolve_inbox` for parent.** Both `project` and `parent` values route through `resolve_inbox` before anything else (D-09). Skipping it for `parent` would miss `$inbox` consumption and contradiction detection — the exact problem D-09 prevents by consolidating.
- **Don't use unsorted sets for `task_id_scope`.** SQL placeholder ordering + test determinism require a sorted list. `sorted(scope_set)` before assignment.
- **Don't relax the `Patch[str]` type to `Patch[str | list[str]]`.** PARENT-09 rejects arrays at validation time; relaxing the type would let arrays through into the resolver.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Recursive subtree collection | Custom BFS/DFS with cycle detection "just in case" | Simple BFS over `parent.task.id` — OmniFocus's data model precludes cycles at the task-parent level by construction | Existing code (`DomainLogic.compute_true_inheritance`, `DomainLogic.check_cycle`) already follows this shape; repo cycle detection is a *write-side* concern, not needed for read-side subtree walks |
| Accept-type dispatch | `if isinstance(entity, Task) ... elif isinstance(entity, Project)` | Set membership against pre-computed `task_ids` / `project_ids` sets from snapshot | Snapshots are already loaded; set membership is O(1); isinstance adds import coupling |
| Entity-type classification for multi-match warning | New `parent`-specific warning generator | Existing `DomainLogic.check_filter_resolution()` — entity-type-agnostic, takes `entity_type: str` label | D-14 explicit reuse |
| 3-arg inbox contradiction matrix | Re-implement 3-arg logic in pipeline | Extend `Resolver.resolve_inbox` | Single consolidation point per D-09; existing 2-arg contradiction tests become extended 3-arg matrix tests |
| Null rejection on `parent` field | Custom field validator | Append `"parent"` to `_PATCH_FIELDS` list at `tasks.py:52-66` | `reject_null_filters` generic helper runs at model_validator(mode=before) on all listed fields |
| Array-rejection error message | Custom validator with educational message | `Patch[str]` type alias — Pydantic generic type error is sufficient | Per CLAUDE.md "schema violation vs semantic misuse" — schema violations get Pydantic-native errors, custom messaging reserved for semantic misuse (contradictory combos, ambiguous refs) |

**Key insight:** Phase 57 is almost entirely **assembly of existing components**. The new code is:
1. `expand_scope()` pure function (~20-30 lines)
2. `_resolve_parent` pipeline step (~15 lines, mirror of existing `_resolve_project`)
3. `resolve_inbox` 3-arg extension (~8 lines added)
4. Three warning constants + three condition-check methods (~30 lines total)
5. Field additions to contracts (~5 lines)

Everything else is rename migration (`project_ids` → `task_id_scope`).

## Runtime State Inventory

> Phase 57 is an in-place refactor + feature addition. No database migration, no external service config, no OS-registered state.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None. OmniFocus database is read-only via snapshot; no persistent state owned by OmniFocus Operator. | None — verified by no `.db` / cache path writes in service or contract layers. |
| Live service config | None — OmniFocus Operator has no external service registration. FastMCP picks up the new `parent` field from `ListTasksQuery` schema automatically at tool registration time. | None — server restart required for MCP client to see the new tool schema, which is expected for any schema change. |
| OS-registered state | None. | None. |
| Secrets/env vars | None affected. | None. |
| Build artifacts | `omnifocus_operator.egg-info/` may reference old field names in cached `PKG-INFO` text (unlikely but possible). | None expected — Pydantic field names are not embedded in package metadata. If `uv sync` is run it rebuilds cleanly. |

**Canonical question answered:** *After every file in the repo is updated, what runtime systems still have the old field name cached, stored, or registered?*

**Answer: none.** The refactor is pure-Python in-process. `ListTasksRepoQuery` is an in-memory Pydantic model — nothing persists its field names. The old `project_ids` name would only leak if (a) golden master fixtures store it (they don't — goldens are tool-output JSON, not repo-query JSON) or (b) a test snapshot file pins it (none found in `grep project_ids` under `tests/` — all hits are live Python construction, migrated mechanically).

## Common Pitfalls

### Pitfall 1: `$inbox` type ambiguity when resolving `parent`
**What goes wrong:** `$inbox` is registered at `config.py:65` as `type=EntityType.PROJECT`. If `parent: "$inbox"` is routed through `Resolver._resolve(value, accept=[PROJECT, TASK])` it resolves successfully. Then `expand_scope()` branches on "resolved ref is project" and tries to collect tasks whose `project.id == "$inbox"`. That works only because `list_tasks` uses `project.id == "$inbox"` as the inbox criterion elsewhere — consistent outcome, but accidentally so.
**Why it happens:** The `$inbox` sentinel is a fake project, not a real one. Without the `resolve_inbox` pre-pass, `expand_scope` would be asked to scope a non-existent entity.
**How to avoid:** **`resolve_inbox` 3-arg consumes `$inbox` BEFORE the resolver is invoked (D-09).** After `resolve_inbox`, `parent_to_resolve` is None if the original value was `$inbox` (and `in_inbox=True`). This means `_resolve_parent` never sees `$inbox`. The interview notes (line 161) called this out explicitly — "the shared filter entry needs a `$`-prefix pre-pass that serves both `project` and `parent`".
**Warning signs:** A test like `test_parent_inbox_equivalence` fails because `expand_scope` returns empty set instead of inbox tasks, OR it returns a wrong set because it walked a project-shaped code path. Symptom: PARENT-07 test fails while `project: "$inbox"` still works.

### Pitfall 2: Mid-hierarchy task with cross-project children
**What goes wrong:** OmniFocus allows action groups (tasks with children) inside a project. If `parent: "SomeTask"` resolves to a task in Project A and one of its children was moved to Project B, the subtree walk via `parent.task.id` edges returns both, but a subsequent `project` filter (if co-specified) intersects them down. If the agent is trying to "list everything under SomeTask" they get a subset — and may be surprised.
**Why it happens:** The intersection semantic (D-05) is strict AND — FILTERED_SUBTREE + PARENT_PROJECT_COMBINED warnings exist precisely to flag this.
**How to avoid:** WARN-01 (FILTERED_SUBTREE) + WARN-03 (PARENT_PROJECT_COMBINED) warn about exactly this case. Locked verbatim text for FILTERED_SUBTREE already addresses the "intermediate and descendant tasks not matching your other filters are excluded" aspect.
**Warning signs:** Agent loops back with "why isn't X in the results?" — the answer is usually "another filter excluded it, WARN-01 told you."

### Pitfall 3: Snapshot staleness between `list_tags` / `list_projects` and `get_all`-driven `expand_scope`
**What goes wrong:** `_ListTasksPipeline.execute` currently calls `asyncio.gather(list_tags, list_projects)` to get filter-resolution entities. Adding `expand_scope` — which needs tasks too — would ideally gather `list_tasks` too OR call `get_all()`. If we mix sources (projects from one call, tasks from another), the two lists could be from different snapshot mtimes on `HybridRepository`.
**Why it happens:** Repositories are cache-backed; `list_projects` and a fresh `list_tasks` call may straddle a cache invalidation.
**How to avoid:** Call `await self._repo.get_all()` once at the start of the pipeline and derive tasks + projects + tags from the single snapshot. This is already the pattern `DomainLogic.compute_true_inheritance` uses (service/domain.py:235). **Research note:** this is a small but real shape change for `_ListTasksPipeline` — it currently uses `list_projects`/`list_tags` specifically. Switching to `get_all()` may affect the existing pipeline tests that stub those methods.
**Alternative:** Keep `list_tags`/`list_projects` for filter-resolution and do `get_all()` only when `expand_scope` is needed. Both are valid; the single-snapshot path is cleaner but touches more tests.
**Warning signs:** Flaky tests where parent-filter results differ between runs, or tests that stub `list_tags`/`list_projects` but not `get_all` and hit empty-snapshot paths.

### Pitfall 4: Field-parity test hard-codes `project_ids`
**What goes wrong:** `tests/test_list_contracts.py:460` literally asserts `repo_only = {"project_ids", "tag_ids"} | _date_repo_fields`. Renaming without updating this test produces a failure that looks unrelated to the contract change.
**Why it happens:** The test was written to lock the Query/RepoQuery divergence intentionally. It's a sentinel test.
**How to avoid:** Update the literal to `{"task_id_scope", "tag_ids"} | _date_repo_fields` as part of the contract plan. Same for `test_list_tasks_repo_query_other_fields_default_none` at line 391.
**Warning signs:** Test `test_tasks_shared_fields_match` fails with "missing `project_ids`" error.

### Pitfall 5: Ordering non-determinism from `set` → SQL placeholders
**What goes wrong:** `task_id_scope: list[str] | None` is a list — but the scope originates as a `set[str]`. Converting with `list(scope_set)` produces insertion-order-dependent ordering in Python 3.7+ but set iteration is unordered. Two runs with identical inputs could produce different SQL placeholder orders, potentially breaking test assertions that check `data_q.params`.
**Why it happens:** Python set iteration is insertion-order in practice but *documented as unordered*. CPython's specific implementation detail is not guaranteed.
**How to avoid:** Use `sorted(scope_set)` when assigning to `ListTasksRepoQuery.task_id_scope`. Test assertions on param ordering become deterministic. `WHERE ... IN (?, ?, ?)` doesn't care about order — sorting is purely for test stability.
**Warning signs:** Flaky tests with ordering-dependent assertions like the existing `test_project_ids_subquery` in `test_query_builder.py`.

### Pitfall 6: BridgeOnlyRepository `get_all` caching and parent snapshots
**What goes wrong:** `BridgeOnlyRepository` snapshots the entire OF database into memory and caches it. If `expand_scope` runs against one `get_all()` snapshot and the repo serves `list_tasks` against a different (newer) snapshot after a cache invalidation between the service calls, a task can be in the scope set but not in the listing (or vice versa).
**Why it happens:** Same root cause as Pitfall 3.
**How to avoid:** In the pipeline, run `_build_repo_query` immediately after `expand_scope` under the assumption that BridgeOnly's cache is stable within a single MCP call (which it is — the repo's `_cached` field invalidates only on writes, and read pipelines are synchronous after `get_all`). HybridRepository's cache is similarly keyed by mtime and reads are cheap after first snapshot.
**Warning signs:** Would only surface under extreme concurrency that doesn't exist in the MCP server.

## Code Examples

Verified patterns from official sources:

### `<noun>Filter` → primitive resolution (existing `DateFilter` precedent)

```python
# Source: src/omnifocus_operator/contracts/use_cases/list/tasks.py
# Agent-facing (complex nested)
class ListTasksQuery(QueryModel):
    due: Patch[DueDateFilter] = Field(default=UNSET, description=DUE_FILTER_DESC)

# Repo-facing (flat primitives)
class ListTasksRepoQuery(QueryModel):
    due_after: datetime | None = None
    due_before: datetime | None = None
```

### Reusing `Resolver._resolve` for entity-type dispatch

```python
# Source: src/omnifocus_operator/service/resolve.py:163-173
# Existing pattern used by resolve_container — reused by parent per D-11
async def resolve_container(self, value: str) -> str | None:
    result = await self._resolve(value, accept=[EntityType.PROJECT, EntityType.TASK])
    return None if result == SYSTEM_LOCATIONS["inbox"].id else result
```

### Multi-match warning reuse

```python
# Source: src/omnifocus_operator/service/domain.py:500-538 (existing code)
# Already works for any entity_type string label — "parent" plugs in unmodified
self._warnings.extend(
    self._domain.check_filter_resolution(
        self._parent_to_resolve, resolved, combined, "parent"
    )
)
```

### Repo layer — set membership pattern

```python
# Source: src/omnifocus_operator/repository/bridge_only/bridge_only.py:227-229 (current project_ids)
# Mechanical rename to task_id_scope:
if query.task_id_scope is not None:
    scope_set = set(query.task_id_scope)
    items = [t for t in items if t.id in scope_set]
```

```python
# Source: src/omnifocus_operator/repository/hybrid/query_builder.py:258-265 (current project_ids)
# Rewrite — simpler clause since no subquery-to-ProjectInfo is needed:
if query.task_id_scope is not None and len(query.task_id_scope) > 0:
    placeholders = ",".join("?" * len(query.task_id_scope))
    conditions.append(f"t.persistentIdentifier IN ({placeholders})")
    params.extend(query.task_id_scope)
```

Note the SQL simplification: the old `project_ids` clause needed a join-through `ProjectInfo` because tasks stored `containingProjectInfo` (not project PK directly). The new `task_id_scope` clause filters by `persistentIdentifier` directly — primary key lookup, no subquery needed. This is strictly faster SQL.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `project_ids: list[str]` on `ListTasksRepoQuery` with subquery-to-ProjectInfo in SQL | `task_id_scope: list[str]` with direct `persistentIdentifier IN (...)` lookup | Phase 57 (this phase) | Simpler SQL, faster execution, one primitive serves both filters |
| Repo-layer `collect_subtree(parent_id, snapshot)` (original UNIFY-05 wording) | Service-layer `expand_scope(ref_id, snapshot, accept_entity_types)` returning `set[str]` | Phase 57 via D-01/D-05 reinterpretation | Single code path; repos stay ignorant of OF hierarchy |
| 2-arg `resolve_inbox(in_inbox, project)` | 3-arg `resolve_inbox(in_inbox, project, parent)` | Phase 57 per D-09 | Unified `$inbox` consumption site |
| Per-filter subtree logic (speculative — never implemented) | Shared `expand_scope` + `accept_entity_types` parameter | Phase 57 | D-02 unification |

**Deprecated/outdated:**
- `ListTasksRepoQuery.project_ids` field — removed in this phase, no backwards-compat layer (per "Pre-release, no compat" memory-only decision).
- MILESTONE-v1.4.1.md UNIFY-05 wording `collect_subtree(parent_id, snapshot) -> list[Task]` — superseded by `expand_scope()` signature (returns `set[str]`, takes `accept_entity_types`).
- MILESTONE-v1.4.1.md UNIFY-06 wording `parent_ids: list[str] | None` — superseded by `task_id_scope` (single unified primitive).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `BridgeOnlyRepository.get_all` returns a consistent snapshot (projects and tasks from the same mtime) when called once per pipeline | Pitfall 3, Pitfall 6 | If cache invalidation happens mid-pipeline, scope set and listing could mismatch. [VERIFIED via code inspection — `_cached` invalidates atomically on write; reads share the same snapshot] |
| A2 | OmniFocus's data model precludes cycles at the task-parent level by construction | Don't Hand-Roll | If cycles somehow exist, subtree BFS would infinite-loop. [VERIFIED: `DomainLogic.check_cycle` exists as a write-side guard, and the cycle-check logic shows cycles can only be introduced by malformed moves — which write-side code already rejects] |
| A3 | Field-parity test `test_tasks_shared_fields_match` is the only place in tests/ that hard-codes `project_ids` beyond the mechanical construction sites | Pitfall 4 | If there's another structural assertion we missed, test breakage surfaces elsewhere. [VERIFIED via `grep project_ids` — all other hits are live constructions like `ListTasksRepoQuery(project_ids=["x"])`, mechanical migration] |
| A4 | FastMCP auto-picks up new `parent` field from `ListTasksQuery` schema at tool registration without manual intervention | Architecture Patterns | [VERIFIED per existing pattern — all current filter fields are picked up this way; PROJECT_FILTER_DESC is wired via `Field(description=...)` and appears in the tool's inputSchema automatically] |
| A5 | No golden-master re-capture needed | CONTEXT.md §Tests | [CITED: CONTEXT.md line 178 explicit — "Golden master captures do NOT need re-take — results are invariant under D1"] |

**None of these assumptions are user-decision-eligible.** They are verified codebase facts or cited from CONTEXT.md.

## Open Questions (RESOLVED)

> All five open questions were resolved by the planner during Plan-Phase iteration 1 (2026-04-20). The resolutions are captured inside the individual plan files (`57-01-PLAN.md`, `57-02-PLAN.md`, `57-03-PLAN.md`) and the checked `57-VALIDATION.md`. Q5 (agent-facing wording) remains escalation-eligible — flagged below.

1. **Does `_ListTasksPipeline` switch from `gather(list_tags, list_projects)` to a single `get_all()` call?**
   - What we know: The pipeline currently avoids a full `get_all` because it only needs tasks for date filtering (via the repo-side `list_tasks`) — projects and tags suffice for filter resolution. Adding `expand_scope` changes this: for parent filtering, we need the task list too.
   - Recommendation: **Use `get_all()`**. Canonical single-snapshot call, matches `DomainLogic.compute_true_inheritance`'s precedent, HybridRepository caches well enough that cost is minimal.
   - **RESOLVED — accept recommendation.** Plan `57-01-PLAN.md` Task 2 restructures `_ListTasksPipeline.execute` to `await self._repository.get_all()` once at pipeline start. Existing test stubs that mock `list_tags`/`list_projects` are migrated as part of the same task.

2. **Should `expand_scope()` accept the snapshot or the task+project lists separately?**
   - What we know: `AllEntities` is the standard snapshot type. `DomainLogic.compute_true_inheritance` takes a `list[Task]` and builds maps from `get_all` internally.
   - Recommendation: Take `AllEntities` (snapshot). Tighter signature, matches the `compute_true_inheritance` pattern.
   - **RESOLVED — accept recommendation.** Plan `57-01-PLAN.md` Task 1 defines `expand_scope(ref_id: str, snapshot: AllEntities, accept_entity_types: frozenset[EntityType]) -> set[str]` in `service/subtree.py`.

3. **Is `accept_entity_types` a `frozenset[EntityType]` or a positional boolean `allow_tasks: bool`?**
   - What we know: CONTEXT.md D-16 leaves this as Claude's Discretion. Current code uses `accept: list[EntityType]` in `Resolver._resolve`.
   - Recommendation: `frozenset[EntityType]`. Matches resolver's existing `accept` parameter shape, extends cleanly to a future `folder` filter.
   - **RESOLVED — accept recommendation.** Plan `57-01-PLAN.md` Task 1 uses `accept_entity_types: frozenset[EntityType]` as the canonical signature. `project` filter passes `frozenset({EntityType.PROJECT})`; `parent` filter passes `frozenset({EntityType.PROJECT, EntityType.TASK})`.

4. **Where does the cross-filter equivalence test (UNIFY-02 / D-15) live?**
   - What we know: CONTEXT.md line 104 says "tests/service/ vs tests/contracts/ — Claude's Discretion." Current `tests/` is flat (no subdirectories).
   - Recommendation: Extend `tests/test_list_pipelines.py` (test content is load-bearing, not file structure).
   - **RESOLVED — accept recommendation.** Plan `57-02-PLAN.md` Task 2 adds `test_parent_and_project_byte_identical_for_same_project` to the existing `tests/test_list_pipelines.py`, using `model_dump(mode="json", by_alias=True)` equality.

5. **Should PARENT_FILTER_DESC mirror PROJECT_FILTER_DESC phrasing exactly?**
   - What we know: `PROJECT_FILTER_DESC` is `"Project ID or name. Names use case-insensitive substring matching -- if multiple projects match, tasks from all are included."` (descriptions.py:443-444).
   - Recommendation: Mirror PROJECT_FILTER_DESC shape but disclose the descendant semantic.
   - **RESOLVED — provisional.** Plan `57-02-PLAN.md` Task 1 Step 2 locks provisional wording:
     > "Task or project ID or name. Names use case-insensitive substring matching -- returns the resolved entity's full descendant subtree (tasks at any depth). If multiple entities match, their subtrees are unioned."
   - **Escalation note for executor / user:** This is user-visible agent-facing copy. If Flo wants to review/refine wording before execution, raise it before Plan 02 Task 1 runs. Otherwise, proceed with the provisional wording and revisit during UAT if it doesn't read well to agents in practice.

## Environment Availability

> Phase 57 has no external dependencies beyond the project's existing stack. All tools/services required for development and testing are already installed and verified in the repo.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | ≥3.12 (verified pyproject.toml) | — |
| pydantic | Contract models | ✓ | 2.12.5 | — |
| pytest | Test runner | ✓ | 9.0.2 | — |
| pytest-asyncio | Async pipeline tests | ✓ | 1.3.0 | — |
| uv | Package manager | ✓ (assumed per project conventions) | — | `pip install -e .` |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_list_contracts.py tests/test_service_resolve.py tests/test_list_pipelines.py tests/test_query_builder.py tests/test_cross_path_equivalence.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PARENT-01 | `parent` field accepted on `ListTasksQuery` | contract | `uv run pytest tests/test_list_contracts.py -x -q -k parent` | ⚠️ New tests needed (`test_list_contracts.py` exists; add cases) |
| PARENT-02 | Three-step resolver cascade works for parent | unit | `uv run pytest tests/test_service_resolve.py -x -q -k "parent or _resolve"` | ⚠️ New tests needed |
| PARENT-03 | Returns all descendants at any depth | unit | `uv run pytest tests/test_service_subtree.py -x -q` | ❌ New file needed — `test_service_subtree.py` |
| PARENT-04 | Anchor semantics (task=anchor, project=no-anchor) | unit | Same as PARENT-03 | ❌ Same file |
| PARENT-05 | AND-composes with other filters | pipeline | `uv run pytest tests/test_list_pipelines.py -x -q -k "parent and (tag or date or flagged)"` | ✅ Test file exists, new cases needed |
| PARENT-06 | Pagination over flat result set | pipeline | `uv run pytest tests/test_list_pipelines.py -x -q -k "parent and pagination"` | ✅ Same file |
| PARENT-07 | `parent: "$inbox"` ≡ `project: "$inbox"` | pipeline + cross-filter equivalence | `uv run pytest tests/test_list_pipelines.py -x -q -k "parent_inbox or inbox_equivalence"` | ✅ Same file |
| PARENT-08 | Contradiction rules for `parent: "$inbox"` | unit | `uv run pytest tests/test_service_resolve.py::TestResolveInbox -x -q` | ✅ Existing class extended with 3-arg cases |
| PARENT-09 | Array rejection at validation | contract | `uv run pytest tests/test_list_contracts.py -x -q -k "parent_array or parent_list"` | ⚠️ New case in existing file |
| UNIFY-01 | Shared mechanism (both filters route through `expand_scope`) | unit | `uv run pytest tests/test_service_subtree.py -x -q` | ❌ New file |
| UNIFY-02 | Byte-identical cross-filter equivalence | pipeline contract | See dedicated test below | ❌ New test needed |
| UNIFY-03 | Conditional anchor injection | unit | `uv run pytest tests/test_service_subtree.py -x -q -k anchor` | ❌ Same new file |
| UNIFY-04 | Repo applies set-membership (no hierarchy knowledge) | query-builder + cross-path | `uv run pytest tests/test_query_builder.py tests/test_cross_path_equivalence.py -x -q -k task_id_scope` | ✅ Both files exist; new cases |
| UNIFY-05 | `expand_scope` used by both resolve-steps | pipeline | `uv run pytest tests/test_list_pipelines.py -x -q` | ✅ Same file |
| UNIFY-06 | `task_id_scope` primitive, `project_ids` retired | contract | `uv run pytest tests/test_list_contracts.py::TestRepoQueryFieldParity::test_tasks_shared_fields_match -x -q` | ✅ Existing test updated |
| WARN-01 | FILTERED_SUBTREE verbatim text fires correctly | pipeline + domain | `uv run pytest tests/test_list_pipelines.py -x -q -k filtered_subtree` | ⚠️ New cases + possibly `test_service_domain.py` |
| WARN-02 | PARENT_RESOLVES_TO_PROJECT fires only when ALL matches are projects | pipeline | Same as PARENT-03 test cases | ⚠️ New cases |
| WARN-03 | PARENT_PROJECT_COMBINED fires when both set | pipeline | `uv run pytest tests/test_list_pipelines.py -x -q -k parent_project_combined` | ⚠️ New cases |
| WARN-04 | Warnings live in domain layer | architectural (import graph) | Covered implicitly by test file organization — domain warning constants imported from `agent_messages/warnings.py`, checks called via `DomainLogic` methods | ✅ Covered by existing pattern |
| WARN-05 | Multi-match + inbox-name-substring reuse for parent | pipeline | `uv run pytest tests/test_list_pipelines.py -x -q -k "parent_multi_match or parent_inbox_substring"` | ⚠️ New cases |
| Tool output schema safety | After ANY contract change | MCP outputSchema | `uv run pytest tests/test_output_schema.py -x -q` | ✅ Existing — MUST run after contract change per CLAUDE.md |

### Validation Layers for PARENT-09 (Array Rejection)

Four independent layers enforce that `parent` rejects arrays at validation time. **All four should have at least one test case.**

**Layer 1 — Type alias (`Patch[str]`):**
- Location: `src/omnifocus_operator/contracts/use_cases/list/tasks.py:~75` (new field addition)
- Mechanism: `Patch = Union[T, _Unset]` at `contracts/base.py:61`. Instantiating with `T=str` means `Patch[str] = Union[str, _Unset]`. Pydantic generates a JSON schema that accepts only string (plus the UNSET sentinel for omitted values). Arrays fail JSON schema validation at Pydantic's type-check pass.
- Test: `tests/test_list_contracts.py` — `ListTasksQuery(parent=["Work"])` raises `ValidationError`. The error message is generic Pydantic ("Input should be a valid string"), which is *intentional* — CLAUDE.md `schema violation vs semantic misuse` principle: arrays are schema violation, no custom messaging needed.

**Layer 2 — Null rejection (`reject_null_filters`):**
- Location: `tasks.py:52-66` `_PATCH_FIELDS` list + `tasks.py:91-96` `_reject_nulls` model_validator
- Mechanism: `reject_null_filters(data, _PATCH_FIELDS)` runs at model_validator(mode="before") and rejects `parent=None` with a specific message `FILTER_NULL.format(field=parent)`.
- Test: `ListTasksQuery(parent=None)` raises `ValidationError` with the "cannot be null" message.
- Action required: **add `"parent"` to `_PATCH_FIELDS` list** — mechanical one-line change.

**Layer 3 — `extra="forbid"` on `QueryModel`:**
- Location: `contracts/base.py:83` — `model_config = ConfigDict(extra="forbid")` inherited via `StrictModel` → `QueryModel`.
- Mechanism: Unknown fields rejected at Pydantic level.
- Test: `ListTasksQuery(parents="Work")` (typo'd plural) raises ValidationError.

**Layer 4 — Output schema safety check (MCP level):**
- Location: `tests/test_output_schema.py`
- Mechanism: Serialized tool output validates against the MCP outputSchema. Input changes to `ListTasksQuery` don't affect the output schema, but running the test confirms no regression.
- Test: `uv run pytest tests/test_output_schema.py -x -q` — mandatory after any contract change per CLAUDE.md.

### Cross-Filter Equivalence Contract Test (UNIFY-02 / D-15)

**Test shape:**

```python
# File: tests/test_list_pipelines.py (append to existing file) OR
# new file tests/test_list_pipelines_scope_unification.py
# Uses InMemoryBridge per SAFE-01

@pytest.mark.asyncio
async def test_parent_and_project_byte_identical_for_same_project(
    in_memory_service: OperatorService,
) -> None:
    """UNIFY-02 / D-15: parent: 'Work' ≡ project: 'Work' when 'Work' resolves to a project.

    Byte-identical contract: both queries produce the same ListResult items in the
    same order with the same field values. Warnings may differ (WARN-03 fires for
    parent+project combined, not here; FILTERED_SUBTREE might differ due to the
    'other filters combined' check but with minimal query it does not fire).
    """
    project_result = await in_memory_service.list_tasks(
        ListTasksQuery(project="Work")
    )
    parent_result = await in_memory_service.list_tasks(
        ListTasksQuery(parent="Work")
    )

    # Byte-identity via model_dump() — no serialization quirks masked
    project_dump = [t.model_dump(mode="json", by_alias=True) for t in project_result.items]
    parent_dump = [t.model_dump(mode="json", by_alias=True) for t in parent_result.items]

    assert project_dump == parent_dump, (
        f"UNIFY-02 violated: same entity 'Work' produced different results\n"
        f"project filter: {len(project_dump)} items\n"
        f"parent filter:  {len(parent_dump)} items"
    )

    # Totals identical
    assert project_result.total == parent_result.total
    assert project_result.has_more == parent_result.has_more
```

**What "byte-identical" means here:**

- **Task content:** Every field value on every returned `Task` is identical — tests via `model_dump(mode="json", by_alias=True)` equality. Using `mode="json"` catches date serialization; using `by_alias=True` catches camelCase field names. This covers `id`, `name`, `availability`, `urgency`, `tags`, `parent`, `project`, inherited fields, etc.
- **Order:** Python list equality requires identical order. Outline order is determined by the CTE / sort step and doesn't depend on which filter scoped the results.
- **Totals:** `result.total` and `result.has_more` identical — no drift from pagination math.

**What's allowed to differ (and why):**

- **Warnings list** — When `parent` is used, no `parent`-specific warnings should fire for a minimal query with no other filters. If any do, the test's warnings assertion would need refinement. Recommend: initially test *only* items/total/has_more byte-identity; warnings are covered by separate dedicated tests (WARN-01/02/03).

**Test data fixture:**

Use a snapshot with a well-defined project ("Work") containing multiple tasks, some at root-of-project, some nested. The `InMemoryBridge` allows constructing any shape. Existing fixtures in `tests/test_list_pipelines.py` provide patterns — reuse or extend.

**Extended equivalence matrix (stretch — nice-to-have, not required by D-15):**

| Scenario | `project` filter | `parent` filter | Expected |
|----------|------------------|-----------------|----------|
| Same project name, no other filters | `project="Work"` | `parent="Work"` | Byte-identical items |
| Same project ID | `project="proj-work-id"` | `parent="proj-work-id"` | Byte-identical items |
| `$inbox` | `project="$inbox"` | `parent="$inbox"` | Byte-identical items (via `resolve_inbox` 3-arg consumption) |
| Project + same other filter | `project="Work", flagged=true` | `parent="Work", flagged=true` | Byte-identical items, FILTERED_SUBTREE warning fires on both |

### Sampling Rate

- **Per task commit (< 30s):** `uv run pytest tests/test_list_contracts.py tests/test_service_resolve.py tests/test_query_builder.py -x -q`
- **Per wave merge (~1-2 min):** `uv run pytest tests/test_list_pipelines.py tests/test_cross_path_equivalence.py tests/test_hybrid_repository.py tests/test_bridge_only_repository.py tests/test_service_domain.py tests/test_output_schema.py -x -q`
- **Phase gate (full suite):** `uv run pytest -x -q` — green before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] New test file: `tests/test_service_subtree.py` — unit tests for `expand_scope()` (anchor semantics, accept-entity-types, empty snapshot, resolved ID not found, cycles-by-construction-not-possible). Primary target for PARENT-03, PARENT-04, UNIFY-01, UNIFY-03.
- [ ] Extension to `tests/test_service_resolve.py::TestResolveInbox` — add 3-arg cases covering all 2^3 combinations of (in_inbox, project, parent) presence, plus `parent="$inbox"` consumption + contradiction with `inInbox=false` (PARENT-07, PARENT-08).
- [ ] New cases in `tests/test_list_pipelines.py` for parent filter + AND-composition, pagination, `$inbox` equivalence, warning emissions. Estimate 15-25 new cases.
- [ ] New cases in `tests/test_list_contracts.py` for `parent` field shape (Patch[str], array rejection, null rejection).
- [ ] Update `tests/test_list_contracts.py::TestRepoQueryFieldParity::test_tasks_shared_fields_match` — replace `project_ids` literal with `task_id_scope`.
- [ ] Update `tests/test_list_contracts.py::test_list_tasks_repo_query_other_fields_default_none` — replace `project_ids` literal.
- [ ] Migrate `tests/test_query_builder.py::TestTasksProjectFilter` — rename to `TestTasksScopeFilter`, rewrite SQL assertions (`t.containingProjectInfo IN` → `t.persistentIdentifier IN`, no ProjectInfo subquery).
- [ ] Migrate `tests/test_hybrid_repository.py::test_list_tasks_project_filter*` — rewrite `ListTasksRepoQuery(project_ids=["proj-work"])` → `ListTasksRepoQuery(task_id_scope=[…])` with the scope ID set that matches expected task output.
- [ ] Migrate `tests/test_cross_path_equivalence.py::test_list_tasks_by_project` — rewrite to use `task_id_scope`.
- [ ] MANDATORY after contract change: `uv run pytest tests/test_output_schema.py -x -q`.

### Framework install

Not needed — pytest already in `pyproject.toml` dev dependencies, installed via `uv sync`.

## Sources

### Primary (HIGH confidence — VERIFIED via codebase inspection or CONTEXT.md citation)

- `.planning/phases/57-parent-filter-filter-unification/57-CONTEXT.md` — D-01 through D-16 locked decisions
- `.planning/REQUIREMENTS.md` — PARENT-01..09, UNIFY-01..06, WARN-01..05 (with UNIFY-04/05/06 revised per commit b53adc9c)
- `.research/updated-spec/MILESTONE-v1.4.1.md` — design contract, filtered-subtree warning verbatim text (line 180)
- `.research/updated-spec/MILESTONE-v1.4.1.interview-notes.md` — session 2 lines 67-73 (filter unification intent), session 3 line 161 (`$inbox` sentinel short-circuit), session 4 line 116 (maintainability principle)
- `.research/deep-dives/v1.4.1-filter-benchmark/FINDINGS.md` — Spike 2 evidence (p95 ≤ 1.30ms at 10K)
- `src/omnifocus_operator/service/resolve.py` — `Resolver._resolve`, `resolve_inbox`, `resolve_filter` existing behavior
- `src/omnifocus_operator/service/service.py` — `_ListTasksPipeline` structure (lines 372-473)
- `src/omnifocus_operator/service/domain.py` — `check_filter_resolution` (lines 500-538), `compute_true_inheritance` symmetric precedent (lines 219-311)
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` — current `ListTasksQuery` + `ListTasksRepoQuery` shape
- `src/omnifocus_operator/contracts/base.py` — `Patch[T]` type alias mechanics
- `src/omnifocus_operator/repository/hybrid/query_builder.py:258-265` — current `project_ids` SQL shape
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py:227-229` — current `project_ids` Python filter shape
- `src/omnifocus_operator/agent_messages/warnings.py` — existing warning constants, reuse targets
- `src/omnifocus_operator/agent_messages/descriptions.py:443-444` — `PROJECT_FILTER_DESC` pattern for new `PARENT_FILTER_DESC`
- `docs/architecture.md` — Method Object pattern (lines 177-208), Service Layer responsibilities (lines 210-239), True Inheritance symmetric precedent (lines 484-620)
- `docs/model-taxonomy.md` — `<noun>Filter` → primitive resolution pattern (lines 102-142)
- `CLAUDE.md` — SAFE-01/02, Method Object convention, model taxonomy gate, output-schema test mandate
- `tests/test_list_contracts.py`, `tests/test_query_builder.py`, `tests/test_hybrid_repository.py`, `tests/test_cross_path_equivalence.py`, `tests/test_service_resolve.py` — existing tests requiring migration

### Secondary (MEDIUM confidence — cross-verified existing behavior)

- Installed package versions: [VERIFIED: `uv pip list`] — pydantic 2.12.5, pytest 9.0.2, pytest-asyncio 1.3.0, fastmcp ≥3.1.1

### Tertiary (LOW confidence — none required for this phase)

- No external library API claims requiring Context7 lookup. Phase 57 is refactor + small feature on the project's own existing idioms; no new library APIs.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all packages already in `pyproject.toml` and verified installed; no new dependencies.
- Architecture: HIGH — matches locked CONTEXT.md decisions; patterns directly mirror existing `_resolve_project` / `compute_true_inheritance` / `DateFilter` precedents.
- Pitfalls: HIGH — enumerated from codebase inspection (existing tests, existing service layer, existing repo layer); no speculation.
- Validation architecture: HIGH — test files and migration targets enumerated from `grep project_ids` across codebase; cross-filter equivalence pattern is specific and runnable.
- Module placement (dedicated module vs DomainLogic method): MEDIUM — defensible either way; recommendation grounded in code, but it's a judgment call.
- Signature of `accept_entity_types`: MEDIUM — `frozenset[EntityType]` recommended for extensibility but `bool` is simpler and defensible.

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (30 days for stable/mature codebase; refactor scope is bounded to files already inspected, so staleness risk is low)
