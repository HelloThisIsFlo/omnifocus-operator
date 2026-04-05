"""Tag list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from pydantic import Field, model_validator

from omnifocus_operator.agent_messages.descriptions import (
    LIMIT_DESC,
    LIST_TAGS_QUERY_DOC,
    OFFSET_DESC,
    SEARCH_FIELD_NAME_ONLY,
)
from omnifocus_operator.config import DEFAULT_LIST_LIMIT
from omnifocus_operator.contracts.base import QueryModel
from omnifocus_operator.contracts.use_cases.list._validators import validate_offset_requires_limit
from omnifocus_operator.models.enums import TagAvailability


class ListTagsQuery(QueryModel):
    __doc__ = LIST_TAGS_QUERY_DOC

    availability: list[TagAvailability] = Field(
        default=[TagAvailability.AVAILABLE, TagAvailability.BLOCKED]
    )
    search: str | None = Field(default=None, description=SEARCH_FIELD_NAME_ONLY)
    limit: int | None = Field(default=DEFAULT_LIST_LIMIT, description=LIMIT_DESC)
    offset: int | None = Field(default=None, description=OFFSET_DESC)

    @model_validator(mode="after")
    def _check_offset_requires_limit(self) -> ListTagsQuery:
        validate_offset_requires_limit(self.limit, self.offset)
        return self


class ListTagsRepoQuery(QueryModel):
    """Repo-facing query -- identical fields today."""

    availability: list[TagAvailability] = Field(
        default=[TagAvailability.AVAILABLE, TagAvailability.BLOCKED]
    )
    search: str | None = None
    limit: int | None = DEFAULT_LIST_LIMIT
    offset: int | None = None
