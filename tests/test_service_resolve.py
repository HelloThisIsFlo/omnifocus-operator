"""Unit tests for Resolver and validate_task_name / validate_task_name_if_set.

Tests the resolve module independently of OperatorService. Resolver tests use
a real InMemoryRepository (per CONTEXT.md strategy), validation tests are pure.
"""

from __future__ import annotations

import pytest

from omnifocus_operator.contracts.base import UNSET
from omnifocus_operator.repository.in_memory import InMemoryRepository
from omnifocus_operator.service.resolve import (
    Resolver,
    validate_task_name,
    validate_task_name_if_set,
)

from .conftest import (
    make_project_dict,
    make_snapshot,
    make_tag_dict,
    make_task_dict,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def resolver() -> Resolver:
    """Resolver with InMemoryRepository containing known test data."""
    snapshot = make_snapshot(
        tasks=[
            make_task_dict(id="task-1", name="Alpha"),
            make_task_dict(
                id="task-2",
                name="Beta",
                parent={"type": "task", "id": "task-1", "name": "Alpha"},
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
    repo = InMemoryRepository(snapshot)
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
    """Resolver resolves parent IDs and tag names against a real InMemoryRepository."""

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

    # -- Tag resolution ----------------------------------------------------

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
        snapshot = make_snapshot(
            tags=[
                make_tag_dict(id="tag-a", name="Duplicate"),
                make_tag_dict(id="tag-b", name="Duplicate"),
            ],
        )
        repo = InMemoryRepository(snapshot)
        ambiguous_resolver = Resolver(repo)

        with pytest.raises(ValueError, match="Ambiguous tag") as exc_info:
            await ambiguous_resolver.resolve_tags(["Duplicate"])
        assert "tag-a" in str(exc_info.value)
        assert "tag-b" in str(exc_info.value)

    async def test_resolve_tags_multiple(self, resolver: Resolver) -> None:
        """Multiple tag names resolve in order."""
        result = await resolver.resolve_tags(["Work", "Home"])
        assert result == ["tag-work", "tag-home"]
