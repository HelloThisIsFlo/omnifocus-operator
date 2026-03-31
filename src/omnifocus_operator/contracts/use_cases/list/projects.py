"""Project list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from omnifocus_operator.contracts.base import QueryModel
from omnifocus_operator.models.enums import Availability


class DurationUnit(StrEnum):
    """Unit for duration-based filters."""

    DAYS = "d"
    WEEKS = "w"
    MONTHS = "m"
    YEARS = "y"


class ReviewDueFilter(QueryModel):
    """Value object: parsed duration for review_due_within filter."""

    amount: int | None = None  # None for "now"
    unit: DurationUnit | None = None  # None for "now"


class ListProjectsQuery(QueryModel):
    """Agent-facing: validated filter + pagination for project listing."""

    availability: list[Availability] = Field(
        default_factory=lambda: [Availability.AVAILABLE, Availability.BLOCKED]
    )
    folder: str | None = None  # case-insensitive partial match on folder name
    review_due_within: ReviewDueFilter | None = None
    flagged: bool | None = None
    limit: int | None = None
    offset: int | None = None

    @field_validator("review_due_within", mode="before")
    @classmethod
    def _parse_review_due_within(cls, v: object) -> object:
        if v is None or isinstance(v, ReviewDueFilter):
            return v
        if isinstance(v, str):
            from omnifocus_operator.service.validate import parse_review_due_within

            return parse_review_due_within(v)
        return v

    @model_validator(mode="after")
    def _check_offset_requires_limit(self) -> ListProjectsQuery:
        from omnifocus_operator.service.validate import validate_offset_requires_limit

        validate_offset_requires_limit(self.limit, self.offset)
        return self


class ListProjectsRepoQuery(QueryModel):
    """Repo-facing query -- IDs only, service resolves names before passing."""

    availability: list[Availability] = Field(
        default_factory=lambda: [Availability.AVAILABLE, Availability.BLOCKED]
    )
    folder_ids: list[str] | None = None
    review_due_before: datetime | None = None
    flagged: bool | None = None
    limit: int | None = None
    offset: int | None = None
