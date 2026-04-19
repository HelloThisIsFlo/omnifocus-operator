"""Parameterized SQL query builder for list operations.

Pure functions producing parameterized SQL strings for sqlite3 execution.
All user-provided values use ? placeholders (INFRA-01: no SQL injection).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol

from omnifocus_operator.models.enums import Availability

_CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)

if TYPE_CHECKING:
    from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsRepoQuery
    from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksRepoQuery

# ---------------------------------------------------------------------------
# Date column mapping (query field prefix -> SQLite column name)
# ---------------------------------------------------------------------------

_DATE_COLUMN_MAP: dict[str, str] = {
    "due": "effectiveDateDue",
    "defer": "effectiveDateToStart",
    "planned": "effectiveDatePlanned",
    "completed": "effectiveDateCompleted",
    "dropped": "effectiveDateHidden",
    "added": "dateAdded",
    "modified": "dateModified",
}

# Lifecycle date fields use additive semantics: remaining tasks (NULL column)
# pass through alongside lifecycle items matching the date bounds.
_LIFECYCLE_DATE_FIELDS = {"completed", "dropped"}


class HasDateBounds(Protocol):
    """Structural type for queries with date _after/_before fields.

    Used by _add_date_conditions to accept both ListTasksRepoQuery and
    ListProjectsRepoQuery without coupling to either concrete type.
    """

    due_after: datetime | None
    due_before: datetime | None
    defer_after: datetime | None
    defer_before: datetime | None
    planned_after: datetime | None
    planned_before: datetime | None
    completed_after: datetime | None
    completed_before: datetime | None
    dropped_after: datetime | None
    dropped_before: datetime | None
    added_after: datetime | None
    added_before: datetime | None
    modified_after: datetime | None
    modified_before: datetime | None


def _add_date_conditions(
    conditions: list[str],
    params: list[Any],
    query: HasDateBounds,
) -> None:
    """Append date predicates to conditions/params for each set _after/_before field.

    Uses >= for _after (inclusive lower bound) and < for _before (exclusive upper bound).
    All datetime values are converted to Core Foundation epoch seconds via _CF_EPOCH.

    Lifecycle fields (completed, dropped) use ``IS NULL OR`` to preserve remaining
    tasks -- these filters are additive ("also show lifecycle items in this date
    range") rather than restrictive.
    """
    for field_name, column in _DATE_COLUMN_MAP.items():
        after_val = getattr(query, f"{field_name}_after", None)
        before_val = getattr(query, f"{field_name}_before", None)
        if field_name in _LIFECYCLE_DATE_FIELDS:
            if after_val is not None:
                conditions.append(f"(t.{column} IS NULL OR t.{column} >= ?)")
                params.append((after_val - _CF_EPOCH).total_seconds())
            if before_val is not None:
                conditions.append(f"(t.{column} IS NULL OR t.{column} < ?)")
                params.append((before_val - _CF_EPOCH).total_seconds())
        else:
            if after_val is not None:
                conditions.append(f"t.{column} >= ?")
                params.append((after_val - _CF_EPOCH).total_seconds())
            if before_val is not None:
                conditions.append(f"t.{column} < ?")
                params.append((before_val - _CF_EPOCH).total_seconds())


__all__ = ["TASK_ORDER_CTE", "SqlQuery", "build_list_projects_sql", "build_list_tasks_sql"]


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

# ---------------------------------------------------------------------------
# Recursive CTE for task outline ordering (ORDER-04, ORDER-05)
# ---------------------------------------------------------------------------
# Builds a sort_path from rank values at each depth level. Three anchors:
# 1. Project root tasks (the task row that IS the project) -- start of each project tree
# 2. Inbox root tasks (no parent, no project) -- prefixed with 0000000000/ to sort before projects
# 3. Recursive children -- append shifted rank to parent's sort_path
#
# The outer query uses LEFT JOIN so orphan tasks still appear (order=None).
# printf('%010d', rank + 2147483648) converts signed 32-bit rank to unsigned
# for correct lexicographic sorting (handles negative ranks from drag-and-drop).

TASK_ORDER_CTE = (
    "WITH RECURSIVE task_order(id, sort_path) AS (\n"
    "  SELECT t.persistentIdentifier,\n"
    "         printf('%010d', t.rank + 2147483648)\n"
    "  FROM Task t\n"
    "  JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task\n"
    "\n"
    "  UNION ALL\n"
    "\n"
    "  SELECT t.persistentIdentifier,\n"
    "         '0000000000/' || printf('%010d', t.rank + 2147483648)\n"
    "  FROM Task t\n"
    "  WHERE t.parent IS NULL\n"
    "    AND t.containingProjectInfo IS NULL\n"
    "    AND NOT EXISTS (SELECT 1 FROM ProjectInfo pi2 WHERE pi2.task = t.persistentIdentifier)\n"
    "\n"
    "  UNION ALL\n"
    "\n"
    "  SELECT t.persistentIdentifier,\n"
    "         o.sort_path || '/' || printf('%010d', t.rank + 2147483648)\n"
    "  FROM Task t\n"
    "  JOIN task_order o ON t.parent = o.id\n"
    ")\n"
)

_TASKS_DATA_BASE = (
    TASK_ORDER_CTE + "SELECT t.*, o.sort_path\n"
    "FROM Task t\n"
    "LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task\n"
    "LEFT JOIN task_order o ON t.persistentIdentifier = o.id\n"
    "WHERE pi.task IS NULL"
)

_PROJECTS_BASE = (
    "SELECT t.*, pi.lastReviewDate, pi.nextReviewDate,\n"
    "       pi.reviewRepetitionString, pi.nextTask, pi.folder,\n"
    "       pi.effectiveStatus, pi.containsSingletonActions\n"
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
        "(t.blocked = 0 AND t.effectiveDateCompleted IS NULL AND t.effectiveDateHidden IS NULL)"
    ),
    Availability.BLOCKED: (
        "(t.blocked != 0 AND t.effectiveDateCompleted IS NULL AND t.effectiveDateHidden IS NULL)"
    ),
    Availability.COMPLETED: (
        "(t.effectiveDateCompleted IS NOT NULL AND t.effectiveDateHidden IS NULL)"
    ),
    Availability.DROPPED: "(t.effectiveDateHidden IS NOT NULL)",
}

_PROJECT_AVAILABILITY_CLAUSES: dict[Availability, str] = {
    Availability.AVAILABLE: (
        "(pi.effectiveStatus NOT IN ('dropped','inactive')"
        " AND t.effectiveDateCompleted IS NULL AND t.effectiveDateHidden IS NULL)"
    ),
    Availability.BLOCKED: (
        "(pi.effectiveStatus = 'inactive'"
        " AND t.effectiveDateCompleted IS NULL AND t.effectiveDateHidden IS NULL)"
    ),
    Availability.COMPLETED: (
        "(t.effectiveDateCompleted IS NOT NULL AND t.effectiveDateHidden IS NULL"
        " AND pi.effectiveStatus != 'dropped')"
    ),
    Availability.DROPPED: ("(t.effectiveDateHidden IS NOT NULL OR pi.effectiveStatus = 'dropped')"),
}


def _build_availability_clause(
    values: list[Availability],
    clause_map: dict[Availability, str],
) -> str:
    """Build compound OR clause for availability filter. No params needed."""
    parts = [clause_map[v] for v in values if v in clause_map]
    if not parts:
        return "1=0"
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
        # OmniFocus only sets inInbox=1 for root-level inbox items; subtasks of
        # inbox action groups have inInbox=0 despite belonging to the inbox.
        # Inbox membership is reliably identified by containingProjectInfo being
        # NULL (no project association), which matches how _build_parent_and_project
        # already determines inbox status for the model.
        if query.in_inbox:
            conditions.append("t.containingProjectInfo IS NULL")
        else:
            conditions.append("t.containingProjectInfo IS NOT NULL")

    if query.flagged is not None:
        conditions.append("t.effectiveFlagged = ?")
        params.append(1 if query.flagged else 0)

    if query.project_ids is not None and len(query.project_ids) > 0:
        placeholders = ",".join("?" * len(query.project_ids))
        conditions.append(
            f"t.containingProjectInfo IN ("
            f"SELECT pi2.pk FROM ProjectInfo pi2 "
            f"WHERE pi2.task IN ({placeholders}))"
        )
        params.extend(query.project_ids)

    if query.tag_ids is not None and len(query.tag_ids) > 0:
        placeholders = ",".join("?" * len(query.tag_ids))
        conditions.append(
            f"t.persistentIdentifier IN ("
            f"SELECT ttg.task FROM TaskToTag ttg "
            f"WHERE ttg.tag IN ({placeholders}))"
        )
        params.extend(query.tag_ids)

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

    # Date filters (all 7 dimensions)
    _add_date_conditions(conditions, params, query)

    # -- Build WHERE clause --
    where_suffix = ""
    if conditions:
        where_suffix = " AND " + " AND ".join(conditions)

    # -- Data query (with CTE for outline ordering) --
    data_sql = _TASKS_DATA_BASE + where_suffix

    # Outline ordering via CTE sort_path (ORDER-04), ID tiebreaker for deterministic pagination
    data_sql += " ORDER BY o.sort_path, t.persistentIdentifier"
    data_params = list(params)

    if query.limit is not None:
        data_sql += " LIMIT ?"
        data_params.append(query.limit)
        if query.offset > 0:
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

    if query.folder_ids is not None and len(query.folder_ids) > 0:
        placeholders = ",".join("?" * len(query.folder_ids))
        conditions.append(f"pi.folder IN ({placeholders})")
        params.extend(query.folder_ids)

    if query.review_due_before is not None:
        conditions.append("pi.nextReviewDate IS NOT NULL AND pi.nextReviewDate <= ?")
        cf_seconds = (query.review_due_before - _CF_EPOCH).total_seconds()
        params.append(cf_seconds)

    if query.flagged is not None:
        conditions.append("t.effectiveFlagged = ?")
        params.append(1 if query.flagged else 0)

    if query.search is not None:
        conditions.append("(t.name LIKE ? COLLATE NOCASE OR t.plainTextNote LIKE ? COLLATE NOCASE)")
        params.append(f"%{query.search}%")
        params.append(f"%{query.search}%")

    # Date filters (all 7 dimensions)
    _add_date_conditions(conditions, params, query)

    # -- Build WHERE clause --
    where_clause = ""
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)

    # -- Data query --
    data_sql = _PROJECTS_BASE + where_clause

    # Deterministic ordering for pagination (ORDER BY before LIMIT/OFFSET)
    data_sql += " ORDER BY t.persistentIdentifier"
    data_params = list(params)

    if query.limit is not None:
        data_sql += " LIMIT ?"
        data_params.append(query.limit)
        if query.offset > 0:
            data_sql += " OFFSET ?"
            data_params.append(query.offset)

    # -- Count query --
    count_sql = _PROJECTS_COUNT_BASE + where_clause

    return (
        SqlQuery(sql=data_sql, params=tuple(data_params)),
        SqlQuery(sql=count_sql, params=tuple(params)),
    )
