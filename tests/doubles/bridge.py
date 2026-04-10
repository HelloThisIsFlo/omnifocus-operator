"""Test doubles -- InMemoryBridge, StubBridge, and BridgeCall for unit tests."""

from __future__ import annotations

import calendar
import copy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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


_ANCHOR_DATE_KEY_MAP: dict[str, str] = {
    "DueDate": "dueDate",
    "DeferDate": "deferDate",
    "PlannedDate": "plannedDate",
}


def _ensure_tz_aware(value: str | None) -> str | None:
    """Ensure a date string has timezone info for read-back parity.

    OmniFocus stores dates as naive local and reads them back as tz-aware.
    The InMemoryBridge simulates this: naive strings get '+00:00' appended
    (test environment has no local tz offset to apply).
    """
    if value is None:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return value + "+00:00"
    return value


def _parse_rrule_interval(rule_string: str) -> tuple[str, int]:
    """Parse an RRULE string into (frequency, interval).

    >>> _parse_rrule_interval("FREQ=DAILY;INTERVAL=3")
    ('DAILY', 3)
    >>> _parse_rrule_interval("FREQ=WEEKLY")
    ('WEEKLY', 1)
    """
    parts = dict(part.split("=", 1) for part in rule_string.split(";"))
    return parts["FREQ"], int(parts.get("INTERVAL", "1"))


def _advance_date_by_rule(date_str: str, freq: str, interval: int) -> str:
    """Advance an ISO-8601 date string by one rule period, return `.000Z` format."""
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    if freq == "MINUTELY":
        dt += timedelta(minutes=interval)
    elif freq == "HOURLY":
        dt += timedelta(hours=interval)
    elif freq == "DAILY":
        dt += timedelta(days=interval)
    elif freq == "WEEKLY":
        dt += timedelta(weeks=interval)
    elif freq == "MONTHLY":
        month = dt.month - 1 + interval
        year = dt.year + month // 12
        month = month % 12 + 1
        day = min(dt.day, calendar.monthrange(year, month)[1])
        dt = dt.replace(year=year, month=month, day=day)
    elif freq == "YEARLY":
        year = dt.year + interval
        day = min(dt.day, calendar.monthrange(year, dt.month)[1])
        dt = dt.replace(year=year, day=day)
    else:
        msg = f"Unsupported RRULE frequency: {freq}"
        raise ValueError(msg)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


class InMemoryBridge(Bridge):
    """Stateful test bridge: stores entities in raw bridge format (matching bridge.js).

    Internal storage uses raw bridge format:
    - Tasks: ``status`` (PascalCase string), ``parent``/``project`` (string IDs)
    - Projects: ``status`` + ``taskStatus`` (PascalCase strings)
    - Tags/Folders: ``status`` (PascalCase string)

    ``get_all`` returns a deep copy of internal state directly -- no conversion.
    ``BridgeOnlyRepository.adapt_snapshot()`` converts raw → model format downstream.

    Supports:
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

    def _set_has_children(self, parent_id: str, value: bool) -> None:
        """Set hasChildren on a task or project by ID."""
        for entity in (*self._tasks, *self._projects):
            if entity["id"] == parent_id:
                entity["hasChildren"] = value
                return

    def _recheck_has_children(self, parent_id: str) -> None:
        """Recompute hasChildren for a task/project based on current children."""
        has = any(t.get("parent") == parent_id for t in self._tasks)
        self._set_has_children(parent_id, has)

    def _compute_effective_field(self, task: dict[str, Any], field: str) -> Any:
        """Walk ancestor chain (parent tasks -> project), return first non-null value."""
        if task.get(field) is not None:
            return task[field]
        task_index = {t["id"]: t for t in self._tasks}
        project_index = {p["id"]: p for p in self._projects}
        current_id = task.get("parent")
        visited: set[str] = set()
        while current_id is not None and current_id not in visited:
            visited.add(current_id)
            if current_id in project_index:
                return project_index[current_id].get(field)
            parent_task = task_index.get(current_id)
            if parent_task is None:
                return None
            if parent_task.get(field) is not None:
                return parent_task[field]
            current_id = parent_task.get("parent")
        return None

    def _compute_effective_flagged(self, task: dict[str, Any]) -> bool:
        """Boolean OR: true if task or any ancestor is flagged."""
        if task.get("flagged", False):
            return True
        task_index = {t["id"]: t for t in self._tasks}
        project_index = {p["id"]: p for p in self._projects}
        current_id = task.get("parent")
        visited: set[str] = set()
        while current_id is not None and current_id not in visited:
            visited.add(current_id)
            if current_id in project_index:
                return project_index[current_id].get("flagged", False)
            parent_task = task_index.get(current_id)
            if parent_task is None:
                return False
            if parent_task.get("flagged", False):
                return True
            current_id = parent_task.get("parent")
        return False

    def _resolve_raw_parent(self, container_id: str) -> tuple[str, str | None]:
        """Resolve a container ID to raw-format (parent_id, project_id).

        Returns:
            (parent_string, project_string_or_None)
            - If container is a project: (container_id, container_id)
            - If container is a task: (container_id, containing_project_or_None)
        """
        # Check if container is a project
        if any(p["id"] == container_id for p in self._projects):
            return (container_id, container_id)
        # Container is a task -- walk up to find containing project
        containing_project = self._find_containing_project_raw(container_id)
        return (container_id, containing_project)

    def _find_containing_project_raw(self, task_id: str) -> str | None:
        """Walk parent chain from a task to find its containing project.

        Uses raw-format string parent IDs. Returns the project ID or None.
        """
        project_ids = {p["id"] for p in self._projects}
        task_index = {t["id"]: t for t in self._tasks}
        current_id: str | None = task_id
        visited: set[str] = set()
        while current_id is not None:
            if current_id in visited:
                return None
            visited.add(current_id)
            if current_id in project_ids:
                return current_id
            task = task_index.get(current_id)
            if task is None:
                return None
            current_id = task.get("parent")  # raw format: string or None
        return None

    def _recycle_repeating_task(self, task: dict[str, Any], lifecycle: str) -> str:
        """Create an archive copy of a repeating task, then advance the original.

        OmniFocus "recycles" repeating tasks: completing/dropping produces a
        generated task (frozen snapshot with completion/drop timestamp) while
        the original task advances to its next occurrence.

        Returns the generated task's ID (for inclusion in the response).
        """
        # 1. Deep-copy as the archive snapshot (keeps original dates)
        generated = copy.deepcopy(task)
        # OmniFocus names generated tasks {parentId}.0, .1, .2, ...
        existing_suffixes = [
            int(t["id"].rsplit(".", 1)[1])
            for t in self._tasks
            if t["id"].startswith(f"{task['id']}.") and t["id"].rsplit(".", 1)[1].isdigit()
        ]
        next_suffix = max(existing_suffixes, default=-1) + 1
        gen_id = f"{task['id']}.{next_suffix}"
        generated["id"] = gen_id
        generated["url"] = f"omnifocus:///task/{gen_id}"

        # 2. Stamp lifecycle on the generated copy
        now = datetime.now(tz=UTC).isoformat()
        if lifecycle == "complete":
            generated["completionDate"] = now
            generated["effectiveCompletionDate"] = now
        elif lifecycle == "drop":
            generated["dropDate"] = now
            generated["effectiveDropDate"] = now

        # 3. Archive copies have catchUpAutomatically = false
        generated["repetitionRule"] = dict(generated["repetitionRule"])
        generated["repetitionRule"]["catchUpAutomatically"] = False

        # 4. Insert generated copy at the original's index (before the
        #    original) so stable sort by name preserves generated-first order
        idx = self._tasks.index(task)
        self._tasks.insert(idx, generated)

        # 5. Advance the original task's anchor date (task ref still valid —
        #    insert shifts it one position right, but the dict is the same)
        rule = task["repetitionRule"]
        anchor_key = _ANCHOR_DATE_KEY_MAP[rule["anchorDateKey"]]
        current_date = task.get(anchor_key)
        if current_date is not None:
            freq, interval = _parse_rrule_interval(rule["ruleString"])
            new_date = _advance_date_by_rule(current_date, freq, interval)
            task[anchor_key] = new_date
            effective_key = f"effective{anchor_key[0].upper()}{anchor_key[1:]}"
            task[effective_key] = new_date

        return gen_id

    # ------------------------------------------------------------------
    # Operation handlers
    # ------------------------------------------------------------------

    def _handle_get_all(self) -> dict[str, Any]:
        """Return a deep copy of internal state (already in raw bridge format)."""
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

        Generates a synthetic ID and builds a complete raw-format task dict
        using make_task_dict() as a template. Returns {id, name}.
        """
        task_id = f"mem-{uuid4().hex[:8]}"
        now = datetime.now(tz=UTC).isoformat()
        parent_id = params.get("parent")
        has_parent = parent_id is not None

        # Resolve parent/project as raw string IDs
        if has_parent:
            parent_str, project_str = self._resolve_raw_parent(parent_id)
        else:
            parent_str, project_str = None, None

        # Resolve tagIds to [{id, name}] list
        tag_ids = params.get("tagIds", [])
        tags = [{"id": tid, "name": self._resolve_tag_name(tid)} for tid in tag_ids]

        # Compute status: "Blocked" if deferred to the future
        defer_date = params.get("deferDate")
        status = "Blocked" if defer_date is not None else "Available"

        task = make_task_dict(
            id=task_id,
            name=params["name"],
            url=f"omnifocus:///task/{task_id}",
            added=now,
            modified=now,
            note=params.get("note", ""),
            flagged=params.get("flagged", False),
            inInbox=not has_parent,
            parent=parent_str,
            project=project_str,
            dueDate=_ensure_tz_aware(params.get("dueDate")),
            deferDate=_ensure_tz_aware(defer_date),
            plannedDate=_ensure_tz_aware(params.get("plannedDate")),
            estimatedMinutes=params.get("estimatedMinutes"),
            tags=tags,
            status=status,
        )

        # Compute effective fields via ancestor-chain inheritance
        task["effectiveFlagged"] = self._compute_effective_flagged(task)
        task["effectiveDueDate"] = self._compute_effective_field(task, "dueDate")
        task["effectiveDeferDate"] = self._compute_effective_field(task, "deferDate")
        task["effectivePlannedDate"] = self._compute_effective_field(task, "plannedDate")

        # Repetition rule (bridge receives camelCase dict or None)
        if "repetitionRule" in params:
            task["repetitionRule"] = params["repetitionRule"]

        self._tasks.append(task)

        if parent_id is not None:
            self._set_has_children(parent_id, value=True)

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
        _DATE_KEYS = {"dueDate", "deferDate", "plannedDate"}
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
                value = params[key]
                if key in _DATE_KEYS:
                    value = _ensure_tz_aware(value)
                task[key] = value

        # Sync effectiveFlagged when flagged is updated (ancestor-chain inheritance)
        if "flagged" in params:
            task["effectiveFlagged"] = self._compute_effective_flagged(task)

        # Recompute effective dates when direct date fields change
        if "dueDate" in params:
            task["effectiveDueDate"] = self._compute_effective_field(task, "dueDate")
        if "deferDate" in params:
            task["effectiveDeferDate"] = self._compute_effective_field(task, "deferDate")
        if "plannedDate" in params:
            task["effectivePlannedDate"] = self._compute_effective_field(task, "plannedDate")

        # Recompute status when deferDate changes
        if "deferDate" in params:
            if params["deferDate"] is not None:
                task["status"] = "Blocked"
            else:
                task["status"] = "Available"

        # Repetition rule: set (dict), clear (None), or no change (absent key)
        if "repetitionRule" in params:
            task["repetitionRule"] = params["repetitionRule"]

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

        # Lifecycle — repeating tasks recycle (generate archive copy + advance).
        # Non-repeating tasks use terminal states (completing clears drop
        # dates, dropping clears completion dates).
        lifecycle = params.get("lifecycle")
        if lifecycle in ("complete", "drop") and task.get("repetitionRule") is not None:
            self._recycle_repeating_task(task, lifecycle)
        elif lifecycle == "complete":
            task["status"] = "Completed"
            task["completionDate"] = datetime.now(tz=UTC).isoformat()
            task["effectiveCompletionDate"] = task["completionDate"]
            task["dropDate"] = None
            task["effectiveDropDate"] = None
        elif lifecycle == "drop":
            task["status"] = "Dropped"
            task["dropDate"] = datetime.now(tz=UTC).isoformat()
            task["effectiveDropDate"] = task["dropDate"]
            task["completionDate"] = None
            task["effectiveCompletionDate"] = None

        # Move (raw string IDs)
        if "moveTo" in params:
            old_parent_id = task.get("parent")
            container_id = params["moveTo"].get("containerId")

            # Anchor-based moves: task becomes sibling of anchor. Use anchor's parent.
            anchor_id = params["moveTo"].get("anchorId")
            if anchor_id is not None:
                anchor = next((t for t in self._tasks if t["id"] == anchor_id), None)
                if anchor is not None:
                    container_id = anchor.get("parent")

            if container_id is None:
                task["parent"] = None
                task["project"] = None
                task["inInbox"] = True
            else:
                task["inInbox"] = False
                parent_str, project_str = self._resolve_raw_parent(container_id)
                task["parent"] = parent_str
                task["project"] = project_str
                self._set_has_children(container_id, value=True)

            # Recompute effective fields after parent change
            task["effectiveFlagged"] = self._compute_effective_flagged(task)
            task["effectiveDueDate"] = self._compute_effective_field(task, "dueDate")
            task["effectiveDeferDate"] = self._compute_effective_field(task, "deferDate")
            task["effectivePlannedDate"] = self._compute_effective_field(task, "plannedDate")

            # Recheck old parent — may no longer have children
            if old_parent_id is not None:
                self._recheck_has_children(old_parent_id)

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
