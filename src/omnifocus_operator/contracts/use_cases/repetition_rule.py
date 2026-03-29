"""Repetition rule write contracts: add spec, edit spec, repo payload.

Naming: Noun-first (RepetitionRuleAddSpec, not AddRepetitionRuleSpec).
Nested specs are about the THING (RepetitionRule), not the ACTION.
Groups them in imports/autocomplete. Top-level commands stay verb-first.

Defines the typed contract for repetition rule creation and editing.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from omnifocus_operator.agent_messages import errors as err
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
    _VALID_DAY_CODES,
    _VALID_DAY_NAMES,
    _VALID_ORDINALS,
)


class FrequencyAddSpec(CommandModel):
    """Flat frequency spec for creating a repetition rule.

    Same field shapes as Frequency. extra='forbid' catches agent typos.
    Has the same validators as Frequency for cross-type checks.
    """

    type: FrequencyType
    interval: int = Field(default=1, ge=1)
    on_days: list[str] | None = None
    on: dict[str, str] | None = None
    on_dates: list[int] | None = None

    @field_validator("on_days", mode="before")
    @classmethod
    def _normalize_day_codes(cls, v: list[str] | None) -> list[str] | None:
        """Normalize day codes to uppercase and validate."""
        if v is None:
            return None
        normalized = []
        for code in v:
            upper = code.upper()
            if upper not in _VALID_DAY_CODES:
                raise ValueError(err.REPETITION_INVALID_DAY_CODE.format(code=code))
            normalized.append(upper)
        return normalized

    @field_validator("on", mode="before")
    @classmethod
    def _validate_on(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """Validate ordinal and day name in the on dict."""
        if v is None:
            return None
        for ordinal, day_name in v.items():
            if ordinal not in _VALID_ORDINALS:
                raise ValueError(err.REPETITION_INVALID_ORDINAL.format(ordinal=ordinal))
            if day_name not in _VALID_DAY_NAMES:
                raise ValueError(err.REPETITION_INVALID_DAY_NAME.format(day=day_name))
        return v

    @field_validator("on_dates", mode="before")
    @classmethod
    def _validate_on_dates(cls, v: list[int] | None) -> list[int] | None:
        """Validate on_dates values are in range (-1, 1-31)."""
        if v is None:
            return None
        for value in v:
            if value == 0 or value < -1 or value > 31:
                raise ValueError(err.REPETITION_INVALID_ON_DATE.format(value=value))
        return v

    @model_validator(mode="after")
    def _validate_cross_type(self) -> FrequencyAddSpec:
        """Validate specialization fields match the type."""
        if self.on_days is not None and self.type != "weekly":
            raise ValueError(
                f"on_days is not valid for type '{self.type}'. "
                "on_days is only valid for type 'weekly'."
            )
        if self.on is not None and self.type != "monthly":
            raise ValueError(
                f"on is not valid for type '{self.type}'. "
                "on is only valid for type 'monthly'."
            )
        if self.on_dates is not None and self.type != "monthly":
            raise ValueError(
                f"on_dates is not valid for type '{self.type}'. "
                "on_dates is only valid for type 'monthly'."
            )
        if self.on is not None and self.on_dates is not None:
            raise ValueError(
                "on and on_dates are mutually exclusive. "
                "Use on for day-of-week patterns (e.g., {\"second\": \"tuesday\"}) "
                "or on_dates for specific dates (e.g., [1, 15]), not both."
            )
        return self


class FrequencyEditSpec(CommandModel):
    """Patch-semantics frequency spec for editing.

    Pure patch container -- NO validators. Validation fires when the
    merged Frequency is constructed in the service layer.
    """

    type: Patch[FrequencyType] = UNSET
    interval: Patch[int] = UNSET
    on_days: PatchOrClear[list[str]] = UNSET
    on: PatchOrClear[dict[str, str]] = UNSET
    on_dates: PatchOrClear[list[int]] = UNSET


class RepetitionRuleAddSpec(CommandModel):
    """All-required spec for creating a repetition rule on a new task.

    Uses FrequencyAddSpec (CommandModel with validators).
    """

    frequency: FrequencyAddSpec
    schedule: Schedule
    based_on: BasedOn
    end: EndCondition | None = None


class RepetitionRuleEditSpec(CommandModel):
    """Patch-semantics spec for editing a repetition rule.

    All fields default to UNSET (no change). Root-level fields (schedule,
    basedOn, end) are independently patchable. Frequency uses
    FrequencyEditSpec (pure patch container, no validators).
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
