#!/usr/bin/env python3
"""
Validate CTE ordering after manual drag-and-drop reordering.

This is a SEMI-INTERACTIVE experiment. It requires human intervention in
OmniFocus between two runs. The script has two modes:

  1. BEFORE mode (default): Creates test tasks via SQL dump, shows current
     CTE order, and prints instructions for the human to reorder in OmniFocus.

  2. AFTER mode (--after): Re-runs the CTE and checks whether the output
     matches the expected hierarchy after reordering.

Usage:
    # Step 1: Create tasks via MCP (see instructions below), then run:
    python3 reorder_validation.py --project <PROJECT_ID>

    # Step 2: Manually reorder tasks in OmniFocus as instructed

    # Step 3: Verify the CTE picks up the new order:
    python3 reorder_validation.py --project <PROJECT_ID> --after

All DB access is read-only (?mode=ro). Task creation is done via MCP, not
this script.

SETUP (via MCP add_tasks, all as flat children of the target project):
  Create these 6 tasks IN THIS ORDER (deliberately scrambled):
    1. "REORDER-2.1.1 (should be nested under 2.1)"
    2. "REORDER-1.2 (should be 2nd child of 1)"
    3. "REORDER-2 (should be 2nd top-level)"
    4. "REORDER-1.1 (should be 1st child of 1)"
    5. "REORDER-2.1 (should be child of 2)"
    6. "REORDER-1 (should be 1st top-level)"

  Target hierarchy after manual reorder:
    Project
    ├── REORDER-1
    │   ├── REORDER-1.1
    │   └── REORDER-1.2
    └── REORDER-2
        └── REORDER-2.1
            └── REORDER-2.1.1

FINDINGS (2026-03-31, project bW2BCrF4TAz):
  - BEFORE: All 6 tasks flat at depth 1, creation-order ranks (65536 gaps)
  - AFTER: CTE produces exact target hierarchy. Observations:
    - REORDER-1 got rank -1,069,498,304 (moved before REORDER-2)
    - REORDER-1.1 got rank -1,073,741,824 (negative, first child)
    - Several children got rank=0 (first child under new parent)
    - The +2147483648 shift handles all negative ranks correctly
  - VERDICT: CTE correctly tracks drag-and-drop reordering, re-parenting,
    and nesting changes. Negative ranks from reorganization are handled.
"""

from __future__ import annotations

import argparse
import os
import sqlite3

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)

CTE_SQL = """
WITH RECURSIVE task_order(id, sort_path, depth) AS (
    SELECT t.persistentIdentifier,
           printf('%010d', t.rank + 2147483648),
           0
    FROM Task t
    JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
    WHERE t.persistentIdentifier = ?

    UNION ALL

    SELECT t.persistentIdentifier,
           o.sort_path || '/' || printf('%010d', t.rank + 2147483648),
           o.depth + 1
    FROM Task t
    JOIN task_order o ON t.parent = o.id
)
SELECT t.persistentIdentifier as id, t.name, t.rank, t.parent,
       o.sort_path, o.depth
FROM Task t
JOIN task_order o ON t.persistentIdentifier = o.id
LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
WHERE pi.task IS NULL
  AND t.dateCompleted IS NULL
ORDER BY o.sort_path
"""


def connect() -> sqlite3.Connection:
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def dump_cte(conn: sqlite3.Connection, project_id: str) -> list[sqlite3.Row]:
    rows = conn.execute(CTE_SQL, (project_id,)).fetchall()
    for i, r in enumerate(rows, 1):
        indent = "  " * r["depth"]
        print(f"  {i:>2}. {indent}{r['name']}")
        print(f"      id={r['id']} rank={r['rank']} "
              f"parent={r['parent']} depth={r['depth']}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate CTE ordering after manual drag-and-drop"
    )
    parser.add_argument(
        "--project", required=True,
        help="Project ID to query (e.g. bW2BCrF4TAz)"
    )
    parser.add_argument(
        "--after", action="store_true",
        help="Run in AFTER mode (verify reordering)"
    )
    args = parser.parse_args()

    conn = connect()

    if not args.after:
        # ── BEFORE mode ─────────────────────────────────────────────
        print("=" * 70)
        print("  BEFORE reorder: current CTE output")
        print("=" * 70)
        print()

        rows = dump_cte(conn, args.project)

        print()
        print("=" * 70)
        print("  INSTRUCTIONS")
        print("=" * 70)
        print()
        print("  In OmniFocus, manually drag-and-drop the REORDER-* tasks")
        print("  into this target hierarchy:")
        print()
        print("    Project")
        print("    ├── REORDER-1")
        print("    │   ├── REORDER-1.1")
        print("    │   └── REORDER-1.2")
        print("    └── REORDER-2")
        print("        └── REORDER-2.1")
        print("            └── REORDER-2.1.1")
        print()
        print("  Then re-run with --after to verify:")
        print(f"    python3 {__file__} --project {args.project} --after")

    else:
        # ── AFTER mode ──────────────────────────────────────────────
        print("=" * 70)
        print("  AFTER reorder: verifying CTE output")
        print("=" * 70)
        print()

        rows = dump_cte(conn, args.project)

        # Validate expected structure
        print()
        print("=" * 70)
        print("  VALIDATION")
        print("=" * 70)
        print()

        reorder_tasks = [r for r in rows if "REORDER-" in (r["name"] or "")]
        if not reorder_tasks:
            print("  No REORDER-* tasks found. Did you create them?")
            conn.close()
            return

        # Build expected order and nesting
        expected = [
            ("REORDER-1", 1),
            ("REORDER-1.1", 2),
            ("REORDER-1.2", 2),
            ("REORDER-2", 1),
            ("REORDER-2.1", 2),
            ("REORDER-2.1.1", 3),
        ]

        all_pass = True
        for i, (exp_prefix, exp_depth) in enumerate(expected):
            if i >= len(reorder_tasks):
                print(f"  FAIL: Expected {exp_prefix} at position {i+1}, "
                      f"but only {len(reorder_tasks)} tasks found")
                all_pass = False
                continue

            actual = reorder_tasks[i]
            name_match = actual["name"].startswith(exp_prefix)
            depth_match = actual["depth"] == exp_depth

            status = "PASS" if (name_match and depth_match) else "FAIL"
            if not (name_match and depth_match):
                all_pass = False

            print(f"  {status}: Position {i+1}: "
                  f"expected '{exp_prefix}' at depth {exp_depth}, "
                  f"got '{actual['name'][:30]}' at depth {actual['depth']}")

        # Check for negative ranks (expected after reordering)
        neg_ranks = [r for r in reorder_tasks if r["rank"] < 0]
        if neg_ranks:
            print(f"\n  Negative ranks found: {len(neg_ranks)} "
                  f"(expected after drag-and-drop)")
            for r in neg_ranks:
                print(f"    {r['name'][:40]}: rank={r['rank']}")

        # Check parent changes (tasks should have different parents now)
        unique_parents = set(r["parent"] for r in reorder_tasks)
        print(f"\n  Unique parents: {len(unique_parents)} "
              f"(should be >1 if nesting worked)")

        print()
        if all_pass:
            print("  ✅ ALL CHECKS PASSED — CTE correctly tracks "
                  "drag-and-drop reordering")
        else:
            print("  ❌ SOME CHECKS FAILED — see details above")

    conn.close()


if __name__ == "__main__":
    main()
