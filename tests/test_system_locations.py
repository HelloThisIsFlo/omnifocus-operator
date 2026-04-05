"""Tests for system location constants (SLOC-01).

Validates: SYSTEM_LOCATION_PREFIX, SYSTEM_LOCATION_INBOX, INBOX_DISPLAY_NAME
exist with correct values and $inbox uses the declared prefix.
"""

from __future__ import annotations

from omnifocus_operator.config import (
    INBOX_DISPLAY_NAME,
    SYSTEM_LOCATION_INBOX,
    SYSTEM_LOCATION_PREFIX,
)


class TestSystemLocationConstants:
    """System location constants exist with expected values."""

    def test_system_location_prefix(self) -> None:
        assert SYSTEM_LOCATION_PREFIX == "$"

    def test_system_location_inbox(self) -> None:
        assert SYSTEM_LOCATION_INBOX == "$inbox"

    def test_inbox_display_name(self) -> None:
        assert INBOX_DISPLAY_NAME == "Inbox"

    def test_inbox_uses_prefix(self) -> None:
        assert SYSTEM_LOCATION_INBOX.startswith(SYSTEM_LOCATION_PREFIX)
