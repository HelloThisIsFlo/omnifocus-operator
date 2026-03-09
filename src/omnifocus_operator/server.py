"""Server module -- FastMCP server for OmniFocus Operator.

The server uses a lifespan context manager to wire the three-layer
architecture: ``FastMCP tool -> OperatorService -> Repository``.
The repository implementation is selected via ``create_repository()``,
which reads ``OMNIFOCUS_REPOSITORY`` (default ``"hybrid"``).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import ValidationError

# NOTE: AllEntities MUST be a runtime import (not TYPE_CHECKING) because
# FastMCP introspects the return type annotation at registration time to
# generate outputSchema.  With `from __future__ import annotations` the
# annotation is a string; FastMCP resolves it via get_type_hints() which
# needs the name in the module namespace.
from omnifocus_operator.models import (
    AllEntities,
    Project,
    Tag,
    Task,
    TaskCreateResult,
    TaskCreateSpec,
    TaskEditResult,
    TaskEditSpec,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

__all__ = ["create_server"]

logger = logging.getLogger("omnifocus_operator")


@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict[str, object]]:
    """Create the service stack and yield it for tool handlers.

    1. IPC sweep runs first (always, regardless of repository mode).
    2. ``create_repository()`` selects the repository based on
       ``OMNIFOCUS_REPOSITORY`` env var (default ``"hybrid"``).
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

        repo_type = os.environ.get("OMNIFOCUS_REPOSITORY")
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
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_all(ctx: Context[Any, Any, Any]) -> AllEntities:
        """Return the full OmniFocus database as structured data.

        Returns all tasks, projects, tags, folders, and perspectives as a
        single snapshot.  The response uses camelCase field names.
        """
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.request_context.lifespan_context["service"]
        return await service.get_all_data()

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_task(id: str, ctx: Context[Any, Any, Any]) -> Task:
        """Look up a single task by its ID. Returns the full Task object."""
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.request_context.lifespan_context["service"]
        result = await service.get_task(id)
        if result is None:
            msg = f"Task not found: {id}"
            raise ValueError(msg)
        return result

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_project(id: str, ctx: Context[Any, Any, Any]) -> Project:
        """Look up a single project by its ID. Returns the full Project object."""
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.request_context.lifespan_context["service"]
        result = await service.get_project(id)
        if result is None:
            msg = f"Project not found: {id}"
            raise ValueError(msg)
        return result

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_tag(id: str, ctx: Context[Any, Any, Any]) -> Tag:
        """Look up a single tag by its ID. Returns the full Tag object."""
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.request_context.lifespan_context["service"]
        result = await service.get_tag(id)
        if result is None:
            msg = f"Tag not found: {id}"
            raise ValueError(msg)
        return result

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False
        ),
    )
    async def add_tasks(
        items: list[dict[str, Any]],
        ctx: Context[Any, Any, Any],
    ) -> list[TaskCreateResult]:
        """Create tasks in OmniFocus.

        Accepts an array of task objects. Currently limited to 1 item per call.

        Each item accepts:
        - name (required): Task name
        - parent: Project or task ID to place task under (omit for inbox)
        - tags: List of tag names (case-insensitive) or tag IDs
        - dueDate: Due date (ISO 8601)
        - deferDate: Defer/start date (ISO 8601)
        - plannedDate: Planned date (ISO 8601)
        - flagged: Boolean flag
        - estimatedMinutes: Estimated duration in minutes
        - note: Task note text

        These are the only supported fields. Repetition rules, notifications,
        and sequential/parallel settings are not yet available.

        Returns array of results: [{success, id, name}]
        """
        if len(items) != 1:
            msg = f"add_tasks currently accepts exactly 1 item, got {len(items)}"
            raise ValueError(msg)

        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.request_context.lifespan_context["service"]
        try:
            spec = TaskCreateSpec.model_validate(items[0])
        except ValidationError as exc:
            messages = "; ".join(e["msg"] for e in exc.errors() if "_Unset" not in e["msg"])
            raise ValueError(messages or "Invalid input") from None
        result = await service.add_task(spec)
        return [result]

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False
        ),
    )
    async def edit_tasks(
        items: list[dict[str, Any]],
        ctx: Context[Any, Any, Any],
    ) -> list[TaskEditResult]:
        """Edit existing tasks in OmniFocus using patch semantics.

        Accepts an array of edit objects. Currently limited to 1 item per call.

        Each item requires:
        - id (required): Task ID to edit

        Optional fields (omit to leave unchanged, set null to clear):
        - name: New task name (cannot be empty)
        - note: Task note text (null to clear)
        - dueDate: Due date ISO 8601 (null to clear)
        - deferDate: Defer/start date ISO 8601 (null to clear)
        - plannedDate: Planned date ISO 8601 (null to clear)
        - flagged: Boolean flag
        - estimatedMinutes: Estimated duration (null to clear)

        Tag editing (mutually exclusive modes):
        - tags: Replace all tags with this list ([] to clear all)
        - addTags: Add these tags without removing existing
        - removeTags: Remove specific tags (addTags + removeTags together is allowed)

        Task movement (omit moveTo entirely to skip):
        - moveTo: Position object with exactly one key:
          - {"ending": "<parentId>"} -- move to end of project/task
          - {"beginning": "<parentId>"} -- move to start of project/task
          - {"before": "<taskId>"} -- move before sibling task
          - {"after": "<taskId>"} -- move after sibling task
          - {"ending": null} / {"beginning": null} -- move to inbox

        Returns array of results: [{success, id, name, warnings?}]
        """
        if len(items) != 1:
            msg = f"edit_tasks currently accepts exactly 1 item, got {len(items)}"
            raise ValueError(msg)

        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.request_context.lifespan_context["service"]
        try:
            spec = TaskEditSpec.model_validate(items[0])
        except ValidationError as exc:
            messages = "; ".join(e["msg"] for e in exc.errors() if "_Unset" not in e["msg"])
            raise ValueError(messages or "Invalid input") from None
        result = await service.edit_task(spec)
        return [result]


def create_server() -> FastMCP:
    """Create and return a configured FastMCP server instance.

    The server is not started -- call ``server.run(transport="stdio")``
    or use the in-process testing pattern with ``server._mcp_server.run()``.
    """
    mcp = FastMCP("omnifocus-operator", lifespan=app_lifespan)
    _register_tools(mcp)
    return mcp
