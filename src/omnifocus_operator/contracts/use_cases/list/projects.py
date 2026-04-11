"""Project list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from omnifocus_operator.agent_messages import errors as err
from omnifocus_operator.agent_messages.descriptions import (
    ADDED_FILTER_DESC,
    COMPLETED_FILTER_DESC,
    DEFER_FILTER_DESC,
    DROPPED_FILTER_DESC,
    DUE_FILTER_DESC,
    FLAGGED_FILTER_DESC,
    FOLDER_FILTER_DESC,
    LIMIT_DESC,
    LIST_PROJECTS_QUERY_DOC,
    MODIFIED_FILTER_DESC,
    OFFSET_DESC,
    PLANNED_FILTER_DESC,
    REVIEW_DUE_WITHIN_DESC,
    SEARCH_FIELD_NAME_NOTES,
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
    validate_duration,
    validate_offset_requires_limit,
)
from omnifocus_operator.models.enums import Availability

_PATCH_FIELDS = [
    "folder",
    "review_due_within",
    "flagged",
    "search",
    "due",
    "defer",
    "planned",
    "completed",
    "dropped",
    "added",
    "modified",
]


class ListProjectsQuery(QueryModel):
    __doc__ = LIST_PROJECTS_QUERY_DOC

    availability: list[AvailabilityFilter] = Field(default=[AvailabilityFilter.REMAINING])
    folder: Patch[str] = Field(default=UNSET, description=FOLDER_FILTER_DESC)
    review_due_within: Patch[str] = Field(default=UNSET, description=REVIEW_DUE_WITHIN_DESC)
    flagged: Patch[bool] = Field(default=UNSET, description=FLAGGED_FILTER_DESC)
    search: Patch[str] = Field(default=UNSET, description=SEARCH_FIELD_NAME_NOTES)
    due: Patch[DueDateFilter] = Field(default=UNSET, description=DUE_FILTER_DESC)
    defer: Patch[DateFilter] = Field(default=UNSET, description=DEFER_FILTER_DESC)
    planned: Patch[DateFilter] = Field(default=UNSET, description=PLANNED_FILTER_DESC)
    completed: Patch[LifecycleDateFilter] = Field(default=UNSET, description=COMPLETED_FILTER_DESC)
    dropped: Patch[LifecycleDateFilter] = Field(default=UNSET, description=DROPPED_FILTER_DESC)
    added: Patch[DateFilter] = Field(default=UNSET, description=ADDED_FILTER_DESC)
    modified: Patch[DateFilter] = Field(default=UNSET, description=MODIFIED_FILTER_DESC)
    limit: int | None = Field(default=DEFAULT_LIST_LIMIT, description=LIMIT_DESC)
    offset: int = Field(default=0, description=OFFSET_DESC)

    @field_validator("review_due_within", mode="after")
    @classmethod
    def _check_review_due_within(cls, v: str) -> str:
        if v == "now":
            return v
        try:
            validate_duration(v)
        except ValueError:
            raise ValueError(err.REVIEW_DUE_WITHIN_INVALID.format(value=v)) from None
        return v

    @model_validator(mode="before")
    @classmethod
    def _reject_nulls(cls, data: dict[str, object]) -> dict[str, object]:
        if isinstance(data, dict):
            reject_null_filters(data, _PATCH_FIELDS)
        return data

    @model_validator(mode="after")
    def _check_offset_requires_limit(self) -> ListProjectsQuery:
        validate_offset_requires_limit(self.limit, self.offset)
        return self


class ListProjectsRepoQuery(QueryModel):
    """Repo-facing query -- IDs only, service resolves names before passing."""

    availability: list[Availability] = Field(default=[Availability.AVAILABLE, Availability.BLOCKED])
    folder_ids: list[str] | None = None
    review_due_before: datetime | None = None
    flagged: bool | None = None
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
