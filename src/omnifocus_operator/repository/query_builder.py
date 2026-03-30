"""Parameterized SQL query builder for list operations.

Pure functions producing parameterized SQL strings for sqlite3 execution.
All user-provided values use ? placeholders (INFRA-01: no SQL injection).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from omnifocus_operator.models.enums import Availability

if TYPE_CHECKING:
    from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsRepoQuery
    from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksRepoQuery

__all__ = ["SqlQuery", "build_list_projects_sql", "build_list_tasks_sql"]


class SqlQuery(NamedTuple):
    """Parameterized SQL query with positional parameters."""

    sql: str
    params: tuple[Any, ...]


# ---------------------------------------------------------------------------
# Base SQL (mirrors hybrid.py constants)
# ---------------------------------------------------------------------------

_TASKS_BASE = (
    "SELECT t.*\n"
    "FROM Task t\n"
    "LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task\n"
    "WHERE pi.task IS NULL"
)

_TASKS_COUNT_BASE = (
    "SELECT COUNT(*)\n"
    "FROM Task t\n"
    "LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task\n"
    "WHERE pi.task IS NULL"
)

_PROJECTS_BASE = (
    "SELECT t.*, pi.lastReviewDate, pi.nextReviewDate,\n"
    "       pi.reviewRepetitionString, pi.nextTask, pi.folder,\n"
    "       pi.effectiveStatus\n"
    "FROM Task t\n"
    "JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task"
)

_PROJECTS_COUNT_BASE = (
    "SELECT COUNT(*)\nFROM Task t\nJOIN ProjectInfo pi ON t.persistentIdentifier = pi.task"
)


# ---------------------------------------------------------------------------
# Availability clause builders (no user params -- pure column conditions)
# ---------------------------------------------------------------------------

_TASK_AVAILABILITY_CLAUSES: dict[Availability, str] = {
    Availability.AVAILABLE: (
        "(t.blocked = 0 AND t.dateCompleted IS NULL AND t.dateHidden IS NULL)"
    ),
    Availability.BLOCKED: ("(t.blocked != 0 AND t.dateCompleted IS NULL AND t.dateHidden IS NULL)"),
    Availability.COMPLETED: ("(t.dateCompleted IS NOT NULL AND t.dateHidden IS NULL)"),
    Availability.DROPPED: "(t.dateHidden IS NOT NULL)",
}

_PROJECT_AVAILABILITY_CLAUSES: dict[Availability, str] = {
    Availability.AVAILABLE: (
        "(pi.effectiveStatus NOT IN ('dropped','inactive')"
        " AND t.dateCompleted IS NULL AND t.dateHidden IS NULL)"
    ),
    Availability.BLOCKED: (
        "(pi.effectiveStatus = 'inactive' AND t.dateCompleted IS NULL AND t.dateHidden IS NULL)"
    ),
    Availability.COMPLETED: (
        "(t.dateCompleted IS NOT NULL AND t.dateHidden IS NULL AND pi.effectiveStatus != 'dropped')"
    ),
    Availability.DROPPED: ("(t.dateHidden IS NOT NULL OR pi.effectiveStatus = 'dropped')"),
}


def _build_availability_clause(
    values: list[Availability],
    clause_map: dict[Availability, str],
) -> str:
    """Build compound OR clause for availability filter. No params needed."""
    parts = [clause_map[v] for v in values if v in clause_map]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return "(" + " OR ".join(parts) + ")"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_list_tasks_sql(query: ListTasksRepoQuery) -> tuple[SqlQuery, SqlQuery]:
    """Build parameterized SQL for task listing.

    Returns (data_query, count_query). All user values use ? placeholders.
    """
    conditions: list[str] = []
    params: list[Any] = []

    # -- Filters --

    if query.in_inbox is not None:
        conditions.append("t.inInbox = ?")
        params.append(1 if query.in_inbox else 0)

    if query.flagged is not None:
        conditions.append("t.flagged = ?")
        params.append(1 if query.flagged else 0)

    if query.project is not None:
        conditions.append(
            "t.containingProjectInfo IN ("
            "SELECT pi2.pk FROM ProjectInfo pi2 "
            "JOIN Task t2 ON pi2.task = t2.persistentIdentifier "
            "WHERE t2.name LIKE ? COLLATE NOCASE)"
        )
        params.append(f"%{query.project}%")

    if query.tags is not None and len(query.tags) > 0:
        placeholders = ",".join("?" * len(query.tags))
        conditions.append(
            f"t.persistentIdentifier IN ("
            f"SELECT ttg.task FROM TaskToTag ttg "
            f"WHERE ttg.tag IN ({placeholders}))"
        )
        params.extend(query.tags)

    if query.estimated_minutes_max is not None:
        conditions.append("t.estimatedMinutes <= ?")
        params.append(query.estimated_minutes_max)

    # Availability (no user params)
    avail_clause = _build_availability_clause(query.availability, _TASK_AVAILABILITY_CLAUSES)
    if avail_clause:
        conditions.append(avail_clause)

    if query.search is not None:
        conditions.append("(t.name LIKE ? COLLATE NOCASE OR t.plainTextNote LIKE ? COLLATE NOCASE)")
        params.append(f"%{query.search}%")
        params.append(f"%{query.search}%")

    # -- Build WHERE clause --
    where_suffix = ""
    if conditions:
        where_suffix = " AND " + " AND ".join(conditions)

    # -- Data query --
    data_sql = _TASKS_BASE + where_suffix
    data_params = list(params)

    if query.limit is not None:
        data_sql += " LIMIT ?"
        data_params.append(query.limit)
        if query.offset is not None:
            data_sql += " OFFSET ?"
            data_params.append(query.offset)

    # -- Count query --
    count_sql = _TASKS_COUNT_BASE + where_suffix

    return (
        SqlQuery(sql=data_sql, params=tuple(data_params)),
        SqlQuery(sql=count_sql, params=tuple(params)),
    )


def build_list_projects_sql(
    query: ListProjectsRepoQuery,
) -> tuple[SqlQuery, SqlQuery]:
    """Build parameterized SQL for project listing.

    Returns (data_query, count_query). All user values use ? placeholders.
    """
    conditions: list[str] = []
    params: list[Any] = []

    # Availability (no user params)
    avail_clause = _build_availability_clause(query.availability, _PROJECT_AVAILABILITY_CLAUSES)
    if avail_clause:
        conditions.append(avail_clause)

    if query.folder is not None:
        conditions.append(
            "pi.folder IN ("
            "SELECT f.persistentIdentifier FROM Folder f "
            "WHERE f.name LIKE ? COLLATE NOCASE)"
        )
        params.append(f"%{query.folder}%")

    if query.review_due_within is not None:
        conditions.append("pi.nextReviewDate IS NOT NULL AND pi.nextReviewDate <= ?")
        params.append(query.review_due_within)

    if query.flagged is not None:
        conditions.append("t.flagged = ?")
        params.append(1 if query.flagged else 0)

    # -- Build WHERE clause --
    where_clause = ""
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)

    # -- Data query --
    data_sql = _PROJECTS_BASE + where_clause
    data_params = list(params)

    if query.limit is not None:
        data_sql += " LIMIT ?"
        data_params.append(query.limit)
        if query.offset is not None:
            data_sql += " OFFSET ?"
            data_params.append(query.offset)

    # -- Count query --
    count_sql = _PROJECTS_COUNT_BASE + where_clause

    return (
        SqlQuery(sql=data_sql, params=tuple(data_params)),
        SqlQuery(sql=count_sql, params=tuple(params)),
    )
