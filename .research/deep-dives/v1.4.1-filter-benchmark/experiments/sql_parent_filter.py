"""SQL prototype for the parent-subtree filter.

Mirrors how ``build_list_tasks_sql`` in production would be extended to
support the v1.4.1 ``parent`` filter. Uses a recursive CTE to collect all
descendants of the target parent (inclusive of the parent itself, per spec
line 164: "resolved parent tasks are always included").

Additional filter predicates (tag, date) compose via AND on the outer
SELECT, matching the pattern of ``build_list_tasks_sql`` today.
"""

from __future__ import annotations

import sqlite3


def parent_only(conn: sqlite3.Connection, parent_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        WITH RECURSIVE descendants(id) AS (
            SELECT ?
            UNION ALL
            SELECT t.persistentIdentifier FROM Task t
            JOIN descendants d ON t.parent = d.id
        )
        SELECT t.* FROM Task t
        JOIN descendants d ON t.persistentIdentifier = d.id
        """,
        (parent_id,),
    ).fetchall()


def parent_plus_tag(conn: sqlite3.Connection, parent_id: str, tag_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        WITH RECURSIVE descendants(id) AS (
            SELECT ?
            UNION ALL
            SELECT t.persistentIdentifier FROM Task t
            JOIN descendants d ON t.parent = d.id
        )
        SELECT t.* FROM Task t
        JOIN descendants d ON t.persistentIdentifier = d.id
        WHERE t.persistentIdentifier IN (
            SELECT ttg.task FROM TaskToTag ttg WHERE ttg.tag = ?
        )
        """,
        (parent_id, tag_id),
    ).fetchall()


def parent_plus_date(
    conn: sqlite3.Connection, parent_id: str, due_after_cf: float
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        WITH RECURSIVE descendants(id) AS (
            SELECT ?
            UNION ALL
            SELECT t.persistentIdentifier FROM Task t
            JOIN descendants d ON t.parent = d.id
        )
        SELECT t.* FROM Task t
        JOIN descendants d ON t.persistentIdentifier = d.id
        WHERE t.effectiveDateDue >= ?
        """,
        (parent_id, due_after_cf),
    ).fetchall()
