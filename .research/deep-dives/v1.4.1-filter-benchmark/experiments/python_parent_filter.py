"""Python prototype for the parent-subtree filter.

Mirrors the shape of ``BridgeOnlyRepository.list_tasks`` — assumes a
pre-loaded snapshot (dict list), builds a parent→children map, traverses
from target parent, then applies downstream filters via list comprehensions.

``load_snapshot`` captures the "cold" cost of loading from SQLite into
Python objects — benchmarked separately so we can see both warm (filter
only) and cold (load + filter) paths. In production, BridgeOnlyRepository
caches snapshots across calls, so the warm path is the dominant case.

For a minimal-overhead comparison, we use dicts rather than Pydantic Task
instances. Validation cost is out of scope for this architectural
question — we measure the *filter algorithm*, not pydantic parsing.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from collections.abc import Iterable
from typing import Any


def load_snapshot(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Load all tasks (as dicts) — analogous to BridgeOnlyRepository.get_all."""
    return [dict(r) for r in conn.execute("SELECT * FROM Task")]


def build_children_map(tasks: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Build parent→children map in one pass. O(n)."""
    children: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t in tasks:
        p = t.get("parent")
        if p is not None:
            children[p].append(t)
    return children


def collect_subtree(
    parent_id: str,
    by_id: dict[str, dict[str, Any]],
    children_map: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Collect parent + all descendants via iterative DFS. O(subtree_size)."""
    result: list[dict[str, Any]] = []
    parent = by_id.get(parent_id)
    if parent is not None:
        result.append(parent)
    stack = [parent_id]
    while stack:
        current = stack.pop()
        for child in children_map.get(current, ()):
            result.append(child)
            stack.append(child["persistentIdentifier"])
    return result


def parent_only(
    snapshot: list[dict[str, Any]],
    parent_id: str,
) -> list[dict[str, Any]]:
    by_id = {t["persistentIdentifier"]: t for t in snapshot}
    children_map = build_children_map(snapshot)
    return collect_subtree(parent_id, by_id, children_map)


def parent_plus_tag(
    snapshot: list[dict[str, Any]],
    parent_id: str,
    tag_id: str,
    task_tag_edges: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    by_id = {t["persistentIdentifier"]: t for t in snapshot}
    children_map = build_children_map(snapshot)
    subtree = collect_subtree(parent_id, by_id, children_map)
    tagged_tasks = {task for task, tag in task_tag_edges if tag == tag_id}
    return [t for t in subtree if t["persistentIdentifier"] in tagged_tasks]


def parent_plus_date(
    snapshot: list[dict[str, Any]],
    parent_id: str,
    due_after_cf: float,
) -> list[dict[str, Any]]:
    by_id = {t["persistentIdentifier"]: t for t in snapshot}
    children_map = build_children_map(snapshot)
    subtree = collect_subtree(parent_id, by_id, children_map)
    return [
        t
        for t in subtree
        if t["effectiveDateDue"] is not None and t["effectiveDateDue"] >= due_after_cf
    ]


def load_task_tag_edges(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    return [(r["task"], r["tag"]) for r in conn.execute("SELECT task, tag FROM TaskToTag")]
