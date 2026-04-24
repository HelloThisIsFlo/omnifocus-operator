"""Bridge adapter -- maps old bridge output format to new model shape.

Transforms raw bridge snapshot dicts in-place before Pydantic validation.
Uses dict-based lookup tables (not if/elif chains) for all status mappings.

The adapter is safe to call on already-adapted data: entities without
old-format markers (e.g. no ``status`` key on tasks) are skipped.
"""

from __future__ import annotations

from typing import Any

from omnifocus_operator.config import SYSTEM_LOCATIONS
from omnifocus_operator.models.enums import ProjectType
from omnifocus_operator.repository.rrule import derive_schedule, parse_end_condition, parse_rrule

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

# Bridge scheduleType -> internal schedule base value
# (bridge "None" means no repetition -- nullify the rule)
_SCHEDULE_TYPE_MAP: dict[str, str] = {
    "Regularly": "regularly",
    "FromCompletion": "from_completion",
}

# Sentinel for bridge scheduleType "None" -- means no real repetition
_SCHEDULE_TYPE_NONE = "None"

# Bridge anchorDateKey -> snake_case
_ANCHOR_DATE_KEY_MAP: dict[str, str] = {
    "DueDate": "due_date",
    "DeferDate": "defer_date",
    "PlannedDate": "planned_date",
}

# Rename mapping: bridge camelCase -> model camelCase (effective* -> inherited*)
_INHERITED_FIELD_RENAMES: dict[str, str] = {
    "effectiveFlagged": "inheritedFlagged",
    "effectiveDueDate": "inheritedDueDate",
    "effectiveDeferDate": "inheritedDeferDate",
    "effectivePlannedDate": "inheritedPlannedDate",
    "effectiveDropDate": "inheritedDropDate",
    "effectiveCompletionDate": "inheritedCompletionDate",
}

# Dead fields to remove from tasks and projects.
# Phase 56-02: `completedByChildren`, `sequential`, and (for projects)
# `containsSingletonActions` are NO LONGER dead -- they're transformed into
# model-shape fields (`completesWithChildren`, `type`) by the per-entity
# property-surface helpers.
_TASK_DEAD_FIELDS = (
    "active",
    "effectiveActive",
    "completed",
    "shouldUseFloatingTimeZone",
)

_PROJECT_EXTRA_DEAD_FIELDS = (
    "effectiveCompletionDate",
    "effectiveFlagged",
    "effectiveDueDate",
    "effectiveDeferDate",
    "effectivePlannedDate",
    "effectiveDropDate",
)

_TAG_DEAD_FIELDS = ("allowsNextAction", "active", "effectiveActive")

_FOLDER_DEAD_FIELDS = ("active", "effectiveActive")

# Value sets for idempotency checks (already-adapted values)
_TAG_AVAILABILITY_VALUES = frozenset(_TAG_AVAILABILITY_MAP.values())
_FOLDER_AVAILABILITY_VALUES = frozenset(_FOLDER_AVAILABILITY_MAP.values())


# ---------------------------------------------------------------------------
# Per-entity adapters
# ---------------------------------------------------------------------------


def _adapt_repetition_rule(raw: dict[str, Any]) -> None:
    """Transform bridge repetition rule to structured model shape.

    Input format (raw bridge):
        ruleString, scheduleType, anchorDateKey, catchUpAutomatically
    Output format (model-ready):
        frequency, schedule, basedOn, end (optional)

    If the bridge sends scheduleType ``"None"``, the entire ``repetitionRule``
    is nullified (OmniFocus uses this to indicate no real repetition).
    """
    rule = raw.get("repetitionRule")
    if rule is None:
        return

    schedule_type = rule.get("scheduleType")
    if schedule_type is None:
        return
    if schedule_type == _SCHEDULE_TYPE_NONE:
        raw["repetitionRule"] = None
        return
    if schedule_type not in _SCHEDULE_TYPE_MAP:
        msg = f"Unknown scheduleType: {schedule_type!r}"
        raise ValueError(msg)

    anchor_key_raw = rule.get("anchorDateKey")
    if anchor_key_raw is not None and anchor_key_raw not in _ANCHOR_DATE_KEY_MAP:
        msg = f"Unknown anchorDateKey: {anchor_key_raw!r}"
        raise ValueError(msg)

    schedule_mapped = _SCHEDULE_TYPE_MAP[schedule_type]
    anchor_mapped = (
        _ANCHOR_DATE_KEY_MAP.get(anchor_key_raw, "due_date") if anchor_key_raw else "due_date"
    )
    catch_up = rule.get("catchUpAutomatically", False)
    rule_string = rule.get("ruleString", "")

    frequency = parse_rrule(rule_string)
    end = parse_end_condition(rule_string)
    schedule = derive_schedule(schedule_mapped, catch_up)

    # Build structured dict with camelCase keys (adapter output → Pydantic by_alias)
    structured: dict[str, Any] = {
        "frequency": frequency,
        "schedule": schedule,
        "basedOn": anchor_mapped,
    }
    if end is not None:
        structured["end"] = end
    raw["repetitionRule"] = structured


def _adapt_parent_ref(raw: dict[str, Any]) -> None:
    """Transform bridge project/parent fields into tagged ParentRef + ProjectRef.

    Bridge sends: project (project ID), parent (parent task ID),
    projectName, parentName as convenience fields.
    Output: parent = tagged dict ({"project": {id,name}} or {"task": {id,name}}),
            project = {id, name} (containing project at any depth).
    """
    parent_task_id = raw.get("parent")
    project_id = raw.get("project")
    inbox_ref = {
        "id": SYSTEM_LOCATIONS["inbox"].id,
        "name": SYSTEM_LOCATIONS["inbox"].name,
    }

    # Detect root task in project: parent points to the project itself
    is_root_in_project = parent_task_id is not None and parent_task_id == project_id

    if parent_task_id is not None and not is_root_in_project:
        # Subtask: parent is a task, project is the containing project
        raw["parent"] = {
            "task": {
                "id": parent_task_id,
                "name": raw.get("parentName", ""),
            }
        }
        if project_id is not None:
            raw["project"] = {
                "id": project_id,
                "name": raw.get("projectName", ""),
            }
        else:
            raw["project"] = inbox_ref
    elif project_id is not None:
        # Root task in a project: parent and project point to same project
        proj_ref = {
            "id": project_id,
            "name": raw.get("projectName", ""),
        }
        raw["parent"] = {"project": proj_ref}
        raw["project"] = proj_ref
    else:
        # Inbox task: parent and project both point to $inbox
        raw["parent"] = {"project": inbox_ref}
        raw["project"] = inbox_ref

    # Clean up convenience fields
    raw.pop("parentName", None)
    raw.pop("projectName", None)


def _rename_inherited_fields(raw: dict[str, Any]) -> None:
    """Rename bridge effective* keys to model inherited* keys.

    Safe to call on already-renamed data: missing old keys are skipped.
    """
    for old_key, new_key in _INHERITED_FIELD_RENAMES.items():
        if old_key in raw:
            raw[new_key] = raw.pop(old_key)


def _adapt_common_entity_property_surface(raw: dict[str, Any]) -> None:
    """Phase 56-02: property-surface bits shared by tasks and projects.

    Pops ``completedByChildren`` into ``completesWithChildren`` and derives
    ``hasNote`` / ``hasRepetition`` / ``hasAttachments`` from raw fields.

    Type resolution stays in the entity-specific callers — tasks use a
    two-state rule, projects use a three-state rule with HIER-05 precedence.
    """
    raw["completesWithChildren"] = bool(raw.pop("completedByChildren", False))
    raw["hasNote"] = bool(raw.get("note"))
    raw["hasRepetition"] = raw.get("repetitionRule") is not None
    raw["hasAttachments"] = bool(raw.get("hasAttachments", False))


def _adapt_task_property_surface(raw: dict[str, Any]) -> None:
    """Phase 56-02: task property surface — two-state type + shared flags."""
    _adapt_common_entity_property_surface(raw)
    raw["type"] = "sequential" if raw.pop("sequential", False) else "parallel"


def _adapt_project_property_surface(raw: dict[str, Any]) -> None:
    """Phase 56-02 (projects): three-state type via HIER-05 precedence + shared flags.

    ``containsSingletonActions`` takes precedence over ``sequential``.
    """
    _adapt_common_entity_property_surface(raw)
    raw["type"] = ProjectType.from_flags(
        sequential=bool(raw.pop("sequential", False)),
        contains_singleton_actions=bool(raw.pop("containsSingletonActions", False)),
    )


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
    _adapt_task_property_surface(raw)
    _adapt_parent_ref(raw)
    raw["order"] = None  # D-03: bridge path cannot compute order


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
    _adapt_project_property_surface(raw)


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


def _enrich_task(
    raw: dict[str, Any], task_names: dict[str, str], project_names: dict[str, str]
) -> None:
    """Enrich task parent and project refs with names from cross-entity lookups.

    After _adapt_parent_ref, parent/project are structured dicts with possibly
    empty names (bridge doesn't send parentName/projectName). This fills them
    in from the snapshot-wide name lookups.
    """
    if not isinstance(raw, dict):
        return
    parent = raw.get("parent")
    if isinstance(parent, dict):
        task_branch = parent.get("task")
        if isinstance(task_branch, dict) and not task_branch.get("name"):
            task_branch["name"] = task_names.get(task_branch.get("id", ""), "")
        proj_branch = parent.get("project")
        if isinstance(proj_branch, dict) and not proj_branch.get("name"):
            proj_branch["name"] = project_names.get(proj_branch.get("id", ""), "")

    project = raw.get("project")
    if isinstance(project, dict) and not project.get("name"):
        project["name"] = project_names.get(project.get("id", ""), "")


def _enrich_project(
    raw: dict[str, Any], folder_names: dict[str, str], task_names: dict[str, str]
) -> None:
    """Enrich project folder and nextTask from bare IDs to {id, name}."""
    folder_val = raw.get("folder")
    if isinstance(folder_val, str):
        raw["folder"] = {"id": folder_val, "name": folder_names.get(folder_val, "")}

    project_id = raw.get("id", "")
    next_task_val = raw.get("nextTask")
    if next_task_val is None:
        next_task_val = raw.get("next_task")
    if isinstance(next_task_val, str) and next_task_val == project_id:
        # Self-reference: project has no real next task
        if "nextTask" in raw:
            raw["nextTask"] = None
        else:
            raw["next_task"] = None
    elif isinstance(next_task_val, str):
        ref = {"id": next_task_val, "name": task_names.get(next_task_val, "")}
        if "nextTask" in raw:
            raw["nextTask"] = ref
        else:
            raw["next_task"] = ref


def _enrich_tag(raw: dict[str, Any], tag_names: dict[str, str]) -> None:
    """Enrich tag parent from bare ID to {id, name}."""
    parent_val = raw.get("parent")
    if isinstance(parent_val, str):
        raw["parent"] = {"id": parent_val, "name": tag_names.get(parent_val, "")}


def _enrich_folder(raw: dict[str, Any], folder_names: dict[str, str]) -> None:
    """Enrich folder parent from bare ID to {id, name}."""
    parent_val = raw.get("parent")
    if isinstance(parent_val, str):
        raw["parent"] = {"id": parent_val, "name": folder_names.get(parent_val, "")}


def adapt_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    """Transform a bridge-format snapshot dict to new model shape.

    Modifies the dict in place and returns it. Handles all entity types:
    tasks, projects, tags, and folders.

    Safe to call on already-adapted data (no-op for entities that are
    already in new-shape format).
    """
    # Build cross-entity name lookups for enrichment
    folder_names: dict[str, str] = {f["id"]: f["name"] for f in raw.get("folders", []) if "id" in f}
    tag_names: dict[str, str] = {t["id"]: t["name"] for t in raw.get("tags", []) if "id" in t}
    task_names: dict[str, str] = {t["id"]: t["name"] for t in raw.get("tasks", []) if "id" in t}
    project_names: dict[str, str] = {
        p["id"]: p["name"] for p in raw.get("projects", []) if "id" in p
    }

    # Exclude project root tasks (every project has an underlying Task object
    # that should not appear in task results -- mirrors SQL LEFT JOIN ProjectInfo
    # WHERE pi.task IS NULL in the hybrid path).
    project_id_set = set(project_names)
    if project_id_set:
        raw["tasks"] = [t for t in raw.get("tasks", []) if t.get("id") not in project_id_set]

    # Per-entity adaptation (status mapping, dead field removal, parent ref)
    for task in raw.get("tasks", []):
        _adapt_task(task)
        _rename_inherited_fields(task)
    for project in raw.get("projects", []):
        _adapt_project(project)
    for tag in raw.get("tags", []):
        _adapt_tag(tag)
    for folder in raw.get("folders", []):
        _adapt_folder(folder)

    # Cross-entity enrichment: convert bare IDs to {id, name} refs
    for task in raw.get("tasks", []):
        _enrich_task(task, task_names, project_names)
    for project in raw.get("projects", []):
        _enrich_project(project, folder_names, task_names)
    for tag in raw.get("tags", []):
        _enrich_tag(tag, tag_names)
    for folder in raw.get("folders", []):
        _enrich_folder(folder, folder_names)

    return raw
