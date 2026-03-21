"""Test doubles -- InMemoryBridge and BridgeCall for unit tests."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from omnifocus_operator.contracts.protocols import Bridge
from tests.conftest import make_task_dict


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
    # Operation handlers
    # ------------------------------------------------------------------

    def _handle_get_all(self) -> dict[str, Any]:
        """Return a deep copy of internal state as a snapshot dict."""
        return copy.deepcopy(
            {
                "tasks": self._tasks,
                "projects": self._projects,
                "tags": self._tags,
                "folders": self._folders,
                "perspectives": self._perspectives,
            }
        )

    def _handle_add_task(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a task in-memory and append to internal tasks list.

        Generates a synthetic ID and builds a complete task dict using
        make_task_dict() as a template. Returns {id, name}.
        """
        task_id = f"mem-{uuid4().hex[:8]}"
        now = datetime.now(tz=UTC).isoformat()
        has_parent = params.get("parent") is not None

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
            parent=None,
            dueDate=params.get("dueDate"),
            deferDate=params.get("deferDate"),
            plannedDate=params.get("plannedDate"),
            estimatedMinutes=params.get("estimatedMinutes"),
            tags=[],
        )

        self._tasks.append(task)
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

        # Tag operations: remove first, then add
        remove_ids = set(params.get("removeTagIds", []))
        if remove_ids:
            task["tags"] = [t for t in task["tags"] if t["id"] not in remove_ids]

        add_ids = params.get("addTagIds", [])
        if add_ids:
            existing_ids = {t["id"] for t in task["tags"]}
            for tid in add_ids:
                if tid not in existing_ids:
                    task["tags"].append({"id": tid, "name": tid})

        # Lifecycle
        lifecycle = params.get("lifecycle")
        if lifecycle == "complete":
            task["availability"] = "completed"
        elif lifecycle == "drop":
            task["availability"] = "dropped"

        # Move (dict-level with parent resolution)
        if "moveTo" in params:
            container_id = params["moveTo"].get("containerId")
            if container_id is None:
                task["parent"] = None
                task["inInbox"] = True
            else:
                task["inInbox"] = False
                # Resolve parent type and name from internal state
                project = next((p for p in self._projects if p["id"] == container_id), None)
                if project is not None:
                    task["parent"] = {
                        "type": "project",
                        "id": container_id,
                        "name": project["name"],
                    }
                else:
                    parent_task = next((t for t in self._tasks if t["id"] == container_id), None)
                    if parent_task is not None:
                        task["parent"] = {
                            "type": "task",
                            "id": container_id,
                            "name": parent_task["name"],
                        }
                    else:
                        task["parent"] = {"type": "task", "id": container_id, "name": container_id}

        return {"id": task_id, "name": task["name"]}
