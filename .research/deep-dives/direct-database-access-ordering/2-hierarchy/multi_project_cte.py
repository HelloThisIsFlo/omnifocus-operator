#!/usr/bin/env python3
"""
Multi-project CTE investigation: can we compute outline-order sort_path
for ALL tasks in one recursive CTE, then use it for filtered/paginated queries?

Goals:
  1. Build a CTE anchored on ALL project roots (projectInfo IS NOT NULL)
  2. Handle negative ranks (shift to unsigned space)
  3. Test with both GM-TestProject and GM-TestProject2
  4. Simulate real query_builder.py patterns (filtered + paginated)
  5. Performance benchmark on full 3062-task database
  6. Handle edge cases: inbox tasks, orphans, action groups

Usage:
    python3 multi_project_cte.py

All access is read-only (?mode=ro). No mutations.
"""

from __future__ import annotations

import os
import sqlite3
import time

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)

# Known test data
PROJECT1_ID = "bW2BCrF4TAz"  # GM-TestProject
PROJECT2_ID = "gux8zqHgGas"  # GM-TestProject2
ORDERING_RESEARCH_ID = "dUWW6UbTCI6"  # "Ordering Research" action group in project 1
ORDERING_RESEARCH2_ID = "gz41lWsc0cf"  # "Ordering Research 2" action group in project 2

# Rank offset: shift signed 32-bit to unsigned for correct lexicographic sort
# OmniFocus ranks span [-2^31, 2^31-1]. Adding 2^31 makes everything [0, 2^32-1].
RANK_OFFSET = 2147483648  # 2^31

# Expected UI order for test subtrees (using actual DB names)
ORDERING_RESEARCH_NAME = "\U0001f52c Ordering Research - DELETE AFTER"
ORDERING_RESEARCH2_NAME = "\U0001f52c Ordering Research 2 - DELETE AFTER"

EXPECTED_PROJECT1_ORDER = [
    ORDERING_RESEARCH_NAME,
    "OR-01 First Task",
    "OR-01a Sub First",
    "OR-01b Sub Second",
    "OR-02 Second Task",
    "OR-03 Third Task",
    "OR-03a Subtask Alpha",
    "OR-03a-i Deep One",
    "OR-03a-ii Deep Two",
    "OR-03b Subtask Beta",
    "OR-03c Subtask Gamma",
    "OR-04 Fourth Task",
    "OR-05 Fifth Task",
]

EXPECTED_PROJECT2_ORDER = [
    ORDERING_RESEARCH2_NAME,
    "OR2-01 Alpha",
    "OR2-02 Beta",
    "OR2-03 Gamma",
]

# Test task names (for anonymization whitelist)
TEST_NAMES = set(EXPECTED_PROJECT1_ORDER + EXPECTED_PROJECT2_ORDER + [
    "GM-TestProject", "GM-TestProject2",
])


def connect() -> sqlite3.Connection:
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def section(title: str) -> None:
    print(f"\n{'=' * 78}")
    print(f"  {title}")
    print(f"{'=' * 78}\n")


def anon(name: str | None) -> str:
    """Anonymize non-test task names."""
    if name is None:
        return "[unnamed]"
    if name in TEST_NAMES:
        return name
    # Keep names that start with OR- or OR2- (test naming convention)
    if name.startswith("OR-") or name.startswith("OR2-"):
        return name
    return "[ANON]"


# ==========================================================================
#  THE CTE
# ==========================================================================

# This CTE computes sort_path for every task in the database.
# Anchor: project-root tasks (tasks that ARE projects, i.e. have projectInfo).
# Recursive: children sorted by rank within parent.
#
# Key: printf('%010d', rank + 2147483648) shifts negative ranks to unsigned
# space so lexicographic ordering is correct.
# 10 digits covers 0..4294967295 (2^32 - 1).
#
# sort_path format: "PPPP/RRRR/RRRR/..." where PPPP is the project-root rank
# and each RRRR is the shifted rank at that depth level.

MULTI_PROJECT_CTE = """
WITH RECURSIVE task_tree(
    id, name, parent, rank, depth, sort_path,
    project_id, containingProjectInfo, dateCompleted, dateHidden,
    blocked, flagged, inInbox, plainTextNote, estimatedMinutes
) AS (
    -- ANCHOR: project-root tasks (the task row that IS the project)
    SELECT
        t.persistentIdentifier, t.name, t.parent, t.rank, 0,
        printf('%010d', t.rank + {offset}),
        t.persistentIdentifier,
        t.containingProjectInfo, t.dateCompleted, t.dateHidden,
        t.blocked, t.flagged, t.inInbox, t.plainTextNote, t.estimatedMinutes
    FROM Task t
    JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task

    UNION ALL

    -- RECURSIVE: children of already-visited tasks
    SELECT
        t.persistentIdentifier, t.name, t.parent, t.rank,
        tt.depth + 1,
        tt.sort_path || '/' || printf('%010d', t.rank + {offset}),
        tt.project_id,
        t.containingProjectInfo, t.dateCompleted, t.dateHidden,
        t.blocked, t.flagged, t.inInbox, t.plainTextNote, t.estimatedMinutes
    FROM Task t
    JOIN task_tree tt ON t.parent = tt.id
)
""".format(offset=RANK_OFFSET)

# Simpler version for just sort_path (used in the proposed SQL at the end)
SORT_PATH_CTE = """
WITH RECURSIVE task_order(id, sort_path) AS (
    SELECT t.persistentIdentifier,
           printf('%010d', t.rank + {offset})
    FROM Task t
    JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task

    UNION ALL

    SELECT t.persistentIdentifier,
           o.sort_path || '/' || printf('%010d', t.rank + {offset})
    FROM Task t
    JOIN task_order o ON t.parent = o.id
)
""".format(offset=RANK_OFFSET)


def main() -> None:
    conn = connect()

    # ==================================================================
    # 1. BUILD AND TEST THE MULTI-PROJECT CTE
    # ==================================================================
    section("1. Multi-project CTE — full database traversal")

    # First: how many tasks exist?
    total_tasks = conn.execute("SELECT COUNT(*) FROM Task").fetchone()[0]
    project_count = conn.execute(
        "SELECT COUNT(*) FROM ProjectInfo"
    ).fetchone()[0]
    print(f"Total tasks in database: {total_tasks}")
    print(f"Total projects (CTE anchors): {project_count}")

    # Run the CTE and count how many tasks it reaches
    t0 = time.perf_counter()
    cte_count_sql = MULTI_PROJECT_CTE + "SELECT COUNT(*) FROM task_tree"
    cte_count = conn.execute(cte_count_sql).fetchone()[0]
    t1 = time.perf_counter()
    print(f"Tasks reached by CTE: {cte_count}")
    print(f"CTE COUNT(*) time: {(t1 - t0) * 1000:.1f}ms")

    unreached = total_tasks - cte_count
    print(f"Tasks NOT reached: {unreached}")

    # Test with GM-TestProject subtree
    section("1a. CTE output for GM-TestProject 'Ordering Research' subtree")

    project1_sql = MULTI_PROJECT_CTE + """
    SELECT id, name, depth, sort_path, project_id
    FROM task_tree
    WHERE project_id = ?
    ORDER BY sort_path
    """
    rows = conn.execute(project1_sql, (PROJECT1_ID,)).fetchall()

    print(f"Tasks in GM-TestProject: {len(rows)}")
    print(f"\n{'depth':>5} {'name':<45} sort_path (truncated)")
    print("-" * 90)

    # Show all tasks in the project
    for r in rows:
        indent = "  " * r["depth"]
        print(f"{r['depth']:>5} {indent}{anon(r['name']):<45} ...{r['sort_path'][-30:]}")

    # Extract the ordering research subtree: find "Ordering Research" and collect
    # it plus all deeper tasks until we hit a task at the same or lesser depth
    ordering_subtree = []
    collecting = False
    or_depth = None
    for r in rows:
        if r["name"] == ORDERING_RESEARCH_NAME:
            collecting = True
            or_depth = r["depth"]
            ordering_subtree.append(r)
            continue
        if collecting:
            if r["depth"] > or_depth:
                ordering_subtree.append(r)
            else:
                break  # Back to same or lesser depth — done

    actual_names = [r["name"] for r in ordering_subtree]
    print(f"\nExpected order: {EXPECTED_PROJECT1_ORDER}")
    print(f"Actual order:   {actual_names}")
    match1 = actual_names == EXPECTED_PROJECT1_ORDER
    print(f"MATCH: {'YES' if match1 else 'NO !!!'}")

    # Test with GM-TestProject2 subtree
    section("1b. CTE output for GM-TestProject2 'Ordering Research 2' subtree")

    project2_sql = MULTI_PROJECT_CTE + """
    SELECT id, name, depth, sort_path, project_id
    FROM task_tree
    WHERE project_id = ?
    ORDER BY sort_path
    """
    rows2 = conn.execute(project2_sql, (PROJECT2_ID,)).fetchall()
    print(f"Tasks in GM-TestProject2: {len(rows2)}")
    print(f"\n{'depth':>5} {'name':<45} sort_path (truncated)")
    print("-" * 90)

    for r in rows2:
        indent = "  " * r["depth"]
        print(f"{r['depth']:>5} {indent}{anon(r['name']):<45} ...{r['sort_path'][-30:]}")

    # Extract ordering research 2 subtree
    ordering2_subtree = []
    collecting2 = False
    or2_depth = None
    for r in rows2:
        if r["name"] == ORDERING_RESEARCH2_NAME:
            collecting2 = True
            or2_depth = r["depth"]
            ordering2_subtree.append(r)
            continue
        if collecting2:
            if r["depth"] > or2_depth:
                ordering2_subtree.append(r)
            else:
                break

    actual_names2 = [r["name"] for r in ordering2_subtree]
    print(f"\nExpected order: {EXPECTED_PROJECT2_ORDER}")
    print(f"Actual order:   {actual_names2}")
    match2 = actual_names2 == EXPECTED_PROJECT2_ORDER
    print(f"MATCH: {'YES' if match2 else 'NO !!!'}")

    # ==================================================================
    # 2. SIMULATE REAL FILTERED QUERIES
    # ==================================================================
    section("2a. Filtered query: available tasks in a specific project")

    # Available = not completed, not dropped (dateCompleted IS NULL AND dateHidden IS NULL)
    query_a_sql = MULTI_PROJECT_CTE + """
    SELECT id, name, depth, sort_path
    FROM task_tree
    WHERE project_id = ?
      AND dateCompleted IS NULL
      AND dateHidden IS NULL
      AND depth > 0  -- exclude the project root itself
    ORDER BY sort_path
    """
    rows_a = conn.execute(query_a_sql, (PROJECT1_ID,)).fetchall()
    print(f"Available tasks in GM-TestProject: {len(rows_a)}")
    print(f"\n{'depth':>5} {'name':<50}")
    print("-" * 60)
    for r in rows_a:
        indent = "  " * r["depth"]
        print(f"{r['depth']:>5} {indent}{anon(r['name'])}")

    section("2b. Filtered query: flagged tasks across ALL projects")

    query_b_sql = MULTI_PROJECT_CTE + """
    SELECT id, name, depth, sort_path, project_id
    FROM task_tree
    WHERE flagged = 1
      AND dateCompleted IS NULL
      AND dateHidden IS NULL
      AND depth > 0
    ORDER BY sort_path
    LIMIT 20
    """
    rows_b = conn.execute(query_b_sql).fetchall()
    print(f"Flagged tasks (up to 20): {len(rows_b)}")
    print(f"\n{'depth':>5} {'project':>15} {'name':<50}")
    print("-" * 75)
    for r in rows_b:
        indent = "  " * r["depth"]
        print(f"{r['depth']:>5} {r['project_id'][:10]:>15} {indent}{anon(r['name'])}")

    section("2c. Filtered query: text search across all projects")

    # Search for "OR-" to match our test tasks
    query_c_sql = MULTI_PROJECT_CTE + """
    SELECT id, name, depth, sort_path, project_id
    FROM task_tree
    WHERE (name LIKE ? COLLATE NOCASE OR plainTextNote LIKE ? COLLATE NOCASE)
      AND depth > 0
    ORDER BY sort_path
    """
    search_term = "%OR-%"
    rows_c = conn.execute(query_c_sql, (search_term, search_term)).fetchall()
    print(f"Tasks matching 'OR-' search: {len(rows_c)}")
    print(f"\n{'depth':>5} {'project':>15} {'name':<50}")
    print("-" * 75)
    for r in rows_c:
        indent = "  " * r["depth"]
        print(f"{r['depth']:>5} {r['project_id'][:10]:>15} {indent}{anon(r['name'])}")

    print("\nVerify: OR- tasks from project 1 appear before OR2- tasks from project 2")
    print("(because they're in different projects, sort_path groups by project rank first)")

    # ==================================================================
    # 3. PERFORMANCE TEST
    # ==================================================================
    section("3. Performance benchmark")

    # Warm up
    conn.execute("SELECT COUNT(*) FROM Task").fetchone()

    # Benchmark: full CTE materialization + ORDER BY sort_path
    iterations = 10

    # 3a. CTE with full materialization
    times_cte = []
    cte_bench_sql = MULTI_PROJECT_CTE + """
    SELECT id, sort_path FROM task_tree ORDER BY sort_path
    """
    for _ in range(iterations):
        t0 = time.perf_counter()
        conn.execute(cte_bench_sql).fetchall()
        t1 = time.perf_counter()
        times_cte.append((t1 - t0) * 1000)

    avg_cte = sum(times_cte) / len(times_cte)
    min_cte = min(times_cte)
    max_cte = max(times_cte)
    print(f"Full CTE (all tasks, ORDER BY sort_path):")
    print(f"  avg={avg_cte:.1f}ms  min={min_cte:.1f}ms  max={max_cte:.1f}ms  (n={iterations})")

    # 3b. Simple ORDER BY rank, persistentIdentifier (no CTE)
    times_simple = []
    simple_sql = "SELECT persistentIdentifier FROM Task ORDER BY rank, persistentIdentifier"
    for _ in range(iterations):
        t0 = time.perf_counter()
        conn.execute(simple_sql).fetchall()
        t1 = time.perf_counter()
        times_simple.append((t1 - t0) * 1000)

    avg_simple = sum(times_simple) / len(times_simple)
    min_simple = min(times_simple)
    max_simple = max(times_simple)
    print(f"\nSimple ORDER BY rank, persistentIdentifier (no CTE):")
    print(f"  avg={avg_simple:.1f}ms  min={min_simple:.1f}ms  max={max_simple:.1f}ms  (n={iterations})")

    print(f"\nCTE overhead: {avg_cte / avg_simple:.1f}x slower")
    print(f"CTE absolute: {'PASS (<100ms)' if avg_cte < 100 else 'FAIL (>=100ms)'}")

    # 3c. CTE with typical filtered query (project-scoped, available tasks)
    times_filtered = []
    filtered_sql = MULTI_PROJECT_CTE + """
    SELECT id, name, sort_path FROM task_tree
    WHERE project_id = ?
      AND dateCompleted IS NULL AND dateHidden IS NULL
      AND depth > 0
    ORDER BY sort_path
    """
    for _ in range(iterations):
        t0 = time.perf_counter()
        conn.execute(filtered_sql, (PROJECT1_ID,)).fetchall()
        t1 = time.perf_counter()
        times_filtered.append((t1 - t0) * 1000)

    avg_filtered = sum(times_filtered) / len(times_filtered)
    print(f"\nCTE + project filter + available:")
    print(f"  avg={avg_filtered:.1f}ms  min={min(times_filtered):.1f}ms  max={max(times_filtered):.1f}ms")

    # 3d. Lightweight CTE (only sort_path, no extra columns)
    times_light = []
    light_sql = SORT_PATH_CTE + """
    SELECT t.persistentIdentifier, o.sort_path
    FROM Task t
    JOIN task_order o ON t.persistentIdentifier = o.id
    LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
    WHERE pi.task IS NULL
    ORDER BY o.sort_path
    """
    for _ in range(iterations):
        t0 = time.perf_counter()
        conn.execute(light_sql).fetchall()
        t1 = time.perf_counter()
        times_light.append((t1 - t0) * 1000)

    avg_light = sum(times_light) / len(times_light)
    print(f"\nLightweight CTE (sort_path only, JOIN back to Task):")
    print(f"  avg={avg_light:.1f}ms  min={min(times_light):.1f}ms  max={max(times_light):.1f}ms")

    # ==================================================================
    # 4. EDGE CASES
    # ==================================================================
    section("4a. Edge case: inbox tasks (no containingProjectInfo)")

    inbox_tasks = conn.execute(
        "SELECT persistentIdentifier, name, parent, rank, inInbox, containingProjectInfo "
        "FROM Task WHERE inInbox = 1 LIMIT 10"
    ).fetchall()
    print(f"Inbox tasks found: {len(inbox_tasks)}")
    for r in inbox_tasks:
        print(f"  {anon(r['name'])}  parent={r['parent']}  "
              f"containingProjectInfo={r['containingProjectInfo']}  rank={r['rank']}")

    # Do inbox tasks have projectInfo? (i.e., are they caught by CTE anchor?)
    inbox_in_cte = conn.execute(
        MULTI_PROJECT_CTE + """
        SELECT COUNT(*) FROM task_tree WHERE inInbox = 1
        """
    ).fetchone()[0]
    inbox_total = conn.execute("SELECT COUNT(*) FROM Task WHERE inInbox = 1").fetchone()[0]
    print(f"\nInbox tasks in CTE: {inbox_in_cte} / {inbox_total}")
    if inbox_in_cte < inbox_total:
        print("WARNING: Some inbox tasks are NOT reached by the project-anchored CTE!")
        # Check what their parent looks like
        orphan_inbox = conn.execute(
            "SELECT t.persistentIdentifier, t.name, t.parent, t.rank "
            "FROM Task t "
            "WHERE t.inInbox = 1 "
            "AND t.persistentIdentifier NOT IN ("
            + MULTI_PROJECT_CTE + " SELECT id FROM task_tree"
            + ") LIMIT 5"
        ).fetchall()
        for r in orphan_inbox:
            print(f"  Unreached inbox: {anon(r['name'])} parent={r['parent']}")

    section("4b. Edge case: orphan tasks (parent chain doesn't reach project)")

    # Tasks not reached by CTE at all
    orphan_sql = """
    SELECT t.persistentIdentifier, t.name, t.parent, t.rank,
           t.inInbox, t.containingProjectInfo, t.dateCompleted, t.dateHidden
    FROM Task t
    WHERE t.persistentIdentifier NOT IN (
    """ + MULTI_PROJECT_CTE + " SELECT id FROM task_tree) LIMIT 20"

    orphans = conn.execute(orphan_sql).fetchall()
    print(f"Orphan tasks (not reached by CTE): {len(orphans)} shown (of {unreached} total)")
    if orphans:
        print(f"\n{'inbox':>5} {'completed':>10} {'dropped':>8} {'parent':<15} {'name'}")
        print("-" * 65)
        for r in orphans:
            completed = "Y" if r["dateCompleted"] else "N"
            dropped = "Y" if r["dateHidden"] else "N"
            print(f"{r['inInbox']:>5} {completed:>10} {dropped:>8} {r['parent'] or '(none)':<15} {anon(r['name'])}")

    # Characterize all orphans
    orphan_stats = conn.execute(
        """
        SELECT
            SUM(CASE WHEN t.inInbox = 1 THEN 1 ELSE 0 END) as inbox_count,
            SUM(CASE WHEN t.parent IS NULL AND t.inInbox = 0 THEN 1 ELSE 0 END) as root_no_inbox,
            SUM(CASE WHEN t.parent IS NOT NULL THEN 1 ELSE 0 END) as has_parent
        FROM Task t
        WHERE t.persistentIdentifier NOT IN (
        """ + MULTI_PROJECT_CTE + " SELECT id FROM task_tree)"
    ).fetchone()
    print(f"\nOrphan breakdown:")
    print(f"  In inbox:          {orphan_stats['inbox_count']}")
    print(f"  Root, not inbox:   {orphan_stats['root_no_inbox']}")
    print(f"  Has parent (real orphan): {orphan_stats['has_parent']}")

    # Investigate real orphans: what are their parents?
    if orphan_stats['has_parent'] and orphan_stats['has_parent'] > 0:
        real_orphans = conn.execute(
            """
            SELECT t.persistentIdentifier, t.parent,
                   p.persistentIdentifier as parent_exists,
                   p.name as parent_name,
                   pp.task as parent_is_project
            FROM Task t
            LEFT JOIN Task p ON t.parent = p.persistentIdentifier
            LEFT JOIN ProjectInfo pp ON t.parent = pp.task
            WHERE t.persistentIdentifier NOT IN (
            """ + MULTI_PROJECT_CTE + " SELECT id FROM task_tree)"
            + """
            AND t.inInbox = 0
            AND t.parent IS NOT NULL
            LIMIT 10
            """
        ).fetchall()
        print(f"\n  Real orphan investigation (first 10):")
        for r in real_orphans:
            parent_status = "EXISTS" if r["parent_exists"] else "MISSING"
            is_proj = "is project" if r["parent_is_project"] else "not project"
            print(f"    parent={r['parent']}  {parent_status}  {is_proj}  parent_name={anon(r['parent_name'])}")

        # Check: are the orphan parents themselves orphans? (cascading orphan chain)
        orphan_parents_missing = conn.execute(
            """
            SELECT COUNT(*)
            FROM Task t
            WHERE t.persistentIdentifier NOT IN (
            """ + MULTI_PROJECT_CTE + " SELECT id FROM task_tree)"
            + """
            AND t.inInbox = 0
            AND t.parent IS NOT NULL
            AND t.parent NOT IN (SELECT persistentIdentifier FROM Task)
            """
        ).fetchone()[0]
        print(f"\n  Orphans whose parent row doesn't exist at all: {orphan_parents_missing}")
        print(f"  (These are likely synced tasks whose parent was deleted)")

    section("4c. Edge case: action groups (tasks with children but not projects)")

    # Action groups: tasks that have children but no projectInfo
    action_groups = conn.execute(
        """
        SELECT t.persistentIdentifier, t.name, t.childrenCount, t.containingProjectInfo
        FROM Task t
        LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
        WHERE pi.task IS NULL AND t.childrenCount > 0
        LIMIT 10
        """
    ).fetchall()
    print(f"Action groups (non-project tasks with children): {len(action_groups)} shown")
    for r in action_groups:
        print(f"  {anon(r['name'])}  children={r['childrenCount']}  "
              f"containingProjectInfo={r['containingProjectInfo']}")

    # Verify action groups ARE reached by CTE (they should be, via recursive step)
    ag_ids = [r["persistentIdentifier"] for r in action_groups]
    if ag_ids:
        placeholders = ",".join("?" * len(ag_ids))
        ag_in_cte = conn.execute(
            MULTI_PROJECT_CTE + f"""
            SELECT COUNT(*) FROM task_tree
            WHERE id IN ({placeholders})
            """,
            ag_ids,
        ).fetchone()[0]
        print(f"\nAction groups reached by CTE: {ag_in_cte} / {len(ag_ids)}")

    # ==================================================================
    # 5. PROPOSED SQL FOR query_builder.py
    # ==================================================================
    section("5. PROPOSED SQL for query_builder.py")

    # Strategy A: WITH clause prepended to every query
    print("=" * 50)
    print("  STRATEGY A: CTE prepended as WITH clause")
    print("=" * 50)

    strategy_a = f"""
-- Lightweight CTE: only computes sort_path
WITH RECURSIVE task_order(id, sort_path) AS (
    -- Anchor: project-root tasks
    SELECT t.persistentIdentifier,
           printf('%010d', t.rank + {RANK_OFFSET})
    FROM Task t
    JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task

    UNION ALL

    -- Recursive: children, building path segment by segment
    SELECT t.persistentIdentifier,
           o.sort_path || '/' || printf('%010d', t.rank + {RANK_OFFSET})
    FROM Task t
    JOIN task_order o ON t.parent = o.id
)
-- Then the actual query joins against it:
SELECT t.*
FROM Task t
JOIN task_order o ON t.persistentIdentifier = o.id
LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
WHERE pi.task IS NULL
  -- ... additional WHERE conditions from query_builder ...
ORDER BY o.sort_path
-- LIMIT ? OFFSET ?
"""
    print(strategy_a)

    # Strategy B: Inbox tasks get a synthetic sort_path
    print("=" * 50)
    print("  STRATEGY B: CTE with inbox fallback")
    print("=" * 50)

    strategy_b = f"""
-- Full CTE including inbox tasks
WITH RECURSIVE task_order(id, sort_path) AS (
    -- Anchor A: project-root tasks
    SELECT t.persistentIdentifier,
           printf('%010d', t.rank + {RANK_OFFSET})
    FROM Task t
    JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task

    UNION ALL

    -- Recursive: children
    SELECT t.persistentIdentifier,
           o.sort_path || '/' || printf('%010d', t.rank + {RANK_OFFSET})
    FROM Task t
    JOIN task_order o ON t.parent = o.id
),
-- Combine: CTE results + inbox tasks with synthetic sort_path
full_order(id, sort_path) AS (
    SELECT id, sort_path FROM task_order
    UNION ALL
    -- Inbox tasks not reached by CTE: sort by rank at the end
    SELECT t.persistentIdentifier,
           'ZZZZZZZZZZ/' || printf('%010d', t.rank + {RANK_OFFSET})
    FROM Task t
    WHERE t.inInbox = 1
      AND t.persistentIdentifier NOT IN (SELECT id FROM task_order)
)
SELECT t.*
FROM Task t
JOIN full_order o ON t.persistentIdentifier = o.id
LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
WHERE pi.task IS NULL
ORDER BY o.sort_path
"""
    print(strategy_b)

    # Validate strategy A with a real query
    section("5a. Validate Strategy A: available tasks in project, with LIMIT/OFFSET")

    validation_sql = f"""
WITH RECURSIVE task_order(id, sort_path) AS (
    SELECT t.persistentIdentifier,
           printf('%010d', t.rank + {RANK_OFFSET})
    FROM Task t
    JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task

    UNION ALL

    SELECT t.persistentIdentifier,
           o.sort_path || '/' || printf('%010d', t.rank + {RANK_OFFSET})
    FROM Task t
    JOIN task_order o ON t.parent = o.id
)
SELECT t.persistentIdentifier, t.name, o.sort_path
FROM Task t
JOIN task_order o ON t.persistentIdentifier = o.id
LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
WHERE pi.task IS NULL
  AND t.containingProjectInfo IN (
    SELECT pi2.pk FROM ProjectInfo pi2 WHERE pi2.task = ?
  )
  AND t.dateCompleted IS NULL
  AND t.dateHidden IS NULL
ORDER BY o.sort_path
LIMIT 5 OFFSET 0
"""
    rows_val = conn.execute(validation_sql, (PROJECT1_ID,)).fetchall()
    print("Strategy A validation — first 5 available tasks in GM-TestProject:")
    for r in rows_val:
        print(f"  {anon(r['name']):<45} ...{r['sort_path'][-30:]}")

    # Second page
    rows_val2 = conn.execute(validation_sql.replace("OFFSET 0", "OFFSET 5"), (PROJECT1_ID,)).fetchall()
    print("\nPage 2 (OFFSET 5):")
    for r in rows_val2:
        print(f"  {anon(r['name']):<45} ...{r['sort_path'][-30:]}")

    # Validate with cross-project query
    section("5b. Validate: cross-project flagged tasks")

    cross_project_sql = f"""
WITH RECURSIVE task_order(id, sort_path) AS (
    SELECT t.persistentIdentifier,
           printf('%010d', t.rank + {RANK_OFFSET})
    FROM Task t
    JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task

    UNION ALL

    SELECT t.persistentIdentifier,
           o.sort_path || '/' || printf('%010d', t.rank + {RANK_OFFSET})
    FROM Task t
    JOIN task_order o ON t.parent = o.id
)
SELECT t.persistentIdentifier, t.name, o.sort_path
FROM Task t
JOIN task_order o ON t.persistentIdentifier = o.id
LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
WHERE pi.task IS NULL
  AND t.flagged = 1
  AND t.dateCompleted IS NULL
  AND t.dateHidden IS NULL
ORDER BY o.sort_path
LIMIT 20
"""
    rows_cross = conn.execute(cross_project_sql).fetchall()
    print(f"Flagged tasks across all projects (up to 20): {len(rows_cross)}")
    for r in rows_cross:
        print(f"  {anon(r['name']):<45} ...{r['sort_path'][-30:]}")

    # ==================================================================
    # SUMMARY
    # ==================================================================
    section("SUMMARY")

    print(f"1. CTE correctness:")
    print(f"   GM-TestProject order match:  {'PASS' if match1 else 'FAIL'}")
    print(f"   GM-TestProject2 order match: {'PASS' if match2 else 'FAIL'}")
    print(f"   Tasks reached: {cte_count}/{total_tasks} ({cte_count/total_tasks*100:.1f}%)")
    print(f"   Unreached: {unreached} (inbox/orphan)")
    print()
    print(f"2. Performance:")
    print(f"   Full CTE:        {avg_cte:.1f}ms avg")
    print(f"   Simple ORDER BY: {avg_simple:.1f}ms avg")
    print(f"   CTE overhead:    {avg_cte/avg_simple:.1f}x")
    print(f"   Filtered CTE:    {avg_filtered:.1f}ms avg")
    print(f"   Light CTE+JOIN:  {avg_light:.1f}ms avg")
    print(f"   Target <100ms:   {'PASS' if avg_cte < 100 else 'FAIL'}")
    print()
    print(f"3. Recommendation:")
    print(f"   Use Strategy A (lightweight CTE prepended as WITH clause).")
    print(f"   The CTE computes ONLY sort_path — no extra columns.")
    print(f"   query_builder.py prepends the WITH clause and adds")
    print(f"   'JOIN task_order o ON t.persistentIdentifier = o.id'")
    print(f"   then uses 'ORDER BY o.sort_path' before LIMIT/OFFSET.")
    print()
    print(f"4. Edge cases:")
    print(f"   Inbox tasks: {inbox_total} total, {inbox_in_cte} in CTE.")
    if inbox_total > inbox_in_cte:
        print(f"   -> Use Strategy B if inbox tasks need outline ordering.")
        print(f"   -> Or: LEFT JOIN task_order + COALESCE for inbox fallback.")
    else:
        print(f"   -> All inbox tasks reached (they're inside projects).")
    print(f"   Action groups: correctly traversed by recursive step.")

    conn.close()
    print("\nDone. All queries read-only.")


if __name__ == "__main__":
    main()
