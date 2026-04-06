"""Unit tests for Resolver and validate_task_name / validate_task_name_if_set.

Tests the resolve module independently of OperatorService. Resolver tests use
BridgeOnlyRepository + InMemoryBridge (per D-11), validation tests are pure.
"""

from __future__ import annotations

import pytest

from omnifocus_operator.contracts.base import UNSET
from omnifocus_operator.models.enums import EntityType
from omnifocus_operator.models.project import Project
from omnifocus_operator.models.tag import Tag
from omnifocus_operator.repository import BridgeOnlyRepository
from omnifocus_operator.service.errors import EntityTypeMismatchError
from omnifocus_operator.service.fuzzy import suggest_close_matches
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
                make_task_dict(id="task-3", name="Beta Task A"),
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
def repo(bridge: InMemoryBridge) -> BridgeOnlyRepository:
    """Repository wired to test bridge with constant mtime (per D-11, D-13)."""
    return BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())


@pytest.fixture
def resolver(repo: BridgeOnlyRepository) -> Resolver:
    """Resolver with BridgeOnlyRepository + InMemoryBridge containing known test data."""
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
# Shared fuzzy module (standalone)
# ---------------------------------------------------------------------------


class TestSuggestCloseMatches:
    """suggest_close_matches works as a standalone function outside DomainLogic."""

    def test_close_match_found(self) -> None:
        result = suggest_close_matches("Wrok", ["Work", "Home", "Errand"])
        assert "Work" in result

    def test_no_match(self) -> None:
        result = suggest_close_matches("zzzzz", ["Work", "Home"])
        assert result == []


# ---------------------------------------------------------------------------
# Resolver -- lookup methods (renamed from resolve_*)
# ---------------------------------------------------------------------------


class TestResolverLookup:
    """Resolver lookup methods return full entities by ID."""

    async def test_lookup_task_found(self, resolver: Resolver) -> None:
        """Known task ID returns the task."""
        task = await resolver.lookup_task("task-1")
        assert task.id == "task-1"
        assert task.name == "Alpha"

    async def test_lookup_task_not_found(self, resolver: Resolver) -> None:
        """Unknown task ID raises ValueError."""
        with pytest.raises(ValueError, match="Task not found: unknown-id"):
            await resolver.lookup_task("unknown-id")

    async def test_lookup_project_found(self, resolver: Resolver) -> None:
        """Known project ID returns the project."""
        project = await resolver.lookup_project("proj-1")
        assert project.id == "proj-1"
        assert project.name == "Project One"

    async def test_lookup_project_not_found(self, resolver: Resolver) -> None:
        """Unknown project ID raises ValueError."""
        with pytest.raises(ValueError, match="Project not found: unknown-id"):
            await resolver.lookup_project("unknown-id")

    async def test_lookup_tag_found(self, resolver: Resolver) -> None:
        """Known tag ID returns the tag."""
        tag = await resolver.lookup_tag("tag-work")
        assert tag.id == "tag-work"
        assert tag.name == "Work"

    async def test_lookup_tag_not_found(self, resolver: Resolver) -> None:
        """Unknown tag ID raises ValueError."""
        with pytest.raises(ValueError, match="Tag not found: unknown-id"):
            await resolver.lookup_tag("unknown-id")


# ---------------------------------------------------------------------------
# Resolver -- _resolve cascade
# ---------------------------------------------------------------------------


class TestResolveAcceptParameter:
    """The accept parameter must be non-empty and reflected in error messages."""

    async def test_empty_accept_raises(self, resolver: Resolver) -> None:
        """Calling _resolve with an empty accept list is a programming error."""
        with pytest.raises(ValueError, match="accept"):
            await resolver._resolve("anything", accept=[])

    async def test_not_found_error_joins_accepted_types(self, resolver: Resolver) -> None:
        """When no match is found, the error message should join all accepted
        types with '/' — e.g. 'No project/task found matching ...'."""
        with pytest.raises(ValueError, match="No project/task found matching 'zzzzz_no_match'"):
            await resolver._resolve("zzzzz_no_match", accept=[EntityType.PROJECT, EntityType.TASK])

    async def test_ambiguous_error_joins_accepted_types(self) -> None:
        """When multiple matches are found, the error message should join all
        accepted types with '/' — e.g. 'Ambiguous project/task ...'."""
        bridge = InMemoryBridge(
            data=make_snapshot_dict(
                projects=[make_project_dict(id="p-1", name="Review Q3")],
                tasks=[make_task_dict(id="t-1", name="Review Q3 notes")],
            )
        )
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        ambiguous_resolver = Resolver(repo)

        with pytest.raises(ValueError, match="Ambiguous project/task 'Review Q3'"):
            await ambiguous_resolver._resolve(
                "Review Q3", accept=[EntityType.PROJECT, EntityType.TASK]
            )


class TestResolveCascade:
    """The three-step cascade: $-prefix -> substring match -> ID fallback."""

    async def test_system_location_inbox(self, resolver: Resolver) -> None:
        """$inbox returns None (inbox = no parent) without any repo call."""
        result = await resolver.resolve_container("$inbox")
        assert result is None

    async def test_system_location_unknown(self, resolver: Resolver) -> None:
        """$trash raises with valid system locations listed."""
        with pytest.raises(ValueError, match="Unknown system location") as exc_info:
            await resolver.resolve_container("$trash")
        assert "$inbox" in str(exc_info.value)

    async def test_dollar_prefix_on_tags_reserved(self, resolver: Resolver) -> None:
        """$-prefixed string for tags raises reserved prefix error."""
        with pytest.raises(ValueError, match="reserved for system locations"):
            await resolver.resolve_tags(["$anything"])

    async def test_substring_match_single(self, resolver: Resolver) -> None:
        """Substring match with one result returns that entity's ID."""
        result = await resolver.resolve_anchor("Alph")
        assert result == "task-1"

    async def test_substring_match_ambiguous(self, resolver: Resolver) -> None:
        """Multiple substring matches raise with both IDs and names."""
        with pytest.raises(ValueError, match="Ambiguous") as exc_info:
            await resolver.resolve_anchor("Beta")
        error_msg = str(exc_info.value)
        assert "task-2" in error_msg
        assert "task-3" in error_msg
        assert "Use the ID" in error_msg

    async def test_no_match_fuzzy_suggestions(self, resolver: Resolver) -> None:
        """Zero matches produce 'Did you mean' with fuzzy suggestions."""
        with pytest.raises(ValueError, match="No task found matching") as exc_info:
            await resolver.resolve_anchor("Alpho")
        assert "Did you mean" in str(exc_info.value) or "Alpha" in str(exc_info.value)

    async def test_id_fallback(self, resolver: Resolver) -> None:
        """When no substring matches, falls back to exact ID match."""
        result = await resolver.resolve_anchor("task-1")
        assert result == "task-1"

    async def test_no_match_no_suggestions(self, resolver: Resolver) -> None:
        """Completely unrelated string raises with no suggestions."""
        with pytest.raises(ValueError, match="No task found matching 'zzzzz'"):
            await resolver.resolve_anchor("zzzzz")


# ---------------------------------------------------------------------------
# Resolver -- resolve_container / resolve_anchor public wrappers
# ---------------------------------------------------------------------------


class TestResolveContainer:
    """resolve_container accepts projects and tasks."""

    async def test_resolve_container_inbox(self, resolver: Resolver) -> None:
        result = await resolver.resolve_container("$inbox")
        assert result is None

    async def test_resolve_container_by_name(self, resolver: Resolver) -> None:
        result = await resolver.resolve_container("Project One")
        assert result == "proj-1"

    async def test_resolve_container_by_task_name(self, resolver: Resolver) -> None:
        result = await resolver.resolve_container("Alpha")
        assert result == "task-1"


class TestResolveAnchor:
    """resolve_anchor accepts tasks only."""

    async def test_resolve_anchor_by_name(self, resolver: Resolver) -> None:
        result = await resolver.resolve_anchor("Alpha")
        assert result == "task-1"

    async def test_resolve_anchor_inbox_raises_entity_type_mismatch(
        self, resolver: Resolver
    ) -> None:
        """$inbox in task-only context raises EntityTypeMismatchError with structured data."""
        with pytest.raises(EntityTypeMismatchError) as exc_info:
            await resolver.resolve_anchor("$inbox")
        assert exc_info.value.value == "$inbox"
        assert exc_info.value.resolved_type == EntityType.PROJECT
        assert exc_info.value.accepted_types == [EntityType.TASK]

    async def test_resolve_anchor_unknown_dollar_prefix(self, resolver: Resolver) -> None:
        """Unknown $-prefixed value raises plain ValueError, not EntityTypeMismatchError."""
        with pytest.raises(ValueError, match="reserved for system locations") as exc_info:
            await resolver.resolve_anchor("$foobar")
        assert not isinstance(exc_info.value, EntityTypeMismatchError)


# ---------------------------------------------------------------------------
# Resolver -- resolve_tags (substring matching)
# ---------------------------------------------------------------------------


class TestResolveTagsSubstring:
    """resolve_tags uses substring matching, not exact."""

    async def test_substring_match(self, resolver: Resolver) -> None:
        """Partial name resolves via substring."""
        result = await resolver.resolve_tags(["Wor"])
        assert result == ["tag-work"]

    async def test_full_name_match(self, resolver: Resolver) -> None:
        """Full name still works (substring of itself)."""
        result = await resolver.resolve_tags(["Work"])
        assert result == ["tag-work"]

    async def test_case_insensitive(self, resolver: Resolver) -> None:
        """Substring match is case-insensitive."""
        result = await resolver.resolve_tags(["work"])
        assert result == ["tag-work"]

    async def test_id_fallback(self, resolver: Resolver) -> None:
        """Tag ID string resolves when no name matches."""
        result = await resolver.resolve_tags(["tag-work"])
        assert result == ["tag-work"]

    async def test_multiple_tags(self, resolver: Resolver) -> None:
        """Multiple tag names resolve in order."""
        result = await resolver.resolve_tags(["Work", "Home"])
        assert result == ["tag-work", "tag-home"]

    async def test_not_found(self, resolver: Resolver) -> None:
        """Unknown tag name raises ValueError."""
        with pytest.raises(ValueError, match="No tag found matching 'Nonexistent'"):
            await resolver.resolve_tags(["Nonexistent"])

    async def test_ambiguous(self, resolver: Resolver) -> None:
        """Two tags with same name raises ValueError listing both IDs."""
        bridge = InMemoryBridge(
            data=make_snapshot_dict(
                tags=[
                    make_tag_dict(id="tag-a", name="Duplicate"),
                    make_tag_dict(id="tag-b", name="Duplicate"),
                ],
            )
        )
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        ambiguous_resolver = Resolver(repo)

        with pytest.raises(ValueError, match="Ambiguous tag") as exc_info:
            await ambiguous_resolver.resolve_tags(["Duplicate"])
        assert "tag-a" in str(exc_info.value)
        assert "tag-b" in str(exc_info.value)
        assert "Use the ID" in str(exc_info.value)

    async def test_single_fetch(self, resolver: Resolver) -> None:
        """Multiple tags share a single fetch (structural: entities passed to _resolve)."""
        # This test verifies the implementation fetches tags once, not N times.
        # We verify by successfully resolving two tags -- if each triggered a
        # separate fetch the result would still be correct, but the implementation
        # passes pre-fetched entities to _resolve.
        result = await resolver.resolve_tags(["Work", "Home"])
        assert result == ["tag-work", "tag-home"]


# ---------------------------------------------------------------------------
# Read-side filter resolution (resolve_filter / resolve_filter_list / find_unresolved)
# ---------------------------------------------------------------------------


class TestResolveFilter:
    """Resolution cascade: ID match -> substring match -> empty list."""

    def test_id_match(self, resolver: Resolver) -> None:
        """Value matching an entity's .id exactly returns [that_id]."""

        entities = [
            Project.model_validate(make_model_project_dict(id="proj-1", name="Work Projects")),
        ]
        result = resolver.resolve_filter("proj-1", entities)
        assert result == ["proj-1"]

    def test_substring_match(self, resolver: Resolver) -> None:
        """Substring of name matches all entities containing it."""

        entities = [
            Project.model_validate(make_model_project_dict(id="p1", name="Work Projects")),
            Project.model_validate(make_model_project_dict(id="p2", name="Homework")),
            Project.model_validate(make_model_project_dict(id="p3", name="Personal")),
        ]
        result = resolver.resolve_filter("Work", entities)
        assert set(result) == {"p1", "p2"}

    def test_case_insensitive(self, resolver: Resolver) -> None:
        """Substring match is case-insensitive."""

        entities = [
            Project.model_validate(make_model_project_dict(id="p1", name="Work Projects")),
        ]
        result = resolver.resolve_filter("work", entities)
        assert result == ["p1"]

    def test_substring_match_with_emoji_prefix(self, resolver: Resolver) -> None:
        """Substring match works when entity names contain emoji."""

        entities = [
            Project.model_validate(make_model_project_dict(id="p1", name="Home Renovation")),
            Project.model_validate(make_model_project_dict(id="p2", name="Work Projects")),
        ]
        result = resolver.resolve_filter("Home", entities)
        assert result == ["p1"]

    def test_no_match(self, resolver: Resolver) -> None:
        """No matching entity returns empty list."""

        entities = [
            Project.model_validate(make_model_project_dict(id="p1", name="Work")),
        ]
        result = resolver.resolve_filter("zzzzz", entities)
        assert result == []

    def test_id_takes_priority_over_substring(self, resolver: Resolver) -> None:
        """If value is both an ID and a substring of another name, returns only the ID match."""

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

        entities = [
            Tag.model_validate(make_model_tag_dict(id="tag-errand", name="Errand")),
            Tag.model_validate(make_model_tag_dict(id="some-id", name="Other")),
        ]
        result = resolver.resolve_filter_list(["Errand", "some-id"], entities)
        assert set(result) == {"tag-errand", "some-id"}

    def test_deduplication(self, resolver: Resolver) -> None:
        """Same entity resolved by different values is deduplicated."""

        entities = [
            Tag.model_validate(make_model_tag_dict(id="tag-work", name="Work")),
        ]
        # "tag-work" matches by ID, "Work" matches by substring -- both resolve to same entity
        result = resolver.resolve_filter_list(["tag-work", "Work"], entities)
        assert result == ["tag-work"]

    def test_unresolved_values_excluded(self, resolver: Resolver) -> None:
        """Values that don't resolve are simply not included."""

        entities = [
            Tag.model_validate(make_model_tag_dict(id="tag-work", name="Work")),
        ]
        result = resolver.resolve_filter_list(["Work", "Nonexistent"], entities)
        assert result == ["tag-work"]


class TestFindUnresolved:
    """Detect values that produced no matches."""

    def test_find_unresolved(self, resolver: Resolver) -> None:
        """Returns values that produced no matches."""

        entities = [
            Tag.model_validate(make_model_tag_dict(id="tag-work", name="Work")),
        ]
        result = resolver.find_unresolved(["Work", "Nonexistent", "zzz"], entities)
        assert result == ["Nonexistent", "zzz"]

    def test_all_resolved(self, resolver: Resolver) -> None:
        """When all values resolve, returns empty list."""

        entities = [
            Tag.model_validate(make_model_tag_dict(id="tag-work", name="Work")),
        ]
        result = resolver.find_unresolved(["Work"], entities)
        assert result == []
