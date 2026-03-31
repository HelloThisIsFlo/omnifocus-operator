#!/usr/bin/env python3
"""
Phase 1: Understand `rank` column semantics empirically.

Queries the real OmniFocus SQLite cache (read-only) for rank values on:
  - Our controlled test tasks (OR-01 through OR-05 and subtasks)
  - A broader sample of existing tasks
  - Statistical characterization: range, gaps, negative values, uniqueness

Usage:
    python3 rank_semantics.py

All access is read-only (?mode=ro). No mutations.

FINDINGS (2026-03-31):
  - rank is unique within each parent (zero within-parent duplicates across 3062 tasks)
  - Globally, rank=0 appears 334 times — but always under different parents
  - Test siblings gap by exactly 65536 (0x10000) — midpoint-insertion scheme
  - Full signed 32-bit range: min=-2,140,575,383 to max=2,147,483,638
  - 935 tasks have negative ranks (normal for reorganized data)
  - creationOrdinal is NULL for all test tasks — not useful
  - Sequential vs parallel projects: same rank mechanism, no difference
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)

# Known test task IDs from the plan
TEST_TASKS = {
    # Project 1: Ordering Research
    "dUWW6UbTCI6": "🔬 Ordering Research (parent)",
    "eWUXvLtFUXE": "OR-01 First Task",
    "a5QSd7fJpKu": "OR-01a Sub First",
    "n6H-BQdPaCC": "OR-01b Sub Second",
    "naAUQS8rkvE": "OR-02 Second Task",
    "f-bTxFgMvNG": "OR-03 Third Task",
    "bMHHXNXm-hM": "OR-03a Subtask Alpha",
    "iDbdzI1IyM-": "OR-03a-i Deep One",
    "p9cKReI2k4f": "OR-03a-ii Deep Two",
    "hWtUbl-c4hc": "OR-03b Subtask Beta",
    "massEEGCHoM": "OR-03c Subtask Gamma",
    "kPwWb89qlqw": "OR-04 Fourth Task",
    "cpq7Y-ukK6J": "OR-05 Fifth Task",
    # Project 2: Ordering Research 2
    "gz41lWsc0cf": "🔬 Ordering Research 2 (parent)",
    "i2bSdT48wms": "OR2-01 Alpha",
    "irzbopJsP4j": "OR2-02 Beta",
    "hs4wm2PM9qM": "OR2-03 Gamma",
}


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

    # ── 1. Test tasks: rank, parent, creationOrdinal ──────────────────
    section("1. Test task rank values (known UI order)")

    ids = ",".join(f"'{k}'" for k in TEST_TASKS)
    rows = conn.execute(
        f"SELECT persistentIdentifier, name, parent, rank, creationOrdinal "
        f"FROM Task WHERE persistentIdentifier IN ({ids}) "
        f"ORDER BY parent, rank"
    ).fetchall()

    print(f"{'ID':<15} {'rank':>8} {'crOrd':>8} {'parent':<15} name")
    print("-" * 80)
    for r in rows:
        pid = r["persistentIdentifier"]
        label = TEST_TASKS.get(pid, r["name"] or "?")
        parent = r["parent"] or "(root)"
        print(f"{pid:<15} {r['rank']:>8} {r['creationOrdinal'] or 'NULL':>8} {parent:<15} {label}")

    # ── 2. Global rank statistics ─────────────────────────────────────
    section("2. Global rank statistics (Task table)")

    stats = conn.execute(
        "SELECT COUNT(*) as cnt, MIN(rank) as min_rank, MAX(rank) as max_rank, "
        "AVG(rank) as avg_rank, COUNT(DISTINCT rank) as distinct_ranks "
        "FROM Task"
    ).fetchone()

    print(f"Total tasks:    {stats['cnt']}")
    print(f"Min rank:       {stats['min_rank']}")
    print(f"Max rank:       {stats['max_rank']}")
    print(f"Avg rank:       {stats['avg_rank']:.1f}")
    print(f"Distinct ranks: {stats['distinct_ranks']}")

    null_count = conn.execute("SELECT COUNT(*) FROM Task WHERE rank IS NULL").fetchone()[0]
    print(f"NULL ranks:     {null_count}")

    neg_count = conn.execute("SELECT COUNT(*) FROM Task WHERE rank < 0").fetchone()[0]
    print(f"Negative ranks: {neg_count}")

    # ── 3. Rank uniqueness within parent ──────────────────────────────
    section("3. Rank uniqueness: global vs within-parent")

    # Global duplicates
    global_dupes = conn.execute(
        "SELECT rank, COUNT(*) as cnt FROM Task "
        "GROUP BY rank HAVING cnt > 1 ORDER BY cnt DESC LIMIT 10"
    ).fetchall()

    print("Top 10 globally duplicated rank values:")
    for r in global_dupes:
        print(f"  rank={r['rank']:>10}  count={r['cnt']}")

    # Within-parent duplicates
    parent_dupes = conn.execute(
        "SELECT parent, rank, COUNT(*) as cnt FROM Task "
        "WHERE parent IS NOT NULL "
        "GROUP BY parent, rank HAVING cnt > 1 ORDER BY cnt DESC LIMIT 10"
    ).fetchall()

    print(f"\nWithin-parent duplicates (top 10):")
    if parent_dupes:
        for r in parent_dupes:
            print(f"  parent={r['parent']:<15} rank={r['rank']:>10} count={r['cnt']}")
    else:
        print("  NONE — rank is unique within each parent!")

    # ── 4. Rank gap analysis (sibling spacing) ────────────────────────
    section("4. Rank gap analysis for test task siblings")

    # OR-01 through OR-05 (parent = dUWW6UbTCI6)
    siblings = conn.execute(
        "SELECT persistentIdentifier, name, rank FROM Task "
        "WHERE parent = 'dUWW6UbTCI6' ORDER BY rank"
    ).fetchall()

    print("Siblings under 'Ordering Research' (expected: OR-01..OR-05):")
    prev_rank = None
    for r in siblings:
        gap = f"  (gap: {r['rank'] - prev_rank})" if prev_rank is not None else ""
        print(f"  rank={r['rank']:>10}  {r['name']}{gap}")
        prev_rank = r["rank"]

    # OR-03a subtasks (parent = bMHHXNXm-hM ... wait, OR-03a's children)
    # OR-03's children (parent = f-bTxFgMvNG)
    siblings2 = conn.execute(
        "SELECT persistentIdentifier, name, rank FROM Task "
        "WHERE parent = 'f-bTxFgMvNG' ORDER BY rank"
    ).fetchall()

    print("\nSiblings under 'OR-03 Third Task' (expected: 03a, 03b, 03c):")
    prev_rank = None
    for r in siblings2:
        gap = f"  (gap: {r['rank'] - prev_rank})" if prev_rank is not None else ""
        print(f"  rank={r['rank']:>10}  {r['name']}{gap}")
        prev_rank = r["rank"]

    # ── 5. Rank distribution (histogram) ──────────────────────────────
    section("5. Rank value distribution (buckets)")

    buckets = conn.execute(
        "SELECT "
        "  CASE "
        "    WHEN rank < 0 THEN '< 0' "
        "    WHEN rank < 1000000 THEN '0 - 1M' "
        "    WHEN rank < 10000000 THEN '1M - 10M' "
        "    WHEN rank < 100000000 THEN '10M - 100M' "
        "    WHEN rank < 1000000000 THEN '100M - 1B' "
        "    ELSE '> 1B' "
        "  END as bucket, COUNT(*) as cnt "
        "FROM Task GROUP BY bucket ORDER BY MIN(rank)"
    ).fetchall()

    for r in buckets:
        print(f"  {r['bucket']:<15} {r['cnt']:>6} tasks")

    # ── 6. Sequential vs parallel projects ────────────────────────────
    section("6. Sequential vs parallel: does rank behavior differ?")

    # Check our test projects
    proj_info = conn.execute(
        "SELECT t.persistentIdentifier, t.name, t.sequential, "
        "       pi.containsSingletonActions "
        "FROM Task t JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task "
        "WHERE t.persistentIdentifier IN ('bW2BCrF4TAz', 'gux8zqHgGas')"
    ).fetchall()

    for r in proj_info:
        seq_type = "sequential" if r["sequential"] else "parallel"
        singleton = "singleton" if r["containsSingletonActions"] else "not singleton"
        print(f"  {r['name']}: {seq_type}, {singleton}")

    # Sample a few sequential and parallel projects to compare rank patterns
    print("\nSample sequential projects (first 3):")
    seq_projs = conn.execute(
        "SELECT t.persistentIdentifier, t.name FROM Task t "
        "JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task "
        "WHERE t.sequential = 1 AND t.dateCompleted IS NULL "
        "LIMIT 3"
    ).fetchall()

    for proj in seq_projs:
        children = conn.execute(
            "SELECT name, rank FROM Task WHERE parent = ? ORDER BY rank LIMIT 5",
            (proj["persistentIdentifier"],),
        ).fetchall()
        # Anonymize
        print(f"  Project [ANON]: {len(children)} children shown")
        for i, c in enumerate(children):
            print(f"    child {i+1}: rank={c['rank']}")

    conn.close()
    print("\n✅ Phase 1 complete. All queries read-only.")


if __name__ == "__main__":
    main()
