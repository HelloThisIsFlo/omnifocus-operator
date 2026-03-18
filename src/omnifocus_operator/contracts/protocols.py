"""Typed protocols for every boundary in the system.

All three protocols -- Service, Repository, Bridge -- live in one file
so a single import shows the full typed contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from typing import Any

    from omnifocus_operator.contracts.use_cases.create_task import (
        CreateTaskCommand,
        CreateTaskRepoPayload,
        CreateTaskRepoResult,
        CreateTaskResult,
    )
    from omnifocus_operator.contracts.use_cases.edit_task import (
        EditTaskCommand,
        EditTaskRepoPayload,
        EditTaskRepoResult,
        EditTaskResult,
    )
    from omnifocus_operator.models import AllEntities, Project, Tag, Task


class Service(Protocol):
    """Agent-facing boundary. Takes commands, returns results."""

    async def get_all_data(self) -> AllEntities: ...

    async def get_task(self, task_id: str) -> Task | None: ...

    async def get_project(self, project_id: str) -> Project | None: ...

    async def get_tag(self, tag_id: str) -> Tag | None: ...

    async def add_task(self, command: CreateTaskCommand) -> CreateTaskResult: ...

    async def edit_task(self, command: EditTaskCommand) -> EditTaskResult: ...


@runtime_checkable
class Repository(Protocol):
    """Service-facing boundary. Takes payloads, returns repo results."""

    async def get_all(self) -> AllEntities: ...

    async def get_task(self, task_id: str) -> Task | None: ...

    async def get_project(self, project_id: str) -> Project | None: ...

    async def get_tag(self, tag_id: str) -> Tag | None: ...

    async def add_task(self, payload: CreateTaskRepoPayload) -> CreateTaskRepoResult: ...

    async def edit_task(self, payload: EditTaskRepoPayload) -> EditTaskRepoResult: ...


class Bridge(Protocol):
    """Repository-facing boundary. Raw dict in, raw dict out."""

    async def send_command(
        self,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


__all__ = ["Bridge", "Repository", "Service"]
