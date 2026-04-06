"""Tests for system location configuration (SLOC-01).

Validates: SYSTEM_LOCATION_PREFIX, SYSTEM_LOCATIONS registry,
and that all location IDs use the declared prefix.
"""

from __future__ import annotations

from omnifocus_operator.agent_messages.descriptions import PROJECT_REF_DOC
from omnifocus_operator.config import SYSTEM_LOCATION_PREFIX, SYSTEM_LOCATIONS, SystemLocation
from omnifocus_operator.models.enums import EntityType


class TestSystemLocationConstants:
    """System location constants exist with expected values."""

    def test_system_location_prefix(self) -> None:
        assert SYSTEM_LOCATION_PREFIX == "$"

    def test_inbox_location_exists(self) -> None:
        assert "inbox" in SYSTEM_LOCATIONS

    def test_inbox_location_values(self) -> None:
        inbox = SYSTEM_LOCATIONS["inbox"]
        assert inbox.id == "$inbox"
        assert inbox.name == "Inbox"
        assert inbox.type == EntityType.PROJECT

    def test_all_locations_are_system_location_type(self) -> None:
        for key, loc in SYSTEM_LOCATIONS.items():
            assert isinstance(loc, SystemLocation), f"{key} is not a SystemLocation"

    def test_all_location_ids_use_prefix(self) -> None:
        for key, loc in SYSTEM_LOCATIONS.items():
            assert loc.id.startswith(SYSTEM_LOCATION_PREFIX), (
                f"Location '{key}' id '{loc.id}' does not start with '{SYSTEM_LOCATION_PREFIX}'"
            )


class TestSystemLocationDocstringDrift:
    """Agent-facing docstrings must reference actual system location values."""

    def test_project_ref_doc_uses_inbox_id_and_name(self) -> None:
        inbox = SYSTEM_LOCATIONS["inbox"]
        assert inbox.id in PROJECT_REF_DOC, (
            f"PROJECT_REF_DOC does not contain inbox id '{inbox.id}'"
        )
        assert inbox.name in PROJECT_REF_DOC, (
            f"PROJECT_REF_DOC does not contain inbox name '{inbox.name}'"
        )
