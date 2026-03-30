"""Task list contracts: agent-facing query and repo-facing query."""

from __future__ import annotations

from pydantic import Field

from omnifocus_operator.contracts.base import QueryModel
from omnifocus_operator.models.enums import Availability


class ListTasksQuery(QueryModel):
    """Agent-facing: validated filter + pagination for task listing."""

    in_inbox: bool | None = None
    flagged: bool | None = None
    project: str | None = None  # case-insensitive partial match on project name
    tags: list[str] | None = None  # tag names (OR logic), service resolves to IDs
    estimated_minutes_max: int | None = None
    availability: list[Availability] = Field(
        default_factory=lambda: [Availability.AVAILABLE, Availability.BLOCKED]
    )
    search: str | None = None  # case-insensitive substring in name+notes
    limit: int | None = None
    offset: int | None = None


class ListTasksRepoQuery(QueryModel):
    """Repo-facing query -- identical fields today, diverges in Phase 35.2 (per D-01d)."""

    in_inbox: bool | None = None
    flagged: bool | None = None
    project: str | None = None
    tags: list[str] | None = None  # names today, Phase 35.2 adds tag_ids
    estimated_minutes_max: int | None = None
    availability: list[Availability] = Field(
        default_factory=lambda: [Availability.AVAILABLE, Availability.BLOCKED]
    )
    search: str | None = None
    limit: int | None = None
    offset: int | None = None
