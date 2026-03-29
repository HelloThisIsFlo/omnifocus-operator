"""Repetition rule write contracts: add spec, edit spec, repo payload.

Naming: Noun-first (RepetitionRuleAddSpec, not AddRepetitionRuleSpec).
Nested specs are about the THING (RepetitionRule), not the ACTION.
Groups them in imports/autocomplete. Top-level commands stay verb-first.

Defines the typed contract for repetition rule creation and editing.
"""

from __future__ import annotations

from typing import Any, get_args

from pydantic import Field, field_validator, model_validator

from omnifocus_operator.agent_messages.errors import (
    REPETITION_INVALID_END_EMPTY,
    REPETITION_INVALID_END_OCCURRENCES,
    REPETITION_INVALID_FREQUENCY_TYPE,
)
from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    Patch,
    PatchOrClear,
)
from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.models.repetition_rule import (
    EndCondition,
    FrequencyType,
    check_frequency_cross_type_fields,
    normalize_day_codes,
    normalize_on,
    validate_interval,
    validate_on_dates,
)


def _validate_frequency_type(v: object) -> object:
    """Shared pre-validator for frequency type across Add and Edit specs."""
    if isinstance(v, str) and v not in get_args(FrequencyType):
        raise ValueError(REPETITION_INVALID_FREQUENCY_TYPE.format(freq_type=v))
    return v


def _validate_end_condition(v: Any) -> Any:
    """Shared pre-validator for end condition across Add and Edit specs."""
    if v is None or not isinstance(v, dict):
        return v
    if "occurrences" in v:
        occ = v["occurrences"]
        if isinstance(occ, int) and occ < 1:
            raise ValueError(REPETITION_INVALID_END_OCCURRENCES.format(value=occ))
        return v
    if "date" in v:
        return v
    raise ValueError(REPETITION_INVALID_END_EMPTY)


class FrequencyAddSpec(CommandModel):
    """All-required frequency spec for creating a repetition rule.

    Same field shapes as Frequency, with extra="forbid" from CommandModel.
    Validators delegate to shared functions in models.repetition_rule.
    """

    type: FrequencyType
    interval: int = Field(default=1)
    on_days: list[str] | None = None
    on: dict[str, str] | None = None
    on_dates: list[int] | None = None

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: object) -> object:
        return _validate_frequency_type(v)

    @field_validator("interval", mode="before")
    @classmethod
    def _validate_interval(cls, v: int) -> int:
        return validate_interval(v)

    @model_validator(mode="after")
    def _check_cross_type_fields(self) -> FrequencyAddSpec:
        check_frequency_cross_type_fields(self.type, self.on_days, self.on, self.on_dates)
        return self

    @field_validator("on_days", mode="before")
    @classmethod
    def _normalize_day_codes(cls, value: list[str] | None) -> list[str] | None:
        return normalize_day_codes(value)

    @field_validator("on", mode="before")
    @classmethod
    def _normalize_on(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return normalize_on(value)

    @field_validator("on_dates", mode="before")
    @classmethod
    def _validate_on_dates(cls, value: list[int] | None) -> list[int] | None:
        return validate_on_dates(value)


class FrequencyEditSpec(CommandModel):
    """Patch-semantics frequency spec for editing a repetition rule.

    Single-field boundary checks (interval >= 1) are validated here.
    Cross-type validation fires when the merged Frequency is constructed
    in the service layer.
    """

    type: Patch[FrequencyType] = UNSET
    interval: Patch[int] = UNSET
    on_days: PatchOrClear[list[str]] = UNSET
    on: PatchOrClear[dict[str, str]] = UNSET
    on_dates: PatchOrClear[list[int]] = UNSET

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: object) -> object:
        return _validate_frequency_type(v)

    @field_validator("interval", mode="before")
    @classmethod
    def _validate_interval(cls, v: int) -> int:
        return validate_interval(v)


class RepetitionRuleAddSpec(CommandModel):
    """All-required spec for creating a repetition rule on a new task."""

    frequency: FrequencyAddSpec
    schedule: Schedule
    based_on: BasedOn
    end: EndCondition | None = None

    @field_validator("end", mode="before")
    @classmethod
    def _validate_end(cls, v: Any) -> Any:
        return _validate_end_condition(v)


class RepetitionRuleEditSpec(CommandModel):
    """Patch-semantics spec for editing a repetition rule.

    All fields default to UNSET (no change). Root-level fields (schedule,
    basedOn, end) are independently patchable. Frequency uses FrequencyEditSpec
    with Patch/PatchOrClear fields.
    """

    frequency: Patch[FrequencyEditSpec] = UNSET
    schedule: Patch[Schedule] = UNSET
    based_on: Patch[BasedOn] = UNSET
    end: PatchOrClear[EndCondition] = UNSET

    @field_validator("end", mode="before")
    @classmethod
    def _validate_end(cls, v: Any) -> Any:
        return _validate_end_condition(v)


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
    "FrequencyAddSpec",
    "FrequencyEditSpec",
    "RepetitionRuleAddSpec",
    "RepetitionRuleEditSpec",
    "RepetitionRuleRepoPayload",
]
