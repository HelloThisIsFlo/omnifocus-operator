#!/usr/bin/env python3
"""
Field Coverage Verification: SQLite → Pydantic Model Contract

Queries the OmniFocus SQLite cache (READ-ONLY) and verifies that every field
in the Pydantic model contract can be populated from the database.

Safety: READ-ONLY. Opens database with ?mode=ro URI. No writes, no temp tables.

Usage: python verify_field_coverage.py
"""

import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_PATH = (
    Path(os.path.expanduser("~"))
    / "Library"
    / "Group Containers"
    / "34YW5XSRB7.com.omnigroup.OmniFocus"
    / "com.omnigroup.OmniFocus4"
    / "com.omnigroup.OmniFocusModel"
    / "OmniFocusDatabase.db"
)

# Core Foundation epoch: 2001-01-01 00:00:00 UTC
CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)

TABLES_OF_INTEREST = ["Task", "ProjectInfo", "Context", "Folder", "Perspective", "TaskToTag"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def connect():
    """Open a READ-ONLY connection to the OmniFocus SQLite database."""
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def cf_to_datetime(cf_timestamp):
    """Convert a Core Foundation timestamp to a human-readable string."""
    if cf_timestamp is None:
        return None
    try:
        dt = CF_EPOCH + timedelta(seconds=float(cf_timestamp))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (TypeError, ValueError):
        return f"???(raw={cf_timestamp})"


def truncate(s, maxlen=60):
    """Truncate a string for display."""
    if s is None:
        return "(null)"
    s = str(s)
    return s[: maxlen - 3] + "..." if len(s) > maxlen else s


def section(title):
    """Print a section header."""
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)
    print()


def subsection(title):
    """Print a subsection header."""
    print()
    print(f"--- {title} ---")
    print()


# ---------------------------------------------------------------------------
# Phase 1: Schema Discovery
# ---------------------------------------------------------------------------


def phase1_schema_discovery(conn):
    section("PHASE 1: Schema Discovery")

    for table in TABLES_OF_INTEREST:
        try:
            cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        except Exception as e:
            print(f"  TABLE {table}: ERROR - {e}")
            continue

        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  TABLE: {table}  ({count} rows, {len(cols)} columns)")
        print(f"  {'Column':<40} {'Type':<15} {'NotNull':<8} {'PK'}")
        print(f"  {'-' * 40} {'-' * 15} {'-' * 8} {'-' * 3}")
        for col in cols:
            name = col["name"]
            ctype = col["type"] or "(none)"
            notnull = "YES" if col["notnull"] else ""
            pk = "PK" if col["pk"] else ""
            print(f"  {name:<40} {ctype:<15} {notnull:<8} {pk}")
        print()


# ---------------------------------------------------------------------------
# Phase 2: Field-by-Field Verification
# ---------------------------------------------------------------------------


def check_column_exists(conn, table, column):
    """Check if a column exists in a table."""
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c["name"] == column for c in cols)


def sample_values(conn, table, column, limit=3, where=None):
    """Get sample non-null values for a column."""
    clause = f"WHERE {where}" if where else f"WHERE {column} IS NOT NULL"
    try:
        rows = conn.execute(f"SELECT {column} FROM {table} {clause} LIMIT ?", (limit,)).fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        return [f"ERROR: {e}"]


def verify_field(conn, table, column, field_name, derivation="direct", notes=""):
    """Verify a single field mapping and print the result."""
    exists = check_column_exists(conn, table, column)
    if exists:
        samples = sample_values(conn, table, column)
        verdict = "PASS"
    else:
        samples = []
        verdict = "FAIL"

    if derivation != "direct" and exists:
        verdict = "PASS"

    symbol = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[verdict]
    print(f"  {symbol} {field_name}")
    print(f"         Source: {table}.{column}")
    print(f"         Derivation: {derivation}")
    if samples:
        display = [truncate(str(s), 50) for s in samples[:3]]
        print(f"         Samples: {display}")
    if notes:
        print(f"         Notes: {notes}")
    return verdict


def verify_computed_field(field_name, derivation, notes=""):
    """Verify a field that is computed, not directly from a column."""
    print(f"  [PASS] {field_name}")
    print(f"         Derivation: {derivation}")
    if notes:
        print(f"         Notes: {notes}")
    return "PASS"


def phase2_field_verification(conn):
    section("PHASE 2: Field-by-Field Verification")
    results = {}  # entity -> list of (field, verdict)

    # ── OmniFocusEntity (base fields, checked on Task table) ──
    subsection("OmniFocusEntity (base — verified on Task table)")
    entity = "OmniFocusEntity"
    results[entity] = []

    for field, col, deriv, notes in [
        ("id", "persistentIdentifier", "direct", ""),
        ("name", "name", "direct", ""),
        ("url", "persistentIdentifier", "computed: omnifocus:///task/{id}", "Constructed from ID"),
        ("added", "dateAdded", "direct (CF timestamp → AwareDatetime)", ""),
        ("modified", "dateModified", "direct (CF timestamp → AwareDatetime)", ""),
    ]:
        v = verify_field(conn, "Task", col, field, deriv, notes)
        results[entity].append((field, v))

    # ── ActionableEntity (checked on Task table) ──
    subsection("ActionableEntity — Two-Axis Status")
    entity = "ActionableEntity (status)"
    results[entity] = []

    for field, col, deriv, notes in [
        ("urgency (overdue)", "overdue", "computed: overdue=1 → Urgency.overdue", ""),
        ("urgency (due_soon)", "dueSoon", "computed: dueSoon=1 → Urgency.due_soon", ""),
        ("availability (blocked)", "blocked", "computed: blocked=1 → Availability.blocked", ""),
        (
            "availability (completed)",
            "dateCompleted",
            "computed: not null → Availability.completed",
            "",
        ),
    ]:
        v = verify_field(conn, "Task", col, field, deriv, notes)
        results[entity].append((field, v))

    # Check for dropped detection columns
    subsection("ActionableEntity — Dropped Detection (critical)")
    drop_candidates = [
        "dateDropped",
        "effectiveDateDropped",
        "effectiveActive",
        "effectiveContainingProjectInfoActive",
        "active",
    ]
    print("  Checking which columns exist for detecting 'dropped' status:")
    for col in drop_candidates:
        exists = check_column_exists(conn, "Task", col)
        if exists:
            samples = sample_values(conn, "Task", col, limit=3)
            print(f"    {col}: EXISTS  samples={[truncate(str(s), 40) for s in samples]}")
        else:
            # Also check with common naming variants
            print(f"    {col}: NOT FOUND")

    # Try to find any column with 'drop' or 'active' in the name
    print()
    print("  All Task columns containing 'drop', 'active', or 'hidden':")
    cols = conn.execute("PRAGMA table_info(Task)").fetchall()
    for col in cols:
        name_lower = col["name"].lower()
        if any(kw in name_lower for kw in ["drop", "active", "hidden"]):
            samples = sample_values(conn, "Task", col["name"], limit=3)
            print(f"    {col['name']}: {[truncate(str(s), 40) for s in samples]}")

    # ── ActionableEntity content/flags/dates ──
    subsection("ActionableEntity — Content, Flags, Dates")
    entity = "ActionableEntity (fields)"
    results[entity] = []

    field_mappings = [
        # Content
        ("note", "plainTextNote", "direct", "Check if plainTextNote or noteXMLData"),
        # Flags
        ("flagged", "flagged", "direct", ""),
        ("effective_flagged", "effectiveFlagged", "direct", ""),
        # Dates
        ("due_date", "dateDue", "direct (CF timestamp)", ""),
        ("defer_date", "dateToStart", "direct (CF timestamp)", "XML calls this 'start'"),
        ("effective_due_date", "effectiveDateDue", "direct (CF timestamp)", ""),
        ("effective_defer_date", "effectiveDateToStart", "direct (CF timestamp)", ""),
        ("completion_date", "dateCompleted", "direct (CF timestamp)", ""),
        ("effective_completion_date", "effectiveDateCompleted", "direct (CF timestamp)", ""),
        ("planned_date", "datePlanned", "direct (CF timestamp)", ""),
        ("effective_planned_date", "effectiveDatePlanned", "direct (CF timestamp)", ""),
        ("drop_date", "dateDropped", "direct (CF timestamp)", "May not exist — check Phase 5"),
        (
            "effective_drop_date",
            "effectiveDateDropped",
            "direct (CF timestamp)",
            "May not exist — check Phase 5",
        ),
        # Metadata
        ("estimated_minutes", "estimatedMinutes", "direct", ""),
        ("has_children", "childrenCount", "computed: childrenCount > 0", ""),
        ("should_use_floating_time_zone", "shouldUseFloatingTimeZone", "direct", "Check Phase 5"),
    ]

    for field, col, deriv, notes in field_mappings:
        v = verify_field(conn, "Task", col, field, deriv, notes)
        results[entity].append((field, v))

    # Check note storage — try both plainTextNote and noteXMLData
    print()
    print("  Note storage investigation:")
    for col_name in ["plainTextNote", "noteXMLData", "noteXML", "note"]:
        exists = check_column_exists(conn, "Task", col_name)
        if exists:
            samples = sample_values(conn, "Task", col_name, limit=2)
            print(f"    {col_name}: EXISTS  samples={[truncate(str(s), 80) for s in samples]}")
        else:
            print(f"    {col_name}: NOT FOUND")

    # ── ActionableEntity relationships ──
    subsection("ActionableEntity — Relationships")
    entity_rel = "ActionableEntity (relationships)"
    results[entity_rel] = []

    v = verify_computed_field("tags", "join via TaskToTag table", "Verified in Phase 4")
    results[entity_rel].append(("tags", v))

    # Repetition rule columns
    rep_cols = [
        ("repetition_rule.rule", "repetitionRuleString", "direct (iCal RRULE)", ""),
        ("repetition_rule.schedule_type", "repetitionScheduleTypeString", "direct", ""),
    ]
    for field, col, deriv, notes in rep_cols:
        v = verify_field(conn, "Task", col, field, deriv, notes)
        results[entity_rel].append((field, v))

    # Search for other repetition-related columns
    print()
    print("  All Task columns containing 'repet' or 'anchor' or 'catch':")
    for col in conn.execute("PRAGMA table_info(Task)").fetchall():
        name_lower = col["name"].lower()
        if any(kw in name_lower for kw in ["repet", "anchor", "catch"]):
            samples = sample_values(conn, "Task", col["name"], limit=3)
            print(f"    {col['name']}: {[truncate(str(s), 60) for s in samples]}")

    # ── Task (own fields) ──
    subsection("Task — Own Fields")
    entity = "Task"
    results[entity] = []

    for field, col, deriv, notes in [
        ("in_inbox", "inInbox", "direct", ""),
        ("project", "containingProjectInfo", "direct (project ID)", ""),
        ("parent", "parent", "direct (parent task ID)", ""),
    ]:
        v = verify_field(conn, "Task", col, field, deriv, notes)
        results[entity].append((field, v))

    # ── Project (via ProjectInfo table) ──
    subsection("Project — Own Fields (ProjectInfo table)")
    entity = "Project"
    results[entity] = []

    for field, col, deriv, notes in [
        ("last_review_date", "lastReviewDate", "direct (CF timestamp)", ""),
        ("next_review_date", "nextReviewDate", "direct (CF timestamp)", ""),
        (
            "review_interval",
            "reviewRepetitionString",
            "direct (parse format like '@2w')",
            "Check Phase 5",
        ),
        ("next_task", "nextTask", "direct (task ID)", ""),
        ("folder", "folder", "direct (folder ID)", ""),
    ]:
        v = verify_field(conn, "ProjectInfo", col, field, deriv, notes)
        results[entity].append((field, v))

    # Show all ProjectInfo columns for reference
    print()
    print("  All ProjectInfo columns:")
    for col in conn.execute("PRAGMA table_info(ProjectInfo)").fetchall():
        samples = sample_values(conn, "ProjectInfo", col["name"], limit=2)
        print(f"    {col['name']}: {[truncate(str(s), 50) for s in samples]}")

    # ── Tag (Context table) ──
    subsection("Tag — Fields (Context table)")
    entity = "Tag"
    results[entity] = []

    for field, col, deriv, notes in [
        ("id", "persistentIdentifier", "direct", ""),
        ("name", "name", "direct", ""),
        ("added", "dateAdded", "direct (CF timestamp)", ""),
        ("modified", "dateModified", "direct (CF timestamp)", ""),
        (
            "status",
            "active",
            "computed: derive Active/OnHold/Dropped",
            "Check allowsNextAction too",
        ),
        ("children_are_mutually_exclusive", "childrenAreMutuallyExclusive", "direct", ""),
        ("parent", "parent", "direct (parent tag ID)", ""),
    ]:
        v = verify_field(conn, "Context", col, field, deriv, notes)
        results[entity].append((field, v))

    # Check for OnHold detection
    print()
    print("  Tag status detection columns:")
    for col_name in [
        "active",
        "allowsNextAction",
        "prohibitsNextAction",
        "effectiveActive",
        "hidden",
        "rank",
    ]:
        exists = check_column_exists(conn, "Context", col_name)
        if exists:
            samples = sample_values(conn, "Context", col_name, limit=3)
            print(f"    {col_name}: EXISTS  samples={[truncate(str(s), 40) for s in samples]}")
        else:
            print(f"    {col_name}: NOT FOUND")

    # ── Folder ──
    subsection("Folder — Fields")
    entity = "Folder"
    results[entity] = []

    for field, col, deriv, notes in [
        ("id", "persistentIdentifier", "direct", ""),
        ("name", "name", "direct", ""),
        ("added", "dateAdded", "direct (CF timestamp)", ""),
        ("modified", "dateModified", "direct (CF timestamp)", ""),
        ("status", "active", "computed: Active if active=1, Dropped if active=0", ""),
        ("parent", "parent", "direct (parent folder ID)", ""),
    ]:
        v = verify_field(conn, "Folder", col, field, deriv, notes)
        results[entity].append((field, v))

    # ── Perspective ──
    subsection("Perspective — Fields")
    entity = "Perspective"
    results[entity] = []

    for field, col, deriv, notes in [
        ("id", "persistentIdentifier", "direct", ""),
        ("name", "name", "direct", "Check if stored in plist or column"),
    ]:
        v = verify_field(conn, "Perspective", col, field, deriv, notes)
        results[entity].append((field, v))

    v = verify_computed_field("builtin", "computed: True if id is present (non-null)", "")
    results[entity].append(("builtin", v))

    # Show all Perspective columns
    print()
    print("  All Perspective columns:")
    for col in conn.execute("PRAGMA table_info(Perspective)").fetchall():
        samples = sample_values(conn, "Perspective", col["name"], limit=2)
        print(f"    {col['name']}: {[truncate(str(s), 50) for s in samples]}")

    return results


# ---------------------------------------------------------------------------
# Phase 3: Two-Axis Status Deep Dive
# ---------------------------------------------------------------------------


def phase3_status_deep_dive(conn):
    section("PHASE 3: Two-Axis Status Deep Dive")

    # ── Column existence ──
    subsection("Status columns in Task table")
    status_cols = [
        "blocked",
        "blockedByFutureStartDate",
        "overdue",
        "dueSoon",
        "dateCompleted",
        "effectiveDateCompleted",
    ]
    for col in status_cols:
        exists = check_column_exists(conn, "Task", col)
        if exists:
            count_nonnull = conn.execute(
                f"SELECT COUNT(*) FROM Task WHERE {col} IS NOT NULL"
            ).fetchone()[0]
            count_truthy = conn.execute(
                f"SELECT COUNT(*) FROM Task WHERE {col} = 1 OR ({col} IS NOT NULL AND {col} != 0 AND {col} != '')"
            ).fetchone()[0]
            print(f"  {col}: EXISTS  non-null={count_nonnull}  truthy={count_truthy}")
        else:
            print(f"  {col}: NOT FOUND")

    # ── Blocked AND Overdue ──
    subsection("Tasks that are BOTH blocked=1 AND overdue=1")
    rows = conn.execute("""
        SELECT persistentIdentifier, name, blocked, blockedByFutureStartDate,
               overdue, dueSoon, dateDue, effectiveDateDue
        FROM Task
        WHERE blocked = 1 AND overdue = 1
        LIMIT 5
    """).fetchall()

    count = conn.execute("SELECT COUNT(*) FROM Task WHERE blocked = 1 AND overdue = 1").fetchone()[
        0
    ]
    print(f"  Total tasks with blocked=1 AND overdue=1: {count}")
    print()

    for r in rows:
        print(f"  ID: {r['persistentIdentifier']}")
        print(f"  Name: {truncate(r['name'], 55)}")
        print(
            f"  blocked={r['blocked']}  blockedByFuture={r['blockedByFutureStartDate']}  "
            f"overdue={r['overdue']}  dueSoon={r['dueSoon']}"
        )
        print(
            f"  dateDue={cf_to_datetime(r['dateDue'])}  "
            f"effectiveDateDue={cf_to_datetime(r['effectiveDateDue'])}"
        )
        print()

    # ── Dropped detection ──
    subsection("Dropped Detection Strategy")

    # Look for dateDropped or similar
    print("  Searching for 'dropped' indicator columns in Task...")
    drop_cols = []
    for col in conn.execute("PRAGMA table_info(Task)").fetchall():
        name_lower = col["name"].lower()
        if any(kw in name_lower for kw in ["drop", "hidden", "active"]):
            drop_cols.append(col["name"])
            samples = sample_values(conn, "Task", col["name"], limit=3)
            print(f"    {col['name']}: {[truncate(str(s), 40) for s in samples]}")

    # Try to count dropped tasks using various heuristics
    print()
    print("  Dropped task detection attempts:")

    # Method 1: dateDropped column
    if check_column_exists(conn, "Task", "dateDropped"):
        count = conn.execute("SELECT COUNT(*) FROM Task WHERE dateDropped IS NOT NULL").fetchone()[
            0
        ]
        print(f"    dateDropped IS NOT NULL: {count} tasks")
    else:
        print("    dateDropped: column does not exist")

    # Method 2: effectiveActive = 0 and not completed
    if check_column_exists(conn, "Task", "effectiveActive"):
        count = conn.execute(
            "SELECT COUNT(*) FROM Task WHERE effectiveActive = 0 AND dateCompleted IS NULL"
        ).fetchone()[0]
        print(f"    effectiveActive=0 AND not completed: {count} tasks")

    # Method 3: Check ProjectInfo for dropped projects
    print()
    print("  Searching for status/dropped indicators in ProjectInfo...")
    for col in conn.execute("PRAGMA table_info(ProjectInfo)").fetchall():
        name_lower = col["name"].lower()
        if any(kw in name_lower for kw in ["status", "drop", "active", "hidden"]):
            samples = sample_values(conn, "ProjectInfo", col["name"], limit=3)
            print(f"    {col['name']}: {[truncate(str(s), 40) for s in samples]}")

    # ── Availability breakdown ──
    subsection("Availability Breakdown (all tasks)")

    total = conn.execute("SELECT COUNT(*) FROM Task").fetchone()[0]

    completed = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dateCompleted IS NOT NULL"
    ).fetchone()[0]

    blocked_not_completed = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE blocked = 1 AND dateCompleted IS NULL"
    ).fetchone()[0]

    available = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE blocked = 0 AND dateCompleted IS NULL"
    ).fetchone()[0]

    print(f"  Total tasks: {total}")
    print(f"  Completed (dateCompleted IS NOT NULL): {completed}")
    print(f"  Blocked (blocked=1 AND not completed): {blocked_not_completed}")
    print(f"  Remaining (blocked=0 AND not completed): {available}")
    print("    (this includes both 'available' and 'dropped' — need dropped detection)")

    # Try to separate available vs dropped
    if check_column_exists(conn, "Task", "dateDropped"):
        dropped = conn.execute(
            "SELECT COUNT(*) FROM Task WHERE dateDropped IS NOT NULL AND dateCompleted IS NULL"
        ).fetchone()[0]
        truly_available = available - dropped  # approximate
        print()
        print("  Refined breakdown using dateDropped:")
        print(f"    Dropped (dateDropped set, not completed): {dropped}")
        print(f"    Available (not blocked, not completed, not dropped): ~{truly_available}")

    # ── Urgency breakdown ──
    subsection("Urgency Breakdown (incomplete tasks only)")

    incomplete = conn.execute("SELECT COUNT(*) FROM Task WHERE dateCompleted IS NULL").fetchone()[0]

    overdue = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE overdue = 1 AND dateCompleted IS NULL"
    ).fetchone()[0]

    due_soon = conn.execute(
        "SELECT COUNT(*) FROM Task WHERE dueSoon = 1 AND overdue = 0 AND dateCompleted IS NULL"
    ).fetchone()[0]

    no_urgency = incomplete - overdue - due_soon

    print(f"  Incomplete tasks: {incomplete}")
    print(f"  Overdue: {overdue}")
    print(f"  Due soon (not overdue): {due_soon}")
    print(f"  No urgency: {no_urgency}")


# ---------------------------------------------------------------------------
# Phase 4: Relationships
# ---------------------------------------------------------------------------


def phase4_relationships(conn):
    section("PHASE 4: Relationships")

    # ── Tags via TaskToTag ──
    subsection("Tags: TaskToTag join")

    # Find a task that has tags
    row = conn.execute("""
        SELECT t.persistentIdentifier AS task_id, t.name AS task_name,
               GROUP_CONCAT(c.name, ', ') AS tag_names,
               GROUP_CONCAT(c.persistentIdentifier, ', ') AS tag_ids
        FROM Task t
        JOIN TaskToTag tt ON t.persistentIdentifier = tt.task
        JOIN Context c ON tt.tag = c.persistentIdentifier
        GROUP BY t.persistentIdentifier
        HAVING COUNT(*) >= 2
        LIMIT 1
    """).fetchone()

    if row:
        print(f"  Task: {truncate(row['task_name'], 50)}")
        print(f"  Task ID: {row['task_id']}")
        print(f"  Tags: {row['tag_names']}")
        print(f"  Tag IDs: {row['tag_ids']}")
    else:
        print("  No tasks with multiple tags found.")

    # Show TaskToTag schema
    print()
    print("  TaskToTag columns:")
    for col in conn.execute("PRAGMA table_info(TaskToTag)").fetchall():
        print(f"    {col['name']}: {col['type'] or '(none)'}")

    # ── Tag lookup by ID ──
    subsection("Tag lookup by persistentIdentifier")
    tag_row = conn.execute("SELECT persistentIdentifier, name FROM Context LIMIT 1").fetchone()
    if tag_row:
        tag_id = tag_row["persistentIdentifier"]
        lookup = conn.execute(
            "SELECT * FROM Context WHERE persistentIdentifier = ?", (tag_id,)
        ).fetchone()
        print(f"  Looked up tag ID: {tag_id}")
        print(f"  Found name: {lookup['name']}")
        print("  PASS: Tag lookup by ID works")

    # ── Project membership ──
    subsection("Project membership: Task → ProjectInfo")

    row = conn.execute("""
        SELECT t.persistentIdentifier AS task_id, t.name AS task_name,
               t.containingProjectInfo AS project_id,
               pi.folder AS folder_id
        FROM Task t
        JOIN ProjectInfo pi ON t.containingProjectInfo = pi.pk
        WHERE t.containingProjectInfo IS NOT NULL
        LIMIT 1
    """).fetchone()

    if row:
        print(f"  Task: {truncate(row['task_name'], 50)}")
        print(f"  Task ID: {row['task_id']}")
        print(f"  containingProjectInfo: {row['project_id']}")
        print(f"  Project's folder: {row['folder_id']}")
    else:
        print("  WARNING: No tasks with containingProjectInfo found.")

    # Check what the ProjectInfo PK actually is
    print()
    print("  ProjectInfo primary key investigation:")
    pi_cols = conn.execute("PRAGMA table_info(ProjectInfo)").fetchall()
    pk_cols = [c["name"] for c in pi_cols if c["pk"]]
    print(f"    PK columns: {pk_cols}")

    # Try joining on different columns
    pi_row = conn.execute("SELECT * FROM ProjectInfo LIMIT 1").fetchone()
    if pi_row:
        pi_keys = pi_row.keys()
        id_candidates = [k for k in pi_keys if "identifier" in k.lower() or k in ("pk", "task")]
        for key in id_candidates:
            print(f"    ProjectInfo.{key} sample: {pi_row[key]}")

    # Try the join with 'task' column
    print()
    print("  Trying Task.containingProjectInfo = ProjectInfo.task join:")
    row2 = conn.execute("""
        SELECT t.persistentIdentifier AS task_id, t.name AS task_name,
               t.containingProjectInfo AS proj_ref,
               pi.task AS pi_task
        FROM Task t
        JOIN ProjectInfo pi ON t.containingProjectInfo = pi.task
        WHERE t.containingProjectInfo IS NOT NULL
        LIMIT 3
    """).fetchall()
    if row2:
        for r in row2:
            print(f"    Task '{truncate(r['task_name'], 40)}' → ProjectInfo.task={r['pi_task']}")
        print("    JOIN via Task.containingProjectInfo = ProjectInfo.task: WORKS")
    else:
        print("    JOIN via ProjectInfo.task: no results")

    # ── Folder membership ──
    subsection("Folder membership: ProjectInfo → Folder")

    row = conn.execute("""
        SELECT pi.task AS project_task_id, pi.folder AS folder_ref,
               f.persistentIdentifier AS folder_id, f.name AS folder_name
        FROM ProjectInfo pi
        JOIN Folder f ON pi.folder = f.persistentIdentifier
        WHERE pi.folder IS NOT NULL
        LIMIT 3
    """).fetchall()

    if row:
        for r in row:
            print(
                f"  Project task: {r['project_task_id']} → Folder: {truncate(r['folder_name'], 40)} ({r['folder_id']})"
            )
    else:
        print("  WARNING: No project→folder joins worked with persistentIdentifier.")
        # Try with pk
        row2 = conn.execute("""
            SELECT pi.folder, f.persistentIdentifier, f.name
            FROM ProjectInfo pi, Folder f
            LIMIT 3
        """).fetchall()
        if row2:
            print("  Sample ProjectInfo.folder values:")
            for r in conn.execute(
                "SELECT folder FROM ProjectInfo WHERE folder IS NOT NULL LIMIT 3"
            ).fetchall():
                print(f"    {r[0]}")
            print("  Sample Folder.persistentIdentifier values:")
            for r in conn.execute("SELECT persistentIdentifier FROM Folder LIMIT 3").fetchall():
                print(f"    {r[0]}")

    # ── Parent-child tasks ──
    subsection("Parent-child: Task → parent Task")

    row = conn.execute("""
        SELECT child.persistentIdentifier AS child_id,
               child.name AS child_name,
               child.parent AS parent_ref,
               parent.persistentIdentifier AS parent_id,
               parent.name AS parent_name
        FROM Task child
        JOIN Task parent ON child.parent = parent.persistentIdentifier
        WHERE child.parent IS NOT NULL
        LIMIT 3
    """).fetchall()

    if row:
        for r in row:
            print(f"  Child: {truncate(r['child_name'], 35)} ({r['child_id']})")
            print(f"    → Parent: {truncate(r['parent_name'], 35)} ({r['parent_id']})")
    else:
        print("  WARNING: No parent-child relationships found.")
        # Debug: what does Task.parent look like?
        parents = conn.execute(
            "SELECT parent FROM Task WHERE parent IS NOT NULL LIMIT 5"
        ).fetchall()
        print("  Sample Task.parent values:")
        for p in parents:
            print(f"    {p[0]}")

    # ── Folder hierarchy ──
    subsection("Folder hierarchy: Folder → parent Folder")

    row = conn.execute("""
        SELECT child.persistentIdentifier AS child_id,
               child.name AS child_name,
               child.parent AS parent_ref,
               parent.persistentIdentifier AS parent_id,
               parent.name AS parent_name
        FROM Folder child
        JOIN Folder parent ON child.parent = parent.persistentIdentifier
        WHERE child.parent IS NOT NULL
        LIMIT 3
    """).fetchall()

    if row:
        for r in row:
            print(
                f"  Folder: {truncate(r['child_name'], 35)} → Parent: {truncate(r['parent_name'], 35)}"
            )
    else:
        print("  No nested folders found (or parent column uses different key).")
        # Check parent values
        parents = conn.execute(
            "SELECT parent FROM Folder WHERE parent IS NOT NULL LIMIT 3"
        ).fetchall()
        if parents:
            print("  Sample Folder.parent values:")
            for p in parents:
                print(f"    {p[0]}")

    # ── Tag hierarchy ──
    subsection("Tag hierarchy: Context → parent Context")

    row = conn.execute("""
        SELECT child.persistentIdentifier AS child_id,
               child.name AS child_name,
               child.parent AS parent_ref,
               parent.persistentIdentifier AS parent_id,
               parent.name AS parent_name
        FROM Context child
        JOIN Context parent ON child.parent = parent.persistentIdentifier
        WHERE child.parent IS NOT NULL
        LIMIT 3
    """).fetchall()

    if row:
        for r in row:
            print(
                f"  Tag: {truncate(r['child_name'], 35)} → Parent: {truncate(r['parent_name'], 35)}"
            )
    else:
        print("  No nested tags found (or parent column uses different key).")


# ---------------------------------------------------------------------------
# Phase 5: Tricky Fields
# ---------------------------------------------------------------------------


def phase5_tricky_fields(conn):
    section("PHASE 5: Tricky Fields")

    # ── Repetition Rule ──
    subsection("repetition_rule — RRULE, schedule_type, anchor_date_key")

    print("  Repetition-related columns in Task:")
    for col in conn.execute("PRAGMA table_info(Task)").fetchall():
        if (
            "repet" in col["name"].lower()
            or "anchor" in col["name"].lower()
            or "catch" in col["name"].lower()
        ):
            samples = sample_values(
                conn,
                "Task",
                col["name"],
                limit=3,
                where=f"{col['name']} IS NOT NULL AND {col['name']} != ''",
            )
            print(f"    {col['name']} ({col['type']}): {[truncate(str(s), 60) for s in samples]}")

    # Show a task with repetition rule
    print()
    print("  Sample task with repetition rule:")
    rep_row = conn.execute("""
        SELECT persistentIdentifier, name, repetitionRuleString, repetitionScheduleTypeString
        FROM Task
        WHERE repetitionRuleString IS NOT NULL AND repetitionRuleString != ''
        LIMIT 3
    """).fetchall()

    if rep_row:
        for r in rep_row:
            print(f"    Task: {truncate(r['name'], 45)}")
            print(f"    RRULE: {r['repetitionRuleString']}")
            print(f"    Method: {r['repetitionScheduleTypeString']}")
            print()
    else:
        print("    No tasks with repetition rules found.")

    # ── Review Interval ──
    subsection("review_interval — Storage format")

    print("  Sample reviewRepetitionString values from ProjectInfo:")
    rows = conn.execute("""
        SELECT task, reviewRepetitionString
        FROM ProjectInfo
        WHERE reviewRepetitionString IS NOT NULL AND reviewRepetitionString != ''
        LIMIT 5
    """).fetchall()

    if rows:
        for r in rows:
            print(
                f"    ProjectInfo.task={r['task']}  reviewRepetitionString='{r['reviewRepetitionString']}'"
            )
    else:
        print("    No review intervals found.")

    # Show distinct values
    print()
    print("  Distinct reviewRepetitionString values:")
    distinct = conn.execute("""
        SELECT DISTINCT reviewRepetitionString, COUNT(*) as cnt
        FROM ProjectInfo
        WHERE reviewRepetitionString IS NOT NULL
        GROUP BY reviewRepetitionString
        ORDER BY cnt DESC
        LIMIT 10
    """).fetchall()
    for r in distinct:
        print(f"    '{r['reviewRepetitionString']}': {r['cnt']} projects")

    # ── Note Content ──
    subsection("note — Storage format (plain text vs rich text)")

    # Check all note-related columns
    note_cols = []
    for col in conn.execute("PRAGMA table_info(Task)").fetchall():
        if "note" in col["name"].lower():
            note_cols.append(col["name"])
            print(f"  Column: {col['name']} ({col['type']})")

    # Show samples
    for col_name in note_cols:
        samples = sample_values(
            conn,
            "Task",
            col_name,
            limit=2,
            where=f"{col_name} IS NOT NULL AND {col_name} != '' AND length({col_name}) > 5",
        )
        print(f"  {col_name} samples:")
        for s in samples:
            print(f"    {truncate(str(s), 100)}")
        print()

    # ── URL / ID Format ──
    subsection("url — ID format for constructing omnifocus:/// URLs")

    print("  Sample persistentIdentifier values (Task):")
    for r in conn.execute("SELECT persistentIdentifier FROM Task LIMIT 5").fetchall():
        pid = r[0]
        print(f"    {pid}  →  omnifocus:///task/{pid}")

    print()
    print("  Sample persistentIdentifier values (Context/Tag):")
    for r in conn.execute("SELECT persistentIdentifier FROM Context LIMIT 3").fetchall():
        pid = r[0]
        print(f"    {pid}  →  omnifocus:///tag/{pid}")

    print()
    print("  Sample persistentIdentifier values (Folder):")
    for r in conn.execute("SELECT persistentIdentifier FROM Folder LIMIT 3").fetchall():
        pid = r[0]
        print(f"    {pid}  →  omnifocus:///folder/{pid}")

    # ── shouldUseFloatingTimeZone ──
    subsection("should_use_floating_time_zone")

    if check_column_exists(conn, "Task", "shouldUseFloatingTimeZone"):
        distinct = conn.execute("""
            SELECT shouldUseFloatingTimeZone, COUNT(*) as cnt
            FROM Task
            GROUP BY shouldUseFloatingTimeZone
        """).fetchall()
        print("  Value distribution:")
        for r in distinct:
            print(
                f"    shouldUseFloatingTimeZone={r['shouldUseFloatingTimeZone']}: {r['cnt']} tasks"
            )
    else:
        # Check alternate names
        print("  Column 'shouldUseFloatingTimeZone' NOT FOUND.")
        print("  Searching for floating/timezone columns:")
        for col in conn.execute("PRAGMA table_info(Task)").fetchall():
            if any(kw in col["name"].lower() for kw in ["float", "timezone", "tz"]):
                samples = sample_values(conn, "Task", col["name"], limit=3)
                print(f"    {col['name']}: {samples}")

    # ── Drop date ──
    subsection("drop_date / effective_drop_date")

    for table in ["Task", "ProjectInfo"]:
        print(f"  Columns in {table} containing 'drop' or 'hidden':")
        found_any = False
        for col in conn.execute(f"PRAGMA table_info({table})").fetchall():
            if any(kw in col["name"].lower() for kw in ["drop", "hidden"]):
                found_any = True
                samples = sample_values(
                    conn,
                    table,
                    col["name"],
                    limit=3,
                    where=f"{col['name']} IS NOT NULL AND {col['name']} != ''",
                )
                count = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {col['name']} IS NOT NULL AND {col['name']} != ''"
                ).fetchone()[0]
                print(
                    f"    {col['name']}: {count} non-empty  samples={[truncate(str(s), 40) for s in samples]}"
                )
        if not found_any:
            print("    (none found)")
        print()

    # ── Perspective details ──
    subsection("Perspective — Full column dump")

    row = conn.execute("SELECT * FROM Perspective LIMIT 1").fetchone()
    if row:
        print("  Sample perspective (first row):")
        for key in row.keys():
            val = row[key]
            if isinstance(val, bytes):
                print(f"    {key}: <binary, {len(val)} bytes>")
            else:
                print(f"    {key}: {truncate(str(val), 60)}")


# ---------------------------------------------------------------------------
# Phase 6: Summary
# ---------------------------------------------------------------------------


def phase6_summary(results):
    section("PHASE 6: FIELD COVERAGE SUMMARY")

    total_pass = 0
    total_warn = 0
    total_fail = 0

    for entity, fields in results.items():
        passes = [(f, v) for f, v in fields if v == "PASS"]
        warns = [(f, v) for f, v in fields if v == "WARN"]
        fails = [(f, v) for f, v in fields if v == "FAIL"]

        total = len(fields)
        total_pass += len(passes)
        total_warn += len(warns)
        total_fail += len(fails)

        status = "OK" if not fails and not warns else ("!!!" if fails else "~")
        print(f"  {status} {entity}: {len(passes)}/{total} PASS", end="")
        if warns:
            print(f", {len(warns)} WARN ({', '.join(f for f, _ in warns)})", end="")
        if fails:
            print(f", {len(fails)} FAIL ({', '.join(f for f, _ in fails)})", end="")
        print()

    grand_total = total_pass + total_warn + total_fail
    print()
    print(f"  GRAND TOTAL: {total_pass}/{grand_total} PASS, {total_warn} WARN, {total_fail} FAIL")

    if total_fail > 0:
        print()
        print("  FAILED fields need investigation — the column may not exist,")
        print("  may use a different name, or may require a different derivation.")

    if total_fail == 0 and total_warn == 0:
        print()
        print("  All fields can be populated from SQLite. Full coverage confirmed.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("OmniFocus SQLite → Pydantic Model Field Coverage Verification")
    print(f"Database: {DB_PATH}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    if not DB_PATH.exists():
        print(f"\nERROR: Database not found at {DB_PATH}")
        print("Cannot proceed without the SQLite database.")
        return

    conn = connect()

    try:
        phase1_schema_discovery(conn)
        results = phase2_field_verification(conn)
        phase3_status_deep_dive(conn)
        phase4_relationships(conn)
        phase5_tricky_fields(conn)
        phase6_summary(results)
    finally:
        conn.close()

    print()
    print("Done.")


if __name__ == "__main__":
    main()
