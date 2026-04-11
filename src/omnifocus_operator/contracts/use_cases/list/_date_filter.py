"""Date filter contract: discriminated union of 4 concrete filter models."""

from __future__ import annotations

from datetime import datetime as _datetime
from typing import TYPE_CHECKING, Annotated, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

from pydantic import (
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
from omnifocus_operator.contracts.shared.dates import validate_date_string
from omnifocus_operator.contracts.use_cases.list._enums import (
    DateShortcut,
    DueDateShortcut,
    LifecycleDateShortcut,
)
from omnifocus_operator.contracts.use_cases.list._validators import validate_duration


def _validate_date_bound_string(v: object) -> object:
    """Validate date bound syntax. 'now' literal and non-str pass through."""
    if isinstance(v, str) and v == "now":
        return v
    return validate_date_string(v)


_DateBound = Annotated[
    Literal["now"] | str,
    BeforeValidator(_validate_date_bound_string),
]


class ThisPeriodFilter(QueryModel):
    __doc__ = desc.THIS_PERIOD_FILTER_DOC

    this: Literal["d", "w", "m", "y"] = Field(description=desc.THIS_PERIOD_UNIT)


class LastPeriodFilter(QueryModel):
    __doc__ = desc.LAST_PERIOD_FILTER_DOC

    last: str = Field(description=desc.LAST_PERIOD_DURATION)

    @field_validator("last", mode="after")
    @classmethod
    def _check_duration(cls, v: str) -> str:
        return validate_duration(v)


class NextPeriodFilter(QueryModel):
    __doc__ = desc.NEXT_PERIOD_FILTER_DOC

    next: str = Field(description=desc.NEXT_PERIOD_DURATION)

    @field_validator("next", mode="after")
    @classmethod
    def _check_duration(cls, v: str) -> str:
        return validate_duration(v)


class AbsoluteRangeFilter(QueryModel):
    __doc__ = desc.ABSOLUTE_RANGE_FILTER_DOC

    before: Patch[_DateBound] = Field(default=UNSET, description=desc.ABSOLUTE_RANGE_BEFORE)
    after: Patch[_DateBound] = Field(default=UNSET, description=desc.ABSOLUTE_RANGE_AFTER)

    @model_validator(mode="after")
    def _validate_bounds(self) -> AbsoluteRangeFilter:
        if not is_set(self.before) and not is_set(self.after):
            raise ValueError(err.DATE_FILTER_RANGE_EMPTY)
        if is_set(self.before) and is_set(self.after):
            before, after = self.before, self.after
            if before == "now" or after == "now":
                return self  # D-10: skip comparison when "now"
            # Both are date/datetime strings -- parse and compare
            after_dt = _datetime.fromisoformat(after)
            before_dt = _datetime.fromisoformat(before)
            # Strip tz for comparison (naive ordering is sufficient)
            after_cmp = after_dt.replace(tzinfo=None) if after_dt.tzinfo else after_dt
            before_cmp = before_dt.replace(tzinfo=None) if before_dt.tzinfo else before_dt
            if after_cmp > before_cmp:
                raise ValueError(err.DATE_FILTER_REVERSED_BOUNDS.format(after=after, before=before))
        return self


def _route_date_filter(v: Any) -> str | None:
    """Route input to the correct DatePeriodFilter union branch.

    Unrecognized dicts fall through to ``absolute_range`` intentionally:
    raising ``ValueError`` here bypasses ValidationReformatterMiddleware
    (Pydantic propagates it raw, not as ``ValidationError``).  The
    absolute_range model_validator then rejects with a proper error.

    Caveat: for truly unrecognized keys (e.g. ``{"foo": "bar"}``), the
    error says "requires at least one of before/after" which is misleading —
    the real issue is unrecognized keys.  Acceptable trade-off vs breaking
    the middleware contract.
    """
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


DatePeriodFilter = Annotated[
    Annotated[ThisPeriodFilter, Tag("this_period")]
    | Annotated[LastPeriodFilter, Tag("last_period")]
    | Annotated[NextPeriodFilter, Tag("next_period")]
    | Annotated[AbsoluteRangeFilter, Tag("absolute_range")],
    Discriminator(_route_date_filter),
]


# ── Annotated date input types with type-rejection validators ─────────
#
# Wrap Shortcut | DatePeriodFilter unions with a BeforeValidator that rejects
# non-string/non-dict input (like true, 123, []) with a helpful message
# listing both shortcut strings and object forms.


def _make_date_input_validator(*shortcuts: str) -> Callable[[object], object]:
    shortcut_list = ", ".join(f"'{s}'" for s in shortcuts)

    def validate(v: object) -> object:
        if isinstance(v, (str, dict)):
            return v
        raise ValueError(err.DATE_INPUT_INVALID_TYPE.format(shortcuts=shortcut_list))

    return validate


LifecycleDateFilter = Annotated[
    LifecycleDateShortcut | DatePeriodFilter,
    BeforeValidator(_make_date_input_validator("all", "today")),
]

DueDateFilter = Annotated[
    DueDateShortcut | DatePeriodFilter,
    BeforeValidator(_make_date_input_validator("overdue", "soon", "today")),
]

DateFilter = Annotated[
    DateShortcut | DatePeriodFilter,
    BeforeValidator(_make_date_input_validator("today")),
]
