# Phase 57: Parent Filter & Filter Unification — Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 12 (9 production + 3 test)
**Analogs found:** 12 / 12

All files to be created or modified have strong in-codebase analogs. Phase 57 is explicitly "assembly of existing components" (RESEARCH.md §Don't Hand-Roll). No analog-less files.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/omnifocus_operator/contracts/use_cases/list/tasks.py` (modify) | contract | request-response | self — existing `project: Patch[str]` on `ListTasksQuery`, existing `project_ids` on `ListTasksRepoQuery` | exact (in-file mirror) |
| `src/omnifocus_operator/agent_messages/descriptions.py` (modify) | config | static string | self — `PROJECT_FILTER_DESC` at line 443-444 | exact |
| `src/omnifocus_operator/agent_messages/warnings.py` (modify) | config | static string | self — `LIST_TASKS_INBOX_PROJECT_WARNING` at line 171-175 | exact |
| `src/omnifocus_operator/service/subtree.py` (NEW) | service utility | in-memory graph walk | `DomainLogic.compute_true_inheritance` in `service/domain.py` line 219-314 | role-match (symmetric: down-walk vs up-walk) |
| `src/omnifocus_operator/service/resolve.py` (modify — `resolve_inbox` 3-arg) | service | request-response | self — existing 2-arg `resolve_inbox` at line 217-239 | exact (in-file extension) |
| `src/omnifocus_operator/service/service.py` (modify — `_resolve_parent`, intersection, warning hooks) | service | pipeline step | self — `_resolve_project` at line 408-419, `_check_inbox_project_warning` at line 401-406, `_build_repo_query` at line 440-464 | exact (in-file mirror) |
| `src/omnifocus_operator/service/domain.py` (modify — new warning check methods) | service | domain check | self — `check_filter_resolution` at line 500-538 | exact (in-file sibling) |
| `src/omnifocus_operator/repository/hybrid/query_builder.py` (modify — SQL rename) | repository | SQL generation | self — existing `project_ids` block at line 258-265 | exact |
| `src/omnifocus_operator/repository/bridge_only/bridge_only.py` (modify — Python filter rename) | repository | in-memory filter | self — existing `project_ids` block at line 227-229 | exact |
| `tests/test_service_subtree.py` (NEW) | test (unit) | in-memory | no direct analog — closest is `tests/test_service_domain.py` style (unit tests on pure DomainLogic methods) | role-match |
| `tests/test_list_pipelines.py` (modify — parent cases + cross-filter equivalence) | test (pipeline) | async in-memory | self — existing project-filter cases in same file | exact |
| `tests/test_list_contracts.py`, `tests/test_query_builder.py`, `tests/test_hybrid_repository.py`, `tests/test_cross_path_equivalence.py`, `tests/test_bridge_contract.py`, `tests/doubles/bridge.py`, `tests/golden_master/normalize.py` (modify — mechanical `project_ids` → `task_id_scope` migration) | test (various) | mechanical | self — existing constructions migrate 1:1 | exact |

## Pattern Assignments

### `contracts/use_cases/list/tasks.py` — add `parent: Patch[str]` to `ListTasksQuery`, retire `project_ids` and add `task_id_scope` on `ListTasksRepoQuery`

**Analog (in-file):** existing `project` field at line 74; existing `project_ids` at line 127.

**Import pattern** (lines 1-46 — extend with `PARENT_FILTER_DESC`):
```python
from omnifocus_operator.agent_messages.descriptions import (
    ADDED_FILTER_DESC,
    # ... existing imports
    PROJECT_FILTER_DESC,
    TAGS_FILTER_DESC,
    # NEW:
    PARENT_FILTER_DESC,
)
```

**Query field pattern** (line 74 — `project` field; new `parent` mirrors shape exactly):
```python
# Existing:
project: Patch[str] = Field(default=UNSET, description=PROJECT_FILTER_DESC)
# New (same Patch[str] type, same default, same description-constant convention):
parent: Patch[str] = Field(default=UNSET, description=PARENT_FILTER_DESC)
```

**`_PATCH_FIELDS` null-rejection registration** (line 52-66 — append `"parent"`):
```python
_PATCH_FIELDS = [
    "in_inbox",
    "flagged",
    "project",
    "parent",   # NEW — enforces FILTER_NULL error on `parent=None`
    "tags",
    # ...
]
```

**Repo query field pattern** (line 127 — `project_ids` retired; new `task_id_scope` replaces):
```python
# REMOVE:
project_ids: list[str] | None = None
# ADD (same shape, broader semantic — applies set-membership on task.persistentIdentifier):
task_id_scope: list[str] | None = None
```

**No `ParentFilter` model.** RESEARCH.md §Alternatives Considered locks this: parent is scalar, no nested model. Single line field addition is the entire contract change.

---

### `agent_messages/descriptions.py` — add `PARENT_FILTER_DESC`

**Analog (in-file):** `PROJECT_FILTER_DESC` at line 443-444.

```python
# Existing (line 443-444):
PROJECT_FILTER_DESC = """\
Project ID or name. Names use case-insensitive substring matching -- if multiple projects match, tasks from all are included."""

# New — mirror shape, disclose descendant-subtree semantic (RESEARCH.md Open Q5 recommendation):
PARENT_FILTER_DESC = """\
Task or project ID or name. Names use case-insensitive substring matching -- returns the resolved entity's full descendant subtree (tasks at any depth). If multiple entities match, their subtrees are unioned."""
```

Exact wording is agent-facing-messaging concern; recommend plan task running wording by the user.

---

### `agent_messages/warnings.py` — three new constants

**Analog (in-file):** `LIST_TASKS_INBOX_PROJECT_WARNING` at line 171-175 (multi-line triple-quoted string, parameterized via `.format()`).

**Pattern — parameterized multi-line constants:**
```python
# Existing (line 171-175):
LIST_TASKS_INBOX_PROJECT_WARNING = """\
The 'project="{value}"' filter also matches the OmniFocus Inbox by name, \
but the Inbox is a virtual location, not a named project. \
Inbox tasks are not included in these results. \
Use 'inInbox=true' to query them."""
```

**New constants** (grouped under a "# --- Task Tool: Scope Filters ---" section, placed adjacent to the existing inbox-project warning):

```python
# WARN-01 — verbatim text from MILESTONE-v1.4.1.md line 180, LOCKED — do not paraphrase:
FILTERED_SUBTREE_WARNING = """\
Filtered subtree: resolved parent tasks are always included, \
but intermediate and descendant tasks not matching your other filters \
(tags, dates, etc.) are excluded. Each returned task's `parent` field \
still references its true parent -- fetch separately if you need data \
for an excluded intermediate."""

# WARN-02 — soft pedagogical hint:
PARENT_RESOLVES_TO_PROJECT_WARNING = """\
The 'parent="{value}"' filter resolved only to projects. \
Consider using 'project' instead -- it's the canonical filter for \
project-level scoping and makes intent clearer."""

# WARN-03 — soft combined-filters hint:
PARENT_PROJECT_COMBINED_WARNING = """\
Both 'project' and 'parent' filters are set. \
Results are the intersection of their task scopes. \
If you meant only one scope, omit the other."""
```

Rationale for grouping: existing file already separates warning families with `# --- X ---` comment headers (lines 10, 17, 31, 53, 61, 72, 118, 134, 154, 162, 169, 177).

---

### `service/subtree.py` (NEW) — `expand_scope()` shared helper

**Analog:** `DomainLogic.compute_true_inheritance()` at `service/domain.py` line 219-314.

The analog is a **symmetric operation**: `compute_true_inheritance` walks the task's ancestor chain UP via `task.parent.task.id` edges and the task's containing project. `expand_scope` walks descendants DOWN via the same `parent.task.id` edges. Both operate on a single snapshot loaded via `await repo.get_all()`.

**Key differences (justifying a free function in a new module over a `DomainLogic` method):**

1. **No async, no DI** — `compute_true_inheritance` calls `await self._repo.get_all()` internally (domain.py:235). `expand_scope` takes the snapshot as an argument — the pipeline already has it.
2. **No self-state dependency** — pure function of (ref_id, snapshot, accept_entity_types).
3. **Testability** — no fixture required for unit tests.
4. **Future extension site** — when `folder` scope filter lands, it slots into the same module.

**Core BFS pattern — copy from `compute_true_inheritance._walk_one` lines 256-282** (ancestor walk), invert edge direction to descend:

```python
# Source: service/domain.py:256-282 (upward walk — the symmetric precedent)
current_id: str | None = task.parent.task.id if task.parent.task else None
while current_id is not None:
    ancestor = task_map.get(current_id)
    if ancestor is None:
        break
    # ... field aggregation
    current_id = ancestor.parent.task.id if ancestor.parent.task else None
```

**`expand_scope()` target shape** (from RESEARCH.md Pattern 1):

```python
# File: src/omnifocus_operator/service/subtree.py
from omnifocus_operator.models.enums import EntityType
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.models.task import Task


def expand_scope(
    ref_id: str,
    snapshot: AllEntities,
    accept_entity_types: frozenset[EntityType],
) -> set[str]:
    """Expand a resolved entity ID to the set of task IDs it scopes.

    - If ref_id is a task AND EntityType.TASK in accept_entity_types:
      returns {ref_id} | {all descendant task ids}
    - If ref_id is a project AND EntityType.PROJECT in accept_entity_types:
      returns {all task ids whose containing project is ref_id at any depth}
    - Otherwise returns set().
    """
    task_ids = {t.id for t in snapshot.tasks}
    project_ids = {p.id for p in snapshot.projects}

    if ref_id in task_ids and EntityType.TASK in accept_entity_types:
        result = {ref_id}
        result |= _collect_task_descendants(ref_id, snapshot.tasks)
        return result

    if ref_id in project_ids and EntityType.PROJECT in accept_entity_types:
        return {t.id for t in snapshot.tasks if t.project.id == ref_id}

    return set()


def _collect_task_descendants(anchor_id: str, tasks: list[Task]) -> set[str]:
    """BFS over parent.task.id edges. anchor_id is NOT included."""
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

**Cycle-safety justification:** A2 in RESEARCH.md §Assumptions Log — OmniFocus data model precludes cycles by construction; `DomainLogic.check_cycle` is a write-side guard. Read-side descent is safe without cycle detection, same as the ancestor walk.

---

### `service/resolve.py` — `resolve_inbox` 3-arg extension

**Analog (in-file):** existing 2-arg `resolve_inbox` at line 217-239.

**Existing pattern to extend:**
```python
# Source: service/resolve.py:217-239
def resolve_inbox(
    self, in_inbox: bool | None, project: str | None
) -> tuple[bool | None, str | None]:
    """Resolve inbox filter state from in_inbox and project filter params.

    Returns (effective_in_inbox, remaining_project_to_resolve).
    If project is "$inbox", it is consumed: returns (True, None).
    Unknown $-prefix raises. Contradictory combos raise.
    """
    if project is not None and project.startswith(SYSTEM_LOCATION_PREFIX):
        self._resolve_system_location(project, [EntityType.PROJECT])
        if in_inbox is False:
            raise ValueError(CONTRADICTORY_INBOX_FALSE)
        return (True, None)

    if in_inbox is True and project is not None:
        raise ValueError(CONTRADICTORY_INBOX_PROJECT)

    return (in_inbox, project)
```

**Extension contract (D-09):**
```python
def resolve_inbox(
    self, in_inbox: bool | None, project: str | None, parent: str | None
) -> tuple[bool | None, str | None, str | None]:
    """Returns (effective_in_inbox, remaining_project, remaining_parent).

    Mirror rules for both project and parent:
    - "$inbox" is consumed → (True, None, None for the consumed side)
    - "$inbox" + in_inbox=False → CONTRADICTORY_INBOX_FALSE
    - in_inbox=True + any non-None real ref → CONTRADICTORY_INBOX_PROJECT (rename?)

    parent's accepted types differ: system-location resolution for parent
    accepts [PROJECT, TASK] (parent filter accepts both entity types).
    """
```

**Planner consideration:** The existing 2-arg signature hard-codes `accept=[EntityType.PROJECT]` in the `_resolve_system_location` call at line 227. For parent, pass `accept=[EntityType.PROJECT, EntityType.TASK]`. `$inbox` itself is declared `type=EntityType.PROJECT` in config — it resolves successfully against either accept set.

**Error constant reuse:** `CONTRADICTORY_INBOX_FALSE` and `CONTRADICTORY_INBOX_PROJECT` already exist. If WARN/error message text needs to mention "project or parent" rather than "project," planner decides whether to generalize the constant or add a parent-specific variant. Recommend generalizing — the contradiction is "inbox sentinel vs explicit in_inbox=false/true", agnostic to which filter introduced it.

---

### `service/service.py` — new `_resolve_parent` step + `_check_inbox_parent_warning` + intersection in `_build_repo_query`

**Analog (in-file):** existing `_resolve_project` at line 408-419, `_check_inbox_project_warning` at line 401-406, `_build_repo_query` at line 440-464, `execute` at line 375-399.

**Imports pattern** (top of `service/service.py` line 25-30):
```python
# Existing:
from omnifocus_operator.agent_messages.warnings import (
    AVAILABILITY_MIXED_ALL,
    LIST_PROJECTS_INBOX_WARNING,
    LIST_TASKS_INBOX_PROJECT_WARNING,
    REPETITION_NO_OP,
)
# Extend with:
from omnifocus_operator.agent_messages.warnings import (
    FILTERED_SUBTREE_WARNING,
    PARENT_PROJECT_COMBINED_WARNING,
    PARENT_RESOLVES_TO_PROJECT_WARNING,
    # ... existing imports
)
from omnifocus_operator.models.enums import EntityType
from omnifocus_operator.service.subtree import expand_scope
```

**`_check_inbox_project_warning` analog** (line 401-406 — mirror for parent):
```python
# Existing:
def _check_inbox_project_warning(self) -> None:
    if matches_inbox_name(self._project_to_resolve):
        self._warnings.append(
            LIST_TASKS_INBOX_PROJECT_WARNING.format(value=self._project_to_resolve)
        )

# New mirror — D-14, reuses LIST_TASKS_INBOX_PROJECT_WARNING constant (WARN-05):
def _check_inbox_parent_warning(self) -> None:
    if matches_inbox_name(self._parent_to_resolve):
        self._warnings.append(
            LIST_TASKS_INBOX_PROJECT_WARNING.format(value=self._parent_to_resolve)
        )
```

Planner note: reusing `LIST_TASKS_INBOX_PROJECT_WARNING` for parent produces a message that says `'project="..."'`. The message-text mentions project specifically. Either (a) generalize the constant to say "filter" or (b) add a `LIST_TASKS_INBOX_PARENT_WARNING` sibling. This is a messaging concern — defer to the planner's preference; D-14 says "no new constant," so recommend generalizing the existing text to "The '{filter}=\"{value}\"' filter..." and formatting with `filter="project"` / `filter="parent"`.

**`_resolve_project` pattern** (line 408-419) — existing shape to mirror:
```python
def _resolve_project(self) -> None:
    self._project_ids: list[str] | None = None
    if self._project_to_resolve is None:
        return
    resolved = self._resolver.resolve_filter(self._project_to_resolve, self._projects)
    if resolved:
        self._project_ids = resolved
    self._warnings.extend(
        self._domain.check_filter_resolution(
            self._project_to_resolve, resolved, self._projects, "project"
        )
    )
```

**`_resolve_parent` target shape** (mirror + D-11 two-entity-type collection + D-13 WARN-02):
```python
def _resolve_parent(self) -> None:
    self._parent_resolved_ids: list[str] | None = None
    if self._parent_to_resolve is None:
        return
    combined = [*self._projects, *self._tasks]
    resolved = self._resolver.resolve_filter(self._parent_to_resolve, combined)
    self._warnings.extend(
        self._domain.check_filter_resolution(
            self._parent_to_resolve, resolved, combined, "parent"
        )
    )
    if resolved:
        self._parent_resolved_ids = resolved
    # WARN-02: fires only when ALL matches are projects (not mixed)
    if resolved and all(rid in {p.id for p in self._projects} for rid in resolved):
        self._warnings.append(
            PARENT_RESOLVES_TO_PROJECT_WARNING.format(value=self._parent_to_resolve)
        )
```

Note on `_parent_resolved_ids` vs `_parent_scope`: RESEARCH.md Pattern 2 assigns scope-set computation inside `_resolve_parent`. Planner may choose to split that further — `_resolve_parent` stores resolved IDs, `_build_repo_query` or a new `_compute_scopes` step calls `expand_scope`. Either is defensible; the split makes test boundaries cleaner.

**Snapshot acquisition** — `_ListTasksPipeline.execute` currently uses `asyncio.gather(list_tags, list_projects)` at line 379-386. For `expand_scope` to work, the pipeline needs tasks too. RESEARCH.md Open Q1 recommends switching to `await self._repo.get_all()` once. Planner's call whether to:
- (a) replace `gather(list_tags, list_projects)` with `get_all()` (cleaner, one snapshot), OR
- (b) retain `gather(list_tags, list_projects)` and add `get_all()` only when scope expansion is needed (minimal test churn).

Recommend (a) — matches `compute_true_inheritance` convention, repo cache makes it free.

**`_build_repo_query` pattern** (line 440-464) — existing field assembly; add scope intersection:
```python
# Existing pattern (line 453-464):
self._repo_query = ListTasksRepoQuery(
    in_inbox=self._in_inbox,
    flagged=unset_to_none(self._query.flagged),
    project_ids=self._project_ids,  # REMOVE
    tag_ids=self._tag_ids,
    # ...
)

# New shape (D-05):
# 1. Compute project_scope via expand_scope(pid, snapshot, {PROJECT}) for each pid
# 2. Compute parent_scope via expand_scope(rid, snapshot, {PROJECT, TASK}) for each rid
# 3. Intersect if both present; union within each filter
# 4. sorted() for deterministic SQL placeholder order (Pitfall 5)
task_id_scope: list[str] | None = None
if self._project_scope is not None and self._parent_scope is not None:
    task_id_scope = sorted(self._project_scope & self._parent_scope)
elif self._project_scope is not None:
    task_id_scope = sorted(self._project_scope)
elif self._parent_scope is not None:
    task_id_scope = sorted(self._parent_scope)

self._repo_query = ListTasksRepoQuery(
    # ...
    task_id_scope=task_id_scope,  # ADD
    # ...
)
```

**Pipeline-level warnings** (WARN-01 FILTERED_SUBTREE and WARN-03 PARENT_PROJECT_COMBINED) fire from pipeline code, not per-filter step. RESEARCH.md Pattern 3 places them post-resolution, before `_delegate`. Delegate condition-check logic to `DomainLogic.check_filtered_subtree(query)` and `DomainLogic.check_parent_project_combined(query)` so domain layer owns filter-semantics reasoning (WARN-04).

---

### `service/domain.py` — new warning-check methods

**Analog (in-file):** `check_filter_resolution` at line 500-538.

**Existing method pattern** (pure function of args, returns `list[str]` warnings, no side effects):
```python
# Source: service/domain.py:500-538
def check_filter_resolution(
    self,
    value: str,
    resolved_ids: list[str],
    entities: Sequence[_HasIdAndName],
    entity_type: str,
) -> list[str]:
    """Generate warnings for filter resolution outcomes."""
    if len(resolved_ids) > 1:
        # ... return [FILTER_MULTI_MATCH.format(...)]
    if len(resolved_ids) == 0:
        # ... return FILTER_DID_YOU_MEAN or FILTER_NO_MATCH
    return []
```

**Target shape — new methods** (each returns `list[str]` for uniform `self._warnings.extend(...)` ergonomics):
```python
def check_filtered_subtree(self, query: ListTasksQuery) -> list[str]:
    """WARN-01: scope filter + any other filter → subtree-filtered warning.

    Fires when (project or parent) is set AND at least one other filter dim is set.
    """
    scope_set = is_set(query.project) or is_set(query.parent)
    if not scope_set:
        return []
    # "Any other filter" = any dimension other than project/parent/pagination/include
    other_filter_set = (
        is_set(query.flagged) or is_set(query.in_inbox) or is_set(query.tags)
        or is_set(query.estimated_minutes_max) or is_set(query.search)
        or is_set(query.due) or is_set(query.defer) or is_set(query.planned)
        or is_set(query.completed) or is_set(query.dropped)
        or is_set(query.added) or is_set(query.modified)
        # availability has a default non-empty value — exclude from "other filter" test
    )
    if other_filter_set:
        return [FILTERED_SUBTREE_WARNING]
    return []


def check_parent_project_combined(self, query: ListTasksQuery) -> list[str]:
    """WARN-03: both project and parent set → intersection warning."""
    if is_set(query.project) and is_set(query.parent):
        return [PARENT_PROJECT_COMBINED_WARNING]
    return []
```

**Placement alternative:** These could live as pipeline-private methods on `_ListTasksPipeline` itself (no visibility to `DomainLogic`). WARN-04 says "warnings live in the domain layer (filter-semantics advice), not projection" — domain placement satisfies WARN-04 explicitly; pipeline placement is acceptable but weaker. Recommend domain.

---

### `repository/hybrid/query_builder.py` — SQL rewrite

**Analog (in-file):** existing `project_ids` block at line 258-265, existing `tag_ids` block at line 267-274.

**Existing pattern to REPLACE** (line 258-265 — subquery-to-ProjectInfo):
```python
if query.project_ids is not None and len(query.project_ids) > 0:
    placeholders = ",".join("?" * len(query.project_ids))
    conditions.append(
        f"t.containingProjectInfo IN ("
        f"SELECT pi2.pk FROM ProjectInfo pi2 "
        f"WHERE pi2.task IN ({placeholders}))"
    )
    params.extend(query.project_ids)
```

**Target shape** (simpler — direct PK lookup, no subquery):
```python
# Replaces the above block; conditions accumulate identically
if query.task_id_scope is not None and len(query.task_id_scope) > 0:
    placeholders = ",".join("?" * len(query.task_id_scope))
    conditions.append(f"t.persistentIdentifier IN ({placeholders})")
    params.extend(query.task_id_scope)
```

**AND-composition unchanged.** The WHERE assembly at line 294-296 (`where_suffix = " AND " + " AND ".join(conditions)`) consumes the new condition identically to the old one.

**Tag-filter pattern is adjacent** (line 267-274) — useful reference for how another "IN (?, ?, ?)" clause composes, but `task_id_scope` is even simpler (no subquery to TaskToTag).

---

### `repository/bridge_only/bridge_only.py` — Python filter rewrite

**Analog (in-file):** existing `project_ids` block at line 227-229, existing `tag_ids` block at line 230-232.

**Existing pattern to REPLACE** (line 227-229):
```python
if query.project_ids is not None:
    pid_set = set(query.project_ids)
    items = [t for t in items if t.project.id in pid_set]
```

**Target shape** (field rename + semantic shift from "project.id" to "task.id"):
```python
if query.task_id_scope is not None:
    scope_set = set(query.task_id_scope)
    items = [t for t in items if t.id in scope_set]
```

**Ordering & pagination unchanged** (line 254-256 — `items.sort(key=lambda t: t.id)` then `paginate(...)`).

---

### `tests/test_service_subtree.py` (NEW) — unit tests for `expand_scope`

**Analog:** No direct in-file analog for this module. Closest parallels:
- Unit tests on pure `DomainLogic` methods live in `tests/test_service_domain.py`.
- `check_filter_resolution` tests are the closest unit-level parallel (pure function, various input shapes).

**Recommended test shapes** (RESEARCH.md Wave 0 Gaps + Pattern 1 §Descendant collection):

```python
# File: tests/test_service_subtree.py
# Pure-function tests; no fixtures beyond synthetic AllEntities.

import pytest
from omnifocus_operator.models.enums import EntityType
from omnifocus_operator.service.subtree import expand_scope


class TestExpandScope:
    def test_task_anchor_includes_self(self, snapshot_two_level: AllEntities) -> None:
        """PARENT-04/UNIFY-03: task resolution injects anchor."""
        result = expand_scope("task-parent", snapshot_two_level, frozenset({EntityType.TASK, EntityType.PROJECT}))
        assert "task-parent" in result

    def test_task_anchor_includes_all_descendants(self, snapshot_three_level: AllEntities) -> None:
        """PARENT-03: descendants at any depth."""
        # ...

    def test_project_anchor_no_self(self, snapshot_with_project: AllEntities) -> None:
        """PARENT-04/UNIFY-03: project resolution does NOT inject anchor (projects aren't list_tasks rows)."""
        # ...

    def test_project_anchor_all_descendants(self, snapshot_with_project: AllEntities) -> None:
        """PARENT-03: project-case collects all tasks under the project."""
        # ...

    def test_accept_type_restriction(self, snapshot_two_level: AllEntities) -> None:
        """UNIFY-01: accept_entity_types={PROJECT} on a task ID returns empty set."""
        result = expand_scope("task-id", snapshot_two_level, frozenset({EntityType.PROJECT}))
        assert result == set()

    def test_unknown_ref_id_returns_empty(self, snapshot_empty: AllEntities) -> None:
        """Edge case: resolved ID not in snapshot (stale)."""
        # ...
```

**Planner note:** Test fixtures should use `InMemoryBridge` or a directly-constructed `AllEntities` — SAFE-01 applies (no real Bridge).

---

### `tests/test_list_pipelines.py` — parent cases + cross-filter equivalence contract test

**Analog (in-file):** Existing project-filter pipeline cases (file already contains project + tag + date + AND-composition tests).

**Cross-filter equivalence pattern — UNIFY-02 / D-15** (from RESEARCH.md §Validation Architecture):
```python
@pytest.mark.asyncio
async def test_parent_and_project_byte_identical_for_same_project(
    in_memory_service: OperatorService,
) -> None:
    """UNIFY-02 / D-15: parent: 'Work' ≡ project: 'Work' when 'Work' resolves to a project."""
    project_result = await in_memory_service.list_tasks(ListTasksQuery(project="Work"))
    parent_result = await in_memory_service.list_tasks(ListTasksQuery(parent="Work"))

    project_dump = [t.model_dump(mode="json", by_alias=True) for t in project_result.items]
    parent_dump = [t.model_dump(mode="json", by_alias=True) for t in parent_result.items]

    assert project_dump == parent_dump
    assert project_result.total == parent_result.total
    assert project_result.has_more == parent_result.has_more
```

**Warning-behavior tests** (WARN-01/02/03) live alongside parent-filter cases in this file — the pipeline fires them, so pipeline tests assert on `result.warnings` content.

---

### Mechanical test migrations (`project_ids` → `task_id_scope`)

**Affected files** (per RESEARCH.md §Wave 0 Gaps, verified via `grep project_ids` across tests):
- `tests/test_list_contracts.py` — `TestRepoQueryFieldParity::test_tasks_shared_fields_match` at line 446-461 (update literal), `test_list_tasks_repo_query_other_fields_default_none` at line 391 (update literal).
- `tests/test_query_builder.py` — `TestTasksProjectFilter` at line 113-128 (rename to `TestTasksScopeFilter`, rewrite SQL assertions: `t.containingProjectInfo IN` → `t.persistentIdentifier IN`, drop ProjectInfo subquery expectation).
- `tests/test_hybrid_repository.py` — `test_list_tasks_project_filter*` cases (rewrite `ListTasksRepoQuery(project_ids=[...])` → `ListTasksRepoQuery(task_id_scope=[...])` with scope IDs matching expected output).
- `tests/test_cross_path_equivalence.py` — `test_list_tasks_by_project` (same rewrite).
- `tests/test_bridge_contract.py` — live constructions.
- `tests/doubles/bridge.py` — live constructions in bridge doubles.
- `tests/golden_master/normalize.py` — check for any `project_ids` references (RESEARCH.md A3 says goldens are tool-output JSON, not repo-query JSON — but confirm during migration).

**Migration shape** (specimen from `test_query_builder.py:114-120`):
```python
# BEFORE:
def test_project_ids_subquery(self):
    query = ListTasksRepoQuery(project_ids=["proj-id-1"])
    data_q, _ = build_list_tasks_sql(query)
    assert "t.containingProjectInfo IN" in data_q.sql
    assert "ProjectInfo pi2" in data_q.sql
    assert "pi2.task IN (?)" in data_q.sql
    assert "proj-id-1" in data_q.params

# AFTER:
def test_task_id_scope_in_clause(self):
    query = ListTasksRepoQuery(task_id_scope=["task-id-1"])
    data_q, _ = build_list_tasks_sql(query)
    assert "t.persistentIdentifier IN (?)" in data_q.sql
    assert "task-id-1" in data_q.params
    # ProjectInfo subquery is gone — direct PK lookup
    assert "ProjectInfo pi2" not in data_q.sql
```

**Pitfall 4 reminder** (RESEARCH.md): `TestRepoQueryFieldParity::test_tasks_shared_fields_match` has a hard-coded `repo_only = {"project_ids", "tag_ids"} | _date_repo_fields` — must update to `{"task_id_scope", "tag_ids"} | _date_repo_fields`.

---

## Shared Patterns

### Pattern A: `<noun>Filter` → primitive resolution (agent-facing complex → repo primitive)

**Source:** `service/service.py::_resolve_date_filters` (existing `DateFilter` → `due_after`/`due_before`) and `_resolve_project` (line 408-419).

**Apply to:** `_resolve_parent` (new), `_build_repo_query` intersection step.

**Canonical excerpt** — project-filter today:
```python
# src/omnifocus_operator/service/service.py:408-419
def _resolve_project(self) -> None:
    self._project_ids: list[str] | None = None
    if self._project_to_resolve is None:
        return
    resolved = self._resolver.resolve_filter(self._project_to_resolve, self._projects)
    if resolved:
        self._project_ids = resolved
    self._warnings.extend(
        self._domain.check_filter_resolution(
            self._project_to_resolve, resolved, self._projects, "project"
        )
    )
```

**Applies everywhere a resolved filter lands on `ListTasksRepoQuery`.** After Phase 57, both `_resolve_project` and `_resolve_parent` produce scope sets that converge on `task_id_scope` inside `_build_repo_query`.

---

### Pattern B: Method Object pipeline step attachment

**Source:** `service/service.py` lines 317-473 (`_ReadPipeline` + `_ListTasksPipeline`).

**Apply to:** All new pipeline steps (`_resolve_parent`, `_check_inbox_parent_warning`).

**Canonical excerpt — attachment order in `execute`** (line 375-399):
```python
async def execute(self, query: ListTasksQuery) -> ListResult[Task]:
    self._query = query
    tags_result, projects_result = await asyncio.gather(...)
    self._in_inbox, self._project_to_resolve = self._resolver.resolve_inbox(...)
    self._check_inbox_project_warning()
    self._resolve_project()
    self._resolve_tags()
    await self._resolve_date_filters()
    self._build_repo_query()
    return await self._delegate()
```

**Target extension order:**
```python
async def execute(self, query: ListTasksQuery) -> ListResult[Task]:
    self._query = query
    self._snapshot = await self._repository.get_all()  # CHANGED — single-snapshot
    self._tags = self._snapshot.tags   # or list_tags(); planner decision
    self._projects = self._snapshot.projects
    self._tasks = self._snapshot.tasks

    # 3-arg inbox consumption (D-09)
    self._in_inbox, self._project_to_resolve, self._parent_to_resolve = (
        self._resolver.resolve_inbox(
            unset_to_none(self._query.in_inbox),
            unset_to_none(self._query.project),
            unset_to_none(self._query.parent),
        )
    )

    self._check_inbox_project_warning()
    self._check_inbox_parent_warning()       # NEW
    self._resolve_project()
    self._resolve_parent()                   # NEW
    self._resolve_tags()
    await self._resolve_date_filters()
    self._build_repo_query()                 # intersection inside
    self._warnings.extend(self._domain.check_filtered_subtree(self._query))        # WARN-01
    self._warnings.extend(self._domain.check_parent_project_combined(self._query)) # WARN-03
    return await self._delegate()
```

---

### Pattern C: Warning constant authoring (parameterized multi-line strings)

**Source:** `agent_messages/warnings.py` — conventions used throughout (line 10-195).

**Apply to:** New `FILTERED_SUBTREE_WARNING`, `PARENT_RESOLVES_TO_PROJECT_WARNING`, `PARENT_PROJECT_COMBINED_WARNING`.

**Key conventions:**
- Triple-quoted `"""\ ... """` with leading backslash to avoid newline after opening quote.
- Trailing backslash at each intermediate line to join into a single string.
- `{placeholder}` syntax for `.format()` at call site.
- Section headers as `# --- Section Name ---` comments group related constants.

**Canonical excerpt** (line 171-175 — `LIST_TASKS_INBOX_PROJECT_WARNING`):
```python
LIST_TASKS_INBOX_PROJECT_WARNING = """\
The 'project="{value}"' filter also matches the OmniFocus Inbox by name, \
but the Inbox is a virtual location, not a named project. \
Inbox tasks are not included in these results. \
Use 'inInbox=true' to query them."""
```

---

### Pattern D: Null-filter rejection via `reject_null_filters` + `_PATCH_FIELDS` list

**Source:** `contracts/use_cases/list/tasks.py:52-96` and `contracts/use_cases/list/_validators.py::reject_null_filters`.

**Apply to:** `parent` field addition — append `"parent"` to `_PATCH_FIELDS` list (single-line change).

**Canonical excerpt** (line 52-96):
```python
_PATCH_FIELDS = [
    "in_inbox", "flagged", "project", "tags",
    "estimated_minutes_max", "search",
    "due", "defer", "planned", "completed", "dropped", "added", "modified",
]

class ListTasksQuery(QueryModel):
    # ... fields ...

    @model_validator(mode="before")
    @classmethod
    def _reject_nulls(cls, data: dict[str, object]) -> dict[str, object]:
        if isinstance(data, dict):
            reject_null_filters(data, _PATCH_FIELDS)
        return data
```

**Effect:** `ListTasksQuery(parent=None)` raises `ValidationError` with `FILTER_NULL.format(field="parent")` message. No new validator needed — the helper is generic.

---

### Pattern E: Deterministic SQL placeholder ordering

**Source:** Pitfall 5 in RESEARCH.md (preventative — no existing bug to fix).

**Apply to:** All conversions `set[str]` → `list[str]` for `task_id_scope`.

**Rule:** When assigning to `ListTasksRepoQuery.task_id_scope`, always `sorted(scope_set)`. Tests that assert on SQL param ordering (e.g., `"proj-1" in data_q.params` works regardless, but order-dependent list equality checks require sorting) become deterministic.

**Canonical excerpt:**
```python
# In _build_repo_query:
task_id_scope = sorted(intersected_scope_set)  # NOT list(intersected_scope_set)
```

---

## No Analog Found

None. Phase 57 is entirely assembly of existing components.

## Metadata

**Analog search scope:**
- `src/omnifocus_operator/` (all service, contract, repository, agent_messages modules)
- `tests/` (contract tests, pipeline tests, query builder tests)
- `docs/architecture.md` and `docs/model-taxonomy.md` for convention references

**Files scanned:**
- `service/service.py` (473 lines — read lines 1-80, 318-473)
- `service/resolve.py` (read lines 60-280)
- `service/domain.py` (read lines 210-538)
- `contracts/use_cases/list/tasks.py` (read in full — 148 lines)
- `agent_messages/warnings.py` (read in full — 195 lines)
- `agent_messages/descriptions.py` (read lines 430-490)
- `repository/hybrid/query_builder.py` (read lines 230-319)
- `repository/bridge_only/bridge_only.py` (read lines 210-270)
- `tests/test_list_contracts.py` (grepped `TestRepoQueryFieldParity`, `parent null` patterns)
- `tests/test_query_builder.py` (read lines 113-155)
- `tests/test_service_resolve.py` (grepped `TestResolveInbox`)

**Pattern extraction date:** 2026-04-20

**Project-skills consulted:** `.claude/skills/test-omnifocus-operator/SKILL.md` (snapshot coverage discipline — not load-bearing for Phase 57 since it's a filter addition, not a model-shape change).

**Project-instruction gates flagged for planner:**
- **CLAUDE.md "After modifying any model that appears in tool output":** `ListTasksQuery` appears in tool inputSchema (not outputSchema), but run `uv run pytest tests/test_output_schema.py -x -q` after contract change per blanket rule.
- **CLAUDE.md Method Object pattern:** `_ListTasksPipeline` already follows this; new `_resolve_parent` step attaches without ceremony.
- **Model taxonomy:** No new Pydantic model introduced (`parent: Patch[str]` is a scalar field, not a `<noun>Filter` class). Taxonomy gate doesn't apply.
- **Memory-only decision "Contracts are pure data":** No `@model_serializer` or `@field_serializer` on any Phase 57 contract. Safe.
- **Memory-only decision "Pre-release, no compat":** `project_ids` field removed outright with no backwards-compat layer.
