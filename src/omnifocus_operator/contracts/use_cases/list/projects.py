"""Project list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from pydantic import Field

from omnifocus_operator.contracts.base import QueryModel
from omnifocus_operator.models.enums import Availability


class ListProjectsQuery(QueryModel):
    """Agent-facing: validated filter + pagination for project listing."""

    availability: list[Availability] = Field(
        default_factory=lambda: [Availability.AVAILABLE, Availability.BLOCKED]
    )
    folder: str | None = None  # case-insensitive partial match on folder name
    review_due_within: str | None = None  # duration string e.g. "1w", "2m", "now"
    flagged: bool | None = None
    limit: int | None = None
    offset: int | None = None


class ListProjectsRepoQuery(QueryModel):
    """Repo-facing query -- identical fields today, diverges in Phase 35.2."""

    availability: list[Availability] = Field(
        default_factory=lambda: [Availability.AVAILABLE, Availability.BLOCKED]
    )
    folder: str | None = None
    review_due_within: str | None = None
    flagged: bool | None = None
    limit: int | None = None
    offset: int | None = None
