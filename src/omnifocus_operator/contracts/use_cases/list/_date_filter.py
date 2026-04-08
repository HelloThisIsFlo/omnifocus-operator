"""Date filter contract: shorthand period or absolute date bounds."""

from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import field_validator, model_validator

from omnifocus_operator.agent_messages import errors as err
from omnifocus_operator.agent_messages.descriptions import DATE_FILTER_DOC
from omnifocus_operator.contracts.base import QueryModel

_DATE_DURATION_PATTERN = re.compile(r"^(\d*)([dwmy])$")
_THIS_UNIT_PATTERN = re.compile(r"^[dwmy]$")


class DateFilter(QueryModel):
    __doc__ = DATE_FILTER_DOC

    this: str | None = None
    last: str | None = None
    next: str | None = None
    before: str | None = None
    after: str | None = None

    @field_validator("last", "next", mode="after")
    @classmethod
    def _validate_duration(cls, v: str | None) -> str | None:
        if v is None:
            return v
        match = _DATE_DURATION_PATTERN.match(v)
        if not match:
            raise ValueError(err.DATE_FILTER_INVALID_DURATION.format(value=v))
        count_str = match.group(1)
        count = int(count_str) if count_str else 1
        if count <= 0:
            raise ValueError(err.DATE_FILTER_ZERO_NEGATIVE.format(value=v))
        return v

    @field_validator("this", mode="after")
    @classmethod
    def _validate_this_unit(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # 'this' accepts only a bare unit (d/w/m/y), not a count+unit.
        # _DATE_DURATION_PATTERN is intentionally NOT used here.
        if not _THIS_UNIT_PATTERN.match(v):
            raise ValueError(err.DATE_FILTER_INVALID_THIS_UNIT.format(value=v))
        return v

    @field_validator("before", "after", mode="after")
    @classmethod
    def _validate_absolute(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v == "now":
            return v
        # Try parsing as datetime or date
        try:
            datetime.fromisoformat(v)
            return v
        except (ValueError, TypeError):
            pass
        try:
            date.fromisoformat(v)
            return v
        except (ValueError, TypeError):
            raise ValueError(err.DATE_FILTER_INVALID_ABSOLUTE.format(value=v)) from None

    @model_validator(mode="after")
    def _validate_groups(self) -> DateFilter:
        shorthand = [self.this, self.last, self.next]
        absolute = [self.before, self.after]
        has_shorthand = any(v is not None for v in shorthand)
        has_absolute = any(v is not None for v in absolute)

        if not has_shorthand and not has_absolute:
            raise ValueError(err.DATE_FILTER_EMPTY)

        if has_shorthand and has_absolute:
            raise ValueError(err.DATE_FILTER_MIXED_GROUPS)

        if has_shorthand:
            count = sum(1 for v in shorthand if v is not None)
            if count != 1:
                raise ValueError(err.DATE_FILTER_MULTIPLE_SHORTHAND)

        if (
            has_absolute
            and self.before is not None
            and self.after is not None
            and self.after != "now"
            and self.before != "now"
        ):
            # Validate ordering when both are concrete dates
            after_dt = _parse_to_comparable(self.after)
            before_dt = _parse_to_comparable(self.before)
            if after_dt is not None and before_dt is not None and after_dt > before_dt:
                raise ValueError(
                    err.DATE_FILTER_REVERSED_BOUNDS.format(after=self.after, before=self.before)
                )

        return self


def _parse_to_comparable(value: str) -> datetime | None:
    """Parse string to datetime for comparison. Returns None if unparseable."""
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        pass
    try:
        d = date.fromisoformat(value)
        return datetime(d.year, d.month, d.day)  # normalize to datetime
    except (ValueError, TypeError):
        return None
