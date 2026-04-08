#!/usr/bin/env python3
"""
Inbox Equivalence Validation

Checks whether `containingProjectInfo IS NULL` and `effectiveInInbox = 1`
always agree across all tasks in the OmniFocus SQLite cache.

This validates our query_builder.py approach: we use containingProjectInfo
as the inbox signal instead of inInbox or effectiveInInbox.

Read-only — no writes, no OmniFocus interaction.

Usage: python validate_inbox_equivalence.py
"""

import sqlite3
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    conn = sqlite3.connect(f"file:{SQLITE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    # Fetch all tasks with the three inbox-related columns
    rows = conn.execute(
        """
        SELECT
            persistentIdentifier,
            name,
            inInbox,
            effectiveInInbox,
            containingProjectInfo,
            parent
        FROM Task
        """
    ).fetchall()
    conn.close()

    total = len(rows)
    print("Inbox Equivalence Validation")
    print("============================")
    print(f"Total tasks: {total}")
    print()

    # Classify each task
    contradictions = []
    stats = {
        "both_inbox": 0,  # effectiveInInbox=1 AND containingProject IS NULL
        "both_not_inbox": 0,  # effectiveInInbox=0 AND containingProject IS NOT NULL
        "effective_only": 0,  # effectiveInInbox=1 BUT containingProject IS NOT NULL
        "containing_only": 0,  # effectiveInInbox=0 BUT containingProject IS NULL
    }

    # Also track raw inInbox vs effectiveInInbox divergences
    raw_vs_effective = {
        "raw_1_effective_1": 0,
        "raw_0_effective_1": 0,  # subtask case — the original bug
        "raw_1_effective_0": 0,  # shouldn't happen
        "raw_0_effective_0": 0,
    }

    for row in rows:
        effective = bool(row["effectiveInInbox"])
        containing_null = row["containingProjectInfo"] is None
        raw = bool(row["inInbox"])

        # Main equivalence check
        if effective and containing_null:
            stats["both_inbox"] += 1
        elif not effective and not containing_null:
            stats["both_not_inbox"] += 1
        elif effective and not containing_null:
            stats["effective_only"] += 1
            contradictions.append(row)
        else:  # not effective and containing_null
            stats["containing_only"] += 1
            contradictions.append(row)

        # Raw vs effective tracking
        key = f"raw_{int(raw)}_effective_{int(effective)}"
        raw_vs_effective[key] += 1

    # --- Report ---

    print("Equivalence: effectiveInInbox vs containingProjectInfo IS NULL")
    print("--------------------------------------------------------------")
    print(f"  Both agree inbox:     {stats['both_inbox']}")
    print(f"  Both agree not inbox: {stats['both_not_inbox']}")
    print(f"  effective=1 but has project (CONTRADICTION): {stats['effective_only']}")
    print(f"  effective=0 but no project  (CONTRADICTION): {stats['containing_only']}")
    print()

    print("Raw inInbox vs effectiveInInbox")
    print("-------------------------------")
    print(f"  raw=1, effective=1: {raw_vs_effective['raw_1_effective_1']}")
    print(
        f"  raw=0, effective=1: {raw_vs_effective['raw_0_effective_1']}  (subtasks — the original bug)"
    )
    print(f"  raw=1, effective=0: {raw_vs_effective['raw_1_effective_0']}  (should not happen)")
    print(f"  raw=0, effective=0: {raw_vs_effective['raw_0_effective_0']}")
    print()

    if contradictions:
        print(f"CONTRADICTIONS FOUND: {len(contradictions)}")
        print()
        for row in contradictions[:20]:  # cap output
            print(f"  ID: {row['persistentIdentifier']}")
            print(f"    name: {row['name']}")
            print(f"    inInbox={row['inInbox']}  effectiveInInbox={row['effectiveInInbox']}")
            print(f"    containingProjectInfo={row['containingProjectInfo']}")
            print(f"    parent={row['parent']}")
            print()
        if len(contradictions) > 20:
            print(f"  ... and {len(contradictions) - 20} more")
    else:
        print("NO CONTRADICTIONS — containingProjectInfo IS NULL ≡ effectiveInInbox")
        print()
        print("Conclusion: Our query_builder approach (containingProjectInfo IS NULL)")
        print("is equivalent to effectiveInInbox for all tasks in this database.")


if __name__ == "__main__":
    main()
