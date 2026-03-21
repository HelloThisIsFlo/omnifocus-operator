"""Tests for OperatorService, ConstantMtimeSource, and bridge factory.

Covers the service layer (thin passthrough to repository), the constant
mtime source (always returns 0 for InMemoryBridge usage), and the bridge
factory function (creates the appropriate bridge implementation).
"""

from __future__ import annotations

from datetime import UTC

import pytest

from omnifocus_operator.bridge import BridgeError
from omnifocus_operator.bridge.mtime import MtimeSource
from omnifocus_operator.repository import BridgeRepository
from omnifocus_operator.service import OperatorService
from tests.doubles import ConstantMtimeSource, InMemoryBridge

from .conftest import make_project_dict, make_snapshot_dict, make_task_dict


# ---------------------------------------------------------------------------
# Shared fixtures (per D-11, D-12, D-13)
# ---------------------------------------------------------------------------


@pytest.fixture
def bridge() -> InMemoryBridge:
    """InMemoryBridge pre-loaded with default snapshot data (per D-11)."""
    return InMemoryBridge(data=make_snapshot_dict())


@pytest.fixture
def repo(bridge: InMemoryBridge) -> BridgeRepository:
    """Repository wired to test bridge with constant mtime (per D-11, D-13)."""
    return BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())

# ---------------------------------------------------------------------------
# OperatorService
# ---------------------------------------------------------------------------


class TestOperatorService:
    """OperatorService delegates to repository and passes through results."""

    async def test_get_all_data_returns_snapshot(self) -> None:
        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.get_all_data()

        assert len(result.tasks) == 1
        assert len(result.projects) == 1
        assert len(result.tags) == 1
        assert len(result.folders) == 1
        assert len(result.perspectives) == 1

    async def test_get_all_data_delegates_to_repository(self) -> None:
        """Service returns a complete snapshot from the repository."""
        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.get_all_data()

        # BridgeRepository deserializes fresh each call; verify structural equality
        assert len(result.tasks) == 1
        assert result.tasks[0].id == "task-001"
        assert len(result.projects) == 1
        assert result.projects[0].id == "proj-001"

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
        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.get_task("task-001")
        assert result is not None
        assert result.id == "task-001"

    async def test_get_task_raises_when_not_found(self) -> None:
        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Task not found: nonexistent"):
            await service.get_task("nonexistent")

    async def test_get_project_delegates_to_repository(self) -> None:
        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.get_project("proj-001")
        assert result is not None
        assert result.id == "proj-001"

    async def test_get_project_raises_when_not_found(self) -> None:
        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Project not found: nonexistent"):
            await service.get_project("nonexistent")

    async def test_get_tag_delegates_to_repository(self) -> None:
        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.get_tag("tag-001")
        assert result is not None
        assert result.id == "tag-001"

    async def test_get_tag_raises_when_not_found(self) -> None:
        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Tag not found: nonexistent"):
            await service.get_tag("nonexistent")


# ---------------------------------------------------------------------------
# OperatorService.add_task
# ---------------------------------------------------------------------------


class TestAddTask:
    """Service.add_task validates inputs and delegates to repository."""

    async def test_create_minimal(self) -> None:
        """Name-only spec creates task and returns AddTaskResult."""
        from omnifocus_operator.contracts.use_cases.add_task import (
            AddTaskCommand,
            AddTaskResult,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.add_task(AddTaskCommand(name="Buy milk"))

        assert isinstance(result, AddTaskResult)
        assert result.success is True
        assert result.name == "Buy milk"

    async def test_create_with_parent_project(self) -> None:
        """Parent ID matching a project resolves successfully."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())  # has proj-001
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.add_task(AddTaskCommand(name="Sub task", parent="proj-001"))
        assert result.success is True

    async def test_create_with_parent_task(self) -> None:
        """Parent ID matching a task (not project) resolves successfully."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())  # has task-001
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.add_task(AddTaskCommand(name="Sub task", parent="task-001"))
        assert result.success is True

    async def test_no_parent_inbox(self) -> None:
        """No parent -> task goes to inbox."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.add_task(AddTaskCommand(name="Inbox task"))
        assert result.success is True

    async def test_parent_not_found(self) -> None:
        """Non-existent parent raises ValueError."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Parent not found: nonexistent-id"):
            await service.add_task(AddTaskCommand(name="Task", parent="nonexistent-id"))

    async def test_tags_by_name(self) -> None:
        """Case-insensitive tag name resolution."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tags=[
                make_tag_dict(id="tag-work", name="Work"),
            ]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        # "work" (lowercase) should match "Work"
        result = await service.add_task(AddTaskCommand(name="Task", tags=["work"]))
        assert result.success is True

    async def test_tags_by_id_fallback(self) -> None:
        """Tag name that doesn't match tries ID fallback."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tags=[
                make_tag_dict(id="tag-work", name="Work"),
            ]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        # "tag-work" as name doesn't match, but as ID it does
        result = await service.add_task(AddTaskCommand(name="Task", tags=["tag-work"]))
        assert result.success is True

    async def test_tag_not_found(self) -> None:
        """Non-existent tag raises ValueError."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Tag not found"):
            await service.add_task(AddTaskCommand(name="Task", tags=["nonexistent"]))

    async def test_tag_ambiguous(self) -> None:
        """Multiple tags with same name raises ValueError with IDs listed."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tags=[
                make_tag_dict(id="tag-a", name="Work"),
                make_tag_dict(id="tag-b", name="Work"),
            ]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Ambiguous tag") as exc_info:
            await service.add_task(AddTaskCommand(name="Task", tags=["Work"]))
        # Error should include both IDs
        assert "tag-a" in str(exc_info.value)
        assert "tag-b" in str(exc_info.value)

    async def test_all_fields(self) -> None:
        """Spec with all fields creates task successfully."""

        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tags=[
                make_tag_dict(id="tag-work", name="Work"),
            ]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        from datetime import datetime

        spec = AddTaskCommand(
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
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Task name is required"):
            await service.add_task(AddTaskCommand(name=""))

    async def test_whitespace_name(self) -> None:
        """Whitespace-only name raises ValueError."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Task name is required"):
            await service.add_task(AddTaskCommand(name="   "))

    async def test_validation_before_write(self) -> None:
        """Validation error prevents repository.add_task from being called."""
        from unittest.mock import AsyncMock

        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        mock_repo = AsyncMock()
        mock_repo.get_project.return_value = None
        mock_repo.get_task.return_value = None
        service = OperatorService(repository=mock_repo)

        with pytest.raises(ValueError, match="Parent not found"):
            await service.add_task(AddTaskCommand(name="Task", parent="bad-id"))

        mock_repo.add_task.assert_not_called()

    async def test_create_hierarchy_in_inbox(self) -> None:
        """Parent task in inbox, then child under that parent (UAT #5)."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        # Create parent in inbox (no parent field)
        parent_result = await service.add_task(AddTaskCommand(name="Parent task"))
        assert parent_result.success is True

        # Create child under that parent
        child_result = await service.add_task(
            AddTaskCommand(name="Child task", parent=parent_result.id)
        )
        assert child_result.success is True

        # Verify child exists in repo
        child = await repo.get_task(child_result.id)
        assert child is not None
        assert child.name == "Child task"

    async def test_multiple_tags(self) -> None:
        """Task with three tags resolves all successfully (UAT #7)."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tags=[
                make_tag_dict(id="tag-a", name="Urgent"),
                make_tag_dict(id="tag-b", name="Work"),
                make_tag_dict(id="tag-c", name="Home"),
            ]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.add_task(
            AddTaskCommand(name="Multi-tag task", tags=["Urgent", "Work", "Home"])
        )
        assert result.success is True

    async def test_planned_date_only(self) -> None:
        """Task with only plannedDate set (no due/defer) succeeds (UAT #11)."""
        from datetime import datetime

        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.add_task(
            AddTaskCommand(
                name="Planned-only task",
                planned_date=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
            )
        )
        assert result.success is True

    async def test_emoji_and_special_chars(self) -> None:
        """Task name with emoji and special characters round-trips (UAT #18)."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        name = '🎯 Buy <milk> & "eggs"'
        result = await service.add_task(AddTaskCommand(name=name))

        assert result.success is True
        assert result.name == name

    async def test_fractional_estimated_minutes(self) -> None:
        """Fractional estimatedMinutes preserved through round-trip (UAT #19)."""
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.add_task(
            AddTaskCommand(name="Fractional estimate", estimated_minutes=150.5)
        )
        assert result.success is True

        task = await repo.get_task(result.id)
        assert task is not None
        assert task.estimated_minutes == 150.5

    async def test_unknown_fields_rejected(self) -> None:
        """Extra fields in model_validate raise ValidationError (STRCT-01)."""
        from pydantic import ValidationError

        from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

        with pytest.raises(ValidationError, match="bogus_field"):
            AddTaskCommand.model_validate({"name": "Task", "bogus_field": "should be rejected"})


# ---------------------------------------------------------------------------
# OperatorService.edit_task
# ---------------------------------------------------------------------------


class TestEditTask:
    """Service.edit_task validates inputs and delegates to repository."""

    async def test_patch_name_only(self) -> None:
        """Editing only name leaves other fields unchanged (EDIT-01)."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Old Name", flagged=True)]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", name="New Name"))

        assert result.success is True
        assert result.name == "New Name"
        # Verify other fields unchanged
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.flagged is True  # unchanged

    async def test_patch_note_only(self) -> None:
        """Editing only note leaves other fields unchanged."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", note="New note"))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.note == "New note"

    async def test_patch_flagged_only(self) -> None:
        """Editing only flagged leaves other fields unchanged."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task", flagged=False)]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", flagged=True))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.flagged is True

    async def test_clear_due_date(self) -> None:
        """Setting due_date=None clears it (EDIT-01)."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", dueDate="2026-04-01T10:00:00+00:00")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", due_date=None))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.due_date is None

    async def test_set_due_date(self) -> None:
        """Setting due_date to a value updates it (EDIT-02)."""
        from datetime import datetime

        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", due_date=datetime(2026, 5, 1, 10, 0, tzinfo=UTC))
        )
        assert result.success is True

    async def test_set_estimated_minutes(self) -> None:
        """Setting estimated_minutes updates it (EDIT-02)."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", estimated_minutes=30.0))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.estimated_minutes == 30.0

    async def test_tag_replace(self) -> None:
        """actions.tags.replace=["tag1"] replaces all tags (EDIT-03)."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-old", "name": "Old"}])
            ],
            tags=[make_tag_dict(id="tag-new", name="NewTag")],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(replace=["NewTag"])),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 1
        assert task.tags[0].id == "tag-new"

    async def test_tag_add(self) -> None:
        """actions.tags.add=["tag2"] adds without removing (EDIT-04)."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
            tags=[
                make_tag_dict(id="tag-a", name="A"),
                make_tag_dict(id="tag-b", name="B"),
            ],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["B"])),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 2
        tag_ids = {t.id for t in task.tags}
        assert "tag-a" in tag_ids
        assert "tag-b" in tag_ids

    async def test_tag_remove(self) -> None:
        """actions.tags.remove=["tag1"] removes specific tag (EDIT-05)."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
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
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(remove=["A"])),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 1
        assert task.tags[0].id == "tag-b"

    async def test_incompatible_tag_edit_modes_replace_with_add(self) -> None:
        """TagAction(replace=..., add=...) raises ValueError (EDIT-06)."""
        from pydantic import ValidationError

        from omnifocus_operator.contracts.common import TagAction

        with pytest.raises(ValidationError, match="Cannot use 'replace' with 'add' or 'remove'"):
            TagAction(replace=["a"], add=["b"])

    async def test_incompatible_tag_edit_modes_replace_with_remove(self) -> None:
        """TagAction(replace=..., remove=...) raises ValueError."""
        from pydantic import ValidationError

        from omnifocus_operator.contracts.common import TagAction

        with pytest.raises(ValidationError, match="Cannot use 'replace' with 'add' or 'remove'"):
            TagAction(replace=["a"], remove=["b"])

    async def test_incompatible_tag_edit_modes_empty(self) -> None:
        """TagAction() with no fields raises ValueError."""
        from pydantic import ValidationError

        from omnifocus_operator.contracts.common import TagAction

        with pytest.raises(ValidationError, match="tags must specify at least one of"):
            TagAction()

    async def test_add_and_remove_tags_together(self) -> None:
        """actions.tags with add + remove together is allowed (EDIT-06)."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
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
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["B"], remove=["A"])),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 1
        assert task.tags[0].id == "tag-b"

    async def test_move_to_project_ending(self) -> None:
        """Move task to project via ending (EDIT-07)."""
        from omnifocus_operator.contracts.common import MoveAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", inInbox=True)],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(ending="proj-001")),
            )
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
        from omnifocus_operator.contracts.common import MoveAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(id="task-001", name="Task"),
                make_task_dict(id="task-parent", name="Parent Task"),
            ],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(beginning="task-parent")),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.parent is not None
        assert task.parent.type == "task"
        assert task.parent.id == "task-parent"

    async def test_move_to_inbox(self) -> None:
        """Move task to inbox via ending=null (EDIT-08)."""
        from omnifocus_operator.contracts.common import MoveAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(
                    id="task-001",
                    name="Task",
                    parent={"type": "project", "id": "proj-001", "name": "Project"},
                    inInbox=False,
                )
            ],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(ending=None)),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.parent is None
        assert task.in_inbox is True

    async def test_cycle_detection(self) -> None:
        """Moving task under its own child raises ValueError."""
        from omnifocus_operator.contracts.common import MoveAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        # task-parent -> task-child (child's parent is task-parent)
        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(id="task-parent", name="Parent"),
                make_task_dict(
                    id="task-child",
                    name="Child",
                    parent={"type": "task", "id": "task-parent", "name": "Parent"},
                ),
            ],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="circular reference"):
            await service.edit_task(
                EditTaskCommand(
                    id="task-parent",
                    actions=EditTaskActions(move=MoveAction(beginning="task-child")),
                )
            )

    async def test_task_not_found(self) -> None:
        """Non-existent task raises ValueError."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Task not found"):
            await service.edit_task(EditTaskCommand(id="nonexistent"))

    async def test_empty_name(self) -> None:
        """Empty name raises ValueError."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Task name cannot be empty"):
            await service.edit_task(EditTaskCommand(id="task-001", name=""))

    async def test_whitespace_name(self) -> None:
        """Whitespace-only name raises ValueError."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Task name cannot be empty"):
            await service.edit_task(EditTaskCommand(id="task-001", name="   "))

    async def test_warning_remove_tag_not_on_task(self) -> None:
        """Removing a tag the task doesn't have produces a warning."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", tags=[])],
            tags=[make_tag_dict(id="tag-x", name="X")],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(remove=["X"])),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("is not on this task" in w for w in result.warnings)
        assert any("(tag-x)" in w for w in result.warnings)

    async def test_no_warnings_when_none(self) -> None:
        """No warnings when edit is clean."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Updated"))
        assert result.warnings is None

    async def test_note_null_clears_note(self) -> None:
        """note=None maps to empty string (null-means-clear)."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", note="Some note")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", note=None))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.note == ""

    async def test_tags_null_clears_all_tags(self) -> None:
        """actions.tags.replace=None clears all tags (null-means-clear)."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
            tags=[make_tag_dict(id="tag-a", name="A")],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(replace=None)),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.tags == []

    async def test_warning_edit_completed_task(self) -> None:
        """Editing a completed task produces a warm warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Done Task", availability="completed")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Renamed"))
        assert result.warnings is not None
        assert any("completed" in w and "confirm with the user" in w for w in result.warnings)

    async def test_warning_edit_dropped_task(self) -> None:
        """Editing a dropped task produces a warm warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Dropped Task", availability="dropped")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Renamed"))
        assert result.warnings is not None
        assert any("dropped" in w and "confirm with the user" in w for w in result.warnings)

    async def test_noop_priority_completed(self) -> None:
        """No-op edit on completed task returns only no-op warning, not status warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Done Task", availability="completed")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        # Set name to same value -- no-op should suppress status warning
        result = await service.edit_task(EditTaskCommand(id="task-001", name="Done Task"))
        assert result.warnings is not None
        assert any("No changes detected" in w for w in result.warnings)
        assert not any("completed" in w for w in result.warnings)
        assert len(result.warnings) == 1

    async def test_noop_priority_dropped(self) -> None:
        """No-op edit on dropped task returns only no-op warning, not status warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Dropped Task", availability="dropped")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Dropped Task"))
        assert result.warnings is not None
        assert any("No changes detected" in w for w in result.warnings)
        assert not any("dropped" in w for w in result.warnings)
        assert len(result.warnings) == 1

    async def test_warning_addtags_duplicate(self) -> None:
        """Adding a tag already on the task produces a warning."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
            tags=[make_tag_dict(id="tag-a", name="A")],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["A"])),
            )
        )
        assert result.warnings is not None
        assert any("already on this task" in w for w in result.warnings)
        assert any("(tag-a)" in w for w in result.warnings)
        # Tag is still present (operation still succeeds)
        task = await repo.get_task("task-001")
        assert task is not None
        assert any(t.id == "tag-a" for t in task.tags)

    async def test_warning_addtags_duplicate_in_add_remove(self) -> None:
        """Adding a tag already present in add_remove mode produces a warning."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
            tags=[
                make_tag_dict(id="tag-a", name="A"),
                make_tag_dict(id="tag-b", name="B"),
            ],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["A"], remove=["A"])),
            )
        )
        assert result.warnings is not None
        assert any("already on this task" in w for w in result.warnings)
        assert any("(tag-a)" in w for w in result.warnings)
        # Should NOT warn "is not on this task" for A since A IS on the task
        assert not any("is not on this task" in w for w in result.warnings)

    async def test_add_tag_warning_resolves_name_from_id(self) -> None:
        """add tags with raw ID for tag already on task shows resolved name, not ID."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-x", "name": "X"}])],
            tags=[make_tag_dict(id="tag-x", name="X")],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        # Pass raw ID instead of name
        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["tag-x"])),
            )
        )
        assert result.warnings is not None
        # Warning should show resolved name "X", not the raw ID "tag-x"
        assert any("Tag 'X'" in w and "(tag-x)" in w for w in result.warnings)
        assert not any("Tag 'tag-x'" in w for w in result.warnings)

    async def test_remove_tag_warning_resolves_name_from_id(self) -> None:
        """remove tags with raw ID for tag NOT on task shows resolved name, not ID."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", tags=[])],
            tags=[make_tag_dict(id="tag-x", name="X")],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        # Pass raw ID instead of name
        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(remove=["tag-x"])),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        # Warning should show resolved name "X", not the raw ID "tag-x"
        assert any("Tag 'X'" in w and "(tag-x)" in w for w in result.warnings)
        assert not any("Tag 'tag-x'" in w for w in result.warnings)

    async def test_add_tag_warning_with_name_still_works(self) -> None:
        """add tags with name string still shows name correctly (regression guard)."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "Alpha"}])
            ],
            tags=[make_tag_dict(id="tag-a", name="Alpha")],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["Alpha"])),
            )
        )
        assert result.warnings is not None
        assert any("Tag 'Alpha'" in w and "(tag-a)" in w for w in result.warnings)

    async def test_warning_empty_edit(self) -> None:
        """Empty edit (only id, no fields) returns warning without calling bridge."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict())
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001"))
        assert result.success is True
        assert result.warnings is not None
        assert any("No changes specified" in w for w in result.warnings)

    async def test_noop_detection_same_name(self) -> None:
        """Editing name to same value triggers no-op detection."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Foo")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Foo"))
        assert result.success is True
        assert result.warnings is not None
        assert any("No changes detected" in w for w in result.warnings)

    async def test_noop_detection_different_name(self) -> None:
        """Editing name to different value does not trigger no-op warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Foo")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Bar"))
        assert result.warnings is None

    async def test_set_estimate_and_flag_together(self) -> None:
        """Edit task with both estimated_minutes and flagged (UAT #3)."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", estimated_minutes=45.0, flagged=True)
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.estimated_minutes == 45.0
        assert task.flagged is True

    async def test_set_defer_and_planned_dates(self) -> None:
        """Edit task setting defer_date and planned_date (UAT #4)."""
        from datetime import datetime

        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                defer_date=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
                planned_date=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.defer_date is not None
        assert task.defer_date.isoformat() == "2026-03-10T08:00:00+00:00"
        assert task.planned_date is not None
        assert task.planned_date.isoformat() == "2026-03-12T09:00:00+00:00"

    async def test_multi_field_edit(self) -> None:
        """Edit task changing name, note, flagged, and estimated_minutes (UAT #5)."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Old")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                name="New Name",
                note="New note",
                flagged=True,
                estimated_minutes=60.0,
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.name == "New Name"
        assert task.note == "New note"
        assert task.flagged is True
        assert task.estimated_minutes == 60.0

    async def test_unflag(self) -> None:
        """Start with flagged=True, edit to flagged=False (UAT #6)."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task", flagged=True)]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", flagged=False))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.flagged is False

    async def test_clear_note_with_empty_string(self) -> None:
        """Edit task with note='' clears note (UAT #9)."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", note="Some note")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", note=""))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.note == ""

    async def test_clear_estimated_minutes(self) -> None:
        """Set estimated_minutes=None clears the estimate (UAT #10)."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", estimatedMinutes=30.0)]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", estimated_minutes=None))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.estimated_minutes is None

    async def test_patch_preserves_untouched_fields(self) -> None:
        """Editing only name preserves note, flagged, estimatedMinutes (UAT #11)."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(
                    id="task-001",
                    name="Original",
                    note="Keep me",
                    flagged=True,
                    estimatedMinutes=45.0,
                )
            ]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Updated"))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.name == "Updated"
        assert task.note == "Keep me"
        assert task.flagged is True
        assert task.estimated_minutes == 45.0

    async def test_move_after_sibling(self) -> None:
        """Move task after a sibling task (UAT #28)."""
        from omnifocus_operator.contracts.common import MoveAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(id="task-001", name="Task A"),
                make_task_dict(id="task-002", name="Task B"),
            ],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(after="task-002")),
            )
        )
        assert result.success is True

    async def test_move_before_sibling(self) -> None:
        """Move task before a sibling task (UAT #29)."""
        from omnifocus_operator.contracts.common import MoveAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(id="task-001", name="Task A"),
                make_task_dict(id="task-002", name="Task B"),
            ],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(before="task-002")),
            )
        )
        assert result.success is True

    async def test_cycle_self_reference(self) -> None:
        """Moving task under itself raises circular reference (UAT #38)."""
        from omnifocus_operator.contracts.common import MoveAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="circular reference"):
            await service.edit_task(
                EditTaskCommand(
                    id="task-001",
                    actions=EditTaskActions(move=MoveAction(beginning="task-001")),
                )
            )

    async def test_moveto_anchor_not_found(self) -> None:
        """MoveToSpec with nonexistent anchor raises ValueError (UAT #46)."""
        from omnifocus_operator.contracts.common import MoveAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        with pytest.raises(ValueError, match="Anchor task not found"):
            await service.edit_task(
                EditTaskCommand(
                    id="task-001",
                    actions=EditTaskActions(move=MoveAction(after="nonexistent-id")),
                )
            )

    async def test_move_and_edit_combined(self) -> None:
        """Edit task with both move and field changes (UAT #39)."""
        from omnifocus_operator.contracts.common import MoveAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Old Name", inInbox=True)],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                name="Renamed",
                actions=EditTaskActions(move=MoveAction(ending="proj-001")),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.name == "Renamed"
        assert task.parent is not None
        assert task.parent.id == "proj-001"

    async def test_noop_detection_same_date_different_timezone(self) -> None:
        """Same absolute time in different timezone triggers no-op (UAT #47)."""
        from datetime import datetime

        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(
                    id="task-001",
                    name="Task",
                    dueDate="2026-03-10T07:00:00+00:00",
                )
            ]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        # Same absolute time but expressed as +01:00
        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                due_date=datetime.fromisoformat("2026-03-10T08:00:00+01:00"),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("No changes detected" in w for w in result.warnings)

    async def test_same_container_move_warning(self) -> None:
        """Moving task to same container (ending) produces location warning (UAT #70)."""
        from omnifocus_operator.contracts.common import MoveAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(
                    id="task-001",
                    name="Task",
                    parent={"type": "project", "id": "proj-001", "name": "Test Project"},
                )
            ],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(ending="proj-001")),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("already in this container" in w for w in result.warnings)

    async def test_lifecycle_complete_available_task(self) -> None:
        """lifecycle='complete' on available task succeeds without special warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        # No lifecycle-specific warnings for fresh complete
        if result.warnings:
            assert not any("already" in w.lower() for w in result.warnings)

    async def test_lifecycle_drop_available_task(self) -> None:
        """lifecycle='drop' on available task succeeds without special warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="drop"))
        )
        assert result.success is True
        if result.warnings:
            assert not any("already" in w.lower() for w in result.warnings)

    async def test_lifecycle_complete_already_completed_noop(self) -> None:
        """Completing an already-completed task is a no-op with warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", availability="completed")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("already complete" in w.lower() for w in result.warnings)

    async def test_lifecycle_drop_already_dropped_noop(self) -> None:
        """Dropping an already-dropped task is a no-op with warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", availability="dropped")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="drop"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("already dropped" in w.lower() for w in result.warnings)

    async def test_lifecycle_complete_dropped_task_cross_state(self) -> None:
        """Completing a dropped task succeeds with cross-state warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", availability="dropped")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("dropped" in w and "complete" in w.lower() for w in result.warnings)

    async def test_lifecycle_drop_completed_task_cross_state(self) -> None:
        """Dropping a completed task succeeds with cross-state warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", availability="completed")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="drop"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("completed" in w and "drop" in w.lower() for w in result.warnings)

    async def test_lifecycle_complete_repeating_task_warning(self) -> None:
        """Completing a repeating task warns about occurrence completion."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(
                    id="task-001",
                    name="Task",
                    repetitionRule={
                        "ruleString": "FREQ=WEEKLY",
                        "scheduleType": "regularly",
                        "anchorDateKey": "due_date",
                        "catchUpAutomatically": False,
                    },
                )
            ]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("repeating" in w.lower() and "occurrence" in w.lower() for w in result.warnings)

    async def test_lifecycle_drop_repeating_task_warning(self) -> None:
        """Dropping a repeating task warns about occurrence skipped."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(
                    id="task-001",
                    name="Task",
                    repetitionRule={
                        "ruleString": "FREQ=WEEKLY",
                        "scheduleType": "regularly",
                        "anchorDateKey": "due_date",
                        "catchUpAutomatically": False,
                    },
                )
            ]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="drop"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("repeating" in w.lower() and "skipped" in w.lower() for w in result.warnings)
        assert any("OmniFocus UI" in w for w in result.warnings)

    async def test_lifecycle_cross_state_repeating_stacked_warnings(self) -> None:
        """Cross-state + repeating: both warnings stack."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(
                    id="task-001",
                    name="Task",
                    availability="dropped",
                    repetitionRule={
                        "ruleString": "FREQ=WEEKLY",
                        "scheduleType": "regularly",
                        "anchorDateKey": "due_date",
                        "catchUpAutomatically": False,
                    },
                )
            ]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        assert result.warnings is not None
        # Both cross-state and repeating warnings should be present
        all_warnings = " ".join(result.warnings).lower()
        assert "dropped" in all_warnings  # cross-state
        assert "repeating" in all_warnings  # repeating

    async def test_lifecycle_with_field_edits(self) -> None:
        """lifecycle + field edits in same call: both applied."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task", flagged=False)]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                flagged=True,
                actions=EditTaskActions(lifecycle="complete"),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.flagged is True

    async def test_lifecycle_only_not_empty_edit(self) -> None:
        """lifecycle-only edit is NOT treated as empty edit."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        # Should NOT have "No changes specified" warning
        if result.warnings:
            assert not any("no changes specified" in w.lower() for w in result.warnings)

    async def test_lifecycle_noop_suppresses_status_warning(self) -> None:
        """No-op lifecycle should NOT produce the generic status warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", availability="completed")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        assert result.warnings is not None
        # Should have no-op warning, but NOT the generic status warning or empty edit warning
        assert any("already complete" in w.lower() for w in result.warnings)
        assert not any(
            "confirm with the user that they intended to edit" in w for w in result.warnings
        )
        assert not any("No changes specified" in w for w in result.warnings)

    async def test_noop_lifecycle_no_spurious_empty_edit_warning(self) -> None:
        """No-op lifecycle (complete already-completed) should NOT add 'No changes specified'."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", availability="completed")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("already complete" in w.lower() for w in result.warnings)
        assert not any("No changes specified" in w for w in result.warnings)
        assert len(result.warnings) == 1

    async def test_noop_same_container_move_no_spurious_noop_warning(self) -> None:
        """Same-container move should NOT add 'No changes detected'."""
        from omnifocus_operator.contracts.common import MoveAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(
                    id="task-001",
                    name="Task",
                    parent={"type": "project", "id": "proj-001", "name": "Test Project"},
                )
            ],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(ending="proj-001")),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("already" in w.lower() for w in result.warnings)
        assert not any("No changes detected" in w for w in result.warnings)
        assert len(result.warnings) == 1

    async def test_noop_tags_no_spurious_empty_edit_warning(self) -> None:
        """Replace tags with identical set should NOT add 'No changes specified'."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
            tags=[make_tag_dict(id="tag-a", name="A")],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(replace=["A"])),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("already match" in w.lower() for w in result.warnings)
        assert not any("No changes specified" in w for w in result.warnings)
        assert len(result.warnings) == 1

    async def test_lifecycle_action_suppresses_status_warning(self) -> None:
        """Cross-state lifecycle should NOT produce the generic status warning."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", availability="completed")]
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="drop"))
        )
        assert result.success is True
        # Should have cross-state warning, but NOT the generic status warning
        if result.warnings:
            assert not any(
                "confirm with the user that they intended to edit" in w for w in result.warnings
            )

    async def test_lifecycle_noop_detection_skips_lifecycle_key(self) -> None:
        """No-op detection (step 7) should skip the lifecycle key in field comparisons."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        # lifecycle="complete" on an available task should NOT trigger
        # "No changes detected" (the lifecycle IS a change)
        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        if result.warnings:
            assert not any("no changes detected" in w.lower() for w in result.warnings)

    async def test_empty_actions_block(self) -> None:
        """EditTaskActions() with all UNSET fields behaves like empty edit."""
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="task-001", name="Task")]))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(EditTaskCommand(id="task-001", actions=EditTaskActions()))
        assert result.success is True
        assert result.warnings is not None
        assert any("No changes" in w for w in result.warnings)

    async def test_tag_replace_noop_same_tags(self) -> None:
        """Replace with same tags produces warning, no bridge tag keys."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
            tags=[make_tag_dict(id="tag-a", name="A")],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(replace=["A"])),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("Tags already match" in w for w in result.warnings)
        # Tags unchanged
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 1
        assert task.tags[0].id == "tag-a"

    async def test_tag_only_noop_produces_warning(self) -> None:
        """Tag action that produces empty diff triggers no-op warning."""
        from omnifocus_operator.contracts.common import TagAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        from .conftest import make_tag_dict

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
            tags=[make_tag_dict(id="tag-a", name="A")],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        # Add a tag that's already there -- diff is empty
        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["A"])),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        # Should have per-tag warning only (no generic empty-edit warning)
        assert any("already on this task" in w for w in result.warnings)
        assert not any("No changes" in w for w in result.warnings)

    async def test_different_container_move_no_warning(self) -> None:
        """Moving task to different container has no location warning."""
        from omnifocus_operator.contracts.common import MoveAction
        from omnifocus_operator.contracts.use_cases.edit_task import (
            EditTaskActions,
            EditTaskCommand,
        )

        bridge = InMemoryBridge(data=make_snapshot_dict(
            tasks=[
                make_task_dict(
                    id="task-001",
                    name="Task",
                    parent={"type": "project", "id": "proj-001", "name": "Test Project"},
                )
            ],
            projects=[
                make_project_dict(id="proj-001", name="Test Project"),
                make_project_dict(id="proj-002", name="Other Project"),
            ],
        ))
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(ending="proj-002")),
            )
        )
        assert result.success is True
        # No "already in this container" warning
        if result.warnings:
            assert not any("already in this container" in w for w in result.warnings)


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
