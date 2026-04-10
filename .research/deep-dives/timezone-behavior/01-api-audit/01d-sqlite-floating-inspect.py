#!/usr/bin/env python3
"""
SQLite Floating vs Fixed Inspection

Queries the SQLite cache for TZ-PROBE-Floating and TZ-PROBE-Fixed tasks
to see how the shouldUseFloatingTimeZone flag manifests in storage.

Key discovery: The flag is NOT a separate column. It's encoded as the
presence or absence of a 'Z' suffix on naive date text columns (dateDue,
dateToStart, datePlanned).

Prerequisite: Run 01b-floating-probe.js in the OmniFocus Automation Console
first — it creates the TZ-PROBE-Floating and TZ-PROBE-Fixed tasks.

Safety: READ-ONLY. Opens database with ?mode=ro URI. No writes.

Usage: uv run python .research/deep-dives/timezone-behavior/01-api-audit/01d-sqlite-floating-inspect.py
"""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

SQLITE_DB = (
    Path.home()
    / "Library"
    / "Group Containers"
    / "34YW5XSRB7.com.omnigroup.OmniFocus"
    / "com.omnigroup.OmniFocus4"
    / "com.omnigroup.OmniFocusModel"
    / "OmniFocusDatabase.db"
)

CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)


def cf_to_iso(cf_val: float | None) -> str:
    if cf_val is None:
        return "null"
    dt = CF_EPOCH + timedelta(seconds=cf_val)
    return dt.strftime("%Y-%m-%dT%H:%M:%S UTC")


def section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print()


def main() -> None:
    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    conn = sqlite3.connect(f"file:{SQLITE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    print("SQLite Floating vs Fixed Inspection")
    print("=" * 40)
    print(f"Database: {SQLITE_DB}")
    print()

    # -----------------------------------------------------------------------
    # 1. Find TZ-PROBE-* tasks
    # -----------------------------------------------------------------------
    section("1. Find TZ-PROBE-* Tasks")

    rows = conn.execute("SELECT * FROM Task WHERE name LIKE 'TZ-PROBE-%' ORDER BY name").fetchall()

    if not rows:
        print("  ERROR: No TZ-PROBE-* tasks found.")
        print("  Run 01b-floating-probe.js in the OmniFocus Automation Console first.")
        conn.close()
        return

    print(f"  Found {len(rows)} TZ-PROBE-* tasks\n")

    # -----------------------------------------------------------------------
    # 2. Full column dump for each task (non-null only)
    # -----------------------------------------------------------------------
    section("2. Full Column Dump (non-null values)")

    task_data: dict[str, dict] = {}
    for row in rows:
        name = row["name"]
        data = {key: row[key] for key in row.keys() if row[key] is not None}
        task_data[name] = data

        print(f"  --- {name} (id: {row['persistentIdentifier']}) ---")
        for key, val in sorted(data.items()):
            print(f"    {key}: {val}")
        print()

    # -----------------------------------------------------------------------
    # 3. Side-by-side differences
    # -----------------------------------------------------------------------
    section("3. Column Differences (floating vs fixed)")

    names = sorted(task_data.keys())
    if len(names) >= 2:
        # Compare first two
        n1, n2 = names[0], names[1]
        d1, d2 = task_data[n1], task_data[n2]
        all_keys = sorted(set(d1.keys()) | set(d2.keys()))

        differs = []
        for key in all_keys:
            v1 = d1.get(key)
            v2 = d2.get(key)
            if v1 != v2:
                differs.append((key, v1, v2))

        if differs:
            print(f"  Comparing: {n1} vs {n2}\n")
            for key, v1, v2 in differs:
                print(f"  {key}:")
                print(f"    {n1}: {v1}")
                print(f"    {n2}: {v2}")
                print()
        else:
            print("  No differences found (unexpected!)")
    else:
        print("  Need at least 2 tasks to compare")

    # -----------------------------------------------------------------------
    # 4. Date column Z-suffix analysis
    # -----------------------------------------------------------------------
    section("4. Date Column Z-Suffix Analysis")

    date_cols = ["dateDue", "dateToStart", "datePlanned"]
    for row in rows:
        name = row["name"]
        print(f"  {name}:")
        for col in date_cols:
            val = row[col]
            if val is not None:
                has_z = val.endswith("Z")
                print(f"    {col}: {val}")
                print(f"      ends with 'Z': {has_z} → {'FIXED' if has_z else 'FLOATING'}")
            else:
                print(f"    {col}: null")
        print()

    # -----------------------------------------------------------------------
    # 5. Verify effectiveDateDue is same for both
    # -----------------------------------------------------------------------
    section("5. Effective Date Comparison")

    for row in rows:
        eff = row["effectiveDateDue"]
        print(f"  {row['name']}:")
        print(f"    effectiveDateDue: {eff} = {cf_to_iso(eff)}")
    print()

    if len(rows) >= 2:
        e1 = rows[0]["effectiveDateDue"]
        e2 = rows[1]["effectiveDateDue"]
        if e1 is not None and e2 is not None:
            delta = abs(e1 - e2)
            print(f"  Delta: {delta}s {'(SAME UTC moment)' if delta < 1 else '(DIFFERENT!)'}")

    # -----------------------------------------------------------------------
    # 6. Broader scan: any Z-suffix dates in the whole database?
    # -----------------------------------------------------------------------
    section("6. Broader Scan: Z-Suffix Dates Across All Tasks")

    for col in date_cols:
        z_count = conn.execute(f"SELECT COUNT(*) FROM Task WHERE \"{col}\" LIKE '%Z'").fetchone()[0]
        total = conn.execute(f'SELECT COUNT(*) FROM Task WHERE "{col}" IS NOT NULL').fetchone()[0]
        print(f"  {col}: {z_count}/{total} end with 'Z'")
        if z_count > 0:
            samples = conn.execute(
                f'SELECT name, "{col}" FROM Task WHERE "{col}" LIKE \'%Z\' LIMIT 3'
            ).fetchall()
            for s in samples:
                print(f"    '{s[0]}': {s[1]}")
    print()

    # -----------------------------------------------------------------------
    # 7. Summary
    # -----------------------------------------------------------------------
    section("7. Summary")

    print("  The shouldUseFloatingTimeZone flag is NOT a separate SQLite column.")
    print("  It is encoded in the date text string:")
    print("    - No 'Z' suffix → floating (naive local time)")
    print("    - 'Z' suffix    → fixed (UTC-anchored)")
    print()
    print("  Detection: dateDue.endswith('Z') → fixed timezone task")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
