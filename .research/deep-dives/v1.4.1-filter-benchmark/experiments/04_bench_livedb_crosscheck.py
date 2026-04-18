"""Benchmark 04 — cross-check against the live OmniFocus SQLite cache.

Read-only pass that runs the same filter shapes (parent-only, parent+tag,
parent+date) against Flo's real DB. Purpose: validate that the synthetic
corpus's results are representative of real-data performance. The real
DB has ~3K tasks (smaller than the 10K synthetic scale), so this isn't a
stress test — it's a shape check.

Strictly read-only via ?mode=ro. No OmniJS, no bridge, no mutation.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _harness import bench, print_header, print_timing_table
from python_parent_filter import (
    load_snapshot,
    load_task_tag_edges,
)
from python_parent_filter import (
    parent_only as py_parent_only,
)
from python_parent_filter import (
    parent_plus_date as py_parent_plus_date,
)
from python_parent_filter import (
    parent_plus_tag as py_parent_plus_tag,
)
from sql_parent_filter import (
    parent_only as sql_parent_only,
)
from sql_parent_filter import (
    parent_plus_date as sql_parent_plus_date,
)
from sql_parent_filter import (
    parent_plus_tag as sql_parent_plus_tag,
)

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)


def pick_target_parent(conn: sqlite3.Connection) -> tuple[str, int]:
    """Pick a live parent task with a non-trivial subtree."""
    # Find tasks that are parents of other tasks, ordered by descendant count
    candidates = conn.execute(
        """
        WITH RECURSIVE descendants(root_id, id) AS (
            SELECT persistentIdentifier, persistentIdentifier FROM Task
            UNION ALL
            SELECT d.root_id, t.persistentIdentifier FROM Task t
            JOIN descendants d ON t.parent = d.id
        )
        SELECT root_id, COUNT(*) - 1 AS subtree_size
        FROM descendants
        GROUP BY root_id
        HAVING subtree_size >= 5
        ORDER BY subtree_size DESC
        LIMIT 5
        """
    ).fetchall()
    if not candidates:
        raise RuntimeError("No parent tasks with subtree ≥ 5 found in live DB")
    # Use the median candidate (not the largest — that's often a project root)
    return candidates[len(candidates) // 2]["root_id"], candidates[len(candidates) // 2][
        "subtree_size"
    ]


def pick_tag_id(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT tag FROM TaskToTag GROUP BY tag ORDER BY COUNT(*) DESC LIMIT 1"
    ).fetchone()
    return row["tag"] if row else None


def pick_date_bound(conn: sqlite3.Connection) -> float:
    """Median effectiveDateDue as CF-epoch float — splits corpus ~50/50."""
    row = conn.execute(
        "SELECT effectiveDateDue FROM Task "
        "WHERE effectiveDateDue IS NOT NULL "
        "ORDER BY effectiveDateDue "
        "LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM Task WHERE effectiveDateDue IS NOT NULL)"
    ).fetchone()
    if row is None:
        return 0.0
    val = row[0]
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return 0.0
    return float(val)


def main() -> None:
    if not os.path.exists(DB_PATH):
        print(f"ABORT: OmniFocus SQLite cache not found at {DB_PATH}")
        sys.exit(1)

    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    try:
        print_header("BENCH 04 — live OmniFocus SQLite cache cross-check")

        total_tasks = conn.execute("SELECT COUNT(*) AS n FROM Task").fetchone()["n"]
        parent_id, subtree_size = pick_target_parent(conn)
        tag_id = pick_tag_id(conn)
        due_bound = pick_date_bound(conn)

        print(
            f"\nLive DB: {total_tasks} total Task rows (includes both pure tasks and project rows)"
        )
        print(f"  target_parent_id  = {parent_id}  (subtree_size={subtree_size})")
        print(f"  target_tag_id     = {tag_id}")
        print(f"  due_bound_cf      = {due_bound:.0f}")

        rows: list[tuple[str, object]] = []

        # --- Parent only ---
        sql_t = bench(
            "LIVE SQL: parent only",
            lambda: sql_parent_only(conn, parent_id),
        )
        rows.append((sql_t.label, sql_t))

        snapshot = load_snapshot(conn)
        edges = load_task_tag_edges(conn)

        def _warm_only() -> list:
            return py_parent_only(snapshot, parent_id)

        py_w = bench("LIVE Python warm: parent only", _warm_only)
        rows.append((py_w.label, py_w))

        def _cold_only() -> list:
            s = load_snapshot(conn)
            return py_parent_only(s, parent_id)

        py_c = bench("LIVE Python cold: parent only (load+filter)", _cold_only)
        rows.append((py_c.label, py_c))

        # --- Parent + tag ---
        if tag_id:
            sql_t = bench(
                "LIVE SQL: parent + tag",
                lambda: sql_parent_plus_tag(conn, parent_id, tag_id),
            )
            rows.append((sql_t.label, sql_t))

            def _warm_pt() -> list:
                return py_parent_plus_tag(snapshot, parent_id, tag_id, edges)

            py_w = bench("LIVE Python warm: parent + tag", _warm_pt)
            rows.append((py_w.label, py_w))

            def _cold_pt() -> list:
                s = load_snapshot(conn)
                e = load_task_tag_edges(conn)
                return py_parent_plus_tag(s, parent_id, tag_id, e)

            py_c = bench("LIVE Python cold: parent + tag (load+filter)", _cold_pt)
            rows.append((py_c.label, py_c))

        # --- Parent + date ---
        sql_t = bench(
            "LIVE SQL: parent + date",
            lambda: sql_parent_plus_date(conn, parent_id, due_bound),
        )
        rows.append((sql_t.label, sql_t))

        def _warm_pd() -> list:
            return py_parent_plus_date(snapshot, parent_id, due_bound)

        py_w = bench("LIVE Python warm: parent + date", _warm_pd)
        rows.append((py_w.label, py_w))

        def _cold_pd() -> list:
            s = load_snapshot(conn)
            return py_parent_plus_date(s, parent_id, due_bound)

        py_c = bench("LIVE Python cold: parent + date (load+filter)", _cold_pd)
        rows.append((py_c.label, py_c))

        print_timing_table(rows)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
