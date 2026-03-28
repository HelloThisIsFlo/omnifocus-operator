"""Repetition rule write contracts: add spec, edit spec, repo payload.

Noun-first naming convention for nested specs: the spec describes the THING
(RepetitionRule), not the ACTION. Top-level commands remain verb-first
(AddTaskCommand, EditTaskCommand).

Defines the typed contract for repetition rule creation and editing.
"""

from __future__ import annotations

from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    Patch,
    PatchOrClear,
)
from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.models.repetition_rule import EndCondition, Frequency


class RepetitionRuleAddSpec(CommandModel):
    """Full repetition rule specification for task creation.

    All three root fields are required on creation. End condition is optional.
    """

    frequency: Frequency
    schedule: Schedule
    based_on: BasedOn
    end: EndCondition | None = None


class RepetitionRuleEditSpec(CommandModel):
    """Patchable repetition rule specification for task editing.

    Each root field can be independently updated, cleared, or omitted (UNSET).
    """

    frequency: Patch[Frequency] = UNSET
    schedule: Patch[Schedule] = UNSET
    based_on: Patch[BasedOn] = UNSET
    end: PatchOrClear[EndCondition] = UNSET


class RepetitionRuleRepoPayload(CommandModel):
    """Bridge-ready payload for repetition rule creation/modification.

    Contains the 4 fields the bridge needs to construct a new
    Task.RepetitionRule in OmniJS.
    """

    rule_string: str
    schedule_type: str
    anchor_date_key: str
    catch_up_automatically: bool


__all__ = [
    "RepetitionRuleAddSpec",
    "RepetitionRuleEditSpec",
    "RepetitionRuleRepoPayload",
]
