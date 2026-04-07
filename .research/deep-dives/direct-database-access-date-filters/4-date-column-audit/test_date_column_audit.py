#!/usr/bin/env python3
"""
Date Column Audit

Audits the storage format, types, and null distribution of all date columns
in the OmniFocus SQLite Task table.

Covers:
  1. typeof() check for all 14 date columns
  2. Sample raw values for each column
  3. Null distribution on active tasks for the 7 filterable columns
  4. Confirm dateAdded/dateModified are never null
  5. Verify dateDue/dateToStart/datePlanned are always text (naive strings)
  6. Verify effective* columns are always real (CF epoch floats)
  7. dateAdded/dateModified type check

Safety: READ-ONLY. Opens database with ?mode=ro URI. No writes.

Usage: python test_date_column_audit.py
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

# All 14 date columns in the Task table
ALL_DATE_COLUMNS = [
    "dateAdded",
    "dateModified",
    "dateCompleted",
    "dateDue",
    "dateToStart",
    "datePlanned",
    "dateHidden",
    "effectiveDateDue",
    "effectiveDateToStart",
    "effectiveDateCompleted",
    "effectiveDatePlanned",
    "effectiveDateHidden",
]

# The 7 columns v1.3.2 will filter on (checked on active tasks)
FILTERABLE_COLUMNS = [
    "effectiveDateDue",
    "effectiveDateToStart",
    "effectiveDatePlanned",
    "effectiveDateCompleted",
    "effectiveDateHidden",
    "dateAdded",
    "dateModified",
]

# Direct date columns expected to be text (naive datetime strings)
DIRECT_TEXT_COLUMNS = ["dateDue", "dateToStart", "datePlanned"]

# Effective columns expected to be real (CF epoch floats)
EFFECTIVE_REAL_COLUMNS = [
    "effectiveDateDue",
    "effectiveDateToStart",
    "effectiveDatePlanned",
    "effectiveDateCompleted",
    "effectiveDateHidden",
]


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

    now_dt = datetime.now(UTC)

    print("Date Column Audit")
    print("=================")
    print(f"Database: {SQLITE_DB}")
    print(f"Now (UTC): {now_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    total_tasks = conn.execute("SELECT COUNT(*) FROM Task").fetchone()[0]
    print(f"Total tasks in database: {total_tasks}")

    # -----------------------------------------------------------------------
    # 1. typeof() check for ALL 14 date columns
    # -----------------------------------------------------------------------
    section("1. typeof() Check for All Date Columns")

    print(f"  {'Column':<30} {'Type':<10} {'Count':>8}")
    print(f"  {'-' * 30} {'-' * 10} {'-' * 8}")

    type_results = {}
    for col in ALL_DATE_COLUMNS:
        rows = conn.execute(
            f"SELECT typeof({col}) AS t, COUNT(*) AS c "
            f"FROM Task WHERE {col} IS NOT NULL GROUP BY typeof({col})"
        ).fetchall()
        type_results[col] = [(r["t"], r["c"]) for r in rows]
        if not rows:
            print(f"  {col:<30} {'(all NULL)':<10} {0:>8}")
        else:
            for i, (typ, cnt) in enumerate(type_results[col]):
                label = col if i == 0 else ""
                print(f"  {label:<30} {typ:<10} {cnt:>8}")

    # -----------------------------------------------------------------------
    # 2. Sample raw values for each column
    # -----------------------------------------------------------------------
    section("2. Sample Raw Values (3 per column)")

    for col in ALL_DATE_COLUMNS:
        rows = conn.execute(f"SELECT {col} FROM Task WHERE {col} IS NOT NULL LIMIT 3").fetchall()
        values = [str(r[0]) for r in rows]
        if values:
            print(f"  {col}:")
            for v in values:
                print(f"    {v}")
        else:
            print(f"  {col}: (no non-NULL values)")
        print()

    # -----------------------------------------------------------------------
    # 3. Null distribution for 7 filterable columns on ACTIVE tasks
    # -----------------------------------------------------------------------
    section("3. Null Distribution on Active Tasks (7 Filterable Columns)")

    active_count = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dateCompleted IS NULL AND effectiveDateHidden IS NULL"
    ).fetchone()[0]
    print(f"  Active tasks (dateCompleted IS NULL AND effectiveDateHidden IS NULL): {active_count}")
    print()

    print(f"  {'Column':<30} {'NOT NULL':>10} {'NULL':>10} {'% NULL':>10}")
    print(f"  {'-' * 30} {'-' * 10} {'-' * 10} {'-' * 10}")

    for col in FILTERABLE_COLUMNS:
        not_null = conn.execute(
            f"SELECT COUNT(*) FROM Task "
            f"WHERE dateCompleted IS NULL AND effectiveDateHidden IS NULL "
            f"AND {col} IS NOT NULL"
        ).fetchone()[0]
        null_count = active_count - not_null
        pct = (null_count / active_count * 100) if active_count > 0 else 0
        print(f"  {col:<30} {not_null:>10} {null_count:>10} {pct:>9.1f}%")

    # -----------------------------------------------------------------------
    # 4. Confirm dateAdded and dateModified are NEVER null
    # -----------------------------------------------------------------------
    section("4. dateAdded / dateModified Null Check (ALL tasks)")

    for col in ["dateAdded", "dateModified"]:
        null_count = conn.execute(f"SELECT COUNT(*) FROM Task WHERE {col} IS NULL").fetchone()[0]
        status = "PASS - never null" if null_count == 0 else f"FAIL - {null_count} nulls found!"
        print(f"  {col}: {status}")

    # -----------------------------------------------------------------------
    # 5. Verify dateDue/dateToStart/datePlanned are always text
    # -----------------------------------------------------------------------
    section("5. Direct Date Columns — Expected: text (naive datetime strings)")

    for col in DIRECT_TEXT_COLUMNS:
        types = type_results.get(col, [])
        non_text = [(t, c) for t, c in types if t != "text"]
        all_text = len(non_text) == 0 and len(types) > 0
        total_non_null = sum(c for _, c in types)

        if len(types) == 0:
            print(f"  {col}: (no non-NULL values to check)")
        elif all_text:
            print(f"  {col}: PASS — all {total_non_null} non-NULL values are 'text'")
        else:
            print(f"  {col}: MIXED TYPES!")
            for t, c in types:
                print(f"    {t}: {c}")

        # Show sample values
        rows = conn.execute(f"SELECT {col} FROM Task WHERE {col} IS NOT NULL LIMIT 3").fetchall()
        if rows:
            print(f"    Samples: {[r[0] for r in rows]}")
        print()

    # -----------------------------------------------------------------------
    # 6. Verify effective* columns are always real (CF epoch floats)
    # -----------------------------------------------------------------------
    section("6. Effective Date Columns — Expected: real (CF epoch floats)")

    for col in EFFECTIVE_REAL_COLUMNS:
        types = type_results.get(col, [])
        non_real = [(t, c) for t, c in types if t != "real"]
        all_real = len(non_real) == 0 and len(types) > 0
        total_non_null = sum(c for _, c in types)

        if len(types) == 0:
            print(f"  {col}: (no non-NULL values to check)")
        elif all_real:
            print(f"  {col}: PASS — all {total_non_null} non-NULL values are 'real'")
        else:
            print(f"  {col}: MIXED TYPES!")
            for t, c in types:
                print(f"    {t}: {c}")

        # Show sample values converted to datetime
        rows = conn.execute(f"SELECT {col} FROM Task WHERE {col} IS NOT NULL LIMIT 3").fetchall()
        if rows:
            samples = []
            for r in rows:
                raw = r[0]
                converted = format_date(cf_to_datetime(raw))
                samples.append(f"{raw} → {converted}")
            print("    Samples:")
            for s in samples:
                print(f"      {s}")
        print()

    # -----------------------------------------------------------------------
    # 7. dateAdded and dateModified type check
    # -----------------------------------------------------------------------
    section("7. dateAdded / dateModified — What type are they?")

    for col in ["dateAdded", "dateModified"]:
        types = type_results.get(col, [])
        print(f"  {col}:")
        for t, c in types:
            print(f"    typeof = '{t}': {c} values")

        # Show samples with both raw and (if real) converted values
        rows = conn.execute(f"SELECT {col} FROM Task WHERE {col} IS NOT NULL LIMIT 3").fetchall()
        if rows:
            print("    Samples:")
            for r in rows:
                raw = r[0]
                # Try CF conversion
                converted = cf_to_datetime(raw)
                if converted and 2000 <= converted.year <= 2030:
                    print(f"      {raw} → {format_date(converted)} (CF epoch)")
                else:
                    print(f"      {raw} (raw value)")
        print()

    # -----------------------------------------------------------------------
    # 8. Summary
    # -----------------------------------------------------------------------
    section("8. Summary — Key Findings for SQL Query Design")

    # Determine types for summary
    date_added_type = type_results.get("dateAdded", [])
    date_modified_type = type_results.get("dateModified", [])

    print("  Storage format by column group:")
    print()

    # Direct dates
    print("  DIRECT DATES (dateDue, dateToStart, datePlanned):")
    all_text = all(
        all(t == "text" for t, _ in type_results.get(col, []))
        for col in DIRECT_TEXT_COLUMNS
        if type_results.get(col, [])
    )
    if all_text:
        print("    Format: text (naive datetime strings, e.g. '2026-04-01T10:00:00.000')")
        print("    SQL comparison: string comparison works (ISO 8601 sorts correctly)")
    else:
        print("    Format: MIXED — review section 5 above")
    print()

    # Effective dates
    print("  EFFECTIVE DATES (effectiveDateDue, effectiveDateToStart, etc.):")
    all_real = all(
        all(t == "real" for t, _ in type_results.get(col, []))
        for col in EFFECTIVE_REAL_COLUMNS
        if type_results.get(col, [])
    )
    if all_real:
        print("    Format: real (CF epoch floats, seconds since 2001-01-01)")
        print("    SQL comparison: numeric comparison against cf_now()")
    else:
        print("    Format: MIXED — review section 6 above")
    print()

    # dateAdded / dateModified
    print("  METADATA DATES (dateAdded, dateModified):")
    da_types = set(t for t, _ in date_added_type)
    dm_types = set(t for t, _ in date_modified_type)
    print(f"    dateAdded types: {da_types}")
    print(f"    dateModified types: {dm_types}")
    if da_types == {"real"} and dm_types == {"real"}:
        print("    Format: real (CF epoch floats) — use numeric comparison")
    elif da_types == {"text"} and dm_types == {"text"}:
        print("    Format: text (datetime strings) — use string comparison")
    else:
        print("    Format: review section 7 above for details")
    print()

    # Null safety
    print("  NULL SAFETY:")
    for col in ["dateAdded", "dateModified"]:
        null_count = conn.execute(f"SELECT COUNT(*) FROM Task WHERE {col} IS NULL").fetchone()[0]
        print(f"    {col}: {'NEVER NULL' if null_count == 0 else f'{null_count} NULLs!'}")
    print()

    print("  IMPLICATION FOR v1.3.2:")
    print("    - effectiveDateDue/ToStart/Planned/Completed/Hidden → compare as real (CF float)")
    print("    - dateAdded/dateModified → check type above, then use appropriate comparison")
    print("    - dateDue/dateToStart/datePlanned → compare as text (ISO 8601 string)")
    print()

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
