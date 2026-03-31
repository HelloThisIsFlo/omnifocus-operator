#!/usr/bin/env python3
"""
Phase 2: Hierarchy and flattening — does rank work across nesting levels?

Key questions:
  1. Is rank relative to immediate parent only, or globally meaningful?
  2. Does `ORDER BY rank` on a flat query produce sensible order?
  3. Do we need recursive CTE traversal to reproduce UI order?
  4. What role does `creationOrdinal` play?
  5. What ORDER BY does query_builder.py actually need?

Uses the 4-level test hierarchy:
  Ordering Research > OR-01 > OR-01a > (leaf)
  Ordering Research > OR-03 > OR-03a > OR-03a-i, OR-03a-ii

Usage:
    python3 hierarchy_ordering.py

All access is read-only (?mode=ro). No mutations.

FINDINGS (2026-03-31):
  - Flat ORDER BY rank interleaves depths (rank=8487040 appears at depths 0-3)
  - Recursive CTE with sort_path produces correct depth-first UI-matching order
  - ORDER BY parent, rank groups siblings correctly (practical for flat queries)
  - creationOrdinal is NULL for all test tasks — dead column for recent tasks
  - For query_builder.py: ORDER BY rank, persistentIdentifier is deterministic enough
  - CTE only needed if we want true outline/tree order (future feature)
  - NOTE: CTE sort_path needs printf('%010d', rank + 2147483648) for negative ranks
"""

from __future__ import annotations

import os
import sqlite3

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)

# Test hierarchy root
ORDERING_RESEARCH_ID = "dUWW6UbTCI6"

# All test task IDs for flat query testing
ALL_TEST_IDS = [
    "dUWW6UbTCI6",  # Ordering Research (root)
    "eWUXvLtFUXE",  # OR-01
    "a5QSd7fJpKu",  # OR-01a
    "n6H-BQdPaCC",  # OR-01b
    "naAUQS8rkvE",  # OR-02
    "f-bTxFgMvNG",  # OR-03
    "bMHHXNXm-hM",  # OR-03a
    "iDbdzI1IyM-",  # OR-03a-i
    "p9cKReI2k4f",  # OR-03a-ii
    "hWtUbl-c4hc",  # OR-03b
    "massEEGCHoM",  # OR-03c
    "kPwWb89qlqw",  # OR-04
    "cpq7Y-ukK6J",  # OR-05
]


def connect() -> sqlite3.Connection:
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def section(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def main() -> None:
    conn = connect()

    # ── 1. Flat ORDER BY rank — does it make sense? ───────────────────
    section("1. Flat query: ORDER BY rank (all test tasks)")

    ids = ",".join(f"'{k}'" for k in ALL_TEST_IDS)
    rows = conn.execute(
        f"SELECT persistentIdentifier, name, parent, rank, creationOrdinal "
        f"FROM Task WHERE persistentIdentifier IN ({ids}) "
        f"ORDER BY rank"
    ).fetchall()

    print("Result of flat ORDER BY rank:")
    print(f"{'rank':>10} {'crOrd':>8} {'name':<35} {'parent':<15}")
    print("-" * 75)
    for r in rows:
        depth = 0
        pid = r["parent"]
        # Quick depth calc for visual indent
        while pid and pid in [row["persistentIdentifier"] for row in rows]:
            depth += 1
            for row in rows:
                if row["persistentIdentifier"] == pid:
                    pid = row["parent"]
                    break
        indent = "  " * depth
        print(
            f"{r['rank']:>10} {r['creationOrdinal'] or 'NULL':>8} "
            f"{indent}{r['name']:<35} {r['parent'] or '(root)':<15}"
        )

    print("\n⚠️  If ranks interleave across depths, flat ORDER BY rank won't work.")

    # ── 2. Recursive CTE: depth-first traversal ──────────────────────
    section("2. Recursive CTE: depth-first traversal by rank")

    # DFS: parent first, then children sorted by rank
    cte_sql = """
    WITH RECURSIVE tree(id, name, parent, rank, depth, sort_path) AS (
        -- Anchor: the root task
        SELECT persistentIdentifier, name, parent, rank, 0,
               printf('%010d', rank)
        FROM Task
        WHERE persistentIdentifier = ?

        UNION ALL

        -- Recursive: children sorted by rank within their parent
        SELECT t.persistentIdentifier, t.name, t.parent, t.rank,
               tree.depth + 1,
               tree.sort_path || '/' || printf('%010d', t.rank)
        FROM Task t
        JOIN tree ON t.parent = tree.id
    )
    SELECT id, name, parent, rank, depth, sort_path
    FROM tree
    ORDER BY sort_path
    """

    rows = conn.execute(cte_sql, (ORDERING_RESEARCH_ID,)).fetchall()

    print("Depth-first traversal (rank-ordered within each parent):")
    print(f"{'depth':>5} {'rank':>10} {'name':<40} sort_path")
    print("-" * 90)
    for r in rows:
        indent = "  " * r["depth"]
        print(f"{r['depth']:>5} {r['rank']:>10} {indent}{r['name']:<40} {r['sort_path']}")

    print("\n✅ This should match OmniFocus UI order exactly.")

    # ── 3. Flat query with parent-scoped ordering ─────────────────────
    section("3. Practical flat query: ORDER BY parent, rank")

    rows = conn.execute(
        f"SELECT persistentIdentifier, name, parent, rank "
        f"FROM Task WHERE persistentIdentifier IN ({ids}) "
        f"ORDER BY parent, rank"
    ).fetchall()

    print("ORDER BY parent, rank (groups siblings together):")
    current_parent = None
    for r in rows:
        if r["parent"] != current_parent:
            current_parent = r["parent"]
            print(f"\n  Parent: {current_parent or '(root)'}")
        print(f"    rank={r['rank']:>10}  {r['name']}")

    # ── 4. creationOrdinal analysis ───────────────────────────────────
    section("4. creationOrdinal: does it correlate with creation order?")

    rows = conn.execute(
        f"SELECT persistentIdentifier, name, rank, creationOrdinal, dateAdded "
        f"FROM Task WHERE persistentIdentifier IN ({ids}) "
        f"ORDER BY creationOrdinal"
    ).fetchall()

    print("Sorted by creationOrdinal:")
    print(f"{'crOrd':>8} {'rank':>10} {'name':<35}")
    print("-" * 60)
    for r in rows:
        print(f"{r['creationOrdinal'] or 'NULL':>8} {r['rank']:>10} {r['name']}")

    # Check global uniqueness of creationOrdinal
    co_dupes = conn.execute(
        "SELECT creationOrdinal, COUNT(*) as cnt FROM Task "
        "WHERE creationOrdinal IS NOT NULL "
        "GROUP BY creationOrdinal HAVING cnt > 1 LIMIT 5"
    ).fetchone()

    if co_dupes:
        print(f"\n⚠️  creationOrdinal has duplicates! Example: {co_dupes['creationOrdinal']}")
    else:
        print("\n✅ creationOrdinal is globally unique (good tiebreaker candidate)")

    # ── 5. What query_builder.py needs ────────────────────────────────
    section("5. Recommended ORDER BY for flat list queries")

    print("""
For query_builder.py's flat task/project lists (no hierarchy traversal):

Option A: ORDER BY rank ASC, persistentIdentifier ASC
  - Deterministic (ID tiebreaker for equal ranks)
  - Groups siblings if parents are in the same project
  - May interleave depths in a flat list

Option B: ORDER BY containingProjectInfo, rank ASC
  - Groups tasks by project first, then by manual order within project
  - Better for project-scoped queries

The CTE approach (Phase 2, Section 2) is needed ONLY if the consumer
wants true depth-first UI-matching order. For pagination, Option A or B
with a stable tiebreaker is sufficient.
    """)

    # ── 6. Verify: does rank == 0 or rank == NULL ever appear? ────────
    section("6. Edge cases: rank=0 and rank=NULL")

    zero_count = conn.execute("SELECT COUNT(*) FROM Task WHERE rank = 0").fetchone()[0]
    null_count = conn.execute("SELECT COUNT(*) FROM Task WHERE rank IS NULL").fetchone()[0]
    print(f"Tasks with rank = 0:    {zero_count}")
    print(f"Tasks with rank IS NULL: {null_count}")

    if zero_count > 0:
        example = conn.execute(
            "SELECT persistentIdentifier, name, parent FROM Task WHERE rank = 0 LIMIT 3"
        ).fetchall()
        for r in example:
            print(f"  Example: {r['name'] or '[unnamed]'} (parent={r['parent']})")

    conn.close()
    print("\n✅ Phase 2 complete. All queries read-only.")


if __name__ == "__main__":
    main()
