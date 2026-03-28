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

from omnifocus_operator.contracts.base import is_set
from omnifocus_operator.contracts.protocols import Service
from omnifocus_operator.contracts.use_cases.add_task import AddTaskResult
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskResult
from omnifocus_operator.service.domain import DomainLogic
from omnifocus_operator.service.payload import PayloadBuilder
from omnifocus_operator.service.resolve import Resolver
from omnifocus_operator.service.validate import (
    validate_repetition_rule_add,
    validate_task_name,
    validate_task_name_if_set,
)

if TYPE_CHECKING:
    from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand
    from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.snapshot import AllEntities
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task
    from omnifocus_operator.repository import Repository

__all__ = ["ErrorOperatorService", "OperatorService"]

logger = logging.getLogger(__name__)


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

    async def get_task(self, task_id: str) -> Task:
        """Return a single task by ID. Raises ValueError if not found."""
        logger.debug("OperatorService.get_task: id=%s", task_id)
        return await self._resolver.resolve_task(task_id)

    async def get_project(self, project_id: str) -> Project:
        """Return a single project by ID. Raises ValueError if not found."""
        logger.debug("OperatorService.get_project: id=%s", project_id)
        return await self._resolver.resolve_project(project_id)

    async def get_tag(self, tag_id: str) -> Tag:
        """Return a single tag by ID. Raises ValueError if not found."""
        logger.debug("OperatorService.get_tag: id=%s", tag_id)
        return await self._resolver.resolve_tag(tag_id)

    # -- add_task: delegates to _AddTaskPipeline (Method Object) --------

    async def add_task(self, command: AddTaskCommand) -> AddTaskResult:
        """Create a task with validation and delegation to repository.

        Raises
        ------
        ValueError
            If name is empty, parent not found, or tag resolution fails.
        """
        pipeline = _AddTaskPipeline(
            self._resolver,
            self._domain,
            self._payload,
            self._repository,
        )
        return await pipeline.execute(command)

    # -- edit_task: delegates to _EditTaskPipeline (Method Object) ---------

    async def edit_task(self, command: EditTaskCommand) -> EditTaskResult:
        """Edit a task with validation and delegation to repository.

        Raises
        ------
        ValueError
            If task not found, name empty, parent not found, anchor not
            found, or move would create a cycle.
        """
        pipeline = _EditTaskPipeline(
            self._resolver,
            self._domain,
            self._payload,
            self._repository,
        )
        return await pipeline.execute(command)


# -- Pipeline base ---------------------------------------------------------


class _Pipeline:
    """Shared dependencies for all task pipelines."""

    def __init__(
        self,
        resolver: Resolver,
        domain: DomainLogic,
        payload: PayloadBuilder,
        repository: Repository,
    ) -> None:
        self._resolver = resolver
        self._domain = domain
        self._payload = payload
        self._repository = repository


# -- add_task pipeline (Method Object) -------------------------------------


class _AddTaskPipeline(_Pipeline):
    """Method object for add_task — validate, resolve, build, delegate."""

    async def execute(self, command: AddTaskCommand) -> AddTaskResult:
        """Run the full create-task pipeline."""
        self._command = command
        self._repetition_warnings: list[str] = []

        self._validate()
        await self._resolve_parent()
        await self._resolve_tags()
        self._validate_repetition_rule()
        self._build_payload()
        return await self._delegate()

    def _validate(self) -> None:
        logger.debug(
            "OperatorService.add_task: name=%s, parent=%s, tags=%s",
            self._command.name,
            self._command.parent,
            self._command.tags,
        )
        validate_task_name(self._command.name)

    async def _resolve_parent(self) -> None:
        if self._command.parent is None:
            return
        await self._resolver.resolve_parent(self._command.parent)

    async def _resolve_tags(self) -> None:
        self._resolved_tag_ids: list[str] | None = None
        if self._command.tags is None:
            return
        self._resolved_tag_ids = await self._resolver.resolve_tags(self._command.tags)
        logger.debug(
            "OperatorService.add_task: resolved %d tags to IDs: %s",
            len(self._resolved_tag_ids),
            self._resolved_tag_ids,
        )

    def _validate_repetition_rule(self) -> None:
        """Validate and normalize repetition rule if present."""
        if self._command.repetition_rule is None:
            return

        spec = self._command.repetition_rule

        # Structural + constraint validation
        spec = validate_repetition_rule_add(spec)

        # Normalize empty on_dates (D-13)
        normalized_freq, on_dates_warns = self._domain.normalize_empty_on_dates(spec.frequency)
        self._repetition_warnings.extend(on_dates_warns)
        if normalized_freq is not spec.frequency:
            spec = spec.model_copy(update={"frequency": normalized_freq})

        # Update the command with the normalized spec
        self._command = self._command.model_copy(update={"repetition_rule": spec})

    def _build_payload(self) -> None:
        self._repo_payload = self._payload.build_add(self._command, self._resolved_tag_ids)

    async def _delegate(self) -> AddTaskResult:
        logger.debug("OperatorService.add_task: delegating to repository")
        repo_result = await self._repository.add_task(self._repo_payload)
        warnings = self._repetition_warnings or None
        return AddTaskResult(
            success=True, id=repo_result.id, name=repo_result.name, warnings=warnings
        )


# -- edit_task pipeline (Method Object) ------------------------------------


class _EditTaskPipeline(_Pipeline):
    """Method object for edit_task — each step is a named method, state on self."""

    async def execute(self, command: EditTaskCommand) -> EditTaskResult:
        """Run the full edit-task pipeline."""
        self._command = command

        await self._verify_task_exists()
        self._validate_and_normalize()
        self._resolve_actions()
        self._apply_lifecycle()
        self._check_completed_status()
        await self._apply_tag_diff()
        await self._apply_move()
        self._build_payload()

        if (early := self._detect_noop()) is not None:
            return early
        return await self._delegate()

    async def _verify_task_exists(self) -> None:
        logger.debug("OperatorService.edit_task: id=%s, fetching current state", self._command.id)
        self._task = await self._resolver.resolve_task(self._command.id)
        logger.debug(
            "OperatorService.edit_task: task found, name=%s, current_tags=%d",
            self._task.name,
            len(self._task.tags),
        )

    def _validate_and_normalize(self) -> None:
        validate_task_name_if_set(self._command.name)
        self._command = self._domain.normalize_clear_intents(self._command)

    def _resolve_actions(self) -> None:
        actions = self._command.actions
        if not is_set(actions):
            self._lifecycle_action = None
            self._tag_actions = None
            self._move_action = None
            return
        self._lifecycle_action = actions.lifecycle if is_set(actions.lifecycle) else None
        self._tag_actions = actions.tags if is_set(actions.tags) else None
        self._move_action = actions.move if is_set(actions.move) else None

    def _apply_lifecycle(self) -> None:
        self._lifecycle: str | None = None
        self._lifecycle_warns: list[str] = []
        if self._lifecycle_action is None:
            return
        should_call, self._lifecycle_warns = self._domain.process_lifecycle(
            self._lifecycle_action,
            self._task,
        )
        if should_call:
            self._lifecycle = self._lifecycle_action

    def _check_completed_status(self) -> None:
        self._status_warns = self._domain.check_completed_status(
            self._task,
            self._lifecycle_action is not None,
        )

    async def _apply_tag_diff(self) -> None:
        self._tag_adds: list[str] | None = None
        self._tag_removes: list[str] | None = None
        self._tag_warns: list[str] = []
        if self._tag_actions is None:
            return
        self._tag_adds, self._tag_removes, self._tag_warns = await self._domain.compute_tag_diff(
            self._tag_actions, self._task.tags
        )
        logger.debug("OperatorService.edit_task: current_tags=%s", [t.id for t in self._task.tags])
        logger.debug(
            "OperatorService.edit_task: tag diff add_ids=%s, remove_ids=%s",
            self._tag_adds,
            self._tag_removes,
        )

    async def _apply_move(self) -> None:
        self._move_to: dict[str, object] | None = None
        if self._move_action is None:
            return
        self._move_to = await self._domain.process_move(
            self._move_action,
            self._command.id,
        )

    def _build_payload(self) -> None:
        self._repo_payload = self._payload.build_edit(
            self._command,
            self._lifecycle,
            self._tag_adds,
            self._tag_removes,
            self._move_to,
        )
        logger.debug(
            "OperatorService.edit_task: payload fields_set=%s",
            self._repo_payload.model_fields_set,
        )
        self._all_warnings = self._lifecycle_warns + self._status_warns + self._tag_warns

    def _detect_noop(self) -> EditTaskResult | None:
        return self._domain.detect_early_return(
            self._repo_payload,
            self._task,
            self._all_warnings,
        )

    async def _delegate(self) -> EditTaskResult:
        logger.debug("OperatorService.edit_task: delegating to repository")
        repo_result = await self._repository.edit_task(self._repo_payload)
        return EditTaskResult(
            success=True,
            id=repo_result.id,
            name=repo_result.name,
            warnings=self._all_warnings or None,
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
