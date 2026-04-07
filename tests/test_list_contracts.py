"""Tests for list-entity contracts: query models, ListResult[T], and model hierarchy.

Validates serialization (camelCase aliases), defaults (typed availability enums),
rejection of unknown fields (extra=forbid via StrictModel), field acceptance,
and the StrictModel/CommandModel/QueryModel inheritance hierarchy.
"""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from omnifocus_operator.agent_messages.errors import (
    AVAILABILITY_EMPTY,
    FILTER_NULL,
    OFFSET_REQUIRES_LIMIT,
    REVIEW_DUE_WITHIN_INVALID,
    TAGS_EMPTY,
)
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
from omnifocus_operator.contracts.base import UNSET, unset_to_none
from omnifocus_operator.contracts.use_cases.list._enums import (
    AvailabilityFilter,
    FolderAvailabilityFilter,
    TagAvailabilityFilter,
)
from omnifocus_operator.contracts.use_cases.list._validators import (
    reject_null_filters,
    validate_non_empty_list,
)
from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult
from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersRepoQuery
from omnifocus_operator.contracts.use_cases.list.perspectives import ListPerspectivesQuery
from omnifocus_operator.contracts.use_cases.list.projects import (
    DurationUnit,
    ListProjectsRepoQuery,
    ReviewDueFilter,
)
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

    def test_list_tasks_query_filter_fields_default_unset(self) -> None:
        query = ListTasksQuery()
        assert query.in_inbox is UNSET
        assert query.flagged is UNSET
        assert query.project is UNSET
        assert query.tags is UNSET
        assert query.estimated_minutes_max is UNSET
        assert query.search is UNSET
        assert query.limit == 50  # DEFAULT_LIST_LIMIT
        assert query.offset == 0

    def test_list_projects_query_default_availability(self) -> None:
        query = ListProjectsQuery()
        assert query.availability == [Availability.AVAILABLE, Availability.BLOCKED]

    def test_list_projects_query_filter_fields_default_unset(self) -> None:
        query = ListProjectsQuery()
        assert query.folder is UNSET
        assert query.review_due_within is UNSET
        assert query.flagged is UNSET
        assert query.limit == 50  # DEFAULT_LIST_LIMIT
        assert query.offset == 0

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
        assert query.review_due_within is not None
        assert query.review_due_within.amount == 1
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
# Offset-requires-limit validation
# ---------------------------------------------------------------------------


class TestOffsetRequiresLimit:
    """Verify offset-without-limit raises educational ValueError."""

    def test_tasks_offset_without_explicit_limit_uses_default(self) -> None:
        """offset=5 is valid because limit defaults to 50."""
        query = ListTasksQuery(offset=5)
        assert query.offset == 5
        assert query.limit == 50

    def test_tasks_offset_with_limit_none_raises(self) -> None:
        """Explicit limit=None + offset still raises."""
        with pytest.raises(ValidationError, match=re.escape(OFFSET_REQUIRES_LIMIT)):
            ListTasksQuery(offset=5, limit=None)

    def test_tasks_offset_with_limit_succeeds(self) -> None:
        query = ListTasksQuery(offset=5, limit=10)
        assert query.offset == 5
        assert query.limit == 10

    def test_tasks_limit_without_offset_uses_default_zero(self) -> None:
        query = ListTasksQuery(limit=10)
        assert query.limit == 10
        assert query.offset == 0

    def test_tasks_offset_zero_with_limit_none_succeeds(self) -> None:
        """offset=0 is the default, no error even with limit=None."""
        query = ListTasksQuery(offset=0, limit=None)
        assert query.offset == 0
        assert query.limit is None

    def test_projects_offset_without_explicit_limit_uses_default(self) -> None:
        """offset=5 is valid because limit defaults to 50."""
        query = ListProjectsQuery(offset=5)
        assert query.offset == 5
        assert query.limit == 50

    def test_projects_offset_with_limit_none_raises(self) -> None:
        """Explicit limit=None + offset still raises."""
        with pytest.raises(ValidationError, match=re.escape(OFFSET_REQUIRES_LIMIT)):
            ListProjectsQuery(offset=5, limit=None)

    def test_projects_offset_with_limit_succeeds(self) -> None:
        query = ListProjectsQuery(offset=5, limit=10)
        assert query.offset == 5
        assert query.limit == 10


# ---------------------------------------------------------------------------
# ReviewDueFilter validation
# ---------------------------------------------------------------------------


class TestReviewDueFilter:
    """Verify review_due_within parsing on ListProjectsQuery."""

    def test_1w_parses_to_weeks(self) -> None:

        query = ListProjectsQuery(review_due_within="1w")
        assert query.review_due_within is not None
        assert query.review_due_within.amount == 1
        assert query.review_due_within.unit == DurationUnit.WEEKS

    def test_2m_parses_to_months(self) -> None:

        query = ListProjectsQuery(review_due_within="2m")
        assert query.review_due_within is not None
        assert query.review_due_within.amount == 2
        assert query.review_due_within.unit == DurationUnit.MONTHS

    def test_30d_parses_to_days(self) -> None:

        query = ListProjectsQuery(review_due_within="30d")
        assert query.review_due_within is not None
        assert query.review_due_within.amount == 30
        assert query.review_due_within.unit == DurationUnit.DAYS

    def test_1y_parses_to_years(self) -> None:

        query = ListProjectsQuery(review_due_within="1y")
        assert query.review_due_within is not None
        assert query.review_due_within.amount == 1
        assert query.review_due_within.unit == DurationUnit.YEARS

    def test_now_parses_to_none_amount_and_unit(self) -> None:
        query = ListProjectsQuery(review_due_within="now")
        assert query.review_due_within is not None
        assert query.review_due_within.amount is None
        assert query.review_due_within.unit is None

    def test_invalid_string_raises(self) -> None:
        expected = REVIEW_DUE_WITHIN_INVALID.format(value="banana")
        with pytest.raises(ValidationError, match=re.escape(expected)):
            ListProjectsQuery(review_due_within="banana")

    def test_empty_string_raises(self) -> None:
        expected = REVIEW_DUE_WITHIN_INVALID.format(value="")
        with pytest.raises(ValidationError, match=re.escape(expected)):
            ListProjectsQuery(review_due_within="")

    def test_zero_amount_raises(self) -> None:
        expected = REVIEW_DUE_WITHIN_INVALID.format(value="0w")
        with pytest.raises(ValidationError, match=re.escape(expected)):
            ListProjectsQuery(review_due_within="0w")

    def test_negative_amount_raises(self) -> None:
        expected = REVIEW_DUE_WITHIN_INVALID.format(value="-1w")
        with pytest.raises(ValidationError, match=re.escape(expected)):
            ListProjectsQuery(review_due_within="-1w")

    def test_direct_construction(self) -> None:

        f = ReviewDueFilter(amount=1, unit=DurationUnit.WEEKS)
        assert f.amount == 1
        assert f.unit == DurationUnit.WEEKS

    def test_direct_construction_now(self) -> None:

        f = ReviewDueFilter(amount=None, unit=None)
        assert f.amount is None
        assert f.unit is None


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
        assert query.review_due_within is not None
        assert query.review_due_within.amount == 2


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
        assert query.limit == 50  # DEFAULT_LIST_LIMIT
        assert query.offset is None

    def test_list_projects_repo_query_default_availability(self) -> None:
        query = ListProjectsRepoQuery()
        assert query.availability == [Availability.AVAILABLE, Availability.BLOCKED]

    def test_list_projects_repo_query_other_fields_default_none(self) -> None:
        query = ListProjectsRepoQuery()
        assert query.folder_ids is None
        assert query.review_due_before is None
        assert query.flagged is None
        assert query.limit == 50  # DEFAULT_LIST_LIMIT
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
        """Non-filter fields (pagination, availability, etc.) must match."""
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
        # Fields that diverged: Query has folder/review_due_within,
        # RepoQuery has folder_ids/review_due_before
        query_only = {"folder", "review_due_within"}
        repo_only = {"folder_ids", "review_due_before"}
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


# ---------------------------------------------------------------------------
# unset_to_none utility
# ---------------------------------------------------------------------------


class TestUnsetToNone:
    """Verify unset_to_none() converts UNSET to None and passes through values."""

    def test_unset_returns_none(self) -> None:

        assert unset_to_none(UNSET) is None

    def test_string_passes_through(self) -> None:

        assert unset_to_none("hello") == "hello"

    def test_none_passes_through(self) -> None:

        assert unset_to_none(None) is None

    def test_int_passes_through(self) -> None:

        assert unset_to_none(42) == 42


# ---------------------------------------------------------------------------
# reject_null_filters validator
# ---------------------------------------------------------------------------


class TestRejectNullFilters:
    """Verify reject_null_filters() catches null values on Patch filter fields."""

    def test_null_field_raises_with_filter_null_message(self) -> None:

        with pytest.raises(ValueError, match=re.escape(FILTER_NULL.format(field="search"))):
            reject_null_filters({"search": None, "flagged": True}, ["search", "flagged"])

    def test_valid_values_pass(self) -> None:

        # Should not raise
        reject_null_filters({"search": "test", "flagged": True}, ["search", "flagged"])

    def test_missing_key_is_fine(self) -> None:

        # Missing keys = omitted = UNSET = fine
        reject_null_filters({"flagged": True}, ["search", "flagged"])

    def test_camel_case_null_raises(self) -> None:
        """reject_null_filters checks both snake_case and camelCase aliases."""

        with pytest.raises(
            ValueError, match=re.escape(FILTER_NULL.format(field="estimatedMinutesMax"))
        ):
            reject_null_filters({"estimatedMinutesMax": None}, ["estimated_minutes_max"])


# ---------------------------------------------------------------------------
# validate_non_empty_list validator
# ---------------------------------------------------------------------------


class TestValidateNonEmptyList:
    """Verify validate_non_empty_list() rejects empty lists."""

    def test_empty_list_raises_with_tags_empty_message(self) -> None:

        with pytest.raises(ValueError, match=re.escape(TAGS_EMPTY.format(field="tags"))):
            validate_non_empty_list([], "tags")

    def test_non_empty_list_passes(self) -> None:

        # Should not raise
        validate_non_empty_list(["x"], "tags")


# ---------------------------------------------------------------------------
# Null rejection on query models (Patch fields)
# ---------------------------------------------------------------------------


class TestNullRejection:
    """Verify null on any Patch filter field raises with FILTER_NULL message."""

    # --- ListTasksQuery ---

    def test_tasks_in_inbox_null_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(FILTER_NULL.format(field="inInbox"))):
            ListTasksQuery(inInbox=None)

    def test_tasks_flagged_null_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(FILTER_NULL.format(field="flagged"))):
            ListTasksQuery(flagged=None)

    def test_tasks_project_null_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(FILTER_NULL.format(field="project"))):
            ListTasksQuery(project=None)

    def test_tasks_tags_null_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(FILTER_NULL.format(field="tags"))):
            ListTasksQuery(tags=None)

    def test_tasks_estimated_minutes_max_null_raises(self) -> None:
        with pytest.raises(
            ValidationError,
            match=re.escape(FILTER_NULL.format(field="estimatedMinutesMax")),
        ):
            ListTasksQuery(estimatedMinutesMax=None)

    def test_tasks_search_null_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(FILTER_NULL.format(field="search"))):
            ListTasksQuery(search=None)

    def test_tasks_snake_case_null_also_rejected(self) -> None:
        """Snake_case keys are also checked by reject_null_filters."""
        with pytest.raises(ValidationError, match=re.escape(FILTER_NULL.format(field="inInbox"))):
            ListTasksQuery(in_inbox=None)

    # --- ListProjectsQuery ---

    def test_projects_folder_null_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(FILTER_NULL.format(field="folder"))):
            ListProjectsQuery(folder=None)

    def test_projects_review_due_within_null_raises(self) -> None:
        with pytest.raises(
            ValidationError,
            match=re.escape(FILTER_NULL.format(field="reviewDueWithin")),
        ):
            ListProjectsQuery(reviewDueWithin=None)

    def test_projects_flagged_null_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(FILTER_NULL.format(field="flagged"))):
            ListProjectsQuery(flagged=None)

    def test_projects_search_null_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(FILTER_NULL.format(field="search"))):
            ListProjectsQuery(search=None)

    # --- ListTagsQuery ---

    def test_tags_search_null_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(FILTER_NULL.format(field="search"))):
            ListTagsQuery(search=None)

    # --- ListFoldersQuery ---

    def test_folders_search_null_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(FILTER_NULL.format(field="search"))):
            ListFoldersQuery(search=None)

    # --- ListPerspectivesQuery ---

    def test_perspectives_search_null_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(FILTER_NULL.format(field="search"))):
            ListPerspectivesQuery(search=None)


# ---------------------------------------------------------------------------
# Empty list rejection on query models
# ---------------------------------------------------------------------------


class TestEmptyListRejection:
    """Verify empty tags list raises with TAGS_EMPTY message."""

    def test_tasks_empty_tags_raises(self) -> None:
        with pytest.raises(ValidationError, match=re.escape(TAGS_EMPTY.format(field="tags"))):
            ListTasksQuery(tags=[])


# ---------------------------------------------------------------------------
# AvailabilityFilter enums
# ---------------------------------------------------------------------------


class TestAvailabilityFilterEnums:
    """Verify AvailabilityFilter enums have correct members including ALL."""

    def test_availability_filter_has_all(self) -> None:

        assert AvailabilityFilter.ALL == "all"
        assert AvailabilityFilter.AVAILABLE == "available"
        assert AvailabilityFilter.BLOCKED == "blocked"
        assert AvailabilityFilter.COMPLETED == "completed"
        assert AvailabilityFilter.DROPPED == "dropped"

    def test_tag_availability_filter_has_all(self) -> None:

        assert TagAvailabilityFilter.ALL == "all"
        assert TagAvailabilityFilter.AVAILABLE == "available"
        assert TagAvailabilityFilter.BLOCKED == "blocked"
        assert TagAvailabilityFilter.DROPPED == "dropped"

    def test_folder_availability_filter_has_all(self) -> None:

        assert FolderAvailabilityFilter.ALL == "all"
        assert FolderAvailabilityFilter.AVAILABLE == "available"
        assert FolderAvailabilityFilter.DROPPED == "dropped"

    def test_enums_re_exported_from_package(self) -> None:
        from omnifocus_operator.contracts.use_cases.list import (  # noqa: PLC0415
            AvailabilityFilter,
            FolderAvailabilityFilter,
            TagAvailabilityFilter,
        )

        assert AvailabilityFilter.ALL == "all"
        assert TagAvailabilityFilter.ALL == "all"
        assert FolderAvailabilityFilter.ALL == "all"


# ---------------------------------------------------------------------------
# Availability field uses AvailabilityFilter enums
# ---------------------------------------------------------------------------


class TestAvailabilityFilterOnQueryModels:
    """Verify query models accept AvailabilityFilter values including ALL."""

    def test_tasks_accepts_all(self) -> None:

        query = ListTasksQuery(availability=[AvailabilityFilter.ALL])
        assert query.availability == [AvailabilityFilter.ALL]

    def test_tasks_accepts_mixed_all(self) -> None:

        query = ListTasksQuery(availability=[AvailabilityFilter.AVAILABLE, AvailabilityFilter.ALL])
        assert len(query.availability) == 2

    def test_projects_accepts_all(self) -> None:

        query = ListProjectsQuery(availability=[AvailabilityFilter.ALL])
        assert query.availability == [AvailabilityFilter.ALL]

    def test_tags_accepts_all(self) -> None:

        query = ListTagsQuery(availability=[TagAvailabilityFilter.ALL])
        assert query.availability == [TagAvailabilityFilter.ALL]

    def test_folders_accepts_all(self) -> None:

        query = ListFoldersQuery(availability=[FolderAvailabilityFilter.ALL])
        assert query.availability == [FolderAvailabilityFilter.ALL]


# ---------------------------------------------------------------------------
# Empty availability rejection
# ---------------------------------------------------------------------------


class TestEmptyAvailabilityRejection:
    """Verify empty availability list raises with AVAILABILITY_EMPTY message."""

    def test_tasks_empty_availability_raises(self) -> None:

        with pytest.raises(
            ValidationError, match=re.escape(AVAILABILITY_EMPTY.format(field="availability"))
        ):
            ListTasksQuery(availability=[])

    def test_projects_empty_availability_raises(self) -> None:

        with pytest.raises(
            ValidationError, match=re.escape(AVAILABILITY_EMPTY.format(field="availability"))
        ):
            ListProjectsQuery(availability=[])

    def test_tags_empty_availability_raises(self) -> None:

        with pytest.raises(
            ValidationError, match=re.escape(AVAILABILITY_EMPTY.format(field="availability"))
        ):
            ListTagsQuery(availability=[])

    def test_folders_empty_availability_raises(self) -> None:

        with pytest.raises(
            ValidationError, match=re.escape(AVAILABILITY_EMPTY.format(field="availability"))
        ):
            ListFoldersQuery(availability=[])
