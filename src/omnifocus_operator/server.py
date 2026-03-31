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
from omnifocus_operator.middleware import ToolLoggingMiddleware, ValidationReformatterMiddleware
from omnifocus_operator.models import (  # noqa: TC001 — FastMCP needs runtime names
    AllEntities,
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
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_all(ctx: Context) -> AllEntities:
        """Return the full OmniFocus database as structured data.

        Returns all tasks, projects, tags, folders, and perspectives as a
        single snapshot.  The response uses camelCase field names.
        """
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
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_task(id: str, ctx: Context) -> Task:
        """Look up a single task by its ID. Returns the full Task object."""
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_task(id)
        logger.debug("server.get_task: returning name=%s", result.name)
        return result

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_project(id: str, ctx: Context) -> Project:
        """Look up a single project by its ID. Returns the full Project object."""
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_project(id)
        logger.debug("server.get_project: returning name=%s", result.name)
        return result

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_tag(id: str, ctx: Context) -> Tag:
        """Look up a single tag by its ID. Returns the full Tag object."""
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_tag(id)
        logger.debug("server.get_tag: returning name=%s", result.name)
        return result

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False
        ),
    )
    async def add_tasks(
        items: list[AddTaskCommand],
        ctx: Context,
    ) -> list[AddTaskResult]:
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
        - repetitionRule: Repetition rule (all three root fields required on creation)
          - frequency (required): Object with "type" + optional specialization fields
            - {type: "minutely", interval: N}
            - {type: "hourly", interval: N}
            - {type: "daily", interval: N}
            - {type: "weekly", interval: N}  -- optionally add onDays
            - {type: "weekly", interval: N, onDays: ["MO","WE","FR"]}  -- specific days (MO-SU)
            - {type: "monthly", interval: N}  -- optionally add on or onDates
            - {type: "monthly", interval: N, on: {"second": "tuesday"}}
                ordinals: first/second/third/fourth/fifth/last
                days: monday-sunday, weekday, weekend_day
            - {type: "monthly", interval: N, onDates: [1, 15]}
                valid dates: 1 to 31, use -1 for last day of month
            - {type: "yearly", interval: N}
            - interval defaults to 1, omit or set explicitly
            - on and onDates are mutually exclusive
          - schedule (required): "regularly" / "regularly_with_catch_up" / "from_completion"
          - basedOn (required): "due_date" / "defer_date" / "planned_date"
          - end: {"date": "ISO-8601"} or {"occurrences": N} -- omit for no end

          Examples:
            Every 3 days from completion:
              {frequency: {type: "daily", interval: 3}, schedule: "from_completion", basedOn: "defer_date"}

            Every 2 weeks on Mon and Fri, stop after 10:
              {frequency: {type: "weekly", interval: 2, onDays: ["MO", "FR"]}, schedule: "regularly", basedOn: "due_date", end: {occurrences: 10}}

            Last Friday of every month:
              {frequency: {type: "monthly", on: {"last": "friday"}}, schedule: "regularly", basedOn: "due_date"}

        Returns array of results: [{success, id, name, warnings?}]
        """  # noqa: E501
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
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False
        ),
    )
    async def edit_tasks(
        items: list[EditTaskCommand],
        ctx: Context,
    ) -> list[EditTaskResult]:
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
        - repetitionRule: Set, update, or clear a repetition rule
          - Full rule: same shape as add_tasks (frequency, schedule, basedOn required)
          - Partial update: send only changed fields, omitted root fields preserved
            - frequency.type optional (inferred from existing task)
            - frequency.type required when changing to a different type
            - Same type: omitted frequency fields preserved from existing rule
            - Different type: full replacement, defaults apply like creation
            - onDays/on/onDates: null to clear, omit to preserve
            - on and onDates are mutually exclusive -- setting one auto-clears the other
          - end: null to clear, omit to preserve
          - null to clear the repetition rule

          Examples:
            Change just the interval (type inferred from existing):
              {frequency: {interval: 5}}

            Add specific days to a weekly task (no type change):
              {frequency: {onDays: ["MO", "WE", "FR"]}}

            Remove day constraint from weekly:
              {frequency: {onDays: null}}

            Switch monthly from dates to weekday pattern (onDates auto-cleared):
              {frequency: {on: {"last": "friday"}}}

            Change from daily to weekly (type required):
              {frequency: {type: "weekly", onDays: ["MO", "FR"]}}

            Clear:
              null

        Actions block (omit to skip, groups stateful operations):
        - actions.tags: Tag operations
          - {"replace": ["tag1"]} -- replace all tags (null or [] to clear)
          - {"add": ["tag1"], "remove": ["tag2"]} -- incremental (combinable)
          - {"add": ["tag1"]} or {"remove": ["tag1"]} -- add-only or remove-only
        - actions.move: Task movement (exactly one key)
          - {"ending": "<parentId>"} / {"beginning": "<parentId>"}
          - {"before": "<taskId>"} / {"after": "<taskId>"}
          - {"ending": null} / {"beginning": null} -- move to inbox
        - actions.lifecycle: Task lifecycle action
          - "complete" -- mark task as complete
          - "drop" -- drop/skip task

        Returns array of results: [{success, id, name, warnings?}]
        """
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
