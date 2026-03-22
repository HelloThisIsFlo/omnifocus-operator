"""Test doubles -- InMemoryBridge, StubBridge, and BridgeCall for unit tests."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from omnifocus_operator.contracts.protocols import Bridge
from tests.conftest import make_task_dict

# ---------------------------------------------------------------------------
# Reverse status maps: model-format -> raw bridge format
# ---------------------------------------------------------------------------

_REVERSE_TASK_STATUS: dict[tuple[str, str], str] = {
    ("none", "available"): "Available",
    ("none", "blocked"): "Blocked",
    ("due_soon", "available"): "DueSoon",
    ("overdue", "available"): "Overdue",
    ("none", "completed"): "Completed",
    ("none", "dropped"): "Dropped",
}

_REVERSE_PROJECT_STATUS: dict[str, str] = {
    "available": "Active",
    "blocked": "OnHold",
    "completed": "Done",
    "dropped": "Dropped",
}

_REVERSE_PROJECT_TASK_STATUS: dict[str, str] = {
    "none": "Available",
    "due_soon": "DueSoon",
    "overdue": "Overdue",
}

_REVERSE_TAG_STATUS: dict[str, str] = {
    "available": "Active",
    "blocked": "OnHold",
    "dropped": "Dropped",
}

_REVERSE_FOLDER_STATUS: dict[str, str] = {
    "available": "Active",
    "dropped": "Dropped",
}

_REVERSE_SCHEDULE_TYPE: dict[str, str] = {
    "regularly": "Regularly",
    "from_completion": "FromCompletion",
}

_REVERSE_ANCHOR_DATE_KEY: dict[str, str] = {
    "due_date": "DueDate",
    "defer_date": "DeferDate",
    "planned_date": "PlannedDate",
}


def _find_containing_project(
    task: dict[str, Any],
    task_index: dict[str, dict[str, Any]],
    project_ids: set[str],
) -> str | None:
    """Walk parent chain to find the containing project for a task.

    Returns the project ID if found, None if the task is in the inbox
    (no project ancestor). Matches OmniFocus t.containingProject behavior.
    """
    current = task
    visited: set[str] = set()
    while True:
        parent_ref = current.get("parent")
        if parent_ref is None:
            # Reached inbox (no parent) -- no containing project
            return None
        parent_id = parent_ref["id"]
        if parent_id in visited:
            # Cycle protection
            return None
        visited.add(parent_id)
        if parent_id in project_ids:
            # Found the containing project
            return parent_id
        # Parent is a task -- walk up
        parent_task = task_index.get(parent_id)
        if parent_task is None:
            # Parent task not in index (shouldn't happen, but safe)
            return None
        current = parent_task


@dataclass(frozen=True)
class BridgeCall:
    """Record of a single ``send_command`` invocation."""

    operation: str
    params: dict[str, Any] | None


class InMemoryBridge(Bridge):
    """Stateful test bridge: stores entities as mutable camelCase dict lists.

    Designed for unit tests.  Supports:
    - Stateful entity storage (tasks, projects, tags, folders, perspectives)
    - Write operations: add_task, edit_task (mutate internal state)
    - Read operation: get_all (returns deep-copied snapshot)
    - Full call history via ``calls`` / ``call_count``
    - Configurable error simulation via ``set_error`` / ``clear_error``

    For canned-response (non-stateful) testing, use StubBridge instead.
    """

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        wal_path: str | Path | None = None,
    ) -> None:
        seed = data if data is not None else {}

        # Decompose seed data into mutable entity lists
        self._tasks: list[dict[str, Any]] = list(seed.get("tasks", []))
        self._projects: list[dict[str, Any]] = list(seed.get("projects", []))
        self._tags: list[dict[str, Any]] = list(seed.get("tags", []))
        self._folders: list[dict[str, Any]] = list(seed.get("folders", []))
        self._perspectives: list[dict[str, Any]] = list(seed.get("perspectives", []))

        self._calls: list[BridgeCall] = []
        self._error: Exception | None = None
        self._wal_path: Path | None = Path(wal_path) if wal_path else None
        if self._wal_path:
            self._wal_path.touch()

    @property
    def calls(self) -> list[BridgeCall]:
        """Copy of recorded calls (prevents external mutation)."""
        return list(self._calls)

    @property
    def call_count(self) -> int:
        """Number of ``send_command`` invocations."""
        return len(self._calls)

    def set_error(self, error: Exception) -> None:
        """Configure an error to raise on the next ``send_command``."""
        self._error = error

    def clear_error(self) -> None:
        """Remove the configured error so subsequent calls succeed."""
        self._error = None

    async def send_command(
        self,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record call, optionally raise error, touch WAL, dispatch operation."""
        self._calls.append(BridgeCall(operation=operation, params=params))
        if self._error is not None:
            raise self._error
        if self._wal_path:
            self._wal_path.write_bytes(b"flushed")

        if operation == "get_all":
            return self._handle_get_all()
        if operation == "add_task":
            return self._handle_add_task(params or {})
        if operation == "edit_task":
            return self._handle_edit_task(params or {})

        # Unknown operations return the assembled snapshot
        return self._handle_get_all()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_tag_name(self, tag_id: str) -> str:
        """Look up tag name from internal _tags list; fall back to tag_id."""
        tag = next((t for t in self._tags if t["id"] == tag_id), None)
        return tag["name"] if tag is not None else tag_id

    def _resolve_parent(self, container_id: str) -> dict[str, Any]:
        """Resolve a parent ID to a {type, id, name} dict.

        Matches OmniFocus behavior: a project's root task is represented as
        type "task" with an empty name in get_all snapshots. Only actual
        task parents get type "task" with their real name.
        """
        project = next((p for p in self._projects if p["id"] == container_id), None)
        if project is not None:
            return {"type": "task", "id": container_id, "name": ""}
        parent_task = next((t for t in self._tasks if t["id"] == container_id), None)
        if parent_task is not None:
            return {"type": "task", "id": container_id, "name": parent_task["name"]}
        return {"type": "task", "id": container_id, "name": container_id}

    # ------------------------------------------------------------------
    # Operation handlers
    # ------------------------------------------------------------------

    def _handle_get_all(self) -> dict[str, Any]:
        """Return a deep copy of internal state converted to raw bridge format.

        Internal storage remains model-format (urgency, availability, parent as dict).
        The output matches what RealBridge/bridge.js returns (status, parent/project
        as string IDs), so BridgeRepository.adapt_snapshot processes it correctly.
        """
        snapshot = copy.deepcopy(
            {
                "tasks": self._tasks,
                "projects": self._projects,
                "tags": self._tags,
                "folders": self._folders,
                "perspectives": self._perspectives,
            }
        )
        self._to_raw_format(snapshot)
        return snapshot

    # ------------------------------------------------------------------
    # Raw format conversion (model -> bridge.js output shape)
    # ------------------------------------------------------------------

    def _to_raw_format(self, snapshot: dict[str, Any]) -> None:
        """Convert a model-format snapshot to raw bridge format in place.

        Each entity type has its own conversion: status fields are reversed
        from model (urgency/availability) back to bridge (status string),
        and task parent dicts are decomposed back to parent/project string IDs.

        Gracefully skips conversion if entity collections are not lists of dicts
        (lets downstream Pydantic validation report the real error).
        """
        tasks = snapshot.get("tasks", [])
        projects = snapshot.get("projects", [])
        tags = snapshot.get("tags", [])
        folders = snapshot.get("folders", [])

        # Guard: only process if entities are lists of dicts
        if not isinstance(tasks, list) or not all(isinstance(t, dict) for t in tasks):
            return
        if not isinstance(projects, list) or not all(isinstance(p, dict) for p in projects):
            return

        # Pre-compute containing project map BEFORE converting tasks.
        # This avoids the iteration-order bug: once _task_to_raw converts
        # parent dicts to strings, walking the parent chain would break.
        task_index: dict[str, dict[str, Any]] = {t["id"]: t for t in tasks}
        project_ids: set[str] = {p["id"] for p in projects}
        containing_project_map = self._build_containing_project_map(task_index, project_ids)

        for task in tasks:
            self._task_to_raw(task, containing_project_map)
        for project in projects:
            self._project_to_raw(project)
        for tag in tags:
            if isinstance(tag, dict):
                self._tag_to_raw(tag)
        for folder in folders:
            if isinstance(folder, dict):
                self._folder_to_raw(folder)

    @staticmethod
    def _build_containing_project_map(
        task_index: dict[str, dict[str, Any]],
        project_ids: set[str],
    ) -> dict[str, str | None]:
        """Pre-compute task_id -> containing_project_id for all tasks.

        Walks the parent chain (while parent dicts are still intact) to find
        the containing project. Handles all 4 cases:
        - Inbox task (parent=None): containing_project = None
        - Direct project child (parent.id is a project): containing_project = parent.id
        - Sub-task in project: walk up until a project is found
        - Sub-task in inbox: walk up, no project found -> None
        """
        result: dict[str, str | None] = {}
        for task_id, task in task_index.items():
            result[task_id] = _find_containing_project(task, task_index, project_ids)
        return result

    @staticmethod
    def _task_to_raw(
        task: dict[str, Any],
        containing_project_map: dict[str, str | None],
    ) -> None:
        """Convert a single task from model format to raw bridge format."""
        # urgency + availability -> status
        urgency = task.pop("urgency", "none")
        availability = task.pop("availability", "available")
        task["status"] = _REVERSE_TASK_STATUS.get((urgency, availability), "Available")

        # repetitionRule: snake_case -> PascalCase
        InMemoryBridge._repetition_rule_to_raw(task)

        # parent dict -> parent (string|None) + project (string|None)
        parent_ref = task.get("parent")
        if parent_ref is None:
            task["parent"] = None
            task["project"] = None
        else:
            parent_id = parent_ref["id"]
            task["parent"] = parent_id
            task["parentName"] = parent_ref.get("name", "")
            task["project"] = containing_project_map.get(task["id"])
            if task["project"] is not None:
                # Add projectName (bridge.js includes it)
                task["projectName"] = ""

    @staticmethod
    def _project_to_raw(project: dict[str, Any]) -> None:
        """Convert a single project from model format to raw bridge format."""
        availability = project.pop("availability", "available")
        urgency = project.pop("urgency", "none")
        project["status"] = _REVERSE_PROJECT_STATUS.get(availability, "Active")
        project["taskStatus"] = _REVERSE_PROJECT_TASK_STATUS.get(urgency, "Available")

        # repetitionRule: snake_case -> PascalCase
        InMemoryBridge._repetition_rule_to_raw(project)

    @staticmethod
    def _repetition_rule_to_raw(entity: dict[str, Any]) -> None:
        """Reverse repetition rule from model format to raw bridge format."""
        rule = entity.get("repetitionRule")
        if rule is None:
            return
        schedule_type = rule.get("scheduleType")
        if schedule_type is not None and schedule_type in _REVERSE_SCHEDULE_TYPE:
            rule["scheduleType"] = _REVERSE_SCHEDULE_TYPE[schedule_type]
        anchor_key = rule.get("anchorDateKey")
        if anchor_key is not None and anchor_key in _REVERSE_ANCHOR_DATE_KEY:
            rule["anchorDateKey"] = _REVERSE_ANCHOR_DATE_KEY[anchor_key]

    @staticmethod
    def _tag_to_raw(tag: dict[str, Any]) -> None:
        """Convert a single tag from model format to raw bridge format."""
        availability = tag.pop("availability", "available")
        tag["status"] = _REVERSE_TAG_STATUS.get(availability, "Active")

    @staticmethod
    def _folder_to_raw(folder: dict[str, Any]) -> None:
        """Convert a single folder from model format to raw bridge format."""
        availability = folder.pop("availability", "available")
        tag_status = _REVERSE_FOLDER_STATUS.get(availability, "Active")
        folder["status"] = tag_status

    def _handle_add_task(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a task in-memory and append to internal tasks list.

        Generates a synthetic ID and builds a complete task dict using
        make_task_dict() as a template. Returns {id, name}.
        """
        task_id = f"mem-{uuid4().hex[:8]}"
        now = datetime.now(tz=UTC).isoformat()
        parent_id = params.get("parent")
        has_parent = parent_id is not None

        # Resolve parent to {type, id, name} dict (or None for inbox)
        parent = self._resolve_parent(parent_id) if has_parent else None

        # Resolve tagIds to [{id, name}] list
        tag_ids = params.get("tagIds", [])
        tags = [{"id": tid, "name": self._resolve_tag_name(tid)} for tid in tag_ids]

        # Compute availability: "blocked" if deferred to the future
        defer_date = params.get("deferDate")
        availability = "available"
        if defer_date is not None:
            availability = "blocked"

        task = make_task_dict(
            id=task_id,
            name=params["name"],
            url=f"omnifocus:///task/{task_id}",
            added=now,
            modified=now,
            note=params.get("note", ""),
            flagged=params.get("flagged", False),
            effectiveFlagged=params.get("flagged", False),
            inInbox=not has_parent,
            parent=parent,
            dueDate=params.get("dueDate"),
            deferDate=defer_date,
            plannedDate=params.get("plannedDate"),
            estimatedMinutes=params.get("estimatedMinutes"),
            tags=tags,
            availability=availability,
        )

        self._tasks.append(task)

        # Update parent project's hasChildren flag
        if parent_id is not None:
            project = next((p for p in self._projects if p["id"] == parent_id), None)
            if project is not None:
                project["hasChildren"] = True

        return {"id": task_id, "name": params["name"]}

    def _handle_edit_task(self, params: dict[str, Any]) -> dict[str, Any]:
        """Edit a task in-memory by mutating the dict in the internal tasks list.

        Finds task by ID, applies field updates, tag operations, lifecycle,
        and move. Returns {id, name}.
        """
        task_id = params["id"]
        task = next((t for t in self._tasks if t["id"] == task_id), None)
        if task is None:
            msg = f"Task not found: {task_id}"
            raise ValueError(msg)

        # Simple field updates (both params and stored dicts use camelCase)
        for key in (
            "name",
            "note",
            "flagged",
            "dueDate",
            "deferDate",
            "plannedDate",
            "estimatedMinutes",
        ):
            if key in params:
                task[key] = params[key]

        # Sync effectiveFlagged when flagged is updated
        if "flagged" in params:
            task["effectiveFlagged"] = params["flagged"]

        # Recompute availability when deferDate changes
        if "deferDate" in params:
            if params["deferDate"] is not None:
                task["availability"] = "blocked"
            else:
                task["availability"] = "available"

        # Tag operations: remove first, then add
        remove_ids = set(params.get("removeTagIds", []))
        if remove_ids:
            task["tags"] = [t for t in task["tags"] if t["id"] not in remove_ids]

        add_ids = params.get("addTagIds", [])
        if add_ids:
            existing_ids = {t["id"] for t in task["tags"]}
            for tid in add_ids:
                if tid not in existing_ids:
                    task["tags"].append({"id": tid, "name": self._resolve_tag_name(tid)})

        # Lifecycle
        lifecycle = params.get("lifecycle")
        if lifecycle == "complete":
            task["availability"] = "completed"
            task["completionDate"] = datetime.now(tz=UTC).isoformat()
        elif lifecycle == "drop":
            task["availability"] = "dropped"
            task["dropDate"] = datetime.now(tz=UTC).isoformat()

        # Move (dict-level with parent resolution)
        if "moveTo" in params:
            container_id = params["moveTo"].get("containerId")
            if container_id is None:
                task["parent"] = None
                task["inInbox"] = True
            else:
                task["inInbox"] = False
                task["parent"] = self._resolve_parent(container_id)
                # Update parent project's hasChildren flag
                project = next((p for p in self._projects if p["id"] == container_id), None)
                if project is not None:
                    project["hasChildren"] = True

        return {"id": task_id, "name": task["name"]}


class StubBridge(Bridge):
    """Canned-response test bridge.

    Returns seed data for every operation without maintaining state.
    Use InMemoryBridge for stateful snapshot testing.
    """

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        wal_path: str | Path | None = None,
    ) -> None:
        self._data: dict[str, Any] = data if data is not None else {}
        self._calls: list[BridgeCall] = []
        self._error: Exception | None = None
        self._wal_path: Path | None = Path(wal_path) if wal_path else None
        if self._wal_path:
            self._wal_path.touch()

    @property
    def calls(self) -> list[BridgeCall]:
        """Copy of recorded calls (prevents external mutation)."""
        return list(self._calls)

    @property
    def call_count(self) -> int:
        """Number of ``send_command`` invocations."""
        return len(self._calls)

    def set_error(self, error: Exception) -> None:
        """Configure an error to raise on the next ``send_command``."""
        self._error = error

    def clear_error(self) -> None:
        """Remove the configured error so subsequent calls succeed."""
        self._error = None

    async def send_command(
        self,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record call, optionally raise error, touch WAL, return seed data."""
        self._calls.append(BridgeCall(operation=operation, params=params))
        if self._error is not None:
            raise self._error
        if self._wal_path:
            self._wal_path.write_bytes(b"flushed")
        return self._data
