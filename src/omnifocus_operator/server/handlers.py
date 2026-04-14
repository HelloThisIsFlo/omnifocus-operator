"""Tool handler registration for the FastMCP server.

All 11 MCP tool definitions live here.  ``_register_tools`` is called by
``create_server()`` in ``__init__.py`` to attach them to a FastMCP instance.
"""

from __future__ import annotations

import logging

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
from omnifocus_operator.contracts.use_cases.list.common import (
    ListResult,  # noqa: TC001 — FastMCP needs runtime
)
from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersQuery  # noqa: TC001
from omnifocus_operator.contracts.use_cases.list.perspectives import (
    ListPerspectivesQuery,  # noqa: TC001
)
from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsQuery  # noqa: TC001
from omnifocus_operator.contracts.use_cases.list.tags import ListTagsQuery  # noqa: TC001
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksQuery  # noqa: TC001
from omnifocus_operator.models import (  # noqa: TC001 — FastMCP needs runtime names
    AllEntities,
    Folder,
    Perspective,
    Project,
    Tag,
    Task,
)

logger = logging.getLogger(__name__)


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
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        return await service.list_tasks(query)

    @mcp.tool(
        description=LIST_PROJECTS_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_projects(query: ListProjectsQuery, ctx: Context) -> ListResult[Project]:
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        return await service.list_projects(query)

    @mcp.tool(
        description=LIST_TAGS_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_tags(query: ListTagsQuery, ctx: Context) -> ListResult[Tag]:
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        return await service.list_tags(query)

    @mcp.tool(
        description=LIST_FOLDERS_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_folders(query: ListFoldersQuery, ctx: Context) -> ListResult[Folder]:
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        return await service.list_folders(query)

    @mcp.tool(
        description=LIST_PERSPECTIVES_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_perspectives(
        query: ListPerspectivesQuery, ctx: Context
    ) -> ListResult[Perspective]:
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        return await service.list_perspectives(query)
