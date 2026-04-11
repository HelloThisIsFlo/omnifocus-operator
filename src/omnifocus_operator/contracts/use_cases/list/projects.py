"""Project list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator, Field, WithJsonSchema, model_validator

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
    REVIEW_DUE_FILTER_DOC,
    REVIEW_DUE_WITHIN_DESC,
    SEARCH_FIELD_NAME_NOTES,
)
from omnifocus_operator.config import DEFAULT_LIST_LIMIT
from omnifocus_operator.contracts.base import UNSET, Patch, QueryModel
from omnifocus_operator.contracts.use_cases.list._date_filter import DateFilter
from omnifocus_operator.contracts.use_cases.list._enums import (
    AvailabilityFilter,
    DateShortcut,
    DueDateShortcut,
    LifecycleDateShortcut,
)
from omnifocus_operator.contracts.use_cases.list._validators import (
    reject_null_filters,
    validate_offset_requires_limit,
)
from omnifocus_operator.models.enums import Availability, DurationUnit

_DURATION_PATTERN = re.compile(r"^(\d+)([dwmy])$")

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


class ReviewDueFilter(QueryModel):
    __doc__ = REVIEW_DUE_FILTER_DOC

    amount: int | None = None  # None for "now"
    unit: DurationUnit | None = None  # None for "now"


def parse_review_due_within(value: str) -> ReviewDueFilter:
    """Parse a duration string like '1w', '2m', 'now' into ReviewDueFilter.

    Raises ValueError with educational message on invalid format.
    """
    if not value:
        raise ValueError(err.REVIEW_DUE_WITHIN_INVALID.format(value=value))

    if value == "now":
        return ReviewDueFilter(amount=None, unit=None)

    match = _DURATION_PATTERN.match(value)
    if not match:
        raise ValueError(err.REVIEW_DUE_WITHIN_INVALID.format(value=value))

    amount = int(match.group(1))
    unit_str = match.group(2)

    if amount <= 0:
        raise ValueError(err.REVIEW_DUE_WITHIN_INVALID.format(value=value))

    return ReviewDueFilter(amount=amount, unit=DurationUnit(unit_str))


def _coerce_review_due_input(v: object) -> object:
    """Convert string input to ReviewDueFilter; pass through model instances."""
    if isinstance(v, ReviewDueFilter):
        return v
    if isinstance(v, str):
        return parse_review_due_within(v)
    raise ValueError(err.REVIEW_DUE_WITHIN_INVALID.format(value=v))


ReviewDueWithinInput = Annotated[
    ReviewDueFilter,
    BeforeValidator(_coerce_review_due_input),
    WithJsonSchema({"type": "string", "description": REVIEW_DUE_WITHIN_DESC}),
]


class ListProjectsQuery(QueryModel):
    __doc__ = LIST_PROJECTS_QUERY_DOC

    availability: list[AvailabilityFilter] = Field(default=[AvailabilityFilter.REMAINING])
    folder: Patch[str] = Field(default=UNSET, description=FOLDER_FILTER_DESC)
    review_due_within: Patch[ReviewDueWithinInput] = Field(
        default=UNSET, description=REVIEW_DUE_WITHIN_DESC
    )
    flagged: Patch[bool] = Field(default=UNSET, description=FLAGGED_FILTER_DESC)
    search: Patch[str] = Field(default=UNSET, description=SEARCH_FIELD_NAME_NOTES)
    due: Patch[DueDateShortcut | DateFilter] = Field(default=UNSET, description=DUE_FILTER_DESC)
    defer: Patch[DateShortcut | DateFilter] = Field(default=UNSET, description=DEFER_FILTER_DESC)
    planned: Patch[DateShortcut | DateFilter] = Field(
        default=UNSET, description=PLANNED_FILTER_DESC
    )
    completed: Patch[LifecycleDateShortcut | DateFilter] = Field(
        default=UNSET, description=COMPLETED_FILTER_DESC
    )
    dropped: Patch[LifecycleDateShortcut | DateFilter] = Field(
        default=UNSET, description=DROPPED_FILTER_DESC
    )
    added: Patch[DateShortcut | DateFilter] = Field(default=UNSET, description=ADDED_FILTER_DESC)
    modified: Patch[DateShortcut | DateFilter] = Field(
        default=UNSET, description=MODIFIED_FILTER_DESC
    )
    limit: int | None = Field(default=DEFAULT_LIST_LIMIT, description=LIMIT_DESC)
    offset: int = Field(default=0, description=OFFSET_DESC)

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
