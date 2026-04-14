"""Tests for response stripping and field projection (server/projection.py)."""

from __future__ import annotations

from typing import Any

import pytest
from omnifocus_operator.server.projection import (
    resolve_fields,
    shape_list_response,
    strip_all_entities,
    strip_entity,
)

from omnifocus_operator.config import (
    PROJECT_DEFAULT_FIELDS,
    PROJECT_FIELD_GROUPS,
    TASK_DEFAULT_FIELDS,
    TASK_FIELD_GROUPS,
)


class TestStripping:
    """Unit tests for strip_entity — STRIP-01, STRIP-02, STRIP-03."""

    def test_strips_null(self) -> None:
        assert strip_entity({"id": "t1", "dueDate": None}) == {"id": "t1"}

    def test_strips_empty_list(self) -> None:
        assert strip_entity({"id": "t1", "tags": []}) == {"id": "t1"}

    def test_strips_empty_string(self) -> None:
        assert strip_entity({"id": "t1", "note": ""}) == {"id": "t1"}

    def test_strips_false(self) -> None:
        assert strip_entity({"id": "t1", "flagged": False}) == {"id": "t1"}

    def test_strips_none_string(self) -> None:
        assert strip_entity({"id": "t1", "urgency": "none"}) == {"id": "t1"}

    def test_availability_never_stripped(self) -> None:
        result = strip_entity({"availability": "available"})
        assert result == {"availability": "available"}

        result = strip_entity({"availability": "blocked"})
        assert result == {"availability": "blocked"}

    def test_preserves_truthy_values(self) -> None:
        entity: dict[str, Any] = {
            "id": "t1",
            "flagged": True,
            "tags": [{"id": "t", "name": "Work"}],
        }
        assert strip_entity(entity) == entity


class TestFieldSelection:
    """Unit tests for resolve_fields — FSEL-01 through FSEL-08."""

    def test_default_fields_no_projection(self) -> None:
        fields, warnings = resolve_fields(
            include=None,
            only=None,
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )
        assert fields is None
        assert warnings == []

    def test_include_adds_group(self) -> None:
        fields, warnings = resolve_fields(
            include=["notes"],
            only=None,
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )
        assert fields is not None
        assert "note" in fields
        # All default fields should still be present
        for f in TASK_DEFAULT_FIELDS:
            assert f in fields
        assert warnings == []

    def test_include_star(self) -> None:
        all_fields = TASK_DEFAULT_FIELDS | frozenset().union(*TASK_FIELD_GROUPS.values())
        fields, warnings = resolve_fields(
            include=["*"],
            only=None,
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )
        assert fields == all_fields
        assert warnings == []

    def test_only_exact_fields(self) -> None:
        fields, warnings = resolve_fields(
            include=None,
            only=["project", "dueDate"],
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )
        assert fields == frozenset({"id", "project", "dueDate"})
        assert warnings == []

    def test_only_always_includes_id(self) -> None:
        fields, warnings = resolve_fields(
            include=None,
            only=["name"],
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )
        assert fields is not None
        assert "id" in fields
        assert "name" in fields

    def test_include_only_conflict(self) -> None:
        fields, warnings = resolve_fields(
            include=["notes"],
            only=["name"],
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )
        # only wins
        assert fields == frozenset({"id", "name"})
        assert len(warnings) == 1
        assert "mutually exclusive" in warnings[0].lower()

    def test_invalid_only_warning(self) -> None:
        fields, warnings = resolve_fields(
            include=None,
            only=["nonexistent"],
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )
        assert fields is not None
        # id always included
        assert "id" in fields
        # Should have a warning about the invalid field
        assert len(warnings) == 1
        assert "nonexistent" in warnings[0]

    def test_only_case_insensitive(self) -> None:
        fields, warnings = resolve_fields(
            include=None,
            only=["DueDate"],
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )
        assert fields is not None
        assert "dueDate" in fields
        assert warnings == []
