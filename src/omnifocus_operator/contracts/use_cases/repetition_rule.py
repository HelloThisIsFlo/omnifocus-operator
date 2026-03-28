"""Repetition rule write contracts: add spec, edit spec, repo payload.

Naming: Noun-first (RepetitionRuleAddSpec, not AddRepetitionRuleSpec).
Nested specs are about the THING (RepetitionRule), not the ACTION.
Groups them in imports/autocomplete. Top-level commands stay verb-first.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.contracts.base import UNSET, CommandModel, Patch, PatchOrClear
from omnifocus_operator.models.enums import BasedOn, Schedule

if TYPE_CHECKING:
    from omnifocus_operator.models.repetition_rule import EndCondition, Frequency


class RepetitionRuleAddSpec(CommandModel):
    """All-required spec for creating a repetition rule on a new task.

    Embeds the read-side Frequency union directly. Phase 33.1 will replace
    with flat FrequencyAddSpec/FrequencyEditSpec (CommandModel).
    """

    frequency: Frequency
    schedule: Schedule
    based_on: BasedOn
    end: EndCondition | None = None


class RepetitionRuleEditSpec(CommandModel):
    """Patch-semantics spec for editing a repetition rule.

    All fields default to UNSET (no change). Root-level fields (schedule,
    basedOn, end) are independently patchable. Frequency must include type
    (Pydantic discriminated union requires it).

    Phase 33.1 will replace with flat FrequencyAddSpec/FrequencyEditSpec
    (CommandModel).
    """

    frequency: Patch[Frequency] = UNSET
    schedule: Patch[Schedule] = UNSET
    based_on: Patch[BasedOn] = UNSET
    end: PatchOrClear[EndCondition] = UNSET


class RepetitionRuleRepoPayload(CommandModel):
    """Bridge-ready repetition rule -- fully resolved, no Patch/UNSET.

    Contains the 4 fields the OmniJS bridge needs to construct a
    Task.RepetitionRule: ruleString, scheduleType, anchorDateKey,
    catchUpAutomatically.
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
