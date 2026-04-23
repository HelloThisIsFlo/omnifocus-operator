"""Tests for parameterized SQL query builder.

Validates that build_list_tasks_sql and build_list_projects_sql produce
correct parameterized SQL with ? placeholders (INFRA-01) for every filter
field, combination, and edge case.
"""

from __future__ import annotations

from datetime import UTC, datetime

from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsRepoQuery
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksRepoQuery
from omnifocus_operator.models.enums import Availability
from omnifocus_operator.repository.hybrid.query_builder import (
    SqlQuery,
    build_list_projects_sql,
    build_list_tasks_sql,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_parameterized(sql: str) -> None:
    """Assert SQL uses ? placeholders and no f-string interpolation."""
    # Should not contain Python f-string markers in actual SQL
    assert "f'" not in sql
    assert 'f"' not in sql


# ===========================================================================
# build_list_tasks_sql
# ===========================================================================


class TestTasksDefaultQuery:
    """Default query with no filters should include only default availability."""

    def test_returns_data_and_count_queries(self):
        query = ListTasksRepoQuery()
        data_q, count_q = build_list_tasks_sql(query)
        assert isinstance(data_q, SqlQuery)
        assert isinstance(count_q, SqlQuery)

    def test_data_query_has_base_sql(self):
        query = ListTasksRepoQuery()
        data_q, _ = build_list_tasks_sql(query)
        assert "FROM Task t" in data_q.sql
        assert "LEFT JOIN ProjectInfo pi" in data_q.sql
        assert "WHERE pi.task IS NULL" in data_q.sql

    def test_count_query_has_select_count(self):
        query = ListTasksRepoQuery()
        _, count_q = build_list_tasks_sql(query)
        assert "SELECT COUNT(*)" in count_q.sql
        assert "LIMIT" not in count_q.sql
        assert "OFFSET" not in count_q.sql

    def test_default_availability_clause_present(self):
        """Default availability=[available, blocked] produces compound OR."""
        query = ListTasksRepoQuery()
        data_q, _ = build_list_tasks_sql(query)
        # Should contain availability-related conditions
        assert "blocked" in data_q.sql.lower() or "effectiveDateCompleted" in data_q.sql
        assert "effectiveDateHidden" in data_q.sql


class TestTasksInInboxFilter:
    def test_in_inbox_true(self):
        query = ListTasksRepoQuery(in_inbox=True)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.containingProjectInfo IS NULL" in data_q.sql

    def test_in_inbox_false(self):
        query = ListTasksRepoQuery(in_inbox=False)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.containingProjectInfo IS NOT NULL" in data_q.sql

    def test_in_inbox_true_adds_no_bind_params(self):
        """containingProjectInfo IS NULL needs no extra bind params beyond defaults."""
        baseline = ListTasksRepoQuery()
        baseline_q, _ = build_list_tasks_sql(baseline)
        query = ListTasksRepoQuery(in_inbox=True)
        data_q, _ = build_list_tasks_sql(query)
        # IS NULL adds no bind params — same count as baseline
        assert len(data_q.params) == len(baseline_q.params)

    def test_in_inbox_false_adds_no_bind_params(self):
        """containingProjectInfo IS NOT NULL needs no extra bind params beyond defaults."""
        baseline = ListTasksRepoQuery()
        baseline_q, _ = build_list_tasks_sql(baseline)
        query = ListTasksRepoQuery(in_inbox=False)
        data_q, _ = build_list_tasks_sql(query)
        assert len(data_q.params) == len(baseline_q.params)


class TestTasksFlaggedFilter:
    def test_flagged_true(self):
        query = ListTasksRepoQuery(flagged=True)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.effectiveFlagged = ?" in data_q.sql
        assert 1 in data_q.params

    def test_flagged_false(self):
        query = ListTasksRepoQuery(flagged=False)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.effectiveFlagged = ?" in data_q.sql
        assert 0 in data_q.params


class TestTasksScopeFilter:
    """Post-Phase 57: task_id_scope is the unified scope primitive.

    The list passed is the set of TASK PKs to keep — service layer
    (get_tasks_subtree) handles project-to-tasks expansion before this point.
    The old ``ProjectInfo pi2`` scope subquery is gone; this is a direct
    indexed PK lookup (``t.persistentIdentifier IN (?, ...)``).

    Note: an unrelated ``ProjectInfo pi2`` subquery persists in the outline
    CTE for root-task detection — ``NOT EXISTS (SELECT 1 FROM ProjectInfo pi2 ...)``.
    These tests assert on the scope-filter WHERE clause shape, not on the
    absence of the literal string.
    """

    def test_task_id_scope_direct_in_clause(self):
        query = ListTasksRepoQuery(task_id_scope=["task-id-1"])
        data_q, _ = build_list_tasks_sql(query)
        assert "t.persistentIdentifier IN (?)" in data_q.sql
        assert "task-id-1" in data_q.params
        # The retired scope-filter subquery is gone.
        assert "pi2.task IN" not in data_q.sql
        assert "t.containingProjectInfo IN" not in data_q.sql

    def test_multiple_task_id_scope(self):
        query = ListTasksRepoQuery(task_id_scope=["task-1", "task-2"])
        data_q, _ = build_list_tasks_sql(query)
        assert "t.persistentIdentifier IN (?,?)" in data_q.sql
        assert "task-1" in data_q.params
        assert "task-2" in data_q.params
        assert "pi2.task IN" not in data_q.sql
        assert "t.containingProjectInfo IN" not in data_q.sql


class TestTasksTagsFilter:
    def test_single_tag(self):
        query = ListTasksRepoQuery(tag_ids=["id1"])
        data_q, _ = build_list_tasks_sql(query)
        assert "TaskToTag" in data_q.sql
        assert "IN (?)" in data_q.sql
        assert "id1" in data_q.params

    def test_multiple_tags(self):
        query = ListTasksRepoQuery(tag_ids=["id1", "id2", "id3"])
        data_q, _ = build_list_tasks_sql(query)
        assert "IN (?,?,?)" in data_q.sql
        assert "id1" in data_q.params
        assert "id2" in data_q.params
        assert "id3" in data_q.params


class TestTasksEstimatedMinutesFilter:
    def test_estimated_minutes_max(self):
        query = ListTasksRepoQuery(estimated_minutes_max=30)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.estimatedMinutes <= ?" in data_q.sql
        assert 30 in data_q.params


class TestTasksSearchFilter:
    def test_search_name_and_note(self):
        query = ListTasksRepoQuery(search="foo")
        data_q, _ = build_list_tasks_sql(query)
        assert "t.name LIKE ? COLLATE NOCASE" in data_q.sql
        assert "t.plainTextNote LIKE ? COLLATE NOCASE" in data_q.sql
        assert "%foo%" in data_q.params
        # Two params for search (name + note)
        assert data_q.params.count("%foo%") == 2


class TestTasksAvailabilityFilter:
    def test_available_only(self):
        query = ListTasksRepoQuery(availability=[Availability.AVAILABLE])
        data_q, _ = build_list_tasks_sql(query)
        # available: not blocked, not completed, not dropped
        assert "t.blocked = 0" in data_q.sql or "t.blocked" in data_q.sql
        assert "t.effectiveDateCompleted IS NULL" in data_q.sql
        assert "t.effectiveDateHidden IS NULL" in data_q.sql

    def test_blocked_only(self):
        query = ListTasksRepoQuery(availability=[Availability.BLOCKED])
        data_q, _ = build_list_tasks_sql(query)
        assert "t.blocked" in data_q.sql

    def test_completed_only(self):
        query = ListTasksRepoQuery(availability=[Availability.COMPLETED])
        data_q, _ = build_list_tasks_sql(query)
        assert "t.effectiveDateCompleted IS NOT NULL" in data_q.sql

    def test_dropped_only(self):
        query = ListTasksRepoQuery(availability=[Availability.DROPPED])
        data_q, _ = build_list_tasks_sql(query)
        assert "t.effectiveDateHidden IS NOT NULL" in data_q.sql

    def test_available_and_blocked(self):
        """Default combo should produce OR of two conditions."""
        query = ListTasksRepoQuery(availability=[Availability.AVAILABLE, Availability.BLOCKED])
        data_q, _ = build_list_tasks_sql(query)
        assert " OR " in data_q.sql

    def test_all_four_values(self):
        query = ListTasksRepoQuery(
            availability=[
                Availability.AVAILABLE,
                Availability.BLOCKED,
                Availability.COMPLETED,
                Availability.DROPPED,
            ]
        )
        data_q, _ = build_list_tasks_sql(query)
        # All 4 values -> 4 OR branches
        assert data_q.sql.count(" OR ") >= 3

    def test_no_user_params_in_availability(self):
        """Availability clauses use column comparisons, no user-provided params.

        Only the default LIMIT param (50) should be present -- no availability params.
        """
        query = ListTasksRepoQuery(availability=[Availability.AVAILABLE])
        data_q, _ = build_list_tasks_sql(query)
        # Only the default LIMIT param (50) -- no availability params
        assert data_q.params == (50,)


class TestTasksLimitOffset:
    def test_limit(self):
        query = ListTasksRepoQuery(limit=10)
        data_q, count_q = build_list_tasks_sql(query)
        assert "LIMIT ?" in data_q.sql
        assert 10 in data_q.params
        assert "LIMIT" not in count_q.sql

    def test_limit_and_offset(self):
        query = ListTasksRepoQuery(limit=10, offset=5)
        data_q, count_q = build_list_tasks_sql(query)
        assert "LIMIT ?" in data_q.sql
        assert "OFFSET ?" in data_q.sql
        assert 10 in data_q.params
        assert 5 in data_q.params
        assert "LIMIT" not in count_q.sql
        assert "OFFSET" not in count_q.sql

    def test_order_by_before_limit(self):
        """ORDER BY must appear before LIMIT for deterministic pagination."""
        query = ListTasksRepoQuery(limit=10)
        data_q, _ = build_list_tasks_sql(query)
        assert "ORDER BY o.sort_path, t.persistentIdentifier" in data_q.sql
        order_pos = data_q.sql.index("ORDER BY")
        limit_pos = data_q.sql.index("LIMIT")
        assert order_pos < limit_pos

    def test_limit_zero_produces_limit_zero(self):
        """limit=0 means count-only; data query should have LIMIT 0."""
        query = ListTasksRepoQuery(limit=0)
        data_q, _ = build_list_tasks_sql(query)
        assert "LIMIT ?" in data_q.sql
        assert 0 in data_q.params

    def test_offset_without_limit_ignored(self):
        """offset without limit should not produce OFFSET clause."""
        query = ListTasksRepoQuery(offset=5, limit=None)
        data_q, _ = build_list_tasks_sql(query)
        assert "OFFSET" not in data_q.sql

    def test_order_by_always_present(self):
        """ORDER BY is always present on data queries for deterministic results."""
        query = ListTasksRepoQuery()
        data_q, count_q = build_list_tasks_sql(query)
        assert "ORDER BY o.sort_path, t.persistentIdentifier" in data_q.sql
        assert "ORDER BY" not in count_q.sql


class TestTasksCombinedFilters:
    def test_inbox_and_flagged(self):
        query = ListTasksRepoQuery(in_inbox=True, flagged=True)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.containingProjectInfo IS NULL" in data_q.sql
        assert "t.effectiveFlagged = ?" in data_q.sql
        assert 1 in data_q.params

    def test_multiple_filters_with_limit(self):
        query = ListTasksRepoQuery(
            flagged=True,
            task_id_scope=["task-id-1"],
            search="urgent",
            limit=5,
        )
        data_q, count_q = build_list_tasks_sql(query)
        assert "t.effectiveFlagged = ?" in data_q.sql
        assert "t.persistentIdentifier IN (?)" in data_q.sql
        assert "LIKE ? COLLATE NOCASE" in data_q.sql
        assert "LIMIT ?" in data_q.sql
        # Verify param ordering: flagged, task_id_scope, search(x2), availability, limit
        assert 1 in data_q.params  # flagged
        assert "task-id-1" in data_q.params  # task_id_scope
        assert "%urgent%" in data_q.params  # search
        assert 5 in data_q.params  # limit
        # Count query should NOT have LIMIT
        assert "LIMIT" not in count_q.sql

    def test_count_query_same_where_as_data_query(self):
        """Count query should have identical WHERE clauses (minus LIMIT/OFFSET)."""
        query = ListTasksRepoQuery(flagged=True, search="test", limit=10, offset=5)
        _data_q, count_q = build_list_tasks_sql(query)
        # Both should have the same filter params (minus limit/offset)
        # Count params should be a subset of data params
        assert "t.effectiveFlagged = ?" in count_q.sql
        assert "LIKE ? COLLATE NOCASE" in count_q.sql
        # Count params = data params minus limit and offset params
        assert 1 in count_q.params  # flagged
        assert "%test%" in count_q.params  # search

    def test_all_params_use_placeholders(self):
        """No user values should appear in SQL string itself."""
        query = ListTasksRepoQuery(
            in_inbox=True,
            flagged=True,
            task_id_scope=["proj-id-1"],
            tag_ids=["tag1"],
            estimated_minutes_max=60,
            search="foo",
            limit=10,
            offset=5,
        )
        data_q, _ = build_list_tasks_sql(query)
        _assert_parameterized(data_q.sql)
        # User values should be in params, not in SQL
        assert "proj-id-1" not in data_q.sql
        assert "tag1" not in data_q.sql
        assert "foo" not in data_q.sql


# ===========================================================================
# build_list_projects_sql
# ===========================================================================


class TestProjectsDefaultQuery:
    def test_returns_data_and_count_queries(self):
        query = ListProjectsRepoQuery()
        data_q, count_q = build_list_projects_sql(query)
        assert isinstance(data_q, SqlQuery)
        assert isinstance(count_q, SqlQuery)

    def test_data_query_has_base_sql(self):
        query = ListProjectsRepoQuery()
        data_q, _ = build_list_projects_sql(query)
        assert "FROM Task t" in data_q.sql
        assert "JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task" in data_q.sql

    def test_data_query_selects_project_columns(self):
        query = ListProjectsRepoQuery()
        data_q, _ = build_list_projects_sql(query)
        assert "pi.lastReviewDate" in data_q.sql
        assert "pi.nextReviewDate" in data_q.sql
        assert "pi.folder" in data_q.sql
        assert "pi.effectiveStatus" in data_q.sql

    def test_count_query_has_select_count(self):
        query = ListProjectsRepoQuery()
        _, count_q = build_list_projects_sql(query)
        assert "SELECT COUNT(*)" in count_q.sql
        assert "LIMIT" not in count_q.sql


class TestProjectsAvailabilityFilter:
    def test_available_only(self):
        query = ListProjectsRepoQuery(availability=[Availability.AVAILABLE])
        data_q, _ = build_list_projects_sql(query)
        assert "pi.effectiveStatus" in data_q.sql
        assert "t.effectiveDateCompleted IS NULL" in data_q.sql
        assert "t.effectiveDateHidden IS NULL" in data_q.sql

    def test_blocked_only(self):
        """Blocked projects have effectiveStatus = 'inactive'."""
        query = ListProjectsRepoQuery(availability=[Availability.BLOCKED])
        data_q, _ = build_list_projects_sql(query)
        assert "inactive" in data_q.sql

    def test_completed_only(self):
        query = ListProjectsRepoQuery(availability=[Availability.COMPLETED])
        data_q, _ = build_list_projects_sql(query)
        assert "t.effectiveDateCompleted IS NOT NULL" in data_q.sql

    def test_dropped_only(self):
        query = ListProjectsRepoQuery(availability=[Availability.DROPPED])
        data_q, _ = build_list_projects_sql(query)
        assert "t.effectiveDateHidden IS NOT NULL" in data_q.sql or "dropped" in data_q.sql

    def test_available_and_blocked_produces_or(self):
        query = ListProjectsRepoQuery(availability=[Availability.AVAILABLE, Availability.BLOCKED])
        data_q, _ = build_list_projects_sql(query)
        assert " OR " in data_q.sql


class TestProjectsFolderFilter:
    def test_single_folder_id(self):
        query = ListProjectsRepoQuery(folder_ids=["folder-id-1"])
        data_q, _ = build_list_projects_sql(query)
        assert "pi.folder IN (?)" in data_q.sql
        assert "folder-id-1" in data_q.params

    def test_multiple_folder_ids(self):
        query = ListProjectsRepoQuery(folder_ids=["folder-1", "folder-2"])
        data_q, _ = build_list_projects_sql(query)
        assert "pi.folder IN (?,?)" in data_q.sql
        assert "folder-1" in data_q.params
        assert "folder-2" in data_q.params


class TestProjectsReviewDueBeforeFilter:
    def test_review_due_before_converts_to_cf_epoch(self):
        dt = datetime(2026, 4, 7, tzinfo=UTC)
        query = ListProjectsRepoQuery(review_due_before=dt)
        data_q, _ = build_list_projects_sql(query)
        assert "pi.nextReviewDate IS NOT NULL" in data_q.sql
        assert "pi.nextReviewDate <= ?" in data_q.sql
        expected_cf = (dt - datetime(2001, 1, 1, tzinfo=UTC)).total_seconds()
        assert expected_cf in data_q.params


class TestProjectsFlaggedFilter:
    def test_flagged_true(self):
        query = ListProjectsRepoQuery(flagged=True)
        data_q, _ = build_list_projects_sql(query)
        assert "t.effectiveFlagged = ?" in data_q.sql
        assert 1 in data_q.params

    def test_flagged_false(self):
        query = ListProjectsRepoQuery(flagged=False)
        data_q, _ = build_list_projects_sql(query)
        assert "t.effectiveFlagged = ?" in data_q.sql
        assert 0 in data_q.params


class TestProjectsLimitOffset:
    def test_limit(self):
        query = ListProjectsRepoQuery(limit=20)
        data_q, count_q = build_list_projects_sql(query)
        assert "LIMIT ?" in data_q.sql
        assert 20 in data_q.params
        assert "LIMIT" not in count_q.sql

    def test_limit_and_offset(self):
        query = ListProjectsRepoQuery(limit=20, offset=10)
        data_q, count_q = build_list_projects_sql(query)
        assert "LIMIT ?" in data_q.sql
        assert "OFFSET ?" in data_q.sql
        assert "LIMIT" not in count_q.sql

    def test_order_by_before_limit(self):
        """ORDER BY must appear before LIMIT for deterministic pagination."""
        query = ListProjectsRepoQuery(limit=20)
        data_q, _ = build_list_projects_sql(query)
        assert "ORDER BY t.persistentIdentifier" in data_q.sql
        order_pos = data_q.sql.index("ORDER BY")
        limit_pos = data_q.sql.index("LIMIT")
        assert order_pos < limit_pos

    def test_order_by_always_present(self):
        """ORDER BY is always present on data queries for deterministic results."""
        query = ListProjectsRepoQuery()
        data_q, count_q = build_list_projects_sql(query)
        assert "ORDER BY t.persistentIdentifier" in data_q.sql
        assert "ORDER BY" not in count_q.sql


class TestProjectsCombinedFilters:
    def test_folder_and_flagged_with_limit(self):
        query = ListProjectsRepoQuery(
            folder_ids=["folder-id-1"],
            flagged=True,
            limit=5,
        )
        data_q, _ = build_list_projects_sql(query)
        assert "pi.folder IN (?)" in data_q.sql
        assert "t.effectiveFlagged = ?" in data_q.sql
        assert "LIMIT ?" in data_q.sql
        assert "folder-id-1" in data_q.params
        assert 1 in data_q.params  # flagged
        assert 5 in data_q.params  # limit

    def test_all_params_use_placeholders(self):
        """No user values should appear in SQL string itself."""
        query = ListProjectsRepoQuery(
            folder_ids=["folder-id-1"],
            flagged=True,
            review_due_before=datetime(2026, 4, 5, tzinfo=UTC),
            limit=10,
        )
        data_q, _ = build_list_projects_sql(query)
        _assert_parameterized(data_q.sql)
        assert "folder-id-1" not in data_q.sql


# ===========================================================================
# SqlQuery structure
# ===========================================================================


class TestDatePredicates:
    """Date predicate generation for all 7 date dimensions."""

    # Reference datetime and its CF epoch float
    _REF_DT = datetime(2026, 4, 7, 14, 0, 0, tzinfo=UTC)
    _CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)
    _REF_CF_SECONDS = (_REF_DT - _CF_EPOCH).total_seconds()

    def test_due_after(self):
        query = ListTasksRepoQuery(due_after=self._REF_DT)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.effectiveDateDue >= ?" in data_q.sql
        assert self._REF_CF_SECONDS in data_q.params

    def test_due_before(self):
        query = ListTasksRepoQuery(due_before=self._REF_DT)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.effectiveDateDue < ?" in data_q.sql
        assert self._REF_CF_SECONDS in data_q.params

    def test_due_after_and_before(self):
        after_dt = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        before_dt = datetime(2026, 4, 10, 0, 0, 0, tzinfo=UTC)
        query = ListTasksRepoQuery(due_after=after_dt, due_before=before_dt)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.effectiveDateDue >= ?" in data_q.sql
        assert "t.effectiveDateDue < ?" in data_q.sql
        after_cf = (after_dt - self._CF_EPOCH).total_seconds()
        before_cf = (before_dt - self._CF_EPOCH).total_seconds()
        assert after_cf in data_q.params
        assert before_cf in data_q.params

    def test_completed_after(self):
        query = ListTasksRepoQuery(completed_after=self._REF_DT)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.effectiveDateCompleted >= ?" in data_q.sql
        assert self._REF_CF_SECONDS in data_q.params

    def test_dropped_before(self):
        query = ListTasksRepoQuery(dropped_before=self._REF_DT)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.effectiveDateHidden < ?" in data_q.sql
        assert self._REF_CF_SECONDS in data_q.params

    def test_added_after(self):
        query = ListTasksRepoQuery(added_after=self._REF_DT)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.dateAdded >= ?" in data_q.sql
        assert self._REF_CF_SECONDS in data_q.params

    def test_modified_before(self):
        query = ListTasksRepoQuery(modified_before=self._REF_DT)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.dateModified < ?" in data_q.sql
        assert self._REF_CF_SECONDS in data_q.params

    def test_defer_after(self):
        query = ListTasksRepoQuery(defer_after=self._REF_DT)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.effectiveDateToStart >= ?" in data_q.sql
        assert self._REF_CF_SECONDS in data_q.params

    def test_planned_before(self):
        query = ListTasksRepoQuery(planned_before=self._REF_DT)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.effectiveDatePlanned < ?" in data_q.sql
        assert self._REF_CF_SECONDS in data_q.params

    def test_date_predicates_combine_with_existing_filters(self):
        """flagged + due_after -> both conditions in WHERE clause."""
        query = ListTasksRepoQuery(flagged=True, due_after=self._REF_DT)
        data_q, _ = build_list_tasks_sql(query)
        assert "t.effectiveFlagged = ?" in data_q.sql
        assert "t.effectiveDateDue >= ?" in data_q.sql
        assert 1 in data_q.params  # flagged
        assert self._REF_CF_SECONDS in data_q.params  # due_after

    def test_cf_epoch_conversion_correct(self):
        """Verify CF epoch conversion matches manual calculation."""
        dt = datetime(2026, 4, 7, 14, 0, 0, tzinfo=UTC)
        expected = (dt - datetime(2001, 1, 1, tzinfo=UTC)).total_seconds()
        query = ListTasksRepoQuery(due_after=dt)
        data_q, _ = build_list_tasks_sql(query)
        # Find the CF seconds param (not the LIMIT param)
        cf_params = [p for p in data_q.params if isinstance(p, float)]
        assert expected in cf_params

    def test_count_query_has_same_date_predicates(self):
        """Count query has same date predicates but no LIMIT/OFFSET."""
        query = ListTasksRepoQuery(due_after=self._REF_DT, limit=10, offset=5)
        data_q, count_q = build_list_tasks_sql(query)
        assert "t.effectiveDateDue >= ?" in data_q.sql
        assert "t.effectiveDateDue >= ?" in count_q.sql
        assert self._REF_CF_SECONDS in count_q.params
        assert "LIMIT" not in count_q.sql
        assert "OFFSET" not in count_q.sql

    def test_no_date_fields_no_date_predicates(self):
        """Query with no date fields set produces no date predicates (backward compatible).

        Note: availability clauses reference effectiveDateCompleted/Hidden with IS [NOT] NULL,
        so we check specifically for the >= / < operators that date predicates use.
        """
        query = ListTasksRepoQuery()
        data_q, _ = build_list_tasks_sql(query)
        for col in [
            "effectiveDateDue",
            "effectiveDateToStart",
            "effectiveDatePlanned",
            "effectiveDateCompleted",
            "effectiveDateHidden",
            "dateAdded",
            "dateModified",
        ]:
            assert f"t.{col} >= ?" not in data_q.sql
            assert f"t.{col} < ?" not in data_q.sql


class TestSqlQueryNamedTuple:
    def test_sql_query_has_sql_and_params(self):
        sq = SqlQuery(sql="SELECT 1", params=(42,))
        assert sq.sql == "SELECT 1"
        assert sq.params == (42,)

    def test_sql_query_is_immutable_tuple(self):
        sq = SqlQuery(sql="SELECT 1", params=())
        assert isinstance(sq, tuple)
        assert len(sq) == 2
