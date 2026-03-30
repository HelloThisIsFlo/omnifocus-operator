"""List-result containers for agent and repository boundaries."""

from __future__ import annotations

from omnifocus_operator.models.base import OmniFocusBaseModel


class ListResult[T](OmniFocusBaseModel):
    """Agent-facing result container for all list operations.

    Uniform shape for all 5 list tools. Non-paginated: total=len(items), has_more=False.
    Includes optional warnings for agent guidance (e.g. name resolution ambiguity).
    """

    items: list[T]
    total: int
    has_more: bool
    warnings: list[str] | None = None


class ListRepoResult[T](OmniFocusBaseModel):
    """Repo-facing result container -- no warnings field.

    Warnings are a service/agent concern, not a repository concern (D-02d).
    """

    items: list[T]
    total: int
    has_more: bool
