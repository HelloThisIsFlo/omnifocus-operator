"""
Parse TaskPaper format back into the OmniFocus JSON schema.

This is the inverse of json_to_taskpaper.py. It reconstructs the JSON
structure from indented TaskPaper text, mapping standard tags back to
their JSON field names.

Limitations:
  - IDs are NOT restored (they're generated as sequential placeholders).
  - Hierarchy is reconstructed from indentation, not from ID references.
  - Some fields (effective* dates, computed status) are not round-trippable
    because they're computed by OmniFocus, not stored.
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Tag parsing
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"@(\w[\w-]*)(?:\(([^)]*)\))?")

# Reverse map: TaskPaper tag name -> JSON field name
_REVERSE_TAG_MAP = {
    "due": "dueDate",
    "defer": "deferDate",
    "effective-due": "effectiveDueDate",
    "effective-defer": "effectiveDeferDate",
    "done": "completionDate",
    "effective-done": "effectiveCompletionDate",
    "dropped": "dropDate",
    "effective-dropped": "effectiveDropDate",
    "estimate": "estimatedMinutes",
    "flagged": "flagged",
    "effective-flagged": "effectiveFlagged",
    "sequential": "sequential",
    "autodone": "completedByChildren",
    "single-actions": "containsSingletonActions",
    "floating-tz": "shouldUseFloatingTimeZone",
    "inbox": "inInbox",
    "has-children": "hasChildren",
    "repeat": "repetitionRule",
    "review": "reviewInterval",
    "last-review": "lastReviewDate",
    "next-review": "nextReviewDate",
    "next-task": "nextTask",
    "status": "status",
    "active": "active",
    "effective-active": "effectiveActive",
    "allows-next": "allowsNextAction",
    "parent": "parent",
    "project": "project",
    "folder": "folder",
    "assigned": "assignedContainer",
    "added": "added",
    "modified": "modified",
    "id": "id",
}

# Boolean tags (presence = True)
_BOOLEAN_TAGS = {
    "flagged", "sequential", "autodone", "single-actions", "floating-tz",
    "inbox", "has-children", "active", "effective-active", "effective-flagged",
    "allows-next",
}

# Date tags (value is ISO date string)
_DATE_TAGS = {
    "due", "defer", "effective-due", "effective-defer",
    "done", "effective-done", "dropped", "effective-dropped",
    "last-review", "next-review", "added", "modified",
}


def _parse_tags(text: str) -> tuple[str, dict[str, Any]]:
    """
    Extract @tags from a line, returning (clean_name, {field: value}).

    The clean_name has all @tag(...) removed and is stripped.
    """
    fields: dict[str, Any] = {}
    tag_names: list[str] = []

    for match in _TAG_RE.finditer(text):
        tag = match.group(1)
        value = match.group(2)

        if tag == "tags":
            # @tags(tag1, tag2, tag3)
            if value:
                tag_names = [t.strip() for t in value.split(",") if t.strip()]
            continue

        json_key = _REVERSE_TAG_MAP.get(tag, tag)

        if tag in _BOOLEAN_TAGS:
            fields[json_key] = True
        elif tag in _DATE_TAGS:
            # Restore to ISO if it's a short date
            if value and len(value) == 10:  # YYYY-MM-DD
                value = value + "T00:00:00.000Z"
            elif value and "T" in value and not value.endswith("Z"):
                value = value + ":00Z" if value.count(":") == 1 else value + "Z"
            fields[json_key] = value
        elif tag == "estimate":
            # @estimate(120m) -> 120
            if value:
                fields["estimatedMinutes"] = int(value.rstrip("m"))
        elif tag == "repeat":
            # @repeat(FREQ=WEEKLY;INTERVAL=1; method=fixed)
            if value:
                parts = value.split("; ")
                rule: dict[str, str] = {}
                for p in parts:
                    if p.startswith("method="):
                        rule["scheduleType"] = p[7:]
                    else:
                        rule["ruleString"] = p
                fields["repetitionRule"] = rule if rule else None
        elif tag == "review":
            # @review(1 week)
            if value:
                parts = value.split()
                if len(parts) == 2:
                    fields["reviewInterval"] = {"steps": int(parts[0]), "unit": parts[1]}
        elif tag == "status":
            fields["status"] = value
        else:
            # Generic tag
            fields[json_key] = value if value else True

    if tag_names:
        fields["tags"] = tag_names

    # Remove tags from the text to get clean name
    clean = _TAG_RE.sub("", text).strip()
    return clean, fields


# ---------------------------------------------------------------------------
# Line classification
# ---------------------------------------------------------------------------

def _classify_line(line: str) -> tuple[int, str, str]:
    """
    Classify a line as project, task, or note.

    Returns (indent_level, kind, content) where:
      - indent_level: number of leading tabs
      - kind: "project", "task", or "note"
      - content: the line content (without indent prefix)
    """
    # Count leading tabs
    stripped = line.lstrip("\t")
    indent = len(line) - len(stripped)
    content = stripped

    if not content.strip():
        return indent, "blank", ""

    # Task: starts with "- "
    if content.startswith("- "):
        return indent, "task", content[2:]

    # Project: ends with ":" (but not if the only colon is in a tag)
    # Remove tags first to check
    no_tags = _TAG_RE.sub("", content).strip()
    if no_tags.endswith(":") and len(no_tags) > 1:
        # It's a project line — content is everything before the trailing :
        # but we want to preserve the original for tag parsing
        return indent, "project", content

    return indent, "note", content


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def taskpaper_to_json(text: str) -> dict:
    """
    Parse TaskPaper text into OmniFocus JSON structure.

    Returns dict with keys: tasks, projects, tags, folders.
    Hierarchy is reconstructed from indentation.

    Note: IDs are placeholders (task_1, proj_1, etc.), not original OmniFocus IDs.
    """
    lines = text.split("\n")

    folders: list[dict] = []
    projects: list[dict] = []
    tasks: list[dict] = []
    tags_list: list[dict] = []

    # Counters for placeholder IDs
    _folder_id = 0
    _project_id = 0
    _task_id = 0
    _tag_id = 0

    # Stack: [(indent, kind, id, data)]
    stack: list[tuple[int, str, str, dict]] = []

    # Special section detection
    in_tags_section = False
    in_perspectives_section = False

    for line_text in lines:
        if not line_text.strip():
            continue

        indent, kind, content = _classify_line(line_text)

        # Skip perspectives (they don't round-trip well)
        if kind == "project" and content.strip().rstrip(":").strip() == "Perspectives":
            in_perspectives_section = True
            in_tags_section = False
            continue
        if in_perspectives_section:
            if kind == "project" and indent == 0:
                in_perspectives_section = False
            else:
                continue

        # Tags section handling
        if kind == "project" and content.strip().rstrip(":").strip() == "Tags":
            in_tags_section = True
            continue
        if in_tags_section:
            if kind == "project" and indent == 0:
                in_tags_section = False
            elif kind == "task":
                # Parse tag definition
                clean_name, fields = _parse_tags(content)
                _tag_id += 1
                tag_data = {
                    "id": f"tag_{_tag_id}",
                    "name": clean_name,
                }
                # Find parent tag from stack
                while stack and stack[-1][0] >= indent:
                    stack.pop()
                if stack and stack[-1][1] == "tag":
                    tag_data["parent"] = stack[-1][2]

                tag_data.update(fields)
                tags_list.append(tag_data)
                stack.append((indent, "tag", tag_data["id"], tag_data))
                continue
            else:
                continue

        # Pop stack to find parent at lower indent
        while stack and stack[-1][0] >= indent:
            stack.pop()

        parent_kind = stack[-1][1] if stack else None
        parent_id = stack[-1][2] if stack else None

        if kind == "note":
            # Attach note to the last item on stack
            if stack:
                existing_note = stack[-1][3].get("note", "")
                if existing_note:
                    stack[-1][3]["note"] = existing_note + "\n" + content.strip()
                else:
                    stack[-1][3]["note"] = content.strip()
            continue

        if kind == "blank":
            continue

        if kind == "project":
            # Parse tags first, then strip the trailing colon from the clean name
            clean_name, fields = _parse_tags(content)
            # The classifier already verified this is a project (colon after removing tags)
            # So strip the trailing colon from the clean name
            if clean_name.endswith(":"):
                clean_name = clean_name[:-1].strip()

            # Determine if this is a folder or project based on context
            # Heuristic: if parent is a folder or no parent, and it contains projects -> folder
            # For simplicity: top-level projects without tasks are treated as folders,
            # but we can't know this until we see children.
            # Strategy: items directly inside folders are projects; items at top level
            # that contain other projects are folders.

            if parent_kind == "folder" or (parent_kind is None and indent == 0):
                # Could be a folder or a project. We'll initially create as project.
                # If its children include other projects, we'll reclassify later.
                # For now: if parent is a folder, this is a project.
                if parent_kind == "folder":
                    _project_id += 1
                    proj_data: dict[str, Any] = {
                        "id": f"proj_{_project_id}",
                        "name": clean_name,
                        "note": "",
                        "folder": parent_id,
                    }
                    proj_data.update(fields)
                    if "tags" not in proj_data:
                        proj_data["tags"] = []
                    projects.append(proj_data)
                    stack.append((indent, "project", proj_data["id"], proj_data))
                else:
                    # Top-level: default to folder
                    _folder_id += 1
                    folder_data: dict[str, Any] = {
                        "id": f"folder_{_folder_id}",
                        "name": clean_name,
                        "note": "",
                    }
                    folder_data.update(fields)
                    folders.append(folder_data)
                    stack.append((indent, "folder", folder_data["id"], folder_data))

            elif parent_kind == "project" or parent_kind == "task":
                # Nested project = action group. In OmniFocus, action groups
                # are just tasks with children. We'll represent as a task
                # with hasChildren=true.
                _task_id += 1
                task_data: dict[str, Any] = {
                    "id": f"task_{_task_id}",
                    "name": clean_name,
                    "note": "",
                    "hasChildren": True,
                }
                if parent_kind == "project":
                    task_data["project"] = parent_id
                else:
                    task_data["parent"] = parent_id
                    # Find project up the stack
                    for s_indent, s_kind, s_id, _ in reversed(stack):
                        if s_kind == "project":
                            task_data["project"] = s_id
                            break

                task_data.update(fields)
                if "tags" not in task_data:
                    task_data["tags"] = []
                tasks.append(task_data)
                stack.append((indent, "task", task_data["id"], task_data))
            else:
                # Default: treat as folder
                _folder_id += 1
                folder_data = {
                    "id": f"folder_{_folder_id}",
                    "name": clean_name,
                    "note": "",
                }
                folder_data.update(fields)
                folders.append(folder_data)
                stack.append((indent, "folder", folder_data["id"], folder_data))

        elif kind == "task":
            clean_name, fields = _parse_tags(content)
            _task_id += 1
            task_data = {
                "id": f"task_{_task_id}",
                "name": clean_name,
                "note": "",
            }

            if parent_kind == "project":
                task_data["project"] = parent_id
            elif parent_kind == "task":
                task_data["parent"] = parent_id
                # Find project
                for s_indent, s_kind, s_id, _ in reversed(stack):
                    if s_kind == "project":
                        task_data["project"] = s_id
                        break
            elif parent_kind == "folder":
                # Task directly in a folder — unusual but handle gracefully
                # Reclassify the folder as a project
                pass

            task_data.update(fields)
            if "tags" not in task_data:
                task_data["tags"] = []

            # Set defaults for boolean fields not present
            if "completed" not in task_data:
                task_data["completed"] = "completionDate" in task_data

            tasks.append(task_data)
            stack.append((indent, "task", task_data["id"], task_data))

    return {
        "tasks": tasks,
        "projects": projects,
        "tags": tags_list,
        "folders": folders,
    }
