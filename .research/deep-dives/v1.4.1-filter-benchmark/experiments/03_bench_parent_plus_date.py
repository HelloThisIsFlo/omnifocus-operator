"""Benchmark 03 — parent subtree + due-date bound filter."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _harness import bench, print_header, print_timing_table
from corpus import build_corpus
from python_parent_filter import (
    load_snapshot,
)
from python_parent_filter import (
    parent_plus_date as py_parent_plus_date,
)
from sql_parent_filter import parent_plus_date as sql_parent_plus_date

SCALES = [1_000, 5_000, 10_000, 25_000]


def main() -> None:
    print_header("BENCH 03 — parent subtree + due-date bound filter (SQL vs Python)")

    rows: list[tuple[str, object]] = []

    for scale in SCALES:
        conn, stats = build_corpus(scale)
        parent_id = stats.target_parent_id
        subtree_size = stats.target_subtree_size

        # Pick a date bound that splits the corpus roughly in half — realistic
        # for "due in the next N days" style queries.
        due_bound_row = conn.execute(
            "SELECT effectiveDateDue AS d FROM Task WHERE effectiveDateDue IS NOT NULL "
            "ORDER BY effectiveDateDue LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM Task "
            "WHERE effectiveDateDue IS NOT NULL)"
        ).fetchone()
        due_bound = due_bound_row["d"] if due_bound_row else 0.0

        scale_tag = (
            f"{scale:>5}T  subtree={subtree_size:<4}"
            f"  depth={stats.max_depth}  due_bound_cf={due_bound:.0f}"
        )
        print(f"\n--- corpus: {scale_tag} ---")

        sql_t = bench(
            f"[{scale:>5}T] SQL: CTE + date clause",
            lambda: sql_parent_plus_date(conn, parent_id, due_bound),
        )
        rows.append((sql_t.label, sql_t))

        snapshot = load_snapshot(conn)

        def _warm() -> list:
            return py_parent_plus_date(snapshot, parent_id, due_bound)

        py_warm = bench(f"[{scale:>5}T] Python warm: filter only", _warm)
        rows.append((py_warm.label, py_warm))

        def _cold() -> list:
            s = load_snapshot(conn)
            return py_parent_plus_date(s, parent_id, due_bound)

        py_cold = bench(f"[{scale:>5}T] Python cold: load+filter", _cold)
        rows.append((py_cold.label, py_cold))

        conn.close()

    print_timing_table(rows)


if __name__ == "__main__":
    main()
