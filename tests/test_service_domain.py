"""Unit tests for DomainLogic -- business rules for the edit-task pipeline.

Tests use StubResolver and StubRepo (no repository dependency),
independent of repository implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from omnifocus_operator.agent_messages.errors import (
    NOTE_APPEND_WITH_REPLACE,
    NOTE_NO_OPERATION,
)
from omnifocus_operator.agent_messages.warnings import (
    EDIT_COMPLETED_TASK,
    FILTERED_SUBTREE_WARNING,
    LIFECYCLE_REPEATING_COMPLETE,
    LIFECYCLE_REPEATING_DROP,
    NOTE_ALREADY_EMPTY,
    NOTE_APPEND_EMPTY,
    NOTE_REPLACE_ALREADY_CONTENT,
    REPETITION_AUTO_CLEAR_ON,
    REPETITION_AUTO_CLEAR_ON_DATES,
    REPETITION_EMPTY_ON,
    REPETITION_EMPTY_ON_DATES,
    REPETITION_EMPTY_ON_DAYS,
    REPETITION_FROM_COMPLETION_BYDAY,
)
from omnifocus_operator.contracts.base import UNSET, _Unset, is_non_default
from omnifocus_operator.contracts.shared.actions import MoveAction, NoteAction, TagAction
from omnifocus_operator.contracts.shared.repetition_rule import (
    FrequencyEditSpec,
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.contracts.use_cases.edit.tasks import (
    EditTaskActions,
    EditTaskCommand,
    EditTaskRepoPayload,
    MoveToRepoPayload,
)
from omnifocus_operator.contracts.use_cases.list._date_filter import (
    AbsoluteRangeFilter,
    LastPeriodFilter,
    NextPeriodFilter,
    ThisPeriodFilter,
)
from omnifocus_operator.contracts.use_cases.list._enums import (
    AvailabilityFilter,
    DateShortcut,
    DueDateShortcut,
    LifecycleDateShortcut,
)
from omnifocus_operator.contracts.use_cases.list.tasks import _PATCH_FIELDS, ListTasksQuery
from omnifocus_operator.models.common import TagRef
from omnifocus_operator.models.enums import (
    Availability,
    BasedOn,
    DueSoonSetting,
    EntityType,
    ProjectType,
    Schedule,
    TaskType,
)
from omnifocus_operator.models.project import Project
from omnifocus_operator.models.repetition_rule import (
    EndByDate,
    Frequency,
    OrdinalWeekday,
)
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.models.task import Task
from omnifocus_operator.service.domain import (
    _NON_SUBTREE_PRUNING_FIELDS,
    _SUBTREE_PRUNING_FIELDS,
    DomainLogic,
    _to_utc_ts,
    normalize_date_input,
)
from omnifocus_operator.service.errors import EntityTypeMismatchError
from tests.conftest import make_snapshot_dict
from tests.doubles import InMemoryBridge

from .conftest import (
    make_model_project_dict,
    make_model_tag_dict,
    make_model_task_dict,
    make_snapshot,
    make_task_dict,
)

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class StubResolver:
    """Returns pre-configured IDs. No repository dependency."""

    def __init__(
        self,
        tag_map: dict[str, str] | None = None,
        tasks: list[Task] | None = None,
        anchor_errors: dict[str, str | Exception] | None = None,
    ) -> None:
        self._tag_map = tag_map or {}
        self._tasks = {t.id: t for t in (tasks or [])}
        self._anchor_errors: dict[str, str | Exception] = anchor_errors or {}

    async def resolve_tags(self, names: list[str]) -> list[str]:
        return [self._tag_map[n] for n in names]

    async def resolve_container(self, pid: str) -> str | None:
        if pid == "$inbox":
            return None
        return pid  # always succeeds

    async def resolve_anchor(self, anchor_id: str) -> str:
        if anchor_id in self._anchor_errors:
            err = self._anchor_errors[anchor_id]
            if isinstance(err, Exception):
                raise err
            raise ValueError(err)
        return anchor_id  # always succeeds

    async def lookup_task(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            msg = f"Task not found: {task_id}"
            raise ValueError(msg)
        return task


class StubRepo:
    """Minimal repo for DomainLogic tests. Returns pre-configured data."""

    def __init__(
        self,
        tasks: list[Task] | None = None,
        tags: list[object] | None = None,
        snapshot: AllEntities | None = None,
        edge_children: dict[tuple[str, str], str | None] | None = None,
    ) -> None:
        if snapshot is not None:
            self._snapshot = snapshot
        else:
            self._snapshot = AllEntities.model_validate(
                {
                    "tasks": [],
                    "projects": [],
                    "tags": [],
                    "folders": [],
                    "perspectives": [],
                }
            )
            if tasks:
                self._snapshot.tasks.extend(tasks)
            if tags:
                self._snapshot.tags.extend(tags)  # type: ignore[arg-type]
        self._edge_children: dict[tuple[str, str], str | None] = edge_children or {}

    async def get_all(self) -> AllEntities:
        return self._snapshot

    async def get_task(self, task_id: str) -> Task | None:
        return next((t for t in self._snapshot.tasks if t.id == task_id), None)

    async def get_project(self, project_id: str) -> object:
        return next((p for p in self._snapshot.projects if p.id == project_id), None)

    async def get_edge_child_id(self, parent_id: str, edge: str) -> str | None:
        return self._edge_children.get((parent_id, edge))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(**overrides: object) -> Task:
    """Create a Task model from make_model_task_dict defaults."""
    return Task.model_validate(make_model_task_dict(**overrides))


def _domain(
    tag_map: dict[str, str] | None = None,
    tasks: list[Task] | None = None,
    tags: list[object] | None = None,
    snapshot: AllEntities | None = None,
    anchor_errors: dict[str, str] | None = None,
    edge_children: dict[tuple[str, str], str | None] | None = None,
) -> DomainLogic:
    """Build a DomainLogic with stub dependencies."""
    resolver = StubResolver(tag_map, tasks=tasks, anchor_errors=anchor_errors)
    repo = StubRepo(tasks=tasks, tags=tags, snapshot=snapshot, edge_children=edge_children)
    return DomainLogic(repo, resolver)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# process_lifecycle
# ---------------------------------------------------------------------------


class TestProcessLifecycle:
    """Lifecycle state transitions and warning generation."""

    def test_complete_available_task(self) -> None:
        task = _make_task(availability="available")
        should_call, warnings = _domain().process_lifecycle("complete", task)
        assert should_call is True
        assert warnings == []

    def test_complete_already_completed(self) -> None:
        task = _make_task(availability="completed")
        should_call, warnings = _domain().process_lifecycle("complete", task)
        assert should_call is False
        assert len(warnings) == 1
        assert "already complete" in warnings[0].lower()

    def test_drop_already_dropped(self) -> None:
        task = _make_task(availability="dropped")
        should_call, warnings = _domain().process_lifecycle("drop", task)
        assert should_call is False
        assert len(warnings) == 1
        assert "already dropped" in warnings[0].lower()

    def test_cross_state_completed_to_dropped(self) -> None:
        task = _make_task(availability="completed")
        should_call, warnings = _domain().process_lifecycle("drop", task)
        assert should_call is True
        assert any("completed" in w and "drop" in w.lower() for w in warnings)

    def test_repeating_complete(self) -> None:
        task = _make_task(
            repetitionRule={
                "frequency": {"type": "weekly"},
                "schedule": "regularly",
                "basedOn": "due_date",
            }
        )
        should_call, warnings = _domain().process_lifecycle("complete", task)
        assert should_call is True
        assert LIFECYCLE_REPEATING_COMPLETE in warnings

    def test_repeating_drop(self) -> None:
        task = _make_task(
            repetitionRule={
                "frequency": {"type": "weekly"},
                "schedule": "regularly",
                "basedOn": "due_date",
            }
        )
        should_call, warnings = _domain().process_lifecycle("drop", task)
        assert should_call is True
        assert LIFECYCLE_REPEATING_DROP in warnings


# ---------------------------------------------------------------------------
# check_completed_status
# ---------------------------------------------------------------------------


class TestCheckCompletedStatus:
    """Warns when editing completed/dropped tasks without lifecycle action."""

    def test_completed_without_lifecycle_warns(self) -> None:
        task = _make_task(availability="completed")
        warnings = _domain().check_completed_status(task, has_lifecycle=False)
        assert len(warnings) == 1
        assert "completed" in warnings[0]
        assert "confirm with the user" in warnings[0]

    def test_completed_with_lifecycle_no_warn(self) -> None:
        task = _make_task(availability="completed")
        warnings = _domain().check_completed_status(task, has_lifecycle=True)
        assert warnings == []

    def test_available_no_warn(self) -> None:
        task = _make_task(availability="available")
        warnings = _domain().check_completed_status(task, has_lifecycle=False)
        assert warnings == []


# ---------------------------------------------------------------------------
# compute_tag_diff
# ---------------------------------------------------------------------------


class TestComputeTagDiff:
    """Tag diff computation with stub Resolver."""

    async def test_add_new_tag(self) -> None:
        domain = _domain(
            tag_map={"Work": "tag-work"},
            snapshot=make_snapshot(tags=[make_model_tag_dict(id="tag-work", name="Work")]),
        )
        current_tags = []  # no tags on task
        add_ids, remove_ids, warnings = await domain.compute_tag_diff(
            TagAction(add=["Work"]),
            current_tags,
        )
        assert "tag-work" in add_ids
        assert remove_ids == []
        assert warnings == []

    async def test_add_existing_tag_warns(self) -> None:
        domain = _domain(
            tag_map={"Work": "tag-work"},
            snapshot=make_snapshot(tags=[make_model_tag_dict(id="tag-work", name="Work")]),
        )
        current_tags = [TagRef(id="tag-work", name="Work")]
        _add_ids, _remove_ids, warnings = await domain.compute_tag_diff(
            TagAction(add=["Work"]),
            current_tags,
        )
        assert any("already on this task" in w for w in warnings)

    async def test_remove_existing_tag(self) -> None:
        domain = _domain(
            tag_map={"Work": "tag-work"},
            snapshot=make_snapshot(tags=[make_model_tag_dict(id="tag-work", name="Work")]),
        )
        current_tags = [TagRef(id="tag-work", name="Work")]
        add_ids, remove_ids, warnings = await domain.compute_tag_diff(
            TagAction(remove=["Work"]),
            current_tags,
        )
        assert "tag-work" in remove_ids
        assert add_ids == []
        assert warnings == []

    async def test_remove_absent_tag_warns(self) -> None:
        domain = _domain(
            tag_map={"Work": "tag-work"},
            snapshot=make_snapshot(tags=[make_model_tag_dict(id="tag-work", name="Work")]),
        )
        current_tags = []  # tag not on task
        _add_ids, _remove_ids, warnings = await domain.compute_tag_diff(
            TagAction(remove=["Work"]),
            current_tags,
        )
        assert any("is not on this task" in w for w in warnings)

    async def test_replace_tags(self) -> None:
        domain = _domain(
            tag_map={"Home": "tag-home"},
            snapshot=make_snapshot(
                tags=[
                    make_model_tag_dict(id="tag-work", name="Work"),
                    make_model_tag_dict(id="tag-home", name="Home"),
                ]
            ),
        )
        current_tags = [TagRef(id="tag-work", name="Work")]
        add_ids, remove_ids, warnings = await domain.compute_tag_diff(
            TagAction(replace=["Home"]),
            current_tags,
        )
        assert "tag-home" in add_ids
        assert "tag-work" in remove_ids
        assert warnings == []

    async def test_replace_same_warns(self) -> None:
        domain = _domain(
            tag_map={"Work": "tag-work"},
            snapshot=make_snapshot(tags=[make_model_tag_dict(id="tag-work", name="Work")]),
        )
        current_tags = [TagRef(id="tag-work", name="Work")]
        add_ids, remove_ids, warnings = await domain.compute_tag_diff(
            TagAction(replace=["Work"]),
            current_tags,
        )
        assert add_ids == []
        assert remove_ids == []
        assert any("already match" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# detect_early_return
# ---------------------------------------------------------------------------


class TestDetectEarlyReturn:
    """No-op and empty-edit detection."""

    def test_empty_edit_no_warnings(self) -> None:
        task = _make_task(id="t1", name="Task")
        payload = EditTaskRepoPayload.model_validate({"id": "t1"})
        result = _domain().detect_early_return(payload, task, [])
        assert result is not None
        assert result.warnings is not None
        assert any("No changes specified" in w for w in result.warnings)

    def test_empty_edit_with_warnings(self) -> None:
        task = _make_task(id="t1", name="Task", availability="completed")
        payload = EditTaskRepoPayload.model_validate({"id": "t1"})
        warnings = [EDIT_COMPLETED_TASK.format(status="completed")]
        result = _domain().detect_early_return(payload, task, warnings)
        assert result is not None
        assert result.warnings is not None
        assert any("completed" in w for w in result.warnings)
        # Should NOT include "No changes specified" when there are existing warnings
        assert not any("No changes specified" in w for w in result.warnings)

    def test_noop_all_fields_match(self) -> None:
        task = _make_task(id="t1", name="Foo")
        payload = EditTaskRepoPayload.model_validate({"id": "t1", "name": "Foo"})
        result = _domain().detect_early_return(payload, task, [])
        assert result is not None
        assert result.warnings is not None
        assert any("No changes detected" in w for w in result.warnings)

    def test_noop_filters_status_warnings(self) -> None:
        task = _make_task(id="t1", name="Foo", availability="completed")
        payload = EditTaskRepoPayload.model_validate({"id": "t1", "name": "Foo"})
        # Status warning contains "your changes were applied"
        warnings = [EDIT_COMPLETED_TASK.format(status="completed")]
        result = _domain().detect_early_return(payload, task, warnings)
        assert result is not None
        assert result.warnings is not None
        # Status warning should be filtered (contains "your changes were applied")
        assert not any("your changes were applied" in w for w in result.warnings)
        # Should have the no-op warning instead
        assert any("No changes detected" in w for w in result.warnings)

    def test_not_noop_returns_none(self) -> None:
        task = _make_task(id="t1", name="Foo")
        payload = EditTaskRepoPayload.model_validate({"id": "t1", "name": "Bar"})
        result = _domain().detect_early_return(payload, task, [])
        assert result is None


# ---------------------------------------------------------------------------
# Move no-op detection (D-12, D-13)
# ---------------------------------------------------------------------------


class TestMoveNoOpDetection:
    """No-op detection for translated moves (D-12, D-13).

    After Plan 01 translates beginning/ending to before/after with anchor IDs,
    the no-op check uses anchor_id == task_id to detect self-reference.
    """

    def test_anchor_id_equals_task_id_beginning_is_noop(self) -> None:
        """First child -> beginning -> before(self) is a no-op with position warning."""
        task = _make_task(
            id="t1",
            name="Task",
            parent={"task": {"id": "parent-1", "name": "P"}},
            project={"id": "proj-1", "name": "Proj"},
        )
        payload = EditTaskRepoPayload(
            id="t1", move_to=MoveToRepoPayload(position="before", anchor_id="t1")
        )
        warnings: list[str] = []
        result = _domain().detect_early_return(payload, task, warnings)
        assert result is not None  # early return = no-op
        assert result.status == "success"
        assert result.warnings is not None
        assert any("beginning" in w for w in result.warnings)
        assert any("already at the" in w for w in result.warnings)

    def test_anchor_id_equals_task_id_ending_is_noop(self) -> None:
        """Last child -> ending -> after(self) is a no-op with position warning."""
        task = _make_task(
            id="t1",
            name="Task",
            parent={"task": {"id": "parent-1", "name": "P"}},
            project={"id": "proj-1", "name": "Proj"},
        )
        payload = EditTaskRepoPayload(
            id="t1", move_to=MoveToRepoPayload(position="after", anchor_id="t1")
        )
        warnings: list[str] = []
        result = _domain().detect_early_return(payload, task, warnings)
        assert result is not None
        assert result.status == "success"
        assert result.warnings is not None
        assert any("ending" in w for w in result.warnings)
        assert any("already at the" in w for w in result.warnings)

    def test_anchor_id_different_from_task_id_not_noop(self) -> None:
        """Non-edge child -> beginning -> before(first) proceeds."""
        task = _make_task(
            id="t1",
            name="Task",
            parent={"task": {"id": "parent-1", "name": "P"}},
            project={"id": "proj-1", "name": "Proj"},
        )
        payload = EditTaskRepoPayload(
            id="t1", move_to=MoveToRepoPayload(position="before", anchor_id="other-child")
        )
        result = _domain().detect_early_return(payload, task, [])
        assert result is None  # not a no-op, proceed

    def test_untranslated_same_container_is_noop(self) -> None:
        """Empty container, same parent -> no-op with position warning."""
        task = _make_task(
            id="t1",
            name="Task",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "Proj"},
        )
        payload = EditTaskRepoPayload(
            id="t1", move_to=MoveToRepoPayload(position="beginning", container_id="proj-1")
        )
        warnings: list[str] = []
        result = _domain().detect_early_return(payload, task, warnings)
        assert result is not None
        assert result.status == "success"
        assert result.warnings is not None
        assert any("beginning" in w for w in result.warnings)
        assert any("already at the" in w for w in result.warnings)

    def test_untranslated_different_container_not_noop(self) -> None:
        """Empty different container -> proceed."""
        task = _make_task(
            id="t1",
            name="Task",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "Proj"},
        )
        payload = EditTaskRepoPayload(
            id="t1", move_to=MoveToRepoPayload(position="beginning", container_id="proj-2")
        )
        result = _domain().detect_early_return(payload, task, [])
        assert result is None  # different container, proceed


# ---------------------------------------------------------------------------
# process_move
# ---------------------------------------------------------------------------


class TestProcessMove:
    """Move processing with stub Resolver."""

    async def test_move_to_inbox(self) -> None:
        domain = _domain()
        result = await domain.process_move(MoveAction(ending="$inbox"), "task-1")
        assert result == {"position": "ending", "container_id": None}

    async def test_move_to_project(self) -> None:
        # StubResolver.resolve_container always succeeds; StubRepo.get_task returns None
        # for the container (it's a project, not a task), so no cycle check
        domain = _domain()
        result = await domain.process_move(MoveAction(ending="proj-1"), "task-1")
        assert result == {"position": "ending", "container_id": "proj-1"}

    async def test_move_before_anchor(self) -> None:
        task = _make_task(id="task-anchor", name="Anchor")
        domain = _domain(tasks=[task])
        result = await domain.process_move(MoveAction(before="task-anchor"), "task-1")
        assert result == {"position": "before", "anchor_id": "task-anchor"}

    async def test_entity_type_mismatch_enriched_with_anchor_context(self) -> None:
        """EntityTypeMismatchError from resolver is caught and enriched with anchor guidance."""
        domain = _domain(
            anchor_errors={
                "$inbox": EntityTypeMismatchError(
                    "$inbox",
                    resolved_type=EntityType.PROJECT,
                    accepted_types=[EntityType.TASK],
                )
            }
        )
        with pytest.raises(ValueError, match="is a project") as exc_info:
            await domain.process_move(MoveAction(before="$inbox"), "task-1")
        error_msg = str(exc_info.value)
        assert "task reference" in error_msg
        assert "ending" in error_msg
        assert "beginning" in error_msg

    async def test_other_resolver_errors_propagate_through_anchor_move(self) -> None:
        """Non-EntityTypeMismatch errors propagate directly — no wrapping."""
        domain = _domain(anchor_errors={"bad-ref": "No task found"})
        with pytest.raises(ValueError, match="No task found"):
            await domain.process_move(MoveAction(before="bad-ref"), "task-1")

    # -- Translation: beginning/ending -> before/after when container has children --

    async def test_move_beginning_translates_to_before_first_child(self) -> None:
        """beginning + container has children -> before(first_child)."""
        domain = _domain(edge_children={("proj-1", "first"): "child-1"})
        result = await domain.process_move(MoveAction(beginning="proj-1"), "task-1")
        assert result == {"position": "before", "anchor_id": "child-1"}

    async def test_move_ending_translates_to_after_last_child(self) -> None:
        """ending + container has children -> after(last_child)."""
        domain = _domain(edge_children={("proj-1", "last"): "child-99"})
        result = await domain.process_move(MoveAction(ending="proj-1"), "task-1")
        assert result == {"position": "after", "anchor_id": "child-99"}

    async def test_move_beginning_empty_container_no_translation(self) -> None:
        """beginning + empty container -> passes through unchanged."""
        domain = _domain()  # no edge_children = empty container
        result = await domain.process_move(MoveAction(beginning="proj-1"), "task-1")
        assert result == {"position": "beginning", "container_id": "proj-1"}

    async def test_move_ending_empty_container_no_translation(self) -> None:
        """ending + empty container -> passes through unchanged."""
        domain = _domain()
        result = await domain.process_move(MoveAction(ending="proj-1"), "task-1")
        assert result == {"position": "ending", "container_id": "proj-1"}

    async def test_move_to_inbox_beginning_translates(self) -> None:
        """beginning + inbox with children -> before(first inbox child)."""
        domain = _domain(edge_children={("$inbox", "first"): "inbox-child-1"})
        result = await domain.process_move(MoveAction(beginning="$inbox"), "task-1")
        assert result == {"position": "before", "anchor_id": "inbox-child-1"}

    async def test_move_to_inbox_ending_empty_no_translation(self) -> None:
        """ending + empty inbox -> passes through unchanged."""
        domain = _domain()
        result = await domain.process_move(MoveAction(ending="$inbox"), "task-1")
        assert result == {"position": "ending", "container_id": None}


# ---------------------------------------------------------------------------
# check_cycle
# ---------------------------------------------------------------------------


class TestCheckCycle:
    """Cycle detection in the parent-child graph."""

    async def test_no_cycle_passes(self) -> None:
        parent = _make_task(id="t-parent", name="Parent")
        child = _make_task(
            id="t-child",
            name="Child",
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "Proj"},
        )
        domain = _domain(tasks=[parent, child])
        # Moving t-parent under t-child would be a cycle, but moving
        # an unrelated task under t-parent is fine
        await domain.check_cycle("t-unrelated", "t-parent")  # should not raise

    async def test_cycle_raises(self) -> None:
        parent = _make_task(id="t-parent", name="Parent")
        child = _make_task(
            id="t-child",
            name="Child",
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "Proj"},
        )
        domain = _domain(tasks=[parent, child])
        with pytest.raises(ValueError, match="circular reference"):
            await domain.check_cycle("t-parent", "t-child")


# ---------------------------------------------------------------------------
# normalize_clear_intents
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# NoteAction — contract-level validator tests (exclusivity + at-least-one)
# ---------------------------------------------------------------------------


class TestNoteAction:
    """Pydantic validator tests for contracts.shared.actions.NoteAction.

    Covers D-01 (exclusivity + at-least-one) and D-02 (Patch[str] null rejection).
    """

    def test_empty_raises_no_operation(self) -> None:
        """NoteAction() with no fields set raises ValidationError (NOTE_NO_OPERATION)."""
        with pytest.raises(ValidationError) as exc_info:
            NoteAction()
        assert NOTE_NO_OPERATION in str(exc_info.value)

    def test_both_modes_raises_append_with_replace(self) -> None:
        """NoteAction(append=..., replace=...) raises ValidationError (NOTE_APPEND_WITH_REPLACE)."""
        with pytest.raises(ValidationError) as exc_info:
            NoteAction(append="x", replace="y")
        assert NOTE_APPEND_WITH_REPLACE in str(exc_info.value)

    def test_append_null_rejected_by_type(self) -> None:
        """NoteAction(append=None) rejected by Patch[str] type machinery.

        Pydantic raises ValidationError with its default type-error message;
        we only assert a ValidationError is raised (custom text not required
        per D-02 — the type alias alone is sufficient).
        """
        with pytest.raises(ValidationError):
            NoteAction(append=None)

    def test_replace_null_is_valid(self) -> None:
        """NoteAction(replace=None) constructs successfully — null = clear intent (PatchOrClear)."""
        action = NoteAction(replace=None)
        # sanity: the field is set (not UNSET), value is None
        assert action.replace is None


class TestNormalizeClearIntents:
    """Null-means-clear normalization centralized in DomainLogic."""

    def test_tags_replace_none_becomes_empty_list(self) -> None:
        domain = _domain()
        cmd = EditTaskCommand(id="t1", actions=EditTaskActions(tags=TagAction(replace=None)))
        result = domain.normalize_clear_intents(cmd)
        assert result.actions.tags.replace == []

    def test_tags_replace_with_names_unchanged(self) -> None:
        domain = _domain()
        cmd = EditTaskCommand(id="t1", actions=EditTaskActions(tags=TagAction(replace=["Work"])))
        result = domain.normalize_clear_intents(cmd)
        assert result.actions.tags.replace == ["Work"]

    def test_no_actions_unchanged(self) -> None:
        domain = _domain()
        cmd = EditTaskCommand(id="t1", name="Foo")
        result = domain.normalize_clear_intents(cmd)
        assert result.name == "Foo"


# ---------------------------------------------------------------------------
# check_repetition_warnings
# ---------------------------------------------------------------------------


class TestRepetitionWarnings:
    """Warning generation for repetition rule edge cases."""

    def test_end_date_in_past_warns(self) -> None:
        """End date before now -> REPETITION_END_DATE_PAST warning."""
        domain = _domain()
        end = EndByDate(date=date(2020, 1, 1))
        warnings = domain.check_repetition_warnings(end=end)
        assert len(warnings) == 1
        assert "2020-01-01" in warnings[0]

    def test_end_date_in_future_no_warn(self) -> None:
        """End date in future -> no warning."""
        domain = _domain()
        end = EndByDate(date=date(2099, 12, 31))
        warnings = domain.check_repetition_warnings(end=end)
        assert warnings == []

    def test_no_end_no_warn(self) -> None:
        """No end condition -> no warning."""
        domain = _domain()
        warnings = domain.check_repetition_warnings(end=None)
        assert warnings == []


# ---------------------------------------------------------------------------
# check_from_completion_byday_warning
# ---------------------------------------------------------------------------


class TestFromCompletionBydayWarning:
    """Warn when from_completion is combined with day-of-week patterns."""

    def test_from_completion_with_on_days_warns(self) -> None:
        """from_completion + onDays -> warning about BYDAY edge cases."""
        domain = _domain()
        freq = Frequency(type="weekly", on_days=["MO", "FR"])
        warnings = domain.check_from_completion_byday_warning(Schedule.FROM_COMPLETION, freq)
        assert len(warnings) == 1
        assert warnings[0] == REPETITION_FROM_COMPLETION_BYDAY

    def test_from_completion_without_on_days_no_warn(self) -> None:
        """from_completion + daily (no onDays) -> no warning."""
        domain = _domain()
        freq = Frequency(type="daily")
        warnings = domain.check_from_completion_byday_warning(Schedule.FROM_COMPLETION, freq)
        assert warnings == []

    def test_catch_up_with_on_days_no_warn(self) -> None:
        """regularly_with_catch_up + onDays -> no warning (BYDAY is fine here)."""
        domain = _domain()
        freq = Frequency(type="weekly", on_days=["MO", "FR"])
        warnings = domain.check_from_completion_byday_warning(
            Schedule.REGULARLY_WITH_CATCH_UP, freq
        )
        assert warnings == []

    def test_regularly_with_on_days_no_warn(self) -> None:
        """regularly + onDays -> no warning."""
        domain = _domain()
        freq = Frequency(type="weekly", on_days=["WE"])
        warnings = domain.check_from_completion_byday_warning(Schedule.REGULARLY, freq)
        assert warnings == []


# ---------------------------------------------------------------------------
# normalize_empty_specialization_fields
# ---------------------------------------------------------------------------


class TestNormalizeEmptySpecializationFields:
    """D-17: Empty specialization fields normalize to None + warning."""

    def test_empty_on_dates(self) -> None:
        """monthly with onDates=[] -> on_dates=None + warning."""
        domain = _domain()
        freq = Frequency(type="monthly", on_dates=[])
        result_freq, warnings = domain.normalize_empty_specialization_fields(freq)
        assert result_freq.on_dates is None
        assert len(warnings) == 1
        assert REPETITION_EMPTY_ON_DATES in warnings[0]

    def test_non_empty_on_dates_unchanged(self) -> None:
        """onDates=[15] -> same frequency, no warning."""
        domain = _domain()
        freq = Frequency(type="monthly", on_dates=[15])
        result_freq, warnings = domain.normalize_empty_specialization_fields(freq)
        assert result_freq is freq
        assert warnings == []

    def test_non_applicable_type_unchanged(self) -> None:
        """Daily -> same frequency, no warning (not applicable)."""
        domain = _domain()
        freq = Frequency(type="daily")
        result_freq, warnings = domain.normalize_empty_specialization_fields(freq)
        assert result_freq is freq
        assert warnings == []

    def test_preserves_interval(self) -> None:
        """Custom interval is preserved when normalizing."""
        domain = _domain()
        freq = Frequency(type="monthly", interval=3, on_dates=[])
        result_freq, _warnings = domain.normalize_empty_specialization_fields(freq)
        assert result_freq.on_dates is None
        assert result_freq.interval == 3

    def test_empty_on_days(self) -> None:
        """weekly with onDays=[] -> on_days=None + warning."""
        domain = _domain()
        freq = Frequency(type="weekly", on_days=[])
        result_freq, warnings = domain.normalize_empty_specialization_fields(freq)
        assert result_freq.on_days is None
        assert len(warnings) == 1
        assert REPETITION_EMPTY_ON_DAYS in warnings[0]

    def test_empty_on(self) -> None:
        """monthly with on={} -> on=None + warning."""
        domain = _domain()
        freq = Frequency(type="monthly", on={})
        result_freq, warnings = domain.normalize_empty_specialization_fields(freq)
        assert result_freq.on is None
        assert len(warnings) == 1
        assert REPETITION_EMPTY_ON in warnings[0]

    def test_non_empty_on_days_unchanged(self) -> None:
        """onDays=["MO"] -> same frequency, no warning."""
        domain = _domain()
        freq = Frequency(type="weekly", on_days=["MO"])
        result_freq, warnings = domain.normalize_empty_specialization_fields(freq)
        assert result_freq is freq
        assert warnings == []


# ---------------------------------------------------------------------------
# merge_frequency
# ---------------------------------------------------------------------------


class TestMergeFrequency:
    """D-08/D-11: Merge edit spec with existing frequency, incl. monthly auto-clear."""

    def test_agent_set_on_clears_existing_on_dates(self) -> None:
        """Agent sets on, existing has on_dates -> auto-clear on_dates."""
        domain = _domain()
        existing = Frequency(type="monthly", on_dates=[1, 15])
        edit_spec = FrequencyEditSpec(on={"last": "friday"})
        result, warnings = domain.merge_frequency(edit_spec, existing)
        assert result.on == OrdinalWeekday(last="friday")
        assert result.on_dates is None
        assert len(warnings) == 1
        assert REPETITION_AUTO_CLEAR_ON_DATES in warnings[0]

    def test_agent_set_on_dates_clears_existing_on(self) -> None:
        """Agent sets on_dates, existing has on -> auto-clear on."""
        domain = _domain()
        existing = Frequency(type="monthly", on={"second": "tuesday"})
        edit_spec = FrequencyEditSpec(on_dates=[1, 15])
        result, warnings = domain.merge_frequency(edit_spec, existing)
        assert result.on is None
        assert result.on_dates == [1, 15]
        assert len(warnings) == 1
        assert REPETITION_AUTO_CLEAR_ON in warnings[0]

    def test_agent_set_both_on_takes_precedence(self) -> None:
        """Agent sets both on and on_dates -> on takes precedence, clear on_dates."""
        domain = _domain()
        existing = Frequency(type="monthly")
        edit_spec = FrequencyEditSpec(on={"first": "monday"}, on_dates=[1])
        result, warnings = domain.merge_frequency(edit_spec, existing)
        assert result.on == OrdinalWeekday(first="monday")
        assert result.on_dates is None
        assert len(warnings) == 1
        assert REPETITION_AUTO_CLEAR_ON_DATES in warnings[0]

    def test_no_conflict_no_warning(self) -> None:
        """Agent sets on, existing has no on_dates -> no auto-clear needed."""
        domain = _domain()
        existing = Frequency(type="monthly")
        edit_spec = FrequencyEditSpec(on={"first": "monday"})
        result, warnings = domain.merge_frequency(edit_spec, existing)
        assert result.on == OrdinalWeekday(first="monday")
        assert result.on_dates is None
        assert warnings == []

    def test_preserves_unset_fields_from_existing(self) -> None:
        """UNSET fields preserved from existing (D-11)."""
        domain = _domain()
        existing = Frequency(type="weekly", interval=2, on_days=["MO", "FR"])
        edit_spec = FrequencyEditSpec(interval=3)
        result, warnings = domain.merge_frequency(edit_spec, existing)
        assert result.type == "weekly"
        assert result.interval == 3
        assert result.on_days == ["MO", "FR"]
        assert warnings == []

    def test_none_clears_field(self) -> None:
        """Explicit None clears a specialization field."""
        domain = _domain()
        existing = Frequency(type="weekly", interval=2, on_days=["MO", "FR"])
        edit_spec = FrequencyEditSpec(on_days=None)
        result, warnings = domain.merge_frequency(edit_spec, existing)
        assert result.type == "weekly"
        assert result.interval == 2
        assert result.on_days is None
        assert warnings == []


# ---------------------------------------------------------------------------
# _all_fields_match: repetition rule no-op detection
# ---------------------------------------------------------------------------


class TestRepetitionRuleNoOp:
    """No-op detection with repetition rule field comparison."""

    def test_identical_repetition_is_noop(self) -> None:
        """Same repetition rule payload as existing -> returns True."""
        task = _make_task(
            repetitionRule={
                "frequency": {"type": "daily", "interval": 1},
                "schedule": "regularly",
                "basedOn": "due_date",
            }
        )
        payload = EditTaskRepoPayload.model_validate(
            {
                "id": "task-001",
                "repetition_rule": RepetitionRuleRepoPayload(
                    frequency=Frequency(type="daily"),
                    schedule=Schedule.REGULARLY,
                    based_on=BasedOn.DUE_DATE,
                ),
            }
        )
        result = _domain()._all_fields_match(payload, task, [])
        assert result is True

    def test_different_repetition_not_noop(self) -> None:
        """Different repetition rule -> returns False."""
        task = _make_task(
            repetitionRule={
                "frequency": {"type": "daily", "interval": 1},
                "schedule": "regularly",
                "basedOn": "due_date",
            }
        )
        payload = EditTaskRepoPayload.model_validate(
            {
                "id": "task-001",
                "repetition_rule": RepetitionRuleRepoPayload(
                    frequency=Frequency(type="daily", interval=3),
                    schedule=Schedule.REGULARLY,
                    based_on=BasedOn.DUE_DATE,
                ),
            }
        )
        result = _domain()._all_fields_match(payload, task, [])
        assert result is False

    def test_clear_when_task_has_rule_not_noop(self) -> None:
        """Clear (repetition_rule=None) when task has a rule -> not a no-op."""
        task = _make_task(
            repetitionRule={
                "frequency": {"type": "daily"},
                "schedule": "regularly",
                "basedOn": "due_date",
            }
        )
        payload = EditTaskRepoPayload.model_validate(
            {
                "id": "task-001",
                "repetition_rule": None,
            }
        )
        result = _domain()._all_fields_match(payload, task, [])
        assert result is False


# ---------------------------------------------------------------------------
# InMemoryBridge: direct repetitionRule verification
# ---------------------------------------------------------------------------


class TestInMemoryBridgeRepetitionRule:
    """Direct verification that InMemoryBridge stores/clears repetition rules."""

    async def test_add_task_with_repetition_rule(self) -> None:
        """add_task with repetitionRule dict -> stored on the task."""
        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[]))
        rule = {
            "ruleString": "FREQ=DAILY",
            "scheduleType": "Regularly",
            "anchorDateKey": "DueDate",
            "catchUpAutomatically": False,
        }
        result = await bridge.send_command(
            "add_task", {"name": "Repeating", "repetitionRule": rule}
        )
        # Read back
        data = await bridge.send_command("get_all")
        task = next(t for t in data["tasks"] if t["id"] == result["id"])
        assert task["repetitionRule"] == rule

    async def test_add_task_without_repetition_rule(self) -> None:
        """add_task without repetitionRule -> task has None."""
        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[]))
        result = await bridge.send_command("add_task", {"name": "Plain"})
        data = await bridge.send_command("get_all")
        task = next(t for t in data["tasks"] if t["id"] == result["id"])
        assert task["repetitionRule"] is None

    async def test_edit_task_set_repetition_rule(self) -> None:
        """edit_task with repetitionRule dict -> sets it on the task."""
        bridge = InMemoryBridge(data=make_snapshot_dict(tasks=[make_task_dict(id="t1")]))
        rule = {
            "ruleString": "FREQ=WEEKLY",
            "scheduleType": "Regularly",
            "anchorDateKey": "DueDate",
            "catchUpAutomatically": False,
        }
        await bridge.send_command("edit_task", {"id": "t1", "repetitionRule": rule})
        data = await bridge.send_command("get_all")
        task = next(t for t in data["tasks"] if t["id"] == "t1")
        assert task["repetitionRule"] == rule

    async def test_edit_task_clear_repetition_rule(self) -> None:
        """edit_task with repetitionRule=None -> clears the rule."""
        bridge = InMemoryBridge(
            data=make_snapshot_dict(
                tasks=[
                    make_task_dict(
                        id="t1",
                        repetitionRule={"ruleString": "FREQ=DAILY"},
                    )
                ]
            )
        )
        await bridge.send_command("edit_task", {"id": "t1", "repetitionRule": None})
        data = await bridge.send_command("get_all")
        task = next(t for t in data["tasks"] if t["id"] == "t1")
        assert task["repetitionRule"] is None

    async def test_edit_task_no_repetition_key_preserves(self) -> None:
        """edit_task without repetitionRule key -> no change."""
        rule = {"ruleString": "FREQ=DAILY"}
        bridge = InMemoryBridge(
            data=make_snapshot_dict(tasks=[make_task_dict(id="t1", repetitionRule=rule)])
        )
        await bridge.send_command("edit_task", {"id": "t1", "name": "Renamed"})
        data = await bridge.send_command("get_all")
        task = next(t for t in data["tasks"] if t["id"] == "t1")
        assert task["repetitionRule"] == rule


# ---------------------------------------------------------------------------
# check_filter_resolution
# ---------------------------------------------------------------------------


@dataclass
class _StubEntity:
    """Minimal entity with id and name for filter resolution tests."""

    id: str
    name: str


class TestCheckFilterResolution:
    """Warning generation for filter resolution outcomes."""

    def test_single_match_no_warning(self) -> None:
        """Single match -> no warning."""
        entities = [_StubEntity("p1", "Work"), _StubEntity("p2", "Home")]
        warnings = _domain().check_filter_resolution("Work", ["p1"], entities, "project")
        assert warnings == []

    def test_multi_match_warning(self) -> None:
        """Multiple matches -> FILTER_MULTI_MATCH with IDs and names."""
        entities = [_StubEntity("p1", "Work A"), _StubEntity("p2", "Work B")]
        warnings = _domain().check_filter_resolution("Work", ["p1", "p2"], entities, "project")
        assert len(warnings) == 1
        assert "p1 (Work A)" in warnings[0]
        assert "p2 (Work B)" in warnings[0]
        assert "matched 2 projects" in warnings[0]

    def test_no_match_with_suggestion(self) -> None:
        """No match with a close name -> FILTER_DID_YOU_MEAN.

        DYM is reworded to stand alone without the retired FILTER_NO_MATCH
        prefix. Text reads: ``Did you mean: 'X'? (no <entity> matched 'Y')``
        with each suggestion wrapped in single quotes for crisp boundaries.
        """
        entities = [_StubEntity("p1", "Personal"), _StubEntity("p2", "Work")]
        warnings = _domain().check_filter_resolution("Personl", [], entities, "project")
        assert len(warnings) == 1
        assert warnings[0] == "Did you mean: 'Personal'? (no project matched 'Personl')"

    def test_no_match_no_suggestion(self) -> None:
        """No match, no close names -> returns [].

        FILTER_NO_MATCH is retired; EMPTY_RESULT_WARNING emitted by
        _ListTasksPipeline.execute covers the silent-empty case, so
        ``check_filter_resolution`` returns no warning when the no-match
        branch has no fuzzy candidates.
        """
        entities = [_StubEntity("p1", "Work"), _StubEntity("p2", "Home")]
        warnings = _domain().check_filter_resolution("zzzzz", [], entities, "project")
        assert warnings == []


# ---------------------------------------------------------------------------
# Cross-filter warning checks (WARN-01 FILTERED_SUBTREE, WARN-03
# PARENT_PROJECT_COMBINED) -- pure DomainLogic methods introspecting
# ListTasksQuery; no resolver or repo dependency.
# ---------------------------------------------------------------------------


class TestCheckFilteredSubtree:
    """WARN-01: scope filter (project/parent) combined with any other dimensional filter.

    The trigger is ``(is_set(project) or is_set(parent)) AND (any other dim is_set)``.
    ``availability`` is EXCLUDED from the "other filter" predicate because it has a
    non-empty default (REMAINING) -- including it would fire the warning on every
    scope-filtered query, destroying signal (D-13).
    """

    def test_no_scope_no_other_no_warning(self) -> None:
        """Empty query -> no warning."""
        assert _domain().check_filtered_subtree(ListTasksQuery()) == []

    def test_project_only_no_other_no_warning(self) -> None:
        """project set, no other filter -> no warning."""
        assert _domain().check_filtered_subtree(ListTasksQuery(project="Work")) == []

    def test_parent_only_no_other_no_warning(self) -> None:
        """parent set, no other filter -> no warning."""
        assert _domain().check_filtered_subtree(ListTasksQuery(parent="Review")) == []

    def test_project_with_flagged_fires(self) -> None:
        """project + flagged -> FILTERED_SUBTREE_WARNING."""
        query = ListTasksQuery(project="Work", flagged=True)
        assert _domain().check_filtered_subtree(query) == [FILTERED_SUBTREE_WARNING]

    def test_parent_with_flagged_fires(self) -> None:
        """parent + flagged -> FILTERED_SUBTREE_WARNING."""
        query = ListTasksQuery(parent="Review", flagged=True)
        assert _domain().check_filtered_subtree(query) == [FILTERED_SUBTREE_WARNING]

    def test_project_with_tags_fires(self) -> None:
        """project + tags -> FILTERED_SUBTREE_WARNING."""
        query = ListTasksQuery(project="Work", tags=["Urgent"])
        assert _domain().check_filtered_subtree(query) == [FILTERED_SUBTREE_WARNING]

    def test_project_with_search_fires(self) -> None:
        """project + search -> FILTERED_SUBTREE_WARNING."""
        query = ListTasksQuery(project="Work", search="draft")
        assert _domain().check_filtered_subtree(query) == [FILTERED_SUBTREE_WARNING]

    def test_project_with_due_filter_fires(self) -> None:
        """project + due filter -> FILTERED_SUBTREE_WARNING (date dimension counts as 'other')."""
        query = ListTasksQuery(project="Work", due="overdue")
        assert _domain().check_filtered_subtree(query) == [FILTERED_SUBTREE_WARNING]

    def test_project_with_completed_does_not_fire(self) -> None:
        """project + completed -> NO warning. completed is an INCLUSION filter,
        not pruning (UAT-57 Case 1). It adds completed tasks on top of the
        default 'remaining' bucket; it never excludes tasks already in it.
        Live-verified: completed={"before": "2020-01-01"} returns the baseline
        unchanged rather than restricting it to zero."""
        query = ListTasksQuery(project="Work", completed="today")
        assert _domain().check_filtered_subtree(query) == []

    def test_project_with_completed_all_does_not_fire(self) -> None:
        """project + completed='all' -> NO warning. 'all' is the most inclusive
        value; it adds every completed task regardless of date. Baseline
        remaining tasks are unchanged."""
        query = ListTasksQuery(project="Work", completed="all")
        assert _domain().check_filtered_subtree(query) == []

    def test_project_with_completed_zero_match_date_does_not_fire(self) -> None:
        """project + completed={"before": "<far past>"} -> NO warning.

        Regression lock for UAT-57 Case 1: the decisive live probe that proved
        completed is additive, not pruning. Zero completed tasks match the
        date range, so the filter adds zero tasks to the baseline. If the
        predicate treated completed as pruning, the baseline remaining tasks
        would be wrongly implicated; it isn't, so no warning.
        """
        query = ListTasksQuery(project="Work", completed={"before": "2020-01-01"})
        assert _domain().check_filtered_subtree(query) == []

    def test_project_with_dropped_does_not_fire(self) -> None:
        """project + dropped -> NO warning. Same inclusion-filter semantics
        as completed (UAT-57 Case 1)."""
        query = ListTasksQuery(project="Work", dropped="today")
        assert _domain().check_filtered_subtree(query) == []

    # -- Availability coverage matrix (Phase 57-05 / G4 fix) -----------------
    # The old predicate ``is_set(getattr(query, f))`` treated every Patch field
    # uniformly and omitted ``availability`` entirely (D-13 "don't spam on the
    # default" implemented by omission). The new value-aware ``is_non_default``
    # predicate lets us classify ``availability`` correctly: the default value
    # does NOT fire (preserves D-13), any non-default value DOES fire.

    def test_project_with_default_availability_implicit_no_fire(self) -> None:
        """project + implicit default availability -> NO warning (D-13 preserved).

        Implicit default means the caller never set ``availability`` -- the
        field holds its declared default ``[REMAINING]``. Warning must not fire.
        """
        query = ListTasksQuery(project="Work")
        assert _domain().check_filtered_subtree(query) == []

    def test_project_with_default_availability_explicit_no_fire(self) -> None:
        """project + explicit default availability -> NO warning (D-13 preserved).

        Caller explicitly passes ``[REMAINING]`` (same value as the declared
        default). Value-equality with the default means "not pruning".
        """
        query = ListTasksQuery(project="Work", availability=[AvailabilityFilter.REMAINING])
        assert _domain().check_filtered_subtree(query) == []

    def test_project_with_narrower_availability_fires(self) -> None:
        """project + non-default availability=[AVAILABLE] -> FIRES (G4 fix).

        ``[AVAILABLE]`` narrows the lifecycle bucket below the default
        ``[REMAINING]`` -- genuinely pruning. This is the case UAT-57 Test 9
        probe (c) was looking for.
        """
        query = ListTasksQuery(project="Work", availability=[AvailabilityFilter.AVAILABLE])
        assert _domain().check_filtered_subtree(query) == [FILTERED_SUBTREE_WARNING]

    def test_project_with_blocked_availability_fires(self) -> None:
        """project + non-default availability=[BLOCKED] -> FIRES (G4 fix)."""
        query = ListTasksQuery(project="Work", availability=[AvailabilityFilter.BLOCKED])
        assert _domain().check_filtered_subtree(query) == [FILTERED_SUBTREE_WARNING]

    def test_project_with_empty_availability_fires(self) -> None:
        """project + availability=[] -> FIRES (empty list != default, genuinely prunes)."""
        query = ListTasksQuery(project="Work", availability=[])
        assert _domain().check_filtered_subtree(query) == [FILTERED_SUBTREE_WARNING]

    def test_project_with_multi_value_availability_fires(self) -> None:
        """project + availability=[REMAINING, AVAILABLE] -> FIRES.

        Any multi-element list differing from the single-element default
        ``[REMAINING]`` is non-default. Pairing REMAINING with AVAILABLE
        (a redundant combo flagged elsewhere by the expansion layer) is
        still non-default from a value-equality standpoint -- predicate
        correctly identifies "pruning".
        """
        query = ListTasksQuery(
            project="Work",
            availability=[AvailabilityFilter.REMAINING, AvailabilityFilter.AVAILABLE],
        )
        assert _domain().check_filtered_subtree(query) == [FILTERED_SUBTREE_WARNING]

    def test_project_with_narrower_availability_and_flagged_fires_once(self) -> None:
        """project + non-default availability + flagged -> FIRES EXACTLY ONCE."""
        query = ListTasksQuery(
            project="Work",
            availability=[AvailabilityFilter.AVAILABLE],
            flagged=True,
        )
        result = _domain().check_filtered_subtree(query)
        assert result == [FILTERED_SUBTREE_WARNING]

    def test_narrower_availability_alone_no_fire(self) -> None:
        """Non-default availability with no scope -> NO warning (scope predicate gates)."""
        query = ListTasksQuery(availability=[AvailabilityFilter.AVAILABLE])
        assert _domain().check_filtered_subtree(query) == []

    def test_parent_with_narrower_availability_fires(self) -> None:
        """parent + non-default availability -> FIRES (parent scope triggers same rule)."""
        query = ListTasksQuery(parent="Review", availability=[AvailabilityFilter.AVAILABLE])
        assert _domain().check_filtered_subtree(query) == [FILTERED_SUBTREE_WARNING]

    def test_both_project_and_parent_with_flagged_fires_once(self) -> None:
        """Both project AND parent set + flagged -> fires EXACTLY ONCE.

        The scope-set predicate is OR -- satisfied by either -- so the domain method
        still returns a single-element list. (D-13: the warning is presence-based on
        the scope-set, not counted per-set.)
        """
        query = ListTasksQuery(project="Work", parent="Review", flagged=True)
        result = _domain().check_filtered_subtree(query)
        assert result == [FILTERED_SUBTREE_WARNING]


class TestIsNonDefault:
    """``is_non_default(model, field_name)`` -- value-aware predicate dispatching
    on field type (Patch vs. regular field with a concrete default).

    Phase 57-05 / G4 fix: the predicate lets ``_SUBTREE_PRUNING_FIELDS``
    classify non-Patch filter fields (e.g. ``availability``) so the default
    value does not fire FILTERED_SUBTREE_WARNING but any non-default value
    does.
    """

    # -- Patch fields (equivalent to is_set) -------------------------------

    def test_is_non_default_patch_field_unset(self) -> None:
        """Patch[T] field with UNSET default -> not set -> False."""
        q = ListTasksQuery()
        assert is_non_default(q, "flagged") is False

    def test_is_non_default_patch_field_set_to_true(self) -> None:
        """Patch[bool] field set to True (distinct from UNSET) -> True."""
        q = ListTasksQuery(flagged=True)
        assert is_non_default(q, "flagged") is True

    def test_is_non_default_patch_field_set_to_false(self) -> None:
        """Patch[bool] field set to False -> True (False != UNSET)."""
        q = ListTasksQuery(flagged=False)
        assert is_non_default(q, "flagged") is True

    # -- Regular fields with a concrete default ----------------------------

    def test_is_non_default_regular_field_matches_default(self) -> None:
        """Regular field left at implicit declared default -> False."""
        q = ListTasksQuery()
        # availability defaults to [AvailabilityFilter.REMAINING]
        assert is_non_default(q, "availability") is False

    def test_is_non_default_regular_field_explicit_default(self) -> None:
        """Regular field explicitly set to the declared default value -> False."""
        q = ListTasksQuery(availability=[AvailabilityFilter.REMAINING])
        assert is_non_default(q, "availability") is False

    def test_is_non_default_regular_field_different_value(self) -> None:
        """Regular field set to a value != default -> True."""
        q = ListTasksQuery(availability=[AvailabilityFilter.AVAILABLE])
        assert is_non_default(q, "availability") is True

    def test_is_non_default_regular_field_empty_list(self) -> None:
        """Regular field set to empty list != declared default list -> True."""
        q = ListTasksQuery(availability=[])
        assert is_non_default(q, "availability") is True

    def test_is_non_default_regular_field_multi_value(self) -> None:
        """Regular field set to a multi-element list != default -> True (list equality)."""
        q = ListTasksQuery(
            availability=[AvailabilityFilter.REMAINING, AvailabilityFilter.AVAILABLE]
        )
        assert is_non_default(q, "availability") is True


class TestSubtreePruningFieldsDrift:
    """Every filter field on ListTasksQuery contributing to FILTERED_SUBTREE_WARNING
    must be classified as either subtree-pruning (fires WARN-01 with scope) or
    non-pruning (scope field / inclusion filter).

    If this test fails, someone added a new Patch[T] filter to ListTasksQuery
    without deciding whether it should contribute to FILTERED_SUBTREE_WARNING.
    Add the new field to exactly one of the two sets in service/domain.py.

    Phase 57-05 / G4 broadening: the classification can now include non-Patch
    fields with a concrete default (e.g. ``availability``). The Patch-only
    assumption of the original drift test is superseded -- membership must
    still couple to real fields on ``ListTasksQuery``, checked via
    ``ListTasksQuery.model_fields`` rather than ``_PATCH_FIELDS``.
    """

    def test_every_patch_field_is_classified(self) -> None:
        classified = set(_SUBTREE_PRUNING_FIELDS) | _NON_SUBTREE_PRUNING_FIELDS
        unclassified = set(_PATCH_FIELDS) - classified
        assert not unclassified, (
            f"Patch filter(s) {sorted(unclassified)} on ListTasksQuery are not "
            f"classified. Add each to exactly one of:\n"
            f"  - _SUBTREE_PRUNING_FIELDS (task-attribute filters that could "
            f"exclude descendants from a scope filter)\n"
            f"  - _NON_SUBTREE_PRUNING_FIELDS (scope filters themselves -- "
            f"currently project, parent)"
        )

    def test_no_overlap_between_classifications(self) -> None:
        """A field can't be both subtree-pruning AND a scope field."""
        overlap = set(_SUBTREE_PRUNING_FIELDS) & _NON_SUBTREE_PRUNING_FIELDS
        assert not overlap, f"Fields classified as both pruning and scope: {overlap}"

    def test_no_unknown_fields_in_classifications(self) -> None:
        """Both classifications must reference real fields on ListTasksQuery.

        Phase 57-05 broadening: reference set is ``ListTasksQuery.model_fields``
        (Patch OR regular with default), not ``_PATCH_FIELDS``. A non-Patch
        classified field like ``availability`` is legitimate when paired with
        the value-aware predicate ``is_non_default``.
        """
        real_fields = set(ListTasksQuery.model_fields.keys())
        unknown_pruning = set(_SUBTREE_PRUNING_FIELDS) - real_fields
        unknown_non_pruning = _NON_SUBTREE_PRUNING_FIELDS - real_fields
        assert not unknown_pruning, (
            f"_SUBTREE_PRUNING_FIELDS references non-existent field(s) on ListTasksQuery: "
            f"{sorted(unknown_pruning)}. Typo or stale classification?"
        )
        assert not unknown_non_pruning, (
            f"_NON_SUBTREE_PRUNING_FIELDS references non-existent field(s) on ListTasksQuery: "
            f"{sorted(unknown_non_pruning)}. Typo or stale classification?"
        )

    def test_every_classified_field_exists_on_query(self) -> None:
        """Every name in the two classifications must be a real field on ListTasksQuery.

        Catches typos (e.g. ``"avilability"``) and stale classifications for
        BOTH Patch and non-Patch classified fields (Phase 57-05 / G4). This
        complements ``test_no_unknown_fields_in_classifications`` with a
        single explicit membership check against ``model_fields``.
        """
        classified = set(_SUBTREE_PRUNING_FIELDS) | _NON_SUBTREE_PRUNING_FIELDS
        real_fields = set(ListTasksQuery.model_fields.keys())
        unknown = classified - real_fields
        assert not unknown, (
            f"Classification references non-existent field(s) on ListTasksQuery: "
            f"{sorted(unknown)}. Typo or stale classification after a rename?"
        )


# ---------------------------------------------------------------------------
# Date filter resolution (moved from pipeline)
# ---------------------------------------------------------------------------

# Fixed "now" for all date tests: Tuesday 2026-04-07 14:00:00 UTC
_NOW = datetime(2026, 4, 7, 14, 0, 0, tzinfo=UTC)


def _date_query(**overrides: object) -> SimpleNamespace:
    """Build a stub query with all 7 date fields defaulting to UNSET."""
    defaults = {
        name: UNSET
        for name in ("due", "defer", "planned", "completed", "dropped", "added", "modified")
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestResolveDateFilters:
    """DomainLogic.resolve_date_filters -- lifecycle mapping, date bounds, fallbacks."""

    def test_empty_fields(self) -> None:
        """All fields UNSET -> empty result."""
        result = _domain().resolve_date_filters(
            _date_query(), _NOW, week_start=0, due_soon_setting=None
        )
        assert result.bounds == {}
        assert result.lifecycle_additions == []
        assert result.warnings == []

    def test_single_date_field(self) -> None:
        """Single 'due: today' -> bounds populated."""
        result = _domain().resolve_date_filters(
            _date_query(due=DueDateShortcut.TODAY), _NOW, week_start=0, due_soon_setting=None
        )
        assert "due" in result.bounds
        assert result.bounds["due"].after == datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)
        assert result.bounds["due"].before == datetime(2026, 4, 8, 0, 0, 0, tzinfo=UTC)
        assert result.lifecycle_additions == []
        assert result.warnings == []

    def test_lifecycle_field_adds_availability(self) -> None:
        """'completed: today' -> COMPLETED in lifecycle_additions AND date bounds."""
        result = _domain().resolve_date_filters(
            _date_query(completed=LifecycleDateShortcut.TODAY),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert Availability.COMPLETED in result.lifecycle_additions
        assert "completed" in result.bounds

    def test_all_on_lifecycle_field(self) -> None:
        """'completed: all' -> lifecycle addition but NO date bounds."""
        result = _domain().resolve_date_filters(
            _date_query(completed=LifecycleDateShortcut.ALL),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert Availability.COMPLETED in result.lifecycle_additions
        assert "completed" not in result.bounds

    def test_multiple_fields(self) -> None:
        """Multiple fields -> all resolved."""
        result = _domain().resolve_date_filters(
            _date_query(due=DueDateShortcut.TODAY, completed=LifecycleDateShortcut.TODAY),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert "due" in result.bounds
        assert "completed" in result.bounds
        assert Availability.COMPLETED in result.lifecycle_additions

    def test_soon_without_due_soon_setting(self) -> None:
        """'soon' without due_soon_setting -> domain falls back to TWO_DAYS bounds + warning."""
        result = _domain().resolve_date_filters(
            _date_query(due=DueDateShortcut.SOON), _NOW, week_start=0, due_soon_setting=None
        )
        assert result.bounds["due"].after == datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)
        assert result.bounds["due"].before == datetime(2026, 4, 9, 0, 0, 0, tzinfo=UTC)
        assert len(result.warnings) == 1
        assert "Due-soon threshold was not detected" in result.warnings[0]

    def test_soon_with_due_soon_setting(self) -> None:
        """'soon' with due_soon_setting -> delegates to resolver, correct bounds."""
        result = _domain().resolve_date_filters(
            _date_query(due=DueDateShortcut.SOON),
            _NOW,
            week_start=0,
            due_soon_setting=DueSoonSetting.TWO_DAYS,
        )
        assert result.bounds["due"].after is None
        assert result.bounds["due"].before == datetime(2026, 4, 9, 0, 0, 0, tzinfo=UTC)
        assert result.warnings == []

    def test_date_filter_object(self) -> None:
        """Concrete filter object (e.g. ThisPeriodFilter) is resolved correctly."""
        result = _domain().resolve_date_filters(
            _date_query(due=ThisPeriodFilter(this="d")), _NOW, week_start=0, due_soon_setting=None
        )
        assert result.bounds["due"].after == datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)
        assert result.bounds["due"].before == datetime(2026, 4, 8, 0, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Defer hint detection (D-18, D-19)
# ---------------------------------------------------------------------------


class TestDeferHintDetection:
    """DomainLogic.resolve_date_filters -- defer hint detection for after/before 'now'."""

    def test_defer_after_now_produces_hint(self) -> None:
        """defer: {after: 'now'} -> warning with 'future defer date' and 'blocked'."""
        from omnifocus_operator.agent_messages.warnings import (  # noqa: PLC0415
            DEFER_AFTER_NOW_HINT,
        )

        result = _domain().resolve_date_filters(
            _date_query(defer=AbsoluteRangeFilter(after="now")),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert DEFER_AFTER_NOW_HINT in result.warnings
        assert "future defer date" in DEFER_AFTER_NOW_HINT
        assert "blocked" in DEFER_AFTER_NOW_HINT

    def test_defer_before_now_produces_hint(self) -> None:
        """defer: {before: 'now'} -> warning with 'defer date has passed' and 'available'."""
        from omnifocus_operator.agent_messages.warnings import (  # noqa: PLC0415
            DEFER_BEFORE_NOW_HINT,
        )

        result = _domain().resolve_date_filters(
            _date_query(defer=AbsoluteRangeFilter(before="now")),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert DEFER_BEFORE_NOW_HINT in result.warnings
        assert "defer date has passed" in DEFER_BEFORE_NOW_HINT
        assert "available" in DEFER_BEFORE_NOW_HINT

    def test_defer_after_now_with_before_still_hints(self) -> None:
        """defer: {after: 'now', before: '2026-05-01'} -> after-now hint fires."""
        from omnifocus_operator.agent_messages.warnings import (  # noqa: PLC0415
            DEFER_AFTER_NOW_HINT,
        )

        result = _domain().resolve_date_filters(
            _date_query(defer=AbsoluteRangeFilter(after="now", before="2026-05-01")),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert DEFER_AFTER_NOW_HINT in result.warnings

    def test_defer_past_absolute_date_produces_before_hint(self) -> None:
        """defer: {after: '2026-01-01'} -> before-now hint (range starts in the past)."""
        from omnifocus_operator.agent_messages.warnings import (  # noqa: PLC0415
            DEFER_BEFORE_NOW_HINT,
        )

        result = _domain().resolve_date_filters(
            _date_query(defer=AbsoluteRangeFilter(after="2026-01-01")),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert DEFER_BEFORE_NOW_HINT in result.warnings

    def test_defer_today_shortcut_produces_before_hint(self) -> None:
        """defer: 'today' -> before-now hint (today's range starts at midnight, before now)."""
        from omnifocus_operator.agent_messages.warnings import (  # noqa: PLC0415
            DEFER_BEFORE_NOW_HINT,
        )

        result = _domain().resolve_date_filters(
            _date_query(defer=DateShortcut.TODAY),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert DEFER_BEFORE_NOW_HINT in result.warnings

    def test_defer_last_period_produces_before_hint(self) -> None:
        """defer: {last: '3d'} -> before-now hint (entirely in the past)."""
        from omnifocus_operator.agent_messages.warnings import (  # noqa: PLC0415
            DEFER_BEFORE_NOW_HINT,
        )

        result = _domain().resolve_date_filters(
            _date_query(defer=LastPeriodFilter(last="3d")),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert DEFER_BEFORE_NOW_HINT in result.warnings

    def test_defer_this_week_produces_before_hint(self) -> None:
        """defer: {this: 'w'} -> before-now hint (week started before now)."""
        from omnifocus_operator.agent_messages.warnings import (  # noqa: PLC0415
            DEFER_BEFORE_NOW_HINT,
        )

        result = _domain().resolve_date_filters(
            _date_query(defer=ThisPeriodFilter(this="w")),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert DEFER_BEFORE_NOW_HINT in result.warnings

    def test_defer_next_period_produces_after_hint(self) -> None:
        """defer: {next: '3d'} -> after-now hint (entirely in the future)."""
        from omnifocus_operator.agent_messages.warnings import (  # noqa: PLC0415
            DEFER_AFTER_NOW_HINT,
        )

        result = _domain().resolve_date_filters(
            _date_query(defer=NextPeriodFilter(next="3d")),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert DEFER_AFTER_NOW_HINT in result.warnings

    def test_defer_future_absolute_date_produces_after_hint(self) -> None:
        """defer: {after: '2026-06-01'} -> after-now hint (starts after now)."""
        from omnifocus_operator.agent_messages.warnings import (  # noqa: PLC0415
            DEFER_AFTER_NOW_HINT,
        )

        result = _domain().resolve_date_filters(
            _date_query(defer=AbsoluteRangeFilter(after="2026-06-01")),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert DEFER_AFTER_NOW_HINT in result.warnings

    def test_non_defer_field_no_hint(self) -> None:
        """due: {after: 'now'} -> no defer hint (field must be 'defer')."""
        result = _domain().resolve_date_filters(
            _date_query(due=AbsoluteRangeFilter(after="now")),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        for w in result.warnings:
            assert "Tip:" not in w

    def test_defer_hints_non_blocking(self) -> None:
        """Query still resolves with bounds present alongside hint."""
        result = _domain().resolve_date_filters(
            _date_query(defer=AbsoluteRangeFilter(after="now")),
            _NOW,
            week_start=0,
            due_soon_setting=None,
        )
        assert "defer" in result.bounds
        assert result.bounds["defer"].after == _NOW


# ---------------------------------------------------------------------------
# Availability expansion (moved from _expand_availability free function)
# ---------------------------------------------------------------------------


class TestExpandTaskAvailability:
    """DomainLogic.expand_availability -- REMAINING expansion + lifecycle merge."""

    def test_remaining_expands_to_available_and_blocked(self) -> None:
        """[REMAINING] -> {AVAILABLE, BLOCKED}, no warnings."""
        expanded, warnings = _domain().expand_availability([AvailabilityFilter.REMAINING], [])
        assert set(expanded) == {Availability.AVAILABLE, Availability.BLOCKED}
        assert warnings == []

    def test_available_remaining_warns_redundant(self) -> None:
        """[AVAILABLE, REMAINING] -> {AVAILABLE, BLOCKED}, 1 warning."""
        from omnifocus_operator.agent_messages.warnings import (  # noqa: PLC0415
            AVAILABILITY_REMAINING_INCLUDES_AVAILABLE,
        )

        expanded, warnings = _domain().expand_availability(
            [AvailabilityFilter.AVAILABLE, AvailabilityFilter.REMAINING], []
        )
        assert set(expanded) == {Availability.AVAILABLE, Availability.BLOCKED}
        assert len(warnings) == 1
        assert warnings[0] == AVAILABILITY_REMAINING_INCLUDES_AVAILABLE

    def test_blocked_remaining_warns_redundant(self) -> None:
        """[BLOCKED, REMAINING] -> {AVAILABLE, BLOCKED}, 1 warning."""
        from omnifocus_operator.agent_messages.warnings import (  # noqa: PLC0415
            AVAILABILITY_REMAINING_INCLUDES_BLOCKED,
        )

        expanded, warnings = _domain().expand_availability(
            [AvailabilityFilter.BLOCKED, AvailabilityFilter.REMAINING], []
        )
        assert set(expanded) == {Availability.AVAILABLE, Availability.BLOCKED}
        assert len(warnings) == 1
        assert warnings[0] == AVAILABILITY_REMAINING_INCLUDES_BLOCKED

    def test_empty_filters_expands_to_empty(self) -> None:
        """[] -> empty set, no warnings."""
        expanded, warnings = _domain().expand_availability([], [])
        assert expanded == []
        assert warnings == []

    def test_single_available_no_warning(self) -> None:
        """[AVAILABLE] -> {AVAILABLE}, no warnings."""
        expanded, warnings = _domain().expand_availability([AvailabilityFilter.AVAILABLE], [])
        assert set(expanded) == {Availability.AVAILABLE}
        assert warnings == []

    def test_empty_plus_lifecycle_completed(self) -> None:
        """[] + lifecycle_additions=[COMPLETED] -> {COMPLETED} only."""
        expanded, warnings = _domain().expand_availability([], [Availability.COMPLETED])
        assert set(expanded) == {Availability.COMPLETED}
        assert warnings == []

    def test_remaining_plus_lifecycle_completed(self) -> None:
        """[REMAINING] + lifecycle_additions=[COMPLETED] -> {AVAILABLE, BLOCKED, COMPLETED}."""
        expanded, warnings = _domain().expand_availability(
            [AvailabilityFilter.REMAINING], [Availability.COMPLETED]
        )
        assert set(expanded) == {
            Availability.AVAILABLE,
            Availability.BLOCKED,
            Availability.COMPLETED,
        }
        assert warnings == []


# ---------------------------------------------------------------------------
# Review-due expansion (moved from _ListProjectsPipeline._expand_review_due)
# ---------------------------------------------------------------------------


class TestExpandReviewDue:
    """DomainLogic.expand_review_due -- deterministic with fixed now."""

    def test_now_returns_now(self) -> None:
        result = _domain().expand_review_due("now", _NOW)
        assert result == _NOW

    def test_days(self) -> None:
        """1 day -> now + 1 day."""
        result = _domain().expand_review_due("1d", _NOW)
        assert result == datetime(2026, 4, 8, 14, 0, 0, tzinfo=UTC)

    def test_weeks(self) -> None:
        """1 week -> now + 7 days."""
        result = _domain().expand_review_due("1w", _NOW)
        assert result == datetime(2026, 4, 14, 14, 0, 0, tzinfo=UTC)

    def test_30_days(self) -> None:
        """30 days -> now + 30 days."""
        result = _domain().expand_review_due("30d", _NOW)
        assert result == datetime(2026, 5, 7, 14, 0, 0, tzinfo=UTC)

    def test_months(self) -> None:
        """2 months with calendar arithmetic."""
        result = _domain().expand_review_due("2m", _NOW)
        assert result == datetime(2026, 6, 7, 14, 0, 0, tzinfo=UTC)

    def test_months_day_clamping(self) -> None:
        """Jan 31 + 1 month -> Feb 28 (day clamped)."""
        jan31 = datetime(2026, 1, 31, 14, 0, 0, tzinfo=UTC)
        result = _domain().expand_review_due("1m", jan31)
        assert result == datetime(2026, 2, 28, 14, 0, 0, tzinfo=UTC)

    def test_years(self) -> None:
        """1 year -> now + 1 year."""
        result = _domain().expand_review_due("1y", _NOW)
        assert result == datetime(2027, 4, 7, 14, 0, 0, tzinfo=UTC)

    def test_count_omitted_defaults_to_1(self) -> None:
        """'w' means 1 week -- count omitted."""
        result = _domain().expand_review_due("w", _NOW)
        assert result == datetime(2026, 4, 14, 14, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# normalize_date_input (LOCAL-03, LOCAL-04, LOCAL-06)
# ---------------------------------------------------------------------------


class TestNormalizeDateInput:
    """normalize_date_input() -- domain-layer product decision for date normalization.

    Requirements covered:
    - LOCAL-03: Aware strings silently converted to naive local
    - LOCAL-04: Date-only strings use default_time (user-configured per date field)
    - LOCAL-06: Naive passthrough (normalization is domain-layer, not contract-layer)
    """

    def test_date_only_uses_default_time(self) -> None:
        """Date-only input with explicit default_time uses that time instead of midnight."""

        result = normalize_date_input("2026-07-15", default_time="17:00:00")
        assert result == "2026-07-15T17:00:00"

    def test_date_only_midnight_when_no_default_time(self) -> None:
        """Date-only input without default_time falls back to midnight."""

        result = normalize_date_input("2026-07-15")
        assert result == "2026-07-15T00:00:00"

    def test_naive_datetime_passes_through_unchanged(self) -> None:
        """LOCAL-06: Naive datetime string returns unchanged (already local by contract)."""

        result = normalize_date_input("2026-07-15T17:00:00")
        assert result == "2026-07-15T17:00:00"

    def test_aware_utc_string_converted_to_naive_local(self) -> None:
        """LOCAL-03: UTC-aware (Z suffix) converted to naive local."""

        result = normalize_date_input("2026-07-15T16:00:00Z")
        # Result must be naive: no Z, no +, and no offset suffix after position 10
        assert "Z" not in result
        assert "+" not in result
        # Date portion must still be present; result is a valid ISO string
        assert "T" in result
        # Verify it parses as naive
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo is None, f"Expected naive datetime, got tzinfo={parsed.tzinfo!r}"

    def test_aware_offset_string_converted_to_naive_local(self) -> None:
        """LOCAL-03: Offset-aware (+01:00) converted to naive local."""

        result = normalize_date_input("2026-07-15T17:00:00+01:00")
        assert "Z" not in result
        assert "+" not in result
        assert "T" in result
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo is None, f"Expected naive datetime, got tzinfo={parsed.tzinfo!r}"


# ---------------------------------------------------------------------------
# _to_utc_ts naive string handling (SUPPLEMENTARY)
# ---------------------------------------------------------------------------


class TestToUtcTsNaiveString:
    """_to_utc_ts() handles naive strings as local time (post-Phase-49 behavior).

    The old assertion `assert dt.tzinfo is not None` was removed. After Phase 49,
    payload dates are naive-local strings and must be comparable without error.
    """

    def test_naive_string_returns_float(self) -> None:
        """_to_utc_ts('2026-07-15T17:00:00') returns a float, no assertion error."""

        result = _to_utc_ts("2026-07-15T17:00:00")
        assert isinstance(result, float), f"Expected float, got {type(result).__name__}: {result!r}"

    def test_none_returns_none(self) -> None:
        """_to_utc_ts(None) returns None (cleared field passthrough)."""

        assert _to_utc_ts(None) is None

    def test_aware_string_returns_float(self) -> None:
        """_to_utc_ts with aware string returns float (existing behavior preserved)."""

        result = _to_utc_ts("2026-07-15T17:00:00Z")
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# True inheritance walk
# ---------------------------------------------------------------------------


def _make_project(**overrides: object) -> Project:
    """Create a Project model from make_model_project_dict defaults."""
    return Project.model_validate(make_model_project_dict(**overrides))


def _make_snapshot_with(
    tasks: list[Task] | None = None,
    projects: list[Project] | None = None,
) -> AllEntities:
    """Build a minimal AllEntities with given tasks and projects."""
    from tests.conftest import (  # noqa: PLC0415
        make_model_snapshot_dict,
    )

    data = make_model_snapshot_dict(
        tasks=[],
        projects=[],
        tags=[],
        folders=[],
        perspectives=[],
    )
    snapshot = AllEntities.model_validate(data)
    if tasks:
        snapshot.tasks.extend(tasks)
    if projects:
        snapshot.projects.extend(projects)
    return snapshot


async def _walk(domain: DomainLogic, tasks: list[Task]) -> list[Task]:
    """Shorthand for compute_true_inheritance."""
    return await domain.compute_true_inheritance(tasks)


class TestComputeTrueInheritance:
    """Unit tests for DomainLogic.compute_true_inheritance -- hierarchy walk."""

    # -- Self-echo stripping (no ancestors set the field) --------------------

    @pytest.mark.anyio
    async def test_self_echo_flagged_stripped(self) -> None:
        """flagged=True, inherited_flagged=True, no ancestors -> inherited_flagged=False."""
        task = _make_task(
            id="t1",
            flagged=True,
            inheritedFlagged=True,
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", flagged=False)
        snapshot = _make_snapshot_with(tasks=[task], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [task])

        assert len(result) == 1
        assert result[0].inherited_flagged is False

    @pytest.mark.anyio
    async def test_self_echo_due_date_stripped(self) -> None:
        """Task with due_date set, no ancestor with due_date -> inherited_due_date=None."""
        task = _make_task(
            id="t1",
            dueDate="2026-07-15T17:00:00.000Z",
            inheritedDueDate="2026-07-15T17:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", dueDate=None)
        snapshot = _make_snapshot_with(tasks=[task], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [task])

        assert result[0].inherited_due_date is None

    # -- Truly inherited from parent task ------------------------------------

    @pytest.mark.anyio
    async def test_truly_inherited_flagged_from_parent_task(self) -> None:
        """Task under flagged parent task -> inherited_flagged stays True."""
        parent = _make_task(
            id="t-parent",
            flagged=True,
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            flagged=False,
            inheritedFlagged=True,
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", flagged=False)
        snapshot = _make_snapshot_with(tasks=[parent, child], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        assert result[0].inherited_flagged is True

    @pytest.mark.anyio
    async def test_truly_inherited_due_date_from_parent_task(self) -> None:
        """Task under parent with due_date -> inherited_due_date stays."""
        parent = _make_task(
            id="t-parent",
            dueDate="2026-08-01T12:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            dueDate=None,
            inheritedDueDate="2026-08-01T12:00:00.000Z",
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", dueDate=None)
        snapshot = _make_snapshot_with(tasks=[parent, child], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        assert result[0].inherited_due_date is not None

    # -- Truly inherited from project (D-01) ---------------------------------

    @pytest.mark.anyio
    async def test_truly_inherited_flagged_from_project(self) -> None:
        """Task under flagged project -> inherited_flagged stays True."""
        task = _make_task(
            id="t1",
            flagged=False,
            inheritedFlagged=True,
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", flagged=True)
        snapshot = _make_snapshot_with(tasks=[task], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [task])

        assert result[0].inherited_flagged is True

    @pytest.mark.anyio
    async def test_truly_inherited_due_date_from_project(self) -> None:
        """Task under project with due_date -> inherited_due_date preserved."""
        task = _make_task(
            id="t1",
            dueDate=None,
            inheritedDueDate="2026-09-01T10:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", dueDate="2026-09-01T10:00:00.000Z")
        snapshot = _make_snapshot_with(tasks=[task], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [task])

        assert result[0].inherited_due_date is not None

    # -- Deep hierarchy (grandparent sets field) -----------------------------

    @pytest.mark.anyio
    async def test_deep_hierarchy_grandparent_flagged(self) -> None:
        """task -> parent -> grandparent(flagged) -> project: inherited_flagged preserved."""
        grandparent = _make_task(
            id="t-gp",
            flagged=True,
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        parent = _make_task(
            id="t-parent",
            flagged=False,
            parent={"task": {"id": "t-gp", "name": "GP"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            flagged=False,
            inheritedFlagged=True,
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", flagged=False)
        snapshot = _make_snapshot_with(tasks=[grandparent, parent, child], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        assert result[0].inherited_flagged is True

    # -- All 6 field pairs are checked ---------------------------------------

    @pytest.mark.anyio
    async def test_all_six_field_pairs_self_echo_stripped(self) -> None:
        """All 6 inherited fields are stripped when self-echoed (no ancestors)."""
        task = _make_task(
            id="t1",
            flagged=True,
            inheritedFlagged=True,
            dueDate="2026-07-15T17:00:00.000Z",
            inheritedDueDate="2026-07-15T17:00:00.000Z",
            deferDate="2026-07-10T09:00:00.000Z",
            inheritedDeferDate="2026-07-10T09:00:00.000Z",
            plannedDate="2026-07-12T08:00:00.000Z",
            inheritedPlannedDate="2026-07-12T08:00:00.000Z",
            dropDate="2026-08-01T00:00:00.000Z",
            inheritedDropDate="2026-08-01T00:00:00.000Z",
            completionDate="2026-06-30T12:00:00.000Z",
            inheritedCompletionDate="2026-06-30T12:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(
            id="proj-1",
            flagged=False,
            dueDate=None,
            deferDate=None,
            plannedDate=None,
            dropDate=None,
            completionDate=None,
        )
        snapshot = _make_snapshot_with(tasks=[task], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [task])

        walked = result[0]
        assert walked.inherited_flagged is False
        assert walked.inherited_due_date is None
        assert walked.inherited_defer_date is None
        assert walked.inherited_planned_date is None
        assert walked.inherited_drop_date is None
        assert walked.inherited_completion_date is None

    # -- Inbox task (no real project) ----------------------------------------

    @pytest.mark.anyio
    async def test_inbox_task_self_echoes_cleared(self) -> None:
        """Inbox task ($inbox project) with self-echoed inherited fields -> all cleared."""
        task = _make_task(
            id="t1",
            flagged=True,
            inheritedFlagged=True,
            dueDate="2026-07-15T17:00:00.000Z",
            inheritedDueDate="2026-07-15T17:00:00.000Z",
            parent={"project": {"id": "$inbox", "name": "Inbox"}},
            project={"id": "$inbox", "name": "Inbox"},
        )
        # No project in project_map for $inbox
        snapshot = _make_snapshot_with(tasks=[task], projects=[])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [task])

        assert result[0].inherited_flagged is False
        assert result[0].inherited_due_date is None

    # -- Empty list ----------------------------------------------------------

    @pytest.mark.anyio
    async def test_empty_list_returns_empty(self) -> None:
        """Empty task list -> returns empty list."""
        snapshot = _make_snapshot_with(tasks=[], projects=[])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [])

        assert result == []

    # -- Orphan task (parent not in task_map) --------------------------------

    @pytest.mark.anyio
    async def test_orphan_task_walk_terminates_safely(self) -> None:
        """Task whose parent task is not in task_map -> walk terminates, self-echoes stripped."""
        task = _make_task(
            id="t1",
            flagged=True,
            inheritedFlagged=True,
            parent={"task": {"id": "t-missing", "name": "Missing"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", flagged=False)
        # Note: t-missing is NOT in the snapshot
        snapshot = _make_snapshot_with(tasks=[task], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [task])

        # Parent missing, project not flagged -> inherited_flagged should be False
        assert result[0].inherited_flagged is False

    # -- Computed ancestor values (not OF effective) ---------------------------

    @pytest.mark.anyio
    async def test_computed_due_date_from_project_not_of_effective(self) -> None:
        """Task dueDate=2026-05-01, project dueDate=2036-03-01 -> inheritedDueDate is 2036-03-01.

        OF resolves inheritedDueDate = min(own, project) = 2026-05-01.
        True inheritance should show the project's actual date: 2036-03-01.
        """
        task = _make_task(
            id="t1",
            dueDate="2026-05-01T17:00:00.000Z",
            # OF sets inheritedDueDate to min(task, project) = task's own date
            inheritedDueDate="2026-05-01T17:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", dueDate="2036-03-01T17:00:00.000Z")
        snapshot = _make_snapshot_with(tasks=[task], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [task])

        assert result[0].inherited_due_date == datetime(2036, 3, 1, 17, 0, tzinfo=UTC)

    @pytest.mark.anyio
    async def test_computed_due_date_soonest_ancestor_not_own(self) -> None:
        """Task dueDate=2026-05-01, parent dueDate=2026-06-15, project dueDate=2036-03-01.

        inheritedDueDate should be 2026-06-15 (soonest ancestor), not 2026-05-01 (task's own).
        """
        parent = _make_task(
            id="t-parent",
            dueDate="2026-06-15T17:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            dueDate="2026-05-01T17:00:00.000Z",
            inheritedDueDate="2026-05-01T17:00:00.000Z",
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", dueDate="2036-03-01T17:00:00.000Z")
        snapshot = _make_snapshot_with(tasks=[parent, child], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        assert result[0].inherited_due_date == datetime(2026, 6, 15, 17, 0, tzinfo=UTC)

    @pytest.mark.anyio
    async def test_computed_due_date_soonest_among_ancestors(self) -> None:
        """Grandparent dueDate=2027-01-01, parent dueDate=2026-06-15 -> soonest is 2026-06-15."""
        grandparent = _make_task(
            id="t-gp",
            dueDate="2027-01-01T12:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        parent = _make_task(
            id="t-parent",
            dueDate="2026-06-15T17:00:00.000Z",
            parent={"task": {"id": "t-gp", "name": "GP"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            dueDate=None,
            inheritedDueDate="2026-06-15T17:00:00.000Z",
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", dueDate=None)
        snapshot = _make_snapshot_with(tasks=[grandparent, parent, child], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        assert result[0].inherited_due_date == datetime(2026, 6, 15, 17, 0, tzinfo=UTC)

    @pytest.mark.anyio
    async def test_computed_flagged_from_ancestor_chain(self) -> None:
        """Task not flagged, parent not flagged, project flagged -> inheritedFlagged is True."""
        task = _make_task(
            id="t1",
            flagged=False,
            inheritedFlagged=True,
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", flagged=True)
        snapshot = _make_snapshot_with(tasks=[task], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [task])

        # This already passes (existing test checks is True), but we assert exact value
        assert result[0].inherited_flagged is True

    @pytest.mark.anyio
    async def test_computed_flagged_parent_contributes(self) -> None:
        """Task flagged, parent flagged, project not flagged -> inheritedFlagged True.

        Parent is an ancestor, so it contributes to inherited_flagged.
        """
        parent = _make_task(
            id="t-parent",
            flagged=True,
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            flagged=True,
            inheritedFlagged=True,
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", flagged=False)
        snapshot = _make_snapshot_with(tasks=[parent, child], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        assert result[0].inherited_flagged is True

    @pytest.mark.anyio
    async def test_all_six_date_fields_compute_ancestor_values(self) -> None:
        """All 6 inherited field pairs compute actual ancestor value, not OF effective.

        Task has distinct dates from project. inheritedX should show project dates.
        """
        task = _make_task(
            id="t1",
            flagged=True,
            # OF sets inherited to task's own (self-echo or min resolution)
            inheritedFlagged=True,
            dueDate="2026-05-01T17:00:00.000Z",
            inheritedDueDate="2026-05-01T17:00:00.000Z",
            deferDate="2026-04-01T09:00:00.000Z",
            inheritedDeferDate="2026-04-01T09:00:00.000Z",
            plannedDate="2026-04-15T08:00:00.000Z",
            inheritedPlannedDate="2026-04-15T08:00:00.000Z",
            dropDate="2026-06-01T00:00:00.000Z",
            inheritedDropDate="2026-06-01T00:00:00.000Z",
            completionDate="2026-03-31T12:00:00.000Z",
            inheritedCompletionDate="2026-03-31T12:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(
            id="proj-1",
            flagged=True,
            dueDate="2036-03-01T17:00:00.000Z",
            deferDate="2036-01-01T09:00:00.000Z",
            plannedDate="2036-02-01T08:00:00.000Z",
            dropDate="2036-06-01T00:00:00.000Z",
            completionDate="2036-05-01T12:00:00.000Z",
        )
        snapshot = _make_snapshot_with(tasks=[task], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [task])

        walked = result[0]
        assert walked.inherited_flagged is True
        assert walked.inherited_due_date == datetime(2036, 3, 1, 17, 0, tzinfo=UTC)
        assert walked.inherited_defer_date == datetime(2036, 1, 1, 9, 0, tzinfo=UTC)
        assert walked.inherited_planned_date == datetime(2036, 2, 1, 8, 0, tzinfo=UTC)
        assert walked.inherited_drop_date == datetime(2036, 6, 1, 0, 0, tzinfo=UTC)
        assert walked.inherited_completion_date == datetime(2036, 5, 1, 12, 0, tzinfo=UTC)

    @pytest.mark.anyio
    async def test_simple_inheritance_no_own_date_exact_value(self) -> None:
        """Task has no dueDate, project has dueDate 2036-03-01 -> inheritedDueDate is 2036-03-01.

        Simple case (already passes for is not None) but asserts exact value.
        """
        task = _make_task(
            id="t1",
            dueDate=None,
            inheritedDueDate="2036-03-01T17:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", dueDate="2036-03-01T17:00:00.000Z")
        snapshot = _make_snapshot_with(tasks=[task], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [task])

        assert result[0].inherited_due_date == datetime(2036, 3, 1, 17, 0, tzinfo=UTC)

    # -- Per-field aggregation semantics (INHERIT-05 through INHERIT-10) -------

    @pytest.mark.anyio
    async def test_aggregation_defer_max(self) -> None:
        """Defer uses max: grandparent=2025-01-01, parent=2027-05-01 -> 2027-05-01."""
        grandparent = _make_task(
            id="t-gp",
            deferDate="2025-01-01T00:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        parent = _make_task(
            id="t-parent",
            deferDate="2027-05-01T00:00:00.000Z",
            parent={"task": {"id": "t-gp", "name": "GP"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            deferDate=None,
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", deferDate=None)
        snapshot = _make_snapshot_with(
            tasks=[grandparent, parent, child],
            projects=[project],
        )
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        # max -> 2027-05-01 (parent). min would give 2025-01-01 (WRONG).
        assert result[0].inherited_defer_date == datetime(2027, 5, 1, 0, 0, tzinfo=UTC)

    @pytest.mark.anyio
    async def test_aggregation_defer_max_with_project(self) -> None:
        """Defer max includes project: parent=2026-06-01, project=2027-05-01 -> 2027-05-01."""
        parent = _make_task(
            id="t-parent",
            deferDate="2026-06-01T00:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            deferDate=None,
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", deferDate="2027-05-01T00:00:00.000Z")
        snapshot = _make_snapshot_with(tasks=[parent, child], projects=[project])
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        # max -> 2027-05-01 (project). min would give 2026-06-01 (WRONG).
        assert result[0].inherited_defer_date == datetime(2027, 5, 1, 0, 0, tzinfo=UTC)

    @pytest.mark.anyio
    async def test_aggregation_planned_first_found(self) -> None:
        """Planned uses first-found: grandparent=2028-01-01, parent=2030-07-01 -> 2030-07-01."""
        grandparent = _make_task(
            id="t-gp",
            plannedDate="2028-01-01T00:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        parent = _make_task(
            id="t-parent",
            plannedDate="2030-07-01T00:00:00.000Z",
            parent={"task": {"id": "t-gp", "name": "GP"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            plannedDate=None,
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", plannedDate=None)
        snapshot = _make_snapshot_with(
            tasks=[grandparent, parent, child],
            projects=[project],
        )
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        # first-found -> 2030-07-01 (parent, nearest). min would give 2028-01-01 (WRONG).
        assert result[0].inherited_planned_date == datetime(2030, 7, 1, 0, 0, tzinfo=UTC)

    @pytest.mark.anyio
    async def test_aggregation_planned_first_found_gap(self) -> None:
        """Planned first-found skips gap: grandparent=2028-01-01, parent=None -> 2028-01-01."""
        grandparent = _make_task(
            id="t-gp",
            plannedDate="2028-01-01T00:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        parent = _make_task(
            id="t-parent",
            plannedDate=None,
            parent={"task": {"id": "t-gp", "name": "GP"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            plannedDate=None,
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", plannedDate=None)
        snapshot = _make_snapshot_with(
            tasks=[grandparent, parent, child],
            projects=[project],
        )
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        # Single non-null ancestor -> all strategies agree: 2028-01-01.
        assert result[0].inherited_planned_date == datetime(2028, 1, 1, 0, 0, tzinfo=UTC)

    @pytest.mark.anyio
    async def test_aggregation_drop_first_found(self) -> None:
        """Drop first-found: parent=T1(earlier), grandparent=T2(later) -> T1."""
        grandparent = _make_task(
            id="t-gp",
            dropDate="2026-04-15T16:45:05.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        parent = _make_task(
            id="t-parent",
            dropDate="2026-04-15T16:44:11.000Z",
            parent={"task": {"id": "t-gp", "name": "GP"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            dropDate=None,
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", dropDate=None)
        snapshot = _make_snapshot_with(
            tasks=[grandparent, parent, child],
            projects=[project],
        )
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        # Nearer ancestor (parent) is earlier -> min also matches. Tests first-found.
        assert result[0].inherited_drop_date == datetime(
            2026,
            4,
            15,
            16,
            44,
            11,
            tzinfo=UTC,
        )

    @pytest.mark.anyio
    async def test_aggregation_drop_first_found_reverse(self) -> None:
        """Drop first-found reverse: parent=T3(later), grandparent=T1(earlier) -> T3."""
        grandparent = _make_task(
            id="t-gp",
            dropDate="2026-04-15T16:44:11.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        parent = _make_task(
            id="t-parent",
            dropDate="2026-04-15T16:51:54.000Z",
            parent={"task": {"id": "t-gp", "name": "GP"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            dropDate=None,
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", dropDate=None)
        snapshot = _make_snapshot_with(
            tasks=[grandparent, parent, child],
            projects=[project],
        )
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        # first-found -> 16:51:54 (parent, nearer). min would give 16:44:11 (WRONG).
        assert result[0].inherited_drop_date == datetime(
            2026,
            4,
            15,
            16,
            51,
            54,
            tzinfo=UTC,
        )

    @pytest.mark.anyio
    async def test_aggregation_completion_first_found(self) -> None:
        """Completion first-found: parent=T2(earlier), grandparent=T3(later) -> T2."""
        grandparent = _make_task(
            id="t-gp",
            completionDate="2026-04-15T17:15:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        parent = _make_task(
            id="t-parent",
            completionDate="2026-04-15T17:14:11.000Z",
            parent={"task": {"id": "t-gp", "name": "GP"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            completionDate=None,
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", completionDate=None)
        snapshot = _make_snapshot_with(
            tasks=[grandparent, parent, child],
            projects=[project],
        )
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        # Nearer ancestor (parent) is earlier -> min also matches. Tests first-found.
        assert result[0].inherited_completion_date == datetime(
            2026,
            4,
            15,
            17,
            14,
            11,
            tzinfo=UTC,
        )

    @pytest.mark.anyio
    async def test_aggregation_completion_first_found_reverse(self) -> None:
        """Completion first-found reverse: parent=T2(later), grandparent=T1(earlier) -> T2."""
        grandparent = _make_task(
            id="t-gp",
            completionDate="2026-04-15T18:38:31.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        parent = _make_task(
            id="t-parent",
            completionDate="2026-04-15T18:39:01.000Z",
            parent={"task": {"id": "t-gp", "name": "GP"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            completionDate=None,
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", completionDate=None)
        snapshot = _make_snapshot_with(
            tasks=[grandparent, parent, child],
            projects=[project],
        )
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        # first-found -> 18:39:01 (parent, nearer). min would give 18:38:31 (WRONG).
        assert result[0].inherited_completion_date == datetime(
            2026,
            4,
            15,
            18,
            39,
            1,
            tzinfo=UTC,
        )

    @pytest.mark.anyio
    async def test_aggregation_due_min_regression(self) -> None:
        """Due still uses min: parent=2032-06-15, grandparent=2029-12-31 -> 2029-12-31."""
        grandparent = _make_task(
            id="t-gp",
            dueDate="2029-12-31T00:00:00.000Z",
            parent={"project": {"id": "proj-1", "name": "P"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        parent = _make_task(
            id="t-parent",
            dueDate="2032-06-15T00:00:00.000Z",
            parent={"task": {"id": "t-gp", "name": "GP"}},
            project={"id": "proj-1", "name": "P"},
            hasChildren=True,
        )
        child = _make_task(
            id="t-child",
            dueDate=None,
            parent={"task": {"id": "t-parent", "name": "Parent"}},
            project={"id": "proj-1", "name": "P"},
        )
        project = _make_project(id="proj-1", dueDate=None)
        snapshot = _make_snapshot_with(
            tasks=[grandparent, parent, child],
            projects=[project],
        )
        d = _domain(snapshot=snapshot)

        result = await _walk(d, [child])

        # min -> 2029-12-31 (grandparent, soonest). Regression guard.
        assert result[0].inherited_due_date == datetime(2029, 12, 31, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# DomainLogic.process_note_action
# ---------------------------------------------------------------------------


class TestProcessNoteAction:
    """Note composition + no-op detection. D-04, D-05, D-06, D-08, D-09."""

    def _task_with_note(self, note: str | None) -> Task:
        """Minimal Task fixture with only the note field populated."""
        return _make_task(note=note)

    # Branch 1 — UNSET (no actions at all)
    def test_no_actions_returns_unset(self) -> None:
        domain = _domain()
        task = self._task_with_note("anything")
        cmd = EditTaskCommand(id="t1")  # no actions at all
        value, skip, warns = domain.process_note_action(cmd, task)
        assert isinstance(value, _Unset)
        assert skip is True
        assert warns == []

    def test_actions_without_note_returns_unset(self) -> None:
        """actions present but note is UNSET inside it."""
        domain = _domain()
        task = self._task_with_note("anything")
        cmd = EditTaskCommand(id="t1", actions=EditTaskActions(tags=TagAction(replace=["Work"])))
        value, skip, warns = domain.process_note_action(cmd, task)
        assert isinstance(value, _Unset)
        assert skip is True
        assert warns == []

    # Branch 2 — append on non-empty note
    def test_append_on_non_empty_note_concatenates_with_separator(self) -> None:
        domain = _domain()
        task = self._task_with_note("existing content")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(append="added")),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert value == "existing content\nadded"
        assert skip is False
        assert warns == []

    # Branch 3 — append on empty note (note field is str, so empty = "" not None)
    def test_append_on_none_note_sets_directly(self) -> None:
        # Task.note is str (not Optional[str]) — empty note is represented as "".
        # The process_note_action logic uses `task.note or ""` so both "" and
        # a hypothetical None would behave identically. This test exercises the
        # empty-string path as the canonical "no existing note" case.
        domain = _domain()
        task = self._task_with_note("")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(append="first text")),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert value == "first text"
        assert skip is False
        assert warns == []

    # Branch 5 — append on whitespace-only (NOTE-04 / D-09)
    def test_append_on_whitespace_only_note_discards_whitespace(self) -> None:
        domain = _domain()
        task = self._task_with_note("   \n\t")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(append="first real text")),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert value == "first real text"
        assert skip is False
        assert warns == []

    # Branch 6 — empty append is N1 no-op
    def test_append_empty_string_is_noop_with_n1_warning(self) -> None:
        domain = _domain()
        task = self._task_with_note("existing")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(append="")),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert isinstance(value, _Unset)
        assert skip is True
        assert warns == [NOTE_APPEND_EMPTY]

    # Branch 7 — whitespace-only append is an N1 no-op (matches OmniFocus normalization)
    def test_append_whitespace_only_is_noop_with_n1_warning(self) -> None:
        """Whitespace-only append fires N1. OmniFocus normalizes whitespace-only
        notes to empty and trims trailing whitespace on write (verified via OmniJS
        UAT Phase 55), so a whitespace-only append is invisible end-to-end.
        Classifying as N1 gives the agent a helpful warning matching observable behavior."""
        domain = _domain()
        task = self._task_with_note("existing")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(append="   ")),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert isinstance(value, _Unset)
        assert skip is True
        assert warns == [NOTE_APPEND_EMPTY]

    # Branch 8 — replace with new content
    def test_replace_with_new_content_sets_note(self) -> None:
        domain = _domain()
        task = self._task_with_note("old content")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(replace="new content")),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert value == "new content"
        assert skip is False
        assert warns == []

    # Branch 9 — identical replace is N2 no-op
    def test_replace_identical_content_is_noop_with_n2_warning(self) -> None:
        domain = _domain()
        task = self._task_with_note("same text")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(replace="same text")),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert isinstance(value, _Unset)
        assert skip is True
        assert warns == [NOTE_REPLACE_ALREADY_CONTENT]

    # Branch 10 — replace null clears non-empty note
    def test_replace_null_clears_non_empty_note(self) -> None:
        domain = _domain()
        task = self._task_with_note("content")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(replace=None)),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert value == ""
        assert skip is False
        assert warns == []

    # Branch 11 — replace empty string clears non-empty note
    def test_replace_empty_string_clears_non_empty_note(self) -> None:
        domain = _domain()
        task = self._task_with_note("content")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(replace="")),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert value == ""
        assert skip is False
        assert warns == []

    # Branch 12 — N3 no-op: clear already-empty note
    def test_replace_null_on_none_note_is_noop_with_n3_warning(self) -> None:
        # Task.note is str — "empty note" is represented as "".
        domain = _domain()
        task = self._task_with_note("")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(replace=None)),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert isinstance(value, _Unset)
        assert skip is True
        assert warns == [NOTE_ALREADY_EMPTY]

    # Branch 13 — N3 wins over N2 (pitfall 3) when both match
    def test_replace_empty_on_empty_note_emits_n3_not_n2(self) -> None:
        """Pitfall 3: N3 takes precedence over N2 when both match."""
        domain = _domain()
        task = self._task_with_note("")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(replace="")),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert isinstance(value, _Unset)
        assert skip is True
        assert warns == [NOTE_ALREADY_EMPTY]
        assert NOTE_REPLACE_ALREADY_CONTENT not in warns

    # Branch 14 — whitespace-only note treated as empty for N3 (D-08)
    def test_replace_null_on_whitespace_only_note_is_n3(self) -> None:
        domain = _domain()
        task = self._task_with_note("   \n\t")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(replace=None)),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert isinstance(value, _Unset)
        assert skip is True
        assert warns == [NOTE_ALREADY_EMPTY]

    # Branch 15 — D-08 strip works for empty-string clear too (symmetric with Branch 14)
    def test_replace_empty_string_on_whitespace_only_note_is_n3(self) -> None:
        """Both replace=None and replace="" trigger clearing; D-08 strips either way."""
        domain = _domain()
        task = self._task_with_note("   \n\t")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(replace="")),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert isinstance(value, _Unset)
        assert skip is True
        assert warns == [NOTE_ALREADY_EMPTY]

    # Branch 16 — whitespace-only append fires N1 regardless of existing note state
    def test_append_whitespace_only_on_whitespace_only_note_is_n1_noop(self) -> None:
        """N1 fires on whitespace-only append text before we check existing-note state."""
        domain = _domain()
        task = self._task_with_note("   \n\t")
        cmd = EditTaskCommand(
            id="t1",
            actions=EditTaskActions(note=NoteAction(append="   ")),
        )
        value, skip, warns = domain.process_note_action(cmd, task)
        assert isinstance(value, _Unset)
        assert skip is True
        assert warns == [NOTE_APPEND_EMPTY]


# ---------------------------------------------------------------------------
# enrich_task_presence_flags (Phase 56-03, FLAG-04 + FLAG-05)
# ---------------------------------------------------------------------------


class TestDomainLogicEnrichTaskPresenceFlags:
    """Truth-table for Task-only derived flags (FLAG-04 + FLAG-05).

    - is_sequential        = (task.type == TaskType.SEQUENTIAL)
    - depends_on_children  = (task.has_children AND NOT task.completes_with_children)

    8 cases = 2 (type) x 2 (has_children) x 2 (completes_with_children).
    """

    @staticmethod
    def _task(
        task_type: TaskType,
        has_children: bool,
        completes_with_children: bool,
    ) -> Task:
        return _make_task(
            type=task_type.value,
            hasChildren=has_children,
            completesWithChildren=completes_with_children,
        )

    def test_parallel_no_children_completes_with_children_true(self) -> None:
        domain = _domain()
        task = self._task(TaskType.PARALLEL, False, True)
        result = domain.enrich_task_presence_flags(task)
        assert result.is_sequential is False
        assert result.depends_on_children is False

    def test_parallel_no_children_completes_with_children_false(self) -> None:
        domain = _domain()
        task = self._task(TaskType.PARALLEL, False, False)
        result = domain.enrich_task_presence_flags(task)
        assert result.is_sequential is False
        # has_children=False -> depends_on_children=False regardless of completes_with_children
        assert result.depends_on_children is False

    def test_parallel_has_children_completes_with_children_true(self) -> None:
        domain = _domain()
        task = self._task(TaskType.PARALLEL, True, True)
        result = domain.enrich_task_presence_flags(task)
        assert result.is_sequential is False
        assert result.depends_on_children is False

    def test_parallel_has_children_completes_with_children_false(self) -> None:
        domain = _domain()
        task = self._task(TaskType.PARALLEL, True, False)
        result = domain.enrich_task_presence_flags(task)
        assert result.is_sequential is False
        assert result.depends_on_children is True

    def test_sequential_no_children_completes_with_children_true(self) -> None:
        domain = _domain()
        task = self._task(TaskType.SEQUENTIAL, False, True)
        result = domain.enrich_task_presence_flags(task)
        assert result.is_sequential is True
        assert result.depends_on_children is False

    def test_sequential_no_children_completes_with_children_false(self) -> None:
        domain = _domain()
        task = self._task(TaskType.SEQUENTIAL, False, False)
        result = domain.enrich_task_presence_flags(task)
        assert result.is_sequential is True
        assert result.depends_on_children is False

    def test_sequential_has_children_completes_with_children_true(self) -> None:
        domain = _domain()
        task = self._task(TaskType.SEQUENTIAL, True, True)
        result = domain.enrich_task_presence_flags(task)
        assert result.is_sequential is True
        assert result.depends_on_children is False

    def test_sequential_has_children_completes_with_children_false(self) -> None:
        domain = _domain()
        task = self._task(TaskType.SEQUENTIAL, True, False)
        result = domain.enrich_task_presence_flags(task)
        assert result.is_sequential is True
        assert result.depends_on_children is True

    def test_returned_task_is_a_copy_not_mutation(self) -> None:
        """Enrichment returns a new Task; input is not mutated in place."""
        domain = _domain()
        task = self._task(TaskType.SEQUENTIAL, True, False)
        # Starting values are defaults (False, False) after construction
        assert task.is_sequential is False
        assert task.depends_on_children is False
        result = domain.enrich_task_presence_flags(task)
        # Returned copy carries computed values
        assert result.is_sequential is True
        assert result.depends_on_children is True
        # Original input remains unchanged (defaults)
        assert task.is_sequential is False
        assert task.depends_on_children is False


# ---------------------------------------------------------------------------
# enrich_project_presence_flags (Phase 56-08, G1 — FLAG-04 applied to projects)
# ---------------------------------------------------------------------------


class TestDomainLogicEnrichProjectPresenceFlags:
    """Truth table for project-side is_sequential enrichment (Phase 56-08).

    - is_sequential = (project.type == ProjectType.SEQUENTIAL)

    Projects do NOT carry depends_on_children (FLAG-05 stays tasks-only —
    projects are always containers).
    """

    @staticmethod
    def _project(project_type: ProjectType) -> Project:
        return _make_project(type=project_type.value)

    def test_parallel_project_is_not_sequential(self) -> None:
        domain = _domain()
        project = self._project(ProjectType.PARALLEL)
        result = domain.enrich_project_presence_flags(project)
        assert result.is_sequential is False

    def test_sequential_project_is_sequential(self) -> None:
        domain = _domain()
        project = self._project(ProjectType.SEQUENTIAL)
        result = domain.enrich_project_presence_flags(project)
        assert result.is_sequential is True

    def test_single_actions_project_is_not_sequential(self) -> None:
        domain = _domain()
        project = self._project(ProjectType.SINGLE_ACTIONS)
        result = domain.enrich_project_presence_flags(project)
        assert result.is_sequential is False

    def test_returned_project_is_a_copy_not_mutation(self) -> None:
        """Enrichment returns a new Project; input is not mutated in place."""
        domain = _domain()
        project = self._project(ProjectType.SEQUENTIAL)
        # Starting value is default (False) after construction
        assert project.is_sequential is False
        result = domain.enrich_project_presence_flags(project)
        # Returned copy carries computed value
        assert result.is_sequential is True
        # Original input remains unchanged (default)
        assert project.is_sequential is False


# ---------------------------------------------------------------------------
# assemble_project_type (Phase 56-03, HIER-05)
# ---------------------------------------------------------------------------


class TestDomainLogicAssembleProjectType:
    """HIER-05 precedence: `singleActions` beats `sequential` when both flags set."""

    def test_sequential_true_singletons_true_returns_single_actions(self) -> None:
        """HIER-05 precedence case: singleActions wins."""
        domain = _domain()
        assert (
            domain.assemble_project_type(sequential=True, contains_singleton_actions=True)
            is ProjectType.SINGLE_ACTIONS
        )

    def test_sequential_false_singletons_true_returns_single_actions(self) -> None:
        domain = _domain()
        assert (
            domain.assemble_project_type(sequential=False, contains_singleton_actions=True)
            is ProjectType.SINGLE_ACTIONS
        )

    def test_sequential_true_singletons_false_returns_sequential(self) -> None:
        domain = _domain()
        assert (
            domain.assemble_project_type(sequential=True, contains_singleton_actions=False)
            is ProjectType.SEQUENTIAL
        )

    def test_sequential_false_singletons_false_returns_parallel(self) -> None:
        domain = _domain()
        assert (
            domain.assemble_project_type(sequential=False, contains_singleton_actions=False)
            is ProjectType.PARALLEL
        )
