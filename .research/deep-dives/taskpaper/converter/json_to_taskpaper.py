"""
Convert OmniFocus JSON dump to TaskPaper format.

The JSON schema matches operatorBridgeScript.js output:
  { tasks: [...], projects: [...], tags: [...], folders: [...], perspectives: [...] }

Two modes:
  - Mode.FULL:  Every field as @tag(value). Lossless round-trip target.
  - Mode.LLM:   Only fields an LLM needs for reasoning. Max token efficiency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Mode(Enum):
    FULL = "full"
    LLM = "llm"


# ---------------------------------------------------------------------------
# Field configuration
# ---------------------------------------------------------------------------

# Fields to SKIP in LLM mode (internal IDs, effective duplicates, metadata)
_LLM_SKIP_TASK = {
    "id", "added", "modified", "active", "effectiveActive",
    "effectiveFlagged", "effectiveCompletionDate", "effectiveDropDate",
    "shouldUseFloatingTimeZone", "assignedContainer",
    "completedByChildren", "hasChildren",
    # effective dates: only show if different from direct date
    # (handled specially below)
}

_LLM_SKIP_PROJECT = {
    "id", "taskStatus", "effectiveFlagged",
    "effectiveCompletionDate", "effectiveDropDate",
    "shouldUseFloatingTimeZone", "hasChildren",
    "completedByChildren", "nextTask",
}

_LLM_SKIP_TAG = {
    "id", "added", "modified", "active", "effectiveActive",
}

_LLM_SKIP_FOLDER = {
    "id", "added", "modified", "active", "effectiveActive",
}

# Standard TaskPaper tag names (OmniFocus conventions)
_TAG_MAP = {
    "dueDate": "due",
    "deferDate": "defer",
    "effectiveDueDate": "effective-due",
    "effectiveDeferDate": "effective-defer",
    "completionDate": "done",
    "effectiveCompletionDate": "effective-done",
    "dropDate": "dropped",
    "effectiveDropDate": "effective-dropped",
    "estimatedMinutes": "estimate",
    "flagged": "flagged",
    "effectiveFlagged": "effective-flagged",
    "sequential": "sequential",
    "completedByChildren": "autodone",
    "containsSingletonActions": "single-actions",
    "shouldUseFloatingTimeZone": "floating-tz",
    "inInbox": "inbox",
    "hasChildren": "has-children",
    "repetitionRule": "repeat",
    "reviewInterval": "review",
    "lastReviewDate": "last-review",
    "nextReviewDate": "next-review",
    "nextTask": "next-task",
    "status": "status",
    "active": "active",
    "effectiveActive": "effective-active",
    "allowsNextAction": "allows-next",
    "parent": "parent",
    "project": "project",
    "folder": "folder",
    "assignedContainer": "assigned",
    "added": "added",
    "modified": "modified",
}


def _format_date(iso: str | None) -> str | None:
    """Shorten ISO dates: drop time if midnight, drop seconds if :00."""
    if not iso:
        return None
    # Full ISO: 2026-02-21T00:00:00.000Z -> 2026-02-21
    if iso.endswith("T00:00:00.000Z") or iso.endswith("T00:00:00Z"):
        return iso[:10]
    # Drop trailing Z and .000 for compactness
    s = iso.replace(".000Z", "").replace("Z", "")
    # Drop seconds if :00
    if s.endswith(":00"):
        s = s[:-3]
    return s


def _format_repetition(rule: dict | None) -> str | None:
    if not rule:
        return None
    parts = []
    if rule.get("ruleString"):
        parts.append(rule["ruleString"])
    if rule.get("scheduleType"):
        parts.append(f"method={rule['scheduleType']}")
    return "; ".join(parts) if parts else None


def _format_review_interval(ri: dict | None) -> str | None:
    if not ri:
        return None
    steps = ri.get("steps", "")
    unit = ri.get("unit", "")
    return f"{steps} {unit}".strip() or None


def _format_tag_value(key: str, value: Any) -> str | None:
    """Format a JSON field as a TaskPaper @tag or @tag(value). Returns None to skip."""
    if value is None:
        return None

    # Boolean fields: only emit if True (except specific ones)
    if isinstance(value, bool):
        if key in ("completed", "flagged", "sequential", "completedByChildren",
                    "containsSingletonActions", "inInbox", "shouldUseFloatingTimeZone",
                    "active", "effectiveActive", "effectiveFlagged",
                    "hasChildren", "allowsNextAction"):
            return f"@{_TAG_MAP.get(key, key)}" if value else None
        return None

    # Date fields
    if key in ("dueDate", "deferDate", "effectiveDueDate", "effectiveDeferDate",
               "completionDate", "effectiveCompletionDate", "dropDate", "effectiveDropDate",
               "lastReviewDate", "nextReviewDate", "added", "modified"):
        d = _format_date(value)
        return f"@{_TAG_MAP.get(key, key)}({d})" if d else None

    # Numeric
    if key == "estimatedMinutes":
        return f"@estimate({value}m)" if value else None

    # Complex objects
    if key == "repetitionRule":
        v = _format_repetition(value)
        return f"@repeat({v})" if v else None

    if key == "reviewInterval":
        v = _format_review_interval(value)
        return f"@review({v})" if v else None

    # String enum fields
    if key == "status":
        return f"@status({value})" if value else None

    # ID references
    if key in ("project", "parent", "folder", "assignedContainer", "nextTask"):
        tag = _TAG_MAP.get(key, key)
        return f"@{tag}({value})"

    # Tags list — handled separately
    if key == "tags":
        return None

    # Fallback: generic @key(value)
    tag = _TAG_MAP.get(key, key)
    return f"@{tag}({value})"


# ---------------------------------------------------------------------------
# Tree building
# ---------------------------------------------------------------------------

@dataclass
class _Node:
    """Internal tree node for hierarchy reconstruction."""
    kind: str  # "folder", "project", "task"
    data: dict
    children: list[_Node] = field(default_factory=list)


def _build_tree(dump: dict) -> list[_Node]:
    """Build a hierarchy: folders > projects > tasks (with sub-tasks)."""
    folders = {f["id"]: _Node("folder", f) for f in dump.get("folders", [])}
    projects = {p["id"]: _Node("project", p) for p in dump.get("projects", [])}
    tasks_by_id: dict[str, _Node] = {}

    # Index tasks
    for t in dump.get("tasks", []):
        tasks_by_id[t["id"]] = _Node("task", t)

    # Build task hierarchy (sub-tasks under parent tasks)
    root_tasks: dict[str, list[_Node]] = {}  # project_id -> [task_nodes]
    orphan_tasks: list[_Node] = []

    for tid, tnode in tasks_by_id.items():
        t = tnode.data
        parent_id = t.get("parent")

        if parent_id and parent_id in tasks_by_id:
            # Sub-task: attach to parent task
            tasks_by_id[parent_id].children.append(tnode)
        elif t.get("project"):
            # Top-level task in a project
            pid = t["project"]
            root_tasks.setdefault(pid, []).append(tnode)
        elif t.get("inInbox"):
            orphan_tasks.append(tnode)
        else:
            orphan_tasks.append(tnode)

    # Attach tasks to projects
    for pid, pnode in projects.items():
        pnode.children = root_tasks.get(pid, [])

    # Attach projects to folders
    for pid, pnode in projects.items():
        fid = pnode.data.get("folder")
        if fid and fid in folders:
            folders[fid].children.append(pnode)

    # Attach sub-folders
    for fid, fnode in folders.items():
        parent_fid = fnode.data.get("parent")
        if parent_fid and parent_fid in folders:
            folders[parent_fid].children.append(fnode)

    # Collect roots: top-level folders, unparented projects, inbox tasks
    root_folder_ids = {fid for fid, f in folders.items() if not f.data.get("parent") or f.data["parent"] not in folders}
    root_project_ids = {pid for pid, p in projects.items() if not p.data.get("folder") or p.data["folder"] not in folders}

    roots: list[_Node] = []
    # Inbox tasks first
    if orphan_tasks:
        inbox_node = _Node("folder", {"name": "Inbox", "id": "__inbox__"}, orphan_tasks)
        roots.append(inbox_node)

    for fid in sorted(root_folder_ids, key=lambda x: folders[x].data.get("name", "")):
        roots.append(folders[fid])

    for pid in sorted(root_project_ids, key=lambda x: projects[x].data.get("name", "")):
        roots.append(projects[pid])

    return roots


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _task_tags_str(data: dict, mode: Mode, entity_type: str = "auto") -> str:
    """Build the @tag portion of a task/project/folder line."""
    skip = set()
    if mode == Mode.LLM:
        if entity_type == "task" or (entity_type == "auto" and "project" in data):
            skip = _LLM_SKIP_TASK
        elif entity_type == "folder":
            skip = _LLM_SKIP_FOLDER
        else:
            skip = _LLM_SKIP_PROJECT

    parts: list[str] = []
    # Name and note handled separately
    skip_keys = {"name", "note", "tags", "id"} | skip

    # In LLM mode, skip effective dates if they match the direct date
    if mode == Mode.LLM:
        for eff, direct in [
            ("effectiveDueDate", "dueDate"),
            ("effectiveDeferDate", "deferDate"),
        ]:
            if data.get(eff) == data.get(direct):
                skip_keys.add(eff)

    for key, value in data.items():
        if key in skip_keys:
            continue
        tag_str = _format_tag_value(key, value)
        if tag_str:
            parts.append(tag_str)

    # OmniFocus tags as @tags(...)
    tag_names = data.get("tags", [])
    if tag_names:
        parts.append(f"@tags({', '.join(tag_names)})")

    return " ".join(parts)


def _serialize_node(node: _Node, indent: int, mode: Mode, lines: list[str]) -> None:
    """Recursively serialize a node to TaskPaper lines."""
    prefix = "\t" * indent
    data = node.data
    name = data.get("name", "")
    tags_str = _task_tags_str(data, mode, entity_type=node.kind)
    tag_suffix = f" {tags_str}" if tags_str else ""

    if node.kind == "folder":
        lines.append(f"{prefix}{name}:{tag_suffix}")
    elif node.kind == "project":
        lines.append(f"{prefix}{name}:{tag_suffix}")
    elif node.kind == "task":
        lines.append(f"{prefix}- {name}{tag_suffix}")

    # Note as indented plain text (only if non-empty)
    note = data.get("note", "")
    if note and note.strip():
        if mode == Mode.LLM and len(note) > 500:
            note = note[:497] + "..."
        for note_line in note.strip().split("\n"):
            lines.append(f"{prefix}\t{note_line}")

    # Children
    for child in node.children:
        _serialize_node(child, indent + 1, mode, lines)


# ---------------------------------------------------------------------------
# Tags section
# ---------------------------------------------------------------------------

def _serialize_tags_section(tags: list[dict], mode: Mode) -> list[str]:
    """Serialize tag definitions as a special Tags: project."""
    if not tags:
        return []

    skip = _LLM_SKIP_TAG if mode == Mode.LLM else set()

    # Build tag hierarchy
    tag_by_id: dict[str, dict] = {t["id"]: t for t in tags}
    root_tags = [t for t in tags if not t.get("parent") or t["parent"] not in tag_by_id]
    child_map: dict[str, list[dict]] = {}
    for t in tags:
        pid = t.get("parent")
        if pid and pid in tag_by_id:
            child_map.setdefault(pid, []).append(t)

    lines = ["Tags:"]

    def _write_tag(tag: dict, depth: int) -> None:
        prefix = "\t" * (depth + 1)
        parts = []
        for k, v in tag.items():
            if k in {"name", "id"} | skip:
                continue
            if k == "parent":
                continue
            tv = _format_tag_value(k, v)
            if tv:
                parts.append(tv)
        tag_str = " ".join(parts)
        suffix = f" {tag_str}" if tag_str else ""
        lines.append(f"{prefix}- {tag['name']}{suffix}")
        for child in child_map.get(tag["id"], []):
            _write_tag(child, depth + 1)

    for rt in sorted(root_tags, key=lambda t: t.get("name", "")):
        _write_tag(rt, 0)

    return lines


# ---------------------------------------------------------------------------
# Perspectives section
# ---------------------------------------------------------------------------

def _serialize_perspectives(perspectives: list[dict], mode: Mode) -> list[str]:
    if not perspectives or mode == Mode.LLM:
        return []
    lines = ["Perspectives:"]
    for p in perspectives:
        lines.append(f"\t- {p.get('name', '')} @id({p.get('id', '')})")
    return lines


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def json_to_taskpaper(dump: dict, mode: Mode = Mode.LLM) -> str:
    """
    Convert an OmniFocus JSON dump to TaskPaper format.

    Args:
        dump: Dict with keys: tasks, projects, tags, folders, perspectives
        mode: Mode.FULL for lossless, Mode.LLM for token-efficient

    Returns:
        TaskPaper-formatted string
    """
    tree = _build_tree(dump)
    lines: list[str] = []

    for root in tree:
        _serialize_node(root, 0, mode, lines)

    # Tags section
    tag_lines = _serialize_tags_section(dump.get("tags", []), mode)
    if tag_lines:
        lines.append("")
        lines.extend(tag_lines)

    # Perspectives (full mode only)
    persp_lines = _serialize_perspectives(dump.get("perspectives", []), mode)
    if persp_lines:
        lines.append("")
        lines.extend(persp_lines)

    return "\n".join(lines) + "\n"
