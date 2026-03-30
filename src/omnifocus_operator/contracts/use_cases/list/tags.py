"""Tag list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from pydantic import Field

from omnifocus_operator.contracts.base import QueryModel
from omnifocus_operator.models.enums import TagAvailability


class ListTagsQuery(QueryModel):
    """Agent-facing: validated filter for tag listing. No pagination."""

    availability: list[TagAvailability] = Field(
        default_factory=lambda: [TagAvailability.AVAILABLE, TagAvailability.BLOCKED]
    )


class ListTagsRepoQuery(QueryModel):
    """Repo-facing query -- identical fields today."""

    availability: list[TagAvailability] = Field(
        default_factory=lambda: [TagAvailability.AVAILABLE, TagAvailability.BLOCKED]
    )
