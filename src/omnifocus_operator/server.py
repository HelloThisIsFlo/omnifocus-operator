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

        Response contains: tasks, projects, tags, folders, perspectives arrays.
        The response uses camelCase field names.
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
        """Look up a single task by its ID.

        Key fields: urgency, availability, dueDate, deferDate, plannedDate,
        effectiveDueDate (inherited from parent), flagged, effectiveFlagged,
        tags (array of {id, name}), parent ({type, id, name} or null for inbox),
        repetitionRule, inInbox.
        The response uses camelCase field names.
        """
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_task(id)
        logger.debug("server.get_task: returning name=%s", result.name)
        return result

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_project(id: str, ctx: Context) -> Project:
        """Look up a single project by its ID.

        Key fields: urgency, availability, dueDate, deferDate, plannedDate,
        effectiveDueDate (inherited from parent), flagged, effectiveFlagged,
        tags (array of {id, name}), nextTask (ID of first available task),
        folder (name or null), reviewInterval, nextReviewDate.
        The response uses camelCase field names.
        """
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.lifespan_context["service"]
        result = await service.get_project(id)
        logger.debug("server.get_project: returning name=%s", result.name)
        return result

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_tag(id: str, ctx: Context) -> Tag:
        """Look up a single tag by its ID.

        Key fields: availability, childrenAreMutuallyExclusive (child tags
        behave like radio buttons when true), parent (parent tag name or null).
        The response uses camelCase field names.
        """
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
        """Create tasks in OmniFocus. Limited to 1 item per call.

        Tags accept names (case-insensitive) or IDs; you can mix both.
        Non-existent names are rejected. Ambiguous names (case-insensitive
        collision) return an error.

        All date fields require timezone info (ISO 8601 with offset or Z).
        Naive datetimes are rejected.

        repetitionRule requires all three root fields (frequency, schedule,
        basedOn) when creating. on and onDates within frequency are
        mutually exclusive.

        Examples (repetitionRule):
          Every 3 days from completion:
            {frequency: {type: "daily", interval: 3}, schedule: "from_completion", basedOn: "defer_date"}

          Every 2 weeks on Mon and Fri, stop after 10:
            {frequency: {type: "weekly", interval: 2, onDays: ["MO", "FR"]}, schedule: "regularly", basedOn: "due_date", end: {occurrences: 10}}

          Last Friday of every month:
            {frequency: {type: "monthly", on: {"last": "friday"}}, schedule: "regularly", basedOn: "due_date"}

        Returns: [{success, id, name, warnings?}]
        """
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
        """Edit existing tasks in OmniFocus using patch semantics. Limited to 1 item per call.

        Patch contract: omit a field to leave it unchanged, set to null to
        clear it, set to a value to update.

        Tags (in all tag fields) accept names (case-insensitive) or IDs;
        you can mix both. Non-existent names are rejected. Ambiguous names
        (case-insensitive collision) return an error.

        All date fields require timezone info (ISO 8601 with offset or Z).
        Naive datetimes are rejected.

        repetitionRule partial updates:
          - Task has no existing rule: all three root fields required
            (frequency, schedule, basedOn) -- same as creation.
          - Task has existing rule: omitted root fields are preserved.
          - frequency.type can be omitted (inferred from existing rule)
            unless changing to a different type.
          - Same type: omitted frequency sub-fields preserved.
          - Different type: full replacement with creation defaults.
          - on and onDates are mutually exclusive -- setting one clears
            the other.
          - null clears the entire repetition rule.

        Examples (repetitionRule):
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

        actions.move: exactly one key must be set. ending/beginning with
        null moves to inbox.

        actions.lifecycle:
          - "complete": marks the task as complete.
          - "drop": skips/cancels the task without completing it.
          On repeating tasks, both actions apply to the current occurrence
          only -- the next occurrence is automatically created. Dropping an
          entire repeating sequence is not supported via this API.

        actions.tags: replace is standalone. add/remove are combinable with
        each other but not with replace.

        Returns: [{success, id, name, warnings?}]
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
