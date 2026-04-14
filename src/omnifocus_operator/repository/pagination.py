"""Shared pagination utility for repository implementations."""

from __future__ import annotations

from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult


def paginate[T](items: list[T], limit: int | None, offset: int) -> ListRepoResult[T]:
    """Apply offset/limit slicing and compute total/has_more for Python-filtered lists."""
    total = len(items)
    if offset:
        items = items[offset:]
    if limit is not None:
        has_more = len(items) > limit
        items = items[:limit]
    else:
        has_more = False
    return ListRepoResult(items=items, total=total, has_more=has_more)
