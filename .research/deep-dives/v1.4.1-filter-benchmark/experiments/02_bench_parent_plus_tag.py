"""Benchmark 02 — parent subtree + tag filter (realistic combo)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _harness import bench, print_header, print_timing_table
from corpus import build_corpus
from python_parent_filter import (
    load_snapshot,
    load_task_tag_edges,
)
from python_parent_filter import (
    parent_plus_tag as py_parent_plus_tag,
)
from sql_parent_filter import parent_plus_tag as sql_parent_plus_tag

SCALES = [1_000, 5_000, 10_000, 25_000]


def main() -> None:
    print_header("BENCH 02 — parent subtree + tag filter (SQL vs Python)")

    rows: list[tuple[str, object]] = []

    for scale in SCALES:
        conn, stats = build_corpus(scale)
        parent_id = stats.target_parent_id
        subtree_size = stats.target_subtree_size

        # Pick a tag that is actually used (sample one from TaskToTag)
        tag_id_row = conn.execute(
            "SELECT tag FROM TaskToTag GROUP BY tag ORDER BY COUNT(*) DESC LIMIT 1"
        ).fetchone()
        tag_id = tag_id_row["tag"]

        scale_tag = (
            f"{scale:>5}T  subtree={subtree_size:<4}"
            f"  depth={stats.max_depth}  tags={stats.task_tag_edges}"
        )
        print(f"\n--- corpus: {scale_tag} ---")

        sql_t = bench(
            f"[{scale:>5}T] SQL: CTE + tag-IN",
            lambda: sql_parent_plus_tag(conn, parent_id, tag_id),
        )
        rows.append((sql_t.label, sql_t))

        snapshot = load_snapshot(conn)
        edges = load_task_tag_edges(conn)

        def _warm() -> list:
            return py_parent_plus_tag(snapshot, parent_id, tag_id, edges)

        py_warm = bench(f"[{scale:>5}T] Python warm: filter only", _warm)
        rows.append((py_warm.label, py_warm))

        def _cold() -> list:
            s = load_snapshot(conn)
            e = load_task_tag_edges(conn)
            return py_parent_plus_tag(s, parent_id, tag_id, e)

        py_cold = bench(f"[{scale:>5}T] Python cold: load+filter", _cold)
        rows.append((py_cold.label, py_cold))

        conn.close()

    print_timing_table(rows)


if __name__ == "__main__":
    main()
