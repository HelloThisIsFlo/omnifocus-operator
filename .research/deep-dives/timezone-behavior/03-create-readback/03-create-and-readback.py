#!/usr/bin/env python3
"""
Create & Readback — Timezone Format Experiment

Creates test tasks with various date formats via RealBridge, then reads back
from both bridge (snapshot) and SQLite to see how OmniFocus normalizes each.

WRITES to OmniFocus database. For manual UAT only (SAFE-01/02).

Usage: uv run python .research/deep-dives/timezone-behavior/03-create-readback/03-create-and-readback.py
"""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from omnifocus_operator.bridge.real import DEFAULT_IPC_DIR, RealBridge

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

# Test tasks to create
TEST_TASKS = [
    {
        "label": "A",
        "name": "TZ-DD-A: UTC summer",
        "dueDate": "2026-07-15T09:00:00Z",
        "description": "Explicit UTC during BST",
    },
    {
        "label": "B",
        "name": "TZ-DD-B: UTC winter",
        "dueDate": "2026-12-15T09:00:00Z",
        "description": "Explicit UTC during GMT",
    },
    {
        "label": "C",
        "name": "TZ-DD-C: Naive no-Z",
        "dueDate": "2026-07-15T09:00:00",
        "description": "JS new Date() on naive string",
    },
    {
        "label": "D",
        "name": "TZ-DD-D: Date-only",
        "dueDate": "2026-07-15",
        "description": "JS new Date('YYYY-MM-DD') quirk (UTC midnight?)",
    },
    {
        "label": "E",
        "name": "TZ-DD-E: Offset +0530",
        "dueDate": "2026-07-15T09:00:00+05:30",
        "description": "Non-local explicit offset",
    },
    {
        "label": "F",
        "name": "TZ-DD-F: Edit tz change",
        "dueDate": "2026-07-15T09:00:00Z",
        "description": "Create with Z, then edit to +05:30",
    },
]


def section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print()


def cf_to_iso(cf_val: float | None) -> str:
    if cf_val is None:
        return "null"
    dt = CF_EPOCH + timedelta(seconds=cf_val)
    return dt.strftime("%Y-%m-%dT%H:%M:%S UTC")


async def main() -> int:
    print("Timezone Create & Readback Experiment")
    print("=" * 40)
    print()

    # -----------------------------------------------------------------------
    # 1. System timezone
    # -----------------------------------------------------------------------
    now = datetime.now().astimezone()
    print(f"System time:  {now.isoformat()}")
    print(f"UTC offset:   {now.strftime('%z')} ({now.tzname()})")
    print(f"IPC dir:      {DEFAULT_IPC_DIR}")
    print()

    # -----------------------------------------------------------------------
    # 2. Create tasks via bridge
    # -----------------------------------------------------------------------
    section("2. Creating Test Tasks via Bridge")

    bridge = RealBridge(ipc_dir=DEFAULT_IPC_DIR, timeout=15.0)
    created: dict[str, dict] = {}  # label → {id, name, dueDate_input}

    for task_def in TEST_TASKS:
        label = task_def["label"]
        name = task_def["name"]
        due = task_def["dueDate"]
        desc = task_def["description"]

        print(f"  [{label}] Creating '{name}' with dueDate='{due}'")
        print(f"       ({desc})")

        try:
            result = await bridge.send_command(
                "add_task",
                {
                    "name": name,
                    "dueDate": due,
                },
            )
            task_id = result["id"]
            created[label] = {"id": task_id, "name": name, "input": due}
            print(f"       → id={task_id}")
        except Exception as e:
            print(f"       → ERROR: {e}")
            created[label] = {"id": None, "name": name, "input": due, "error": str(e)}

    # -----------------------------------------------------------------------
    # 3. Edit task F to change timezone
    # -----------------------------------------------------------------------
    if created.get("F", {}).get("id"):
        f_id = created["F"]["id"]
        print(f"\n  [F] Editing task {f_id}: dueDate → '2026-07-15T09:00:00+05:30'")
        try:
            await bridge.send_command(
                "edit_task",
                {
                    "id": f_id,
                    "dueDate": "2026-07-15T09:00:00+05:30",
                },
            )
            print("       → edit succeeded")
        except Exception as e:
            print(f"       → ERROR: {e}")

    # -----------------------------------------------------------------------
    # 4. Wait for SQLite cache sync
    # -----------------------------------------------------------------------
    print("\n  Waiting 3s for SQLite cache sync...")
    await asyncio.sleep(3)

    # -----------------------------------------------------------------------
    # 5. Bridge readback via snapshot
    # -----------------------------------------------------------------------
    section("5. Bridge Readback (snapshot)")

    try:
        snapshot = await bridge.send_command("snapshot")
        tasks = snapshot.get("tasks", [])

        # Filter to our test tasks
        id_set = {v["id"] for v in created.values() if v.get("id")}
        bridge_tasks = {t["id"]: t for t in tasks if t["id"] in id_set}

        for label in ["A", "B", "C", "D", "E", "F"]:
            info = created.get(label, {})
            tid = info.get("id")
            if not tid:
                print(f"  [{label}] (not created)")
                continue

            bt = bridge_tasks.get(tid, {})
            print(f"  [{label}] {info['name']}")
            print(f"    Input:            {info['input']}")
            print(f"    Bridge dueDate:   {bt.get('dueDate', 'NOT FOUND')}")
            print(f"    Bridge effDue:    {bt.get('effectiveDueDate', 'NOT FOUND')}")
            print(f"    Bridge floating:  {bt.get('shouldUseFloatingTimeZone', 'N/A')}")
            print()

    except Exception as e:
        print(f"  ERROR reading snapshot: {e}")

    # -----------------------------------------------------------------------
    # 6. SQLite readback
    # -----------------------------------------------------------------------
    section("6. SQLite Readback")

    if not SQLITE_DB.exists():
        print(f"  ERROR: SQLite database not found at {SQLITE_DB}")
    else:
        conn = sqlite3.connect(f"file:{SQLITE_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row

        for label in ["A", "B", "C", "D", "E", "F"]:
            info = created.get(label, {})
            tid = info.get("id")
            if not tid:
                print(f"  [{label}] (not created)")
                continue

            row = conn.execute(
                "SELECT dateDue, effectiveDateDue, shouldUseFloatingTimeZone "
                "FROM Task WHERE persistentIdentifier = ?",
                (tid,),
            ).fetchone()

            if row:
                print(f"  [{label}] {info['name']}")
                print(f"    Input:                      {info['input']}")
                print(f"    SQLite dateDue (text):      {row['dateDue']}")
                print(
                    f"    SQLite effectiveDateDue:    {row['effectiveDateDue']} "
                    f"= {cf_to_iso(row['effectiveDateDue'])}"
                )
                print(f"    SQLite floatingTZ:          {row['shouldUseFloatingTimeZone']}")
                print()
            else:
                print(f"  [{label}] {info['name']}: NOT FOUND in SQLite")

        conn.close()

    # -----------------------------------------------------------------------
    # 7. Side-by-side comparison table
    # -----------------------------------------------------------------------
    section("7. Side-by-Side Comparison")

    print(
        f"  {'Label':<6} {'Input':<30} {'SQLite dateDue':<28} {'SQLite effDue (UTC)':<24} {'Bridge dueDate':<30}"
    )
    print(f"  {'-' * 6} {'-' * 30} {'-' * 28} {'-' * 24} {'-' * 30}")

    # Re-read SQLite for the table
    if SQLITE_DB.exists():
        conn = sqlite3.connect(f"file:{SQLITE_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row

        for label in ["A", "B", "C", "D", "E", "F"]:
            info = created.get(label, {})
            tid = info.get("id")
            if not tid:
                continue

            row = conn.execute(
                "SELECT dateDue, effectiveDateDue FROM Task WHERE persistentIdentifier = ?",
                (tid,),
            ).fetchone()

            bt = bridge_tasks.get(tid, {}) if "bridge_tasks" in dir() else {}
            sqlite_due = str(row["dateDue"]) if row else "?"
            sqlite_eff = cf_to_iso(row["effectiveDateDue"]) if row else "?"
            bridge_due = bt.get("dueDate", "?") if bt else "?"

            print(
                f"  {label:<6} {info['input']:<30} {sqlite_due:<28} {sqlite_eff:<24} {bridge_due:<30}"
            )

        conn.close()

    # -----------------------------------------------------------------------
    # 8. Task IDs for script 04
    # -----------------------------------------------------------------------
    section("8. Task IDs for Script 04")

    for label in ["A", "B", "C", "D", "E", "F"]:
        info = created.get(label, {})
        print(f"  TZ-DD-{label}: {info.get('id', 'N/A')}")

    print()
    print("=" * 70)
    print("SPOT CHECK: Open OmniFocus UI and note how each TZ-DD-* task displays.")
    print("What time does each show? Does any look wrong?")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(asyncio.run(main()))
