"""Unit tests for DomainLogic -- business rules for the edit-task pipeline.

Tests use StubResolver and StubRepo (no repository dependency),
independent of repository implementation.
"""

from __future__ import annotations

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
)
from omnifocus_operator.contracts.base import _Unset
from omnifocus_operator.contracts.common import MoveAction, TagAction
from omnifocus_operator.contracts.use_cases.edit_task import (
    EditTaskActions,
    EditTaskCommand,
    EditTaskRepoPayload,
)
from omnifocus_operator.contracts.use_cases.repetition_rule import (
    FrequencyEditSpec,
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.models.common import TagRef
from omnifocus_operator.models.repetition_rule import (
    EndByDate,
    Frequency,
)
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.models.task import Task
from omnifocus_operator.service.domain import DomainLogic
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
    ) -> None:
        self._tag_map = tag_map or {}
        self._tasks = {t.id: t for t in (tasks or [])}

    async def resolve_tags(self, names: list[str]) -> list[str]:
        return [self._tag_map[n] for n in names]

    async def resolve_parent(self, pid: str) -> str:
        return pid  # always succeeds

    async def resolve_task(self, task_id: str) -> Task:
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

    async def get_all(self) -> AllEntities:
        return self._snapshot

    async def get_task(self, task_id: str) -> Task | None:
        return next((t for t in self._snapshot.tasks if t.id == task_id), None)

    async def get_project(self, project_id: str) -> object:
        return next((p for p in self._snapshot.projects if p.id == project_id), None)


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
) -> DomainLogic:
    """Build a DomainLogic with stub dependencies."""
    resolver = StubResolver(tag_map, tasks=tasks)
    repo = StubRepo(tasks=tasks, tags=tags, snapshot=snapshot)
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
        result = await domain.process_move(MoveAction(ending=None), "task-1")
        assert result == {"position": "ending", "container_id": None}

    async def test_move_to_project(self) -> None:
        # StubResolver.resolve_parent always succeeds; StubRepo.get_task returns None
        # for the container (it's a project, not a task), so no cycle check
        domain = _domain()
        result = await domain.process_move(MoveAction(ending="proj-1"), "task-1")
        assert result == {"position": "ending", "container_id": "proj-1"}

    async def test_move_before_anchor(self) -> None:
        task = _make_task(id="task-anchor", name="Anchor")
        domain = _domain(tasks=[task])
        result = await domain.process_move(MoveAction(before="task-anchor"), "task-1")
        assert result == {"position": "before", "anchor_id": "task-anchor"}


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
            parent={"type": "task", "id": "t-parent", "name": "Parent"},
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
            parent={"type": "task", "id": "t-parent", "name": "Parent"},
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
        end = EndByDate(date="2020-01-01T00:00:00Z")
        warnings = domain.check_repetition_warnings(end=end, task=task)
        assert len(warnings) == 1
        assert "2020-01-01" in warnings[0]

    def test_end_date_in_future_no_warn(self) -> None:
        """End date in future -> no warning."""
        domain = _domain()
        task = _make_task()
        end = EndByDate(date="2099-12-31T00:00:00Z")
        warnings = domain.check_repetition_warnings(end=end, task=task)
        assert warnings == []

    def test_no_end_no_warn(self) -> None:
        """No end condition -> no warning."""
        domain = _domain()
        task = _make_task()
        warnings = domain.check_repetition_warnings(end=None, task=task)
        assert warnings == []

    def test_completed_task_warns(self) -> None:
        """Setting repetition on completed task -> warning."""
        domain = _domain()
        task = _make_task(availability="completed")
        warnings = domain.check_repetition_warnings(end=None, task=task)
        assert len(warnings) == 1
        assert "completed" in warnings[0]

    def test_dropped_task_warns(self) -> None:
        """Setting repetition on dropped task -> warning (D-12: both completed AND dropped)."""
        domain = _domain()
        task = _make_task(availability="dropped")
        warnings = domain.check_repetition_warnings(end=None, task=task)
        assert len(warnings) == 1
        assert "dropped" in warnings[0]

    def test_available_task_no_warn(self) -> None:
        """Available task -> no status warning."""
        domain = _domain()
        task = _make_task(availability="available")
        warnings = domain.check_repetition_warnings(end=None, task=task)
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
        assert result.on == {"last": "friday"}
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
        assert result.on == {"first": "monday"}
        assert result.on_dates is None
        assert len(warnings) == 1
        assert REPETITION_AUTO_CLEAR_ON_DATES in warnings[0]

    def test_no_conflict_no_warning(self) -> None:
        """Agent sets on, existing has no on_dates -> no auto-clear needed."""
        domain = _domain()
        existing = Frequency(type="monthly")
        edit_spec = FrequencyEditSpec(on={"first": "monday"})
        result, warnings = domain.merge_frequency(edit_spec, existing)
        assert result.on == {"first": "monday"}
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
                    rule_string="FREQ=DAILY",
                    schedule_type="Regularly",
                    anchor_date_key="DueDate",
                    catch_up_automatically=False,
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
                    rule_string="FREQ=DAILY;INTERVAL=3",
                    schedule_type="Regularly",
                    anchor_date_key="DueDate",
                    catch_up_automatically=False,
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
