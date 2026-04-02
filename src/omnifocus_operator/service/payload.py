"""Typed payload construction -- assemble repo payloads from processed data.

Transforms validated, resolved command data into typed ``AddTaskRepoPayload``
and ``EditTaskRepoPayload`` instances ready for the repository layer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from omnifocus_operator.contracts.base import is_set
from omnifocus_operator.contracts.shared.repetition_rule import (
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskRepoPayload
from omnifocus_operator.contracts.use_cases.edit.tasks import (
    EditTaskRepoPayload,
    MoveToRepoPayload,
)
from omnifocus_operator.rrule.builder import build_rrule
from omnifocus_operator.rrule.schedule import based_on_to_bridge, schedule_to_bridge

if TYPE_CHECKING:
    from omnifocus_operator.contracts.shared.repetition_rule import (
        EndConditionSpec,
        FrequencyAddSpec,
    )
    from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskCommand
    from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskCommand
    from omnifocus_operator.models.enums import BasedOn, Schedule
    from omnifocus_operator.models.repetition_rule import EndCondition, Frequency

logger = logging.getLogger(__name__)

__all__ = ["PayloadBuilder"]


class PayloadBuilder:
    """Assembles typed repo payloads from processed command data."""

    def build_add(
        self,
        command: AddTaskCommand,
        resolved_tag_ids: list[str] | None,
    ) -> AddTaskRepoPayload:
        """Build add-task payload. Only includes populated fields."""
        kwargs: dict[str, object] = {"name": command.name}
        if command.parent is not None:
            kwargs["parent"] = command.parent
        if resolved_tag_ids is not None:
            kwargs["tag_ids"] = resolved_tag_ids
        if command.due_date is not None:
            kwargs["due_date"] = command.due_date.isoformat()
        if command.defer_date is not None:
            kwargs["defer_date"] = command.defer_date.isoformat()
        if command.planned_date is not None:
            kwargs["planned_date"] = command.planned_date.isoformat()
        kwargs["flagged"] = command.flagged
        if command.estimated_minutes is not None:
            kwargs["estimated_minutes"] = command.estimated_minutes
        if command.note is not None:
            kwargs["note"] = command.note
        if command.repetition_rule is not None:
            kwargs["repetition_rule"] = self._build_repetition_rule_payload(
                command.repetition_rule.frequency,
                command.repetition_rule.schedule,
                command.repetition_rule.based_on,
                command.repetition_rule.end,
            )
        return AddTaskRepoPayload.model_validate(kwargs)

    def build_edit(
        self,
        command: EditTaskCommand,
        lifecycle: str | None,
        add_tag_ids: list[str] | None,
        remove_tag_ids: list[str] | None,
        move_to: dict[str, object] | None,
        repetition_rule_payload: RepetitionRuleRepoPayload | None = None,
        repetition_rule_clear: bool = False,
    ) -> EditTaskRepoPayload:
        """Build edit-task payload from command + domain results."""
        # --- 1. Extract command fields ---
        kwargs: dict[str, object] = {"id": command.id}

        # Simple fields (name, note, flagged, estimated_minutes)
        self._add_if_set(kwargs, command, "name", "note", "flagged", "estimated_minutes")

        # Date fields -> ISO strings (None stays None = clear)
        self._add_dates_if_set(kwargs, command, "due_date", "defer_date", "planned_date")

        # --- 2. Merge domain results ---
        if lifecycle is not None:
            kwargs["lifecycle"] = lifecycle
        if add_tag_ids:
            kwargs["add_tag_ids"] = add_tag_ids
        if remove_tag_ids:
            kwargs["remove_tag_ids"] = remove_tag_ids
        if move_to is not None:
            kwargs["move_to"] = MoveToRepoPayload.model_validate(move_to)

        if repetition_rule_clear:
            kwargs["repetition_rule"] = None
        elif repetition_rule_payload is not None:
            kwargs["repetition_rule"] = repetition_rule_payload

        # --- 3. Build typed payload ---
        return EditTaskRepoPayload.model_validate(kwargs)

    def _add_if_set(self, kwargs: dict[str, object], command: object, *fields: str) -> None:
        """Add non-UNSET command fields to kwargs dict."""
        for field in fields:
            value = getattr(command, field)
            if is_set(value):
                kwargs[field] = value

    def _build_repetition_rule_payload(
        self,
        frequency: Frequency | FrequencyAddSpec,
        schedule: Schedule,
        based_on: BasedOn,
        end: EndCondition | EndConditionSpec | None,
    ) -> RepetitionRuleRepoPayload:
        """Convert structured repetition rule fields to bridge-ready payload."""
        rule_string = build_rrule(frequency, end)
        schedule_type, catch_up = schedule_to_bridge(schedule)
        anchor_date_key = based_on_to_bridge(based_on)
        return RepetitionRuleRepoPayload(
            rule_string=rule_string,
            schedule_type=schedule_type,
            anchor_date_key=anchor_date_key,
            catch_up_automatically=catch_up,
        )

    def _add_dates_if_set(self, kwargs: dict[str, object], command: object, *fields: str) -> None:
        """Add non-UNSET date fields, serialized to ISO string."""
        for field in fields:
            value = getattr(command, field)
            if is_set(value):
                kwargs[field] = value.isoformat() if value is not None else None
