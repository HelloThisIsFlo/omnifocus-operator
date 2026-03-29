"""Typed protocols for every boundary in the system.

All three protocols -- Service, Repository, Bridge -- live in one file
so a single import shows the full typed contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from typing import Any

    from omnifocus_operator.contracts.use_cases.add_task import (
        AddTaskCommand,
        AddTaskRepoPayload,
        AddTaskRepoResult,
        AddTaskResult,
    )
    from omnifocus_operator.contracts.use_cases.edit_task import (
        EditTaskCommand,
        EditTaskRepoPayload,
        EditTaskRepoResult,
        EditTaskResult,
    )
    from omnifocus_operator.contracts.use_cases.list_entities import (
        ListFoldersQuery,
        ListProjectsQuery,
        ListResult,
        ListTagsQuery,
        ListTasksQuery,
    )
    from omnifocus_operator.models import AllEntities, Folder, Perspective, Project, Tag, Task


@runtime_checkable
class Service(Protocol):
    """Agent-facing boundary. Takes commands, returns results."""

    async def get_all_data(self) -> AllEntities: ...

    async def get_task(self, task_id: str) -> Task: ...

    async def get_project(self, project_id: str) -> Project: ...

    async def get_tag(self, tag_id: str) -> Tag: ...

    async def add_task(self, command: AddTaskCommand) -> AddTaskResult: ...

    async def edit_task(self, command: EditTaskCommand) -> EditTaskResult: ...

    async def list_tasks(self, query: ListTasksQuery) -> ListResult[Task]: ...

    async def list_projects(self, query: ListProjectsQuery) -> ListResult[Project]: ...

    async def list_tags(self, query: ListTagsQuery) -> ListResult[Tag]: ...

    async def list_folders(self, query: ListFoldersQuery) -> ListResult[Folder]: ...

    async def list_perspectives(self) -> ListResult[Perspective]: ...


@runtime_checkable
class Repository(Protocol):
    """Service-facing boundary. Takes payloads, returns repo results."""

    async def get_all(self) -> AllEntities: ...

    async def get_task(self, task_id: str) -> Task | None: ...

    async def get_project(self, project_id: str) -> Project | None: ...

    async def get_tag(self, tag_id: str) -> Tag | None: ...

    async def add_task(self, payload: AddTaskRepoPayload) -> AddTaskRepoResult: ...

    async def edit_task(self, payload: EditTaskRepoPayload) -> EditTaskRepoResult: ...

    async def list_tasks(self, query: ListTasksQuery) -> ListResult[Task]: ...

    async def list_projects(self, query: ListProjectsQuery) -> ListResult[Project]: ...

    async def list_tags(self, query: ListTagsQuery) -> ListResult[Tag]: ...

    async def list_folders(self, query: ListFoldersQuery) -> ListResult[Folder]: ...

    async def list_perspectives(self) -> ListResult[Perspective]: ...


@runtime_checkable
class Bridge(Protocol):
    """Repository-facing boundary. Raw dict in, raw dict out."""

    async def send_command(
        self,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


__all__ = ["Bridge", "Repository", "Service"]
