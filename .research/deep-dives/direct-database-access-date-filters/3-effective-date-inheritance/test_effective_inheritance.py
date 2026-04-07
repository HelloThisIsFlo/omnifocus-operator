#!/usr/bin/env python3
"""
Effective Date Inheritance Test

Quantifies how many tasks inherit dates from parent projects/tasks
vs having their own direct dates. Validates the claim that ~45% of
overdue tasks would be missed without effective dates.

Safety: READ-ONLY. Opens database with ?mode=ro URI. No writes.

Usage: python test_effective_inheritance.py
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

    print("Effective Date Inheritance Test")
    print("===============================")
    print(f"Database: {SQLITE_DB}")
    print(f"Now (UTC): {now_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Now (CF):  {now_cf:.0f}")

    # -----------------------------------------------------------------------
    # 1. Four-category breakdown for each date pair
    # -----------------------------------------------------------------------

    DATE_PAIRS = [
        ("dateDue", "effectiveDateDue"),
        ("dateToStart", "effectiveDateToStart"),
        ("datePlanned", "effectiveDatePlanned"),
        ("dateCompleted", "effectiveDateCompleted"),
        ("dateHidden", "effectiveDateHidden"),
    ]

    for scope_label, where_clause in [
        ("ALL tasks", "1=1"),
        (
            "ACTIVE tasks only (dateCompleted IS NULL AND effectiveDateHidden IS NULL)",
            "dateCompleted IS NULL AND effectiveDateHidden IS NULL",
        ),
    ]:
        section(f"1. Four-Category Breakdown — {scope_label}")

        total = conn.execute(f"SELECT COUNT(*) FROM Task WHERE {where_clause}").fetchone()[0]
        print(f"  Total tasks in scope: {total}")
        print()

        for direct_col, effective_col in DATE_PAIRS:
            # A: Both set (task has its own date)
            cat_a = conn.execute(f"""
                SELECT COUNT(*) FROM Task
                WHERE {where_clause}
                  AND {direct_col} IS NOT NULL
                  AND {effective_col} IS NOT NULL
            """).fetchone()[0]

            # B: Effective set, direct NULL (inherited)
            cat_b = conn.execute(f"""
                SELECT COUNT(*) FROM Task
                WHERE {where_clause}
                  AND {direct_col} IS NULL
                  AND {effective_col} IS NOT NULL
            """).fetchone()[0]

            # C: Direct set, effective NULL (should be impossible)
            cat_c = conn.execute(f"""
                SELECT COUNT(*) FROM Task
                WHERE {where_clause}
                  AND {direct_col} IS NOT NULL
                  AND {effective_col} IS NULL
            """).fetchone()[0]

            # D: Both NULL (no date at all)
            cat_d = conn.execute(f"""
                SELECT COUNT(*) FROM Task
                WHERE {where_clause}
                  AND {direct_col} IS NULL
                  AND {effective_col} IS NULL
            """).fetchone()[0]

            inheritance_pct = (cat_b / (cat_a + cat_b) * 100) if (cat_a + cat_b) > 0 else 0

            print(f"  {direct_col} vs {effective_col}:")
            print(f"    [A] Both set (own date):          {cat_a:>6}")
            print(f"    [B] Effective only (inherited):    {cat_b:>6}")
            print(
                f"    [C] Direct only (IMPOSSIBLE?):     {cat_c:>6}{'  *** FLAG ***' if cat_c > 0 else ''}"
            )
            print(f"    [D] Both NULL (no date):           {cat_d:>6}")
            print(f"    Inheritance %% = B/(A+B):          {inheritance_pct:>6.1f}%")
            print(f"    Sum check: {cat_a + cat_b + cat_c + cat_d} (expected {total})")
            print()

    # -----------------------------------------------------------------------
    # 2. Validate "~45% of overdue tasks missed without effective dates"
    # -----------------------------------------------------------------------
    section("2. Overdue Tasks: How Many Would Be Missed Without Effective Dates?")

    # Total overdue via effective date (active tasks)
    overdue_effective = conn.execute(
        """
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND effectiveDateDue IS NOT NULL
          AND effectiveDateDue < ?
    """,
        (now_cf,),
    ).fetchone()[0]

    # Of those, how many have dateDue IS NULL (inherited-only)
    overdue_inherited_only = conn.execute(
        """
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND effectiveDateDue IS NOT NULL
          AND effectiveDateDue < ?
          AND dateDue IS NULL
    """,
        (now_cf,),
    ).fetchone()[0]

    # Tasks overdue via direct date only
    overdue_direct = conn.execute(
        """
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND dateDue IS NOT NULL
          AND dateDue < ?
    """,
        (now_cf,),
    ).fetchone()[0]

    missed_pct = (overdue_inherited_only / overdue_effective * 100) if overdue_effective > 0 else 0

    print(f"  Overdue via effectiveDateDue < now:  {overdue_effective}")
    print(f"  Of those, dateDue IS NULL (inherited): {overdue_inherited_only}")
    print(f"  => Would be MISSED without effective dates: {missed_pct:.1f}%")
    print()
    print(f"  Overdue via dateDue < now (direct only): {overdue_direct}")
    print(f"  Difference (effective - direct):         {overdue_effective - overdue_direct}")

    # -----------------------------------------------------------------------
    # 3. Parent chain walk for 10 sample inherited tasks
    # -----------------------------------------------------------------------
    section("3. Parent Chain Walk — 10 Sample Tasks With Inherited Due Dates")

    inherited_samples = conn.execute("""
        SELECT persistentIdentifier, name, dateDue, effectiveDateDue, parent,
               containingProjectInfo
        FROM Task
        WHERE dateCompleted IS NULL
          AND effectiveDateDue IS NOT NULL
          AND dateDue IS NULL
        LIMIT 10
    """).fetchall()

    for i, task in enumerate(inherited_samples, 1):
        name = (task["name"] or "(unnamed)")[:60]
        eff_due = cf_to_datetime(task["effectiveDateDue"])
        print(f"  [{i}] {name}")
        print(f"      ID: {task['persistentIdentifier']}")
        print(f"      dateDue: none  effectiveDateDue: {format_date(eff_due)}")

        # Walk up the parent chain
        current_parent = task["parent"]
        level = 1
        found_source = False
        while current_parent:
            parent_row = conn.execute(
                """
                SELECT persistentIdentifier, name, dateDue, effectiveDateDue, parent
                FROM Task
                WHERE persistentIdentifier = ?
            """,
                (current_parent,),
            ).fetchone()

            if parent_row is None:
                print(f"      L{level}: parent {current_parent} NOT FOUND in Task table")
                break

            p_name = (parent_row["name"] or "(unnamed)")[:50]
            p_due = cf_to_datetime(parent_row["dateDue"])
            p_eff = cf_to_datetime(parent_row["effectiveDateDue"])
            has_own = parent_row["dateDue"] is not None

            print(f"      L{level}: {p_name}")
            print(f"          dateDue={format_date(p_due)}  effectiveDateDue={format_date(p_eff)}")

            if has_own:
                print("          ^^^ SOURCE FOUND (has own dateDue)")
                found_source = True
                break

            current_parent = parent_row["parent"]
            level += 1

            if level > 20:
                print("          ... stopping at depth 20")
                break

        # Also check containing project
        if not found_source and task["containingProjectInfo"]:
            proj_row = conn.execute(
                """
                SELECT pi.pk, t.persistentIdentifier, t.name, t.dateDue, t.effectiveDateDue
                FROM ProjectInfo pi
                JOIN Task t ON pi.task = t.persistentIdentifier
                WHERE pi.pk = ?
            """,
                (task["containingProjectInfo"],),
            ).fetchone()

            if proj_row:
                proj_name = (proj_row["name"] or "(unnamed)")[:50]
                proj_due = cf_to_datetime(proj_row["dateDue"])
                proj_eff = cf_to_datetime(proj_row["effectiveDateDue"])
                print(f"      Project: {proj_name}")
                print(
                    f"          dateDue={format_date(proj_due)}  effectiveDateDue={format_date(proj_eff)}"
                )
                if proj_row["dateDue"] is not None:
                    print("          ^^^ SOURCE FOUND (project has dateDue)")
                    found_source = True

        if not found_source:
            print("      *** NO SOURCE FOUND — date origin unclear ***")

        print()

    # -----------------------------------------------------------------------
    # 4. Verify effective dates are always CF epoch floats
    # -----------------------------------------------------------------------
    section("4. Effective Date Column Types (should all be 'real')")

    effective_cols = [
        "effectiveDateDue",
        "effectiveDateToStart",
        "effectiveDatePlanned",
        "effectiveDateCompleted",
        "effectiveDateHidden",
    ]

    for col in effective_cols:
        type_counts = conn.execute(f"""
            SELECT typeof({col}) AS t, COUNT(*) AS cnt
            FROM Task
            WHERE {col} IS NOT NULL
            GROUP BY typeof({col})
            ORDER BY cnt DESC
        """).fetchall()

        type_str = ", ".join(f"{r['t']}={r['cnt']}" for r in type_counts)
        print(f"  {col}:")
        print(f"    Types: {type_str if type_str else '(no non-NULL values)'}")

        # Sample 3 raw values
        samples = conn.execute(f"""
            SELECT {col} FROM Task WHERE {col} IS NOT NULL LIMIT 3
        """).fetchall()
        for j, s in enumerate(samples):
            raw = s[0]
            dt = cf_to_datetime(raw)
            print(f"    Sample {j + 1}: raw={raw}  => {format_date(dt)}")
        print()

    # -----------------------------------------------------------------------
    # 5. Verify direct date column types
    # -----------------------------------------------------------------------
    section("5. Direct Date Column Types (expected: 'text' for naive local datetimes)")

    direct_cols = ["dateDue", "dateToStart", "datePlanned"]

    for col in direct_cols:
        type_counts = conn.execute(f"""
            SELECT typeof({col}) AS t, COUNT(*) AS cnt
            FROM Task
            WHERE {col} IS NOT NULL
            GROUP BY typeof({col})
            ORDER BY cnt DESC
        """).fetchall()

        type_str = ", ".join(f"{r['t']}={r['cnt']}" for r in type_counts)
        print(f"  {col}:")
        print(f"    Types: {type_str if type_str else '(no non-NULL values)'}")

        # Sample 3 raw values
        samples = conn.execute(f"""
            SELECT {col} FROM Task WHERE {col} IS NOT NULL LIMIT 3
        """).fetchall()
        for j, s in enumerate(samples):
            print(f"    Sample {j + 1}: raw={s[0]!r}")
        print()

    # Also check dateCompleted and dateHidden for completeness
    print("  (Also checking dateCompleted, dateHidden:)")
    for col in ["dateCompleted", "dateHidden"]:
        type_counts = conn.execute(f"""
            SELECT typeof({col}) AS t, COUNT(*) AS cnt
            FROM Task
            WHERE {col} IS NOT NULL
            GROUP BY typeof({col})
            ORDER BY cnt DESC
        """).fetchall()

        type_str = ", ".join(f"{r['t']}={r['cnt']}" for r in type_counts)
        print(f"  {col}:")
        print(f"    Types: {type_str if type_str else '(no non-NULL values)'}")

        samples = conn.execute(f"""
            SELECT {col} FROM Task WHERE {col} IS NOT NULL LIMIT 3
        """).fetchall()
        for j, s in enumerate(samples):
            raw = s[0]
            dt = cf_to_datetime(raw) if isinstance(raw, (int, float)) else raw
            print(
                f"    Sample {j + 1}: raw={raw!r}  => {format_date(dt) if isinstance(dt, datetime) else dt}"
            )
        print()

    # -----------------------------------------------------------------------
    # 6. Summary
    # -----------------------------------------------------------------------
    section("6. Summary")

    print("  Date Inheritance:")
    print(f"    Overdue via effective dates:           {overdue_effective}")
    print(f"    Overdue via inherited dates only:      {overdue_inherited_only}")
    print(f"    Missed without effective dates:        {missed_pct:.1f}%")
    print()
    print("  Key finding:")
    if missed_pct >= 30:
        print(f"    CONFIRMED: {missed_pct:.0f}% of overdue tasks have inherited due dates.")
        print("    Using dateDue alone would miss a significant portion of overdue tasks.")
        print("    effectiveDateDue is REQUIRED for accurate overdue filtering.")
    elif missed_pct >= 10:
        print(f"    NOTABLE: {missed_pct:.0f}% of overdue tasks have inherited due dates.")
        print("    effectiveDateDue is recommended for accurate overdue filtering.")
    else:
        print(f"    LOW: Only {missed_pct:.0f}% of overdue tasks have inherited due dates.")
        print("    dateDue alone may be sufficient, but effectiveDateDue is still safer.")

    print()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
