"""Tests for date filter agent message constants."""

from omnifocus_operator.agent_messages.errors import (
    DATE_FILTER_INVALID_THIS_UNIT,
)


class TestDateFilterErrorConstants:
    """Date filter error constants are importable and well-formed."""

    def test_this_unit_error_importable(self) -> None:
        assert isinstance(DATE_FILTER_INVALID_THIS_UNIT, str)
        assert len(DATE_FILTER_INVALID_THIS_UNIT) > 0

    def test_this_unit_error_format_placeholder(self) -> None:
        """The constant accepts a {value} placeholder and mentions only bare units."""
        formatted = DATE_FILTER_INVALID_THIS_UNIT.format(value="2w")
        assert "2w" in formatted
        # Should mention bare unit chars
        assert "d" in formatted
        assert "w" in formatted
        assert "m" in formatted
        assert "y" in formatted
        # Should NOT mention count+unit examples like '3d' or '2w' as valid examples
        # (the '2w' appears only because we injected it as the invalid value)
        assert "e.g." not in formatted.lower()
        assert "count" not in formatted.lower()
