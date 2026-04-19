"""Typed payload construction -- assemble repo payloads from processed data.

Transforms validated, resolved command data into typed ``AddTaskRepoPayload``
and ``EditTaskRepoPayload`` instances ready for the repository layer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from omnifocus_operator.contracts.base import UNSET, _Unset, is_set
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskRepoPayload
from omnifocus_operator.contracts.use_cases.edit.tasks import (
    EditTaskRepoPayload,
    MoveToRepoPayload,
)
from omnifocus_operator.models.enums import TaskType

if TYPE_CHECKING:
    from omnifocus_operator.contracts.shared.repetition_rule import (
        RepetitionRuleRepoPayload,
    )
    from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskCommand
    from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskCommand

logger = logging.getLogger(__name__)

__all__ = ["PayloadBuilder"]


class PayloadBuilder:
    """Assembles typed repo payloads from processed command data."""

    def build_add(
        self,
        command: AddTaskCommand,
        resolved_tag_ids: list[str] | None,
        resolved_parent: str | None = None,
        repetition_rule_payload: RepetitionRuleRepoPayload | None = None,
        *,
        resolved_completes_with_children: bool,
        resolved_type: str,
    ) -> AddTaskRepoPayload:
        """Build add-task payload. Service has resolved all defaults explicitly.

        `resolved_completes_with_children` and `resolved_type` are keyword-only
        and REQUIRED — the service pipeline's ``_resolve_type_defaults`` step
        (PROP-05/06) is responsible for producing them (from the agent's value
        or from OmniFocusPreferences). The bridge always receives concrete
        values on add; the server never relies on OmniFocus implicit defaulting.
        """
        kwargs: dict[str, object] = {"name": command.name}
        if resolved_parent is not None:
            kwargs["parent"] = resolved_parent
        if resolved_tag_ids is not None:
            kwargs["tag_ids"] = resolved_tag_ids
        if command.due_date is not None:
            kwargs["due_date"] = command.due_date  # already str after domain normalization
        if command.defer_date is not None:
            kwargs["defer_date"] = command.defer_date
        if command.planned_date is not None:
            kwargs["planned_date"] = command.planned_date
        kwargs["flagged"] = command.flagged
        kwargs["completes_with_children"] = resolved_completes_with_children  # PROP-05
        kwargs["type"] = resolved_type  # PROP-06
        if command.estimated_minutes is not None:
            kwargs["estimated_minutes"] = command.estimated_minutes
        if command.note is not None:
            kwargs["note"] = command.note
        if repetition_rule_payload is not None:
            kwargs["repetition_rule"] = repetition_rule_payload
        return AddTaskRepoPayload.model_validate(kwargs)

    def build_edit(
        self,
        command: EditTaskCommand,
        lifecycle: str | None,
        add_tag_ids: list[str] | None,
        remove_tag_ids: list[str] | None,
        move_to: dict[str, object] | None,
        *,
        note_value: str | _Unset = UNSET,
        repetition_rule_payload: RepetitionRuleRepoPayload | None = None,
        repetition_rule_clear: bool = False,
    ) -> EditTaskRepoPayload:
        """Build edit-task payload from command + domain results."""
        # --- 1. Extract command fields ---
        kwargs: dict[str, object] = {"id": command.id}

        # Simple fields (name, flagged, estimated_minutes, completes_with_children, type)
        self._add_if_set(
            kwargs,
            command,
            "name",
            "flagged",
            "estimated_minutes",
            "completes_with_children",
            "type",
        )
        # type arrives as a TaskType enum on the command; repo payload stores
        # raw str to keep bridge-serialisation straightforward (PROP-06 edit).
        if "type" in kwargs and isinstance(kwargs["type"], TaskType):
            kwargs["type"] = kwargs["type"].value

        # Note enters via explicit note_value kwarg (composed by process_note_action)
        if is_set(note_value):
            kwargs["note"] = note_value

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

    def _add_dates_if_set(self, kwargs: dict[str, object], command: object, *fields: str) -> None:
        """Add non-UNSET date fields to kwargs. Values are str after normalization."""
        for field in fields:
            value = getattr(command, field)
            if is_set(value):
                kwargs[field] = value  # str or None; None = clear
