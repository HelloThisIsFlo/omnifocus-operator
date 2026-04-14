"""Tests for response stripping and field projection (server/projection.py)."""

from __future__ import annotations

from typing import Any

from omnifocus_operator.config import (
    PROJECT_DEFAULT_FIELDS,
    PROJECT_FIELD_GROUPS,
    TASK_DEFAULT_FIELDS,
    TASK_FIELD_GROUPS,
)
from omnifocus_operator.contracts.use_cases.list.common import ListResult
from omnifocus_operator.models.project import Project
from omnifocus_operator.models.tag import Tag
from omnifocus_operator.models.task import Task
from omnifocus_operator.server.projection import (
    project_entity,
    resolve_fields,
    shape_list_response,
    shape_list_response_strip_only,
    strip_all_entities,
    strip_entity,
)
from tests.conftest import make_model_project_dict, make_model_tag_dict, make_model_task_dict


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

    def test_strips_multiple_values_at_once(self) -> None:
        entity: dict[str, Any] = {
            "id": "t1",
            "name": "Buy milk",
            "flagged": False,
            "tags": [],
            "note": "",
            "urgency": "none",
            "dueDate": None,
            "availability": "available",
        }
        result = strip_entity(entity)
        assert result == {"id": "t1", "name": "Buy milk", "availability": "available"}

    def test_preserves_dict_values(self) -> None:
        """Dict values (e.g. parent refs) are never stripped, even empty."""
        entity: dict[str, Any] = {
            "id": "t1",
            "parent": {"project": {"id": "p1", "name": "Test"}},
        }
        assert strip_entity(entity) == entity

    def test_strip_all_entities_strips_each_collection(self) -> None:
        """strip_all_entities applies strip_entity to each item in each collection."""
        data: dict[str, Any] = {
            "tasks": [
                {"id": "t1", "name": "Buy milk", "flagged": False, "tags": []},
                {"id": "t2", "name": "Clean", "flagged": True},
            ],
            "projects": [
                {"id": "p1", "name": "Home", "note": ""},
            ],
            "tags": [
                {"id": "tag1", "name": "Errands"},
            ],
            "folders": [],
            "perspectives": [],
        }
        result = strip_all_entities(data)

        assert result["tasks"] == [
            {"id": "t1", "name": "Buy milk"},
            {"id": "t2", "name": "Clean", "flagged": True},
        ]
        assert result["projects"] == [{"id": "p1", "name": "Home"}]
        assert result["tags"] == [{"id": "tag1", "name": "Errands"}]
        assert result["folders"] == []
        assert result["perspectives"] == []

    def test_envelope_fields_not_in_entity_scope(self) -> None:
        """shape_list_response preserves total/hasMore/warnings at envelope level."""

        task = Task.model_validate(make_model_task_dict(name="Buy milk"))
        result = ListResult[Task](
            items=[task], total=1, has_more=False, warnings=["service warning"]
        )
        envelope = shape_list_response(
            result,
            include=None,
            only=None,
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )

        # Envelope fields are always present regardless of stripping
        assert "total" in envelope
        assert envelope["total"] == 1
        assert "hasMore" in envelope
        assert envelope["hasMore"] is False
        assert "warnings" in envelope
        assert "service warning" in envelope["warnings"]


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
        fields, _warnings = resolve_fields(
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

    def test_project_entity_keeps_only_allowed_fields(self) -> None:
        entity: dict[str, Any] = {
            "id": "t1",
            "name": "Buy milk",
            "dueDate": "2026-04-15",
            "note": "Check prices",
        }
        result = project_entity(entity, frozenset({"id", "name"}))
        assert result == {"id": "t1", "name": "Buy milk"}

    def test_include_multiple_groups(self) -> None:
        fields, warnings = resolve_fields(
            include=["notes", "time"],
            only=None,
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )
        assert fields is not None
        assert "note" in fields
        assert "estimatedMinutes" in fields
        assert "repetitionRule" in fields
        for f in TASK_DEFAULT_FIELDS:
            assert f in fields
        assert warnings == []

    def test_project_include_review_group(self) -> None:
        fields, warnings = resolve_fields(
            include=["review"],
            only=None,
            default_fields=PROJECT_DEFAULT_FIELDS,
            field_groups=PROJECT_FIELD_GROUPS,
        )
        assert fields is not None
        assert "nextReviewDate" in fields
        assert "reviewInterval" in fields
        assert "lastReviewDate" in fields
        assert "nextTask" in fields
        assert warnings == []

    def test_only_with_multiple_invalid_produces_multiple_warnings(self) -> None:
        fields, warnings = resolve_fields(
            include=None,
            only=["bogus1", "bogus2", "name"],
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )
        assert fields is not None
        assert "id" in fields
        assert "name" in fields
        assert len(warnings) == 2
        assert "bogus1" in warnings[0]
        assert "bogus2" in warnings[1]


class TestShapeListResponse:
    """Integration tests for shape_list_response."""

    def test_shape_with_default_fields(self) -> None:
        task = Task.model_validate(make_model_task_dict(name="Buy milk"))

        result = ListResult[Task](items=[task], total=1, has_more=False)
        envelope = shape_list_response(
            result,
            include=None,
            only=None,
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )
        assert envelope["total"] == 1
        assert envelope["hasMore"] is False
        assert len(envelope["items"]) == 1
        # Default: no projection, only stripping
        item = envelope["items"][0]
        assert "id" in item
        assert "name" in item
        # Stripped values should be gone
        assert "note" not in item  # empty string stripped
        assert "dueDate" not in item  # None stripped

    def test_shape_with_only_projects_to_selected_fields(self) -> None:
        task = Task.model_validate(
            make_model_task_dict(name="Buy milk", dueDate="2026-04-15T17:00:00+00:00")
        )

        result = ListResult[Task](items=[task], total=1, has_more=False)
        envelope = shape_list_response(
            result,
            include=None,
            only=["name", "dueDate"],
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
        )
        item = envelope["items"][0]
        assert set(item.keys()) == {"id", "name", "dueDate"}

    def test_shape_collects_all_warnings(self) -> None:
        task = Task.model_validate(make_model_task_dict(name="Buy milk"))

        result = ListResult[Task](
            items=[task],
            total=1,
            has_more=False,
            warnings=["result warning"],
        )
        envelope = shape_list_response(
            result,
            include=["notes"],
            only=["name"],  # conflict: only wins, warning added
            default_fields=TASK_DEFAULT_FIELDS,
            field_groups=TASK_FIELD_GROUPS,
            warnings_from_service=["service warning"],
        )
        # Service warning + result warning + conflict warning
        assert len(envelope["warnings"]) == 3
        assert "service warning" in envelope["warnings"]
        assert "result warning" in envelope["warnings"]
        assert any("mutually exclusive" in w.lower() for w in envelope["warnings"])


class TestShapeListResponseStripOnly:
    """Unit tests for shape_list_response_strip_only (list_tags/folders/perspectives)."""

    def test_strips_items_and_preserves_envelope(self) -> None:

        tag = Tag.model_validate(make_model_tag_dict(id="tag-1", name="Work"))
        result = ListResult[Tag](items=[tag], total=1, has_more=False, warnings=["test warning"])
        envelope = shape_list_response_strip_only(result)

        assert envelope["total"] == 1
        assert envelope["hasMore"] is False
        assert envelope["warnings"] == ["test warning"]
        assert len(envelope["items"]) == 1
        item = envelope["items"][0]
        assert item["id"] == "tag-1"
        assert item["name"] == "Work"
        assert item["availability"] == "available"
        # False is stripped
        assert "childrenAreMutuallyExclusive" not in item
        # None is stripped
        assert "parent" not in item

    def test_no_warnings_omitted_from_envelope(self) -> None:

        tag = Tag.model_validate(make_model_tag_dict(id="tag-1", name="Work"))
        result = ListResult[Tag](items=[tag], total=1, has_more=False)
        envelope = shape_list_response_strip_only(result)
        assert "warnings" not in envelope


class TestFieldGroupSync:
    """Enforcement tests: field group definitions stay in sync with model fields (D-05, FSEL-10).

    These catch drift in both directions:
    - New model field not assigned to any group
    - Group field that no longer exists on the model
    """

    def test_every_task_model_field_in_exactly_one_group(self) -> None:
        """Every field from Task.model_dump(by_alias=True) appears in exactly one group."""
        task = Task.model_validate(make_model_task_dict())
        model_fields = set(task.model_dump(by_alias=True).keys())

        # Collect all group fields (defaults + all opt-in groups)
        all_group_fields: set[str] = set(TASK_DEFAULT_FIELDS)
        for group_fields in TASK_FIELD_GROUPS.values():
            all_group_fields |= group_fields

        assert model_fields == all_group_fields, (
            f"Task model/group mismatch.\n"
            f"In model but not in groups: {model_fields - all_group_fields}\n"
            f"In groups but not in model: {all_group_fields - model_fields}"
        )

    def test_every_project_model_field_in_exactly_one_group(self) -> None:
        """Every field from Project.model_dump(by_alias=True) appears in exactly one group."""
        project = Project.model_validate(make_model_project_dict())
        model_fields = set(project.model_dump(by_alias=True).keys())

        all_group_fields: set[str] = set(PROJECT_DEFAULT_FIELDS)
        for group_fields in PROJECT_FIELD_GROUPS.values():
            all_group_fields |= group_fields

        assert model_fields == all_group_fields, (
            f"Project model/group mismatch.\n"
            f"In model but not in groups: {model_fields - all_group_fields}\n"
            f"In groups but not in model: {all_group_fields - model_fields}"
        )

    def test_every_task_group_field_exists_on_model(self) -> None:
        """Every field in TASK_FIELD_GROUPS exists as a model_dump key on Task."""
        task = Task.model_validate(make_model_task_dict())
        model_fields = set(task.model_dump(by_alias=True).keys())

        for group_name, group_fields in TASK_FIELD_GROUPS.items():
            missing = group_fields - model_fields
            assert not missing, f"Task group '{group_name}' contains fields not on model: {missing}"

    def test_every_project_group_field_exists_on_model(self) -> None:
        """Every field in PROJECT_FIELD_GROUPS exists as a model_dump key on Project."""
        project = Project.model_validate(make_model_project_dict())
        model_fields = set(project.model_dump(by_alias=True).keys())

        for group_name, group_fields in PROJECT_FIELD_GROUPS.items():
            missing = group_fields - model_fields
            assert not missing, (
                f"Project group '{group_name}' contains fields not on model: {missing}"
            )

    def test_no_field_in_multiple_groups_task(self) -> None:
        """No task field appears in more than one group (defaults count as a group)."""
        all_groups = {"_defaults": TASK_DEFAULT_FIELDS, **TASK_FIELD_GROUPS}
        seen: dict[str, str] = {}
        for group_name, group_fields in all_groups.items():
            for field in group_fields:
                assert field not in seen, (
                    f"Task field '{field}' in both '{seen[field]}' and '{group_name}'"
                )
                seen[field] = group_name

    def test_no_field_in_multiple_groups_project(self) -> None:
        """No project field appears in more than one group (defaults count as a group)."""
        all_groups = {"_defaults": PROJECT_DEFAULT_FIELDS, **PROJECT_FIELD_GROUPS}
        seen: dict[str, str] = {}
        for group_name, group_fields in all_groups.items():
            for field in group_fields:
                assert field not in seen, (
                    f"Project field '{field}' in both '{seen[field]}' and '{group_name}'"
                )
                seen[field] = group_name
