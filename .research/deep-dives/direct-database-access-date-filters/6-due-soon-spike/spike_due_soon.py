#!/usr/bin/env python3
"""
DueSoon Spike: Map OmniFocus "due soon" settings to database behavior.

Reads (READ-ONLY) the OmniFocus SQLite cache to answer:
  1. What DueSoonInterval value corresponds to each UI setting?
  2. Is "today" calendar-aligned (midnight) or rolling (24h from now)?
  3. Does changing the setting update SQLite immediately?

Usage:
  python spike_due_soon.py          # full report
  python spike_due_soon.py --quick  # just settings + dueSoon flags

Safety: READ-ONLY. Opens database with ?mode=ro URI. No writes.
"""

import plistlib
import sqlite3
import sys
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

CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)

SPIKE_PREFIX = "[SPIKE-DS]"

# Known task IDs from this spike (fallback if name search fails)
SPIKE_TASK_IDS = [
    "i6dO-XHQYFh",  # Due 23:59 tonight (pre-midnight)
    "iMJbpEH3j5B",  # Due 00:01 tomorrow (post-midnight)
    "o2oTf6krEEm",  # Due +6h
    "fbIYQTobdyw",  # Due +20h
    "jgm_oK9TjVI",  # Due +25h
    "jTb8ITw-Hwh",  # Due +49h
    "n4qVoA27-lk",  # Due +73h
    "lVkCjgoGjXX",  # Due +169h
]


def cf_to_datetime(cf_timestamp):
    if cf_timestamp is None:
        return None
    return CF_EPOCH + timedelta(seconds=float(cf_timestamp))


def now_as_cf() -> float:
    return (datetime.now(UTC) - CF_EPOCH).total_seconds()


def hours_from_now(cf_timestamp) -> str:
    if cf_timestamp is None:
        return "n/a"
    dt = cf_to_datetime(cf_timestamp)
    delta = dt - datetime.now(UTC)
    hours = delta.total_seconds() / 3600
    if hours < 0:
        return f"{hours:.1f}h (OVERDUE)"
    return f"+{hours:.1f}h"


def format_dt(cf_timestamp) -> str:
    if cf_timestamp is None:
        return "NULL"
    dt = cf_to_datetime(cf_timestamp)
    # Show in local time (BST)
    local = dt.astimezone()
    return local.strftime("%a %b %d %H:%M %Z")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    quick = "--quick" in sys.argv

    conn = sqlite3.connect(f"file:{SQLITE_DB}?mode=ro", uri=True)
    now_cf = now_as_cf()
    now_dt = datetime.now(UTC).astimezone()

    print("=" * 72)
    print(f"DueSoon Spike — {now_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 72)

    # --- Settings ---
    print("\n--- Settings ---")
    for setting_id in [
        "DueSoonInterval",
        "DueSoonGranularity",
        "DefaultDueTime",
        "DefaultStartTime",
    ]:
        row = conn.execute(
            "SELECT valueData FROM Setting WHERE persistentIdentifier = ?",
            (setting_id,),
        ).fetchone()
        if row:
            try:
                val = plistlib.loads(row[0])
                extra = ""
                if setting_id == "DueSoonInterval" and isinstance(val, (int, float)):
                    hours = val / 3600
                    days = val / 86400
                    extra = f"  ({hours:.0f}h / {days:.1f}d)"
                print(f"  {setting_id}: {val!r}{extra}")
            except Exception as e:
                print(f"  {setting_id}: (decode error: {e})")
        else:
            print(f"  {setting_id}: NOT FOUND")

    # --- Spike Tasks ---
    print("\n--- Spike Tasks (dueSoon column from SQLite) ---")
    print(f"  {'Task':<50} {'Due (local)':<22} {'Offset':<14} {'dueSoon'}")
    print(f"  {'-' * 50} {'-' * 22} {'-' * 14} {'-' * 7}")

    # Find by name prefix first, fall back to IDs
    rows = conn.execute(
        """
        SELECT name, effectiveDateDue, dueSoon, persistentIdentifier
        FROM Task
        WHERE name LIKE ?
        ORDER BY effectiveDateDue
        """,
        (f"{SPIKE_PREFIX}%",),
    ).fetchall()

    if not rows:
        # Fallback to known IDs
        placeholders = ",".join("?" for _ in SPIKE_TASK_IDS)
        rows = conn.execute(
            f"""
            SELECT name, effectiveDateDue, dueSoon, persistentIdentifier
            FROM Task
            WHERE persistentIdentifier IN ({placeholders})
            ORDER BY effectiveDateDue
            """,
            SPIKE_TASK_IDS,
        ).fetchall()

    if not rows:
        print("  (no spike tasks found — were they deleted?)")
    else:
        due_soon_count = 0
        for name, eff_due, due_soon, pid in rows:
            short_name = name.replace(SPIKE_PREFIX + " ", "")
            flag = "YES" if due_soon else "no"
            if due_soon:
                due_soon_count += 1
            print(
                f"  {short_name:<50} {format_dt(eff_due):<22} {hours_from_now(eff_due):<14} {flag}"
            )
        print(f"\n  Summary: {due_soon_count}/{len(rows)} tasks flagged dueSoon")

    if not quick:
        # --- Boundary Analysis ---
        print("\n--- Boundary Analysis ---")
        print(f"  Current time (CF): {now_cf:.0f}")
        print(f"  Current time:      {now_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        # Find the exact dueSoon boundary by looking at ALL tasks
        boundary_rows = conn.execute(
            """
            SELECT effectiveDateDue, dueSoon
            FROM Task
            WHERE effectiveDateDue IS NOT NULL
              AND dateCompleted IS NULL
              AND effectiveDateHidden IS NULL
            ORDER BY effectiveDateDue
            """,
        ).fetchall()

        # Find the transition point: last dueSoon=1 and first dueSoon=0
        last_due_soon = None
        first_not_due_soon = None
        for eff_due, ds in boundary_rows:
            if eff_due < now_cf:
                continue  # skip overdue
            if ds:
                last_due_soon = eff_due
            elif last_due_soon is not None and first_not_due_soon is None:
                first_not_due_soon = eff_due

        if last_due_soon and first_not_due_soon:
            last_dt = cf_to_datetime(last_due_soon)
            first_dt = cf_to_datetime(first_not_due_soon)
            gap_hours = (first_not_due_soon - last_due_soon) / 3600
            threshold_from_now_low = (last_due_soon - now_cf) / 3600
            threshold_from_now_high = (first_not_due_soon - now_cf) / 3600
            print(
                f"\n  Last task with dueSoon=1:    {format_dt(last_due_soon)} ({hours_from_now(last_due_soon)})"
            )
            print(
                f"  First task with dueSoon=0:   {format_dt(first_not_due_soon)} ({hours_from_now(first_not_due_soon)})"
            )
            print(f"  Gap between them:            {gap_hours:.1f}h")
            print(
                f"  Threshold bracketed at:      {threshold_from_now_low:.1f}h — {threshold_from_now_high:.1f}h from now"
            )

            # Check if midnight falls in the bracket
            midnight_local = now_dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
                days=1
            )
            midnight_cf = (midnight_local.astimezone(UTC) - CF_EPOCH).total_seconds()
            hours_to_midnight = (midnight_cf - now_cf) / 3600
            print(
                f"\n  Next midnight (local):       {midnight_local.strftime('%Y-%m-%d %H:%M %Z')} ({hours_to_midnight:.1f}h from now)"
            )

            if threshold_from_now_low < hours_to_midnight < threshold_from_now_high:
                print("  ** Midnight falls INSIDE the bracket — could be calendar-aligned! **")
            elif hours_to_midnight < threshold_from_now_low:
                print(
                    "  ** Midnight is BEFORE the bracket — threshold is time-based, not calendar **"
                )
            else:
                print("  ** Midnight is AFTER the bracket — inconclusive from this run **")
        else:
            print("  (could not determine boundary — not enough future tasks with mixed dueSoon)")

    conn.close()
    print("\n" + "=" * 72)
    print("Re-run after changing OmniFocus Preferences > Due Soon setting")
    print("=" * 72)


if __name__ == "__main__":
    main()
