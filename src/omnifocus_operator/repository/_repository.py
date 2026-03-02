"""OmniFocusRepository (stub for TDD RED)."""

from __future__ import annotations

from omnifocus_operator.models._snapshot import DatabaseSnapshot


class OmniFocusRepository:
    """Caching repository (stub)."""

    def __init__(self, bridge: object, mtime_source: object) -> None:
        raise NotImplementedError

    async def get_snapshot(self) -> DatabaseSnapshot:
        raise NotImplementedError

    async def initialize(self) -> None:
        raise NotImplementedError
