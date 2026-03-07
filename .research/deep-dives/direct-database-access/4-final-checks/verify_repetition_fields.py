#!/usr/bin/env python3
"""
Verify all 4 RepetitionRule fields exist in SQLite with expected values.

Checks: repetitionRuleString, repetitionScheduleTypeString,
        repetitionAnchorDateKey, catchUpAutomatically

Safety: READ-ONLY. Opens SQLite with ?mode=ro.

Usage:
    python verify_repetition_fields.py
"""

import sqlite3
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


def main():
    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    conn = sqlite3.connect(f"file:{SQLITE_DB}?mode=ro", uri=True)

    # 1. Confirm all 4 columns exist
    cols = conn.execute("PRAGMA table_info(Task)").fetchall()
    expected = {
        "repetitionRuleString",
        "repetitionScheduleTypeString",
        "repetitionAnchorDateKey",
        "catchUpAutomatically",
    }
    actual = {c[1] for c in cols}
    print("=== Column existence ===")
    for col in sorted(expected):
        status = "FOUND" if col in actual else "MISSING"
        print(f"  {col}: {status}")

    # 2. Value distributions
    print("\n=== repetitionScheduleTypeString values ===")
    rows = conn.execute("""
        SELECT repetitionScheduleTypeString, COUNT(*) AS cnt
        FROM Task
        WHERE repetitionRuleString IS NOT NULL
        GROUP BY repetitionScheduleTypeString
    """).fetchall()
    for r in rows:
        print(f"  {r[0]!r}: {r[1]} tasks")

    print("\n=== repetitionAnchorDateKey values ===")
    rows = conn.execute("""
        SELECT repetitionAnchorDateKey, COUNT(*) AS cnt
        FROM Task
        WHERE repetitionRuleString IS NOT NULL
        GROUP BY repetitionAnchorDateKey
    """).fetchall()
    for r in rows:
        print(f"  {r[0]!r}: {r[1]} tasks")

    print("\n=== catchUpAutomatically values ===")
    rows = conn.execute("""
        SELECT catchUpAutomatically, COUNT(*) AS cnt
        FROM Task
        WHERE repetitionRuleString IS NOT NULL
        GROUP BY catchUpAutomatically
    """).fetchall()
    for r in rows:
        print(f"  {r[0]!r}: {r[1]} tasks")

    # 3. Sample tasks with all fields
    print("\n=== Sample tasks with repetition rules ===")
    rows = conn.execute("""
        SELECT persistentIdentifier, name,
               repetitionRuleString, repetitionScheduleTypeString,
               repetitionAnchorDateKey, catchUpAutomatically
        FROM Task
        WHERE repetitionRuleString IS NOT NULL
        LIMIT 5
    """).fetchall()
    for r in rows:
        print(f"  ID: {r[0]}")
        print(f"  Name: {r[1][:60]}")
        print(f"  ruleString: {r[2]}")
        print(f"  scheduleType: {r[3]}")
        print(f"  anchorDateKey: {r[4]}")
        print(f"  catchUpAutomatically: {r[5]}")
        print()

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
