"""Service-layer scope expansion for project + parent filters (UNIFY-01/D-02).

Phase 57 unifies the ``project`` and ``parent`` ``list_tasks`` filters on a
single repo primitive (``ListTasksRepoQuery.task_id_scope``) and a single
service-layer expansion helper defined here.

``expand_scope`` takes a resolved entity ID plus a frozenset of accepted
entity types and returns the set of task IDs the entity scopes:

- Task anchor → ``{ref_id} | {descendants}`` (the task itself is included
  because tasks are ``list_tasks`` rows).
- Project branch → ``{task.id for task in snapshot.tasks if task.project.id == ref_id}``
  (projects are NOT ``list_tasks`` rows; no anchor is injected).

The helper is a pure, synchronous function: the caller passes in the snapshot,
so no repository round-trip happens here. This matches the
``compute_true_inheritance`` neighbour in ``domain.py`` — that one walks
ancestors UP, this one walks descendants DOWN.
"""

from __future__ import annotations

from omnifocus_operator.models.enums import EntityType
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.models.task import Task


def expand_scope(
    ref_id: str,
    snapshot: AllEntities,
    accept_entity_types: frozenset[EntityType],
) -> set[str]:
    """Expand a resolved entity ID to the set of task IDs it scopes.

    - If ``ref_id`` is a task AND ``EntityType.TASK in accept_entity_types``:
      returns ``{ref_id} | {all descendant task ids}`` (task acts as anchor).
    - If ``ref_id`` is a project AND ``EntityType.PROJECT in accept_entity_types``:
      returns ``{task ids whose containing project is ref_id}`` (no anchor;
      projects are not ``list_tasks`` rows).
    - Otherwise returns ``set()`` (unknown ID or disallowed entity type).
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
    """BFS over ``parent.task.id`` edges. ``anchor_id`` is NOT included.

    Cycle-safety: the OmniFocus data model precludes cycles at the
    task-parent level by construction (``DomainLogic.check_cycle`` is the
    write-side guard). Read-side descent is safe without cycle detection,
    same as ``compute_true_inheritance``'s ancestor walk.
    """
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
