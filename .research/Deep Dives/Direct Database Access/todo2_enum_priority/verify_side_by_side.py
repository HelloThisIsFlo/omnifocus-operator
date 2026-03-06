#!/usr/bin/env python3
"""
Side-by-side verification: SQLite flags vs OmniFocus bridge taskStatus.

1. Queries SQLite for tasks that are both blocked=1 AND overdue=1
2. Prints the SQLite view (independent flags)
3. Generates a JS console snippet to copy-paste into OmniFocus
   that reports the bridge's single-winner taskStatus for those same tasks

Safety: READ-ONLY. No writes to SQLite or OmniFocus.

Usage:
    python verify_side_by_side.py
    Then copy the JS snippet into OmniFocus > Automation > Console
"""

import sqlite3
from datetime import datetime, timedelta
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

CF_EPOCH = datetime(2001, 1, 1)


def cf_to_str(cf_timestamp):
    if cf_timestamp is None:
        return "none"
    try:
        dt = CF_EPOCH + timedelta(seconds=float(cf_timestamp))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return "???"


def main():
    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    conn = sqlite3.connect(str(SQLITE_DB))
    conn.row_factory = sqlite3.Row

    # Get tasks that are both blocked AND overdue (active only)
    rows = conn.execute("""
        SELECT persistentIdentifier, name,
               blocked, blockedByFutureStartDate, overdue, dueSoon,
               dateDue, effectiveDateDue, dateToStart, effectiveDateToStart,
               parent, containingProjectInfo
        FROM Task
        WHERE dateCompleted IS NULL
          AND blocked = 1
          AND overdue = 1
        LIMIT 10
    """).fetchall()

    if not rows:
        print("No tasks found with both blocked=1 AND overdue=1.")
        conn.close()
        return

    task_ids = [r["persistentIdentifier"] for r in rows]

    # ── Part 1: SQLite view ──
    print("=" * 70)
    print("PART 1: SQLite View (independent flags)")
    print("=" * 70)
    print()
    for r in rows:
        name = r["name"] or "(unnamed)"
        if len(name) > 55:
            name = name[:52] + "..."
        print(f"  ID: {r['persistentIdentifier']}")
        print(f"  Name: {name}")
        print(
            f"  blocked={r['blocked']}  blockedByFutureStart={r['blockedByFutureStartDate']}  "
            f"overdue={r['overdue']}  dueSoon={r['dueSoon']}"
        )
        due = cf_to_str(r["dateDue"])
        eff_due = cf_to_str(r["effectiveDateDue"])
        print(f"  dateDue={due}  effectiveDateDue={eff_due}")
        start = cf_to_str(r["dateToStart"])
        eff_start = cf_to_str(r["effectiveDateToStart"])
        print(f"  dateToStart={start}  effectiveDateToStart={eff_start}")
        print()

    conn.close()

    # ── Part 2: Generate JS console snippet ──
    print("=" * 70)
    print("PART 2: Copy this JS into OmniFocus > Automation > Console")
    print("=" * 70)
    print()

    # Build JS array of IDs to look up
    ids_js = ", ".join(f'"{tid}"' for tid in task_ids)

    js_snippet = f"""(function() {{
    var ids = [{ids_js}];

    function resolveStatus(s) {{
        if (s === Task.Status.Available) return "Available";
        if (s === Task.Status.Blocked) return "Blocked";
        if (s === Task.Status.Completed) return "Completed";
        if (s === Task.Status.Dropped) return "Dropped";
        if (s === Task.Status.DueSoon) return "DueSoon";
        if (s === Task.Status.Next) return "Next";
        if (s === Task.Status.Overdue) return "Overdue";
        return "Unknown(" + String(s) + ")";
    }}

    var allTasks = flattenedTasks;
    var results = [];

    ids.forEach(function(id) {{
        for (var i = 0; i < allTasks.length; i++) {{
            var t = allTasks[i];
            if (t.id.primaryKey === id) {{
                var proj = t.containingProject;
                var dueD = t.effectiveDueDate;
                var defD = t.effectiveDeferDate;
                var dueS = dueD ? dueD.toISOString() : "none";
                var defS = defD ? defD.toISOString() : "none";
                var projS = proj
                    ? proj.name + " (" + resolveStatus(proj.task.taskStatus) + ")"
                    : "none";
                results.push(
                    "ID: " + id +
                    "\\n  Name: " + t.name +
                    "\\n  taskStatus: " + resolveStatus(t.taskStatus) +
                    "\\n  effectiveDueDate: " + dueS +
                    "\\n  effectiveDeferDate: " + defS +
                    "\\n  project: " + projS +
                    "\\n  sequential: " + t.sequential +
                    "\\n"
                );
                break;
            }}
        }}
    }});

    if (results.length === 0) {{
        console.log("No matching tasks found!");
    }} else {{
        console.log("Bridge taskStatus for blocked+overdue tasks:\\n\\n" + results.join("\\n"));
    }}
}})();"""

    print(js_snippet)
    print()
    print("=" * 70)
    print("EXPECTED RESULT:")
    print("  If overdue wins: all tasks show taskStatus=Overdue")
    print("  If blocked wins: all tasks show taskStatus=Blocked")
    print("  Compare with SQLite flags above to confirm the masking behavior")
    print("=" * 70)


if __name__ == "__main__":
    main()
