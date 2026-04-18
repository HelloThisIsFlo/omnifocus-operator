"""Benchmark 01 — pure parent-subtree filter, SQL vs Python.

Scale sweep: 1K / 5K / 10K / 25K tasks. For each scale:
- SQL: recursive CTE + SELECT (measures full query execution)
- Python warm: snapshot already loaded, filter only
- Python cold: load snapshot from SQLite + build maps + filter

The warm Python measurement is the architecturally relevant number: in
production, BridgeOnlyRepository caches the snapshot across calls. The
cold measurement is worst-case/first-call.
"""

from __future__ import annotations

# Make sibling modules importable when run as a script
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _harness import bench, print_header, print_timing_table
from corpus import build_corpus
from python_parent_filter import (
    build_children_map,
    collect_subtree,
    load_snapshot,
)
from python_parent_filter import (
    parent_only as py_parent_only,
)
from sql_parent_filter import parent_only as sql_parent_only

SCALES = [1_000, 5_000, 10_000, 25_000]


def main() -> None:
    print_header("BENCH 01 — parent-subtree filter only (SQL vs Python)")
    print()
    print("Pre-declared thresholds:")
    print("  Python viable (repo-layer unification): p95 at 10K ≤ 100 ms")
    print("  Python too slow (service-layer fallback): p95 > 200 ms at 10K")
    print()

    rows: list[tuple[str, object]] = []

    for scale in SCALES:
        conn, stats = build_corpus(scale)
        parent_id = stats.target_parent_id
        subtree_size = stats.target_subtree_size

        scale_tag = (
            f"{scale:>5}T  subtree={subtree_size:<4}"
            f"  depth={stats.max_depth}  tags={stats.task_tag_edges}"
        )
        print(f"\n--- corpus: {scale_tag} ---")

        # SQL: recursive CTE
        sql_timing = bench(
            f"[{scale:>5}T] SQL: recursive CTE",
            lambda: sql_parent_only(conn, parent_id),
        )
        rows.append((sql_timing.label, sql_timing))

        # Python warm: pre-load snapshot + maps, measure filter only
        snapshot = load_snapshot(conn)

        def _warm() -> list:
            return py_parent_only(snapshot, parent_id)

        py_warm = bench(f"[{scale:>5}T] Python warm: filter only", _warm)
        rows.append((py_warm.label, py_warm))

        # Python even-warmer: pre-build by_id + children_map, measure traversal only
        # This models the BridgeOnlyRepository pattern where the map is pre-built
        # and the service-layer re-runs filters as queries come in. Actually the
        # production BridgeOnly builds the map inside each call, so the "warm"
        # number above is the correct production-cold-filter number. We add this
        # as an extra data point for architectural interpretation.
        by_id = {t["persistentIdentifier"]: t for t in snapshot}
        children_map = build_children_map(snapshot)

        def _traversal_only() -> list:
            return collect_subtree(parent_id, by_id, children_map)

        py_traversal = bench(f"[{scale:>5}T] Python traversal: maps cached", _traversal_only)
        rows.append((py_traversal.label, py_traversal))

        # Python cold: SELECT * + build maps + filter, all in the timed window
        def _cold() -> list:
            s = load_snapshot(conn)
            return py_parent_only(s, parent_id)

        py_cold = bench(f"[{scale:>5}T] Python cold: load+filter", _cold)
        rows.append((py_cold.label, py_cold))

        conn.close()

    print_timing_table(rows)


if __name__ == "__main__":
    main()
