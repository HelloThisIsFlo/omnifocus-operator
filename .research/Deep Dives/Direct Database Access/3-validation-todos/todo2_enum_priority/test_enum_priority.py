#!/usr/bin/env python3
"""
Enum Priority Analysis: Status Flag Overlaps in OmniFocus SQLite Cache

The OmniFocus bridge returns a single taskStatus enum where conditions compete
(a task is Overdue OR Blocked, never both). The SQLite cache has independent
boolean columns: blocked, blockedByFutureStartDate, overdue, dueSoon.

This script analyzes which combinations actually occur in the database,
revealing the priority order of the single-winner enum.

Safety: READ-ONLY. No writes to SQLite or OmniFocus.

Usage: python test_enum_priority.py
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SQLITE_DB = (
    Path.home()
    / "Library"
    / "Group Containers"
    / "34YW5XSRB7.com.omnigroup.OmniFocus"
    / "com.omnigroup.OmniFocus4"
    / "com.omnigroup.OmniFocusModel"
    / "OmniFocusDatabase.db"
)

CF_EPOCH = datetime(2001, 1, 1)


def cf_to_datetime(cf_timestamp):
    """Convert Core Foundation Absolute Time to datetime."""
    if cf_timestamp is None:
        return None
    try:
        return CF_EPOCH + timedelta(seconds=float(cf_timestamp))
    except (TypeError, ValueError):
        return None


def format_date(dt):
    """Format a datetime for display, or return 'none' if None."""
    if dt is None:
        return "none"
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    conn = sqlite3.connect(str(SQLITE_DB))
    conn.row_factory = sqlite3.Row

    print("Enum Priority Analysis")
    print("======================")
    print(f"Database: {SQLITE_DB}")
    print()

    # -----------------------------------------------------------------------
    # 1. Total task counts
    # -----------------------------------------------------------------------
    total = conn.execute("SELECT COUNT(*) FROM Task").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM Task WHERE dateCompleted IS NULL").fetchone()[0]
    completed = total - active

    print(f"Total tasks: {total}")
    print(f"  Active (not completed): {active}")
    print(f"  Completed: {completed}")
    print()

    # -----------------------------------------------------------------------
    # 2. Full status flag matrix (active tasks only)
    # -----------------------------------------------------------------------
    print("Status Flag Distribution (active tasks only, dateCompleted IS NULL):")
    print("-" * 75)

    rows = conn.execute("""
        SELECT
            blocked,
            blockedByFutureStartDate,
            overdue,
            dueSoon,
            COUNT(*) as cnt
        FROM Task
        WHERE dateCompleted IS NULL
        GROUP BY blocked, blockedByFutureStartDate, overdue, dueSoon
        ORDER BY cnt DESC
    """).fetchall()

    overlap_count = 0
    for row in rows:
        b = row["blocked"]
        bfs = row["blockedByFutureStartDate"]
        od = row["overdue"]
        ds = row["dueSoon"]
        cnt = row["cnt"]

        # Check if this is an overlap (more than one flag set)
        flags_set = sum([b or 0, bfs or 0, od or 0, ds or 0])
        marker = "  <-- OVERLAP" if flags_set > 1 else ""
        if flags_set > 1:
            overlap_count += cnt

        print(
            f"  blocked={b or 0}, blockedByFutureStart={bfs or 0}, "
            f"overdue={od or 0}, dueSoon={ds or 0}: {cnt:>6} tasks{marker}"
        )

    print()
    print(f"Total tasks with overlapping flags: {overlap_count}")
    print()

    # -----------------------------------------------------------------------
    # 3. Key overlap counts
    # -----------------------------------------------------------------------
    print("Key Overlaps:")
    print("-" * 50)

    overlaps = [
        ("blocked AND overdue", "blocked = 1 AND overdue = 1"),
        ("blocked AND dueSoon", "blocked = 1 AND dueSoon = 1"),
        ("blockedByFutureStartDate AND overdue", "blockedByFutureStartDate = 1 AND overdue = 1"),
        ("blockedByFutureStartDate AND dueSoon", "blockedByFutureStartDate = 1 AND dueSoon = 1"),
        ("overdue AND dueSoon", "overdue = 1 AND dueSoon = 1"),
        ("blocked AND blockedByFutureStartDate", "blocked = 1 AND blockedByFutureStartDate = 1"),
    ]

    for label, condition in overlaps:
        cnt = conn.execute(
            f"SELECT COUNT(*) FROM Task WHERE dateCompleted IS NULL AND {condition}"
        ).fetchone()[0]
        print(f"  {label + ':':<45} {cnt:>5} tasks")

    print()

    # -----------------------------------------------------------------------
    # 4. Sample tasks for each overlap
    # -----------------------------------------------------------------------
    print("Sample Tasks for Key Overlaps:")
    print("-" * 50)

    sample_overlaps = [
        ("blocked AND overdue", "blocked = 1 AND overdue = 1"),
        ("blocked AND dueSoon", "blocked = 1 AND dueSoon = 1"),
        ("blockedByFutureStartDate AND overdue", "blockedByFutureStartDate = 1 AND overdue = 1"),
        ("blockedByFutureStartDate AND dueSoon", "blockedByFutureStartDate = 1 AND dueSoon = 1"),
    ]

    for label, condition in sample_overlaps:
        samples = conn.execute(
            f"""
            SELECT name, dateDue, dateToStart, blocked, blockedByFutureStartDate, overdue, dueSoon
            FROM Task
            WHERE dateCompleted IS NULL AND {condition}
            LIMIT 5
            """
        ).fetchall()

        print(f"\n  {label}:")
        if not samples:
            print("    (none found)")
        else:
            for s in samples:
                due = format_date(cf_to_datetime(s["dateDue"]))
                defer = format_date(cf_to_datetime(s["dateToStart"]))
                name = s["name"] or "(unnamed)"
                # Truncate long names
                if len(name) > 60:
                    name = name[:57] + "..."
                print(f'    "{name}" (due: {due}, defer: {defer})')

    print()

    # -----------------------------------------------------------------------
    # 5. Completed tasks with status flags still set
    # -----------------------------------------------------------------------
    print("Completed Tasks with Status Flags Still Set:")
    print("-" * 50)

    completed_with_flags = conn.execute("""
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NOT NULL
          AND (blocked = 1 OR overdue = 1 OR dueSoon = 1 OR blockedByFutureStartDate = 1)
    """).fetchone()[0]

    print(f"  Total: {completed_with_flags}")

    if completed_with_flags > 0:
        # Break down which flags
        for flag_name in ["blocked", "blockedByFutureStartDate", "overdue", "dueSoon"]:
            cnt = conn.execute(
                f"SELECT COUNT(*) FROM Task WHERE dateCompleted IS NOT NULL AND {flag_name} = 1"
            ).fetchone()[0]
            if cnt > 0:
                print(f"  With {flag_name}=1: {cnt}")

        # Show a few samples
        samples = conn.execute("""
            SELECT name, dateCompleted, blocked, blockedByFutureStartDate, overdue, dueSoon
            FROM Task
            WHERE dateCompleted IS NOT NULL
              AND (blocked = 1 OR overdue = 1 OR dueSoon = 1 OR blockedByFutureStartDate = 1)
            LIMIT 5
        """).fetchall()

        print("\n  Samples:")
        for s in samples:
            completed_dt = format_date(cf_to_datetime(s["dateCompleted"]))
            flags = []
            if s["blocked"]:
                flags.append("blocked")
            if s["blockedByFutureStartDate"]:
                flags.append("blockedByFutureStart")
            if s["overdue"]:
                flags.append("overdue")
            if s["dueSoon"]:
                flags.append("dueSoon")
            name = s["name"] or "(unnamed)"
            if len(name) > 50:
                name = name[:47] + "..."
            print(f'    "{name}" (completed: {completed_dt}, flags: {", ".join(flags)})')

    print()

    # -----------------------------------------------------------------------
    # 6. Bonus: blocked vs blockedByFutureStartDate relationship
    # -----------------------------------------------------------------------
    print("Blocked vs BlockedByFutureStartDate Relationship (active tasks):")
    print("-" * 50)

    # Is blockedByFutureStartDate always a subset of blocked?
    bfs_not_blocked = conn.execute("""
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND blockedByFutureStartDate = 1
          AND blocked = 0
    """).fetchone()[0]

    blocked_not_bfs = conn.execute("""
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND blocked = 1
          AND blockedByFutureStartDate = 0
    """).fetchone()[0]

    both = conn.execute("""
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND blocked = 1
          AND blockedByFutureStartDate = 1
    """).fetchone()[0]

    print(f"  blockedByFutureStartDate=1 AND blocked=0: {bfs_not_blocked}")
    print(f"  blocked=1 AND blockedByFutureStartDate=0: {blocked_not_bfs}")
    print(f"  Both blocked=1 AND blockedByFutureStartDate=1: {both}")

    if bfs_not_blocked == 0:
        print("  => blockedByFutureStartDate is a SUBSET of blocked")
    elif blocked_not_bfs == 0:
        print("  => blocked is a SUBSET of blockedByFutureStartDate")
    else:
        print("  => They are INDEPENDENT flags (neither is a subset)")

    print()

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
