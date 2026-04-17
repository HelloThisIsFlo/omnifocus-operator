"""Tool handler registration for the FastMCP server.

All 11 MCP tool definitions live here.  ``_register_tools`` is called by
``create_server()`` in ``__init__.py`` to attach them to a FastMCP instance.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import (
    ToolAnnotations,  # TODO(Phase 30): no fastmcp equivalent; revisit if fastmcp adds re-export
)
from pydantic import Field

if TYPE_CHECKING:
    from omnifocus_operator.service import OperatorService

# NOTE: Imports below MUST stay at runtime (not TYPE_CHECKING) because
# FastMCP introspects return/param type annotations at registration time
# via get_type_hints() which needs names in the module namespace.
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
from omnifocus_operator.config import (
    MAX_BATCH_SIZE,
    PROGRESS_NOTIFICATIONS_ENABLED,
    PROJECT_DEFAULT_FIELDS,
    PROJECT_FIELD_GROUPS,
    TASK_DEFAULT_FIELDS,
    TASK_FIELD_GROUPS,
)
from omnifocus_operator.contracts.use_cases.add.tasks import (
    AddTaskCommand,
    AddTaskResult,
)
from omnifocus_operator.contracts.use_cases.edit.tasks import (
    EditTaskCommand,
    EditTaskResult,
)
from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersQuery  # noqa: TC001
from omnifocus_operator.contracts.use_cases.list.perspectives import (
    ListPerspectivesQuery,  # noqa: TC001
)
from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsQuery  # noqa: TC001
from omnifocus_operator.contracts.use_cases.list.tags import ListTagsQuery  # noqa: TC001
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksQuery  # noqa: TC001
from omnifocus_operator.server.projection import (
    shape_list_response,
    shape_list_response_strip_only,
    strip_all_entities,
    strip_batch_results,
    strip_entity,
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
    async def get_all(ctx: Context) -> dict[str, Any]:
        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_all_data()
        logger.debug(
            "server.get_all: returning tasks=%d, projects=%d, tags=%d",
            len(result.tasks),
            len(result.projects),
            len(result.tags),
        )
        return strip_all_entities(result.model_dump(by_alias=True))

    @mcp.tool(
        description=GET_TASK_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_task(id: str, ctx: Context) -> dict[str, Any]:
        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_task(id)
        logger.debug("server.get_task: returning name=%s", result.name)
        return strip_entity(result.model_dump(by_alias=True))

    @mcp.tool(
        description=GET_PROJECT_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_project(id: str, ctx: Context) -> dict[str, Any]:
        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_project(id)
        logger.debug("server.get_project: returning name=%s", result.name)
        return strip_entity(result.model_dump(by_alias=True))

    @mcp.tool(
        description=GET_TAG_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_tag(id: str, ctx: Context) -> dict[str, Any]:
        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_tag(id)
        logger.debug("server.get_tag: returning name=%s", result.name)
        return strip_entity(result.model_dump(by_alias=True))

    @mcp.tool(
        description=ADD_TASKS_TOOL_DOC,
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False
        ),
    )
    async def add_tasks(
        items: Annotated[list[AddTaskCommand], Field(min_length=1, max_length=MAX_BATCH_SIZE)],
        ctx: Context,
    ) -> list[dict[str, Any]]:
        service: OperatorService = ctx.lifespan_context["service"]
        total = len(items)
        results: list[AddTaskResult] = []
        for i, command in enumerate(items):
            if PROGRESS_NOTIFICATIONS_ENABLED:
                await ctx.report_progress(progress=i, total=total)
            try:
                result = await service.add_task(command)
                results.append(result)
            except (ToolError, ValueError) as e:
                results.append(
                    AddTaskResult(
                        status="error",
                        error=f"Task {i + 1}: {e}",
                    )
                )
        if PROGRESS_NOTIFICATIONS_ENABLED:
            await ctx.report_progress(progress=total, total=total)
        return strip_batch_results(results)

    @mcp.tool(
        description=EDIT_TASKS_TOOL_DOC,
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False
        ),
    )
    async def edit_tasks(
        items: Annotated[list[EditTaskCommand], Field(min_length=1, max_length=MAX_BATCH_SIZE)],
        ctx: Context,
    ) -> list[dict[str, Any]]:
        service: OperatorService = ctx.lifespan_context["service"]
        total = len(items)
        results: list[EditTaskResult] = []
        failed_idx: int | None = None
        for i, command in enumerate(items):
            if PROGRESS_NOTIFICATIONS_ENABLED:
                await ctx.report_progress(progress=i, total=total)
            if failed_idx is not None:
                results.append(
                    EditTaskResult(
                        status="skipped",
                        id=command.id,
                        warnings=[f"Skipped: task {failed_idx + 1} failed"],
                    )
                )
                continue
            try:
                result = await service.edit_task(command)
                results.append(result)
            except (ToolError, ValueError) as e:
                failed_idx = i
                results.append(
                    EditTaskResult(
                        status="error",
                        id=command.id,
                        error=f"Task {i + 1}: {e}",
                    )
                )
        if PROGRESS_NOTIFICATIONS_ENABLED:
            await ctx.report_progress(progress=total, total=total)
        return strip_batch_results(results)

    @mcp.tool(
        description=LIST_TASKS_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_tasks(query: ListTasksQuery, ctx: Context) -> dict[str, Any]:
        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.list_tasks(query)
        return shape_list_response(
            result,
            include=query.include,
            only=query.only,
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )

    @mcp.tool(
        description=LIST_PROJECTS_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_projects(query: ListProjectsQuery, ctx: Context) -> dict[str, Any]:
        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.list_projects(query)
        return shape_list_response(
            result,
            include=query.include,
            only=query.only,
            default_fields=PROJECT_DEFAULT_FIELDS,
            field_groups=PROJECT_FIELD_GROUPS,
        )

    @mcp.tool(
        description=LIST_TAGS_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_tags(query: ListTagsQuery, ctx: Context) -> dict[str, Any]:
        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.list_tags(query)
        return shape_list_response_strip_only(result)

    @mcp.tool(
        description=LIST_FOLDERS_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_folders(query: ListFoldersQuery, ctx: Context) -> dict[str, Any]:
        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.list_folders(query)
        return shape_list_response_strip_only(result)

    @mcp.tool(
        description=LIST_PERSPECTIVES_TOOL_DOC,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_perspectives(query: ListPerspectivesQuery, ctx: Context) -> dict[str, Any]:
        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.list_perspectives(query)
        return shape_list_response_strip_only(result)
