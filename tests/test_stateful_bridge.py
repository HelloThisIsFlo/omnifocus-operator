"""Tests for the stateful InMemoryBridge (Phase 26 -- add_task/edit_task handlers)."""

from __future__ import annotations

import pytest

from omnifocus_operator.bridge import BridgeError
from omnifocus_operator.repository.bridge_only.adapter import adapt_snapshot
from omnifocus_operator.models.snapshot import AllEntities
from tests.conftest import make_snapshot_dict, make_task_dict
from tests.doubles import BridgeCall, InMemoryBridge

# ---------------------------------------------------------------------------
# State decomposition
# ---------------------------------------------------------------------------


class TestStatefulBridgeConstruction:
    """InMemoryBridge decomposes seed data into mutable entity lists."""

    def test_stores_tasks_as_mutable_list(self) -> None:
        """Constructor parses 'tasks' from seed data into _tasks list."""
        data = make_snapshot_dict()
        bridge = InMemoryBridge(data=data)

        assert isinstance(bridge._tasks, list)
        assert len(bridge._tasks) == 1
        assert bridge._tasks[0]["id"] == "task-001"

    def test_stores_projects_as_mutable_list(self) -> None:
        """Constructor parses 'projects' from seed data into _projects list."""
        data = make_snapshot_dict()
        bridge = InMemoryBridge(data=data)

        assert isinstance(bridge._projects, list)
        assert len(bridge._projects) == 1
        assert bridge._projects[0]["id"] == "proj-001"

    def test_stores_tags_as_mutable_list(self) -> None:
        """Constructor parses 'tags' from seed data into _tags list."""
        data = make_snapshot_dict()
        bridge = InMemoryBridge(data=data)

        assert isinstance(bridge._tags, list)
        assert len(bridge._tags) == 1
        assert bridge._tags[0]["id"] == "tag-001"

    def test_stores_folders_as_mutable_list(self) -> None:
        """Constructor parses 'folders' from seed data into _folders list."""
        data = make_snapshot_dict()
        bridge = InMemoryBridge(data=data)

        assert isinstance(bridge._folders, list)
        assert len(bridge._folders) == 1

    def test_stores_perspectives_as_mutable_list(self) -> None:
        """Constructor parses 'perspectives' from seed data into _perspectives list."""
        data = make_snapshot_dict()
        bridge = InMemoryBridge(data=data)

        assert isinstance(bridge._perspectives, list)
        assert len(bridge._perspectives) == 1

    def test_empty_data_gives_empty_lists(self) -> None:
        """Constructor with empty dict gives empty entity lists."""
        bridge = InMemoryBridge(data={})

        assert bridge._tasks == []
        assert bridge._projects == []
        assert bridge._tags == []
        assert bridge._folders == []
        assert bridge._perspectives == []

    def test_none_data_gives_empty_lists(self) -> None:
        """Constructor with data=None gives empty entity lists."""
        bridge = InMemoryBridge()

        assert bridge._tasks == []
        assert bridge._projects == []
        assert bridge._tags == []
        assert bridge._folders == []
        assert bridge._perspectives == []


# ---------------------------------------------------------------------------
# get_all dispatch
# ---------------------------------------------------------------------------


class TestGetAll:
    """send_command("get_all") returns deep-copied snapshot from internal state."""

    async def test_get_all_returns_snapshot_dict(self) -> None:
        """get_all returns dict with all five entity keys."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        result = await bridge.send_command("get_all")

        assert "tasks" in result
        assert "projects" in result
        assert "tags" in result
        assert "folders" in result
        assert "perspectives" in result

    async def test_get_all_parseable_by_all_entities(self) -> None:
        """get_all result can be parsed by AllEntities after adapt_snapshot."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        result = await bridge.send_command("get_all")
        adapt_snapshot(result)  # Convert raw -> model format

        snapshot = AllEntities.model_validate(result)
        assert len(snapshot.tasks) == 1
        assert len(snapshot.projects) == 1

    async def test_get_all_returns_deep_copy(self) -> None:
        """get_all returns a deep copy -- mutations don't affect internal state."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        result = await bridge.send_command("get_all")
        result["tasks"].clear()

        # Internal state unaffected
        result2 = await bridge.send_command("get_all")
        assert len(result2["tasks"]) == 1

    async def test_get_all_reflects_mutations(self) -> None:
        """After add_task, get_all includes the new task."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command("add_task", {"name": "New Task"})
        result = await bridge.send_command("get_all")

        assert len(result["tasks"]) == 2


# ---------------------------------------------------------------------------
# add_task
# ---------------------------------------------------------------------------


class TestAddTask:
    """send_command("add_task", params) creates tasks in internal state."""

    async def test_add_task_returns_id_and_name(self) -> None:
        """add_task returns dict with id and name."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        result = await bridge.send_command("add_task", {"name": "New Task"})

        assert "id" in result
        assert result["name"] == "New Task"

    async def test_add_task_generates_mem_id(self) -> None:
        """add_task generates IDs starting with 'mem-'."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        result = await bridge.send_command("add_task", {"name": "Test"})

        assert result["id"].startswith("mem-")

    async def test_add_task_unique_ids(self) -> None:
        """add_task generates unique IDs for each call."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        r1 = await bridge.send_command("add_task", {"name": "Task 1"})
        r2 = await bridge.send_command("add_task", {"name": "Task 2"})

        assert r1["id"] != r2["id"]

    async def test_add_task_appends_to_internal_tasks(self) -> None:
        """add_task appends a complete task dict to _tasks."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command("add_task", {"name": "New"})

        assert len(bridge._tasks) == 2
        new_task = bridge._tasks[-1]
        assert new_task["name"] == "New"

    async def test_add_task_no_parent_sets_inbox_true(self) -> None:
        """add_task with no parent sets inInbox=True."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command("add_task", {"name": "Inbox Task"})

        new_task = bridge._tasks[-1]
        assert new_task["inInbox"] is True

    async def test_add_task_with_parent_sets_inbox_false(self) -> None:
        """add_task with parent sets inInbox=False."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command("add_task", {"name": "Child", "parent": "proj-001"})

        new_task = bridge._tasks[-1]
        assert new_task["inInbox"] is False

    async def test_add_task_generates_all_26_fields(self) -> None:
        """add_task generates a complete task dict with all 26 fields."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command("add_task", {"name": "Complete"})

        new_task = bridge._tasks[-1]
        # All fields from make_task_dict should be present
        template = make_task_dict()
        for key in template:
            assert key in new_task, f"Missing field: {key}"

    async def test_add_task_sets_flagged(self) -> None:
        """add_task respects flagged parameter."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command("add_task", {"name": "Flagged", "flagged": True})

        new_task = bridge._tasks[-1]
        assert new_task["flagged"] is True
        assert new_task["effectiveFlagged"] is True

    async def test_add_task_sets_dates(self) -> None:
        """add_task respects date parameters."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command(
            "add_task",
            {
                "name": "Dated",
                "dueDate": "2026-03-15T17:00:00Z",
                "deferDate": "2026-03-10T09:00:00Z",
            },
        )

        new_task = bridge._tasks[-1]
        assert new_task["dueDate"] == "2026-03-15T17:00:00Z"
        assert new_task["deferDate"] == "2026-03-10T09:00:00Z"

    async def test_add_task_with_parent_resolves_project(self) -> None:
        """add_task with parent=project ID stores raw string parent and project."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command("add_task", {"name": "Child", "parent": "proj-001"})

        new_task = bridge._tasks[-1]
        assert new_task["parent"] == "proj-001"
        assert new_task["project"] == "proj-001"

    async def test_add_task_with_parent_resolves_task(self) -> None:
        """add_task with parent=task ID (not a project) stores raw string parent."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command("add_task", {"name": "Sub", "parent": "task-001"})

        new_task = bridge._tasks[-1]
        assert new_task["parent"] == "task-001"
        assert new_task["project"] is None

    async def test_add_task_with_parent_unknown_falls_back(self) -> None:
        """add_task with unknown parent ID stores raw string parent."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command("add_task", {"name": "Orphan", "parent": "unknown-id"})

        new_task = bridge._tasks[-1]
        assert new_task["parent"] == "unknown-id"
        assert new_task["project"] is None

    async def test_add_task_with_tag_ids_resolves_names(self) -> None:
        """add_task with tagIds resolves tag names from internal state."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command("add_task", {"name": "Tagged", "tagIds": ["tag-001"]})

        new_task = bridge._tasks[-1]
        assert new_task["tags"] == [{"id": "tag-001", "name": "Test Tag"}]

    async def test_add_task_with_tag_ids_unknown_falls_back(self) -> None:
        """add_task with unknown tagIds uses ID as name fallback."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command("add_task", {"name": "Tagged", "tagIds": ["no-such-tag"]})

        new_task = bridge._tasks[-1]
        assert new_task["tags"] == [{"id": "no-such-tag", "name": "no-such-tag"}]


# ---------------------------------------------------------------------------
# edit_task
# ---------------------------------------------------------------------------


class TestEditTask:
    """send_command("edit_task", params) mutates tasks in internal state."""

    async def test_edit_task_updates_name(self) -> None:
        """edit_task with name updates the task's name."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        result = await bridge.send_command("edit_task", {"id": "task-001", "name": "Updated"})

        assert result["id"] == "task-001"
        assert result["name"] == "Updated"
        assert bridge._tasks[0]["name"] == "Updated"

    async def test_edit_task_returns_id_and_name(self) -> None:
        """edit_task returns dict with id and current name."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        result = await bridge.send_command("edit_task", {"id": "task-001", "flagged": True})

        assert result["id"] == "task-001"
        assert result["name"] == "Test Task"  # unchanged name

    async def test_edit_task_unknown_id_raises(self) -> None:
        """edit_task with unknown task ID raises ValueError."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        with pytest.raises(ValueError, match="Task not found: nonexistent"):
            await bridge.send_command("edit_task", {"id": "nonexistent", "name": "X"})

    async def test_edit_task_add_tags(self) -> None:
        """edit_task with addTagIds appends tags to the task."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command(
            "edit_task",
            {
                "id": "task-001",
                "addTagIds": ["tag-a", "tag-b"],
            },
        )

        task_tags = bridge._tasks[0]["tags"]
        tag_ids = [t["id"] for t in task_tags]
        assert "tag-a" in tag_ids
        assert "tag-b" in tag_ids

    async def test_edit_task_remove_tags(self) -> None:
        """edit_task with removeTagIds removes tags from the task."""
        data = make_snapshot_dict(
            tasks=[
                make_task_dict(
                    tags=[
                        {"id": "tag-x", "name": "X"},
                        {"id": "tag-y", "name": "Y"},
                    ]
                )
            ]
        )
        bridge = InMemoryBridge(data=data)

        await bridge.send_command(
            "edit_task",
            {
                "id": "task-001",
                "removeTagIds": ["tag-x"],
            },
        )

        task_tags = bridge._tasks[0]["tags"]
        tag_ids = [t["id"] for t in task_tags]
        assert "tag-x" not in tag_ids
        assert "tag-y" in tag_ids

    async def test_edit_task_remove_then_add_tags(self) -> None:
        """edit_task processes removeTagIds before addTagIds."""
        data = make_snapshot_dict(
            tasks=[
                make_task_dict(
                    tags=[
                        {"id": "tag-a", "name": "A"},
                    ]
                )
            ]
        )
        bridge = InMemoryBridge(data=data)

        await bridge.send_command(
            "edit_task",
            {
                "id": "task-001",
                "removeTagIds": ["tag-a"],
                "addTagIds": ["tag-a"],  # re-add after remove
            },
        )

        # tag-a should be present (removed then re-added)
        task_tags = bridge._tasks[0]["tags"]
        tag_ids = [t["id"] for t in task_tags]
        assert "tag-a" in tag_ids

    async def test_edit_task_lifecycle_complete(self) -> None:
        """edit_task with lifecycle='complete' sets status to 'Completed'."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command(
            "edit_task",
            {
                "id": "task-001",
                "lifecycle": "complete",
            },
        )

        assert bridge._tasks[0]["status"] == "Completed"

    async def test_edit_task_lifecycle_drop(self) -> None:
        """edit_task with lifecycle='drop' sets status to 'Dropped'."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command(
            "edit_task",
            {
                "id": "task-001",
                "lifecycle": "drop",
            },
        )

        assert bridge._tasks[0]["status"] == "Dropped"

    async def test_edit_task_add_tags_resolves_name_from_internal_tags(self) -> None:
        """edit_task addTagIds resolves tag names from internal _tags list."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command(
            "edit_task",
            {"id": "task-001", "addTagIds": ["tag-001"]},
        )

        task_tags = bridge._tasks[0]["tags"]
        assert {"id": "tag-001", "name": "Test Tag"} in task_tags

    async def test_edit_task_add_tags_unknown_falls_back(self) -> None:
        """edit_task addTagIds with unknown tag uses ID as name fallback."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command(
            "edit_task",
            {"id": "task-001", "addTagIds": ["unknown-tag"]},
        )

        task_tags = bridge._tasks[0]["tags"]
        assert {"id": "unknown-tag", "name": "unknown-tag"} in task_tags

    async def test_edit_task_move_to_inbox(self) -> None:
        """edit_task with moveTo containerId=null moves task to inbox."""
        data = make_snapshot_dict(tasks=[make_task_dict(inInbox=False)])
        bridge = InMemoryBridge(data=data)

        await bridge.send_command(
            "edit_task",
            {
                "id": "task-001",
                "moveTo": {"containerId": None},
            },
        )

        assert bridge._tasks[0]["inInbox"] is True
        assert bridge._tasks[0]["parent"] is None
        assert bridge._tasks[0]["project"] is None

    async def test_edit_task_move_to_project(self) -> None:
        """edit_task with moveTo containerId sets inInbox=False and updates parent/project."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command(
            "edit_task",
            {
                "id": "task-001",
                "moveTo": {"containerId": "proj-001"},
            },
        )

        assert bridge._tasks[0]["inInbox"] is False
        assert bridge._tasks[0]["parent"] == "proj-001"
        assert bridge._tasks[0]["project"] == "proj-001"


# ---------------------------------------------------------------------------
# Call tracking and error injection (preserved behavior)
# ---------------------------------------------------------------------------


class TestCallTrackingPreserved:
    """Call tracking still records all send_command calls."""

    async def test_add_task_recorded(self) -> None:
        """add_task call is recorded in call history."""
        bridge = InMemoryBridge(data=make_snapshot_dict())
        params = {"name": "Test"}

        await bridge.send_command("add_task", params)

        assert bridge.call_count == 1
        assert bridge.calls[0] == BridgeCall(operation="add_task", params=params)

    async def test_edit_task_recorded(self) -> None:
        """edit_task call is recorded in call history."""
        bridge = InMemoryBridge(data=make_snapshot_dict())
        params = {"id": "task-001", "name": "Updated"}

        await bridge.send_command("edit_task", params)

        assert bridge.call_count == 1
        assert bridge.calls[0] == BridgeCall(operation="edit_task", params=params)

    async def test_get_all_recorded(self) -> None:
        """get_all call is recorded in call history."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        await bridge.send_command("get_all")

        assert bridge.call_count == 1
        assert bridge.calls[0] == BridgeCall(operation="get_all", params=None)


class TestErrorInjectionPreserved:
    """set_error/clear_error still works (error raised before processing)."""

    async def test_error_raised_before_add_task(self) -> None:
        """set_error prevents add_task from executing."""
        bridge = InMemoryBridge(data=make_snapshot_dict())
        bridge.set_error(BridgeError("add_task", "fail"))

        with pytest.raises(BridgeError):
            await bridge.send_command("add_task", {"name": "Test"})

        # Task was NOT added
        assert len(bridge._tasks) == 1

    async def test_clear_error_allows_processing(self) -> None:
        """clear_error removes configured error."""
        bridge = InMemoryBridge(data=make_snapshot_dict())
        bridge.set_error(BridgeError("test", "fail"))
        bridge.clear_error()

        result = await bridge.send_command("add_task", {"name": "Test"})
        assert "id" in result


# ---------------------------------------------------------------------------
# Unknown operations
# ---------------------------------------------------------------------------


class TestUnknownOperations:
    """Unknown operations return assembled snapshot (same as get_all)."""

    async def test_unknown_operation_returns_snapshot(self) -> None:
        """send_command with unknown operation returns assembled snapshot."""
        bridge = InMemoryBridge(data=make_snapshot_dict())

        result = await bridge.send_command("some_unknown_op")

        assert "tasks" in result
        assert "projects" in result
        assert "tags" in result
        assert "folders" in result
        assert "perspectives" in result

    async def test_unknown_operation_with_empty_data_returns_empty_collections(self) -> None:
        """send_command with unknown operation on empty bridge returns empty collections."""
        bridge = InMemoryBridge(data={})

        result = await bridge.send_command("unknown_op")

        assert result == {
            "tasks": [],
            "projects": [],
            "tags": [],
            "folders": [],
            "perspectives": [],
        }
