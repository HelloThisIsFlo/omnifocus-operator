"""Tests for list-entity contracts: query models, ListResult[T], and model hierarchy.

Validates serialization (camelCase aliases), defaults (typed availability enums),
rejection of unknown fields (extra=forbid via StrictModel), field acceptance,
and the StrictModel/CommandModel/QueryModel inheritance hierarchy.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnifocus_operator.contracts import (
    CommandModel,
    ListFoldersQuery,
    ListProjectsQuery,
    ListResult,
    ListTagsQuery,
    ListTasksQuery,
    QueryModel,
    StrictModel,
)
from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult
from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersRepoQuery
from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsRepoQuery
from omnifocus_operator.contracts.use_cases.list.tags import ListTagsRepoQuery
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksRepoQuery
from omnifocus_operator.models import Task
from omnifocus_operator.models.base import OmniFocusBaseModel
from omnifocus_operator.models.enums import Availability, FolderAvailability, TagAvailability
from tests.conftest import make_model_task_dict

# ---------------------------------------------------------------------------
# StrictModel hierarchy
# ---------------------------------------------------------------------------


class TestStrictModelHierarchy:
    """Verify StrictModel is the shared base for CommandModel and QueryModel."""

    def test_strict_model_inherits_from_omnifocus_base_model(self) -> None:
        assert issubclass(StrictModel, OmniFocusBaseModel)

    def test_command_model_inherits_from_strict_model(self) -> None:
        assert issubclass(CommandModel, StrictModel)

    def test_query_model_inherits_from_strict_model(self) -> None:
        assert issubclass(QueryModel, StrictModel)

    def test_strict_model_has_extra_forbid(self) -> None:
        assert StrictModel.model_config.get("extra") == "forbid"

    def test_command_model_inherits_extra_forbid(self) -> None:
        """CommandModel gets extra=forbid from StrictModel, not its own ConfigDict."""
        assert CommandModel.model_config.get("extra") == "forbid"

    def test_query_model_inherits_extra_forbid(self) -> None:
        assert QueryModel.model_config.get("extra") == "forbid"


# ---------------------------------------------------------------------------
# ListResult serialization
# ---------------------------------------------------------------------------


class TestListResultSerialization:
    """Verify ListResult[T] serializes with camelCase aliases."""

    def test_list_result_camel_case_keys(self) -> None:
        result = ListResult[str](items=["a", "b"], total=2, has_more=False)
        dumped = result.model_dump(by_alias=True)
        assert "hasMore" in dumped
        assert "items" in dumped
        assert "total" in dumped
        assert dumped["hasMore"] is False
        assert dumped["items"] == ["a", "b"]
        assert dumped["total"] == 2

    def test_list_result_has_more_true_serializes(self) -> None:
        result = ListResult[str](items=[], total=5, has_more=True)
        dumped = result.model_dump(by_alias=True)
        assert dumped["hasMore"] is True
        assert dumped["total"] == 5
        assert dumped["items"] == []

    def test_list_result_with_task_model(self) -> None:
        task_data = make_model_task_dict()
        task = Task(**task_data)
        result = ListResult[Task](items=[task], total=1, has_more=False)
        dumped = result.model_dump(by_alias=True)
        assert len(dumped["items"]) == 1
        assert dumped["items"][0]["name"] == "Test Task"
        assert dumped["hasMore"] is False

    def test_list_result_json_schema_succeeds(self) -> None:
        """ListResult[Task].model_json_schema() produces valid schema."""
        schema = ListResult[Task].model_json_schema()
        assert "properties" in schema
        assert "items" in schema["properties"]
        assert "total" in schema["properties"]
        # hasMore is the alias for has_more
        assert "hasMore" in schema["properties"]

    def test_list_result_snake_case_construction(self) -> None:
        """ListResult can be constructed with snake_case field names."""
        result = ListResult[str](items=[], total=0, has_more=False)
        assert result.has_more is False
        assert result.total == 0


# ---------------------------------------------------------------------------
# Query model defaults
# ---------------------------------------------------------------------------


class TestQueryModelDefaults:
    """Verify each query model has correct default availability values."""

    def test_list_tasks_query_default_availability(self) -> None:
        query = ListTasksQuery()
        assert query.availability == [Availability.AVAILABLE, Availability.BLOCKED]

    def test_list_tasks_query_other_fields_default_none(self) -> None:
        query = ListTasksQuery()
        assert query.in_inbox is None
        assert query.flagged is None
        assert query.project is None
        assert query.tags is None
        assert query.estimated_minutes_max is None
        assert query.search is None
        assert query.limit is None
        assert query.offset is None

    def test_list_projects_query_default_availability(self) -> None:
        query = ListProjectsQuery()
        assert query.availability == [Availability.AVAILABLE, Availability.BLOCKED]

    def test_list_projects_query_other_fields_default_none(self) -> None:
        query = ListProjectsQuery()
        assert query.folder is None
        assert query.review_due_within is None
        assert query.flagged is None
        assert query.limit is None
        assert query.offset is None

    def test_list_tags_query_default_availability(self) -> None:
        query = ListTagsQuery()
        assert query.availability == [TagAvailability.AVAILABLE, TagAvailability.BLOCKED]

    def test_list_folders_query_default_availability(self) -> None:
        query = ListFoldersQuery()
        assert query.availability == [FolderAvailability.AVAILABLE]


# ---------------------------------------------------------------------------
# Query model rejection (extra=forbid)
# ---------------------------------------------------------------------------


class TestQueryModelRejection:
    """Verify all query models reject unknown fields."""

    def test_list_tasks_query_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="unknown_field"):
            ListTasksQuery(unknown_field="x")

    def test_list_projects_query_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="unknown_field"):
            ListProjectsQuery(unknown_field="x")

    def test_list_tags_query_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="unknown_field"):
            ListTagsQuery(unknown_field="x")

    def test_list_folders_query_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="unknown_field"):
            ListFoldersQuery(unknown_field="x")


# ---------------------------------------------------------------------------
# Query model acceptance
# ---------------------------------------------------------------------------


class TestQueryModelAcceptance:
    """Verify query models accept all defined fields with valid values."""

    def test_list_tasks_query_accepts_all_9_fields(self) -> None:
        query = ListTasksQuery(
            in_inbox=True,
            flagged=False,
            project="Work",
            tags=["Home"],
            estimated_minutes_max=30,
            availability=[Availability.AVAILABLE],
            search="test",
            limit=10,
            offset=5,
        )
        assert query.in_inbox is True
        assert query.flagged is False
        assert query.project == "Work"
        assert query.tags == ["Home"]
        assert query.estimated_minutes_max == 30
        assert query.availability == [Availability.AVAILABLE]
        assert query.search == "test"
        assert query.limit == 10
        assert query.offset == 5

    def test_list_projects_query_accepts_all_6_fields(self) -> None:
        query = ListProjectsQuery(
            availability=[Availability.AVAILABLE, Availability.COMPLETED],
            folder="Personal",
            review_due_within="1w",
            flagged=True,
            limit=20,
            offset=0,
        )
        assert query.availability == [Availability.AVAILABLE, Availability.COMPLETED]
        assert query.folder == "Personal"
        assert query.review_due_within == "1w"
        assert query.flagged is True
        assert query.limit == 20
        assert query.offset == 0

    def test_list_tasks_query_limit_zero_is_valid(self) -> None:
        """limit=0 is valid for count-only queries (D-10a)."""
        query = ListTasksQuery(limit=0)
        assert query.limit == 0

    def test_list_tasks_query_invalid_availability_raises(self) -> None:
        """Invalid availability string values are rejected by the enum."""
        with pytest.raises(ValidationError, match="invalid"):
            ListTasksQuery(availability=["invalid"])

    def test_list_tags_query_accepts_availability(self) -> None:
        query = ListTagsQuery(availability=[TagAvailability.DROPPED])
        assert query.availability == [TagAvailability.DROPPED]

    def test_list_folders_query_accepts_availability(self) -> None:
        query = ListFoldersQuery(availability=[FolderAvailability.DROPPED])
        assert query.availability == [FolderAvailability.DROPPED]


# ---------------------------------------------------------------------------
# Query model camelCase alias support
# ---------------------------------------------------------------------------


class TestQueryModelCamelCaseAliases:
    """Verify query models accept camelCase field names (from agent JSON)."""

    def test_list_tasks_query_camel_case_construction(self) -> None:
        query = ListTasksQuery(inInbox=True, estimatedMinutesMax=15)
        assert query.in_inbox is True
        assert query.estimated_minutes_max == 15

    def test_list_projects_query_camel_case_construction(self) -> None:
        query = ListProjectsQuery(reviewDueWithin="2w")
        assert query.review_due_within == "2w"


# ---------------------------------------------------------------------------
# RepoQuery models: defaults, validation, field parity
# ---------------------------------------------------------------------------


class TestRepoQueryDefaults:
    """Verify each RepoQuery model has correct default values matching its Query counterpart."""

    def test_list_tasks_repo_query_default_availability(self) -> None:
        query = ListTasksRepoQuery()
        assert query.availability == [Availability.AVAILABLE, Availability.BLOCKED]

    def test_list_tasks_repo_query_other_fields_default_none(self) -> None:
        query = ListTasksRepoQuery()
        assert query.in_inbox is None
        assert query.flagged is None
        assert query.project_ids is None
        assert query.tag_ids is None
        assert query.estimated_minutes_max is None
        assert query.search is None
        assert query.limit is None
        assert query.offset is None

    def test_list_projects_repo_query_default_availability(self) -> None:
        query = ListProjectsRepoQuery()
        assert query.availability == [Availability.AVAILABLE, Availability.BLOCKED]

    def test_list_projects_repo_query_other_fields_default_none(self) -> None:
        query = ListProjectsRepoQuery()
        assert query.folder_ids is None
        assert query.review_due_within is None
        assert query.flagged is None
        assert query.limit is None
        assert query.offset is None

    def test_list_tags_repo_query_default_availability(self) -> None:
        query = ListTagsRepoQuery()
        assert query.availability == [TagAvailability.AVAILABLE, TagAvailability.BLOCKED]

    def test_list_folders_repo_query_default_availability(self) -> None:
        query = ListFoldersRepoQuery()
        assert query.availability == [FolderAvailability.AVAILABLE]


class TestRepoQueryRejection:
    """Verify all RepoQuery models reject unknown fields (extra=forbid via QueryModel)."""

    def test_list_tasks_repo_query_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="unknown_field"):
            ListTasksRepoQuery(unknown_field="x")

    def test_list_projects_repo_query_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="unknown_field"):
            ListProjectsRepoQuery(unknown_field="x")

    def test_list_tags_repo_query_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="unknown_field"):
            ListTagsRepoQuery(unknown_field="x")

    def test_list_folders_repo_query_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="unknown_field"):
            ListFoldersRepoQuery(unknown_field="x")


class TestRepoQueryFieldParity:
    """Verify RepoQuery models have correct field relationships to their Query counterparts.

    After Phase 35.2, RepoQuery uses ID-list fields (project_ids, tag_ids, folder_ids)
    while Query uses name strings (project, tags, folder). Shared fields must still match.
    """

    def test_tasks_shared_fields_match(self) -> None:
        """Non-filter fields (pagination, availability, etc.) must match between Query and RepoQuery."""
        query_fields = set(ListTasksQuery.model_fields.keys())
        repo_fields = set(ListTasksRepoQuery.model_fields.keys())
        # Fields that diverged: Query has project/tags, RepoQuery has project_ids/tag_ids
        query_only = {"project", "tags"}
        repo_only = {"project_ids", "tag_ids"}
        assert query_fields - query_only == repo_fields - repo_only

    def test_tasks_repo_query_has_id_fields(self) -> None:
        """RepoQuery must have ID-list fields, not name fields."""
        repo_fields = set(ListTasksRepoQuery.model_fields.keys())
        assert "project_ids" in repo_fields
        assert "tag_ids" in repo_fields
        assert "project" not in repo_fields
        assert "tags" not in repo_fields

    def test_projects_shared_fields_match(self) -> None:
        """Non-filter fields must match between Query and RepoQuery."""
        query_fields = set(ListProjectsQuery.model_fields.keys())
        repo_fields = set(ListProjectsRepoQuery.model_fields.keys())
        query_only = {"folder"}
        repo_only = {"folder_ids"}
        assert query_fields - query_only == repo_fields - repo_only

    def test_projects_repo_query_has_id_fields(self) -> None:
        """RepoQuery must have ID-list fields, not name fields."""
        repo_fields = set(ListProjectsRepoQuery.model_fields.keys())
        assert "folder_ids" in repo_fields
        assert "folder" not in repo_fields

    def test_tags_field_parity(self) -> None:
        assert set(ListTagsRepoQuery.model_fields.keys()) == set(ListTagsQuery.model_fields.keys())

    def test_folders_field_parity(self) -> None:
        assert set(ListFoldersRepoQuery.model_fields.keys()) == set(
            ListFoldersQuery.model_fields.keys()
        )


# ---------------------------------------------------------------------------
# ListRepoResult
# ---------------------------------------------------------------------------


class TestListRepoResult:
    """Verify ListRepoResult construction, serialization, and field parity."""

    def test_construction(self) -> None:
        result = ListRepoResult[str](items=["a", "b"], total=2, has_more=False)
        assert result.items == ["a", "b"]
        assert result.total == 2
        assert result.has_more is False

    def test_camel_case_serialization(self) -> None:
        result = ListRepoResult[str](items=[], total=5, has_more=True)
        dumped = result.model_dump(by_alias=True)
        assert "hasMore" in dumped
        assert dumped["hasMore"] is True
        assert "items" in dumped
        assert "total" in dumped

    def test_with_task_model(self) -> None:
        task_data = make_model_task_dict()
        task = Task(**task_data)
        result = ListRepoResult[Task](items=[task], total=1, has_more=False)
        dumped = result.model_dump(by_alias=True)
        assert len(dumped["items"]) == 1
        assert dumped["items"][0]["name"] == "Test Task"

    def test_fields_subset_of_list_result(self) -> None:
        """ListRepoResult has items/total/has_more but NOT warnings (D-02d)."""
        repo_fields = set(ListRepoResult[str].model_fields.keys())
        result_fields = set(ListResult[str].model_fields.keys())
        assert repo_fields == {"items", "total", "has_more"}
        assert "warnings" in result_fields
        assert "warnings" not in repo_fields

    def test_inherits_omnifocus_base_model(self) -> None:
        assert issubclass(ListRepoResult, OmniFocusBaseModel)
