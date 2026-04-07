"""Tests for date filter agent message constants."""


class TestDateFilterErrorConstants:
    """All date filter error constants are importable and well-formed."""

    def test_error_constants_importable(self) -> None:
        from omnifocus_operator.agent_messages.errors import (
            DATE_FILTER_EMPTY,
            DATE_FILTER_INVALID_ABSOLUTE,
            DATE_FILTER_INVALID_DURATION,
            DATE_FILTER_MIXED_GROUPS,
            DATE_FILTER_MULTIPLE_SHORTHAND,
            DATE_FILTER_REVERSED_BOUNDS,
            DATE_FILTER_ZERO_NEGATIVE,
        )

        assert DATE_FILTER_MIXED_GROUPS
        assert DATE_FILTER_MULTIPLE_SHORTHAND
        assert DATE_FILTER_EMPTY
        assert DATE_FILTER_INVALID_DURATION
        assert DATE_FILTER_ZERO_NEGATIVE
        assert DATE_FILTER_REVERSED_BOUNDS
        assert DATE_FILTER_INVALID_ABSOLUTE

    def test_duration_error_format_placeholder(self) -> None:
        from omnifocus_operator.agent_messages.errors import DATE_FILTER_INVALID_DURATION

        msg = DATE_FILTER_INVALID_DURATION.format(value="3x")
        assert "3x" in msg
        assert "d/w/m/y" in msg

    def test_zero_negative_error_format_placeholder(self) -> None:
        from omnifocus_operator.agent_messages.errors import DATE_FILTER_ZERO_NEGATIVE

        msg = DATE_FILTER_ZERO_NEGATIVE.format(value="0d")
        assert "0d" in msg
        assert "positive" in msg

    def test_reversed_bounds_error_format_placeholder(self) -> None:
        from omnifocus_operator.agent_messages.errors import DATE_FILTER_REVERSED_BOUNDS

        msg = DATE_FILTER_REVERSED_BOUNDS.format(after="2026-04-14", before="2026-04-01")
        assert "2026-04-14" in msg
        assert "2026-04-01" in msg

    def test_invalid_absolute_error_format_placeholder(self) -> None:
        from omnifocus_operator.agent_messages.errors import DATE_FILTER_INVALID_ABSOLUTE

        msg = DATE_FILTER_INVALID_ABSOLUTE.format(value="not-a-date")
        assert "not-a-date" in msg
        assert "ISO 8601" in msg


class TestDateFilterDescriptionConstants:
    """All date filter description constants are importable."""

    def test_description_constants_importable(self) -> None:
        from omnifocus_operator.agent_messages.descriptions import (
            ADDED_FILTER_DESC,
            COMPLETED_FILTER_DESC,
            DATE_FILTER_DOC,
            DEFER_FILTER_DESC,
            DROPPED_FILTER_DESC,
            DUE_DATE_SHORTCUT_DOC,
            DUE_FILTER_DESC,
            LIFECYCLE_DATE_SHORTCUT_DOC,
            MODIFIED_FILTER_DESC,
            PLANNED_FILTER_DESC,
        )

        assert DATE_FILTER_DOC
        assert DUE_DATE_SHORTCUT_DOC
        assert LIFECYCLE_DATE_SHORTCUT_DOC
        assert DUE_FILTER_DESC
        assert COMPLETED_FILTER_DESC
        assert DROPPED_FILTER_DESC
        assert DEFER_FILTER_DESC
        assert PLANNED_FILTER_DESC
        assert ADDED_FILTER_DESC
        assert MODIFIED_FILTER_DESC
