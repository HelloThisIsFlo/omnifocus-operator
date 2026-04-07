#!/usr/bin/env python3
"""
Overdue Flag Equivalence Test

Tests whether `overdue = 1` in the OmniFocus SQLite cache is always
equivalent to `effectiveDateDue < now()`.

Checks all four possible mismatch categories:
  1. overdue=1 AND effectiveDateDue IS NULL     (flag without a due date?)
  2. overdue=1 AND effectiveDateDue >= now       (flag set but not yet past due?)
  3. overdue=0 AND effectiveDateDue < now        (past due but flag not set?)
  4. overdue=1 AND effectiveDateDue < now        (agreement — expected case)

Also checks whether `dueSoon` has a similar relationship with effectiveDateDue.

Safety: READ-ONLY. Opens database with ?mode=ro URI. No writes.

Usage: python test_overdue_equivalence.py
"""

import sqlite3
from datetime import UTC, datetime, timedelta
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

# Core Foundation epoch: 2001-01-01 00:00:00 UTC
CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)


def cf_to_datetime(cf_timestamp):
    """Convert Core Foundation Absolute Time to datetime (UTC)."""
    if cf_timestamp is None:
        return None
    try:
        return CF_EPOCH + timedelta(seconds=float(cf_timestamp))
    except (TypeError, ValueError):
        return None


def now_as_cf() -> float:
    """Current time as Core Foundation Absolute Time (seconds since 2001-01-01)."""
    return (datetime.now(UTC) - CF_EPOCH).total_seconds()


def format_date(dt):
    """Format a datetime for display, or return 'none' if None."""
    if dt is None:
        return "none"
    return dt.strftime("%Y-%m-%d %H:%M")


def section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    uri = f"file:{SQLITE_DB}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    now_cf = now_as_cf()
    now_dt = datetime.now(UTC)

    print("Overdue Flag Equivalence Test")
    print("=============================")
    print(f"Database: {SQLITE_DB}")
    print(f"Now (UTC): {now_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Now (CF):  {now_cf:.0f}")
    print()

    # -----------------------------------------------------------------------
    # 1. Baseline counts (active tasks only — dateCompleted IS NULL)
    # -----------------------------------------------------------------------
    section("1. Baseline Counts (active tasks, dateCompleted IS NULL)")

    total = conn.execute("SELECT COUNT(*) FROM Task WHERE dateCompleted IS NULL").fetchone()[0]

    with_due = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dateCompleted IS NULL AND effectiveDateDue IS NOT NULL"
    ).fetchone()[0]

    overdue_count = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dateCompleted IS NULL AND overdue = 1"
    ).fetchone()[0]

    due_soon_count = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dateCompleted IS NULL AND dueSoon = 1"
    ).fetchone()[0]

    print(f"  Active tasks:                {total}")
    print(f"  With effectiveDateDue:       {with_due}")
    print(f"  With overdue=1:              {overdue_count}")
    print(f"  With dueSoon=1:              {due_soon_count}")

    # -----------------------------------------------------------------------
    # 2. Overdue equivalence: overdue=1 ↔ effectiveDateDue < now
    # -----------------------------------------------------------------------
    section("2. Overdue Equivalence: overdue=1 ↔ effectiveDateDue < now")

    # Category A: overdue=1 AND effectiveDateDue IS NULL
    cat_a = conn.execute("""
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND overdue = 1
          AND effectiveDateDue IS NULL
    """).fetchone()[0]

    # Category B: overdue=1 AND effectiveDateDue >= now (flag set, but not past due)
    cat_b = conn.execute(
        """
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND overdue = 1
          AND effectiveDateDue IS NOT NULL
          AND effectiveDateDue >= ?
    """,
        (now_cf,),
    ).fetchone()[0]

    # Category C: overdue=0 AND effectiveDateDue < now (past due, but flag not set)
    cat_c = conn.execute(
        """
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND (overdue = 0 OR overdue IS NULL)
          AND effectiveDateDue IS NOT NULL
          AND effectiveDateDue < ?
    """,
        (now_cf,),
    ).fetchone()[0]

    # Category D: overdue=1 AND effectiveDateDue < now (agreement)
    cat_d = conn.execute(
        """
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND overdue = 1
          AND effectiveDateDue IS NOT NULL
          AND effectiveDateDue < ?
    """,
        (now_cf,),
    ).fetchone()[0]

    print(f"  [A] overdue=1, effectiveDateDue IS NULL:   {cat_a:>5}  (flag without due date)")
    print(f"  [B] overdue=1, effectiveDateDue >= now:    {cat_b:>5}  (flag set but not past due)")
    print(f"  [C] overdue=0, effectiveDateDue < now:     {cat_c:>5}  (past due but flag not set)")
    print(f"  [D] overdue=1, effectiveDateDue < now:     {cat_d:>5}  (agreement)")
    print()

    total_mismatches = cat_a + cat_b + cat_c
    if total_mismatches == 0:
        print("  RESULT: Perfect equivalence — overdue=1 ↔ effectiveDateDue < now")
    else:
        print(f"  RESULT: {total_mismatches} mismatches found")

    # -----------------------------------------------------------------------
    # 3. Sample mismatches (if any)
    # -----------------------------------------------------------------------
    if cat_a > 0:
        section("3A. Samples: overdue=1 but effectiveDateDue IS NULL")
        rows = conn.execute("""
            SELECT persistentIdentifier, name, overdue, dateDue, effectiveDateDue,
                   blocked, blockedByFutureStartDate, parent, containingProjectInfo
            FROM Task
            WHERE dateCompleted IS NULL
              AND overdue = 1
              AND effectiveDateDue IS NULL
            LIMIT 10
        """).fetchall()
        for r in rows:
            name = (r["name"] or "(unnamed)")[:55]
            print(f"    ID: {r['persistentIdentifier']}")
            print(f"    Name: {name}")
            print(f"    dateDue={format_date(cf_to_datetime(r['dateDue']))}")
            print(f"    effectiveDateDue={format_date(cf_to_datetime(r['effectiveDateDue']))}")
            print(
                f"    blocked={r['blocked']}  blockedByFutureStart={r['blockedByFutureStartDate']}"
            )
            print()

    if cat_b > 0:
        section("3B. Samples: overdue=1 but effectiveDateDue >= now")
        rows = conn.execute(
            """
            SELECT persistentIdentifier, name, overdue, dateDue, effectiveDateDue,
                   blocked, blockedByFutureStartDate
            FROM Task
            WHERE dateCompleted IS NULL
              AND overdue = 1
              AND effectiveDateDue IS NOT NULL
              AND effectiveDateDue >= ?
            LIMIT 10
        """,
            (now_cf,),
        ).fetchall()
        for r in rows:
            name = (r["name"] or "(unnamed)")[:55]
            eff_due = cf_to_datetime(r["effectiveDateDue"])
            delta = eff_due - now_dt if eff_due else None
            print(f"    ID: {r['persistentIdentifier']}")
            print(f"    Name: {name}")
            print(f"    effectiveDateDue={format_date(eff_due)} (in {delta})")
            print(
                f"    blocked={r['blocked']}  blockedByFutureStart={r['blockedByFutureStartDate']}"
            )
            print()

    if cat_c > 0:
        section("3C. Samples: effectiveDateDue < now but overdue=0")
        rows = conn.execute(
            """
            SELECT persistentIdentifier, name, overdue, dateDue, effectiveDateDue,
                   blocked, blockedByFutureStartDate, dateCompleted
            FROM Task
            WHERE dateCompleted IS NULL
              AND (overdue = 0 OR overdue IS NULL)
              AND effectiveDateDue IS NOT NULL
              AND effectiveDateDue < ?
            LIMIT 10
        """,
            (now_cf,),
        ).fetchall()
        for r in rows:
            name = (r["name"] or "(unnamed)")[:55]
            eff_due = cf_to_datetime(r["effectiveDateDue"])
            delta = now_dt - eff_due if eff_due else None
            print(f"    ID: {r['persistentIdentifier']}")
            print(f"    Name: {name}")
            print(f"    effectiveDateDue={format_date(eff_due)} (overdue by {delta})")
            print(f"    overdue={r['overdue']}  blocked={r['blocked']}")
            print(f"    blockedByFutureStart={r['blockedByFutureStartDate']}")
            print()

    # -----------------------------------------------------------------------
    # 4. dueSoon equivalence probe
    # -----------------------------------------------------------------------
    section("4. dueSoon Probe: What date range does dueSoon=1 cover?")

    # Find the effectiveDateDue range for dueSoon=1 tasks
    due_soon_range = conn.execute("""
        SELECT
            MIN(effectiveDateDue) AS earliest,
            MAX(effectiveDateDue) AS latest,
            COUNT(*) AS cnt
        FROM Task
        WHERE dateCompleted IS NULL
          AND dueSoon = 1
          AND effectiveDateDue IS NOT NULL
    """).fetchone()

    if due_soon_range["cnt"] > 0:
        earliest = cf_to_datetime(due_soon_range["earliest"])
        latest = cf_to_datetime(due_soon_range["latest"])
        print(f"  dueSoon=1 tasks with effectiveDateDue: {due_soon_range['cnt']}")
        print(f"  Earliest effectiveDateDue: {format_date(earliest)}")
        print(f"  Latest effectiveDateDue:   {format_date(latest)}")
        if earliest and latest:
            print(f"  Delta from now to earliest: {earliest - now_dt}")
            print(f"  Delta from now to latest:   {latest - now_dt}")
    else:
        print("  No dueSoon=1 tasks with effectiveDateDue found.")

    print()

    # dueSoon but NOT overdue — what's the date range?
    ds_not_od = conn.execute("""
        SELECT
            MIN(effectiveDateDue) AS earliest,
            MAX(effectiveDateDue) AS latest,
            COUNT(*) AS cnt
        FROM Task
        WHERE dateCompleted IS NULL
          AND dueSoon = 1
          AND (overdue = 0 OR overdue IS NULL)
          AND effectiveDateDue IS NOT NULL
    """).fetchone()

    if ds_not_od["cnt"] > 0:
        earliest = cf_to_datetime(ds_not_od["earliest"])
        latest = cf_to_datetime(ds_not_od["latest"])
        print(f"  dueSoon=1 AND overdue=0 (truly upcoming): {ds_not_od['cnt']}")
        print(f"  Earliest: {format_date(earliest)} (in {earliest - now_dt if earliest else '?'})")
        print(f"  Latest:   {format_date(latest)} (in {latest - now_dt if latest else '?'})")
    else:
        print("  No dueSoon-only (non-overdue) tasks found.")

    # dueSoon=0 but effectiveDateDue within 48h — are there tasks OmniFocus
    # doesn't consider "due soon" that we might expect it to?
    print()
    soon_threshold_cf = now_cf + (48 * 3600)  # 48 hours from now
    not_ds_but_soon = conn.execute(
        """
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND (dueSoon = 0 OR dueSoon IS NULL)
          AND effectiveDateDue IS NOT NULL
          AND effectiveDateDue > ?
          AND effectiveDateDue < ?
    """,
        (now_cf, soon_threshold_cf),
    ).fetchone()[0]

    print(f"  Tasks due within 48h but dueSoon=0: {not_ds_but_soon}")
    if not_ds_but_soon > 0:
        print("  (OmniFocus 'due soon' window may be shorter or longer than 48h)")

    # -----------------------------------------------------------------------
    # 5. Completed tasks: are overdue flags cleared?
    # -----------------------------------------------------------------------
    section("5. Completed Tasks: Are overdue/dueSoon flags cleared?")

    completed_overdue = conn.execute("""
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NOT NULL AND overdue = 1
    """).fetchone()[0]

    completed_due_soon = conn.execute("""
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NOT NULL AND dueSoon = 1
    """).fetchone()[0]

    print(f"  Completed tasks with overdue=1:  {completed_overdue}")
    print(f"  Completed tasks with dueSoon=1:  {completed_due_soon}")
    if completed_overdue == 0 and completed_due_soon == 0:
        print("  => Flags are cleared on completion")
    else:
        print("  => Flags persist after completion (stale?)")

    # -----------------------------------------------------------------------
    # 6. Summary
    # -----------------------------------------------------------------------
    section("6. Summary")

    print("  Overdue equivalence (overdue=1 ↔ effectiveDateDue < now):")
    print(f"    Matches (D):                    {cat_d}")
    print(f"    Flag without due date (A):      {cat_a}")
    print(f"    Flag set, not past due (B):     {cat_b}")
    print(f"    Past due, flag not set (C):     {cat_c}")
    print()

    if total_mismatches == 0:
        print("  VERDICT: overdue=1 is equivalent to effectiveDateDue < now()")
        print("           Safe to use either form in queries.")
    elif cat_c > 0 and cat_a == 0 and cat_b == 0:
        print("  VERDICT: overdue=1 is a SUBSET of effectiveDateDue < now()")
        print("           Some past-due tasks don't have the flag set.")
        print("           Use effectiveDateDue < now() for complete results.")
    elif cat_a == 0 and cat_b == 0:
        print("  VERDICT: overdue=1 IMPLIES effectiveDateDue < now() (no false positives)")
    else:
        print("  VERDICT: The relationship is more complex — review mismatches above.")

    print()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
