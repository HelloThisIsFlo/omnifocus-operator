#!/usr/bin/env python3
"""
Flag Equivalence Tests: dueSoon & blockedByFutureStartDate

Tests whether OmniFocus SQLite cache flags can be reproduced from
raw date columns:
  - dueSoon=1  ↔  effectiveDateDue within some threshold of now
  - blockedByFutureStartDate=1  ↔  effectiveDateToStart > now

Also scans the Setting table for the due-soon threshold config.

Safety: READ-ONLY. Opens database with ?mode=ro URI. No writes.

Usage: python test_flag_equivalences.py
"""

import plistlib
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

    print("Flag Equivalence Tests: dueSoon & blockedByFutureStartDate")
    print("==========================================================")
    print(f"Database: {SQLITE_DB}")
    print(f"Now (UTC): {now_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Now (CF):  {now_cf:.0f}")

    # ===================================================================
    # 1. dueSoon 4-quadrant matrix at multiple thresholds
    # ===================================================================
    section("1. dueSoon 4-Quadrant Matrix at Multiple Thresholds")

    thresholds_hours = [1, 2, 6, 12, 24, 48]

    print(
        f"  {'Threshold':>10}  {'Agree-In':>10}  {'Flag,Out':>10}  {'NoFlag,In':>10}  {'Agree-Out':>10}"
    )
    print(f"  {'':>10}  {'(dueSn=1':>10}  {'(dueSn=1':>10}  {'(dueSn=0':>10}  {'(dueSn=0':>10}")
    print(f"  {'':>10}  {'due<=thr)':>10}  {'due>thr)':>10}  {'due<=thr)':>10}  {'due>thr)':>10}")
    print(f"  {'-' * 10}  {'-' * 10}  {'-' * 10}  {'-' * 10}  {'-' * 10}")

    for hours in thresholds_hours:
        threshold_cf = now_cf + (hours * 3600)

        # Q1: dueSoon=1 AND effectiveDateDue <= threshold (agreement — inside window)
        q1 = conn.execute(
            """
            SELECT COUNT(*) FROM Task
            WHERE dateCompleted IS NULL
              AND dueSoon = 1
              AND effectiveDateDue IS NOT NULL
              AND effectiveDateDue <= ?
        """,
            (threshold_cf,),
        ).fetchone()[0]

        # Q2: dueSoon=1 AND effectiveDateDue > threshold (flag set but outside window)
        q2 = conn.execute(
            """
            SELECT COUNT(*) FROM Task
            WHERE dateCompleted IS NULL
              AND dueSoon = 1
              AND effectiveDateDue IS NOT NULL
              AND effectiveDateDue > ?
        """,
            (threshold_cf,),
        ).fetchone()[0]

        # Also count dueSoon=1 with no due date
        q2_null = conn.execute("""
            SELECT COUNT(*) FROM Task
            WHERE dateCompleted IS NULL
              AND dueSoon = 1
              AND effectiveDateDue IS NULL
        """).fetchone()[0]

        # Q3: dueSoon=0 AND effectiveDateDue <= threshold (inside window but flag not set)
        # Exclude overdue tasks (effectiveDateDue < now) since dueSoon might not cover those
        q3 = conn.execute(
            """
            SELECT COUNT(*) FROM Task
            WHERE dateCompleted IS NULL
              AND (dueSoon = 0 OR dueSoon IS NULL)
              AND effectiveDateDue IS NOT NULL
              AND effectiveDateDue <= ?
        """,
            (threshold_cf,),
        ).fetchone()[0]

        # Q4: dueSoon=0 AND effectiveDateDue > threshold (agreement — both say not soon)
        q4 = conn.execute(
            """
            SELECT COUNT(*) FROM Task
            WHERE dateCompleted IS NULL
              AND (dueSoon = 0 OR dueSoon IS NULL)
              AND effectiveDateDue IS NOT NULL
              AND effectiveDateDue > ?
        """,
            (threshold_cf,),
        ).fetchone()[0]

        label = f"{hours}h"
        extra = f" (+{q2_null} null)" if q2_null > 0 else ""
        print(f"  {label:>10}  {q1:>10}  {q2:>10}{extra}  {q3:>10}  {q4:>10}")

    # ===================================================================
    # 2. dueSoon threshold binary search
    # ===================================================================
    section("2. dueSoon Threshold Binary Search")

    # Farthest-future dueSoon=1 task
    farthest = conn.execute("""
        SELECT persistentIdentifier, name, effectiveDateDue
        FROM Task
        WHERE dateCompleted IS NULL
          AND dueSoon = 1
          AND effectiveDateDue IS NOT NULL
        ORDER BY effectiveDateDue DESC
        LIMIT 1
    """).fetchone()

    # Nearest non-dueSoon task with future due date
    nearest_not = conn.execute(
        """
        SELECT persistentIdentifier, name, effectiveDateDue
        FROM Task
        WHERE dateCompleted IS NULL
          AND (dueSoon = 0 OR dueSoon IS NULL)
          AND effectiveDateDue IS NOT NULL
          AND effectiveDateDue > ?
        ORDER BY effectiveDateDue ASC
        LIMIT 1
    """,
        (now_cf,),
    ).fetchone()

    if farthest:
        far_dt = cf_to_datetime(farthest["effectiveDateDue"])
        far_delta = far_dt - now_dt if far_dt else None
        print("  Farthest dueSoon=1 task:")
        print(f"    ID:   {farthest['persistentIdentifier']}")
        print(f"    Name: {(farthest['name'] or '(unnamed)')[:60]}")
        print(f"    Due:  {format_date(far_dt)}  (in {far_delta})")
    else:
        print("  No dueSoon=1 tasks with effectiveDateDue found.")

    print()

    if nearest_not:
        near_dt = cf_to_datetime(nearest_not["effectiveDateDue"])
        near_delta = near_dt - now_dt if near_dt else None
        print("  Nearest dueSoon=0 task (future due):")
        print(f"    ID:   {nearest_not['persistentIdentifier']}")
        print(f"    Name: {(nearest_not['name'] or '(unnamed)')[:60]}")
        print(f"    Due:  {format_date(near_dt)}  (in {near_delta})")
    else:
        print("  No dueSoon=0 tasks with future effectiveDateDue found.")

    print()

    if farthest and nearest_not:
        far_dt = cf_to_datetime(farthest["effectiveDateDue"])
        near_dt = cf_to_datetime(nearest_not["effectiveDateDue"])
        if far_dt and near_dt:
            gap = near_dt - far_dt
            threshold_lower = far_dt - now_dt
            threshold_upper = near_dt - now_dt
            print("  => Threshold is bracketed between:")
            print(f"     Lower bound: {threshold_lower}  (farthest dueSoon=1)")
            print(f"     Upper bound: {threshold_upper}  (nearest dueSoon=0)")
            print(f"     Gap:         {gap}")
            # Express in hours
            lower_h = threshold_lower.total_seconds() / 3600
            upper_h = threshold_upper.total_seconds() / 3600
            print(f"     Lower (hours): {lower_h:.1f}h")
            print(f"     Upper (hours): {upper_h:.1f}h")

    # ===================================================================
    # 3. dueSoon vs overdue overlap
    # ===================================================================
    section("3. dueSoon vs Overdue Overlap")

    both = conn.execute("""
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND dueSoon = 1
          AND overdue = 1
    """).fetchone()[0]

    due_soon_only = conn.execute("""
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND dueSoon = 1
          AND (overdue = 0 OR overdue IS NULL)
    """).fetchone()[0]

    overdue_only = conn.execute("""
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND overdue = 1
          AND (dueSoon = 0 OR dueSoon IS NULL)
    """).fetchone()[0]

    print(f"  dueSoon=1 AND overdue=1:   {both}")
    print(f"  dueSoon=1 AND overdue=0:   {due_soon_only}  (truly upcoming)")
    print(f"  overdue=1 AND dueSoon=0:   {overdue_only}  (overdue but not 'soon')")
    print()

    if both > 0:
        print("  => dueSoon INCLUDES overdue tasks")
    else:
        print("  => dueSoon does NOT include overdue tasks")

    if overdue_only > 0:
        print(f"  => {overdue_only} overdue tasks are NOT marked dueSoon")
    elif both > 0:
        print("  => All overdue tasks are also marked dueSoon (superset)")

    # ===================================================================
    # 4. blockedByFutureStartDate 4-quadrant matrix
    # ===================================================================
    section("4. blockedByFutureStartDate 4-Quadrant Matrix")

    # Q1: flag=1 AND effectiveDateToStart > now (agreement)
    bq1 = conn.execute(
        """
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND blockedByFutureStartDate = 1
          AND effectiveDateToStart IS NOT NULL
          AND effectiveDateToStart > ?
    """,
        (now_cf,),
    ).fetchone()[0]

    # Q2: flag=1 AND (effectiveDateToStart <= now OR IS NULL) — flag set but date passed/missing
    bq2 = conn.execute(
        """
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND blockedByFutureStartDate = 1
          AND (effectiveDateToStart IS NULL OR effectiveDateToStart <= ?)
    """,
        (now_cf,),
    ).fetchone()[0]

    # Q3: flag=0 AND effectiveDateToStart > now — future start but flag not set
    bq3 = conn.execute(
        """
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND (blockedByFutureStartDate = 0 OR blockedByFutureStartDate IS NULL)
          AND effectiveDateToStart IS NOT NULL
          AND effectiveDateToStart > ?
    """,
        (now_cf,),
    ).fetchone()[0]

    # Q4: flag=0 AND (effectiveDateToStart IS NULL OR <= now) — agreement
    bq4 = conn.execute(
        """
        SELECT COUNT(*) FROM Task
        WHERE dateCompleted IS NULL
          AND (blockedByFutureStartDate = 0 OR blockedByFutureStartDate IS NULL)
          AND (effectiveDateToStart IS NULL OR effectiveDateToStart <= ?)
    """,
        (now_cf,),
    ).fetchone()[0]

    print(f"  [Q1] flag=1, startDate > now:          {bq1:>5}  (agreement)")
    print(f"  [Q2] flag=1, startDate <= now or NULL:  {bq2:>5}  (flag set but not future)")
    print(f"  [Q3] flag=0, startDate > now:           {bq3:>5}  (future start, no flag)")
    print(f"  [Q4] flag=0, startDate <= now or NULL:  {bq4:>5}  (agreement)")
    print()

    total_bfs_mismatches = bq2 + bq3
    if total_bfs_mismatches == 0:
        print(
            "  RESULT: Perfect equivalence — blockedByFutureStartDate=1 ↔ effectiveDateToStart > now"
        )
    else:
        print(f"  RESULT: {total_bfs_mismatches} mismatches found")

    # Sample mismatches: Q2 — flag=1 but start date passed or missing
    if bq2 > 0:
        print()
        print("  --- Samples: flag=1 but startDate <= now or NULL (up to 5) ---")
        rows = conn.execute(
            """
            SELECT persistentIdentifier, name, blockedByFutureStartDate, blocked,
                   effectiveDateToStart, dateToStart
            FROM Task
            WHERE dateCompleted IS NULL
              AND blockedByFutureStartDate = 1
              AND (effectiveDateToStart IS NULL OR effectiveDateToStart <= ?)
            LIMIT 5
        """,
            (now_cf,),
        ).fetchall()
        for r in rows:
            name = (r["name"] or "(unnamed)")[:55]
            eff_start = cf_to_datetime(r["effectiveDateToStart"])
            print(f"    ID: {r['persistentIdentifier']}")
            print(f"    Name: {name}")
            print(
                f"    blockedByFutureStartDate={r['blockedByFutureStartDate']}  blocked={r['blocked']}"
            )
            print(
                f"    effectiveDateToStart={format_date(eff_start)}  dateToStart={r['dateToStart']}"
            )
            print()

    # Sample mismatches: Q3 — future start but flag not set
    if bq3 > 0:
        print()
        print("  --- Samples: startDate > now but flag=0 (up to 5) ---")
        rows = conn.execute(
            """
            SELECT persistentIdentifier, name, blockedByFutureStartDate, blocked,
                   effectiveDateToStart, dateToStart
            FROM Task
            WHERE dateCompleted IS NULL
              AND (blockedByFutureStartDate = 0 OR blockedByFutureStartDate IS NULL)
              AND effectiveDateToStart IS NOT NULL
              AND effectiveDateToStart > ?
            LIMIT 5
        """,
            (now_cf,),
        ).fetchall()
        for r in rows:
            name = (r["name"] or "(unnamed)")[:55]
            eff_start = cf_to_datetime(r["effectiveDateToStart"])
            delta = eff_start - now_dt if eff_start else None
            print(f"    ID: {r['persistentIdentifier']}")
            print(f"    Name: {name}")
            print(
                f"    blockedByFutureStartDate={r['blockedByFutureStartDate']}  blocked={r['blocked']}"
            )
            print(f"    effectiveDateToStart={format_date(eff_start)}  (starts in {delta})")
            print()

    # ===================================================================
    # 5. Setting table scan for due-soon threshold
    # ===================================================================
    section("5. Setting Table Scan for Due-Soon Threshold")

    keywords = ["soon", "due", "threshold", "warning", "horizon"]

    rows = conn.execute("""
        SELECT persistentIdentifier, valueData
        FROM Setting
    """).fetchall()

    print(f"  Total settings: {len(rows)}")
    print()

    found_any = False
    for r in rows:
        pid = r["persistentIdentifier"]
        blob = r["valueData"]

        # Check if persistentIdentifier itself contains keywords
        pid_lower = (pid or "").lower()
        pid_match = any(kw in pid_lower for kw in keywords)

        # Try to decode the plist blob
        decoded = None
        if blob:
            try:
                decoded = plistlib.loads(blob)
            except Exception:
                pass

        # Check if decoded plist contains keywords (search string representation)
        plist_match = False
        if decoded is not None:
            decoded_str = str(decoded).lower()
            plist_match = any(kw in decoded_str for kw in keywords)

        if pid_match or plist_match:
            found_any = True
            print(f"  Setting: {pid}")
            if decoded is not None:
                print(f"  Decoded: {decoded}")
            else:
                print(f"  Raw blob: {blob[:100] if blob else 'empty'}...")
            print()

    if not found_any:
        print("  No settings matched keywords: " + ", ".join(keywords))
        print()
        # Print all setting IDs for reference
        print("  All setting persistentIdentifiers:")
        for r in rows:
            pid = r["persistentIdentifier"]
            blob = r["valueData"]
            decoded = None
            if blob:
                try:
                    decoded = plistlib.loads(blob)
                except Exception:
                    pass
            decoded_preview = str(decoded)[:80] if decoded is not None else "(decode failed)"
            print(f"    {pid}: {decoded_preview}")

    # ===================================================================
    # 6. Summary
    # ===================================================================
    section("6. Summary")

    print("  dueSoon:")
    if farthest and nearest_not:
        far_dt = cf_to_datetime(farthest["effectiveDateDue"])
        near_dt = cf_to_datetime(nearest_not["effectiveDateDue"])
        if far_dt and near_dt:
            lower_h = (far_dt - now_dt).total_seconds() / 3600
            upper_h = (near_dt - now_dt).total_seconds() / 3600
            print(f"    Threshold bracketed: {lower_h:.1f}h - {upper_h:.1f}h from now")
    print(f"    Includes overdue tasks: {'YES' if both > 0 else 'NO'}")
    print(f"    dueSoon=1 AND overdue=1: {both}")
    print(f"    dueSoon=1 AND overdue=0: {due_soon_only}")
    print()

    print("  blockedByFutureStartDate:")
    print(f"    Matches (Q1+Q4):     {bq1 + bq4}")
    print(f"    Mismatches (Q2+Q3):  {total_bfs_mismatches}")
    if total_bfs_mismatches == 0:
        print("    VERDICT: blockedByFutureStartDate=1 ↔ effectiveDateToStart > now")
    elif bq3 > 0 and bq2 == 0:
        print("    VERDICT: blockedByFutureStartDate=1 is SUBSET of effectiveDateToStart > now")
        print(
            "             Some future-start tasks don't have the flag (may depend on 'blocked' status)"
        )
    elif bq2 > 0 and bq3 == 0:
        print("    VERDICT: effectiveDateToStart > now is SUBSET of blockedByFutureStartDate=1")
    else:
        print("    VERDICT: Complex relationship — review mismatches above")

    print()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
