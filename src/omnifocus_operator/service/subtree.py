"""Service-layer scope expansion for project + parent filters (UNIFY-01/D-02).

Phase 57 unifies the ``project`` and ``parent`` ``list_tasks`` filters on a
single repo primitive (``ListTasksRepoQuery.task_id_scope``) and a single
service-layer expansion helper defined here.

``get_tasks_subtree`` takes a resolved entity ID and returns the set of task IDs
the entity scopes — dispatching on whether the ID is a task or a project:

- Task anchor → ``{ref_id} | {descendants}`` (the task itself is included
  because tasks are ``list_tasks`` rows).
- Project branch → ``{task.id for task in snapshot.tasks if task.project.id == ref_id}``
  (projects are NOT ``list_tasks`` rows; no anchor is injected).

The helper is a pure, synchronous function: the caller passes in the snapshot,
so no repository round-trip happens here. This matches the
``compute_true_inheritance`` neighbour in ``domain.py`` — that one walks
ancestors UP, this one walks descendants DOWN.

Callers are trusted to pass IDs that came from the resolver (i.e. the ID is
known to be a project or task). Unknown IDs return ``set()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnifocus_operator.models.snapshot import AllEntities
    from omnifocus_operator.models.task import Task


def get_tasks_subtree(ref_id: str, snapshot: AllEntities) -> set[str]:
    """Expand a resolved entity ID to the set of task IDs it scopes.

    Dispatches on ``ref_id``'s type in the snapshot:

    - Task → ``{ref_id} | {all descendant task ids}`` (task is its own anchor).
    - Project → ``{task ids whose containing project is ref_id}`` (no anchor;
      projects are not ``list_tasks`` rows).
    - Unknown → ``set()``.
    """
    if any(t.id == ref_id for t in snapshot.tasks):
        return {ref_id} | _collect_task_descendants(ref_id, snapshot.tasks)

    if any(p.id == ref_id for p in snapshot.projects):
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
