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
from typing import TYPE_CHECKING, Any, NoReturn

from omnifocus_operator.agent_messages.errors import (
    REPETITION_NO_EXISTING_RULE,
)
from omnifocus_operator.agent_messages.warnings import (
    FILTER_DID_YOU_MEAN,
    FILTER_NO_MATCH,
    REPETITION_NO_OP,
)
from omnifocus_operator.contracts.base import is_set
from omnifocus_operator.contracts.protocols import Service
from omnifocus_operator.contracts.shared.repetition_rule import FrequencyAddSpec
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskResult
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskResult
from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult, ListResult
from omnifocus_operator.contracts.use_cases.list.folders import (
    ListFoldersRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.projects import (
    ListProjectsRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.tags import (
    ListTagsRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.tasks import (
    ListTasksRepoQuery,
)
from omnifocus_operator.models.repetition_rule import Frequency
from omnifocus_operator.service.domain import DomainLogic
from omnifocus_operator.service.payload import PayloadBuilder
from omnifocus_operator.service.resolve import Resolver
from omnifocus_operator.service.validate import (
    validate_task_name,
    validate_task_name_if_set,
)

if TYPE_CHECKING:
    from omnifocus_operator.contracts.shared.repetition_rule import (
        FrequencyEditSpec,
        RepetitionRuleRepoPayload,
    )
    from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskCommand
    from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskCommand
    from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersQuery
    from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsQuery
    from omnifocus_operator.contracts.use_cases.list.tags import ListTagsQuery
    from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksQuery
    from omnifocus_operator.models.enums import BasedOn, Schedule
    from omnifocus_operator.models.folder import Folder
    from omnifocus_operator.models.perspective import Perspective
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.repetition_rule import EndCondition
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

    # -- list_tasks: delegates to _ListTasksPipeline (Method Object) --------

    async def list_tasks(self, query: ListTasksQuery) -> ListResult[Task]:
        """List tasks with name-to-ID resolution for project and tag filters."""
        pipeline = _ListTasksPipeline(
            self._resolver,
            self._domain,
            self._repository,
        )
        return await pipeline.execute(query)

    # -- list_projects: delegates to _ListProjectsPipeline (Method Object) --

    async def list_projects(self, query: ListProjectsQuery) -> ListResult[Project]:
        """List projects with name-to-ID resolution for folder filter."""
        pipeline = _ListProjectsPipeline(
            self._resolver,
            self._domain,
            self._repository,
        )
        return await pipeline.execute(query)

    # -- list pass-throughs (no entity-reference filters to resolve) ---------

    async def list_tags(self, query: ListTagsQuery) -> ListResult[Tag]:
        """List tags -- inline pass-through (no entity-reference filters)."""
        repo_query = ListTagsRepoQuery(availability=query.availability)
        repo_result = await self._repository.list_tags(repo_query)
        return ListResult(
            items=repo_result.items, total=repo_result.total, has_more=repo_result.has_more
        )

    async def list_folders(self, query: ListFoldersQuery) -> ListResult[Folder]:
        """List folders -- inline pass-through (no entity-reference filters)."""
        repo_query = ListFoldersRepoQuery(availability=query.availability)
        repo_result = await self._repository.list_folders(repo_query)
        return ListResult(
            items=repo_result.items, total=repo_result.total, has_more=repo_result.has_more
        )

    async def list_perspectives(self) -> ListResult[Perspective]:
        """List perspectives -- inline pass-through (no filters)."""
        repo_result = await self._repository.list_perspectives()
        return ListResult(
            items=repo_result.items, total=repo_result.total, has_more=repo_result.has_more
        )


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


# -- Read pipeline base ----------------------------------------------------


class _ReadPipeline:
    """Shared dependencies for read-side list pipelines."""

    def __init__(
        self,
        resolver: Resolver,
        domain: DomainLogic,
        repository: Repository,
    ) -> None:
        self._resolver = resolver
        self._domain = domain
        self._repository = repository
        self._warnings: list[str] = []

    def _build_warning(self, entity_type: str, value: str, entity_names: list[str]) -> str:
        """Build a did-you-mean or no-match warning for a failed resolution."""
        suggestions = self._domain.suggest_close_matches(value, entity_names)
        if suggestions:
            return FILTER_DID_YOU_MEAN.format(
                entity_type=entity_type,
                value=value,
                suggestions=", ".join(suggestions),
            )
        return FILTER_NO_MATCH.format(entity_type=entity_type, value=value)

    def _result_from_repo[T](self, repo_result: ListRepoResult[T]) -> ListResult[T]:
        """Convert ListRepoResult to ListResult with accumulated warnings."""
        return ListResult(
            items=repo_result.items,
            total=repo_result.total,
            has_more=repo_result.has_more,
            warnings=self._warnings or None,
        )


# -- list_tasks pipeline (Method Object) ------------------------------------


class _ListTasksPipeline(_ReadPipeline):
    """Method object for list_tasks -- resolve project + tags to IDs, then delegate."""

    async def execute(self, query: ListTasksQuery) -> ListResult[Task]:
        """Run the full list-tasks pipeline."""
        self._query = query
        self._all_data = await self._repository.get_all()

        self._resolve_project()
        self._resolve_tags()
        self._build_repo_query()
        return await self._delegate()

    def _resolve_project(self) -> None:
        self._project_ids: list[str] | None = None
        if self._query.project is None:
            return
        resolved = self._resolver.resolve_filter(self._query.project, self._all_data.projects)
        if resolved:
            self._project_ids = resolved
        else:
            # No match -- skip filter, warn
            self._warnings.append(
                self._build_warning(
                    "project",
                    self._query.project,
                    [p.name for p in self._all_data.projects],
                )
            )

    def _resolve_tags(self) -> None:
        self._tag_ids: list[str] | None = None
        if self._query.tags is None:
            return
        resolved = self._resolver.resolve_filter_list(self._query.tags, self._all_data.tags)
        unresolved = self._resolver.find_unresolved(self._query.tags, self._all_data.tags)
        if resolved:
            self._tag_ids = resolved
        for value in unresolved:
            self._warnings.append(
                self._build_warning(
                    "tag",
                    value,
                    [t.name for t in self._all_data.tags],
                )
            )

    def _build_repo_query(self) -> None:
        self._repo_query = ListTasksRepoQuery(
            in_inbox=self._query.in_inbox,
            flagged=self._query.flagged,
            project_ids=self._project_ids,
            tag_ids=self._tag_ids,
            estimated_minutes_max=self._query.estimated_minutes_max,
            availability=self._query.availability,
            search=self._query.search,
            limit=self._query.limit,
            offset=self._query.offset,
        )

    async def _delegate(self) -> ListResult[Task]:
        repo_result = await self._repository.list_tasks(self._repo_query)
        return self._result_from_repo(repo_result)


# -- list_projects pipeline (Method Object) ---------------------------------


class _ListProjectsPipeline(_ReadPipeline):
    """Method object for list_projects -- resolve folder to IDs, then delegate."""

    async def execute(self, query: ListProjectsQuery) -> ListResult[Project]:
        """Run the full list-projects pipeline."""
        self._query = query
        self._all_data = await self._repository.get_all()

        self._resolve_folder()
        self._build_repo_query()
        return await self._delegate()

    def _resolve_folder(self) -> None:
        self._folder_ids: list[str] | None = None
        if self._query.folder is None:
            return
        resolved = self._resolver.resolve_filter(self._query.folder, self._all_data.folders)
        if resolved:
            self._folder_ids = resolved
        else:
            # No match -- skip filter, warn
            self._warnings.append(
                self._build_warning(
                    "folder",
                    self._query.folder,
                    [f.name for f in self._all_data.folders],
                )
            )

    def _build_repo_query(self) -> None:
        self._repo_query = ListProjectsRepoQuery(
            availability=self._query.availability,
            folder_ids=self._folder_ids,
            review_due_within=self._query.review_due_within,
            flagged=self._query.flagged,
            limit=self._query.limit,
            offset=self._query.offset,
        )

    async def _delegate(self) -> ListResult[Project]:
        repo_result = await self._repository.list_projects(self._repo_query)
        return self._result_from_repo(repo_result)


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
        self._process_repetition_rule()
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

    def _process_repetition_rule(self) -> None:
        """Normalize repetition rule if present.

        FrequencyAddSpec has model validators that already validated
        the spec on construction. We only need to normalize empty
        specialization fields here.
        """
        if self._command.repetition_rule is None:
            return

        spec = self._command.repetition_rule

        # Convert FrequencyAddSpec to Frequency for normalization
        freq = Frequency.model_validate(spec.frequency.model_dump())

        # Normalize empty specialization fields (D-17)
        normalized_freq, spec_warns = self._domain.normalize_empty_specialization_fields(freq)
        self._repetition_warnings.extend(spec_warns)
        if normalized_freq is not freq:
            # Rebuild the spec with normalized frequency
            new_freq_spec = FrequencyAddSpec.model_validate(normalized_freq.model_dump())
            spec = spec.model_copy(update={"frequency": new_freq_spec})

        # Update the command with the normalized spec
        self._command = self._command.model_copy(update={"repetition_rule": spec})

        # Check anchor date warning (VALID-05)
        effective_dates = {
            "due_date": self._command.due_date,
            "defer_date": self._command.defer_date,
            "planned_date": self._command.planned_date,
        }
        self._repetition_warnings.extend(
            self._domain.check_anchor_date_warning(spec.based_on, effective_dates)
        )

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
        self._apply_repetition_rule()
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

    def _apply_repetition_rule(self) -> None:
        """Merge, validate, and prepare repetition rule for the edit payload.

        Handles: UNSET (no change), None (clear), full set, partial update,
        same-type merge, type change, and no-existing-rule validation.

        Uses is_set() on FrequencyEditSpec fields for merge (D-11).
        """
        self._repetition_rule_payload: RepetitionRuleRepoPayload | None = None
        self._repetition_rule_clear: bool = False
        self._repetition_warns: list[str] = []

        spec = self._command.repetition_rule

        # EDIT-03: UNSET = no change
        if not is_set(spec):
            return

        # EDIT-02: None = clear the rule
        if spec is None:
            self._repetition_rule_clear = True
            return

        existing = self._task.repetition_rule

        # Resolve root fields, falling back to existing
        schedule: Schedule | None = (
            spec.schedule if is_set(spec.schedule) else (existing.schedule if existing else None)
        )
        based_on: BasedOn | None = (
            spec.based_on if is_set(spec.based_on) else (existing.based_on if existing else None)
        )

        # End: None = clear end, UNSET = preserve, value = set/change
        end: EndCondition | None
        if is_set(spec.end):
            end = spec.end  # EDIT-06/07/08: explicit set or clear (None)
        elif existing is not None:
            end = existing.end  # preserve existing
        else:
            end = None

        # Handle frequency
        frequency: Frequency | None = None
        if is_set(spec.frequency):
            edit_spec: FrequencyEditSpec = spec.frequency

            if existing is not None:
                # Determine type: use edit_spec.type if is_set(), else existing
                if is_set(edit_spec.type):
                    effective_type = edit_spec.type
                else:
                    effective_type = existing.frequency.type

                if is_set(edit_spec.type) and edit_spec.type != existing.frequency.type:
                    # Type change (D-09): full replacement with defaults
                    frequency = self._build_frequency_from_edit_spec(edit_spec, effective_type)
                else:
                    # Same type (explicit or inferred) -> merge (EDIT-09)
                    frequency = self._merge_frequency(edit_spec, existing.frequency)
            else:
                # No existing rule (EDIT-15)
                if not is_set(edit_spec.type):
                    raise ValueError(REPETITION_NO_EXISTING_RULE)
                frequency = self._build_frequency_from_edit_spec(edit_spec, edit_spec.type)
        else:
            # Frequency UNSET -> use existing
            frequency = existing.frequency if existing else None

        # EDIT-15: Can't partially update without an existing rule
        if frequency is None or schedule is None or based_on is None:
            raise ValueError(REPETITION_NO_EXISTING_RULE)

        # Normalize empty specialization fields (D-17)
        frequency, spec_warns = self._domain.normalize_empty_specialization_fields(frequency)
        self._repetition_warns.extend(spec_warns)

        # Check warnings (end date in past, completed/dropped task)
        self._repetition_warns.extend(
            self._domain.check_repetition_warnings(end=end, task=self._task)
        )

        # Check anchor date warning (VALID-05)
        effective_dates = {
            "due_date": self._command.due_date
            if is_set(self._command.due_date)
            else self._task.due_date,
            "defer_date": self._command.defer_date
            if is_set(self._command.defer_date)
            else self._task.defer_date,
            "planned_date": self._command.planned_date
            if is_set(self._command.planned_date)
            else self._task.planned_date,
        }
        self._repetition_warns.extend(
            self._domain.check_anchor_date_warning(based_on, effective_dates)
        )

        # Build the repo payload
        self._repetition_rule_payload = self._payload._build_repetition_rule_payload(
            frequency, schedule, based_on, end
        )

        if (
            existing is not None
            and self._repetition_rule_payload is not None
            and self._domain.repetition_payload_matches_existing(
                self._repetition_rule_payload, existing
            )
        ):
            self._repetition_warns.append(REPETITION_NO_OP)
            self._repetition_rule_payload = None

    def _merge_frequency(
        self,
        edit_spec: FrequencyEditSpec,
        existing: Frequency,
    ) -> Frequency:
        """Merge edit spec with existing frequency for same-type updates."""
        frequency, merge_warns = self._domain.merge_frequency(edit_spec, existing)
        self._repetition_warns.extend(merge_warns)
        return frequency

    def _build_frequency_from_edit_spec(
        self,
        edit_spec: FrequencyEditSpec,
        freq_type: str,
    ) -> Frequency:
        """Build a Frequency from an edit spec for type change or new rule.

        Full replacement with defaults: UNSET fields get defaults (like creation),
        not preserved from existing.
        """
        merged: dict[str, Any] = {"type": freq_type}

        # Interval: use if set, else default to 1
        merged["interval"] = edit_spec.interval if is_set(edit_spec.interval) else 1

        # Specialization fields: use if set (and not None), else default to None
        for field_name in ("on_days", "on", "on_dates"):
            edit_val = getattr(edit_spec, field_name)
            if is_set(edit_val):
                merged[field_name] = edit_val
            # else: defaults to None (not included in dict -> Frequency default)

        # Construct Frequency -> @model_validator fires (catches cross-type
        # violations and mutual exclusion — no auto-clear here since all
        # fields come from the agent, not merged with existing)
        return Frequency.model_validate(merged)

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
            repetition_rule_payload=self._repetition_rule_payload,
            repetition_rule_clear=self._repetition_rule_clear,
        )
        logger.debug(
            "OperatorService.edit_task: payload fields_set=%s",
            self._repo_payload.model_fields_set,
        )
        self._all_warnings = (
            self._lifecycle_warns + self._status_warns + self._repetition_warns + self._tag_warns
        )

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
