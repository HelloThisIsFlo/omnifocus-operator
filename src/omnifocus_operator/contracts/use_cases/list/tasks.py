"""Task list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from pydantic import Field, model_validator

from omnifocus_operator.agent_messages.descriptions import (
    ESTIMATED_MINUTES_MAX_DESC,
    FLAGGED_FILTER_DESC,
    IN_INBOX_FILTER_DESC,
    LIMIT_DESC,
    LIST_TASKS_QUERY_DOC,
    OFFSET_DESC,
    PROJECT_FILTER_DESC,
    SEARCH_FIELD_NAME_NOTES,
    TAGS_FILTER_DESC,
)
from omnifocus_operator.config import DEFAULT_LIST_LIMIT
from omnifocus_operator.contracts.base import QueryModel
from omnifocus_operator.contracts.use_cases.list._validators import validate_offset_requires_limit
from omnifocus_operator.models.enums import Availability


class ListTasksQuery(QueryModel):
    __doc__ = LIST_TASKS_QUERY_DOC

    in_inbox: bool | None = Field(default=None, description=IN_INBOX_FILTER_DESC)
    flagged: bool | None = Field(default=None, description=FLAGGED_FILTER_DESC)
    project: str | None = Field(default=None, description=PROJECT_FILTER_DESC)
    tags: list[str] | None = Field(default=None, description=TAGS_FILTER_DESC)
    estimated_minutes_max: int | None = Field(default=None, description=ESTIMATED_MINUTES_MAX_DESC)
    availability: list[Availability] = Field(default=[Availability.AVAILABLE, Availability.BLOCKED])
    search: str | None = Field(default=None, description=SEARCH_FIELD_NAME_NOTES)
    limit: int | None = Field(default=DEFAULT_LIST_LIMIT, description=LIMIT_DESC)
    offset: int | None = Field(default=None, description=OFFSET_DESC)

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
    availability: list[Availability] = Field(default=[Availability.AVAILABLE, Availability.BLOCKED])
    search: str | None = None
    limit: int | None = DEFAULT_LIST_LIMIT
    offset: int | None = None
