"""List-result containers for agent and repository boundaries."""

from __future__ import annotations

from omnifocus_operator.models.base import OmniFocusBaseModel


class ListResult[T](OmniFocusBaseModel):
    """Agent-facing result container for all list operations.

    Uniform shape for all 5 list tools. Non-paginated: total=len(items), has_more=False.
    """

    items: list[T]
    total: int
    has_more: bool


class ListRepoResult[T](OmniFocusBaseModel):
    """Repo-facing result container -- identical to ListResult today.

    No warnings field (added to ListResult in Phase 37 per D-02).
    """

    items: list[T]
    total: int
    has_more: bool
