"""Folder list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from pydantic import Field, model_validator

from omnifocus_operator.agent_messages.descriptions import (
    LIST_FOLDERS_QUERY_DOC,
    SEARCH_FIELD_NAME_ONLY,
)
from omnifocus_operator.config import DEFAULT_LIST_LIMIT
from omnifocus_operator.contracts.base import QueryModel
from omnifocus_operator.contracts.use_cases.list._validators import validate_offset_requires_limit
from omnifocus_operator.models.enums import FolderAvailability


class ListFoldersQuery(QueryModel):
    __doc__ = LIST_FOLDERS_QUERY_DOC

    availability: list[FolderAvailability] = Field(
        default=[FolderAvailability.AVAILABLE]
    )
    search: str | None = Field(default=None, description=SEARCH_FIELD_NAME_ONLY)
    limit: int | None = DEFAULT_LIST_LIMIT
    offset: int | None = None

    @model_validator(mode="after")
    def _check_offset_requires_limit(self) -> ListFoldersQuery:
        validate_offset_requires_limit(self.limit, self.offset)
        return self


class ListFoldersRepoQuery(QueryModel):
    """Repo-facing query -- identical fields today."""

    availability: list[FolderAvailability] = Field(
        default=[FolderAvailability.AVAILABLE]
    )
    search: str | None = None
    limit: int | None = DEFAULT_LIST_LIMIT
    offset: int | None = None
