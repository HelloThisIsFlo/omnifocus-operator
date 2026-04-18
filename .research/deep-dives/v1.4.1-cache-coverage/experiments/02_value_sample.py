"""Experiment 02 — Value sample for candidate columns.

Confirms candidate columns are not only present but populated. Checks:
- Storage type (should be INTEGER 0/1 for booleans)
- Null rate (should be 0 for NOT NULL columns — sanity check)
- Distribution (are all values the same? That'd be suspicious)
- Cross-section: separate task rows from project rows (projects have
  a ProjectInfo row, tasks do not)
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


def sample() -> None:
    if not os.path.exists(DB_PATH):
        print(f"ABORT: OmniFocus SQLite cache not found at {DB_PATH}")
        sys.exit(1)

    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    try:
        total_rows = conn.execute("SELECT COUNT(*) AS n FROM Task").fetchone()["n"]
        project_rows = conn.execute(
            "SELECT COUNT(*) AS n FROM Task t JOIN ProjectInfo pi"
            " ON t.persistentIdentifier = pi.task"
        ).fetchone()["n"]
        task_rows = total_rows - project_rows

        print("=" * 72)
        print(f"ROW COUNTS  total={total_rows}  tasks={task_rows}  projects={project_rows}")
        print("=" * 72)

        def distribution(table: str, column: str, scope_sql: str, scope_label: str) -> None:
            rows = list(
                conn.execute(
                    f"SELECT t.{column} AS v, COUNT(*) AS n "
                    f"FROM {table} t {scope_sql} "
                    f"GROUP BY t.{column} ORDER BY t.{column}"
                )
            )
            total = sum(r["n"] for r in rows)
            print(f"\n[{scope_label}] {table}.{column}  (rows={total})")
            if total == 0:
                print("  (no rows in scope — skipped)")
                return
            for r in rows:
                v = r["v"]
                n = r["n"]
                pct = (n / total) * 100
                typ = type(v).__name__
                print(f"  {v!s:<10} ({typ:<4}) count={n:<6} {pct:5.1f}%")

        # --- completeWhenChildrenComplete ---
        print("\n" + "=" * 72)
        print("completedByChildren → Task.completeWhenChildrenComplete")
        print("=" * 72)
        distribution("Task", "completeWhenChildrenComplete", "", "ALL rows (tasks + projects)")
        distribution(
            "Task",
            "completeWhenChildrenComplete",
            "LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task WHERE pi.task IS NULL",
            "TASK-only rows",
        )
        distribution(
            "Task",
            "completeWhenChildrenComplete",
            "JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task",
            "PROJECT-only rows",
        )

        # --- sequential ---
        print("\n" + "=" * 72)
        print("sequential → Task.sequential  +  ProjectInfo.containsSingletonActions")
        print("=" * 72)
        distribution("Task", "sequential", "", "ALL rows (tasks + projects)")
        distribution(
            "Task",
            "sequential",
            "LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task WHERE pi.task IS NULL",
            "TASK-only rows",
        )
        distribution(
            "Task",
            "sequential",
            "JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task",
            "PROJECT-only rows",
        )
        # ProjectInfo.containsSingletonActions
        print()
        rows = list(
            conn.execute(
                "SELECT containsSingletonActions AS v, COUNT(*) AS n "
                "FROM ProjectInfo GROUP BY containsSingletonActions"
                " ORDER BY containsSingletonActions"
            )
        )
        total = sum(r["n"] for r in rows)
        print(f"[PROJECTS only] ProjectInfo.containsSingletonActions  (rows={total})")
        for r in rows:
            v, n = r["v"], r["n"]
            pct = (n / total) * 100 if total else 0.0
            print(f"  {v!s:<10} ({type(v).__name__:<4}) count={n:<6} {pct:5.1f}%")

        # --- Sample concrete rows (5 tasks, 5 projects) ---
        print("\n" + "=" * 72)
        print("SAMPLE ROWS — 5 tasks, 5 projects")
        print("=" * 72)
        print("\nTASKS (no ProjectInfo):")
        for r in conn.execute(
            "SELECT t.persistentIdentifier AS id, t.name,"
            " t.completeWhenChildrenComplete AS cwcc, t.sequential AS seq"
            " FROM Task t LEFT JOIN ProjectInfo pi"
            " ON t.persistentIdentifier = pi.task"
            " WHERE pi.task IS NULL AND t.name IS NOT NULL"
            " ORDER BY t.dateModified DESC LIMIT 5"
        ):
            print(
                f"  id={r['id'][:12]}  cwcc={r['cwcc']} seq={r['seq']}"
                f"  name={(r['name'] or '')[:40]!r}"
            )

        print("\nPROJECTS (ProjectInfo joined):")
        for r in conn.execute(
            "SELECT t.persistentIdentifier AS id, t.name,"
            " t.completeWhenChildrenComplete AS cwcc, t.sequential AS seq,"
            " pi.containsSingletonActions AS csa"
            " FROM Task t JOIN ProjectInfo pi"
            " ON t.persistentIdentifier = pi.task"
            " WHERE t.name IS NOT NULL"
            " ORDER BY t.dateModified DESC LIMIT 5"
        ):
            print(
                f"  id={r['id'][:12]}  cwcc={r['cwcc']} seq={r['seq']} csa={r['csa']}"
                f"  name={(r['name'] or '')[:40]!r}"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    sample()
