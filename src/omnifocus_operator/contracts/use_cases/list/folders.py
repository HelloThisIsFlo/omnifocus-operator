"""Folder list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from pydantic import Field

from omnifocus_operator.agent_messages.descriptions import LIST_FOLDERS_QUERY_DOC
from omnifocus_operator.contracts.base import QueryModel
from omnifocus_operator.models.enums import FolderAvailability


class ListFoldersQuery(QueryModel):
    __doc__ = LIST_FOLDERS_QUERY_DOC

    availability: list[FolderAvailability] = Field(
        default_factory=lambda: [FolderAvailability.AVAILABLE]
    )


class ListFoldersRepoQuery(QueryModel):
    """Repo-facing query -- identical fields today."""

    availability: list[FolderAvailability] = Field(
        default_factory=lambda: [FolderAvailability.AVAILABLE]
    )
