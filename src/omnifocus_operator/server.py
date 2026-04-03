"""Server module -- FastMCP server for OmniFocus Operator.

The server uses a lifespan context manager to wire the three-layer
architecture: ``FastMCP tool -> OperatorService -> Repository``.
The repository implementation is selected via ``create_repository()``,
which reads ``OPERATOR_REPOSITORY`` (default ``"hybrid"``).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastmcp import Context, FastMCP
from mcp.types import (
    ToolAnnotations,  # TODO(Phase 30): no fastmcp equivalent; revisit if fastmcp adds re-export
)

# NOTE: AllEntities MUST be a runtime import (not TYPE_CHECKING) because
# FastMCP introspects the return type annotation at registration time to
# generate outputSchema.  With `from __future__ import annotations` the
# annotation is a string; FastMCP resolves it via get_type_hints() which
# needs the name in the module namespace.
from omnifocus_operator.agent_messages.descriptions import (
    ADD_TASKS_TOOL_DOC,
    EDIT_TASKS_TOOL_DOC,
    GET_ALL_TOOL_DOC,
    GET_PROJECT_TOOL_DOC,
    GET_TAG_TOOL_DOC,
    GET_TASK_TOOL_DOC,
    LIST_FOLDERS_TOOL_DOC,
    LIST_PERSPECTIVES_TOOL_DOC,
    LIST_PROJECTS_TOOL_DOC,
    LIST_TAGS_TOOL_DOC,
    LIST_TASKS_TOOL_DOC,
)
from omnifocus_operator.agent_messages.errors import (
    ADD_TASKS_BATCH_LIMIT,
    EDIT_TASKS_BATCH_LIMIT,
)
from omnifocus_operator.contracts.use_cases.add.tasks import (  # noqa: TC001 — FastMCP resolves param annotations at runtime
    AddTaskCommand,
    AddTaskResult,
)
from omnifocus_operator.contracts.use_cases.edit.tasks import (  # noqa: TC001
    EditTaskCommand,
    EditTaskResult,
)
from omnifocus_operator.contracts.use_cases.list.common import ListResult  # noqa: TC001 — FastMCP needs runtime
from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersQuery  # noqa: TC001
from omnifocus_operator.contracts.use_cases.list.perspectives import ListPerspectivesQuery  # noqa: TC001
from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsQuery  # noqa: TC001
from omnifocus_operator.contracts.use_cases.list.tags import ListTagsQuery  # noqa: TC001
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksQuery  # noqa: TC001
from omnifocus_operator.middleware import (
    ToolLoggingMiddleware,
    ValidationReformatterMiddleware,
)
from omnifocus_operator.models import (  # noqa: TC001 — FastMCP needs runtime names
    AllEntities,
    Folder,
    Perspective,
    Project,
    Tag,
    Task,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

__all__ = ["create_server"]

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict[str, object]]:
    """Create the service stack and yield it for tool handlers.

    1. IPC sweep runs first (always, regardless of repository mode).
    2. ``create_repository()`` selects the repository based on
       ``OPERATOR_REPOSITORY`` env var (default ``"hybrid"``).
    3. Startup errors are caught and served through ``ErrorOperatorService``.
    """
    # IPC sweep always runs -- cleans orphaned files from dead processes.
    # This is safe even when using sqlite mode (sweep handles missing dirs).
    from omnifocus_operator.bridge.real import DEFAULT_IPC_DIR, sweep_orphaned_files

    logger.info("Sweeping orphaned IPC files...")
    await sweep_orphaned_files(DEFAULT_IPC_DIR)
    logger.info("IPC sweep complete")

    try:
        from omnifocus_operator.repository import create_repository
        from omnifocus_operator.service import OperatorService

        repo_type = os.environ.get("OPERATOR_REPOSITORY")
        logger.info("Repository type: %s", repo_type or "hybrid (default)")

        repository = create_repository(repo_type)
        service = OperatorService(repository=repository)

        yield {"service": service}

        logger.info("Server shutting down")
    except Exception as exc:
        logger.exception("Fatal error during startup")
        from omnifocus_operator.service import ErrorOperatorService

        error_service = ErrorOperatorService(exc)
        yield {"service": error_service}
        logger.info("Error-mode server shutting down")


def _register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools on the given server instance.

    Separated from ``create_server`` so tests can register tools on a
    custom server with a patched lifespan.
    """

    @mcp.tool(
        description=GET_ALL_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_all(ctx: Context) -> AllEntities:
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_all_data()
        logger.debug(
            "server.get_all: returning tasks=%d, projects=%d, tags=%d",
            len(result.tasks),
            len(result.projects),
            len(result.tags),
        )
        return result

    @mcp.tool(
        description=GET_TASK_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_task(id: str, ctx: Context) -> Task:
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_task(id)
        logger.debug("server.get_task: returning name=%s", result.name)
        return result

    @mcp.tool(
        description=GET_PROJECT_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_project(id: str, ctx: Context) -> Project:
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_project(id)
        logger.debug("server.get_project: returning name=%s", result.name)
        return result

    @mcp.tool(
        description=GET_TAG_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_tag(id: str, ctx: Context) -> Tag:
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_tag(id)
        logger.debug("server.get_tag: returning name=%s", result.name)
        return result

    @mcp.tool(
        description=ADD_TASKS_TOOL_DOC,
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False
        ),
    )
    async def add_tasks(
        items: list[AddTaskCommand],
        ctx: Context,
    ) -> list[AddTaskResult]:
        if len(items) != 1:
            msg = ADD_TASKS_BATCH_LIMIT.format(count=len(items))
            raise ValueError(msg)

        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        command = items[0]
        # Progress reporting (scaffolding for future batch support per D-05):
        total = len(items)
        results: list[AddTaskResult] = []
        for i, validated in enumerate([command]):
            await ctx.report_progress(progress=i, total=total)
            result = await service.add_task(validated)
            results.append(result)
        await ctx.report_progress(progress=total, total=total)
        logger.debug("server.add_tasks: returning id=%s, name=%s", results[0].id, results[0].name)
        return results

    @mcp.tool(
        description=EDIT_TASKS_TOOL_DOC,
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False
        ),
    )
    async def edit_tasks(
        items: list[EditTaskCommand],
        ctx: Context,
    ) -> list[EditTaskResult]:
        if len(items) != 1:
            msg = EDIT_TASKS_BATCH_LIMIT.format(count=len(items))
            raise ValueError(msg)

        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        command = items[0]
        # Progress reporting (scaffolding for future batch support per D-05):
        total = len(items)
        results: list[EditTaskResult] = []
        for i, validated in enumerate([command]):
            await ctx.report_progress(progress=i, total=total)
            result = await service.edit_task(validated)
            results.append(result)
        await ctx.report_progress(progress=total, total=total)
        logger.debug(
            "server.edit_tasks: returning id=%s, success=%s, warnings=%s",
            results[0].id,
            results[0].success,
            results[0].warnings,
        )
        return results

    @mcp.tool(
        description=LIST_TASKS_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_tasks(query: ListTasksQuery, ctx: Context) -> ListResult[Task]:
        from omnifocus_operator.service import OperatorService

        service: OperatorService = ctx.lifespan_context["service"]
        return await service.list_tasks(query)

    @mcp.tool(
        description=LIST_PROJECTS_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_projects(query: ListProjectsQuery, ctx: Context) -> ListResult[Project]:
        from omnifocus_operator.service import OperatorService

        service: OperatorService = ctx.lifespan_context["service"]
        return await service.list_projects(query)

    @mcp.tool(
        description=LIST_TAGS_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_tags(query: ListTagsQuery, ctx: Context) -> ListResult[Tag]:
        from omnifocus_operator.service import OperatorService

        service: OperatorService = ctx.lifespan_context["service"]
        return await service.list_tags(query)

    @mcp.tool(
        description=LIST_FOLDERS_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_folders(query: ListFoldersQuery, ctx: Context) -> ListResult[Folder]:
        from omnifocus_operator.service import OperatorService

        service: OperatorService = ctx.lifespan_context["service"]
        return await service.list_folders(query)

    @mcp.tool(
        description=LIST_PERSPECTIVES_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_perspectives(query: ListPerspectivesQuery, ctx: Context) -> ListResult[Perspective]:
        from omnifocus_operator.service import OperatorService

        service: OperatorService = ctx.lifespan_context["service"]
        return await service.list_perspectives(query)


def create_server() -> FastMCP:
    """Create and return a configured FastMCP server instance.

    The server is not started -- call ``server.run(transport="stdio")``
    or use the in-process testing pattern with ``server._mcp_server.run()``.
    """
    mcp = FastMCP("omnifocus-operator", lifespan=app_lifespan)
    _register_tools(mcp)
    mcp.add_middleware(ValidationReformatterMiddleware())  # innermost (added first)
    mcp.add_middleware(ToolLoggingMiddleware(logger))  # outermost (added second)
    return mcp
