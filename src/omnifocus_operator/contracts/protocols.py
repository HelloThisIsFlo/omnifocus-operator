"""Typed protocols for every boundary in the system.

All three protocols -- Service, Repository, Bridge -- live in one file
so a single import shows the full typed contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from typing import Any

    from omnifocus_operator.contracts.use_cases.add.tasks import (
        AddTaskCommand,
        AddTaskRepoPayload,
        AddTaskRepoResult,
        AddTaskResult,
    )
    from omnifocus_operator.contracts.use_cases.edit.tasks import (
        EditTaskCommand,
        EditTaskRepoPayload,
        EditTaskRepoResult,
        EditTaskResult,
    )
    from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult, ListResult
    from omnifocus_operator.contracts.use_cases.list.folders import (
        ListFoldersQuery,
        ListFoldersRepoQuery,
    )
    from omnifocus_operator.contracts.use_cases.list.perspectives import (
        ListPerspectivesQuery,
        ListPerspectivesRepoQuery,
    )
    from omnifocus_operator.contracts.use_cases.list.projects import (
        ListProjectsQuery,
        ListProjectsRepoQuery,
    )
    from omnifocus_operator.contracts.use_cases.list.tags import (
        ListTagsQuery,
        ListTagsRepoQuery,
    )
    from omnifocus_operator.contracts.use_cases.list.tasks import (
        ListTasksQuery,
        ListTasksRepoQuery,
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

    async def list_perspectives(self, query: ListPerspectivesQuery) -> ListResult[Perspective]: ...


@runtime_checkable
class Repository(Protocol):
    """Service-facing boundary. Takes payloads, returns repo results."""

    async def get_all(self) -> AllEntities: ...

    async def get_task(self, task_id: str) -> Task | None: ...

    async def get_project(self, project_id: str) -> Project | None: ...

    async def get_tag(self, tag_id: str) -> Tag | None: ...

    async def add_task(self, payload: AddTaskRepoPayload) -> AddTaskRepoResult: ...

    async def edit_task(self, payload: EditTaskRepoPayload) -> EditTaskRepoResult: ...

    async def list_tasks(self, query: ListTasksRepoQuery) -> ListRepoResult[Task]: ...

    async def list_projects(self, query: ListProjectsRepoQuery) -> ListRepoResult[Project]: ...

    async def list_tags(self, query: ListTagsRepoQuery) -> ListRepoResult[Tag]: ...

    async def list_folders(self, query: ListFoldersRepoQuery) -> ListRepoResult[Folder]: ...

    async def list_perspectives(
        self, query: ListPerspectivesRepoQuery
    ) -> ListRepoResult[Perspective]: ...

    async def get_edge_child_id(
        self, parent_id: str, edge: Literal["first", "last"]
    ) -> str | None: ...


@runtime_checkable
class Bridge(Protocol):
    """Repository-facing boundary. Raw dict in, raw dict out."""

    async def send_command(
        self,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


__all__ = ["Bridge", "Repository", "Service"]
