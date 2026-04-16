"""Thin orchestrator -- OperatorService and ErrorOperatorService.

OperatorService is the primary API surface for the MCP server. Each method
follows a short sequence: validate, resolve, domain logic, build payload,
delegate to repository. All heavy lifting lives in the extracted modules:

- ``resolve.py`` -- input resolution (parent, tags, validation)
- ``domain.py`` -- business rules (lifecycle, tags, cycle, no-op, move)
- ``payload.py`` -- typed repo payload construction
"""

from __future__ import annotations

import asyncio
import logging
from enum import StrEnum
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    from datetime import datetime

from omnifocus_operator.agent_messages.errors import (
    REPETITION_NO_EXISTING_RULE,
)
from omnifocus_operator.agent_messages.warnings import (
    AVAILABILITY_MIXED_ALL,
    LIST_PROJECTS_INBOX_WARNING,
    LIST_TASKS_INBOX_PROJECT_WARNING,
    REPETITION_NO_OP,
)
from omnifocus_operator.config import get_week_start, local_now
from omnifocus_operator.contracts.base import is_set, unset_to_none
from omnifocus_operator.contracts.protocols import Service
from omnifocus_operator.contracts.shared.repetition_rule import RepetitionRuleRepoPayload
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskResult
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskResult
from omnifocus_operator.contracts.use_cases.list._enums import (
    FolderAvailabilityFilter,
    TagAvailabilityFilter,
)
from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult, ListResult
from omnifocus_operator.contracts.use_cases.list.folders import (
    ListFoldersRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.perspectives import (
    ListPerspectivesRepoQuery,
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
from omnifocus_operator.models.enums import Availability, FolderAvailability, TagAvailability
from omnifocus_operator.models.repetition_rule import Frequency
from omnifocus_operator.service.convert import end_condition_from_spec, frequency_from_spec
from omnifocus_operator.service.domain import DomainLogic, normalize_date_input
from omnifocus_operator.service.payload import PayloadBuilder
from omnifocus_operator.service.resolve import Resolver
from omnifocus_operator.service.validate import (
    validate_task_name,
    validate_task_name_if_set,
)

if TYPE_CHECKING:
    from omnifocus_operator.contracts.shared.repetition_rule import (
        FrequencyEditSpec,
        RepetitionRuleEditSpec,
    )
    from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskCommand
    from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskCommand
    from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersQuery
    from omnifocus_operator.contracts.use_cases.list.perspectives import ListPerspectivesQuery
    from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsQuery
    from omnifocus_operator.contracts.use_cases.list.tags import ListTagsQuery
    from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksQuery
    from omnifocus_operator.models.enums import BasedOn, DueSoonSetting, Schedule
    from omnifocus_operator.models.folder import Folder
    from omnifocus_operator.models.perspective import Perspective
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.repetition_rule import EndCondition, RepetitionRule
    from omnifocus_operator.models.snapshot import AllEntities
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task
    from omnifocus_operator.repository import Repository
    from omnifocus_operator.service.preferences import OmniFocusPreferences

__all__ = ["ErrorOperatorService", "OperatorService"]

logger = logging.getLogger(__name__)


def matches_inbox_name(value: object) -> bool:
    """Check if a value is a case-insensitive substring of the inbox name."""
    if not isinstance(value, str):
        return False
    return value.lower() in "Inbox".lower()


def _expand_tag_availability(
    filters: list[TagAvailabilityFilter], warnings: list[str]
) -> list[TagAvailability]:
    """Expand TagAvailabilityFilter values to core TagAvailability for repo query."""
    has_all = TagAvailabilityFilter.ALL in filters
    if has_all:
        if len(filters) > 1:
            warnings.append(AVAILABILITY_MIXED_ALL)
        return list(TagAvailability)
    return [TagAvailability(f.value) for f in filters]


def _expand_folder_availability(
    filters: list[FolderAvailabilityFilter], warnings: list[str]
) -> list[FolderAvailability]:
    """Expand FolderAvailabilityFilter values to core FolderAvailability for repo query."""
    has_all = FolderAvailabilityFilter.ALL in filters
    if has_all:
        if len(filters) > 1:
            warnings.append(AVAILABILITY_MIXED_ALL)
        return list(FolderAvailability)
    return [FolderAvailability(f.value) for f in filters]


class OperatorService(Service):  # explicitly implements Service protocol
    """Service layer that delegates to the Repository protocol.

    Parameters
    ----------
    repository:
        Any ``Repository`` implementation (e.g. ``BridgeOnlyRepository``,
        ``HybridRepository``) that provides ``get_all()``.
    """

    def __init__(self, repository: Repository, preferences: OmniFocusPreferences) -> None:
        self._repository = repository
        self._preferences = preferences
        self._resolver = Resolver(repository)
        self._domain = DomainLogic(repository, self._resolver)
        self._payload = PayloadBuilder()

    # -- Read delegation (one-liner pass-throughs) -------------------------

    async def get_all_data(self) -> AllEntities:
        """Return all OmniFocus entities from the repository."""
        logger.debug("OperatorService.get_all_data: delegating to repository")
        raw = await self._repository.get_all()
        walked_tasks = await self._domain.compute_true_inheritance(raw.tasks)
        return raw.model_copy(update={"tasks": walked_tasks})

    async def get_task(self, task_id: str) -> Task:
        """Return a single task by ID. Raises ValueError if not found."""
        logger.debug("OperatorService.get_task: id=%s", task_id)
        task = await self._resolver.lookup_task(task_id)
        walked = await self._domain.compute_true_inheritance([task])
        return walked[0]

    async def get_project(self, project_id: str) -> Project:
        """Return a single project by ID. Raises ValueError if not found."""
        logger.debug("OperatorService.get_project: id=%s", project_id)
        return await self._resolver.lookup_project(project_id)

    async def get_tag(self, tag_id: str) -> Tag:
        """Return a single tag by ID. Raises ValueError if not found."""
        logger.debug("OperatorService.get_tag: id=%s", tag_id)
        return await self._resolver.lookup_tag(tag_id)

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
            self._preferences,
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
            self._preferences,
        )
        return await pipeline.execute(command)

    # -- list_tasks: delegates to _ListTasksPipeline (Method Object) --------

    async def list_tasks(self, query: ListTasksQuery) -> ListResult[Task]:
        """List tasks with name-to-ID resolution for project and tag filters."""
        pipeline = _ListTasksPipeline(
            self._resolver,
            self._domain,
            self._repository,
            self._preferences,
        )
        return await pipeline.execute(query)

    # -- list_projects: delegates to _ListProjectsPipeline (Method Object) --

    async def list_projects(self, query: ListProjectsQuery) -> ListResult[Project]:
        """List projects with name-to-ID resolution for folder filter."""
        pipeline = _ListProjectsPipeline(
            self._resolver,
            self._domain,
            self._repository,
            self._preferences,
        )
        return await pipeline.execute(query)

    # -- list pass-throughs (no entity-reference filters to resolve) ---------

    async def list_tags(self, query: ListTagsQuery) -> ListResult[Tag]:
        """List tags -- inline pass-through (no entity-reference filters)."""
        warnings: list[str] = []
        repo_query = ListTagsRepoQuery(
            availability=_expand_tag_availability(query.availability, warnings),
            search=unset_to_none(query.search),
            limit=query.limit,
            offset=query.offset,
        )
        repo_result = await self._repository.list_tags(repo_query)
        return ListResult(
            items=repo_result.items,
            total=repo_result.total,
            has_more=repo_result.has_more,
            warnings=warnings or None,
        )

    async def list_folders(self, query: ListFoldersQuery) -> ListResult[Folder]:
        """List folders -- inline pass-through (no entity-reference filters)."""
        warnings: list[str] = []
        repo_query = ListFoldersRepoQuery(
            availability=_expand_folder_availability(query.availability, warnings),
            search=unset_to_none(query.search),
            limit=query.limit,
            offset=query.offset,
        )
        repo_result = await self._repository.list_folders(repo_query)
        return ListResult(
            items=repo_result.items,
            total=repo_result.total,
            has_more=repo_result.has_more,
            warnings=warnings or None,
        )

    async def list_perspectives(self, query: ListPerspectivesQuery) -> ListResult[Perspective]:
        """List perspectives -- inline pass-through (search only)."""
        repo_query = ListPerspectivesRepoQuery(
            search=unset_to_none(query.search),
            limit=query.limit,
            offset=query.offset,
        )
        repo_result = await self._repository.list_perspectives(repo_query)
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
        preferences: OmniFocusPreferences,
    ) -> None:
        self._resolver = resolver
        self._domain = domain
        self._payload = payload
        self._repository = repository
        self._preferences = preferences


# -- Read pipeline base ----------------------------------------------------


class _ReadPipeline:
    """Shared dependencies for read-side list pipelines."""

    def __init__(
        self,
        resolver: Resolver,
        domain: DomainLogic,
        repository: Repository,
        preferences: OmniFocusPreferences,
    ) -> None:
        self._resolver = resolver
        self._domain = domain
        self._repository = repository
        self._preferences = preferences
        self._warnings: list[str] = []
        self._query: Any = None  # Set by subclass execute() before use

    async def _resolve_date_filters(self) -> None:
        """Resolve all 7 date filter fields via domain delegation."""
        self._now = local_now()

        # Resolve due-soon setting conditionally (D-02) -- I/O stays in pipeline
        due_soon_setting: DueSoonSetting | None = None
        if (
            is_set(self._query.due)
            and isinstance(self._query.due, StrEnum)
            and self._query.due.value == "soon"
        ):
            due_soon_setting = await self._preferences.get_due_soon_setting()

        # Drain preferences warnings (PREF-03) — surfaces fallback/unknown warnings
        self._warnings.extend(await self._preferences.get_warnings())

        week_start = get_week_start()

        # Delegate to domain -- field extraction + UNSET filtering handled there
        self._date_result = self._domain.resolve_date_filters(
            self._query, self._now, week_start, due_soon_setting
        )
        self._warnings.extend(self._date_result.warnings)

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

        tags_result, projects_result = await asyncio.gather(
            self._repository.list_tags(
                ListTagsRepoQuery(availability=list(TagAvailability), limit=None)
            ),
            self._repository.list_projects(
                ListProjectsRepoQuery(availability=list(Availability), limit=None)
            ),
        )
        self._tags = tags_result.items
        self._projects = projects_result.items

        self._in_inbox, self._project_to_resolve = self._resolver.resolve_inbox(
            unset_to_none(self._query.in_inbox), unset_to_none(self._query.project)
        )

        self._check_inbox_project_warning()
        self._resolve_project()
        self._resolve_tags()
        await self._resolve_date_filters()
        self._build_repo_query()
        return await self._delegate()

    def _check_inbox_project_warning(self) -> None:
        """Warn if project filter matches the inbox name (but $inbox was already consumed)."""
        if matches_inbox_name(self._project_to_resolve):
            self._warnings.append(
                LIST_TASKS_INBOX_PROJECT_WARNING.format(value=self._project_to_resolve)
            )

    def _resolve_project(self) -> None:
        self._project_ids: list[str] | None = None
        if self._project_to_resolve is None:
            return
        resolved = self._resolver.resolve_filter(self._project_to_resolve, self._projects)
        if resolved:
            self._project_ids = resolved
        self._warnings.extend(
            self._domain.check_filter_resolution(
                self._project_to_resolve, resolved, self._projects, "project"
            )
        )

    def _resolve_tags(self) -> None:
        self._tag_ids: list[str] | None = None
        if not is_set(self._query.tags):
            return
        all_resolved: list[str] = []
        seen: set[str] = set()
        for value in self._query.tags:
            resolved = self._resolver.resolve_filter(value, self._tags)
            if resolved:
                for eid in resolved:
                    if eid not in seen:
                        seen.add(eid)
                        all_resolved.append(eid)
            self._warnings.extend(
                self._domain.check_filter_resolution(value, resolved, self._tags, "tag")
            )
        if all_resolved:
            self._tag_ids = all_resolved

    def _build_repo_query(self) -> None:
        # Expand availability + merge lifecycle additions via domain
        expanded, avail_warns = self._domain.expand_availability(
            self._query.availability, self._date_result.lifecycle_additions
        )
        self._warnings.extend(avail_warns)

        # Unpack date bounds from domain result
        date_kwargs: dict[str, datetime | None] = {}
        for name, bounds in self._date_result.bounds.items():
            date_kwargs[f"{name}_after"] = bounds.after
            date_kwargs[f"{name}_before"] = bounds.before

        self._repo_query = ListTasksRepoQuery(
            in_inbox=self._in_inbox,
            flagged=unset_to_none(self._query.flagged),
            project_ids=self._project_ids,
            tag_ids=self._tag_ids,
            estimated_minutes_max=unset_to_none(self._query.estimated_minutes_max),
            availability=expanded,
            search=unset_to_none(self._query.search),
            limit=self._query.limit,
            offset=self._query.offset,
            **date_kwargs,
        )

    async def _delegate(self) -> ListResult[Task]:
        repo_result = await self._repository.list_tasks(self._repo_query)
        walked_items = await self._domain.compute_true_inheritance(repo_result.items)
        walked_result = repo_result.model_copy(update={"items": walked_items})
        return self._result_from_repo(walked_result)


# -- list_projects pipeline (Method Object) ---------------------------------


class _ListProjectsPipeline(_ReadPipeline):
    """Method object for list_projects -- resolve folder to IDs, then delegate."""

    async def execute(self, query: ListProjectsQuery) -> ListResult[Project]:
        """Run the full list-projects pipeline."""
        self._query = query

        folders_result = await self._repository.list_folders(
            ListFoldersRepoQuery(availability=list(FolderAvailability), limit=None)
        )
        self._folders = folders_result.items

        self._resolve_folder()
        self._check_inbox_search_warning()
        await self._resolve_date_filters()
        self._build_repo_query()
        return await self._delegate()

    def _check_inbox_search_warning(self) -> None:
        """Warn if search term matches system inbox name (per D-16 to D-19)."""
        if matches_inbox_name(self._query.search):
            self._warnings.append(LIST_PROJECTS_INBOX_WARNING)

    def _resolve_folder(self) -> None:
        self._folder_ids: list[str] | None = None
        if not is_set(self._query.folder):
            return
        resolved = self._resolver.resolve_filter(self._query.folder, self._folders)
        if resolved:
            self._folder_ids = resolved
        self._warnings.extend(
            self._domain.check_filter_resolution(
                self._query.folder, resolved, self._folders, "folder"
            )
        )

    def _build_repo_query(self) -> None:
        review_due_before: datetime | None = None
        review_due_within = unset_to_none(self._query.review_due_within)
        if review_due_within is not None:
            review_due_before = self._domain.expand_review_due(review_due_within, local_now())

        expanded, avail_warns = self._domain.expand_availability(
            self._query.availability, self._date_result.lifecycle_additions
        )
        self._warnings.extend(avail_warns)

        # Unpack date bounds from domain result
        date_kwargs: dict[str, datetime | None] = {}
        for name, bounds in self._date_result.bounds.items():
            date_kwargs[f"{name}_after"] = bounds.after
            date_kwargs[f"{name}_before"] = bounds.before

        self._repo_query = ListProjectsRepoQuery(
            availability=expanded,
            folder_ids=self._folder_ids,
            review_due_before=review_due_before,
            flagged=unset_to_none(self._query.flagged),
            search=unset_to_none(self._query.search),
            limit=self._query.limit,
            offset=self._query.offset,
            **date_kwargs,
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
        self._preferences_warnings: list[str] = []

        self._validate()
        await self._normalize_dates()
        await self._resolve_parent()
        await self._resolve_tags()
        self._process_repetition_rule()
        self._build_payload()
        return await self._delegate()

    async def _normalize_dates(self) -> None:
        """Normalize date inputs with user-configured default times from preferences."""
        updates: dict[str, str] = {}
        for field in ("due_date", "defer_date", "planned_date"):
            value = getattr(self._command, field)
            if value is not None:
                default_time = await self._preferences.get_default_time(field)
                updates[field] = normalize_date_input(value, default_time=default_time)
        if updates:
            self._command = self._command.model_copy(update=updates)
        # Drain preferences warnings (PREF-03) — surfaces fallback/unknown warnings
        self._preferences_warnings.extend(await self._preferences.get_warnings())

    def _validate(self) -> None:
        logger.debug(
            "OperatorService.add_task: name=%s, parent=%s, tags=%s",
            self._command.name,
            self._command.parent if is_set(self._command.parent) else "UNSET",
            self._command.tags,
        )
        validate_task_name(self._command.name)

    async def _resolve_parent(self) -> None:
        self._resolved_parent: str | None = None
        if not is_set(self._command.parent):
            return
        self._resolved_parent = await self._resolver.resolve_container(self._command.parent)

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
        """Normalize repetition rule and convert specs to core models.

        Converts FrequencyAddSpec -> Frequency and EndConditionSpec ->
        EndCondition at the service boundary. Stores core types on self
        for downstream use (no round-trip back to specs).
        """
        self._frequency: Frequency | None = None
        self._end_condition: EndCondition | None = None

        if self._command.repetition_rule is None:
            return

        spec = self._command.repetition_rule

        # Convert specs to core models at the service boundary
        freq = frequency_from_spec(spec.frequency)
        self._end_condition = end_condition_from_spec(spec.end)

        # Normalize empty specialization fields (D-17)
        normalized_freq, spec_warns = self._domain.normalize_empty_specialization_fields(freq)
        self._repetition_warnings.extend(spec_warns)
        self._frequency = normalized_freq

        # Collect all repetition warnings
        effective_dates = {
            "due_date": self._command.due_date,
            "defer_date": self._command.defer_date,
            "planned_date": self._command.planned_date,
        }
        self._repetition_warnings.extend(
            self._domain.collect_repetition_warnings(
                end=self._end_condition,
                based_on=spec.based_on,
                effective_dates=effective_dates,
                schedule=spec.schedule,
                frequency=self._frequency,
            )
        )

    def _build_payload(self) -> None:
        repetition_payload = None
        if self._frequency is not None and self._command.repetition_rule is not None:
            spec = self._command.repetition_rule
            repetition_payload = RepetitionRuleRepoPayload(
                frequency=self._frequency,
                schedule=spec.schedule,
                based_on=spec.based_on,
                end=self._end_condition,
            )
        self._repo_payload = self._payload.build_add(
            self._command,
            self._resolved_tag_ids,
            resolved_parent=self._resolved_parent,
            repetition_rule_payload=repetition_payload,
        )

    async def _delegate(self) -> AddTaskResult:
        logger.debug("OperatorService.add_task: delegating to repository")
        repo_result = await self._repository.add_task(self._repo_payload)
        all_warnings = self._preferences_warnings + self._repetition_warnings
        return AddTaskResult(
            status="success",
            id=repo_result.id,
            name=repo_result.name,
            warnings=all_warnings or None,
        )


# -- edit_task pipeline (Method Object) ------------------------------------


class _EditTaskPipeline(_Pipeline):
    """Method object for edit_task — each step is a named method, state on self."""

    async def execute(self, command: EditTaskCommand) -> EditTaskResult:
        """Run the full edit-task pipeline."""
        self._command = command
        self._preferences_warnings: list[str] = []

        await self._verify_task_exists()
        self._validate_and_normalize()
        await self._normalize_dates()
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
        self._task = await self._resolver.lookup_task(self._command.id)
        logger.debug(
            "OperatorService.edit_task: task found, name=%s, current_tags=%d",
            self._task.name,
            len(self._task.tags),
        )

    def _validate_and_normalize(self) -> None:
        validate_task_name_if_set(self._command.name)
        self._command = self._domain.normalize_clear_intents(self._command)

    async def _normalize_dates(self) -> None:
        """Normalize date inputs with user-configured default times from preferences."""
        updates: dict[str, str] = {}
        for field in ("due_date", "defer_date", "planned_date"):
            value = getattr(self._command, field)
            if is_set(value) and value is not None:
                default_time = await self._preferences.get_default_time(field)
                updates[field] = normalize_date_input(value, default_time=default_time)
        if updates:
            self._command = self._command.model_copy(update=updates)
        # Drain preferences warnings (PREF-03) — surfaces fallback/unknown warnings
        self._preferences_warnings.extend(await self._preferences.get_warnings())

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
        """Resolve, normalize, and prepare repetition rule for the edit payload.

        Three-phase structure mirroring _process_repetition_rule in Add:
        1. Resolve — each field to a core type (from spec, existing, or merge)
        2. Normalize + warn — domain normalization and validation warnings
        3. Assemble — build RepetitionRuleRepoPayload and detect no-op
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

        self._resolve_repetition_fields(spec, existing)
        self._normalize_and_warn_repetition()
        self._assemble_repetition_payload(existing)

    # -- Repetition rule sub-steps ------------------------------------------

    def _resolve_repetition_fields(
        self,
        spec: RepetitionRuleEditSpec,
        existing: RepetitionRule | None,
    ) -> None:
        """Resolve each repetition field to a core type from spec or existing."""
        # Resolve with locals (may be None before validation)
        schedule: Schedule | None = (
            spec.schedule if is_set(spec.schedule) else (existing.schedule if existing else None)
        )
        based_on: BasedOn | None = (
            spec.based_on if is_set(spec.based_on) else (existing.based_on if existing else None)
        )

        # End condition: set → convert, existing → preserve, neither → None
        end: EndCondition | None
        if is_set(spec.end):
            end = end_condition_from_spec(spec.end)
        elif existing is not None:
            end = existing.end
        else:
            end = None

        # Frequency: merge, type-change, fresh build, or keep existing
        frequency: Frequency | None = self._resolve_frequency(spec.frequency, existing)

        # EDIT-15: All fields must be resolved — validation narrows types
        if frequency is None or schedule is None or based_on is None:
            raise ValueError(REPETITION_NO_EXISTING_RULE)

        # Store validated (non-None) types for downstream methods
        self._rr_frequency: Frequency = frequency
        self._rr_schedule: Schedule = schedule
        self._rr_based_on: BasedOn = based_on
        self._rr_end: EndCondition | None = end

    def _resolve_frequency(
        self,
        freq_spec: FrequencyEditSpec | object,
        existing: RepetitionRule | None,
    ) -> Frequency | None:
        """Resolve frequency from edit spec, existing rule, or both.

        Handles same-type merge (EDIT-09), type change (D-09),
        fresh build (EDIT-15), and UNSET (keep existing).
        """
        if not is_set(freq_spec):
            return existing.frequency if existing else None

        edit_spec: FrequencyEditSpec = freq_spec  # type: ignore[assignment]

        if existing is not None:
            effective_type = edit_spec.type if is_set(edit_spec.type) else existing.frequency.type

            if is_set(edit_spec.type) and edit_spec.type != existing.frequency.type:
                # Type change (D-09): full replacement with defaults
                return self._build_frequency_from_edit_spec(edit_spec, effective_type)
            # Same type (explicit or inferred) -> merge (EDIT-09)
            return self._merge_frequency(edit_spec, existing.frequency)

        # No existing rule (EDIT-15)
        if not is_set(edit_spec.type):
            raise ValueError(REPETITION_NO_EXISTING_RULE)
        return self._build_frequency_from_edit_spec(edit_spec, edit_spec.type)

    def _normalize_and_warn_repetition(self) -> None:
        """Normalize frequency and collect all repetition warnings."""
        # Normalize empty specialization fields (D-17)
        self._rr_frequency, spec_warns = self._domain.normalize_empty_specialization_fields(
            self._rr_frequency
        )
        self._repetition_warns.extend(spec_warns)

        # Collect all repetition warnings
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
            self._domain.collect_repetition_warnings(
                end=self._rr_end,
                based_on=self._rr_based_on,
                effective_dates=effective_dates,
                schedule=self._rr_schedule,
                frequency=self._rr_frequency,
            )
        )

    def _assemble_repetition_payload(self, existing: RepetitionRule | None) -> None:
        """Build RepetitionRuleRepoPayload and detect no-op edits."""
        self._repetition_rule_payload = RepetitionRuleRepoPayload(
            frequency=self._rr_frequency,
            schedule=self._rr_schedule,
            based_on=self._rr_based_on,
            end=self._rr_end,
        )

        if existing is not None and self._domain.repetition_payload_matches_existing(
            self._repetition_rule_payload, existing
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
        # Dump spec to dict — converts nested models (e.g. OrdinalWeekdaySpec)
        # to plain dicts and strips UNSET fields in one shot.
        spec_dict = edit_spec.model_dump(exclude_defaults=True)

        merged: dict[str, Any] = {"type": freq_type}
        merged["interval"] = spec_dict.get("interval", 1)

        for field_name in ("on_days", "on", "on_dates"):
            if field_name in spec_dict:
                merged[field_name] = spec_dict[field_name]

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
            self._preferences_warnings
            + self._lifecycle_warns
            + self._status_warns
            + self._repetition_warns
            + self._tag_warns
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
            status="success",
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
