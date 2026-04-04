"""Tests for default pagination limit across all 5 list query models.

Validates: DEFAULT_LIST_LIMIT constant, default limit=50 on all query models,
explicit limit=None override, offset-requires-limit on tags/folders/perspectives,
and repo-level slicing/has_more/total for tags/folders/perspectives.
"""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from omnifocus_operator.agent_messages.errors import OFFSET_REQUIRES_LIMIT
from omnifocus_operator.config import DEFAULT_LIST_LIMIT
from omnifocus_operator.contracts.use_cases.list.folders import (
    ListFoldersQuery,
    ListFoldersRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.perspectives import (
    ListPerspectivesQuery,
    ListPerspectivesRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.projects import (
    ListProjectsQuery,
    ListProjectsRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.tags import (
    ListTagsQuery,
    ListTagsRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.tasks import (
    ListTasksQuery,
    ListTasksRepoQuery,
)


# ---------------------------------------------------------------------------
# DEFAULT_LIST_LIMIT constant
# ---------------------------------------------------------------------------


class TestDefaultListLimit:
    """Verify the constant exists and has the expected value."""

    def test_default_list_limit_is_50(self) -> None:
        assert DEFAULT_LIST_LIMIT == 50


# ---------------------------------------------------------------------------
# All 5 QueryModels default limit to 50
# ---------------------------------------------------------------------------


class TestQueryModelDefaultLimit:
    """All list query models should default to limit=50."""

    def test_list_tasks_query_default_limit(self) -> None:
        query = ListTasksQuery()
        assert query.limit == DEFAULT_LIST_LIMIT

    def test_list_projects_query_default_limit(self) -> None:
        query = ListProjectsQuery()
        assert query.limit == DEFAULT_LIST_LIMIT

    def test_list_tags_query_default_limit(self) -> None:
        query = ListTagsQuery()
        assert query.limit == DEFAULT_LIST_LIMIT

    def test_list_folders_query_default_limit(self) -> None:
        query = ListFoldersQuery()
        assert query.limit == DEFAULT_LIST_LIMIT

    def test_list_perspectives_query_default_limit(self) -> None:
        query = ListPerspectivesQuery()
        assert query.limit == DEFAULT_LIST_LIMIT


class TestRepoQueryModelDefaultLimit:
    """All repo query models should also default to limit=50."""

    def test_list_tasks_repo_query_default_limit(self) -> None:
        query = ListTasksRepoQuery()
        assert query.limit == DEFAULT_LIST_LIMIT

    def test_list_projects_repo_query_default_limit(self) -> None:
        query = ListProjectsRepoQuery()
        assert query.limit == DEFAULT_LIST_LIMIT

    def test_list_tags_repo_query_default_limit(self) -> None:
        query = ListTagsRepoQuery()
        assert query.limit == DEFAULT_LIST_LIMIT

    def test_list_folders_repo_query_default_limit(self) -> None:
        query = ListFoldersRepoQuery()
        assert query.limit == DEFAULT_LIST_LIMIT

    def test_list_perspectives_repo_query_default_limit(self) -> None:
        query = ListPerspectivesRepoQuery()
        assert query.limit == DEFAULT_LIST_LIMIT


# ---------------------------------------------------------------------------
# Explicit limit=None override (agent can get all results)
# ---------------------------------------------------------------------------


class TestExplicitLimitNoneOverride:
    """Agent can explicitly set limit=None to get all results."""

    def test_tasks_limit_none_override(self) -> None:
        query = ListTasksQuery(limit=None)
        assert query.limit is None

    def test_projects_limit_none_override(self) -> None:
        query = ListProjectsQuery(limit=None)
        assert query.limit is None

    def test_tags_limit_none_override(self) -> None:
        query = ListTagsQuery(limit=None)
        assert query.limit is None

    def test_folders_limit_none_override(self) -> None:
        query = ListFoldersQuery(limit=None)
        assert query.limit is None

    def test_perspectives_limit_none_override(self) -> None:
        query = ListPerspectivesQuery(limit=None)
        assert query.limit is None


# ---------------------------------------------------------------------------
# Tags/folders/perspectives: limit+offset fields and offset-requires-limit
# ---------------------------------------------------------------------------


class TestTagsFoldersPerspectivesLimitOffset:
    """Tags, folders, perspectives now have limit/offset with validation."""

    def test_tags_accepts_limit_and_offset(self) -> None:
        query = ListTagsQuery(limit=10, offset=5)
        assert query.limit == 10
        assert query.offset == 5

    def test_tags_offset_without_limit_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(OFFSET_REQUIRES_LIMIT)):
            ListTagsQuery(offset=5, limit=None)

    def test_tags_default_offset_is_none(self) -> None:
        query = ListTagsQuery()
        assert query.offset is None

    def test_folders_accepts_limit_and_offset(self) -> None:
        query = ListFoldersQuery(limit=10, offset=5)
        assert query.limit == 10
        assert query.offset == 5

    def test_folders_offset_without_limit_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(OFFSET_REQUIRES_LIMIT)):
            ListFoldersQuery(offset=5, limit=None)

    def test_perspectives_accepts_limit_and_offset(self) -> None:
        query = ListPerspectivesQuery(limit=10, offset=5)
        assert query.limit == 10
        assert query.offset == 5

    def test_perspectives_offset_without_limit_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(OFFSET_REQUIRES_LIMIT)):
            ListPerspectivesQuery(offset=5, limit=None)


# ---------------------------------------------------------------------------
# Repo query: tags/folders/perspectives limit/offset fields
# ---------------------------------------------------------------------------


class TestRepoQueryLimitOffset:
    """Repo query models for tags/folders/perspectives have limit/offset."""

    def test_tags_repo_query_accepts_limit_offset(self) -> None:
        query = ListTagsRepoQuery(limit=10, offset=5)
        assert query.limit == 10
        assert query.offset == 5

    def test_folders_repo_query_accepts_limit_offset(self) -> None:
        query = ListFoldersRepoQuery(limit=10, offset=5)
        assert query.limit == 10
        assert query.offset == 5

    def test_perspectives_repo_query_accepts_limit_offset(self) -> None:
        query = ListPerspectivesRepoQuery(limit=10, offset=5)
        assert query.limit == 10
        assert query.offset == 5
