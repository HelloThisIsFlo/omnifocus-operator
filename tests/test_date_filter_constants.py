"""Tests for date filter agent message constants."""

from omnifocus_operator.agent_messages.errors import (
    ABSOLUTE_RANGE_FILTER_EMPTY,
    DATE_FILTER_INVALID_DURATION,
    DATE_FILTER_NAIVE_DATETIME,
    DATE_FILTER_REVERSED_BOUNDS,
    DATE_FILTER_ZERO_NEGATIVE,
)


class TestDateFilterErrorConstants:
    """Date filter error constants are importable and well-formed."""

    def test_absolute_range_empty_importable(self) -> None:
        assert isinstance(ABSOLUTE_RANGE_FILTER_EMPTY, str)
        assert len(ABSOLUTE_RANGE_FILTER_EMPTY) > 0
        assert "AbsoluteRangeFilter" in ABSOLUTE_RANGE_FILTER_EMPTY

    def test_naive_datetime_importable(self) -> None:
        assert isinstance(DATE_FILTER_NAIVE_DATETIME, str)
        assert len(DATE_FILTER_NAIVE_DATETIME) > 0
        assert "timezone" in DATE_FILTER_NAIVE_DATETIME

    def test_invalid_duration_format_placeholder(self) -> None:
        formatted = DATE_FILTER_INVALID_DURATION.format(value="3x")
        assert "3x" in formatted

    def test_zero_negative_format_placeholder(self) -> None:
        formatted = DATE_FILTER_ZERO_NEGATIVE.format(value="0d")
        assert "0d" in formatted

    def test_reversed_bounds_format_placeholders(self) -> None:
        formatted = DATE_FILTER_REVERSED_BOUNDS.format(after="2026-04-14", before="2026-04-01")
        assert "2026-04-14" in formatted
        assert "2026-04-01" in formatted
