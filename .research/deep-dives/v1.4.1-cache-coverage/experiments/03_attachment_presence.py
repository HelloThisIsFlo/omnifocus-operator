"""Experiment 03 — Attachment storage and presence test.

The Attachment table has a `task` FK. This experiment:
- Counts total attachments
- Counts distinct tasks/projects with attachments
- Checks indexes on the `task` column (cheap join?)
- Benchmarks the presence-test query (EXISTS / LEFT JOIN) at the
  current corpus size to estimate whether it's viable for default
  response inclusion.

No schema changes, no writes — strictly read-only.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)


def probe_attachments() -> None:
    if not os.path.exists(DB_PATH):
        print(f"ABORT: OmniFocus SQLite cache not found at {DB_PATH}")
        sys.exit(1)

    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    try:
        # --- Counts ---
        print("=" * 72)
        print("ATTACHMENT TABLE — counts")
        print("=" * 72)
        total = conn.execute("SELECT COUNT(*) AS n FROM Attachment").fetchone()["n"]
        print(f"  total rows in Attachment: {total}")

        distinct_tasks = conn.execute(
            "SELECT COUNT(DISTINCT task) AS n FROM Attachment WHERE task IS NOT NULL"
        ).fetchone()["n"]
        print(f"  distinct task FKs         : {distinct_tasks}")

        # FK distribution
        by_target = list(
            conn.execute(
                "SELECT COUNT(*) AS n, "
                "SUM(CASE WHEN task IS NOT NULL THEN 1 ELSE 0 END) AS task_nn, "
                "SUM(CASE WHEN folder IS NOT NULL THEN 1 ELSE 0 END) AS folder_nn, "
                "SUM(CASE WHEN context IS NOT NULL THEN 1 ELSE 0 END) AS context_nn, "
                "SUM(CASE WHEN perspective IS NOT NULL THEN 1 ELSE 0 END) AS persp_nn "
                "FROM Attachment"
            )
        )[0]
        print("  FK target distribution:")
        print(f"    task FK non-null    : {by_target['task_nn']}")
        print(f"    folder FK non-null  : {by_target['folder_nn']}")
        print(f"    context FK non-null : {by_target['context_nn']}")
        print(f"    perspective FK nn   : {by_target['persp_nn']}")

        # --- Indexes ---
        print()
        print("=" * 72)
        print("INDEXES on Attachment")
        print("=" * 72)
        for r in conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='Attachment'"
        ):
            print(f"  {r['name']}: {r['sql']}")

        # Query plan for a representative presence query
        print()
        print("=" * 72)
        print("EXPLAIN QUERY PLAN — presence test via EXISTS")
        print("=" * 72)
        presence_sql = (
            "SELECT t.persistentIdentifier, "
            "(CASE WHEN EXISTS (SELECT 1 FROM Attachment a WHERE a.task = t.persistentIdentifier)"
            " THEN 1 ELSE 0 END) AS hasAttachments "
            "FROM Task t LEFT JOIN ProjectInfo pi "
            "ON t.persistentIdentifier = pi.task WHERE pi.task IS NULL"
        )
        for r in conn.execute(f"EXPLAIN QUERY PLAN {presence_sql}"):
            print(f"  {dict(r)}")

        print()
        print("=" * 72)
        print("EXPLAIN QUERY PLAN — presence test via LEFT JOIN + GROUP BY")
        print("=" * 72)
        leftjoin_sql = (
            "SELECT t.persistentIdentifier, "
            "COUNT(a.persistentIdentifier) > 0 AS hasAttachments "
            "FROM Task t LEFT JOIN Attachment a ON a.task = t.persistentIdentifier "
            "LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task "
            "WHERE pi.task IS NULL GROUP BY t.persistentIdentifier"
        )
        for r in conn.execute(f"EXPLAIN QUERY PLAN {leftjoin_sql}"):
            print(f"  {dict(r)}")

        # --- Timing ---
        def bench(sql: str, iters: int = 20) -> tuple[float, float, float]:
            for _ in range(3):  # warmup
                conn.execute(sql).fetchall()
            samples: list[float] = []
            for _ in range(iters):
                s = time.perf_counter()
                conn.execute(sql).fetchall()
                samples.append((time.perf_counter() - s) * 1000)  # ms
            samples.sort()
            return (
                samples[0],
                samples[len(samples) // 2],
                samples[-1],
            )

        print()
        print("=" * 72)
        print("TIMING — presence query over full corpus (ms, 20 iters)")
        print("=" * 72)
        mn, md, mx = bench(presence_sql)
        print(f"  EXISTS subquery     min={mn:.2f}  median={md:.2f}  max={mx:.2f}")
        mn, md, mx = bench(leftjoin_sql)
        print(f"  LEFT JOIN + GROUP   min={mn:.2f}  median={md:.2f}  max={mx:.2f}")

        # --- Sample rows ---
        print()
        print("=" * 72)
        print("SAMPLE — 5 tasks WITH attachments")
        print("=" * 72)
        for r in conn.execute(
            "SELECT t.persistentIdentifier AS id, t.name, "
            "COUNT(a.persistentIdentifier) AS n "
            "FROM Task t JOIN Attachment a ON a.task = t.persistentIdentifier "
            "WHERE t.name IS NOT NULL GROUP BY t.persistentIdentifier LIMIT 5"
        ):
            print(f"  id={r['id'][:12]}  n_attachments={r['n']}  name={(r['name'] or '')[:50]!r}")

        # --- Project-attached check ---
        proj_with_attach = conn.execute(
            "SELECT COUNT(DISTINCT t.persistentIdentifier) AS n "
            "FROM Task t JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task "
            "JOIN Attachment a ON a.task = t.persistentIdentifier"
        ).fetchone()["n"]
        print()
        print(f"  Projects (as Task rows with ProjectInfo) with attachments: {proj_with_attach}")
    finally:
        conn.close()


if __name__ == "__main__":
    probe_attachments()
