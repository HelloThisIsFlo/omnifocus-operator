"""Bridge adapter -- maps old bridge output format to new model shape.

Transforms raw bridge snapshot dicts in-place before Pydantic validation.
Uses dict-based lookup tables (not if/elif chains) for all status mappings.

This module is NOT wired into the repository yet -- that happens in Plan 03.
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

# TagStatus -> snake_case
_TAG_STATUS_MAP: dict[str, str] = {
    "Active": "active",
    "OnHold": "on_hold",
    "Dropped": "dropped",
}

# FolderStatus -> snake_case
_FOLDER_STATUS_MAP: dict[str, str] = {
    "Active": "active",
    "Dropped": "dropped",
}

# ScheduleType -> snake_case
_SCHEDULE_TYPE_MAP: dict[str, str] = {
    "Regularly": "regularly",
    "FromCompletion": "from_completion",
    "None": "none",
}

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

_PROJECT_EXTRA_DEAD_FIELDS = ("containsSingletonActions",)

_TAG_DEAD_FIELDS = ("allowsNextAction", "active", "effectiveActive")

_FOLDER_DEAD_FIELDS = ("active", "effectiveActive")


# ---------------------------------------------------------------------------
# Per-entity adapters
# ---------------------------------------------------------------------------


def _adapt_repetition_rule(rule: dict[str, Any] | None) -> None:
    """Map ScheduleType and AnchorDateKey to snake_case in a repetition rule dict."""
    if rule is None:
        return

    schedule_type = rule.get("scheduleType")
    if schedule_type is not None:
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


def _adapt_task(raw: dict[str, Any]) -> None:
    """Map old TaskStatus -> urgency + availability, remove dead fields."""
    old_status = raw.pop("status")
    mapping = _TASK_STATUS_MAP.get(old_status)
    if mapping is None:
        msg = f"Unknown task status: {old_status!r}"
        raise ValueError(msg)
    raw["urgency"], raw["availability"] = mapping

    for key in _TASK_DEAD_FIELDS:
        raw.pop(key, None)

    _adapt_repetition_rule(raw.get("repetitionRule"))


def _adapt_project(raw: dict[str, Any]) -> None:
    """Map ProjectStatus -> availability, TaskStatus -> urgency, remove dead fields."""
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

    _adapt_repetition_rule(raw.get("repetitionRule"))


def _adapt_tag(raw: dict[str, Any]) -> None:
    """Map TagStatus -> snake_case, remove dead fields."""
    old_status = raw.get("status")
    new_status = _TAG_STATUS_MAP.get(old_status)  # type: ignore[arg-type]
    if new_status is None:
        msg = f"Unknown tag status: {old_status!r}"
        raise ValueError(msg)
    raw["status"] = new_status

    for key in _TAG_DEAD_FIELDS:
        raw.pop(key, None)


def _adapt_folder(raw: dict[str, Any]) -> None:
    """Map FolderStatus -> snake_case, remove dead fields."""
    old_status = raw.get("status")
    new_status = _FOLDER_STATUS_MAP.get(old_status)  # type: ignore[arg-type]
    if new_status is None:
        msg = f"Unknown folder status: {old_status!r}"
        raise ValueError(msg)
    raw["status"] = new_status

    for key in _FOLDER_DEAD_FIELDS:
        raw.pop(key, None)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def adapt_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    """Transform a bridge-format snapshot dict to new model shape.

    Modifies the dict in place and returns it. Handles all entity types:
    tasks, projects, tags, and folders.

    Not wired into repository yet -- that happens in Plan 03.
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
