#!/usr/bin/env python3
"""
Completed & Dropped Task Date Behavior Test

Validates date field behavior on completed and dropped tasks in the
OmniFocus SQLite cache:
  1. Completed task date completeness (dateCompleted vs effectiveDateCompleted)
  2. Dropped task date completeness (dateHidden vs effectiveDateHidden)
  3. Can a task be both completed AND dropped?
  4. Stale flag audit (overdue, dueSoon, blocked, blockedByFutureStartDate)
  5. Do completed tasks retain due/defer/planned dates?
  6. Dropped project propagation (inherited dateHidden)

Safety: READ-ONLY. Opens database with ?mode=ro URI. No writes.

Usage: python test_completed_dropped.py
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

    print("Completed & Dropped Task Date Behavior Test")
    print("============================================")
    print(f"Database: {SQLITE_DB}")
    print(f"Now (UTC): {now_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Now (CF):  {now_cf:.0f}")
    print()

    # -----------------------------------------------------------------------
    # 1. Completed task date completeness
    # -----------------------------------------------------------------------
    section("1. Completed Task Date Completeness")

    completed_count = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dateCompleted IS NOT NULL"
    ).fetchone()[0]

    completed_with_effective = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dateCompleted IS NOT NULL AND effectiveDateCompleted IS NOT NULL"
    ).fetchone()[0]

    effective_only = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dateCompleted IS NULL AND effectiveDateCompleted IS NOT NULL"
    ).fetchone()[0]

    print(f"  Tasks with dateCompleted IS NOT NULL:           {completed_count}")
    print(f"  Of those, effectiveDateCompleted IS NOT NULL:   {completed_with_effective}")
    print(f"  effectiveDateCompleted set but dateCompleted NULL (inherited?): {effective_only}")

    print()
    print("  Sample completed tasks (up to 5):")
    samples = conn.execute("""
        SELECT persistentIdentifier, name, dateCompleted, effectiveDateCompleted
        FROM Task
        WHERE dateCompleted IS NOT NULL
        LIMIT 5
    """).fetchall()
    for r in samples:
        name = (r["name"] or "(unnamed)")[:55]
        print(f"    ID: {r['persistentIdentifier']}")
        print(f"    Name: {name}")
        print(f"    dateCompleted:          {format_date(cf_to_datetime(r['dateCompleted']))}")
        print(
            f"    effectiveDateCompleted: {format_date(cf_to_datetime(r['effectiveDateCompleted']))}"
        )
        print()

    if effective_only > 0:
        print("  Sample inherited completions (up to 5):")
        inherited = conn.execute("""
            SELECT persistentIdentifier, name, dateCompleted, effectiveDateCompleted
            FROM Task
            WHERE dateCompleted IS NULL AND effectiveDateCompleted IS NOT NULL
            LIMIT 5
        """).fetchall()
        for r in inherited:
            name = (r["name"] or "(unnamed)")[:55]
            print(f"    ID: {r['persistentIdentifier']}")
            print(f"    Name: {name}")
            print(f"    dateCompleted:          {format_date(cf_to_datetime(r['dateCompleted']))}")
            print(
                f"    effectiveDateCompleted: {format_date(cf_to_datetime(r['effectiveDateCompleted']))}"
            )
            print()

    # -----------------------------------------------------------------------
    # 2. Dropped task date completeness
    # -----------------------------------------------------------------------
    section("2. Dropped Task Date Completeness")

    effectively_hidden = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE effectiveDateHidden IS NOT NULL"
    ).fetchone()[0]

    directly_hidden = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dateHidden IS NOT NULL"
    ).fetchone()[0]

    inherited_hidden = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dateHidden IS NULL AND effectiveDateHidden IS NOT NULL"
    ).fetchone()[0]

    print(f"  Tasks with effectiveDateHidden IS NOT NULL:     {effectively_hidden}")
    print(f"  Of those, dateHidden IS NOT NULL (direct):      {directly_hidden}")
    print(f"  dateHidden IS NULL but effectiveDateHidden set (inherited): {inherited_hidden}")

    if inherited_hidden > 0:
        print()
        print("  Sample inherited drops — tracing to containing project (up to 5):")
        inherited_rows = conn.execute("""
            SELECT t.persistentIdentifier, t.name, t.dateHidden, t.effectiveDateHidden,
                   t.containingProjectInfo,
                   pi.task AS project_task_id,
                   pt.name AS project_name,
                   pt.dateHidden AS project_dateHidden
            FROM Task t
            LEFT JOIN ProjectInfo pi ON t.containingProjectInfo = pi.pk
            LEFT JOIN Task pt ON pi.task = pt.persistentIdentifier
            WHERE t.dateHidden IS NULL AND t.effectiveDateHidden IS NOT NULL
            LIMIT 5
        """).fetchall()
        for r in inherited_rows:
            name = (r["name"] or "(unnamed)")[:55]
            proj_name = (r["project_name"] or "(no project)")[:45]
            print(f"    Task: {name}")
            print(f"    Task ID: {r['persistentIdentifier']}")
            print(
                f"    effectiveDateHidden: {format_date(cf_to_datetime(r['effectiveDateHidden']))}"
            )
            print(f"    Containing project: {proj_name}")
            print(
                f"    Project dateHidden:  {format_date(cf_to_datetime(r['project_dateHidden']))}"
            )
            print()

    # -----------------------------------------------------------------------
    # 3. Can a task be both completed AND dropped?
    # -----------------------------------------------------------------------
    section("3. Can a Task Be Both Completed AND Dropped?")

    both_completed_eff_hidden = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dateCompleted IS NOT NULL AND effectiveDateHidden IS NOT NULL"
    ).fetchone()[0]

    both_completed_hidden = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dateCompleted IS NOT NULL AND dateHidden IS NOT NULL"
    ).fetchone()[0]

    print(f"  dateCompleted set AND effectiveDateHidden set: {both_completed_eff_hidden}")
    print(f"  dateCompleted set AND dateHidden set:          {both_completed_hidden}")

    if both_completed_eff_hidden > 0:
        print()
        print("  Samples (up to 5):")
        both_rows = conn.execute("""
            SELECT persistentIdentifier, name, dateCompleted, dateHidden,
                   effectiveDateCompleted, effectiveDateHidden
            FROM Task
            WHERE dateCompleted IS NOT NULL AND effectiveDateHidden IS NOT NULL
            LIMIT 5
        """).fetchall()
        for r in both_rows:
            name = (r["name"] or "(unnamed)")[:55]
            print(f"    ID: {r['persistentIdentifier']}")
            print(f"    Name: {name}")
            print(f"    dateCompleted:          {format_date(cf_to_datetime(r['dateCompleted']))}")
            print(f"    dateHidden:             {format_date(cf_to_datetime(r['dateHidden']))}")
            print(
                f"    effectiveDateCompleted: {format_date(cf_to_datetime(r['effectiveDateCompleted']))}"
            )
            print(
                f"    effectiveDateHidden:    {format_date(cf_to_datetime(r['effectiveDateHidden']))}"
            )
            print()

    if both_completed_eff_hidden == 0 and both_completed_hidden == 0:
        print("  => No tasks are both completed and dropped — mutually exclusive states.")

    # -----------------------------------------------------------------------
    # 4. Stale flag audit
    # -----------------------------------------------------------------------
    section("4. Stale Flag Audit on Completed/Dropped Tasks")

    flags = ["overdue", "dueSoon", "blockedByFutureStartDate", "blocked"]

    print(f"  {'Flag':<30} {'Completed w/ flag':>18} {'Dropped w/ flag':>16}")
    print(f"  {'-' * 30} {'-' * 18} {'-' * 16}")

    for flag in flags:
        completed_flag = conn.execute(f"""
            SELECT COUNT(*) FROM Task
            WHERE dateCompleted IS NOT NULL AND {flag} = 1
        """).fetchone()[0]

        dropped_flag = conn.execute(f"""
            SELECT COUNT(*) FROM Task
            WHERE effectiveDateHidden IS NOT NULL
              AND dateCompleted IS NULL
              AND {flag} = 1
        """).fetchone()[0]

        print(f"  {flag:<30} {completed_flag:>18} {dropped_flag:>16}")

    # -----------------------------------------------------------------------
    # 5. Do completed tasks retain due/defer/planned dates?
    # -----------------------------------------------------------------------
    section("5. Do Completed Tasks Retain Due/Defer/Planned Dates?")

    date_fields = [
        ("effectiveDateDue", "effectiveDateDue"),
        ("effectiveDateToStart", "effectiveDateToStart"),
        ("effectiveDatePlanned", "effectiveDatePlanned"),
        ("dateDue", "dateDue"),
        ("dateToStart", "dateToStart"),
        ("datePlanned", "datePlanned"),
    ]

    print(f"  {'Field':<30} {'Completed tasks with field set':>32}")
    print(f"  {'-' * 30} {'-' * 32}")

    for label, col in date_fields:
        count = conn.execute(f"""
            SELECT COUNT(*) FROM Task
            WHERE dateCompleted IS NOT NULL AND {col} IS NOT NULL
        """).fetchone()[0]
        print(f"  {label:<30} {count:>32}")

    print()
    print("  Sample completed tasks with due date (up to 5):")
    due_samples = conn.execute("""
        SELECT persistentIdentifier, name, dateCompleted, dateDue, effectiveDateDue
        FROM Task
        WHERE dateCompleted IS NOT NULL AND dateDue IS NOT NULL
        LIMIT 5
    """).fetchall()
    for r in due_samples:
        name = (r["name"] or "(unnamed)")[:55]
        print(f"    ID: {r['persistentIdentifier']}")
        print(f"    Name: {name}")
        print(f"    dateCompleted:   {format_date(cf_to_datetime(r['dateCompleted']))}")
        print(f"    dateDue:         {format_date(cf_to_datetime(r['dateDue']))}")
        print(f"    effectiveDateDue:{format_date(cf_to_datetime(r['effectiveDateDue']))}")
        print()

    # -----------------------------------------------------------------------
    # 6. Dropped project propagation
    # -----------------------------------------------------------------------
    section("6. Dropped Project Propagation (Inherited dateHidden)")

    propagation_rows = conn.execute("""
        SELECT t.persistentIdentifier AS task_id,
               t.name AS task_name,
               t.effectiveDateHidden,
               pi.task AS project_task_id,
               pt.name AS project_name,
               pt.dateHidden AS project_dateHidden,
               pt.effectiveDateHidden AS project_effectiveDateHidden
        FROM Task t
        LEFT JOIN ProjectInfo pi ON t.containingProjectInfo = pi.pk
        LEFT JOIN Task pt ON pi.task = pt.persistentIdentifier
        WHERE t.effectiveDateHidden IS NOT NULL
          AND t.dateHidden IS NULL
        LIMIT 10
    """).fetchall()

    print(f"  Found {len(propagation_rows)} sample tasks with inherited drop (showing up to 10):")
    print()

    for r in propagation_rows:
        task_name = (r["task_name"] or "(unnamed)")[:50]
        proj_name = (r["project_name"] or "(no project)")[:40]
        print(f"    Task: {task_name}")
        print(f"    Task ID: {r['task_id']}")
        print(
            f"    Task effectiveDateHidden:    {format_date(cf_to_datetime(r['effectiveDateHidden']))}"
        )
        print(f"    Project: {proj_name}")
        print(
            f"    Project dateHidden:          {format_date(cf_to_datetime(r['project_dateHidden']))}"
        )
        print(
            f"    Project effectiveDateHidden: {format_date(cf_to_datetime(r['project_effectiveDateHidden']))}"
        )
        project_explains = (
            r["project_dateHidden"] is not None or r["project_effectiveDateHidden"] is not None
        )
        print(f"    Project explains inheritance: {'YES' if project_explains else 'NO'}")
        print()

    # -----------------------------------------------------------------------
    # 7. Summary
    # -----------------------------------------------------------------------
    section("7. Summary of Key Findings")

    print(f"  Completed tasks total:                          {completed_count}")
    print(f"  Completed with effectiveDateCompleted:          {completed_with_effective}")
    print(f"  Inherited completion (effective only):          {effective_only}")
    print()
    print(f"  Effectively hidden/dropped tasks:               {effectively_hidden}")
    print(f"  Directly dropped (dateHidden set):              {directly_hidden}")
    print(f"  Inherited drop (effectiveDateHidden only):      {inherited_hidden}")
    print()
    print(f"  Both completed AND dropped:                     {both_completed_eff_hidden}")
    print()

    # Stale flags summary
    any_stale = False
    for flag in flags:
        c = conn.execute(f"""
            SELECT COUNT(*) FROM Task
            WHERE dateCompleted IS NOT NULL AND {flag} = 1
        """).fetchone()[0]
        d = conn.execute(f"""
            SELECT COUNT(*) FROM Task
            WHERE effectiveDateHidden IS NOT NULL AND dateCompleted IS NULL AND {flag} = 1
        """).fetchone()[0]
        if c > 0 or d > 0:
            any_stale = True
            break

    if any_stale:
        print("  Stale flags: SOME flags persist on completed/dropped tasks (see section 4)")
    else:
        print("  Stale flags: All flags cleared on completed/dropped tasks")

    # Date retention
    retained = conn.execute("""
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NOT NULL AND effectiveDateDue IS NOT NULL
    """).fetchone()[0]
    if retained > 0:
        print(
            f"  Date retention: Completed tasks DO retain dates ({retained} have effectiveDateDue)"
        )
    else:
        print("  Date retention: Completed tasks do NOT retain dates")

    print()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
