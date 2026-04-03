"""Task list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from pydantic import Field, model_validator

from omnifocus_operator.agent_messages.descriptions import (
    LIST_TASKS_QUERY_DOC,
    SEARCH_FIELD_NAME_NOTES,
)
from omnifocus_operator.contracts.base import QueryModel
from omnifocus_operator.contracts.use_cases.list._validators import validate_offset_requires_limit
from omnifocus_operator.models.enums import Availability


class ListTasksQuery(QueryModel):
    __doc__ = LIST_TASKS_QUERY_DOC

    in_inbox: bool | None = None
    flagged: bool | None = None
    project: str | None = None  # case-insensitive partial match on project name
    tags: list[str] | None = None  # tag names (OR logic), service resolves to IDs
    estimated_minutes_max: int | None = None
    availability: list[Availability] = Field(
        default_factory=lambda: [Availability.AVAILABLE, Availability.BLOCKED]
    )
    search: str | None = Field(default=None, description=SEARCH_FIELD_NAME_NOTES)
    limit: int | None = None
    offset: int | None = None

    @model_validator(mode="after")
    def _check_offset_requires_limit(self) -> ListTasksQuery:
        validate_offset_requires_limit(self.limit, self.offset)
        return self


class ListTasksRepoQuery(QueryModel):
    """Repo-facing query -- IDs only, service resolves names before passing."""

    in_inbox: bool | None = None
    flagged: bool | None = None
    project_ids: list[str] | None = None
    tag_ids: list[str] | None = None
    estimated_minutes_max: int | None = None
    availability: list[Availability] = Field(
        default_factory=lambda: [Availability.AVAILABLE, Availability.BLOCKED]
    )
    search: str | None = None
    limit: int | None = None
    offset: int | None = None
