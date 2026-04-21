"""Unit tests for ``service/subtree.py::expand_scope`` (Phase 57-01 Task 1).

Covers PARENT-03, PARENT-04, UNIFY-01, UNIFY-03:
- Task-as-anchor (PARENT-04, UNIFY-03): resolved task is included in the set.
- Descendant-at-any-depth (PARENT-03): BFS returns all descendants.
- Project-no-anchor (PARENT-04, UNIFY-03): project ID is NOT in the set.
- accept_entity_types gating (UNIFY-01): gating via frozenset.
- Disjoint-subtree isolation (UNIFY-03): unrelated branches are excluded.

Tests build synthetic ``AllEntities`` directly. No repository, no async,
no bridge — pure function testing (SAFE-01 compliant by construction).
"""

from __future__ import annotations

import pytest

from omnifocus_operator.models.enums import EntityType
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.service.subtree import expand_scope
from tests.conftest import make_model_project_dict, make_model_task_dict

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task(task_id: str, *, project_id: str, parent_task_id: str | None = None) -> dict:
    """Build a model-format task dict with parent/project references.

    - If parent_task_id is None, parent points at the containing project (root task).
    - If parent_task_id is set, parent points at another task.
    - project is always the containing project at any depth.
    """
    parent = (
        {"task": {"id": parent_task_id, "name": parent_task_id}}
        if parent_task_id is not None
        else {"project": {"id": project_id, "name": project_id}}
    )
    return make_model_task_dict(
        id=task_id,
        name=task_id,
        url=f"omnifocus:///task/{task_id}",
        parent=parent,
        project={"id": project_id, "name": project_id},
    )


def _project(project_id: str) -> dict:
    """Build a model-format project dict."""
    return make_model_project_dict(
        id=project_id,
        name=project_id,
        url=f"omnifocus:///project/{project_id}",
    )


def _snapshot(tasks: list[dict], projects: list[dict]) -> AllEntities:
    """Build a validated AllEntities from dicts."""
    return AllEntities.model_validate(
        {
            "tasks": tasks,
            "projects": projects,
            "tags": [],
            "folders": [],
            "perspectives": [],
        }
    )


_ACCEPT_BOTH = frozenset({EntityType.TASK, EntityType.PROJECT})


# ---------------------------------------------------------------------------
# Fixtures: shared synthetic snapshots
# ---------------------------------------------------------------------------


@pytest.fixture
def snapshot_two_level() -> AllEntities:
    """Project "proj-a" with root task "root" that has two children: "child-1" + "child-2"."""
    return _snapshot(
        tasks=[
            _task("root", project_id="proj-a"),
            _task("child-1", project_id="proj-a", parent_task_id="root"),
            _task("child-2", project_id="proj-a", parent_task_id="root"),
        ],
        projects=[_project("proj-a")],
    )


@pytest.fixture
def snapshot_three_level() -> AllEntities:
    """Project "proj-a" with a three-level subtree: top → mid → leaf."""
    return _snapshot(
        tasks=[
            _task("top", project_id="proj-a"),
            _task("mid", project_id="proj-a", parent_task_id="top"),
            _task("leaf", project_id="proj-a", parent_task_id="mid"),
        ],
        projects=[_project("proj-a")],
    )


@pytest.fixture
def snapshot_with_project() -> AllEntities:
    """Project "proj-a" with 3 tasks (some nested) and project "proj-b" with 1 task.

    Tasks under proj-a:
      - "a-root" (root)
      - "a-child" (child of a-root)
      - "a-other" (root, sibling of a-root)
    Task under proj-b:
      - "b-task" (unrelated branch)
    """
    return _snapshot(
        tasks=[
            _task("a-root", project_id="proj-a"),
            _task("a-child", project_id="proj-a", parent_task_id="a-root"),
            _task("a-other", project_id="proj-a"),
            _task("b-task", project_id="proj-b"),
        ],
        projects=[_project("proj-a"), _project("proj-b")],
    )


@pytest.fixture
def snapshot_disjoint() -> AllEntities:
    """Two disjoint task subtrees under the same project:

    Tree A: "a-root" → "a-child"
    Tree B: "b-root" → "b-child"
    """
    return _snapshot(
        tasks=[
            _task("a-root", project_id="proj-a"),
            _task("a-child", project_id="proj-a", parent_task_id="a-root"),
            _task("b-root", project_id="proj-a"),
            _task("b-child", project_id="proj-a", parent_task_id="b-root"),
        ],
        projects=[_project("proj-a")],
    )


@pytest.fixture
def snapshot_leaf_only() -> AllEntities:
    """Project "proj-a" with a single leaf task (no children)."""
    return _snapshot(
        tasks=[_task("leaf", project_id="proj-a")],
        projects=[_project("proj-a")],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExpandScope:
    """Unit tests for expand_scope — pure-function behavior."""

    def test_task_anchor_includes_self(self, snapshot_two_level: AllEntities) -> None:
        """PARENT-04 / UNIFY-03: task resolution injects the anchor into the set."""
        result = expand_scope("root", snapshot_two_level, _ACCEPT_BOTH)
        assert "root" in result

    def test_task_anchor_includes_direct_children(self, snapshot_two_level: AllEntities) -> None:
        """PARENT-03: direct children of the anchor task are included."""
        result = expand_scope("root", snapshot_two_level, _ACCEPT_BOTH)
        assert result == {"root", "child-1", "child-2"}

    def test_task_anchor_includes_descendants_any_depth(
        self, snapshot_three_level: AllEntities
    ) -> None:
        """PARENT-03: descendants at any depth are included (BFS walks whole subtree)."""
        result = expand_scope("top", snapshot_three_level, _ACCEPT_BOTH)
        assert result == {"top", "mid", "leaf"}

    def test_project_returns_no_anchor(self, snapshot_with_project: AllEntities) -> None:
        """PARENT-04 / UNIFY-03: project ID is NOT in the returned set.

        Projects are not list_tasks rows, so they never appear as anchors.
        """
        result = expand_scope("proj-a", snapshot_with_project, _ACCEPT_BOTH)
        assert "proj-a" not in result

    def test_project_returns_all_project_tasks(self, snapshot_with_project: AllEntities) -> None:
        """PARENT-03: project branch returns all tasks whose containing project matches."""
        result = expand_scope("proj-a", snapshot_with_project, _ACCEPT_BOTH)
        # a-root, a-child, and a-other all have project.id == "proj-a"
        assert result == {"a-root", "a-child", "a-other"}

    def test_accept_type_restriction_task_id_with_project_only(
        self, snapshot_two_level: AllEntities
    ) -> None:
        """UNIFY-01: task ID with accept={PROJECT} only → empty set.

        project-only accept set short-circuits the task-anchor branch.
        """
        result = expand_scope("root", snapshot_two_level, frozenset({EntityType.PROJECT}))
        assert result == set()

    def test_accept_type_restriction_project_id_with_task_only(
        self, snapshot_with_project: AllEntities
    ) -> None:
        """UNIFY-01: project ID with accept={TASK} only → empty set.

        task-only accept set short-circuits the project branch.
        """
        result = expand_scope("proj-a", snapshot_with_project, frozenset({EntityType.TASK}))
        assert result == set()

    def test_unknown_ref_id_returns_empty(self, snapshot_two_level: AllEntities) -> None:
        """Edge: ID not in tasks or projects → empty set."""
        result = expand_scope("does-not-exist", snapshot_two_level, _ACCEPT_BOTH)
        assert result == set()

    def test_task_with_no_children_returns_only_self(self, snapshot_leaf_only: AllEntities) -> None:
        """Leaf task (no descendants) → result contains only the anchor."""
        result = expand_scope("leaf", snapshot_leaf_only, _ACCEPT_BOTH)
        assert result == {"leaf"}

    def test_disjoint_subtrees_not_included(self, snapshot_disjoint: AllEntities) -> None:
        """UNIFY-03: expanding Tree A must NOT include any of Tree B's task IDs.

        Siblings at the project root must not leak across subtrees.
        """
        result = expand_scope("a-root", snapshot_disjoint, _ACCEPT_BOTH)
        assert result == {"a-root", "a-child"}
        # Explicit isolation assertions
        assert "b-root" not in result
        assert "b-child" not in result
