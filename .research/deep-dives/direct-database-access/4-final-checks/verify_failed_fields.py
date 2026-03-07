#!/usr/bin/env python3
"""
Investigate the 6 FAILED fields from field coverage verification.

1. Queries SQLite (read-only) to gather data for each failed field
2. Prints findings from SQLite
3. Generates a JS snippet to paste into OmniFocus > Automation > Console

Safety: READ-ONLY. No writes to SQLite or OmniFocus.

Usage:
    python verify_failed_fields.py
    Then copy the JS snippet into OmniFocus > Automation > Console
"""

import plistlib
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


def section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print()


def main():
    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    uri = f"file:{SQLITE_DB}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    # Collect IDs for JS snippet across all investigations
    sample_task_ids = []
    sample_tag_ids = []
    sample_folder_ids = []
    sample_perspective_ids = []

    # ── Investigation 1: drop_date / effective_drop_date ──
    section("1. drop_date / effective_drop_date — Is dateHidden the same as 'dropped'?")

    # Count dateHidden values
    row = conn.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN dateHidden IS NOT NULL THEN 1 ELSE 0 END) AS with_dateHidden,
               SUM(CASE WHEN effectiveDateHidden IS NOT NULL THEN 1 ELSE 0 END) AS with_effectiveDateHidden
        FROM Task
    """).fetchone()
    print(
        f"  Task counts: total={row['total']}, "
        f"dateHidden={row['with_dateHidden']}, "
        f"effectiveDateHidden={row['with_effectiveDateHidden']}"
    )
    print()

    # Tasks with dateHidden — check their project's effectiveStatus
    print("  Tasks with dateHidden != NULL (sample, with project status):")
    rows = conn.execute("""
        SELECT t.persistentIdentifier, t.name, t.dateHidden, t.effectiveDateHidden,
               pi.effectiveStatus AS projStatus, pi.status AS projDirectStatus
        FROM Task t
        LEFT JOIN ProjectInfo pi ON t.containingProjectInfo = pi.pk
        WHERE t.dateHidden IS NOT NULL
        LIMIT 10
    """).fetchall()
    for r in rows:
        name = (r["name"] or "(unnamed)")[:55]
        print(f"    ID: {r['persistentIdentifier']}")
        print(f"    Name: {name}")
        print(
            f"    dateHidden={cf_to_str(r['dateHidden'])}  "
            f"effectiveDateHidden={cf_to_str(r['effectiveDateHidden'])}"
        )
        print(f"    projStatus={r['projStatus']}  projDirectStatus={r['projDirectStatus']}")
        print()
        sample_task_ids.append(r["persistentIdentifier"])

    # Tasks in dropped projects — check their dateHidden
    print("  Tasks in projects with effectiveStatus='dropped':")
    rows_dropped = conn.execute("""
        SELECT t.persistentIdentifier, t.name, t.dateHidden, t.effectiveDateHidden,
               pi.effectiveStatus
        FROM Task t
        JOIN ProjectInfo pi ON t.containingProjectInfo = pi.pk
        WHERE pi.effectiveStatus = 'dropped'
        LIMIT 5
    """).fetchall()
    if not rows_dropped:
        print("    (none found)")
    for r in rows_dropped:
        name = (r["name"] or "(unnamed)")[:55]
        print(f"    ID: {r['persistentIdentifier']}")
        print(f"    Name: {name}")
        print(
            f"    dateHidden={cf_to_str(r['dateHidden'])}  "
            f"effectiveDateHidden={cf_to_str(r['effectiveDateHidden'])}"
        )
        print()
        if r["persistentIdentifier"] not in sample_task_ids:
            sample_task_ids.append(r["persistentIdentifier"])

    # ── Investigation 2: should_use_floating_time_zone ──
    section("2. should_use_floating_time_zone — Does it exist anywhere?")

    # Search Task columns for anything timezone-related
    task_cols = conn.execute("PRAGMA table_info(Task)").fetchall()
    tz_keywords = ["float", "tz", "timezone", "zone", "time"]
    matching_cols = [
        c["name"] for c in task_cols if any(kw in c["name"].lower() for kw in tz_keywords)
    ]
    print(f"  Task columns matching timezone-related keywords: {matching_cols or '(none)'}")

    # Also check all tables for such columns
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("  All tables with timezone-related columns:")
    found_any = False
    for tbl in tables:
        cols = conn.execute(f"PRAGMA table_info({tbl['name']})").fetchall()
        matches = [c["name"] for c in cols if any(kw in c["name"].lower() for kw in tz_keywords)]
        if matches:
            print(f"    {tbl['name']}: {matches}")
            found_any = True
    if not found_any:
        print("    (none found in any table)")

    # Grab a few task IDs with due dates for JS cross-check
    rows_tz = conn.execute("""
        SELECT persistentIdentifier, name, dateDue
        FROM Task
        WHERE dateDue IS NOT NULL AND dateCompleted IS NULL
        LIMIT 3
    """).fetchall()
    print()
    print("  Sample tasks with due dates (for JS cross-check):")
    for r in rows_tz:
        name = (r["name"] or "(unnamed)")[:55]
        print(f"    ID: {r['persistentIdentifier']}  due={cf_to_str(r['dateDue'])}  name={name}")
        if r["persistentIdentifier"] not in sample_task_ids:
            sample_task_ids.append(r["persistentIdentifier"])

    # ── Investigation 3: Tag.status — Can we derive from allowsNextAction? ──
    section("3. Tag.status — Can we derive from allowsNextAction?")

    rows_tag_counts = conn.execute("""
        SELECT allowsNextAction, COUNT(*) AS cnt
        FROM Context
        GROUP BY allowsNextAction
        ORDER BY allowsNextAction
    """).fetchall()
    print("  allowsNextAction value distribution:")
    for r in rows_tag_counts:
        print(f"    allowsNextAction={r['allowsNextAction']}: {r['cnt']} tags")

    print()
    print("  Tags where allowsNextAction = 0 (on hold?):")
    rows_tags_blocked = conn.execute("""
        SELECT persistentIdentifier, name, allowsNextAction, dateHidden
        FROM Context
        WHERE allowsNextAction = 0
        LIMIT 10
    """).fetchall()
    if not rows_tags_blocked:
        print("    (none found)")
    for r in rows_tags_blocked:
        name = (r["name"] or "(unnamed)")[:55]
        print(
            f"    ID: {r['persistentIdentifier']}  name={name}  "
            f"dateHidden={cf_to_str(r['dateHidden'])}"
        )
        sample_tag_ids.append(r["persistentIdentifier"])

    # Also grab a couple active tags for comparison
    rows_tags_active = conn.execute("""
        SELECT persistentIdentifier, name, allowsNextAction
        FROM Context
        WHERE allowsNextAction = 1
        LIMIT 3
    """).fetchall()
    print()
    print("  Sample active tags (allowsNextAction=1) for comparison:")
    for r in rows_tags_active:
        name = (r["name"] or "(unnamed)")[:55]
        print(f"    ID: {r['persistentIdentifier']}  name={name}")
        sample_tag_ids.append(r["persistentIdentifier"])

    # ── Investigation 4: Folder.status — How to detect dropped folders? ──
    section("4. Folder.status — How to detect dropped folders?")

    row = conn.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN dateHidden IS NOT NULL THEN 1 ELSE 0 END) AS with_dateHidden,
               SUM(CASE WHEN effectiveDateHidden IS NOT NULL THEN 1 ELSE 0 END) AS with_effectiveDateHidden
        FROM Folder
    """).fetchone()
    print(
        f"  Folder counts: total={row['total']}, "
        f"dateHidden={row['with_dateHidden']}, "
        f"effectiveDateHidden={row['with_effectiveDateHidden']}"
    )

    # List all folder columns for reference
    folder_cols = conn.execute("PRAGMA table_info(Folder)").fetchall()
    print(f"  All Folder columns: {[c['name'] for c in folder_cols]}")

    print()
    print("  Folders with dateHidden != NULL:")
    rows_folders = conn.execute("""
        SELECT persistentIdentifier, name, dateHidden, effectiveDateHidden
        FROM Folder
        WHERE dateHidden IS NOT NULL
        LIMIT 10
    """).fetchall()
    if not rows_folders:
        print("    (none found)")
    for r in rows_folders:
        name = (r["name"] or "(unnamed)")[:55]
        print(f"    ID: {r['persistentIdentifier']}  name={name}")
        print(
            f"    dateHidden={cf_to_str(r['dateHidden'])}  "
            f"effectiveDateHidden={cf_to_str(r['effectiveDateHidden'])}"
        )
        print()
        sample_folder_ids.append(r["persistentIdentifier"])

    # Also grab a couple normal folders for comparison
    rows_folders_normal = conn.execute("""
        SELECT persistentIdentifier, name
        FROM Folder
        WHERE dateHidden IS NULL
        LIMIT 3
    """).fetchall()
    for r in rows_folders_normal:
        sample_folder_ids.append(r["persistentIdentifier"])

    # ── Investigation 5: Perspective.name — Stored in valueData plist? ──
    section("5. Perspective.name — Stored in valueData plist?")

    persp_cols = conn.execute("PRAGMA table_info(Perspective)").fetchall()
    print(f"  Perspective columns: {[c['name'] for c in persp_cols]}")
    print()

    rows_persp = conn.execute("""
        SELECT persistentIdentifier, valueData
        FROM Perspective
    """).fetchall()
    print(f"  Total perspectives: {len(rows_persp)}")
    print()
    print("  Attempting plist parse of valueData for each perspective:")
    for r in rows_persp:
        pid = r["persistentIdentifier"]
        sample_perspective_ids.append(pid)
        vdata = r["valueData"]
        if vdata is None:
            print(f"    ID: {pid}  valueData=NULL")
            continue
        try:
            plist = plistlib.loads(vdata)
            # Look for name-like keys
            name = None
            for key in plist:
                if "name" in key.lower() or "title" in key.lower() or "label" in key.lower():
                    name = plist[key]
                    break
            if name:
                print(f"    ID: {pid}  name={name!r}  (key found)")
            else:
                top_keys = list(plist.keys())[:10]
                print(f"    ID: {pid}  no name key found. Top keys: {top_keys}")
        except Exception as e:
            print(f"    ID: {pid}  plist parse error: {e}")

    conn.close()

    # ── Part 2: Generate JS console snippet ──
    section("JS SNIPPET — Copy into OmniFocus > Automation > Console")

    task_ids_js = ", ".join(f'"{tid}"' for tid in sample_task_ids)
    tag_ids_js = ", ".join(f'"{tid}"' for tid in sample_tag_ids)
    folder_ids_js = ", ".join(f'"{fid}"' for fid in sample_folder_ids)
    persp_ids_js = ", ".join(f'"{pid}"' for pid in sample_perspective_ids)

    js_snippet = f"""(function() {{
    // ── 1. drop_date: check taskStatus and project status for tasks with dateHidden ──
    console.log("=== 1. drop_date / effective_drop_date ===\\n");
    var taskIds = [{task_ids_js}];
    var allTasks = flattenedTasks;
    taskIds.forEach(function(id) {{
        for (var i = 0; i < allTasks.length; i++) {{
            var t = allTasks[i];
            if (t.id.primaryKey === id) {{
                var proj = t.containingProject;
                var projInfo = proj
                    ? "name=" + proj.name + " status=" + String(proj.status) + " active=" + proj.active
                    : "none";
                console.log(
                    "ID: " + id +
                    "\\n  Name: " + t.name +
                    "\\n  taskStatus: " + String(t.taskStatus) +
                    "\\n  dropDate: " + t.dropDate +
                    "\\n  effectiveDropDate: " + t.effectiveDropDate +
                    "\\n  project: " + projInfo + "\\n"
                );
                break;
            }}
        }}
    }});

    // ── 2. shouldUseFloatingTimeZone ──
    console.log("\\n=== 2. shouldUseFloatingTimeZone ===\\n");
    taskIds.forEach(function(id) {{
        for (var i = 0; i < allTasks.length; i++) {{
            var t = allTasks[i];
            if (t.id.primaryKey === id) {{
                var dueS = t.dueDate ? t.dueDate.toISOString() : "none";
                console.log(
                    "ID: " + id +
                    "\\n  Name: " + t.name +
                    "\\n  shouldUseFloatingTimeZone: " + t.shouldUseFloatingTimeZone +
                    "\\n  dueDate: " + dueS + "\\n"
                );
                break;
            }}
        }}
    }});

    // ── 3. Tag.status — compare with allowsNextAction ──
    console.log("\\n=== 3. Tag.status ===\\n");
    var tagIds = [{tag_ids_js}];
    var allTags = flattenedTags;
    tagIds.forEach(function(id) {{
        for (var i = 0; i < allTags.length; i++) {{
            var tg = allTags[i];
            if (tg.id.primaryKey === id) {{
                console.log(
                    "ID: " + id +
                    "\\n  Name: " + tg.name +
                    "\\n  status: " + String(tg.status) +
                    "\\n  active: " + tg.active +
                    "\\n  allowsNextAction: " + tg.allowsNextAction + "\\n"
                );
                break;
            }}
        }}
    }});

    // ── 4. Folder.status — compare with dateHidden ──
    console.log("\\n=== 4. Folder.status ===\\n");
    var folderIds = [{folder_ids_js}];
    var allFolders = flattenedFolders;
    folderIds.forEach(function(id) {{
        for (var i = 0; i < allFolders.length; i++) {{
            var f = allFolders[i];
            if (f.id.primaryKey === id) {{
                console.log(
                    "ID: " + id +
                    "\\n  Name: " + f.name +
                    "\\n  status: " + String(f.status) +
                    "\\n  active: " + f.active + "\\n"
                );
                break;
            }}
        }}
    }});

    // ── 5. Perspective.name ──
    console.log("\\n=== 5. Perspective.name ===\\n");
    var perspIds = [{persp_ids_js}];
    var allPerspectives = flattenedPerspectives;
    perspIds.forEach(function(id) {{
        for (var i = 0; i < allPerspectives.length; i++) {{
            var p = allPerspectives[i];
            if (p.id.primaryKey === id) {{
                console.log(
                    "ID: " + id +
                    "\\n  Name: " + p.name + "\\n"
                );
                break;
            }}
        }}
    }});

    console.log("\\nDone.");
}})();"""

    print(js_snippet)

    # ── Summary ──
    section("WHAT TO LOOK FOR WHEN COMPARING")

    print("""  1. drop_date / effective_drop_date:
     - Does dateHidden in SQLite correspond to dropDate in OmniFocus JS?
     - Do tasks in "dropped" projects show a dropDate or effectiveDropDate?
     - Is dateHidden used for BOTH "on hold" and "dropped", or just one?

  2. shouldUseFloatingTimeZone:
     - Does the property exist on tasks in OmniFocus? (true/false/undefined?)
     - If it exists but has no SQLite column, we must read it from the bridge.

  3. Tag.status:
     - Does allowsNextAction=0 map to Tag.Status.OnHold?
     - Does allowsNextAction=1 map to Tag.Status.Active?
     - Are there other statuses (Dropped?) and how are they stored?
     - Check if tags with dateHidden != NULL are "Dropped".

  4. Folder.status:
     - Does dateHidden != NULL mean Folder.Status.Dropped?
     - Or does it mean "on hold"? Is there a separate "dropped" indicator?
     - Compare folder.active (bool) vs folder.status (enum).

  5. Perspective.name:
     - Does the plist valueData contain the perspective name?
     - If so, which key holds it? Compare parsed name vs JS perspective.name.
     - If not in plist, the name may only be accessible via the bridge.
""")


if __name__ == "__main__":
    main()
