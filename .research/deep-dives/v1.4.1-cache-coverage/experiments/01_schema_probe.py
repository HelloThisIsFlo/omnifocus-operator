"""Experiment 01 — Schema probe for v1.4.1 candidate columns.

Reads OmniFocus SQLite cache in read-only mode. For each of the three
candidate fields, dumps the columns on Task and ProjectInfo and filters
for plausible matches. No schema changes, no writes.

Fields and candidate column patterns:
- completedByChildren: completesWithChildren, completedByChildren,
  completeWhenChildrenComplete
- sequential: sequential, isSequential, actionOrder
- attachments: any column/table with "attach" in the name
"""

from __future__ import annotations

import os
import sqlite3
import sys

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)


def probe() -> None:
    if not os.path.exists(DB_PATH):
        print(f"ABORT: OmniFocus SQLite cache not found at {DB_PATH}")
        sys.exit(1)

    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    try:
        # All tables
        print("=" * 72)
        print("ALL TABLES")
        print("=" * 72)
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        ]
        for t in tables:
            print(f"  {t}")

        # Columns of interest
        for table in ("Task", "ProjectInfo"):
            print()
            print("=" * 72)
            print(f"{table} — full column list")
            print("=" * 72)
            rows = list(conn.execute(f"PRAGMA table_info({table})"))
            for r in rows:
                nullable = "NULL" if r["notnull"] == 0 else "NOT NULL"
                default = f" default={r['dflt_value']}" if r["dflt_value"] is not None else ""
                print(f"  {r['name']:<42} {r['type']:<15} {nullable}{default}")

        # Targeted candidate column filter
        print()
        print("=" * 72)
        print("CANDIDATE COLUMNS — targeted filter")
        print("=" * 72)
        patterns = {
            "completedByChildren": ["completesWith", "completedBy", "completeWhen"],
            "sequential": ["sequential", "actionOrder", "isSequential"],
            "attachments": ["attach"],
        }
        for table in ("Task", "ProjectInfo"):
            print(f"\n[{table}]")
            rows = list(conn.execute(f"PRAGMA table_info({table})"))
            col_names = [r["name"] for r in rows]
            for field, needles in patterns.items():
                matches = [
                    c for c in col_names if any(needle.lower() in c.lower() for needle in needles)
                ]
                label = "(none)" if not matches else ", ".join(matches)
                print(f"  {field:<24} → {label}")

        # Tables with "attach" in name
        print()
        print("=" * 72)
        print("TABLES CONTAINING 'attach' (case-insensitive)")
        print("=" * 72)
        attach_tables = [t for t in tables if "attach" in t.lower()]
        if not attach_tables:
            print("  (no tables with 'attach' in the name)")
        else:
            for t in attach_tables:
                print(f"  {t}")
                for r in conn.execute(f"PRAGMA table_info({t})"):
                    print(f"    {r['name']:<40} {r['type']}")
    finally:
        conn.close()


if __name__ == "__main__":
    probe()
