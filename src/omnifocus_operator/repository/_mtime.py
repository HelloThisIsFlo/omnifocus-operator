"""MtimeSource protocol and production implementation (stub for TDD RED)."""

from __future__ import annotations

from typing import Protocol


class MtimeSource(Protocol):
    """Protocol for mtime sources."""

    async def get_mtime_ns(self) -> int: ...


class FileMtimeSource:
    """Production mtime source (stub)."""

    def __init__(self, path: str) -> None:
        raise NotImplementedError

    async def get_mtime_ns(self) -> int:
        raise NotImplementedError
