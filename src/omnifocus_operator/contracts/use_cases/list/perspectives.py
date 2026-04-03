"""Perspective list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from pydantic import Field

from omnifocus_operator.agent_messages.descriptions import (
    LIST_PERSPECTIVES_QUERY_DOC,
    SEARCH_FIELD_NAME_ONLY,
)
from omnifocus_operator.contracts.base import QueryModel


class ListPerspectivesQuery(QueryModel):
    __doc__ = LIST_PERSPECTIVES_QUERY_DOC

    search: str | None = Field(default=None, description=SEARCH_FIELD_NAME_ONLY)


class ListPerspectivesRepoQuery(QueryModel):
    """Repo-facing query -- identical fields today."""

    search: str | None = None
