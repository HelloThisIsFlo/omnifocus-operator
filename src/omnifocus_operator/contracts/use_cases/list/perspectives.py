"""Perspective list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from pydantic import Field, model_validator

from omnifocus_operator.agent_messages.descriptions import (
    LIMIT_DESC,
    LIST_PERSPECTIVES_QUERY_DOC,
    OFFSET_DESC,
    SEARCH_FIELD_NAME_ONLY,
)
from omnifocus_operator.config import DEFAULT_LIST_LIMIT
from omnifocus_operator.contracts.base import QueryModel
from omnifocus_operator.contracts.use_cases.list._validators import validate_offset_requires_limit


class ListPerspectivesQuery(QueryModel):
    __doc__ = LIST_PERSPECTIVES_QUERY_DOC

    search: str | None = Field(default=None, description=SEARCH_FIELD_NAME_ONLY)
    limit: int | None = Field(default=DEFAULT_LIST_LIMIT, description=LIMIT_DESC)
    offset: int | None = Field(default=None, description=OFFSET_DESC)

    @model_validator(mode="after")
    def _check_offset_requires_limit(self) -> ListPerspectivesQuery:
        validate_offset_requires_limit(self.limit, self.offset)
        return self


class ListPerspectivesRepoQuery(QueryModel):
    """Repo-facing query -- identical fields today."""

    search: str | None = None
    limit: int | None = DEFAULT_LIST_LIMIT
    offset: int | None = None
