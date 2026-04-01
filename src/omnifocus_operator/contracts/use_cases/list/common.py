"""List-result containers for agent and repository boundaries."""

from __future__ import annotations

from omnifocus_operator.agent_messages.descriptions import LIST_RESULT_DOC
from omnifocus_operator.models.base import OmniFocusBaseModel


class ListResult[T](OmniFocusBaseModel):
    __doc__ = LIST_RESULT_DOC

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
