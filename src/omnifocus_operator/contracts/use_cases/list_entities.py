"""List-entity contracts: query models and generic result container.

Defines validated filter + pagination models for all list operations
and the uniform ListResult[T] response shape.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import Field

from omnifocus_operator.contracts.base import QueryModel
from omnifocus_operator.models.base import OmniFocusBaseModel
from omnifocus_operator.models.enums import (
    Availability,
    FolderAvailability,
    TagAvailability,
)

T = TypeVar("T")


class ListResult(OmniFocusBaseModel, Generic[T]):
    """Generic result container for all list operations.

    Uniform shape for all 5 list tools. Non-paginated: total=len(items), has_more=False.
    """

    items: list[T]
    total: int
    has_more: bool


class ListTasksQuery(QueryModel):
    """Validated filter + pagination for task listing.

    All filter fields optional. Unknown fields rejected (extra=forbid via QueryModel).
    """

    in_inbox: bool | None = None
    flagged: bool | None = None
    project: str | None = None  # case-insensitive partial match on project name
    tags: list[str] | None = None  # tag names (OR logic), service resolves to IDs
    estimated_minutes_max: int | None = None
    availability: list[Availability] = Field(
        default_factory=lambda: [Availability.AVAILABLE, Availability.BLOCKED]
    )
    search: str | None = None  # case-insensitive substring in name+notes
    limit: int | None = None
    offset: int | None = None


class ListProjectsQuery(QueryModel):
    """Validated filter + pagination for project listing."""

    availability: list[Availability] = Field(
        default_factory=lambda: [Availability.AVAILABLE, Availability.BLOCKED]
    )
    folder: str | None = None  # case-insensitive partial match on folder name
    review_due_within: str | None = None  # duration string e.g. "1w", "2m", "now"
    flagged: bool | None = None
    limit: int | None = None
    offset: int | None = None


class ListTagsQuery(QueryModel):
    """Validated filter for tag listing. No pagination."""

    availability: list[TagAvailability] = Field(
        default_factory=lambda: [TagAvailability.AVAILABLE, TagAvailability.BLOCKED]
    )


class ListFoldersQuery(QueryModel):
    """Validated filter for folder listing. No pagination."""

    availability: list[FolderAvailability] = Field(
        default_factory=lambda: [FolderAvailability.AVAILABLE]
    )


__all__ = [
    "ListFoldersQuery",
    "ListProjectsQuery",
    "ListResult",
    "ListTagsQuery",
    "ListTasksQuery",
]
