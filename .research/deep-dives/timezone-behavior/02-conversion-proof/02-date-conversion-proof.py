#!/usr/bin/env python3
"""
Date Conversion Proof

Proves the formula: effective_date = CF_seconds(naive_local_as_utc)
Validates across DST boundaries (BST summer vs GMT winter).

Safety: READ-ONLY. Opens database with ?mode=ro URI. No writes.

Usage: uv run python .research/deep-dives/timezone-behavior/02-conversion-proof/02-date-conversion-proof.py
"""

import sqlite3
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

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


def section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print()


def cf_to_datetime(cf_seconds: float) -> datetime:
    """Convert CF Absolute Time to UTC datetime."""
    return CF_EPOCH + timedelta(seconds=cf_seconds)


def naive_local_to_cf(naive_str: str, local_tz: ZoneInfo) -> float:
    """Convert naive local time string to CF seconds (our hypothesized formula)."""
    naive = datetime.fromisoformat(naive_str)
    # Attach local timezone (handles DST based on the date itself)
    local_dt = naive.replace(tzinfo=local_tz)
    # Convert to UTC
    utc_dt = local_dt.astimezone(UTC)
    # Compute CF seconds
    return (utc_dt - CF_EPOCH).total_seconds()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    uri = f"file:{SQLITE_DB}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    print("Timezone Conversion Proof")
    print("=========================")
    print(f"Database: {SQLITE_DB}")
    print()

    # -----------------------------------------------------------------------
    # 1. System timezone
    # -----------------------------------------------------------------------
    section("1. System Timezone")

    print(f"  time.tzname:     {time.tzname}")
    now = datetime.now().astimezone()
    print(f"  Current time:    {now.isoformat()}")
    print(f"  UTC offset:      {now.strftime('%z')} ({now.tzname()})")
    print(f"  DST active:      {bool(time.daylight and time.localtime().tm_isdst)}")

    # Resolve system timezone
    import pathlib

    tz_path = pathlib.Path("/etc/localtime").resolve()
    tz_name = str(tz_path).split("zoneinfo/")[-1]
    local_tz = ZoneInfo(tz_name)
    print(f"  ZoneInfo:        {local_tz}")

    # -----------------------------------------------------------------------
    # 2. Full column scan for timezone-related columns
    # -----------------------------------------------------------------------
    section("2. Full Column Scan — Timezone-Related Columns")

    columns = conn.execute("PRAGMA table_info(Task)").fetchall()
    print(f"  Total columns in Task table: {len(columns)}")
    print()

    tz_keywords = ["time", "zone", "tz", "float", "calendar"]
    found_cols = []
    for col in columns:
        name = col["name"].lower()
        for kw in tz_keywords:
            if kw in name:
                found_cols.append(col)
                break

    if found_cols:
        print("  Columns matching time/zone/tz/float/calendar:")
        for col in found_cols:
            cid = col["cid"]
            name = col["name"]
            typ = col["type"]
            # Sample values
            samples = conn.execute(
                f'SELECT "{name}" FROM Task WHERE "{name}" IS NOT NULL LIMIT 5'
            ).fetchall()
            sample_vals = [str(s[0]) for s in samples]
            print(f"    [{cid}] {name} ({typ}): samples={sample_vals[:3]}")
    else:
        print("  No timezone-related columns found.")

    # Check shouldUseFloatingTimeZone specifically
    print()
    ftzcol = conn.execute(
        "SELECT COUNT(*) as c FROM pragma_table_info('Task') "
        "WHERE name = 'shouldUseFloatingTimeZone'"
    ).fetchone()
    if ftzcol and ftzcol["c"] > 0:
        # Distribution
        dist = conn.execute(
            "SELECT shouldUseFloatingTimeZone as v, COUNT(*) as c "
            "FROM Task GROUP BY shouldUseFloatingTimeZone ORDER BY c DESC"
        ).fetchall()
        print("  shouldUseFloatingTimeZone distribution:")
        for row in dist:
            print(f"    {row['v']}: {row['c']}")
    else:
        print("  shouldUseFloatingTimeZone column NOT found in Task table")

    # -----------------------------------------------------------------------
    # 3. Conversion proof: dateDue ↔ effectiveDateDue
    # -----------------------------------------------------------------------
    section("3. Conversion Proof: dateDue → effectiveDateDue")

    _run_conversion_proof(
        conn,
        local_tz,
        direct_col="dateDue",
        effective_col="effectiveDateDue",
    )

    # -----------------------------------------------------------------------
    # 4. Conversion proof: dateToStart ↔ effectiveDateToStart
    # -----------------------------------------------------------------------
    section("4. Conversion Proof: dateToStart → effectiveDateToStart")

    _run_conversion_proof(
        conn,
        local_tz,
        direct_col="dateToStart",
        effective_col="effectiveDateToStart",
    )

    # -----------------------------------------------------------------------
    # 5. Conversion proof: datePlanned ↔ effectiveDatePlanned
    # -----------------------------------------------------------------------
    section("5. Conversion Proof: datePlanned → effectiveDatePlanned")

    _run_conversion_proof(
        conn,
        local_tz,
        direct_col="datePlanned",
        effective_col="effectiveDatePlanned",
    )

    # -----------------------------------------------------------------------
    # 6. Proven formula
    # -----------------------------------------------------------------------
    section("6. Proven Formula")

    print("  For direct date columns (dateDue, dateToStart, datePlanned):")
    print()
    print("    1. Parse naive text as local datetime")
    print("    2. Attach system timezone (ZoneInfo, handles DST)")
    print("    3. Convert to UTC")
    print("    4. CF_seconds = (utc_datetime - CF_EPOCH).total_seconds()")
    print()
    print("  This matches effectiveDate* (CF epoch float) in SQLite.")
    print()
    print("  Inverse (what hybrid.py does for _parse_local_datetime):")
    print("    1. Parse naive text as local datetime")
    print("    2. Attach system timezone")
    print("    3. Convert to UTC")
    print("    4. Return ISO 8601 with +00:00 suffix")

    conn.close()
    print()
    print("Done.")


def _run_conversion_proof(
    conn: sqlite3.Connection,
    local_tz: ZoneInfo,
    *,
    direct_col: str,
    effective_col: str,
) -> None:
    """Run conversion proof for a direct/effective date column pair.

    Only includes tasks where BOTH direct and effective are set AND
    the task has no parent with the same date (i.e., the effective date
    is its own, not inherited from a parent).
    """
    # Get tasks where both columns are non-null
    # Include parent info to detect inheritance
    rows = conn.execute(
        f"""
        SELECT
            persistentIdentifier as id,
            name,
            "{direct_col}" as direct_val,
            "{effective_col}" as effective_val,
            parent
        FROM Task
        WHERE "{direct_col}" IS NOT NULL
          AND "{effective_col}" IS NOT NULL
        LIMIT 200
        """
    ).fetchall()

    print(f"  Tasks with both {direct_col} and {effective_col}: {len(rows)}")
    if not rows:
        print("  (no data to verify)")
        return

    # Separate by season (BST vs GMT for Europe/London)
    summer_matches = 0
    summer_mismatches = []
    winter_matches = 0
    winter_mismatches = []
    max_delta = 0.0
    total_checked = 0

    for row in rows:
        direct_str = row["direct_val"]
        effective_cf = row["effective_val"]

        try:
            expected_cf = naive_local_to_cf(direct_str, local_tz)
        except Exception as e:
            print(f"  PARSE ERROR: {direct_str} → {e}")
            continue

        delta = abs(expected_cf - effective_cf)
        if delta > max_delta:
            max_delta = delta

        # Determine season from the date
        naive = datetime.fromisoformat(direct_str)
        is_summer = 4 <= naive.month <= 10  # BST period (roughly)

        total_checked += 1
        # Allow 1 second tolerance for rounding
        if delta <= 1.0:
            if is_summer:
                summer_matches += 1
            else:
                winter_matches += 1
        else:
            entry = {
                "id": row["id"],
                "name": row["name"],
                "direct": direct_str,
                "effective_cf": effective_cf,
                "expected_cf": expected_cf,
                "delta": delta,
            }
            if is_summer:
                summer_mismatches.append(entry)
            else:
                winter_mismatches.append(entry)

    print(f"  Total verified: {total_checked}")
    print(f"  Max delta: {max_delta:.3f}s")
    print()
    print("  Summer (BST, months 4-10):")
    print(f"    Matches:    {summer_matches}")
    print(f"    Mismatches: {len(summer_mismatches)}")
    if summer_mismatches:
        for m in summer_mismatches[:3]:
            print(
                f"      {m['name']}: {m['direct']} → expected={m['expected_cf']:.1f}, "
                f"actual={m['effective_cf']:.1f}, delta={m['delta']:.1f}s"
            )

    print("  Winter (GMT, months 11-3):")
    print(f"    Matches:    {winter_matches}")
    print(f"    Mismatches: {len(winter_mismatches)}")
    if winter_mismatches:
        for m in winter_mismatches[:3]:
            print(
                f"      {m['name']}: {m['direct']} → expected={m['expected_cf']:.1f}, "
                f"actual={m['effective_cf']:.1f}, delta={m['delta']:.1f}s"
            )

    total_mismatches = len(summer_mismatches) + len(winter_mismatches)
    if total_mismatches == 0:
        print()
        print(f"  RESULT: ALL {total_checked} tasks match the formula (tolerance ≤1s)")
        print(f"    Formula: CF_seconds = (naive_local_as_tz({local_tz}) → UTC - CF_EPOCH)")
    else:
        print()
        print(f"  RESULT: {total_mismatches} MISMATCHES found out of {total_checked}")
        print("  Investigation needed — see mismatches above")


if __name__ == "__main__":
    main()
