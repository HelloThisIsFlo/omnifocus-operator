#!/usr/bin/env python3
"""
SQLite Read Benchmark for OmniFocus Database

Benchmarks various read queries against the OmniFocus SQLite cache to
understand performance characteristics for snapshot reads.

Safety: READ-ONLY. No writes to SQLite or OmniFocus.

Usage: python test_sqlite_benchmark.py
"""

import sqlite3
import time
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

ITERATIONS = 10


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------


def benchmark(func, iterations=ITERATIONS, warmup=1):
    """Run func `warmup` times (discarded), then `iterations` times.

    Returns (min, avg, max) in seconds.
    """
    # Warmup
    for _ in range(warmup):
        func()

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return min(times), sum(times) / len(times), max(times)


def fmt_ms(seconds):
    """Format seconds as milliseconds string."""
    return f"{seconds * 1000:.1f}ms"


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------


def make_full_task_read(conn):
    """Read all rows from Task into Python dicts."""

    def run():
        rows = conn.execute("SELECT * FROM Task").fetchall()
        # Force materialization as dicts
        return [dict(row) for row in rows]

    return run


def make_full_snapshot(conn):
    """Read all tables needed for a complete snapshot."""

    def run():
        tasks = [dict(r) for r in conn.execute("SELECT * FROM Task").fetchall()]
        projects = [dict(r) for r in conn.execute("SELECT * FROM ProjectInfo").fetchall()]
        tags = [dict(r) for r in conn.execute("SELECT * FROM Context").fetchall()]
        folders = [dict(r) for r in conn.execute("SELECT * FROM Folder").fetchall()]
        task_to_tag = [dict(r) for r in conn.execute("SELECT * FROM TaskToTag").fetchall()]
        return tasks, projects, tags, folders, task_to_tag

    return run


def make_task_count(conn):
    """Simple COUNT(*) query."""

    def run():
        return conn.execute("SELECT COUNT(*) FROM Task").fetchone()[0]

    return run


def make_filtered_query(conn):
    """Actionable overdue tasks: overdue=1 AND blocked=0."""

    def run():
        rows = conn.execute("SELECT * FROM Task WHERE overdue = 1 AND blocked = 0").fetchall()
        return [dict(row) for row in rows]

    return run


def make_join_query(conn):
    """Tasks with their tag names via TaskToTag join."""

    def run():
        rows = conn.execute("""
            SELECT t.persistentIdentifier, t.name AS task_name,
                   c.name AS tag_name
            FROM Task t
            LEFT JOIN TaskToTag tt ON t.persistentIdentifier = tt.task
            LEFT JOIN Context c ON tt.tag = c.persistentIdentifier
        """).fetchall()
        return [dict(row) for row in rows]

    return run


# ---------------------------------------------------------------------------
# Connection overhead benchmark
# ---------------------------------------------------------------------------


def benchmark_connection_overhead(iterations=ITERATIONS):
    """Compare open+close per query vs reused connection."""
    db_path = str(SQLITE_DB)

    # Open+close per query
    def with_open_close():
        c = sqlite3.connect(db_path)
        c.row_factory = sqlite3.Row
        c.execute("SELECT COUNT(*) FROM Task").fetchone()
        c.close()

    # Reused connection
    persistent_conn = sqlite3.connect(db_path)
    persistent_conn.row_factory = sqlite3.Row

    def with_reuse():
        persistent_conn.execute("SELECT COUNT(*) FROM Task").fetchone()

    oc_min, oc_avg, oc_max = benchmark(with_open_close, iterations)
    re_min, re_avg, re_max = benchmark(with_reuse, iterations)

    persistent_conn.close()

    return (oc_min, oc_avg, oc_max), (re_min, re_avg, re_max)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    conn = sqlite3.connect(str(SQLITE_DB))
    conn.row_factory = sqlite3.Row

    # Database stats
    task_count = conn.execute("SELECT COUNT(*) FROM Task").fetchone()[0]
    tag_count = conn.execute("SELECT COUNT(*) FROM Context").fetchone()[0]
    folder_count = conn.execute("SELECT COUNT(*) FROM Folder").fetchone()[0]
    project_count = conn.execute("SELECT COUNT(*) FROM ProjectInfo").fetchone()[0]
    task_to_tag_count = conn.execute("SELECT COUNT(*) FROM TaskToTag").fetchone()[0]

    print(f"SQLite Read Benchmark ({ITERATIONS} iterations)")
    print("=" * 55)
    print()
    print(f"Database: {SQLITE_DB}")
    print(f"  Tasks: {task_count} rows")
    print(f"  Projects: {project_count} rows")
    print(f"  Tags: {tag_count} rows")
    print(f"  Folders: {folder_count} rows")
    print(f"  TaskToTag: {task_to_tag_count} rows")
    print()

    # Define benchmarks
    benchmarks = [
        ("Full task read", make_full_task_read(conn)),
        ("Full snapshot (all tables)", make_full_snapshot(conn)),
        ("Task count only", make_task_count(conn)),
        ("Actionable overdue filter", make_filtered_query(conn)),
        ("Task+tag join", make_join_query(conn)),
    ]

    # Header
    print(f"{'Query':<30} {'Min':>8} {'Avg':>8} {'Max':>8}")
    print("-" * 55)

    # Run each benchmark
    for name, func in benchmarks:
        bmin, bavg, bmax = benchmark(func)
        print(f"{name:<30} {fmt_ms(bmin):>8} {fmt_ms(bavg):>8} {fmt_ms(bmax):>8}")

    conn.close()

    # Connection overhead
    print()
    print("Connection overhead:")
    (oc_min, oc_avg, oc_max), (re_min, re_avg, re_max) = benchmark_connection_overhead()
    print(f"  Open+close per query:  {fmt_ms(oc_avg)} avg ({fmt_ms(oc_min)} - {fmt_ms(oc_max)})")
    print(f"  Reused connection:     {fmt_ms(re_avg)} avg ({fmt_ms(re_min)} - {fmt_ms(re_max)})")
    print(f"  Overhead per open:     {fmt_ms(oc_avg - re_avg)}")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
