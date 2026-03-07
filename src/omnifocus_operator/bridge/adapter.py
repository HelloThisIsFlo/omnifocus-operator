"""Bridge adapter -- maps old bridge output format to new model shape.

Transforms raw bridge snapshot dicts in-place before Pydantic validation.
Uses dict-based lookup tables (not if/elif chains) for all status mappings.

The adapter is safe to call on already-adapted data: entities without
old-format markers (e.g. no ``status`` key on tasks) are skipped.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Mapping tables: old bridge string -> new model value(s)
# ---------------------------------------------------------------------------

# TaskStatus -> (urgency, availability)
_TASK_STATUS_MAP: dict[str, tuple[str, str]] = {
    "Available": ("none", "available"),
    "Next": ("none", "available"),
    "Blocked": ("none", "blocked"),
    "DueSoon": ("due_soon", "available"),
    "Overdue": ("overdue", "available"),
    "Completed": ("none", "completed"),
    "Dropped": ("none", "dropped"),
}

# ProjectStatus -> availability
_PROJECT_STATUS_MAP: dict[str, str] = {
    "Active": "available",
    "OnHold": "blocked",
    "Done": "completed",
    "Dropped": "dropped",
}

# TagStatus -> TagAvailability (bridge "status" field -> model "availability" field)
_TAG_AVAILABILITY_MAP: dict[str, str] = {
    "Active": "available",
    "OnHold": "blocked",
    "Dropped": "dropped",
}

# FolderStatus -> FolderAvailability (bridge "status" field -> model "availability" field)
_FOLDER_AVAILABILITY_MAP: dict[str, str] = {
    "Active": "available",
    "Dropped": "dropped",
}

# ScheduleType -> snake_case (bridge "None" means no repetition -- nullify the rule)
_SCHEDULE_TYPE_MAP: dict[str, str] = {
    "Regularly": "regularly",
    "FromCompletion": "from_completion",
}

# Sentinel for bridge scheduleType "None" -- means no real repetition
_SCHEDULE_TYPE_NONE = "None"

# AnchorDateKey -> snake_case
_ANCHOR_DATE_KEY_MAP: dict[str, str] = {
    "DueDate": "due_date",
    "DeferDate": "defer_date",
    "PlannedDate": "planned_date",
}

# Dead fields to remove from tasks and projects
_TASK_DEAD_FIELDS = (
    "active",
    "effectiveActive",
    "completed",
    "completedByChildren",
    "sequential",
    "shouldUseFloatingTimeZone",
)

_PROJECT_EXTRA_DEAD_FIELDS = ("containsSingletonActions", "effectiveCompletionDate")

_TAG_DEAD_FIELDS = ("allowsNextAction", "active", "effectiveActive")

_FOLDER_DEAD_FIELDS = ("active", "effectiveActive")

# Value sets for idempotency checks (already-adapted values)
_TAG_AVAILABILITY_VALUES = frozenset(_TAG_AVAILABILITY_MAP.values())
_FOLDER_AVAILABILITY_VALUES = frozenset(_FOLDER_AVAILABILITY_MAP.values())


# ---------------------------------------------------------------------------
# Per-entity adapters
# ---------------------------------------------------------------------------


def _adapt_repetition_rule(raw: dict[str, Any]) -> None:
    """Map ScheduleType and AnchorDateKey to snake_case in an entity's repetition rule.

    If the bridge sends scheduleType ``"None"``, the entire ``repetitionRule``
    is nullified (OmniFocus uses this to indicate no real repetition).
    """
    rule = raw.get("repetitionRule")
    if rule is None:
        return

    schedule_type = rule.get("scheduleType")
    if schedule_type is not None:
        if schedule_type == _SCHEDULE_TYPE_NONE:
            raw["repetitionRule"] = None
            return
        if schedule_type not in _SCHEDULE_TYPE_MAP:
            msg = f"Unknown scheduleType: {schedule_type!r}"
            raise ValueError(msg)
        rule["scheduleType"] = _SCHEDULE_TYPE_MAP[schedule_type]

    anchor_key = rule.get("anchorDateKey")
    if anchor_key is not None:
        if anchor_key not in _ANCHOR_DATE_KEY_MAP:
            msg = f"Unknown anchorDateKey: {anchor_key!r}"
            raise ValueError(msg)
        rule["anchorDateKey"] = _ANCHOR_DATE_KEY_MAP[anchor_key]


def _adapt_parent_ref(raw: dict[str, Any]) -> None:
    """Transform bridge project/parent string fields into unified ParentRef dict.

    Priority: parent task > containing project > None (inbox).
    Bridge sends project as project ID and parent as parent task ID (strings).
    Name fields (projectName, parentName) are used if present, else empty string.
    """
    parent_task_id = raw.get("parent")
    project_id = raw.get("project")

    if parent_task_id is not None:
        raw["parent"] = {
            "type": "task",
            "id": parent_task_id,
            "name": raw.get("parentName", ""),
        }
        raw.pop("project", None)
    elif project_id is not None:
        raw["parent"] = {
            "type": "project",
            "id": project_id,
            "name": raw.get("projectName", ""),
        }
        raw.pop("project", None)
    else:
        raw["parent"] = None
        raw.pop("project", None)

    # Clean up convenience name fields if present
    raw.pop("parentName", None)
    raw.pop("projectName", None)


def _adapt_task(raw: dict[str, Any]) -> None:
    """Map old TaskStatus -> urgency + availability, transform parent, remove dead fields.

    No-op if ``status`` key is absent (already adapted or new-shape data).
    """
    if "status" not in raw:
        return
    old_status = raw.pop("status")
    mapping = _TASK_STATUS_MAP.get(old_status)
    if mapping is None:
        msg = f"Unknown task status: {old_status!r}"
        raise ValueError(msg)
    raw["urgency"], raw["availability"] = mapping

    for key in _TASK_DEAD_FIELDS:
        raw.pop(key, None)

    _adapt_repetition_rule(raw)
    _adapt_parent_ref(raw)


def _adapt_project(raw: dict[str, Any]) -> None:
    """Map ProjectStatus -> availability, TaskStatus -> urgency, remove dead fields.

    No-op if ``status`` key is absent (already adapted or new-shape data).
    """
    if "status" not in raw:
        return
    old_status = raw.pop("status")
    availability = _PROJECT_STATUS_MAP.get(old_status)
    if availability is None:
        msg = f"Unknown project status: {old_status!r}"
        raise ValueError(msg)
    raw["availability"] = availability

    old_task_status = raw.pop("taskStatus")
    task_mapping = _TASK_STATUS_MAP.get(old_task_status)
    if task_mapping is None:
        msg = f"Unknown project taskStatus: {old_task_status!r}"
        raise ValueError(msg)
    raw["urgency"] = task_mapping[0]  # First element is urgency

    for key in _TASK_DEAD_FIELDS:
        raw.pop(key, None)
    for key in _PROJECT_EXTRA_DEAD_FIELDS:
        raw.pop(key, None)

    _adapt_repetition_rule(raw)


def _adapt_tag(raw: dict[str, Any]) -> None:
    """Map bridge ``status`` -> model ``availability``, remove dead fields.

    No-op if ``availability`` key already exists with a valid value
    (already adapted or new-shape data).
    """
    existing = raw.get("availability")
    if existing in _TAG_AVAILABILITY_VALUES:
        return  # Already adapted
    old_status = raw.pop("status", None)
    new_availability = _TAG_AVAILABILITY_MAP.get(old_status)
    if new_availability is None:
        msg = f"Unknown tag status: {old_status!r}"
        raise ValueError(msg)
    raw["availability"] = new_availability

    for key in _TAG_DEAD_FIELDS:
        raw.pop(key, None)


def _adapt_folder(raw: dict[str, Any]) -> None:
    """Map bridge ``status`` -> model ``availability``, remove dead fields.

    No-op if ``availability`` key already exists with a valid value
    (already adapted or new-shape data).
    """
    existing = raw.get("availability")
    if existing in _FOLDER_AVAILABILITY_VALUES:
        return  # Already adapted
    old_status = raw.pop("status", None)
    new_availability = _FOLDER_AVAILABILITY_MAP.get(old_status)
    if new_availability is None:
        msg = f"Unknown folder status: {old_status!r}"
        raise ValueError(msg)
    raw["availability"] = new_availability

    for key in _FOLDER_DEAD_FIELDS:
        raw.pop(key, None)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def adapt_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    """Transform a bridge-format snapshot dict to new model shape.

    Modifies the dict in place and returns it. Handles all entity types:
    tasks, projects, tags, and folders.

    Safe to call on already-adapted data (no-op for entities that are
    already in new-shape format).
    """
    for task in raw.get("tasks", []):
        _adapt_task(task)
    for project in raw.get("projects", []):
        _adapt_project(project)
    for tag in raw.get("tags", []):
        _adapt_tag(tag)
    for folder in raw.get("folders", []):
        _adapt_folder(folder)
    return raw
