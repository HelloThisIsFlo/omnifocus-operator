"""Unit tests for DomainLogic -- business rules for the edit-task pipeline.

Tests use StubResolver and StubRepo (no repository dependency),
independent of repository implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from omnifocus_operator.agent_messages.warnings import (
    EDIT_COMPLETED_TASK,
    LIFECYCLE_REPEATING_COMPLETE,
    LIFECYCLE_REPEATING_DROP,
    REPETITION_AUTO_CLEAR_ON,
    REPETITION_AUTO_CLEAR_ON_DATES,
    REPETITION_EMPTY_ON,
    REPETITION_EMPTY_ON_DATES,
    REPETITION_EMPTY_ON_DAYS,
    REPETITION_FROM_COMPLETION_BYDAY,
)
from omnifocus_operator.contracts.base import UNSET, _Unset
from omnifocus_operator.contracts.shared.actions import MoveAction, TagAction
from omnifocus_operator.contracts.shared.repetition_rule import (
    FrequencyEditSpec,
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.contracts.use_cases.edit.tasks import (
    EditTaskActions,
    EditTaskCommand,
    EditTaskRepoPayload,
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
from omnifocus_operator.models.common import TagRef
from omnifocus_operator.models.enums import (
    Availability,
    BasedOn,
    DueSoonSetting,
    EntityType,
    Schedule,
)
from omnifocus_operator.models.repetition_rule import (
    EndByDate,
    Frequency,
    OrdinalWeekday,
)
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.models.task import Task
from omnifocus_operator.service.domain import DomainLogic, _to_utc_ts, normalize_date_input
from omnifocus_operator.service.errors import EntityTypeMismatchError
from tests.conftest import make_snapshot_dict
from tests.doubles import InMemoryBridge

from .conftest import make_model_tag_dict, make_model_task_dict, make_snapshot, make_task_dict

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


class TestNormalizeClearIntents:
    """Null-means-clear normalization centralized in DomainLogic."""

    def test_note_none_becomes_empty_string(self) -> None:
        domain = _domain()
        cmd = EditTaskCommand(id="t1", note=None)
        result = domain.normalize_clear_intents(cmd)
        assert result.note == ""

    def test_note_with_value_unchanged(self) -> None:
        domain = _domain()
        cmd = EditTaskCommand(id="t1", note="Hello")
        result = domain.normalize_clear_intents(cmd)
        assert result.note == "Hello"

    def test_note_unset_unchanged(self) -> None:
        domain = _domain()
        cmd = EditTaskCommand(id="t1")
        result = domain.normalize_clear_intents(cmd)
        assert isinstance(result.note, _Unset)

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
        task = _make_task()
        end = EndByDate(date=date(2020, 1, 1))
        warnings = domain.check_repetition_warnings(end=end, task=task)
        assert len(warnings) == 1
        assert "2020-01-01" in warnings[0]

    def test_end_date_in_future_no_warn(self) -> None:
        """End date in future -> no warning."""
        domain = _domain()
        task = _make_task()
        end = EndByDate(date=date(2099, 12, 31))
        warnings = domain.check_repetition_warnings(end=end, task=task)
        assert warnings == []

    def test_no_end_no_warn(self) -> None:
        """No end condition -> no warning."""
        domain = _domain()
        task = _make_task()
        warnings = domain.check_repetition_warnings(end=None, task=task)
        assert warnings == []

    def test_available_task_no_warn(self) -> None:
        """Available task -> no status warning."""
        domain = _domain()
        task = _make_task(availability="available")
        warnings = domain.check_repetition_warnings(end=None, task=task)
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
        """No match with a close name -> FILTER_DID_YOU_MEAN."""
        entities = [_StubEntity("p1", "Personal"), _StubEntity("p2", "Work")]
        warnings = _domain().check_filter_resolution("Personl", [], entities, "project")
        assert len(warnings) == 1
        assert "Did you mean" in warnings[0]
        assert "Personal" in warnings[0]

    def test_no_match_no_suggestion(self) -> None:
        """No match, no close names -> FILTER_NO_MATCH."""
        entities = [_StubEntity("p1", "Work"), _StubEntity("p2", "Home")]
        warnings = _domain().check_filter_resolution("zzzzz", [], entities, "project")
        assert len(warnings) == 1
        assert "No project found" in warnings[0]
        assert "skipped" in warnings[0].lower()


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
