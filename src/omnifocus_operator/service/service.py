"""Thin orchestrator -- OperatorService and ErrorOperatorService.

OperatorService is the primary API surface for the MCP server. Each method
follows a short sequence: validate, resolve, domain logic, build payload,
delegate to repository. All heavy lifting lives in the extracted modules:

- ``resolve.py`` -- input resolution (parent, tags, validation)
- ``domain.py`` -- business rules (lifecycle, tags, cycle, no-op, move)
- ``payload.py`` -- typed repo payload construction
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, NoReturn

from omnifocus_operator.contracts.protocols import Service
from omnifocus_operator.service.domain import DomainLogic
from omnifocus_operator.service.payload import PayloadBuilder
from omnifocus_operator.service.resolve import (
    Resolver,
    validate_task_name,
    validate_task_name_if_set,
)

if TYPE_CHECKING:
    from omnifocus_operator.contracts.use_cases.create_task import (
        CreateTaskCommand,
        CreateTaskResult,
    )
    from omnifocus_operator.contracts.use_cases.edit_task import (
        EditTaskCommand,
        EditTaskResult,
    )
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.snapshot import AllEntities
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task
    from omnifocus_operator.repository import Repository

__all__ = ["ErrorOperatorService", "OperatorService"]

logger = logging.getLogger("omnifocus_operator")


class OperatorService(Service):  # explicitly implements Service protocol
    """Service layer that delegates to the Repository protocol.

    Parameters
    ----------
    repository:
        Any ``Repository`` implementation (e.g. ``BridgeRepository``,
        ``HybridRepository``) that provides ``get_all()``.
    """

    def __init__(self, repository: Repository) -> None:
        self._repository = repository
        self._resolver = Resolver(repository)
        self._domain = DomainLogic(repository, self._resolver)
        self._payload = PayloadBuilder()

    # -- Read delegation (one-liner pass-throughs) -------------------------

    async def get_all_data(self) -> AllEntities:
        """Return all OmniFocus entities from the repository."""
        logger.debug("OperatorService.get_all_data: delegating to repository")
        return await self._repository.get_all()

    async def get_task(self, task_id: str) -> Task | None:
        """Return a single task by ID, or None if not found."""
        logger.debug("OperatorService.get_task: id=%s", task_id)
        return await self._repository.get_task(task_id)

    async def get_project(self, project_id: str) -> Project | None:
        """Return a single project by ID, or None if not found."""
        logger.debug("OperatorService.get_project: id=%s", project_id)
        return await self._repository.get_project(project_id)

    async def get_tag(self, tag_id: str) -> Tag | None:
        """Return a single tag by ID, or None if not found."""
        logger.debug("OperatorService.get_tag: id=%s", tag_id)
        return await self._repository.get_tag(tag_id)

    # -- add_task: validate -> resolve -> build -> delegate ----------------

    async def add_task(self, command: CreateTaskCommand) -> CreateTaskResult:
        """Create a task with validation and delegation to repository.

        Raises
        ------
        ValueError
            If name is empty, parent not found, or tag resolution fails.
        """
        from omnifocus_operator.contracts.use_cases.create_task import CreateTaskResult

        logger.debug(
            "OperatorService.add_task: name=%s, parent=%s, tags=%s",
            command.name,
            command.parent,
            command.tags,
        )

        validate_task_name(command.name)

        if command.parent is not None:
            await self._resolver.resolve_parent(command.parent)

        resolved_tag_ids: list[str] | None = None
        if command.tags is not None:
            resolved_tag_ids = await self._resolver.resolve_tags(command.tags)
            logger.debug(
                "OperatorService.add_task: resolved %d tags to IDs: %s",
                len(resolved_tag_ids),
                resolved_tag_ids,
            )

        repo_payload = self._payload.build_add(command, resolved_tag_ids)

        logger.debug("OperatorService.add_task: delegating to repository")
        repo_result = await self._repository.add_task(repo_payload)
        return CreateTaskResult(success=True, id=repo_result.id, name=repo_result.name)

    # -- edit_task: fetch -> domain -> build -> no-op check -> delegate ----

    async def edit_task(self, command: EditTaskCommand) -> EditTaskResult:
        """Edit a task with validation and delegation to repository.

        Raises
        ------
        ValueError
            If task not found, name empty, parent not found, anchor not
            found, or move would create a cycle.
        """
        from omnifocus_operator.contracts.base import _Unset
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskResult

        # 1. Verify task exists
        logger.debug("OperatorService.edit_task: id=%s, fetching current state", command.id)
        task = await self._repository.get_task(command.id)
        if task is None:
            msg = f"Task not found: {command.id}"
            raise ValueError(msg)
        logger.debug(
            "OperatorService.edit_task: task found, name=%s, current_tags=%d",
            task.name,
            len(task.tags),
        )

        validate_task_name_if_set(command.name)

        # 2. _Unset checks -- orchestrator decides what to call
        has_actions = not isinstance(command.actions, _Unset)
        has_lifecycle = (
            has_actions
            and not isinstance(command.actions, _Unset)
            and not isinstance(command.actions.lifecycle, _Unset)
        )
        has_tag_actions = (
            has_actions
            and not isinstance(command.actions, _Unset)
            and not isinstance(command.actions.tags, _Unset)
        )
        has_move = (
            has_actions
            and not isinstance(command.actions, _Unset)
            and not isinstance(command.actions.move, _Unset)
        )

        # 3. Domain: lifecycle
        lifecycle: str | None = None
        lifecycle_warns: list[str] = []
        if has_lifecycle:
            lifecycle_action: str = command.actions.lifecycle  # type: ignore[union-attr,assignment]
            should_call, lifecycle_warns = self._domain.process_lifecycle(lifecycle_action, task)
            if should_call:
                lifecycle = lifecycle_action

        # 4. Domain: status warnings
        status_warns = self._domain.check_completed_status(task, has_lifecycle)

        # 5. Domain: tag diff
        tag_adds: list[str] | None = None
        tag_removes: list[str] | None = None
        tag_warns: list[str] = []
        if has_tag_actions:
            tag_adds, tag_removes, tag_warns = await self._domain.compute_tag_diff(
                command.actions.tags,  # type: ignore[union-attr,arg-type]
                task.tags,
            )
            logger.debug("OperatorService.edit_task: current_tags=%s", [t.id for t in task.tags])
            logger.debug(
                "OperatorService.edit_task: tag diff add_ids=%s, remove_ids=%s",
                tag_adds,
                tag_removes,
            )

        # 6. Domain: move processing
        move_to: dict[str, object] | None = None
        if has_move:
            move_to = await self._domain.process_move(
                command.actions.move,  # type: ignore[union-attr,arg-type]
                command.id,
            )

        # 7. Build payload
        repo_payload = self._payload.build_edit(command, lifecycle, tag_adds, tag_removes, move_to)
        logger.debug(
            "OperatorService.edit_task: payload fields_set=%s",
            repo_payload.model_fields_set,
        )

        # 8. Domain: no-op + empty-edit detection
        all_warnings = lifecycle_warns + status_warns + tag_warns
        early = self._domain.detect_early_return(repo_payload, task, all_warnings)
        if early is not None:
            return early

        # 9. Delegate
        logger.debug("OperatorService.edit_task: delegating to repository")
        repo_result = await self._repository.edit_task(repo_payload)
        return EditTaskResult(
            success=True,
            id=repo_result.id,
            name=repo_result.name,
            warnings=all_warnings or None,
        )


class ErrorOperatorService(OperatorService):
    """Stand-in service that raises on every attribute access.

    Used when the server fails to start (e.g. missing OmniFocus database).
    Instead of crashing, the MCP server stays alive in degraded mode and
    serves the startup error through tool responses.
    """

    def __init__(self, error: Exception) -> None:
        # Bypass OperatorService.__init__ -- we have no repository.
        # Use object.__setattr__ to avoid triggering __getattr__.
        object.__setattr__(
            self,
            "_error_message",
            f"OmniFocus Operator failed to start:\n\n{error!s}\n\nRestart the server after fixing.",
        )

    def __getattr__(self, name: str) -> NoReturn:
        """Intercept every attribute access and raise with the startup error."""
        logger.warning("Tool call in error mode (attribute: %s)", name)
        raise RuntimeError(self._error_message)
