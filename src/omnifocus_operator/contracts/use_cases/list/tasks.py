"""Task list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from omnifocus_operator.agent_messages import errors as err
from omnifocus_operator.agent_messages.descriptions import (
    ADDED_FILTER_DESC,
    COMPLETED_FILTER_DESC,
    DEFER_FILTER_DESC,
    DROPPED_FILTER_DESC,
    DUE_FILTER_DESC,
    ESTIMATED_MINUTES_MAX_DESC,
    FLAGGED_FILTER_DESC,
    IN_INBOX_FILTER_DESC,
    INCLUDE_FIELD_DESC,
    LIMIT_DESC,
    LIST_TASKS_QUERY_DOC,
    MODIFIED_FILTER_DESC,
    OFFSET_DESC,
    ONLY_FIELD_DESC,
    PARENT_FILTER_DESC,
    PLANNED_FILTER_DESC,
    PROJECT_FILTER_DESC,
    SEARCH_FIELD_NAME_NOTES,
    TAGS_FILTER_DESC,
)
from omnifocus_operator.config import DEFAULT_LIST_LIMIT
from omnifocus_operator.contracts.base import UNSET, Patch, QueryModel
from omnifocus_operator.contracts.use_cases.list._date_filter import (
    DateFilter,
    DueDateFilter,
    LifecycleDateFilter,
)
from omnifocus_operator.contracts.use_cases.list._enums import (
    AvailabilityFilter,
)
from omnifocus_operator.contracts.use_cases.list._validators import (
    reject_null_filters,
    validate_non_empty_list,
    validate_offset_requires_limit,
)
from omnifocus_operator.models.enums import Availability

TaskFieldGroup = Literal["notes", "metadata", "hierarchy", "time", "*"]

_TASK_FIELD_GROUPS_VALID: set[str] = {"notes", "metadata", "hierarchy", "time", "*"}

_PATCH_FIELDS = [
    "in_inbox",
    "flagged",
    "project",
    "parent",
    "tags",
    "estimated_minutes_max",
    "search",
    "due",
    "defer",
    "planned",
    "completed",
    "dropped",
    "added",
    "modified",
]


class ListTasksQuery(QueryModel):
    __doc__ = LIST_TASKS_QUERY_DOC

    in_inbox: Patch[bool] = Field(default=UNSET, description=IN_INBOX_FILTER_DESC)
    flagged: Patch[bool] = Field(default=UNSET, description=FLAGGED_FILTER_DESC)
    project: Patch[str] = Field(default=UNSET, description=PROJECT_FILTER_DESC)
    parent: Patch[str] = Field(default=UNSET, description=PARENT_FILTER_DESC)
    tags: Patch[list[str]] = Field(default=UNSET, description=TAGS_FILTER_DESC)
    estimated_minutes_max: Patch[int] = Field(default=UNSET, description=ESTIMATED_MINUTES_MAX_DESC)
    availability: list[AvailabilityFilter] = Field(default=[AvailabilityFilter.REMAINING])
    search: Patch[str] = Field(default=UNSET, description=SEARCH_FIELD_NAME_NOTES)
    due: Patch[DueDateFilter] = Field(default=UNSET, description=DUE_FILTER_DESC)
    defer: Patch[DateFilter] = Field(default=UNSET, description=DEFER_FILTER_DESC)
    planned: Patch[DateFilter] = Field(default=UNSET, description=PLANNED_FILTER_DESC)
    completed: Patch[LifecycleDateFilter] = Field(default=UNSET, description=COMPLETED_FILTER_DESC)
    dropped: Patch[LifecycleDateFilter] = Field(default=UNSET, description=DROPPED_FILTER_DESC)
    added: Patch[DateFilter] = Field(default=UNSET, description=ADDED_FILTER_DESC)
    modified: Patch[DateFilter] = Field(default=UNSET, description=MODIFIED_FILTER_DESC)
    include: list[TaskFieldGroup] = Field(default=[], description=INCLUDE_FIELD_DESC)
    only: list[str] = Field(default=[], description=ONLY_FIELD_DESC)
    limit: int | None = Field(default=DEFAULT_LIST_LIMIT, description=LIMIT_DESC)
    offset: int = Field(default=0, description=OFFSET_DESC)

    @model_validator(mode="before")
    @classmethod
    def _reject_nulls(cls, data: dict[str, object]) -> dict[str, object]:
        if isinstance(data, dict):
            reject_null_filters(data, _PATCH_FIELDS)
        return data

    @field_validator("include", mode="before")
    @classmethod
    def _validate_include(cls, v: list[str]) -> list[str]:
        if not isinstance(v, list):
            return v  # Let Pydantic handle type validation
        invalid = [g for g in v if g not in _TASK_FIELD_GROUPS_VALID]
        if invalid:
            raise ValueError(
                err.INCLUDE_INVALID_TASK.format(groups=", ".join(repr(g) for g in invalid))
            )
        return v

    @field_validator("tags", mode="after")
    @classmethod
    def _reject_empty_tags(cls, v: list[str]) -> list[str]:
        validate_non_empty_list(v, "tags")
        return v

    @model_validator(mode="after")
    def _check_offset_requires_limit(self) -> ListTasksQuery:
        validate_offset_requires_limit(self.limit, self.offset)
        return self


class ListTasksRepoQuery(QueryModel):
    """Repo-facing query -- IDs only, service resolves names before passing."""

    in_inbox: bool | None = None
    flagged: bool | None = None
    candidate_task_ids: list[str] | None = None
    pinned_task_ids: list[str] | None = None
    tag_ids: list[str] | None = None
    estimated_minutes_max: int | None = None
    availability: list[Availability] = Field(default=[Availability.AVAILABLE, Availability.BLOCKED])
    search: str | None = None
    limit: int | None = DEFAULT_LIST_LIMIT
    offset: int = 0
    due_after: datetime | None = None
    due_before: datetime | None = None
    defer_after: datetime | None = None
    defer_before: datetime | None = None
    planned_after: datetime | None = None
    planned_before: datetime | None = None
    completed_after: datetime | None = None
    completed_before: datetime | None = None
    dropped_after: datetime | None = None
    dropped_before: datetime | None = None
    added_after: datetime | None = None
    added_before: datetime | None = None
    modified_after: datetime | None = None
    modified_before: datetime | None = None
