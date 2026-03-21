"""Unit tests for DomainLogic -- business rules for the edit-task pipeline.

Tests use StubResolver and StubRepo (no repository dependency),
independent of repository implementation.
"""

from __future__ import annotations

import pytest

from omnifocus_operator.agent_messages.warnings import (
    EDIT_COMPLETED_TASK,
    LIFECYCLE_REPEATING_COMPLETE,
    LIFECYCLE_REPEATING_DROP,
)
from omnifocus_operator.contracts.base import _Unset
from omnifocus_operator.contracts.common import MoveAction, TagAction
from omnifocus_operator.contracts.use_cases.edit_task import (
    EditTaskActions,
    EditTaskCommand,
    EditTaskRepoPayload,
)
from omnifocus_operator.models.common import TagRef
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.models.task import Task
from omnifocus_operator.service.domain import DomainLogic

from .conftest import make_snapshot, make_tag_dict, make_task_dict

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class StubResolver:
    """Returns pre-configured IDs. No repository dependency."""

    def __init__(
        self,
        tag_map: dict[str, str] | None = None,
        tasks: list[Task] | None = None,
    ) -> None:
        self._tag_map = tag_map or {}
        self._tasks = {t.id: t for t in (tasks or [])}

    async def resolve_tags(self, names: list[str]) -> list[str]:
        return [self._tag_map[n] for n in names]

    async def resolve_parent(self, pid: str) -> str:
        return pid  # always succeeds

    async def resolve_task(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            msg = f"Task not found: {task_id}"
            raise ValueError(msg)
        return task


class StubRepo:
    """Minimal repo for DomainLogic tests. Returns pre-configured data."""

    def __init__(
        self,
        tasks: list[Task] | None = None,
        tags: list[object] | None = None,
        snapshot: AllEntities | None = None,
    ) -> None:
        if snapshot is not None:
            self._snapshot = snapshot
        else:
            self._snapshot = AllEntities.model_validate(
                {
                    "tasks": [],
                    "projects": [],
                    "tags": [],
                    "folders": [],
                    "perspectives": [],
                }
            )
            if tasks:
                self._snapshot.tasks.extend(tasks)
            if tags:
                self._snapshot.tags.extend(tags)  # type: ignore[arg-type]

    async def get_all(self) -> AllEntities:
        return self._snapshot

    async def get_task(self, task_id: str) -> Task | None:
        return next((t for t in self._snapshot.tasks if t.id == task_id), None)

    async def get_project(self, project_id: str) -> object:
        return next((p for p in self._snapshot.projects if p.id == project_id), None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(**overrides: object) -> Task:
    """Create a Task model from make_task_dict defaults."""
    return Task.model_validate(make_task_dict(**overrides))


def _domain(
    tag_map: dict[str, str] | None = None,
    tasks: list[Task] | None = None,
    tags: list[object] | None = None,
    snapshot: AllEntities | None = None,
) -> DomainLogic:
    """Build a DomainLogic with stub dependencies."""
    resolver = StubResolver(tag_map, tasks=tasks)
    repo = StubRepo(tasks=tasks, tags=tags, snapshot=snapshot)
    return DomainLogic(repo, resolver)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# process_lifecycle
# ---------------------------------------------------------------------------


class TestProcessLifecycle:
    """Lifecycle state transitions and warning generation."""

    def test_complete_available_task(self) -> None:
        task = _make_task(availability="available")
        should_call, warnings = _domain().process_lifecycle("complete", task)
        assert should_call is True
        assert warnings == []

    def test_complete_already_completed(self) -> None:
        task = _make_task(availability="completed")
        should_call, warnings = _domain().process_lifecycle("complete", task)
        assert should_call is False
        assert len(warnings) == 1
        assert "already complete" in warnings[0].lower()

    def test_drop_already_dropped(self) -> None:
        task = _make_task(availability="dropped")
        should_call, warnings = _domain().process_lifecycle("drop", task)
        assert should_call is False
        assert len(warnings) == 1
        assert "already dropped" in warnings[0].lower()

    def test_cross_state_completed_to_dropped(self) -> None:
        task = _make_task(availability="completed")
        should_call, warnings = _domain().process_lifecycle("drop", task)
        assert should_call is True
        assert any("completed" in w and "drop" in w.lower() for w in warnings)

    def test_repeating_complete(self) -> None:
        task = _make_task(
            repetitionRule={
                "ruleString": "FREQ=WEEKLY",
                "scheduleType": "regularly",
                "anchorDateKey": "due_date",
                "catchUpAutomatically": False,
            }
        )
        should_call, warnings = _domain().process_lifecycle("complete", task)
        assert should_call is True
        assert LIFECYCLE_REPEATING_COMPLETE in warnings

    def test_repeating_drop(self) -> None:
        task = _make_task(
            repetitionRule={
                "ruleString": "FREQ=WEEKLY",
                "scheduleType": "regularly",
                "anchorDateKey": "due_date",
                "catchUpAutomatically": False,
            }
        )
        should_call, warnings = _domain().process_lifecycle("drop", task)
        assert should_call is True
        assert LIFECYCLE_REPEATING_DROP in warnings


# ---------------------------------------------------------------------------
# check_completed_status
# ---------------------------------------------------------------------------


class TestCheckCompletedStatus:
    """Warns when editing completed/dropped tasks without lifecycle action."""

    def test_completed_without_lifecycle_warns(self) -> None:
        task = _make_task(availability="completed")
        warnings = _domain().check_completed_status(task, has_lifecycle=False)
        assert len(warnings) == 1
        assert "completed" in warnings[0]
        assert "confirm with the user" in warnings[0]

    def test_completed_with_lifecycle_no_warn(self) -> None:
        task = _make_task(availability="completed")
        warnings = _domain().check_completed_status(task, has_lifecycle=True)
        assert warnings == []

    def test_available_no_warn(self) -> None:
        task = _make_task(availability="available")
        warnings = _domain().check_completed_status(task, has_lifecycle=False)
        assert warnings == []


# ---------------------------------------------------------------------------
# compute_tag_diff
# ---------------------------------------------------------------------------


class TestComputeTagDiff:
    """Tag diff computation with stub Resolver."""

    async def test_add_new_tag(self) -> None:
        domain = _domain(
            tag_map={"Work": "tag-work"},
            snapshot=make_snapshot(tags=[make_tag_dict(id="tag-work", name="Work")]),
        )
        current_tags = []  # no tags on task
        add_ids, remove_ids, warnings = await domain.compute_tag_diff(
            TagAction(add=["Work"]),
            current_tags,
        )
        assert "tag-work" in add_ids
        assert remove_ids == []
        assert warnings == []

    async def test_add_existing_tag_warns(self) -> None:
        domain = _domain(
            tag_map={"Work": "tag-work"},
            snapshot=make_snapshot(tags=[make_tag_dict(id="tag-work", name="Work")]),
        )
        current_tags = [TagRef(id="tag-work", name="Work")]
        _add_ids, _remove_ids, warnings = await domain.compute_tag_diff(
            TagAction(add=["Work"]),
            current_tags,
        )
        assert any("already on this task" in w for w in warnings)

    async def test_remove_existing_tag(self) -> None:
        domain = _domain(
            tag_map={"Work": "tag-work"},
            snapshot=make_snapshot(tags=[make_tag_dict(id="tag-work", name="Work")]),
        )
        current_tags = [TagRef(id="tag-work", name="Work")]
        add_ids, remove_ids, warnings = await domain.compute_tag_diff(
            TagAction(remove=["Work"]),
            current_tags,
        )
        assert "tag-work" in remove_ids
        assert add_ids == []
        assert warnings == []

    async def test_remove_absent_tag_warns(self) -> None:
        domain = _domain(
            tag_map={"Work": "tag-work"},
            snapshot=make_snapshot(tags=[make_tag_dict(id="tag-work", name="Work")]),
        )
        current_tags = []  # tag not on task
        _add_ids, _remove_ids, warnings = await domain.compute_tag_diff(
            TagAction(remove=["Work"]),
            current_tags,
        )
        assert any("is not on this task" in w for w in warnings)

    async def test_replace_tags(self) -> None:
        domain = _domain(
            tag_map={"Home": "tag-home"},
            snapshot=make_snapshot(
                tags=[
                    make_tag_dict(id="tag-work", name="Work"),
                    make_tag_dict(id="tag-home", name="Home"),
                ]
            ),
        )
        current_tags = [TagRef(id="tag-work", name="Work")]
        add_ids, remove_ids, warnings = await domain.compute_tag_diff(
            TagAction(replace=["Home"]),
            current_tags,
        )
        assert "tag-home" in add_ids
        assert "tag-work" in remove_ids
        assert warnings == []

    async def test_replace_same_warns(self) -> None:
        domain = _domain(
            tag_map={"Work": "tag-work"},
            snapshot=make_snapshot(tags=[make_tag_dict(id="tag-work", name="Work")]),
        )
        current_tags = [TagRef(id="tag-work", name="Work")]
        add_ids, remove_ids, warnings = await domain.compute_tag_diff(
            TagAction(replace=["Work"]),
            current_tags,
        )
        assert add_ids == []
        assert remove_ids == []
        assert any("already match" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# detect_early_return
# ---------------------------------------------------------------------------


class TestDetectEarlyReturn:
    """No-op and empty-edit detection."""

    def test_empty_edit_no_warnings(self) -> None:
        task = _make_task(id="t1", name="Task")
        payload = EditTaskRepoPayload.model_validate({"id": "t1"})
        result = _domain().detect_early_return(payload, task, [])
        assert result is not None
        assert result.warnings is not None
        assert any("No changes specified" in w for w in result.warnings)

    def test_empty_edit_with_warnings(self) -> None:
        task = _make_task(id="t1", name="Task", availability="completed")
        payload = EditTaskRepoPayload.model_validate({"id": "t1"})
        warnings = [EDIT_COMPLETED_TASK.format(status="completed")]
        result = _domain().detect_early_return(payload, task, warnings)
        assert result is not None
        assert result.warnings is not None
        assert any("completed" in w for w in result.warnings)
        # Should NOT include "No changes specified" when there are existing warnings
        assert not any("No changes specified" in w for w in result.warnings)

    def test_noop_all_fields_match(self) -> None:
        task = _make_task(id="t1", name="Foo")
        payload = EditTaskRepoPayload.model_validate({"id": "t1", "name": "Foo"})
        result = _domain().detect_early_return(payload, task, [])
        assert result is not None
        assert result.warnings is not None
        assert any("No changes detected" in w for w in result.warnings)

    def test_noop_filters_status_warnings(self) -> None:
        task = _make_task(id="t1", name="Foo", availability="completed")
        payload = EditTaskRepoPayload.model_validate({"id": "t1", "name": "Foo"})
        # Status warning contains "your changes were applied"
        warnings = [EDIT_COMPLETED_TASK.format(status="completed")]
        result = _domain().detect_early_return(payload, task, warnings)
        assert result is not None
        assert result.warnings is not None
        # Status warning should be filtered (contains "your changes were applied")
        assert not any("your changes were applied" in w for w in result.warnings)
        # Should have the no-op warning instead
        assert any("No changes detected" in w for w in result.warnings)

    def test_not_noop_returns_none(self) -> None:
        task = _make_task(id="t1", name="Foo")
        payload = EditTaskRepoPayload.model_validate({"id": "t1", "name": "Bar"})
        result = _domain().detect_early_return(payload, task, [])
        assert result is None


# ---------------------------------------------------------------------------
# process_move
# ---------------------------------------------------------------------------


class TestProcessMove:
    """Move processing with stub Resolver."""

    async def test_move_to_inbox(self) -> None:
        domain = _domain()
        result = await domain.process_move(MoveAction(ending=None), "task-1")
        assert result == {"position": "ending", "container_id": None}

    async def test_move_to_project(self) -> None:
        # StubResolver.resolve_parent always succeeds; StubRepo.get_task returns None
        # for the container (it's a project, not a task), so no cycle check
        domain = _domain()
        result = await domain.process_move(MoveAction(ending="proj-1"), "task-1")
        assert result == {"position": "ending", "container_id": "proj-1"}

    async def test_move_before_anchor(self) -> None:
        task = _make_task(id="task-anchor", name="Anchor")
        domain = _domain(tasks=[task])
        result = await domain.process_move(MoveAction(before="task-anchor"), "task-1")
        assert result == {"position": "before", "anchor_id": "task-anchor"}


# ---------------------------------------------------------------------------
# check_cycle
# ---------------------------------------------------------------------------


class TestCheckCycle:
    """Cycle detection in the parent-child graph."""

    async def test_no_cycle_passes(self) -> None:
        parent = _make_task(id="t-parent", name="Parent")
        child = _make_task(
            id="t-child",
            name="Child",
            parent={"type": "task", "id": "t-parent", "name": "Parent"},
        )
        domain = _domain(tasks=[parent, child])
        # Moving t-parent under t-child would be a cycle, but moving
        # an unrelated task under t-parent is fine
        await domain.check_cycle("t-unrelated", "t-parent")  # should not raise

    async def test_cycle_raises(self) -> None:
        parent = _make_task(id="t-parent", name="Parent")
        child = _make_task(
            id="t-child",
            name="Child",
            parent={"type": "task", "id": "t-parent", "name": "Parent"},
        )
        domain = _domain(tasks=[parent, child])
        with pytest.raises(ValueError, match="circular reference"):
            await domain.check_cycle("t-parent", "t-child")


# ---------------------------------------------------------------------------
# normalize_clear_intents
# ---------------------------------------------------------------------------


class TestNormalizeClearIntents:
    """Null-means-clear normalization centralized in DomainLogic."""

    def test_note_none_becomes_empty_string(self) -> None:
        domain = _domain()
        cmd = EditTaskCommand(id="t1", note=None)
        result = domain.normalize_clear_intents(cmd)
        assert result.note == ""

    def test_note_with_value_unchanged(self) -> None:
        domain = _domain()
        cmd = EditTaskCommand(id="t1", note="Hello")
        result = domain.normalize_clear_intents(cmd)
        assert result.note == "Hello"

    def test_note_unset_unchanged(self) -> None:
        domain = _domain()
        cmd = EditTaskCommand(id="t1")
        result = domain.normalize_clear_intents(cmd)
        assert isinstance(result.note, _Unset)

    def test_tags_replace_none_becomes_empty_list(self) -> None:
        domain = _domain()
        cmd = EditTaskCommand(id="t1", actions=EditTaskActions(tags=TagAction(replace=None)))
        result = domain.normalize_clear_intents(cmd)
        assert result.actions.tags.replace == []

    def test_tags_replace_with_names_unchanged(self) -> None:
        domain = _domain()
        cmd = EditTaskCommand(id="t1", actions=EditTaskActions(tags=TagAction(replace=["Work"])))
        result = domain.normalize_clear_intents(cmd)
        assert result.actions.tags.replace == ["Work"]

    def test_no_actions_unchanged(self) -> None:
        domain = _domain()
        cmd = EditTaskCommand(id="t1", name="Foo")
        result = domain.normalize_clear_intents(cmd)
        assert result.name == "Foo"
