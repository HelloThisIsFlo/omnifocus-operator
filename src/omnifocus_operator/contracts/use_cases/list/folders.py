"""Folder list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from omnifocus_operator.agent_messages import errors as err
from omnifocus_operator.agent_messages.descriptions import (
    LIMIT_DESC,
    LIST_FOLDERS_QUERY_DOC,
    OFFSET_DESC,
    SEARCH_FIELD_NAME_ONLY,
)
from omnifocus_operator.config import DEFAULT_LIST_LIMIT
from omnifocus_operator.contracts.base import UNSET, Patch, QueryModel
from omnifocus_operator.contracts.use_cases.list._enums import FolderAvailabilityFilter
from omnifocus_operator.contracts.use_cases.list._validators import (
    reject_null_filters,
    validate_offset_requires_limit,
)
from omnifocus_operator.models.enums import FolderAvailability

_PATCH_FIELDS = ["search"]


class ListFoldersQuery(QueryModel):
    __doc__ = LIST_FOLDERS_QUERY_DOC

    availability: list[FolderAvailabilityFilter] = Field(
        default=[FolderAvailabilityFilter.AVAILABLE]
    )
    search: Patch[str] = Field(default=UNSET, description=SEARCH_FIELD_NAME_ONLY)
    limit: int | None = Field(default=DEFAULT_LIST_LIMIT, description=LIMIT_DESC)
    offset: int = Field(default=0, description=OFFSET_DESC)

    @model_validator(mode="before")
    @classmethod
    def _reject_nulls(cls, data: dict[str, object]) -> dict[str, object]:
        if isinstance(data, dict):
            reject_null_filters(data, _PATCH_FIELDS)
        return data

    @field_validator("availability")
    @classmethod
    def _reject_empty_availability(
        cls, v: list[FolderAvailabilityFilter]
    ) -> list[FolderAvailabilityFilter]:
        if len(v) == 0:
            raise ValueError(err.AVAILABILITY_EMPTY.format(field="availability"))
        return v

    @model_validator(mode="after")
    def _check_offset_requires_limit(self) -> ListFoldersQuery:
        validate_offset_requires_limit(self.limit, self.offset)
        return self


class ListFoldersRepoQuery(QueryModel):
    """Repo-facing query -- identical fields today."""

    availability: list[FolderAvailability] = Field(default=[FolderAvailability.AVAILABLE])
    search: str | None = None
    limit: int | None = DEFAULT_LIST_LIMIT
    offset: int | None = None
