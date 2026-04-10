"""Date filter contract: discriminated union of 4 concrete filter models."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AwareDatetime,
    BeforeValidator,
    Discriminator,
    Field,
    Tag,
    field_validator,
    model_validator,
)

from omnifocus_operator.agent_messages import descriptions as desc
from omnifocus_operator.agent_messages import errors as err
from omnifocus_operator.contracts.base import QueryModel

_DATE_DURATION_PATTERN = re.compile(r"^(\d*)([dwmy])$")


def _reject_naive_datetime(v: Any) -> Any:
    """Intercept naive datetime strings before Pydantic union dispatch."""
    if isinstance(v, str) and "T" in v:
        # Check if string looks like a datetime but lacks timezone indicator
        if not (v.endswith("Z") or "+" in v[19:] or "-" in v[19:]):
            raise ValueError(err.DATE_FILTER_NAIVE_DATETIME)
    return v


def _to_naive(v: AwareDatetime | date) -> datetime:
    """Normalize to naive datetime for ordering comparison."""
    if isinstance(v, datetime):
        return v.replace(tzinfo=None)
    return datetime(v.year, v.month, v.day)


class ThisPeriodFilter(QueryModel):
    __doc__ = desc.THIS_PERIOD_FILTER_DOC

    this: Literal["d", "w", "m", "y"] = Field(description=desc.THIS_PERIOD_UNIT)


class LastPeriodFilter(QueryModel):
    __doc__ = desc.LAST_PERIOD_FILTER_DOC

    last: str = Field(description=desc.LAST_PERIOD_DURATION)

    @field_validator("last", mode="after")
    @classmethod
    def _validate_duration(cls, v: str) -> str:
        match = _DATE_DURATION_PATTERN.match(v)
        if not match:
            raise ValueError(err.DATE_FILTER_INVALID_DURATION.format(value=v))
        count_str = match.group(1)
        count = int(count_str) if count_str else 1
        if count <= 0:
            raise ValueError(err.DATE_FILTER_ZERO_NEGATIVE.format(value=v))
        return v


class NextPeriodFilter(QueryModel):
    __doc__ = desc.NEXT_PERIOD_FILTER_DOC

    next: str = Field(description=desc.NEXT_PERIOD_DURATION)

    @field_validator("next", mode="after")
    @classmethod
    def _validate_duration(cls, v: str) -> str:
        match = _DATE_DURATION_PATTERN.match(v)
        if not match:
            raise ValueError(err.DATE_FILTER_INVALID_DURATION.format(value=v))
        count_str = match.group(1)
        count = int(count_str) if count_str else 1
        if count <= 0:
            raise ValueError(err.DATE_FILTER_ZERO_NEGATIVE.format(value=v))
        return v


class AbsoluteRangeFilter(QueryModel):
    __doc__ = desc.ABSOLUTE_RANGE_FILTER_DOC

    before: Annotated[
        Literal["now"] | AwareDatetime | date | None,
        BeforeValidator(_reject_naive_datetime),
    ] = Field(default=None, description=desc.ABSOLUTE_RANGE_BEFORE)
    after: Annotated[
        Literal["now"] | AwareDatetime | date | None,
        BeforeValidator(_reject_naive_datetime),
    ] = Field(default=None, description=desc.ABSOLUTE_RANGE_AFTER)

    @model_validator(mode="after")
    def _validate_bounds(self) -> AbsoluteRangeFilter:
        if self.before is None and self.after is None:
            raise ValueError(err.ABSOLUTE_RANGE_FILTER_EMPTY)
        if self.before is not None and self.after is not None:
            if self.before == "now" or self.after == "now":
                return self  # D-10: skip comparison when "now"
            after_dt = _to_naive(self.after)
            before_dt = _to_naive(self.before)
            if after_dt > before_dt:
                raise ValueError(
                    err.DATE_FILTER_REVERSED_BOUNDS.format(after=self.after, before=self.before)
                )
        return self


def _route_date_filter(v: Any) -> str:
    """Route input to the correct DateFilter union branch."""
    if isinstance(v, dict):
        if "this" in v:
            return "this_period"
        if "last" in v:
            return "last_period"
        if "next" in v:
            return "next_period"
        return "absolute_range"
    # Non-dict: route to absolute_range for Pydantic type rejection.
    # Do NOT raise ValueError here -- it bypasses ValidationReformatterMiddleware.
    return "absolute_range"


DateFilter = Annotated[
    Annotated[ThisPeriodFilter, Tag("this_period")]
    | Annotated[LastPeriodFilter, Tag("last_period")]
    | Annotated[NextPeriodFilter, Tag("next_period")]
    | Annotated[AbsoluteRangeFilter, Tag("absolute_range")],
    Discriminator(_route_date_filter),
]
