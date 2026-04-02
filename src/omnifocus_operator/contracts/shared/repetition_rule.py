"""Repetition rule write contracts: add and edit specs."""

from __future__ import annotations

from datetime import date as date_type
from typing import Annotated, Any, Literal, get_args

from pydantic import Field, field_validator, model_validator

from omnifocus_operator.agent_messages.descriptions import (
    END_BY_DATE_DATE,
    END_BY_DATE_DOC,
    END_BY_OCCURRENCES_DOC,
    FREQUENCY_ADD_SPEC_DOC,
    FREQUENCY_EDIT_SPEC_DOC,
    ON_DATE,
    ON_DAYS,
    ON_WEEKDAY_PATTERN,
    ORDINAL_WEEKDAY_SPEC_DOC,
    REPETITION_RULE_ADD_SPEC_DOC,
    REPETITION_RULE_EDIT_SPEC_DOC,
)
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
    is_set,
)
from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.models.repetition_rule import (
    check_at_most_one_ordinal,
    check_frequency_cross_type_fields,
    normalize_day_codes,
    normalize_day_name,
    validate_interval,
    validate_on_dates,
)

# -- Type aliases for agent-facing contracts ----------------------------------
# These carry Literal/Annotated constraints that enrich JSON Schema for agents.
# Core models in models/ use plain types (str, int) instead.

FrequencyType = Literal["minutely", "hourly", "daily", "weekly", "monthly", "yearly"]
DayCode = Literal["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
OnDate = Annotated[int, Field(ge=-1, le=31, description=ON_DATE)]
DayName = Literal[
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "weekday",
    "weekend_day",
]


# -- End Condition Spec Models (contract-side) --------------------------------


class EndByDateSpec(CommandModel):
    __doc__ = END_BY_DATE_DOC
    date: date_type = Field(description=END_BY_DATE_DATE)


class EndByOccurrencesSpec(CommandModel):
    __doc__ = END_BY_OCCURRENCES_DOC
    occurrences: Annotated[int, Field(ge=1)]

    @field_validator("occurrences", mode="before")
    @classmethod
    def _validate_occurrences(cls, v: int) -> int:
        if isinstance(v, int) and v < 1:
            raise ValueError(REPETITION_INVALID_END_OCCURRENCES.format(value=v))
        return v


EndConditionSpec = EndByDateSpec | EndByOccurrencesSpec


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


class OrdinalWeekdaySpec(CommandModel):
    __doc__ = ORDINAL_WEEKDAY_SPEC_DOC

    first: DayName | None = None
    second: DayName | None = None
    third: DayName | None = None
    fourth: DayName | None = None
    fifth: DayName | None = None
    last: DayName | None = None

    @field_validator("first", "second", "third", "fourth", "fifth", "last", mode="before")
    @classmethod
    def _normalize_day_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return normalize_day_name(v)

    @model_validator(mode="after")
    def _check_at_most_one(self) -> OrdinalWeekdaySpec:
        check_at_most_one_ordinal(self)
        return self


class FrequencyAddSpec(CommandModel):
    __doc__ = FREQUENCY_ADD_SPEC_DOC

    type: FrequencyType
    interval: Annotated[int, Field(ge=1, default=1)]
    on_days: list[DayCode] | None = Field(default=None, description=ON_DAYS)
    on: OrdinalWeekdaySpec | None = Field(default=None, description=ON_WEEKDAY_PATTERN)
    on_dates: list[OnDate] | None = Field(default=None, description=ON_DATE)

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
        check_frequency_cross_type_fields(self.type, self.on_days, self.on, self.on_dates)  # type: ignore[arg-type]
        return self

    @field_validator("on_days", mode="before")
    @classmethod
    def _normalize_day_codes(cls, value: list[str] | None) -> list[str] | None:
        return normalize_day_codes(value)

    @field_validator("on_dates", mode="before")
    @classmethod
    def _validate_on_dates(cls, value: list[int] | None) -> list[int] | None:
        return validate_on_dates(value)


class FrequencyEditSpec(CommandModel):
    __doc__ = FREQUENCY_EDIT_SPEC_DOC

    type: Patch[FrequencyType] = UNSET
    interval: Patch[Annotated[int, Field(ge=1)]] = UNSET
    on_days: PatchOrClear[list[DayCode]] = Field(default=UNSET, description=ON_DAYS)
    on: PatchOrClear[OrdinalWeekdaySpec] = Field(default=UNSET, description=ON_WEEKDAY_PATTERN)
    on_dates: PatchOrClear[list[OnDate]] = Field(default=UNSET, description=ON_DATE)

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: object) -> object:
        return _validate_frequency_type(v)

    @field_validator("interval", mode="before")
    @classmethod
    def _validate_interval(cls, v: int) -> int:
        return validate_interval(v)

    @field_validator("on_days", mode="before")
    @classmethod
    def _normalize_day_codes(cls, value: list[str] | None) -> list[str] | None:
        return normalize_day_codes(value)

    @field_validator("on_dates", mode="before")
    @classmethod
    def _validate_on_dates(cls, value: list[int] | None) -> list[int] | None:
        return validate_on_dates(value)

    @model_validator(mode="after")
    def _check_cross_type_fields(self) -> FrequencyEditSpec:
        if not is_set(self.type):
            return self
        check_frequency_cross_type_fields(
            self.type,
            self.on_days if is_set(self.on_days) else None,
            self.on if is_set(self.on) else None,  # type: ignore[arg-type]
            self.on_dates if is_set(self.on_dates) else None,
        )
        return self


class RepetitionRuleAddSpec(CommandModel):
    __doc__ = REPETITION_RULE_ADD_SPEC_DOC

    frequency: FrequencyAddSpec
    schedule: Schedule
    based_on: BasedOn
    end: EndConditionSpec | None = None

    @field_validator("end", mode="before")
    @classmethod
    def _validate_end(cls, v: Any) -> Any:
        return _validate_end_condition(v)


class RepetitionRuleEditSpec(CommandModel):
    __doc__ = REPETITION_RULE_EDIT_SPEC_DOC

    frequency: Patch[FrequencyEditSpec] = UNSET
    schedule: Patch[Schedule] = UNSET
    based_on: Patch[BasedOn] = UNSET
    end: PatchOrClear[EndConditionSpec] = UNSET

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
    "EndByDateSpec",
    "EndByOccurrencesSpec",
    "EndConditionSpec",
    "FrequencyAddSpec",
    "FrequencyEditSpec",
    "OrdinalWeekdaySpec",
    "RepetitionRuleAddSpec",
    "RepetitionRuleEditSpec",
    "RepetitionRuleRepoPayload",
]
