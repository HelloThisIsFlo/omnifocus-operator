"""Repetition rule write contracts: add spec, edit spec, repo payload.

Naming: Noun-first (RepetitionRuleAddSpec, not AddRepetitionRuleSpec).
Nested specs are about the THING (RepetitionRule), not the ACTION.
Groups them in imports/autocomplete. Top-level commands stay verb-first.

Defines the typed contract for repetition rule creation and editing.
"""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from omnifocus_operator.agent_messages.errors import (
    REPETITION_INVALID_DAY_CODE,
    REPETITION_INVALID_DAY_NAME,
    REPETITION_INVALID_ON_DATE,
    REPETITION_INVALID_ORDINAL,
)
from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    Patch,
    PatchOrClear,
)
from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.models.repetition_rule import (
    _VALID_DAY_CODES,
    _VALID_DAY_NAMES,
    _VALID_ORDINALS,
    EndCondition,
    FrequencyType,
)


class FrequencyAddSpec(CommandModel):
    """All-required frequency spec for creating a repetition rule.

    Same field shapes as Frequency, with extra="forbid" from CommandModel.
    Includes the same cross-type validators and field normalizers as Frequency.
    """

    type: FrequencyType
    interval: int = Field(default=1, ge=1)
    on_days: list[str] | None = None
    on: dict[str, str] | None = None
    on_dates: list[int] | None = None

    @model_validator(mode="after")
    def _check_cross_type_fields(self) -> FrequencyAddSpec:
        if self.on_days is not None and self.type != "weekly":
            raise ValueError(
                f"on_days is not valid for type '{self.type}'. "
                "on_days can only be used with type 'weekly'."
            )
        if self.on is not None and self.type != "monthly":
            raise ValueError(
                f"on is not valid for type '{self.type}'. on can only be used with type 'monthly'."
            )
        if self.on_dates is not None and self.type != "monthly":
            raise ValueError(
                f"on_dates is not valid for type '{self.type}'. "
                "on_dates can only be used with type 'monthly'."
            )
        if self.on is not None and self.on_dates is not None:
            raise ValueError(
                "on and on_dates are mutually exclusive on monthly frequency. "
                "Use on for day-of-week patterns (e.g., {'second': 'tuesday'}) "
                "or onDates for specific dates (e.g., [1, 15])."
            )
        return self

    @field_validator("on_days", mode="before")
    @classmethod
    def _normalize_day_codes(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = []
        for code in value:
            upper = code.upper()
            if upper not in _VALID_DAY_CODES:
                raise ValueError(REPETITION_INVALID_DAY_CODE.format(code=code))
            normalized.append(upper)
        return normalized

    @field_validator("on", mode="before")
    @classmethod
    def _normalize_on(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return None
        normalized = {}
        for ordinal, day_name in value.items():
            lower_ordinal = ordinal.lower()
            lower_day = day_name.lower()
            if lower_ordinal not in _VALID_ORDINALS:
                raise ValueError(REPETITION_INVALID_ORDINAL.format(ordinal=ordinal))
            if lower_day not in _VALID_DAY_NAMES:
                raise ValueError(REPETITION_INVALID_DAY_NAME.format(day=day_name))
            normalized[lower_ordinal] = lower_day
        return normalized

    @field_validator("on_dates", mode="before")
    @classmethod
    def _validate_on_dates(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        for v in value:
            if v == 0 or v < -1 or v > 31:
                raise ValueError(REPETITION_INVALID_ON_DATE.format(value=v))
        return value


class FrequencyEditSpec(CommandModel):
    """Patch-semantics frequency spec for editing a repetition rule.

    Pure patch container -- NO validators. Cross-type validation fires
    when the merged Frequency is constructed in the service layer.
    """

    type: Patch[FrequencyType] = UNSET
    interval: Patch[int] = UNSET
    on_days: PatchOrClear[list[str]] = UNSET
    on: PatchOrClear[dict[str, str]] = UNSET
    on_dates: PatchOrClear[list[int]] = UNSET


class RepetitionRuleAddSpec(CommandModel):
    """All-required spec for creating a repetition rule on a new task."""

    frequency: FrequencyAddSpec
    schedule: Schedule
    based_on: BasedOn
    end: EndCondition | None = None


class RepetitionRuleEditSpec(CommandModel):
    """Patch-semantics spec for editing a repetition rule.

    All fields default to UNSET (no change). Root-level fields (schedule,
    basedOn, end) are independently patchable. Frequency uses FrequencyEditSpec
    with Patch/PatchOrClear fields and no validators.
    """

    frequency: Patch[FrequencyEditSpec] = UNSET
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
    "FrequencyAddSpec",
    "FrequencyEditSpec",
    "RepetitionRuleAddSpec",
    "RepetitionRuleEditSpec",
    "RepetitionRuleRepoPayload",
]
