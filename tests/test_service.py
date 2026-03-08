"""Tests for OperatorService, ConstantMtimeSource, and bridge factory.

Covers the service layer (thin passthrough to repository), the constant
mtime source (always returns 0 for InMemoryBridge usage), and the bridge
factory function (creates the appropriate bridge implementation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from datetime import UTC

from omnifocus_operator.bridge import BridgeError, InMemoryBridge, create_bridge
from omnifocus_operator.bridge.mtime import ConstantMtimeSource, MtimeSource
from omnifocus_operator.repository import InMemoryRepository
from omnifocus_operator.service import OperatorService

from .conftest import make_snapshot, make_task_dict

# ---------------------------------------------------------------------------
# OperatorService
# ---------------------------------------------------------------------------


class TestOperatorService:
    """OperatorService delegates to repository and passes through results."""

    async def test_get_all_data_returns_snapshot(self) -> None:
        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.get_all_data()

        assert len(result.tasks) == 1
        assert len(result.projects) == 1
        assert len(result.tags) == 1
        assert len(result.folders) == 1
        assert len(result.perspectives) == 1

    async def test_get_all_data_delegates_to_repository(self) -> None:
        """Service returns the exact snapshot from the repository."""
        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.get_all_data()

        assert result is snapshot

    async def test_get_all_data_propagates_errors(self) -> None:
        """Service propagates errors from the repository unchanged."""
        from unittest.mock import AsyncMock

        mock_repo = AsyncMock()
        mock_repo.get_all.side_effect = BridgeError("snapshot", "connection lost")
        service = OperatorService(repository=mock_repo)

        with pytest.raises(BridgeError, match="connection lost"):
            await service.get_all_data()

    async def test_get_task_delegates_to_repository(self) -> None:
        """Service.get_task delegates to repository and returns result."""
        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.get_task("task-001")
        assert result is not None
        assert result.id == "task-001"

    async def test_get_task_returns_none_when_not_found(self) -> None:
        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.get_task("nonexistent")
        assert result is None

    async def test_get_project_delegates_to_repository(self) -> None:
        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.get_project("proj-001")
        assert result is not None
        assert result.id == "proj-001"

    async def test_get_project_returns_none_when_not_found(self) -> None:
        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.get_project("nonexistent")
        assert result is None

    async def test_get_tag_delegates_to_repository(self) -> None:
        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.get_tag("tag-001")
        assert result is not None
        assert result.id == "tag-001"

    async def test_get_tag_returns_none_when_not_found(self) -> None:
        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.get_tag("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# OperatorService.add_task
# ---------------------------------------------------------------------------


class TestAddTask:
    """Service.add_task validates inputs and delegates to repository."""

    async def test_create_minimal(self) -> None:
        """Name-only spec creates task and returns TaskCreateResult."""
        from omnifocus_operator.models.write import TaskCreateResult, TaskCreateSpec

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.add_task(TaskCreateSpec(name="Buy milk"))

        assert isinstance(result, TaskCreateResult)
        assert result.success is True
        assert result.name == "Buy milk"

    async def test_create_with_parent_project(self) -> None:
        """Parent ID matching a project resolves successfully."""
        from omnifocus_operator.models.write import TaskCreateSpec

        snapshot = make_snapshot()  # has proj-001
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.add_task(TaskCreateSpec(name="Sub task", parent="proj-001"))
        assert result.success is True

    async def test_create_with_parent_task(self) -> None:
        """Parent ID matching a task (not project) resolves successfully."""
        from omnifocus_operator.models.write import TaskCreateSpec

        snapshot = make_snapshot()  # has task-001
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.add_task(TaskCreateSpec(name="Sub task", parent="task-001"))
        assert result.success is True

    async def test_no_parent_inbox(self) -> None:
        """No parent -> task goes to inbox."""
        from omnifocus_operator.models.write import TaskCreateSpec

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.add_task(TaskCreateSpec(name="Inbox task"))
        assert result.success is True

    async def test_parent_not_found(self) -> None:
        """Non-existent parent raises ValueError."""
        from omnifocus_operator.models.write import TaskCreateSpec

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Parent not found: nonexistent-id"):
            await service.add_task(TaskCreateSpec(name="Task", parent="nonexistent-id"))

    async def test_tags_by_name(self) -> None:
        """Case-insensitive tag name resolution."""
        from omnifocus_operator.models.write import TaskCreateSpec

        from .conftest import make_tag_dict

        snapshot = make_snapshot(
            tags=[
                make_tag_dict(id="tag-work", name="Work"),
            ]
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        # "work" (lowercase) should match "Work"
        result = await service.add_task(TaskCreateSpec(name="Task", tags=["work"]))
        assert result.success is True

    async def test_tags_by_id_fallback(self) -> None:
        """Tag name that doesn't match tries ID fallback."""
        from omnifocus_operator.models.write import TaskCreateSpec

        from .conftest import make_tag_dict

        snapshot = make_snapshot(
            tags=[
                make_tag_dict(id="tag-work", name="Work"),
            ]
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        # "tag-work" as name doesn't match, but as ID it does
        result = await service.add_task(TaskCreateSpec(name="Task", tags=["tag-work"]))
        assert result.success is True

    async def test_tag_not_found(self) -> None:
        """Non-existent tag raises ValueError."""
        from omnifocus_operator.models.write import TaskCreateSpec

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Tag not found"):
            await service.add_task(TaskCreateSpec(name="Task", tags=["nonexistent"]))

    async def test_tag_ambiguous(self) -> None:
        """Multiple tags with same name raises ValueError with IDs listed."""
        from omnifocus_operator.models.write import TaskCreateSpec

        from .conftest import make_tag_dict

        snapshot = make_snapshot(
            tags=[
                make_tag_dict(id="tag-a", name="Work"),
                make_tag_dict(id="tag-b", name="Work"),
            ]
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Ambiguous tag") as exc_info:
            await service.add_task(TaskCreateSpec(name="Task", tags=["Work"]))
        # Error should include both IDs
        assert "tag-a" in str(exc_info.value)
        assert "tag-b" in str(exc_info.value)

    async def test_all_fields(self) -> None:
        """Spec with all fields creates task successfully."""

        from omnifocus_operator.models.write import TaskCreateSpec

        from .conftest import make_tag_dict

        snapshot = make_snapshot(
            tags=[
                make_tag_dict(id="tag-work", name="Work"),
            ]
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        from datetime import datetime

        spec = TaskCreateSpec(
            name="Full task",
            parent="proj-001",
            tags=["Work"],
            due_date=datetime(2026, 3, 15, 10, 0, tzinfo=UTC),
            defer_date=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
            planned_date=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
            flagged=True,
            estimated_minutes=45.0,
            note="Some note",
        )
        result = await service.add_task(spec)
        assert result.success is True

    async def test_empty_name(self) -> None:
        """Empty string name raises ValueError."""
        from omnifocus_operator.models.write import TaskCreateSpec

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Task name is required"):
            await service.add_task(TaskCreateSpec(name=""))

    async def test_whitespace_name(self) -> None:
        """Whitespace-only name raises ValueError."""
        from omnifocus_operator.models.write import TaskCreateSpec

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Task name is required"):
            await service.add_task(TaskCreateSpec(name="   "))

    async def test_validation_before_write(self) -> None:
        """Validation error prevents repository.add_task from being called."""
        from unittest.mock import AsyncMock

        from omnifocus_operator.models.write import TaskCreateSpec

        mock_repo = AsyncMock()
        mock_repo.get_project.return_value = None
        mock_repo.get_task.return_value = None
        service = OperatorService(repository=mock_repo)

        with pytest.raises(ValueError, match="Parent not found"):
            await service.add_task(TaskCreateSpec(name="Task", parent="bad-id"))

        mock_repo.add_task.assert_not_called()


# ---------------------------------------------------------------------------
# OperatorService.edit_task
# ---------------------------------------------------------------------------


class TestEditTask:
    """Service.edit_task validates inputs and delegates to repository."""

    async def test_patch_name_only(self) -> None:
        """Editing only name leaves other fields unchanged (EDIT-01)."""
        from omnifocus_operator.models.write import TaskEditSpec

        snapshot = make_snapshot(
            tasks=[make_task_dict(id="task-001", name="Old Name", flagged=True)]
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(TaskEditSpec(id="task-001", name="New Name"))

        assert result.success is True
        assert result.name == "New Name"
        # Verify other fields unchanged
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.flagged is True  # unchanged

    async def test_patch_note_only(self) -> None:
        """Editing only note leaves other fields unchanged."""
        from omnifocus_operator.models.write import TaskEditSpec

        snapshot = make_snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(TaskEditSpec(id="task-001", note="New note"))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.note == "New note"

    async def test_patch_flagged_only(self) -> None:
        """Editing only flagged leaves other fields unchanged."""
        from omnifocus_operator.models.write import TaskEditSpec

        snapshot = make_snapshot(tasks=[make_task_dict(id="task-001", name="Task", flagged=False)])
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(TaskEditSpec(id="task-001", flagged=True))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.flagged is True

    async def test_clear_due_date(self) -> None:
        """Setting due_date=None clears it (EDIT-01)."""
        from omnifocus_operator.models.write import TaskEditSpec

        snapshot = make_snapshot(
            tasks=[make_task_dict(id="task-001", name="Task", dueDate="2026-04-01T10:00:00+00:00")]
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(TaskEditSpec(id="task-001", due_date=None))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.due_date is None

    async def test_set_due_date(self) -> None:
        """Setting due_date to a value updates it (EDIT-02)."""
        from datetime import datetime

        from omnifocus_operator.models.write import TaskEditSpec

        snapshot = make_snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            TaskEditSpec(id="task-001", due_date=datetime(2026, 5, 1, 10, 0, tzinfo=UTC))
        )
        assert result.success is True

    async def test_set_estimated_minutes(self) -> None:
        """Setting estimated_minutes updates it (EDIT-02)."""
        from omnifocus_operator.models.write import TaskEditSpec

        snapshot = make_snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(TaskEditSpec(id="task-001", estimated_minutes=30.0))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.estimated_minutes == 30.0

    async def test_tag_replace(self) -> None:
        """tags=["tag1"] replaces all tags (EDIT-03)."""
        from omnifocus_operator.models.write import TaskEditSpec

        from .conftest import make_tag_dict

        snapshot = make_snapshot(
            tasks=[
                make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-old", "name": "Old"}])
            ],
            tags=[make_tag_dict(id="tag-new", name="NewTag")],
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(TaskEditSpec(id="task-001", tags=["NewTag"]))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 1
        assert task.tags[0].id == "tag-new"

    async def test_tag_add(self) -> None:
        """add_tags=["tag2"] adds without removing (EDIT-04)."""
        from omnifocus_operator.models.write import TaskEditSpec

        from .conftest import make_tag_dict

        snapshot = make_snapshot(
            tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
            tags=[
                make_tag_dict(id="tag-a", name="A"),
                make_tag_dict(id="tag-b", name="B"),
            ],
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(TaskEditSpec(id="task-001", add_tags=["B"]))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 2
        tag_ids = {t.id for t in task.tags}
        assert "tag-a" in tag_ids
        assert "tag-b" in tag_ids

    async def test_tag_remove(self) -> None:
        """remove_tags=["tag1"] removes specific tag (EDIT-05)."""
        from omnifocus_operator.models.write import TaskEditSpec

        from .conftest import make_tag_dict

        snapshot = make_snapshot(
            tasks=[
                make_task_dict(
                    id="task-001",
                    name="Task",
                    tags=[{"id": "tag-a", "name": "A"}, {"id": "tag-b", "name": "B"}],
                )
            ],
            tags=[
                make_tag_dict(id="tag-a", name="A"),
                make_tag_dict(id="tag-b", name="B"),
            ],
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(TaskEditSpec(id="task-001", remove_tags=["A"]))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 1
        assert task.tags[0].id == "tag-b"

    async def test_tag_mutual_exclusivity(self) -> None:
        """tags + add_tags raises ValueError (EDIT-06)."""
        from pydantic import ValidationError

        from omnifocus_operator.models.write import TaskEditSpec

        with pytest.raises(ValidationError, match="Cannot use 'tags'"):
            TaskEditSpec(id="task-001", tags=["a"], add_tags=["b"])

    async def test_add_and_remove_tags_together(self) -> None:
        """add_tags + remove_tags together is allowed (EDIT-06)."""
        from omnifocus_operator.models.write import TaskEditSpec

        from .conftest import make_tag_dict

        snapshot = make_snapshot(
            tasks=[
                make_task_dict(
                    id="task-001",
                    name="Task",
                    tags=[{"id": "tag-a", "name": "A"}],
                )
            ],
            tags=[
                make_tag_dict(id="tag-a", name="A"),
                make_tag_dict(id="tag-b", name="B"),
            ],
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            TaskEditSpec(id="task-001", add_tags=["B"], remove_tags=["A"])
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 1
        assert task.tags[0].id == "tag-b"

    async def test_move_to_project_ending(self) -> None:
        """Move task to project via ending (EDIT-07)."""
        from omnifocus_operator.models.write import MoveToSpec, TaskEditSpec

        snapshot = make_snapshot(
            tasks=[make_task_dict(id="task-001", name="Task", inInbox=True)],
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            TaskEditSpec(id="task-001", move_to=MoveToSpec(ending="proj-001"))
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.parent is not None
        assert task.parent.type == "project"
        assert task.parent.id == "proj-001"
        assert task.in_inbox is False

    async def test_move_to_task_beginning(self) -> None:
        """Move task under another task via beginning (EDIT-07)."""
        from omnifocus_operator.models.write import MoveToSpec, TaskEditSpec

        snapshot = make_snapshot(
            tasks=[
                make_task_dict(id="task-001", name="Task"),
                make_task_dict(id="task-parent", name="Parent Task"),
            ],
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            TaskEditSpec(id="task-001", move_to=MoveToSpec(beginning="task-parent"))
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.parent is not None
        assert task.parent.type == "task"
        assert task.parent.id == "task-parent"

    async def test_move_to_inbox(self) -> None:
        """Move task to inbox via ending=null (EDIT-08)."""
        from omnifocus_operator.models.write import MoveToSpec, TaskEditSpec

        snapshot = make_snapshot(
            tasks=[
                make_task_dict(
                    id="task-001",
                    name="Task",
                    parent={"type": "project", "id": "proj-001", "name": "Project"},
                    inInbox=False,
                )
            ],
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            TaskEditSpec(id="task-001", move_to=MoveToSpec(ending=None))
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.parent is None
        assert task.in_inbox is True

    async def test_cycle_detection(self) -> None:
        """Moving task under its own child raises ValueError."""
        from omnifocus_operator.models.write import MoveToSpec, TaskEditSpec

        # task-parent -> task-child (child's parent is task-parent)
        snapshot = make_snapshot(
            tasks=[
                make_task_dict(id="task-parent", name="Parent"),
                make_task_dict(
                    id="task-child",
                    name="Child",
                    parent={"type": "task", "id": "task-parent", "name": "Parent"},
                ),
            ],
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="circular reference"):
            await service.edit_task(
                TaskEditSpec(id="task-parent", move_to=MoveToSpec(beginning="task-child"))
            )

    async def test_task_not_found(self) -> None:
        """Non-existent task raises ValueError."""
        from omnifocus_operator.models.write import TaskEditSpec

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Task not found"):
            await service.edit_task(TaskEditSpec(id="nonexistent"))

    async def test_empty_name(self) -> None:
        """Empty name raises ValueError."""
        from omnifocus_operator.models.write import TaskEditSpec

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Task name cannot be empty"):
            await service.edit_task(TaskEditSpec(id="task-001", name=""))

    async def test_whitespace_name(self) -> None:
        """Whitespace-only name raises ValueError."""
        from omnifocus_operator.models.write import TaskEditSpec

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Task name cannot be empty"):
            await service.edit_task(TaskEditSpec(id="task-001", name="   "))

    async def test_warning_remove_tag_not_on_task(self) -> None:
        """Removing a tag the task doesn't have produces a warning."""
        from omnifocus_operator.models.write import TaskEditSpec

        from .conftest import make_tag_dict

        snapshot = make_snapshot(
            tasks=[make_task_dict(id="task-001", name="Task", tags=[])],
            tags=[make_tag_dict(id="tag-x", name="X")],
        )
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(TaskEditSpec(id="task-001", remove_tags=["X"]))
        assert result.success is True
        assert result.warnings is not None
        assert any("was not on this task" in w for w in result.warnings)

    async def test_no_warnings_when_none(self) -> None:
        """No warnings when edit is clean."""
        from omnifocus_operator.models.write import TaskEditSpec

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        result = await service.edit_task(TaskEditSpec(id="task-001", name="Updated"))
        assert result.warnings is None


# ---------------------------------------------------------------------------
# ConstantMtimeSource
# ---------------------------------------------------------------------------


class TestConstantMtimeSource:
    """ConstantMtimeSource always returns 0 and satisfies MtimeSource."""

    async def test_always_returns_zero(self) -> None:
        source = ConstantMtimeSource()

        first = await source.get_mtime_ns()
        second = await source.get_mtime_ns()

        assert first == 0
        assert second == 0

    async def test_satisfies_mtime_protocol(self) -> None:
        source = ConstantMtimeSource()

        assert isinstance(source, MtimeSource)


# ---------------------------------------------------------------------------
# Bridge factory (create_bridge)
# ---------------------------------------------------------------------------


class TestCreateBridge:
    """create_bridge() factory returns the correct bridge or raises."""

    def test_inmemory_returns_inmemory_bridge(self) -> None:
        bridge = create_bridge("inmemory")

        assert isinstance(bridge, InMemoryBridge)

    def test_simulator_returns_simulator_bridge(self) -> None:
        from omnifocus_operator.bridge.simulator import SimulatorBridge

        bridge = create_bridge("simulator")
        assert isinstance(bridge, SimulatorBridge)

    def test_real_refused_during_pytest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SAFE-01: create_bridge('real') is refused during automated testing."""
        monkeypatch.setenv("OMNIFOCUS_IPC_DIR", str(tmp_path))
        with pytest.raises(RuntimeError, match="PYTEST_CURRENT_TEST"):
            create_bridge("real")

    def test_unknown_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown bridge type"):
            create_bridge("something_else")


# ---------------------------------------------------------------------------
# ErrorOperatorService
# ---------------------------------------------------------------------------


class TestErrorOperatorService:
    """ErrorOperatorService serves startup errors through tool responses."""

    def test_getattr_raises_runtime_error(self) -> None:
        from omnifocus_operator.service import ErrorOperatorService

        service = ErrorOperatorService(ValueError("bad config"))

        with pytest.raises(RuntimeError, match="OmniFocus Operator failed to start"):
            _ = service._repository

    def test_getattr_raises_for_arbitrary_attribute(self) -> None:
        from omnifocus_operator.service import ErrorOperatorService

        service = ErrorOperatorService(ValueError("bad config"))

        with pytest.raises(RuntimeError, match="bad config"):
            _ = service.some_future_method

    def test_error_message_includes_restart_instruction(self) -> None:
        from omnifocus_operator.service import ErrorOperatorService

        service = ErrorOperatorService(ValueError("bad config"))

        with pytest.raises(RuntimeError, match="Restart the server after fixing"):
            _ = service._repository

    def test_getattr_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        from omnifocus_operator.service import ErrorOperatorService

        service = ErrorOperatorService(ValueError("bad config"))

        with caplog.at_level(logging.WARNING), pytest.raises(RuntimeError):
            _ = service._repository

        assert any("error mode" in r.message.lower() for r in caplog.records)

    def test_does_not_call_super_init(self) -> None:
        from omnifocus_operator.service import ErrorOperatorService

        service = ErrorOperatorService(ValueError("x"))

        assert "_repository" not in service.__dict__
