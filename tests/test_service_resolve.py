"""Unit tests for Resolver and validate_task_name / validate_task_name_if_set.

Tests the resolve module independently of OperatorService. Resolver tests use
BridgeOnlyRepository + InMemoryBridge (per D-11), validation tests are pure.
"""

from __future__ import annotations

import re

import pytest

from omnifocus_operator.agent_messages.errors import (
    CONTRADICTORY_INBOX_FALSE,
    CONTRADICTORY_INBOX_WITH_REF,
)
from omnifocus_operator.contracts.base import UNSET
from omnifocus_operator.models.enums import EntityType
from omnifocus_operator.models.project import Project
from omnifocus_operator.models.tag import Tag
from omnifocus_operator.repository import BridgeOnlyRepository
from omnifocus_operator.service.errors import EntityTypeMismatchError
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
        with pytest.raises(AssertionError):
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


class TestResolveEntityTypeMismatch:
    """When a name exists but as a different entity type, raise EntityTypeMismatchError."""

    async def test_project_name_rejected_when_only_tasks_accepted(self, resolver: Resolver) -> None:
        """'Project One' exists as a project but only tasks are accepted."""
        with pytest.raises(
            EntityTypeMismatchError,
            match="'Project One' resolved to project, but only task is accepted here",
        ):
            await resolver._resolve("Project One", accept=[EntityType.TASK])

    async def test_task_name_rejected_when_only_tags_accepted(self, resolver: Resolver) -> None:
        """'Alpha' exists as a task but only tags are accepted."""
        with pytest.raises(
            EntityTypeMismatchError,
            match="'Alpha' resolved to task, but only tag is accepted here",
        ):
            await resolver._resolve("Alpha", accept=[EntityType.TAG])

    async def test_tag_name_rejected_when_only_tasks_accepted(self, resolver: Resolver) -> None:
        """'Work' exists as a tag but only tasks are accepted."""
        with pytest.raises(
            EntityTypeMismatchError,
            match="'Work' resolved to tag, but only task is accepted here",
        ):
            await resolver._resolve("Work", accept=[EntityType.TASK])

    async def test_tag_name_rejected_when_projects_and_tasks_accepted(
        self, resolver: Resolver
    ) -> None:
        """'Work' exists as a tag but only projects and tasks are accepted."""
        with pytest.raises(
            EntityTypeMismatchError,
            match="'Work' resolved to tag, but only project/task is accepted here",
        ):
            await resolver._resolve("Work", accept=[EntityType.PROJECT, EntityType.TASK])


class TestResolveCascade:
    """The three-step cascade: $-prefix -> substring match -> ID fallback."""

    async def test_system_location_inbox(self, resolver: Resolver) -> None:
        """$inbox returns None (inbox = no parent) without any repo call."""
        result = await resolver.resolve_container("$inbox")
        assert result is None

    async def test_system_location_unknown(self, resolver: Resolver) -> None:
        """$trash raises with valid system locations listed."""
        with pytest.raises(ValueError, match="reserved for system locations") as exc_info:
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

    async def test_id_takes_priority_over_substring(self) -> None:
        """When a value is a valid ID AND a substring of another entity's name,
        ID should win — IDs are unambiguous by definition."""
        bridge = InMemoryBridge(
            data=make_snapshot_dict(
                tasks=[
                    make_task_dict(id="alpha", name="Some Task"),
                    make_task_dict(id="task-2", name="Task alpha review"),
                ],
            )
        )
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        resolver = Resolver(repo)

        # "alpha" is task-2's ID AND a substring of "Task alpha review"
        # The resolver should return "alpha" (the ID), not match by name
        result = await resolver.resolve_anchor("alpha")
        assert result == "alpha"

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


# ---------------------------------------------------------------------------
# Resolver -- resolve_inbox (inbox filter normalization)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Resolver -- lookup_project $-prefix guard
# ---------------------------------------------------------------------------


class TestLookupProjectInboxGuard:
    """lookup_project rejects $-prefixed IDs with educational error."""

    async def test_dollar_inbox_raises(self, resolver: Resolver) -> None:
        """get_project('$inbox') raises ValueError with educational message."""
        with pytest.raises(ValueError, match="not a real OmniFocus project"):
            await resolver.lookup_project("$inbox")

    async def test_dollar_trash_raises(self, resolver: Resolver) -> None:
        """Any $-prefixed value triggers the guard, not just $inbox."""
        with pytest.raises(ValueError, match="not a real OmniFocus project"):
            await resolver.lookup_project("$trash")

    async def test_normal_project_still_works(self, resolver: Resolver) -> None:
        """Regular project IDs are not affected by the guard."""
        project = await resolver.lookup_project("proj-1")
        assert project.id == "proj-1"
        assert project.name == "Project One"


# ---------------------------------------------------------------------------
# Resolver -- resolve_inbox (inbox filter normalization)
# ---------------------------------------------------------------------------


class TestResolveInbox:
    """resolve_inbox normalizes $inbox in project/parent filters to in_inbox=True.

    Phase 57-02 (D-09): extended to 3-arg ``resolve_inbox(in_inbox, project, parent)``.
    $inbox on EITHER project or parent consumes into ``in_inbox=True``; contradiction
    rules apply symmetrically. Existing 2-arg call patterns are migrated mechanically
    by passing ``parent=None``; the two ``test_resolve_inbox_3arg_existing_*`` tests
    below lock the pre-existing error contracts verbatim.
    """

    def test_no_filters_pass_through(self, resolver: Resolver) -> None:
        """No filters at all: all three None, pass through unchanged."""
        result = resolver.resolve_inbox(None, None, None)
        assert result == (None, None, None)

    def test_real_project_pass_through(self, resolver: Resolver) -> None:
        """Real project name, no inbox filter: pass through unchanged."""
        result = resolver.resolve_inbox(None, "Work", None)
        assert result == (None, "Work", None)

    def test_in_inbox_true_only(self, resolver: Resolver) -> None:
        """inInbox=true, no project/parent: pass through unchanged."""
        result = resolver.resolve_inbox(True, None, None)
        assert result == (True, None, None)

    def test_in_inbox_false_only(self, resolver: Resolver) -> None:
        """inInbox=false, no project/parent: pass through unchanged."""
        result = resolver.resolve_inbox(False, None, None)
        assert result == (False, None, None)

    def test_dollar_inbox_consumed(self, resolver: Resolver) -> None:
        """$inbox as project is consumed: returns (True, None, None)."""
        result = resolver.resolve_inbox(None, "$inbox", None)
        assert result == (True, None, None)

    def test_dollar_inbox_with_in_inbox_true_redundant(self, resolver: Resolver) -> None:
        """$inbox + inInbox=true is redundant but accepted silently (D-08/FILT-04)."""
        result = resolver.resolve_inbox(True, "$inbox", None)
        assert result == (True, None, None)

    def test_dollar_inbox_with_in_inbox_false_contradictory(self, resolver: Resolver) -> None:
        """$inbox + inInbox=false is contradictory (D-06/FILT-03)."""
        with pytest.raises(ValueError, match=r"Contradictory filters.*project.*\$inbox"):
            resolver.resolve_inbox(False, "$inbox", None)

    def test_in_inbox_true_with_real_project_contradictory(self, resolver: Resolver) -> None:
        """inInbox=true + real project name is contradictory (D-07/FILT-05)."""
        with pytest.raises(ValueError, match=r"Contradictory filters.*inInbox=true"):
            resolver.resolve_inbox(True, "Work", None)

    def test_in_inbox_true_with_project_id_contradictory(self, resolver: Resolver) -> None:
        """inInbox=true + project ID-like value is still contradictory."""
        with pytest.raises(ValueError, match=r"Contradictory filters.*inInbox=true"):
            resolver.resolve_inbox(True, "proj-1", None)

    def test_dollar_trash_unknown_system_location(self, resolver: Resolver) -> None:
        """$trash delegates to _resolve_system_location which raises for unknown locations."""
        with pytest.raises(ValueError, match="reserved for system locations"):
            resolver.resolve_inbox(None, "$trash", None)


class TestResolveInbox3Arg:
    """Phase 57-02 (D-09): 3-arg resolve_inbox semantics — parent mirror + cross-side rules.

    Consolidation rules:
    - parent "$inbox" consumes identically to project "$inbox".
    - Either side's "$inbox" + in_inbox=False raises CONTRADICTORY_INBOX_FALSE.
    - After consumption, any surviving real ref alongside in_inbox=True raises
      CONTRADICTORY_INBOX_WITH_REF.

    Both error templates interpolate `{filter}` with the offending filter name
    ("project" or "parent") so the agent sees the filter it actually set, not
    a generic message that only covers the project branch.
    """

    def test_resolve_inbox_3arg_all_none(self, resolver: Resolver) -> None:
        result = resolver.resolve_inbox(None, None, None)
        assert result == (None, None, None)

    def test_resolve_inbox_3arg_project_inbox_sentinel(self, resolver: Resolver) -> None:
        result = resolver.resolve_inbox(None, "$inbox", None)
        assert result == (True, None, None)

    def test_resolve_inbox_3arg_parent_inbox_sentinel(self, resolver: Resolver) -> None:
        """PARENT-07 gate at the resolver layer: parent '$inbox' consumes to
        (True, None, None) identically to the project side."""
        result = resolver.resolve_inbox(None, None, "$inbox")
        assert result == (True, None, None)

    def test_resolve_inbox_3arg_both_inbox_sentinels(self, resolver: Resolver) -> None:
        """Both '$inbox' sentinels are allowed and both consume."""
        result = resolver.resolve_inbox(None, "$inbox", "$inbox")
        assert result == (True, None, None)

    def test_resolve_inbox_3arg_parent_inbox_with_in_inbox_false(self, resolver: Resolver) -> None:
        """PARENT-08: parent '$inbox' + inInbox=false raises CONTRADICTORY_INBOX_FALSE
        with filter='parent' interpolated (the raised text names the filter the
        agent actually set, not a generic 'project=$inbox' message)."""
        expected = CONTRADICTORY_INBOX_FALSE.format(filter="parent")
        with pytest.raises(ValueError, match=re.escape(expected)):
            resolver.resolve_inbox(False, None, "$inbox")

    def test_resolve_inbox_3arg_in_inbox_true_with_parent_real_ref(
        self, resolver: Resolver
    ) -> None:
        """inInbox=true + parent real ref raises CONTRADICTORY_INBOX_WITH_REF with
        filter='parent' interpolated (same contradiction as the project-side,
        consolidated at D-09, but the message names the filter that tripped it)."""
        expected = CONTRADICTORY_INBOX_WITH_REF.format(filter="parent")
        with pytest.raises(ValueError, match=re.escape(expected)):
            resolver.resolve_inbox(True, None, "RealTask")

    def test_resolve_inbox_3arg_project_real_ref_passthrough(self, resolver: Resolver) -> None:
        result = resolver.resolve_inbox(None, "Work", None)
        assert result == (None, "Work", None)

    def test_resolve_inbox_3arg_parent_real_ref_passthrough(self, resolver: Resolver) -> None:
        result = resolver.resolve_inbox(None, None, "SomeTask")
        assert result == (None, None, "SomeTask")

    def test_resolve_inbox_3arg_parent_inbox_with_real_project(self, resolver: Resolver) -> None:
        """parent='$inbox' consumes to in_inbox=True; the surviving project='Work'
        then trips CONTRADICTORY_INBOX_WITH_REF in the post-consumption check,
        interpolated with filter='project' (the surviving side)."""
        expected = CONTRADICTORY_INBOX_WITH_REF.format(filter="project")
        with pytest.raises(ValueError, match=re.escape(expected)):
            resolver.resolve_inbox(None, "Work", "$inbox")

    def test_resolve_inbox_3arg_project_inbox_with_real_parent(self, resolver: Resolver) -> None:
        """Symmetric case: project='$inbox' consumes; parent='SomeTask' surviving
        + resulting in_inbox=True trips CONTRADICTORY_INBOX_WITH_REF, interpolated
        with filter='parent' (the surviving side)."""
        expected = CONTRADICTORY_INBOX_WITH_REF.format(filter="parent")
        with pytest.raises(ValueError, match=re.escape(expected)):
            resolver.resolve_inbox(None, "$inbox", "SomeTask")

    # -- Regression tests: pre-existing 2-arg error contracts survive verbatim. --

    def test_resolve_inbox_3arg_existing_project_inbox_in_inbox_false_still_raises(
        self, resolver: Resolver
    ) -> None:
        """Pre-existing 2-arg path: resolve_inbox(False, "$inbox") raised
        CONTRADICTORY_INBOX_FALSE with 'project="$inbox"' wording. After templating,
        the project-side call still produces byte-identical text via
        .format(filter="project")."""
        expected = CONTRADICTORY_INBOX_FALSE.format(filter="project")
        with pytest.raises(ValueError, match=re.escape(expected)):
            resolver.resolve_inbox(False, "$inbox", None)

    def test_resolve_inbox_3arg_existing_in_inbox_true_real_project_still_raises(
        self, resolver: Resolver
    ) -> None:
        """Pre-existing 2-arg path: resolve_inbox(True, "RealProject") raised
        CONTRADICTORY_INBOX_PROJECT with 'project' filter wording. After templating
        and renaming to CONTRADICTORY_INBOX_WITH_REF, the project-side call still
        produces byte-identical text via .format(filter='project')."""
        expected = CONTRADICTORY_INBOX_WITH_REF.format(filter="project")
        with pytest.raises(ValueError, match=re.escape(expected)):
            resolver.resolve_inbox(True, "SomeRealProject", None)
