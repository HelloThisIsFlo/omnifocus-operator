"""Tag list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from pydantic import Field

from omnifocus_operator.agent_messages.descriptions import LIST_TAGS_QUERY_DOC
from omnifocus_operator.contracts.base import QueryModel
from omnifocus_operator.models.enums import TagAvailability


class ListTagsQuery(QueryModel):
    __doc__ = LIST_TAGS_QUERY_DOC

    availability: list[TagAvailability] = Field(
        default_factory=lambda: [TagAvailability.AVAILABLE, TagAvailability.BLOCKED]
    )


class ListTagsRepoQuery(QueryModel):
    """Repo-facing query -- identical fields today."""

    availability: list[TagAvailability] = Field(
        default_factory=lambda: [TagAvailability.AVAILABLE, TagAvailability.BLOCKED]
    )
