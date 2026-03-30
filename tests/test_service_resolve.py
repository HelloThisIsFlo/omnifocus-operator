"""Unit tests for Resolver and validate_task_name / validate_task_name_if_set.

Tests the resolve module independently of OperatorService. Resolver tests use
BridgeRepository + InMemoryBridge (per D-11), validation tests are pure.
"""

from __future__ import annotations

import pytest

from omnifocus_operator.contracts.base import UNSET
from omnifocus_operator.repository import BridgeRepository
from omnifocus_operator.service.resolve import Resolver
from omnifocus_operator.service.validate import validate_task_name, validate_task_name_if_set
from tests.doubles import ConstantMtimeSource, InMemoryBridge

from .conftest import (
    make_model_project_dict,
    make_model_tag_dict,
    make_project_dict,
    make_snapshot_dict,
    make_tag_dict,
    make_task_dict,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bridge() -> InMemoryBridge:
    """InMemoryBridge pre-loaded with resolver test data (per D-11)."""
    return InMemoryBridge(
        data=make_snapshot_dict(
            tasks=[
                make_task_dict(id="task-1", name="Alpha"),
                make_task_dict(
                    id="task-2",
                    name="Beta",
                    parent="task-1",
                ),
            ],
            projects=[
                make_project_dict(id="proj-1", name="Project One"),
            ],
            tags=[
                make_tag_dict(id="tag-work", name="Work"),
                make_tag_dict(id="tag-home", name="Home"),
                make_tag_dict(id="tag-errand", name="Errand"),
            ],
        )
    )


@pytest.fixture
def repo(bridge: InMemoryBridge) -> BridgeRepository:
    """Repository wired to test bridge with constant mtime (per D-11, D-13)."""
    return BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())


@pytest.fixture
def resolver(repo: BridgeRepository) -> Resolver:
    """Resolver with BridgeRepository + InMemoryBridge containing known test data."""
    return Resolver(repo)


# ---------------------------------------------------------------------------
# validate_task_name
# ---------------------------------------------------------------------------


class TestValidateTaskName:
    """Standalone name validation for add_task (name is required)."""

    def test_valid_name_passes(self) -> None:
        validate_task_name("Buy milk")  # should not raise

    def test_none_raises(self) -> None:
        with pytest.raises(ValueError, match="Task name is required"):
            validate_task_name(None)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="Task name is required"):
            validate_task_name("")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(ValueError, match="Task name is required"):
            validate_task_name("   ")


# ---------------------------------------------------------------------------
# validate_task_name_if_set
# ---------------------------------------------------------------------------


class TestValidateTaskNameIfSet:
    """Name validation for edit_task (name is optional, but if set must be non-empty)."""

    def test_unset_passes(self) -> None:
        validate_task_name_if_set(UNSET)  # should not raise

    def test_valid_name_passes(self) -> None:
        validate_task_name_if_set("Buy milk")  # should not raise

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="Task name cannot be empty"):
            validate_task_name_if_set("")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(ValueError, match="Task name cannot be empty"):
            validate_task_name_if_set("   ")


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


class TestResolver:
    """Resolver resolves parent IDs and tag names against BridgeRepository + InMemoryBridge."""

    # -- Parent resolution -------------------------------------------------

    async def test_resolve_parent_project(self, resolver: Resolver) -> None:
        """Known project ID resolves, returns the ID."""
        result = await resolver.resolve_parent("proj-1")
        assert result == "proj-1"

    async def test_resolve_parent_task(self, resolver: Resolver) -> None:
        """Known task ID resolves (falls through project check)."""
        result = await resolver.resolve_parent("task-1")
        assert result == "task-1"

    async def test_resolve_parent_not_found(self, resolver: Resolver) -> None:
        """Unknown ID raises ValueError."""
        with pytest.raises(ValueError, match="Parent not found: unknown-id"):
            await resolver.resolve_parent("unknown-id")

    # -- Task resolution ---------------------------------------------------

    async def test_resolve_task_found(self, resolver: Resolver) -> None:
        """Known task ID returns the task."""
        task = await resolver.resolve_task("task-1")
        assert task.id == "task-1"
        assert task.name == "Alpha"

    async def test_resolve_task_not_found(self, resolver: Resolver) -> None:
        """Unknown task ID raises ValueError."""
        with pytest.raises(ValueError, match="Task not found: unknown-id"):
            await resolver.resolve_task("unknown-id")

    # -- Project resolution ------------------------------------------------

    async def test_resolve_project_found(self, resolver: Resolver) -> None:
        """Known project ID returns the project."""
        project = await resolver.resolve_project("proj-1")
        assert project.id == "proj-1"
        assert project.name == "Project One"

    async def test_resolve_project_not_found(self, resolver: Resolver) -> None:
        """Unknown project ID raises ValueError."""
        with pytest.raises(ValueError, match="Project not found: unknown-id"):
            await resolver.resolve_project("unknown-id")

    # -- Tag resolution (by ID) --------------------------------------------

    async def test_resolve_tag_found(self, resolver: Resolver) -> None:
        """Known tag ID returns the tag."""
        tag = await resolver.resolve_tag("tag-work")
        assert tag.id == "tag-work"
        assert tag.name == "Work"

    async def test_resolve_tag_not_found(self, resolver: Resolver) -> None:
        """Unknown tag ID raises ValueError."""
        with pytest.raises(ValueError, match="Tag not found: unknown-id"):
            await resolver.resolve_tag("unknown-id")

    # -- Tag resolution (by name) ------------------------------------------

    async def test_resolve_tags_by_name(self, resolver: Resolver) -> None:
        """Exact name match resolves to the tag's ID."""
        result = await resolver.resolve_tags(["Work"])
        assert result == ["tag-work"]

    async def test_resolve_tags_case_insensitive(self, resolver: Resolver) -> None:
        """Lowercase name matches tag with different casing."""
        result = await resolver.resolve_tags(["work"])
        assert result == ["tag-work"]

    async def test_resolve_tags_by_id_fallback(self, resolver: Resolver) -> None:
        """Tag ID string resolves when no name matches."""
        result = await resolver.resolve_tags(["tag-work"])
        assert result == ["tag-work"]

    async def test_resolve_tags_not_found(self, resolver: Resolver) -> None:
        """Unknown tag name raises ValueError."""
        with pytest.raises(ValueError, match="Tag not found: Nonexistent"):
            await resolver.resolve_tags(["Nonexistent"])

    async def test_resolve_tags_ambiguous(self, resolver: Resolver) -> None:
        """Two tags with same name raises ValueError listing both IDs."""
        bridge = InMemoryBridge(
            data=make_snapshot_dict(
                tags=[
                    make_tag_dict(id="tag-a", name="Duplicate"),
                    make_tag_dict(id="tag-b", name="Duplicate"),
                ],
            )
        )
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        ambiguous_resolver = Resolver(repo)

        with pytest.raises(ValueError, match="Ambiguous tag") as exc_info:
            await ambiguous_resolver.resolve_tags(["Duplicate"])
        assert "tag-a" in str(exc_info.value)
        assert "tag-b" in str(exc_info.value)

    async def test_resolve_tags_multiple(self, resolver: Resolver) -> None:
        """Multiple tag names resolve in order."""
        result = await resolver.resolve_tags(["Work", "Home"])
        assert result == ["tag-work", "tag-home"]


# ---------------------------------------------------------------------------
# Read-side filter resolution (resolve_filter / resolve_filter_list / find_unresolved)
# ---------------------------------------------------------------------------


class TestResolveFilter:
    """Resolution cascade: ID match -> substring match -> empty list."""

    def test_id_match(self, resolver: Resolver) -> None:
        """Value matching an entity's .id exactly returns [that_id]."""
        from omnifocus_operator.models.project import Project

        entities = [
            Project.model_validate(make_model_project_dict(id="proj-1", name="Work Projects")),
        ]
        result = resolver.resolve_filter("proj-1", entities)
        assert result == ["proj-1"]

    def test_substring_match(self, resolver: Resolver) -> None:
        """Substring of name matches all entities containing it."""
        from omnifocus_operator.models.project import Project

        entities = [
            Project.model_validate(make_model_project_dict(id="p1", name="Work Projects")),
            Project.model_validate(make_model_project_dict(id="p2", name="Homework")),
            Project.model_validate(make_model_project_dict(id="p3", name="Personal")),
        ]
        result = resolver.resolve_filter("Work", entities)
        assert set(result) == {"p1", "p2"}

    def test_case_insensitive(self, resolver: Resolver) -> None:
        """Substring match is case-insensitive."""
        from omnifocus_operator.models.project import Project

        entities = [
            Project.model_validate(make_model_project_dict(id="p1", name="Work Projects")),
        ]
        result = resolver.resolve_filter("work", entities)
        assert result == ["p1"]

    def test_no_match(self, resolver: Resolver) -> None:
        """No matching entity returns empty list."""
        from omnifocus_operator.models.project import Project

        entities = [
            Project.model_validate(make_model_project_dict(id="p1", name="Work")),
        ]
        result = resolver.resolve_filter("zzzzz", entities)
        assert result == []

    def test_id_takes_priority_over_substring(self, resolver: Resolver) -> None:
        """If value is both an ID and a substring of another name, returns only the ID match."""
        from omnifocus_operator.models.tag import Tag

        entities = [
            Tag.model_validate(make_model_tag_dict(id="work", name="Office")),
            Tag.model_validate(make_model_tag_dict(id="tag-2", name="work-related")),
        ]
        result = resolver.resolve_filter("work", entities)
        assert result == ["work"]


class TestResolveFilterList:
    """Multi-value resolution: resolve each independently, return flat deduped list."""

    def test_multi_value_resolve(self, resolver: Resolver) -> None:
        """Multiple values resolve independently, returning flat deduped ID list."""
        from omnifocus_operator.models.tag import Tag

        entities = [
            Tag.model_validate(make_model_tag_dict(id="tag-errand", name="Errand")),
            Tag.model_validate(make_model_tag_dict(id="some-id", name="Other")),
        ]
        result = resolver.resolve_filter_list(["Errand", "some-id"], entities)
        assert set(result) == {"tag-errand", "some-id"}

    def test_deduplication(self, resolver: Resolver) -> None:
        """Same entity resolved by different values is deduplicated."""
        from omnifocus_operator.models.tag import Tag

        entities = [
            Tag.model_validate(make_model_tag_dict(id="tag-work", name="Work")),
        ]
        # "tag-work" matches by ID, "Work" matches by substring -- both resolve to same entity
        result = resolver.resolve_filter_list(["tag-work", "Work"], entities)
        assert result == ["tag-work"]

    def test_unresolved_values_excluded(self, resolver: Resolver) -> None:
        """Values that don't resolve are simply not included."""
        from omnifocus_operator.models.tag import Tag

        entities = [
            Tag.model_validate(make_model_tag_dict(id="tag-work", name="Work")),
        ]
        result = resolver.resolve_filter_list(["Work", "Nonexistent"], entities)
        assert result == ["tag-work"]


class TestFindUnresolved:
    """Detect values that produced no matches."""

    def test_find_unresolved(self, resolver: Resolver) -> None:
        """Returns values that produced no matches."""
        from omnifocus_operator.models.tag import Tag

        entities = [
            Tag.model_validate(make_model_tag_dict(id="tag-work", name="Work")),
        ]
        result = resolver.find_unresolved(["Work", "Nonexistent", "zzz"], entities)
        assert result == ["Nonexistent", "zzz"]

    def test_all_resolved(self, resolver: Resolver) -> None:
        """When all values resolve, returns empty list."""
        from omnifocus_operator.models.tag import Tag

        entities = [
            Tag.model_validate(make_model_tag_dict(id="tag-work", name="Work")),
        ]
        result = resolver.find_unresolved(["Work"], entities)
        assert result == []
