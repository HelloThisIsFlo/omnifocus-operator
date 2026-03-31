#!/usr/bin/env python3
"""
Inbox task ordering: extend the recursive CTE to cover inbox trees.

The project-anchored CTE misses inbox tasks because they have no ProjectInfo
row. This script tests whether we can extend the CTE anchor to include inbox
roots (parent IS NULL, no containingProjectInfo, not a project).

Key questions:
  1. Does the extended CTE produce correct depth-first order for inbox trees?
  2. Where should inbox tasks sort relative to project tasks?
  3. Does the recursive step handle inbox children the same as project children?

Usage:
    python3 inbox_ordering.py

All access is read-only (?mode=ro). No mutations.

Compare the output against your OmniFocus inbox UI to verify ordering.
"""

from __future__ import annotations

import os
import sqlite3

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)


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

    # ══════════════════════════════════════════════════════════════════
    #  1. Inbox-only CTE: depth-first traversal
    # ══════════════════════════════════════════════════════════════════

    section("1. Inbox CTE: depth-first traversal by rank")

    # Inbox roots: parent IS NULL, no ProjectInfo, no containingProjectInfo
    inbox_cte_sql = """
    WITH RECURSIVE inbox_order(id, sort_path, depth) AS (
        -- Anchor: inbox root tasks
        SELECT t.persistentIdentifier,
               printf('%010d', t.rank + 2147483648),
               0
        FROM Task t
        LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
        WHERE t.parent IS NULL
          AND t.containingProjectInfo IS NULL
          AND pi.task IS NULL
          AND t.dateCompleted IS NULL

        UNION ALL

        -- Recursive: children
        SELECT t.persistentIdentifier,
               o.sort_path || '/' || printf('%010d', t.rank + 2147483648),
               o.depth + 1
        FROM Task t
        JOIN inbox_order o ON t.parent = o.id
    )
    SELECT t.persistentIdentifier, t.name, t.rank, t.parent,
           o.sort_path, o.depth
    FROM Task t
    JOIN inbox_order o ON t.persistentIdentifier = o.id
    ORDER BY o.sort_path
    """

    rows = conn.execute(inbox_cte_sql).fetchall()

    print(f"Total inbox tasks (including nested): {len(rows)}")
    print(f"\nDepth-first order (compare against OmniFocus inbox UI):\n")
    print(f"{'#':>3} {'depth':>5} {'name':<60} sort_path")
    print("-" * 120)
    for i, r in enumerate(rows, 1):
        indent = "  " * r["depth"]
        name = r["name"] or "[unnamed]"
        # Truncate long names
        display = f"{indent}{name}"
        if len(display) > 58:
            display = display[:55] + "..."
        print(f"{i:>3} {r['depth']:>5} {display:<60} {r['sort_path']}")

    # ══════════════════════════════════════════════════════════════════
    #  2. Combined CTE: projects + inbox
    # ══════════════════════════════════════════════════════════════════

    section("2. Combined CTE: projects + inbox (Strategy B)")

    # Strategy B: inbox gets a ZZZZZZZZZZ prefix so it sorts AFTER projects
    combined_cte_sql = """
    WITH RECURSIVE task_order(id, sort_path) AS (
        -- Anchor A: project-root tasks
        SELECT t.persistentIdentifier,
               printf('%010d', t.rank + 2147483648)
        FROM Task t
        JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task

        UNION ALL

        -- Anchor B: inbox root tasks (prefixed to sort after projects)
        SELECT t.persistentIdentifier,
               'ZZZZZZZZZZ/' || printf('%010d', t.rank + 2147483648)
        FROM Task t
        LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
        WHERE t.parent IS NULL
          AND t.containingProjectInfo IS NULL
          AND pi.task IS NULL

        UNION ALL

        -- Recursive: all children (works for both project and inbox trees)
        SELECT t.persistentIdentifier,
               o.sort_path || '/' || printf('%010d', t.rank + 2147483648)
        FROM Task t
        JOIN task_order o ON t.parent = o.id
    )
    SELECT t.persistentIdentifier, t.name,
           o.sort_path,
           CASE WHEN o.sort_path LIKE 'ZZZZ%' THEN 'INBOX' ELSE 'PROJECT' END as source
    FROM Task t
    JOIN task_order o ON t.persistentIdentifier = o.id
    LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
    WHERE pi.task IS NULL  -- exclude project-root tasks themselves
      AND t.dateCompleted IS NULL
    ORDER BY o.sort_path
    """

    rows = conn.execute(combined_cte_sql).fetchall()

    project_count = sum(1 for r in rows if r["source"] == "PROJECT")
    inbox_count = sum(1 for r in rows if r["source"] == "INBOX")
    print(f"Combined result: {len(rows)} tasks ({project_count} project, {inbox_count} inbox)")

    # Show the boundary where projects end and inbox begins
    print(f"\n--- Last 3 project tasks ---")
    project_rows = [r for r in rows if r["source"] == "PROJECT"]
    for r in project_rows[-3:]:
        print(f"  [PROJECT] {r['name'] or '[unnamed]'}")

    print(f"\n--- First 5 inbox tasks ---")
    inbox_rows = [r for r in rows if r["source"] == "INBOX"]
    for r in inbox_rows[:5]:
        print(f"  [INBOX]   {r['name'] or '[unnamed]'}")

    # ══════════════════════════════════════════════════════════════════
    #  3. Verify: inbox CTE covers all inbox tasks
    # ══════════════════════════════════════════════════════════════════

    section("3. Coverage check: does the CTE reach all inbox tasks?")

    # Count inbox tasks the old way
    old_count = conn.execute("""
        SELECT COUNT(*)
        FROM Task t
        LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
        WHERE t.containingProjectInfo IS NULL
          AND pi.task IS NULL
          AND t.dateCompleted IS NULL
    """).fetchone()[0]

    # Count via CTE
    cte_count = conn.execute(f"""
    WITH RECURSIVE inbox_order(id, sort_path) AS (
        SELECT t.persistentIdentifier,
               printf('%010d', t.rank + 2147483648)
        FROM Task t
        LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
        WHERE t.parent IS NULL
          AND t.containingProjectInfo IS NULL
          AND pi.task IS NULL
          AND t.dateCompleted IS NULL

        UNION ALL

        SELECT t.persistentIdentifier,
               o.sort_path || '/' || printf('%010d', t.rank + 2147483648)
        FROM Task t
        JOIN inbox_order o ON t.parent = o.id
    )
    SELECT COUNT(*) FROM inbox_order
    """).fetchone()[0]

    print(f"Inbox tasks (direct query): {old_count}")
    print(f"Inbox tasks (CTE):          {cte_count}")
    match = old_count == cte_count
    print(f"Coverage:                    {'PASS' if match else 'FAIL'}")

    if not match:
        # Find the missing ones
        missing = conn.execute(f"""
        WITH RECURSIVE inbox_order(id, sort_path) AS (
            SELECT t.persistentIdentifier,
                   printf('%010d', t.rank + 2147483648)
            FROM Task t
            LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
            WHERE t.parent IS NULL
              AND t.containingProjectInfo IS NULL
              AND pi.task IS NULL
              AND t.dateCompleted IS NULL

            UNION ALL

            SELECT t.persistentIdentifier,
                   o.sort_path || '/' || printf('%010d', t.rank + 2147483648)
            FROM Task t
            JOIN inbox_order o ON t.parent = o.id
        )
        SELECT t.persistentIdentifier, t.name, t.parent
        FROM Task t
        LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
        LEFT JOIN inbox_order o ON t.persistentIdentifier = o.id
        WHERE t.containingProjectInfo IS NULL
          AND pi.task IS NULL
          AND t.dateCompleted IS NULL
          AND o.id IS NULL
        """).fetchall()
        print(f"\nMissing tasks ({len(missing)}):")
        for m in missing:
            print(f"  {m['name'] or '[unnamed]'} (parent={m['parent']})")

    # ══════════════════════════════════════════════════════════════════
    #  4. Performance
    # ══════════════════════════════════════════════════════════════════

    section("4. Performance: inbox CTE vs combined CTE")

    import time

    # Inbox-only CTE
    times = []
    for _ in range(10):
        start = time.perf_counter()
        conn.execute(inbox_cte_sql).fetchall()
        times.append((time.perf_counter() - start) * 1000)
    print(f"Inbox-only CTE:  avg={sum(times)/len(times):.1f}ms "
          f"min={min(times):.1f}ms max={max(times):.1f}ms")

    # Combined CTE
    times = []
    for _ in range(10):
        start = time.perf_counter()
        conn.execute(combined_cte_sql).fetchall()
        times.append((time.perf_counter() - start) * 1000)
    print(f"Combined CTE:    avg={sum(times)/len(times):.1f}ms "
          f"min={min(times):.1f}ms max={max(times):.1f}ms")

    conn.close()
    print("\n✅ Inbox ordering analysis complete. All queries read-only.")


if __name__ == "__main__":
    main()
