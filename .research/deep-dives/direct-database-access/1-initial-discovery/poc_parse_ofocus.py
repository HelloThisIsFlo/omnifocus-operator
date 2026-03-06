#!/usr/bin/env python3
"""
OmniFocus .ofocus Direct Database Parser — Proof of Concept

Reads the .ofocus database bundle directly from the filesystem,
bypassing OmniFocus entirely. No IPC, no URL scheme, no Omni Automation.

Usage:
    python3 parse_ofocus.py [path_to_ofocus_bundle]

If no path is given, uses the backup at /tmp/omnifocus-db-copy/OmniFocus.ofocus
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NS = "{http://www.omnigroup.com/namespace/OmniFocus/v2}"

# ─── Data classes ───────────────────────────────────────────


@dataclass
class OFTask:
    id: str
    name: str = ""
    note: str = ""
    added: str | None = None
    modified: str | None = None
    flagged: bool = False
    completed: str | None = None  # completion date
    due: str | None = None
    start: str | None = None  # defer date
    planned: str | None = None
    estimated_minutes: int | None = None
    sequential: bool = False  # order == "sequential"
    completed_by_children: bool = False
    inbox: bool = False
    repetition_rule: str | None = None
    repetition_method: str | None = None
    # Relationships
    parent_id: str | None = None  # parent task id
    project_folder_id: str | None = None  # folder containing this project
    is_project: bool = False
    project_status: str | None = None  # active/on-hold/done/dropped
    project_singleton: bool = False
    last_review: str | None = None
    next_review: str | None = None
    review_interval: str | None = None
    tag_ids: list[str] = field(default_factory=list)


@dataclass
class OFFolder:
    id: str
    name: str = ""
    added: str | None = None
    modified: str | None = None
    parent_id: str | None = None
    hidden: bool = False


@dataclass
class OFTag:
    """OmniFocus calls these 'context' in the XML."""

    id: str
    name: str = ""
    added: str | None = None
    modified: str | None = None
    parent_id: str | None = None
    hidden: bool = False
    prohibits_next_action: bool = False


@dataclass
class OFPerspective:
    id: str
    name: str = ""
    added: str | None = None
    modified: str | None = None


@dataclass
class OFSnapshot:
    """Complete parsed state of the OmniFocus database."""

    tasks: dict[str, OFTask] = field(default_factory=dict)
    folders: dict[str, OFFolder] = field(default_factory=dict)
    tags: dict[str, OFTag] = field(default_factory=dict)
    perspectives: dict[str, OFPerspective] = field(default_factory=dict)
    task_tag_links: dict[str, tuple[str, str]] = field(
        default_factory=dict
    )  # link_id -> (task_id, tag_id)

    # Tracking
    transactions_applied: int = 0
    deleted_count: int = 0


# ─── XML parsing helpers ───────────────────────────────────


def _text(el: ET.Element, tag: str) -> str | None:
    """Get text content of a child element, or None if empty/missing."""
    child = el.find(f"{NS}{tag}")
    if child is not None and child.text:
        return child.text.strip()
    return None


def _bool(el: ET.Element, tag: str) -> bool:
    return _text(el, tag) == "true"


def _idref(el: ET.Element, tag: str) -> str | None:
    """Get the idref attribute from a child element."""
    child = el.find(f"{NS}{tag}")
    if child is not None:
        return child.get("idref")
    return None


def _note_text(el: ET.Element) -> str:
    """Extract plain text from the rich-text note structure."""
    note_el = el.find(f"{NS}note")
    if note_el is None:
        return ""
    # Notes have <text><p><run><lit>...</lit></run></p></text>
    parts = []
    for lit in note_el.iter(f"{NS}lit"):
        if lit.text:
            parts.append(lit.text)
    return "\n".join(parts)


# ─── Element parsers ───────────────────────────────────────


def _parse_task(el: ET.Element) -> OFTask:
    task = OFTask(id=el.get("id", ""))
    task.name = _text(el, "name") or ""
    task.note = _note_text(el)
    task.added = _text(el, "added")
    task.modified = _text(el, "modified")
    task.flagged = _bool(el, "flagged")
    task.completed = _text(el, "completed")
    task.due = _text(el, "due")
    task.start = _text(el, "start")
    task.planned = _text(el, "planned")
    task.inbox = _bool(el, "inbox")
    task.completed_by_children = _bool(el, "completed-by-children")
    task.repetition_rule = _text(el, "repetition-rule")
    task.repetition_method = _text(el, "repetition-method")

    est = _text(el, "estimated-minutes")
    if est:
        with contextlib.suppress(ValueError):
            task.estimated_minutes = int(float(est))

    order = _text(el, "order")
    task.sequential = order == "sequential"

    # Parent task reference: <task idref="..."/>
    task.parent_id = _idref(el, "task")

    # Project info: <project><folder idref="..."/><status>active</status>...</project>
    proj_el = el.find(f"{NS}project")
    if proj_el is not None and len(proj_el) > 0:
        task.is_project = True
        task.project_folder_id = _idref(proj_el, "folder")  # uses 'folder' inside project
        # Need to look for folder idref within project element
        folder_child = proj_el.find(f"{NS}folder")
        if folder_child is not None:
            task.project_folder_id = folder_child.get("idref")
        status_el = proj_el.find(f"{NS}status")
        if status_el is not None and status_el.text:
            task.project_status = status_el.text.strip()
        singleton_el = proj_el.find(f"{NS}singleton")
        task.project_singleton = singleton_el is not None and singleton_el.text == "true"
        lr = proj_el.find(f"{NS}last-review")
        if lr is not None and lr.text:
            task.last_review = lr.text.strip()
        nr = proj_el.find(f"{NS}next-review")
        if nr is not None and nr.text:
            task.next_review = nr.text.strip()
        ri = proj_el.find(f"{NS}review-interval")
        if ri is not None and ri.text:
            task.review_interval = ri.text.strip()

    # Legacy context reference (still present as <context idref="..."/>)
    # This is the "primary" tag, but task-to-tag is the canonical source
    ctx_ref = _idref(el, "context")
    if ctx_ref:
        task.tag_ids = [ctx_ref]  # Will be overwritten by task-to-tag links

    return task


def _parse_folder(el: ET.Element) -> OFFolder:
    f = OFFolder(id=el.get("id", ""))
    f.name = _text(el, "name") or ""
    f.added = _text(el, "added")
    f.modified = _text(el, "modified")
    f.parent_id = _idref(el, "folder")
    f.hidden = el.find(f"{NS}hidden") is not None
    return f


def _parse_tag(el: ET.Element) -> OFTag:
    """Parse a <context> element (OmniFocus's internal name for tags)."""
    t = OFTag(id=el.get("id", ""))
    t.name = _text(el, "name") or ""
    t.added = _text(el, "added")
    t.modified = _text(el, "modified")
    t.parent_id = _idref(el, "context")
    t.hidden = el.find(f"{NS}hidden") is not None
    t.prohibits_next_action = _bool(el, "prohibits-next-action")
    return t


def _parse_perspective(el: ET.Element) -> OFPerspective:
    p = OFPerspective(id=el.get("id", ""))
    p.added = _text(el, "added")
    p.modified = _text(el, "modified")
    # Name is inside the plist structure
    plist = el.find(f"{NS}plist")
    if plist is not None:
        # Look for name key in the plist dict
        dict_el = plist.find(f"{NS}dict")
        if dict_el is not None:
            all_children = list(dict_el)
            for i, child in enumerate(all_children):
                if child.tag == f"{NS}key" and child.text == "name" and i + 1 < len(all_children):
                    val = all_children[i + 1]
                    if val.text:
                        p.name = val.text
    return p


def _parse_task_to_tag(el: ET.Element) -> tuple[str, str, str] | None:
    """Parse a <task-to-tag> element. Returns (link_id, task_id, tag_id) or None."""
    link_id = el.get("id", "")
    task_id = _idref(el, "task")
    tag_id = _idref(el, "context")
    if task_id and tag_id:
        return (link_id, task_id, tag_id)
    return None


# ─── Merge logic (delta application) ──────────────────────


def _merge_task_update(existing: OFTask, el: ET.Element) -> None:
    """Apply an update delta to an existing task (in-place)."""
    for child in el:
        tag = child.tag.replace(NS, "")
        if tag == "name" and child.text:
            existing.name = child.text.strip()
        elif tag == "modified" and child.text:
            existing.modified = child.text.strip()
        elif tag == "added" and child.text:
            existing.added = child.text.strip()
        elif tag == "flagged":
            existing.flagged = child.text == "true"
        elif tag == "completed" and child.text:
            existing.completed = child.text.strip()
        elif tag == "due" and child.text:
            existing.due = child.text.strip()
        elif tag == "start" and child.text:
            existing.start = child.text.strip()
        elif tag == "planned" and child.text:
            existing.planned = child.text.strip()
        elif tag == "order":
            existing.sequential = child.text == "sequential"
        elif tag == "note":
            parts = []
            for lit in child.iter(f"{NS}lit"):
                if lit.text:
                    parts.append(lit.text)
            existing.note = "\n".join(parts)


# ─── Main parser ──────────────────────────────────────────


def parse_ofocus(bundle_path: Path) -> OFSnapshot:
    """Parse an .ofocus bundle into a complete OFSnapshot."""
    snap = OFSnapshot()

    # Collect all transaction zips (excluding data/ subdirectory)
    zip_files = sorted(
        [
            f
            for f in os.listdir(bundle_path)
            if f.endswith(".zip") and os.path.isfile(bundle_path / f)
        ]
    )

    for zname in zip_files:
        zf = zipfile.ZipFile(bundle_path / zname)
        root = ET.fromstring(zf.read("contents.xml"))
        snap.transactions_applied += 1

        for child in root:
            tag = child.tag.replace(NS, "")
            op = child.get("op", "")  # "", "update", "delete", "reference"
            elem_id = child.get("id", "")

            if tag == "task":
                if op == "delete":
                    snap.tasks.pop(elem_id, None)
                    snap.deleted_count += 1
                elif op == "update":
                    if elem_id in snap.tasks:
                        _merge_task_update(snap.tasks[elem_id], child)
                    else:
                        snap.tasks[elem_id] = _parse_task(child)
                elif op == "reference":
                    pass  # Context for other elements, not actual data
                else:
                    snap.tasks[elem_id] = _parse_task(child)

            elif tag == "folder":
                if op == "delete":
                    snap.folders.pop(elem_id, None)
                    snap.deleted_count += 1
                elif op in ("", "insert"):
                    snap.folders[elem_id] = _parse_folder(child)
                # update/reference: skip for now

            elif tag == "context":
                if op == "delete":
                    snap.tags.pop(elem_id, None)
                    snap.deleted_count += 1
                elif op in ("", "insert"):
                    snap.tags[elem_id] = _parse_tag(child)

            elif tag == "perspective":
                if op == "delete":
                    snap.perspectives.pop(elem_id, None)
                    snap.deleted_count += 1
                elif op in ("", "insert"):
                    snap.perspectives[elem_id] = _parse_perspective(child)

            elif tag == "task-to-tag":
                if op == "delete":
                    snap.task_tag_links.pop(elem_id, None)
                else:
                    result = _parse_task_to_tag(child)
                    if result:
                        link_id, task_id, tag_id = result
                        snap.task_tag_links[link_id] = (task_id, tag_id)

    # Rebuild tag_ids on tasks from task-to-tag links
    for task in snap.tasks.values():
        task.tag_ids = []
    for _link_id, (task_id, tag_id) in snap.task_tag_links.items():
        if task_id in snap.tasks:
            snap.tasks[task_id].tag_ids.append(tag_id)

    return snap


# ─── Output formatters ────────────────────────────────────


def print_summary(snap: OFSnapshot) -> None:
    """Print a human-readable summary of the database."""
    all_tasks = list(snap.tasks.values())
    projects = [t for t in all_tasks if t.is_project]
    active_projects = [p for p in projects if p.project_status == "active" and not p.completed]
    plain_tasks = [t for t in all_tasks if not t.is_project]
    active_tasks = [t for t in plain_tasks if not t.completed]
    completed_tasks = [t for t in plain_tasks if t.completed]
    flagged = [t for t in active_tasks if t.flagged]
    inbox = [t for t in active_tasks if t.inbox]
    with_due = sorted([t for t in active_tasks if t.due], key=lambda t: t.due or "")

    print("=" * 60)
    print("OmniFocus Database — Direct Parse Summary")
    print("=" * 60)
    print(f"Transactions applied:  {snap.transactions_applied}")
    print(f"Deleted elements:      {snap.deleted_count}")
    print()
    print(f"Folders:               {len(snap.folders)}")
    print(f"Tags:                  {len(snap.tags)}")
    print(f"Perspectives:          {len(snap.perspectives)}")
    print()
    print(f"Total tasks (incl projects): {len(all_tasks)}")
    print(f"  Projects:            {len(projects)} ({len(active_projects)} active)")
    print(f"  Tasks:               {len(plain_tasks)}")
    print(f"    Active:            {len(active_tasks)}")
    print(f"    Completed:         {len(completed_tasks)}")
    print(f"    Flagged:           {len(flagged)}")
    print(f"    In inbox:          {len(inbox)}")
    print(f"    With due date:     {len(with_due)}")

    if with_due:
        print()
        print("── Next 10 Due Tasks ──")
        for t in with_due[:10]:
            tags_str = ""
            if t.tag_ids:
                tag_names = [snap.tags[tid].name for tid in t.tag_ids if tid in snap.tags]
                if tag_names:
                    tags_str = f" [{', '.join(tag_names)}]"
            print(f"  {t.due[:16]}  {t.name[:55]}{tags_str}")

    if flagged:
        print()
        print("── Flagged Tasks ──")
        for t in flagged[:10]:
            print(f"  {t.name[:70]}")

    if inbox:
        print()
        print("── Inbox ──")
        for t in inbox[:10]:
            print(f"  {t.name[:70]}")

    # Show folder tree
    print()
    print("── Top-level Folders ──")
    top_folders = [f for f in snap.folders.values() if not f.parent_id]
    for f in sorted(top_folders, key=lambda x: x.name):
        child_count = sum(1 for c in snap.folders.values() if c.parent_id == f.id)
        proj_count = sum(1 for t in projects if t.project_folder_id == f.id)
        print(f"  {f.name[:50]} ({child_count} subfolders, {proj_count} projects)")

    # Show tag tree
    print()
    print("── Top-level Tags ──")
    top_tags = [t for t in snap.tags.values() if not t.parent_id]
    for t in sorted(top_tags, key=lambda x: x.name):
        child_count = sum(1 for c in snap.tags.values() if c.parent_id == t.id)
        task_count = sum(1 for task in active_tasks if t.id in task.tag_ids)
        suffix = " (on hold)" if t.prohibits_next_action else ""
        print(f"  {t.name[:50]} ({task_count} tasks, {child_count} children){suffix}")


def to_bridge_format(snap: OFSnapshot) -> dict[str, Any]:
    """Convert to the same format as bridge.js handleSnapshot() for comparison."""
    result: dict[str, Any] = {
        "tasks": [],
        "projects": [],
        "tags": [],
        "folders": [],
        "perspectives": [],
    }

    for task in snap.tasks.values():
        if task.is_project:
            result["projects"].append(
                {
                    "id": task.id,
                    "name": task.name,
                    "note": task.note,
                    "status": (task.project_status or "active")
                    .replace("-", "")
                    .title()
                    .replace("On Hold", "OnHold")
                    .replace("Active", "Active"),
                    "active": task.project_status == "active",
                    "completed": bool(task.completed),
                    "flagged": task.flagged,
                    "sequential": task.sequential,
                    "dueDate": task.due,
                    "deferDate": task.start,
                    "completionDate": task.completed,
                    "plannedDate": task.planned,
                    "estimatedMinutes": task.estimated_minutes,
                    "folder": task.project_folder_id,
                    "tags": [
                        {"id": tid, "name": snap.tags[tid].name}
                        for tid in task.tag_ids
                        if tid in snap.tags
                    ],
                }
            )
        else:
            result["tasks"].append(
                {
                    "id": task.id,
                    "name": task.name,
                    "note": task.note,
                    "added": task.added,
                    "modified": task.modified,
                    "flagged": task.flagged,
                    "completed": bool(task.completed),
                    "sequential": task.sequential,
                    "dueDate": task.due,
                    "deferDate": task.start,
                    "completionDate": task.completed,
                    "plannedDate": task.planned,
                    "estimatedMinutes": task.estimated_minutes,
                    "inInbox": task.inbox,
                    "parent": task.parent_id,
                    "project": _find_project_id(task, snap),
                    "tags": [
                        {"id": tid, "name": snap.tags[tid].name}
                        for tid in task.tag_ids
                        if tid in snap.tags
                    ],
                }
            )

    for f in snap.folders.values():
        result["folders"].append(
            {
                "id": f.id,
                "name": f.name,
                "added": f.added,
                "modified": f.modified,
                "parent": f.parent_id,
            }
        )

    for t in snap.tags.values():
        result["tags"].append(
            {
                "id": t.id,
                "name": t.name,
                "added": t.added,
                "modified": t.modified,
                "parent": t.parent_id,
                "allowsNextAction": not t.prohibits_next_action,
            }
        )

    for p in snap.perspectives.values():
        result["perspectives"].append(
            {
                "id": p.id,
                "name": p.name,
            }
        )

    return result


def _find_project_id(task: OFTask, snap: OFSnapshot) -> str | None:
    """Walk up the parent chain to find the containing project."""
    visited = set()
    current_id = task.parent_id
    while current_id and current_id not in visited:
        visited.add(current_id)
        parent = snap.tasks.get(current_id)
        if parent is None:
            return None
        if parent.is_project:
            return parent.id
        current_id = parent.parent_id
    return None


# ─── Main ─────────────────────────────────────────────────


def main():
    if len(sys.argv) > 1:
        bundle_path = Path(sys.argv[1])
    else:
        bundle_path = Path("/tmp/omnifocus-db-copy/OmniFocus.ofocus")

    if not bundle_path.exists():
        print(f"Error: {bundle_path} does not exist", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing: {bundle_path}")
    print()

    snap = parse_ofocus(bundle_path)
    print_summary(snap)

    # Also write bridge-compatible JSON
    bridge_data = to_bridge_format(snap)
    out_path = bundle_path.parent / "parsed_snapshot.json"
    with open(out_path, "w") as f:
        json.dump(bridge_data, f, indent=2)
    print(f"\nBridge-format JSON written to: {out_path}")
    print(f"  Tasks:        {len(bridge_data['tasks'])}")
    print(f"  Projects:     {len(bridge_data['projects'])}")
    print(f"  Tags:         {len(bridge_data['tags'])}")
    print(f"  Folders:      {len(bridge_data['folders'])}")
    print(f"  Perspectives: {len(bridge_data['perspectives'])}")


if __name__ == "__main__":
    main()
