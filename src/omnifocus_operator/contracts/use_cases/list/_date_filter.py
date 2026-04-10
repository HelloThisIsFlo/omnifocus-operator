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
from omnifocus_operator.contracts.base import UNSET, Patch, QueryModel, is_set

_DATE_DURATION_PATTERN = re.compile(r"^(\d*)([dwmy])$")


def _reject_naive_datetime(v: Any) -> Any:
    """Intercept naive datetime strings before Pydantic union dispatch."""
    if isinstance(v, str) and "T" in v:  # noqa: SIM102 — readability
        # Looks like a datetime — reject if missing timezone indicator
        if not (v.endswith("Z") or "+" in v[19:] or "-" in v[19:]):
            raise ValueError(err.DATE_FILTER_NAIVE_DATETIME)
    return v


_DateBound = Annotated[
    Literal["now"] | AwareDatetime | date,
    BeforeValidator(_reject_naive_datetime),
]


def _to_naive(v: AwareDatetime | date) -> datetime:
    """Normalize to naive datetime for ordering comparison."""
    if isinstance(v, datetime):
        return v.replace(tzinfo=None)
    return datetime(v.year, v.month, v.day)


class ThisPeriodFilter(QueryModel):
    __doc__ = desc.THIS_PERIOD_FILTER_DOC

    this: Literal["d", "w", "m", "y"] = Field(description=desc.THIS_PERIOD_UNIT)


def _validate_duration(v: str) -> str:
    """Validate a duration string like '3d', '2w', 'm', '1y'."""
    match = _DATE_DURATION_PATTERN.match(v)
    if not match:
        raise ValueError(err.DATE_FILTER_INVALID_DURATION.format(value=v))
    count_str = match.group(1)
    count = int(count_str) if count_str else 1
    if count <= 0:
        raise ValueError(err.DATE_FILTER_ZERO_NEGATIVE.format(value=v))
    return v


class LastPeriodFilter(QueryModel):
    __doc__ = desc.LAST_PERIOD_FILTER_DOC

    last: str = Field(description=desc.LAST_PERIOD_DURATION)

    @field_validator("last", mode="after")
    @classmethod
    def _check_duration(cls, v: str) -> str:
        return _validate_duration(v)


class NextPeriodFilter(QueryModel):
    __doc__ = desc.NEXT_PERIOD_FILTER_DOC

    next: str = Field(description=desc.NEXT_PERIOD_DURATION)

    @field_validator("next", mode="after")
    @classmethod
    def _check_duration(cls, v: str) -> str:
        return _validate_duration(v)


class AbsoluteRangeFilter(QueryModel):
    __doc__ = desc.ABSOLUTE_RANGE_FILTER_DOC

    before: Patch[_DateBound] = Field(default=UNSET, description=desc.ABSOLUTE_RANGE_BEFORE)
    after: Patch[_DateBound] = Field(default=UNSET, description=desc.ABSOLUTE_RANGE_AFTER)

    @model_validator(mode="after")
    def _validate_bounds(self) -> AbsoluteRangeFilter:
        if not is_set(self.before) and not is_set(self.after):
            raise ValueError(err.ABSOLUTE_RANGE_FILTER_EMPTY)
        if is_set(self.before) and is_set(self.after):
            before, after = self.before, self.after
            if before == "now" or after == "now":
                return self  # D-10: skip comparison when "now"
            # Only Literal["now"] is str-typed; early return above handles it
            assert not isinstance(after, str), (
                f"unexpected str {after!r} — only 'now' is allowed and should be caught above"
            )
            assert not isinstance(before, str), (
                f"unexpected str {before!r} — only 'now' is allowed and should be caught above"
            )
            after_dt = _to_naive(after)  # type: ignore[arg-type]  # python/mypy#11907
            before_dt = _to_naive(before)  # type: ignore[arg-type]  # python/mypy#11907
            if after_dt > before_dt:
                raise ValueError(err.DATE_FILTER_REVERSED_BOUNDS.format(after=after, before=before))
        return self


def _route_date_filter(v: Any) -> str | None:
    """Route input to the correct DateFilter union branch."""
    if isinstance(v, dict):
        if "this" in v:
            return "this_period"
        if "last" in v:
            return "last_period"
        if "next" in v:
            return "next_period"
        return "absolute_range"
    # Non-dict: return None so Pydantic raises ValidationError (union_tag_not_found).
    return None


DateFilter = Annotated[
    Annotated[ThisPeriodFilter, Tag("this_period")]
    | Annotated[LastPeriodFilter, Tag("last_period")]
    | Annotated[NextPeriodFilter, Tag("next_period")]
    | Annotated[AbsoluteRangeFilter, Tag("absolute_range")],
    Discriminator(_route_date_filter),
]
