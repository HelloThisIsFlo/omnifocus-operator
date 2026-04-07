"""Integration tests for list pipelines and pass-throughs.

Tests the OperatorService public API for all 5 list methods:
- list_tasks: name-to-ID resolution for project and tag filters
- list_projects: name-to-ID resolution for folder filter
- list_tags: inline pass-through
- list_folders: inline pass-through
- list_perspectives: inline pass-through

Uses InMemoryBridge (per SAFE-01) via the conftest fixture chain.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from omnifocus_operator.contracts.base import UNSET
from omnifocus_operator.contracts.use_cases.list._enums import (
    AvailabilityFilter,
    FolderAvailabilityFilter,
    TagAvailabilityFilter,
)
from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersQuery
from omnifocus_operator.contracts.use_cases.list.perspectives import ListPerspectivesQuery
from omnifocus_operator.contracts.use_cases.list.projects import (
    DurationUnit,
    ListProjectsQuery,
    ReviewDueFilter,
)
from omnifocus_operator.contracts.use_cases.list.tags import ListTagsQuery
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksQuery
from omnifocus_operator.service.service import _ListProjectsPipeline, matches_inbox_name

from .conftest import (
    make_folder_dict,
    make_perspective_dict,
    make_project_dict,
    make_tag_dict,
    make_task_dict,
)

if TYPE_CHECKING:
    from omnifocus_operator.service import OperatorService


# ---------------------------------------------------------------------------
# list_tasks: name resolution
# ---------------------------------------------------------------------------


class TestListTasksResolution:
    """Pipeline resolves project and tag names to IDs before repo call."""

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Task in Work", project="proj-work"),
            make_task_dict(id="t2", name="Task in Home", project="proj-home"),
            make_task_dict(id="t3", name="Inbox task"),
        ],
        projects=[
            make_project_dict(id="proj-work", name="Work Projects"),
            make_project_dict(id="proj-home", name="Home"),
        ],
        tags=[make_tag_dict(id="tag-1", name="Errand")],
        folders=[],
        perspectives=[],
    )
    async def test_resolves_project_name_to_ids(self, service: OperatorService) -> None:
        """Pass project='Work', verify results contain tasks from matching projects."""
        result = await service.list_tasks(ListTasksQuery(project="Work"))
        task_ids = {t.id for t in result.items}
        # "Work" is substring of "Work Projects" -> proj-work matches
        assert "t1" in task_ids
        assert "t3" not in task_ids  # inbox task has no parent

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t1", name="Errand task", tags=[{"id": "tag-errand", "name": "Errand"}]
            ),
            make_task_dict(id="t2", name="No tags"),
        ],
        projects=[],
        tags=[make_tag_dict(id="tag-errand", name="Errand")],
        folders=[],
        perspectives=[],
    )
    async def test_resolves_tag_names_to_ids(self, service: OperatorService) -> None:
        """Pass tags=['Errand'], verify filtered results."""
        result = await service.list_tasks(ListTasksQuery(tags=["Errand"]))
        task_ids = {t.id for t in result.items}
        assert "t1" in task_ids
        assert "t2" not in task_ids

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Task in proj", project="proj-work"),
        ],
        projects=[
            make_project_dict(id="proj-work", name="Work"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_id_match_takes_priority(self, service: OperatorService) -> None:
        """Pass project='proj-work' (an actual ID), verify resolves as ID not substring."""
        result = await service.list_tasks(ListTasksQuery(project="proj-work"))
        assert len(result.items) == 1
        assert result.items[0].id == "t1"

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Task A"),
            make_task_dict(id="t2", name="Task B"),
        ],
        projects=[
            make_project_dict(id="proj-1", name="Real Project"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_unresolved_project_skips_filter_with_warning(
        self, service: OperatorService
    ) -> None:
        """Pass project='Nonexistent', verify all tasks returned + warning."""
        result = await service.list_tasks(ListTasksQuery(project="Nonexistent"))
        # Filter was skipped -> all tasks returned
        assert len(result.items) == 2
        assert result.warnings is not None
        assert len(result.warnings) == 1
        assert "Nonexistent" in result.warnings[0]
        assert "skipped" in result.warnings[0].lower()

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Task A"),
        ],
        projects=[
            make_project_dict(id="proj-1", name="Personal"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_did_you_mean_warning(self, service: OperatorService) -> None:
        """Pass project='Personl' when 'Personal' exists, verify did-you-mean."""
        result = await service.list_tasks(ListTasksQuery(project="Personl"))
        assert result.warnings is not None
        assert any("Did you mean" in w for w in result.warnings)
        assert any("Personal" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Task in Work", project="proj-work"),
            make_task_dict(id="t2", name="Task in Homework", project="proj-homework"),
            make_task_dict(id="t3", name="Inbox task"),
        ],
        projects=[
            make_project_dict(id="proj-work", name="Work Projects"),
            make_project_dict(id="proj-homework", name="Homework"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_project_multi_match_warns(self, service: OperatorService) -> None:
        """Project filter matching 2 projects emits multi-match warning with names and IDs."""
        result = await service.list_tasks(ListTasksQuery(project="Work"))
        # Both projects match "Work" as substring
        task_ids = {t.id for t in result.items}
        assert "t1" in task_ids
        assert "t2" in task_ids
        # Warning should include both project names and IDs
        assert result.warnings is not None
        assert any("proj-work" in w and "proj-homework" in w for w in result.warnings)
        assert any("filter by ID" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Work task", tags=[{"id": "tag-work", "name": "Work"}]),
            make_task_dict(
                id="t2", name="Homework task", tags=[{"id": "tag-homework", "name": "Homework"}]
            ),
        ],
        projects=[],
        tags=[
            make_tag_dict(id="tag-work", name="Work"),
            make_tag_dict(id="tag-homework", name="Homework"),
        ],
        folders=[],
        perspectives=[],
    )
    async def test_tag_multi_match_warns(self, service: OperatorService) -> None:
        """Tag filter value matching 2 tags emits per-value multi-match warning."""
        result = await service.list_tasks(ListTasksQuery(tags=["Work"]))
        # "Work" is substring of both "Work" and "Homework"
        task_ids = {t.id for t in result.items}
        assert "t1" in task_ids
        assert "t2" in task_ids
        # Warning for the "Work" value matching multiple tags
        assert result.warnings is not None
        assert any("tag-work" in w and "tag-homework" in w for w in result.warnings)
        assert any("filter by ID" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Task in Work", project="proj-work"),
        ],
        projects=[
            make_project_dict(id="proj-work", name="Work Projects"),
            make_project_dict(id="proj-home", name="Home"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_single_match_no_multi_match_warning(self, service: OperatorService) -> None:
        """Single match produces no multi-match warning (no regression)."""
        result = await service.list_tasks(ListTasksQuery(project="Home"))
        assert result.warnings is None


# ---------------------------------------------------------------------------
# list_projects: name resolution
# ---------------------------------------------------------------------------


class TestListTasksInboxFilter:
    """Pipeline handles $inbox in project filter and contradictory inbox combinations."""

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-inbox-1", name="Inbox task A"),
            make_task_dict(id="t-inbox-2", name="Inbox task B"),
            make_task_dict(id="t-proj", name="Project task", project="proj-work"),
        ],
        projects=[
            make_project_dict(id="proj-work", name="Work Projects"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_dollar_inbox_returns_inbox_tasks(self, service: OperatorService) -> None:
        """project='$inbox' returns the same tasks as inInbox=true (FILT-01)."""
        result_dollar = await service.list_tasks(ListTasksQuery(project="$inbox"))
        result_flag = await service.list_tasks(ListTasksQuery(in_inbox=True))
        assert {t.id for t in result_dollar.items} == {t.id for t in result_flag.items}
        assert {t.id for t in result_dollar.items} == {"t-inbox-1", "t-inbox-2"}

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-inbox", name="Inbox task"),
            make_task_dict(id="t-proj", name="Project task", project="proj-inbox"),
        ],
        projects=[
            make_project_dict(id="proj-inbox", name="My Inbox Tasks"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_bare_inbox_matches_project_name_not_system(
        self, service: OperatorService
    ) -> None:
        """project='inbox' (no $) matches real projects, NOT system inbox (FILT-02)."""
        result = await service.list_tasks(ListTasksQuery(project="inbox"))
        task_ids = {t.id for t in result.items}
        # Should match "My Inbox Tasks" project (substring)
        assert "t-proj" in task_ids
        # Should NOT include inbox tasks (those have no project)
        assert "t-inbox" not in task_ids

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Task")],
        projects=[],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_dollar_inbox_with_in_inbox_false_raises(self, service: OperatorService) -> None:
        """project='$inbox' + inInbox=false raises ValueError (FILT-03)."""
        with pytest.raises(ValueError, match="Contradictory"):
            await service.list_tasks(ListTasksQuery(project="$inbox", in_inbox=False))

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-inbox", name="Inbox task"),
            make_task_dict(id="t-proj", name="Project task", project="proj-1"),
        ],
        projects=[
            make_project_dict(id="proj-1", name="Work"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_dollar_inbox_with_in_inbox_true_redundant(
        self, service: OperatorService
    ) -> None:
        """project='$inbox' + inInbox=true returns inbox tasks (redundant accepted, FILT-04)."""
        result = await service.list_tasks(ListTasksQuery(project="$inbox", in_inbox=True))
        task_ids = {t.id for t in result.items}
        assert "t-inbox" in task_ids
        assert "t-proj" not in task_ids

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Task")],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_in_inbox_true_with_project_raises(self, service: OperatorService) -> None:
        """inInbox=true + project='Work' raises ValueError (FILT-05)."""
        with pytest.raises(ValueError, match="Contradictory"):
            await service.list_tasks(ListTasksQuery(in_inbox=True, project="Work"))

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-inbox", name="Inbox task"),
        ],
        projects=[],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_dollar_inbox_no_unresolved_warning(self, service: OperatorService) -> None:
        """project='$inbox' does not trigger 'filter not resolved' warnings."""
        result = await service.list_tasks(ListTasksQuery(project="$inbox"))
        assert result.warnings is None


class TestListTasksInboxProjectWarning:
    """list_tasks warns when project filter matches the inbox name."""

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-proj", name="Project task", project="proj-inbox"),
        ],
        projects=[
            make_project_dict(id="proj-inbox", name="My Inbox Tasks"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_project_inbox_warns(self, service: OperatorService) -> None:
        """project='inbox' triggers inbox project warning."""
        result = await service.list_tasks(ListTasksQuery(project="inbox"))
        assert result.warnings is not None
        assert any("Inbox is a virtual location" in w for w in result.warnings)
        assert any('project="inbox"' in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-proj", name="Project task", project="proj-inbox"),
        ],
        projects=[
            make_project_dict(id="proj-inbox", name="My Inbox Tasks"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_project_inbox_case_insensitive(self, service: OperatorService) -> None:
        """project='INBOX' (uppercase) also triggers warning."""
        result = await service.list_tasks(ListTasksQuery(project="INBOX"))
        assert result.warnings is not None
        assert any("Inbox is a virtual location" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-proj", name="Project task", project="proj-inbox"),
        ],
        projects=[
            make_project_dict(id="proj-inbox", name="My Inbox Tasks"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_project_inb_substring_warns(self, service: OperatorService) -> None:
        """project='inb' (substring of Inbox) triggers warning."""
        result = await service.list_tasks(ListTasksQuery(project="inb"))
        assert result.warnings is not None
        assert any("Inbox is a virtual location" in w for w in result.warnings)
        assert any('project="inb"' in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-proj", name="Project task", project="proj-work"),
        ],
        projects=[
            make_project_dict(id="proj-work", name="Work Projects"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_project_work_no_warning(self, service: OperatorService) -> None:
        """project='Work' does NOT trigger inbox warning."""
        result = await service.list_tasks(ListTasksQuery(project="Work"))
        inbox_warnings = [w for w in (result.warnings or []) if "Inbox is a virtual location" in w]
        assert inbox_warnings == []

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-inbox", name="Inbox task"),
        ],
        projects=[],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_dollar_inbox_no_inbox_project_warning(self, service: OperatorService) -> None:
        """project='$inbox' does NOT trigger the inbox project warning (already consumed)."""
        result = await service.list_tasks(ListTasksQuery(project="$inbox"))
        inbox_warnings = [w for w in (result.warnings or []) if "Inbox is a virtual location" in w]
        assert inbox_warnings == []


class TestListProjectsResolution:
    """Pipeline resolves folder names to IDs before repo call."""

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(id="proj-1", name="Work Project", folder="folder-home"),
            make_project_dict(id="proj-2", name="Other Project"),
        ],
        tags=[],
        folders=[
            make_folder_dict(id="folder-home", name="Home"),
        ],
        perspectives=[],
    )
    async def test_resolves_folder_name_to_ids(self, service: OperatorService) -> None:
        """Pass folder='Home', verify filtered results."""
        result = await service.list_projects(ListProjectsQuery(folder="Home"))
        proj_ids = {p.id for p in result.items}
        assert "proj-1" in proj_ids
        assert "proj-2" not in proj_ids

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(id="proj-1", name="Work Project"),
        ],
        tags=[],
        folders=[
            make_folder_dict(id="folder-1", name="Real Folder"),
        ],
        perspectives=[],
    )
    async def test_unresolved_folder_warns(self, service: OperatorService) -> None:
        """Pass folder='Nonexistent', verify warning."""
        result = await service.list_projects(ListProjectsQuery(folder="Nonexistent"))
        assert result.warnings is not None
        assert len(result.warnings) == 1
        assert "Nonexistent" in result.warnings[0]

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(id="proj-1", name="Work Project", folder="folder-home"),
            make_project_dict(id="proj-2", name="Other Project", folder="folder-homework"),
        ],
        tags=[],
        folders=[
            make_folder_dict(id="folder-home", name="Home"),
            make_folder_dict(id="folder-homework", name="Homework"),
        ],
        perspectives=[],
    )
    async def test_folder_multi_match_warns(self, service: OperatorService) -> None:
        """Folder filter matching 2 folders emits multi-match warning."""
        result = await service.list_projects(ListProjectsQuery(folder="Home"))
        # "Home" matches both "Home" and "Homework"
        proj_ids = {p.id for p in result.items}
        assert "proj-1" in proj_ids
        assert "proj-2" in proj_ids
        # Warning should include both folder names and IDs
        assert result.warnings is not None
        assert any("folder-home" in w and "folder-homework" in w for w in result.warnings)
        assert any("filter by ID" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# list_projects: inbox search warning
# ---------------------------------------------------------------------------


class TestListProjectsInboxWarning:
    """list_projects warns when search term matches system inbox name."""

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(id="proj-1", name="Work Project"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_search_inbox_warns(self, service: OperatorService) -> None:
        """search='Inbox' triggers inbox warning."""
        result = await service.list_projects(ListProjectsQuery(search="Inbox"))
        assert result.warnings is not None
        assert any("not a real OmniFocus project" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(id="proj-1", name="Work Project"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_search_inbox_case_insensitive(self, service: OperatorService) -> None:
        """search='inbox' (lowercase) also triggers warning."""
        result = await service.list_projects(ListProjectsQuery(search="inbox"))
        assert result.warnings is not None
        assert any("not a real OmniFocus project" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(id="proj-1", name="Work Project"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_search_work_no_warning(self, service: OperatorService) -> None:
        """search='Work' does NOT trigger inbox warning."""
        result = await service.list_projects(ListProjectsQuery(search="Work"))
        assert result.warnings is None

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(id="proj-1", name="Work Project"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_search_none_no_warning(self, service: OperatorService) -> None:
        """search=None does NOT trigger inbox warning."""
        result = await service.list_projects(ListProjectsQuery())
        assert result.warnings is None

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(id="proj-1", name="Work Project"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_search_in_substring_warns(self, service: OperatorService) -> None:
        """search='in' is substring of 'Inbox', triggers warning."""
        result = await service.list_projects(ListProjectsQuery(search="in"))
        assert result.warnings is not None
        assert any("not a real OmniFocus project" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Pass-throughs: tags, folders, perspectives
# ---------------------------------------------------------------------------


class TestListPassThroughs:
    """Inline pass-throughs for entities without entity-reference filters."""

    @pytest.mark.snapshot(
        tasks=[],
        projects=[],
        tags=[
            make_tag_dict(id="tag-1", name="Work"),
            make_tag_dict(id="tag-2", name="Home"),
        ],
        folders=[],
        perspectives=[],
    )
    async def test_list_tags(self, service: OperatorService) -> None:
        """list_tags returns tags from repository."""
        result = await service.list_tags(ListTagsQuery())
        assert len(result.items) == 2
        tag_names = {t.name for t in result.items}
        assert "Work" in tag_names
        assert "Home" in tag_names

    @pytest.mark.snapshot(
        tasks=[],
        projects=[],
        tags=[],
        folders=[
            make_folder_dict(id="f1", name="Personal"),
            make_folder_dict(id="f2", name="Work"),
        ],
        perspectives=[],
    )
    async def test_list_folders(self, service: OperatorService) -> None:
        """list_folders returns folders from repository."""
        result = await service.list_folders(ListFoldersQuery())
        assert len(result.items) == 2
        folder_names = {f.name for f in result.items}
        assert "Personal" in folder_names

    @pytest.mark.snapshot(
        tasks=[],
        projects=[],
        tags=[],
        folders=[],
        perspectives=[
            make_perspective_dict(id="p1", name="Inbox"),
            make_perspective_dict(id="p2", name="Projects"),
        ],
    )
    async def test_list_perspectives(self, service: OperatorService) -> None:
        """list_perspectives returns perspectives from repository."""
        result = await service.list_perspectives(ListPerspectivesQuery())
        assert len(result.items) == 2
        persp_names = {p.name for p in result.items}
        assert "Inbox" in persp_names


# ---------------------------------------------------------------------------
# No NotImplementedError
# ---------------------------------------------------------------------------


class TestNoNotImplementedError:
    """All 5 list methods are callable without NotImplementedError."""

    async def test_list_tasks_callable(self, service: OperatorService) -> None:
        result = await service.list_tasks(ListTasksQuery())
        assert result is not None

    async def test_list_projects_callable(self, service: OperatorService) -> None:
        result = await service.list_projects(ListProjectsQuery())
        assert result is not None

    async def test_list_tags_callable(self, service: OperatorService) -> None:
        result = await service.list_tags(ListTagsQuery())
        assert result is not None

    async def test_list_folders_callable(self, service: OperatorService) -> None:
        result = await service.list_folders(ListFoldersQuery())
        assert result is not None

    async def test_list_perspectives_callable(self, service: OperatorService) -> None:
        result = await service.list_perspectives(ListPerspectivesQuery())
        assert result is not None


# ---------------------------------------------------------------------------
# ReviewDueFilter pipeline expansion
# ---------------------------------------------------------------------------


class TestReviewDueFilterExpansion:
    """Verify _ListProjectsPipeline expands ReviewDueFilter to datetime."""

    def test_expand_review_due_1w(self) -> None:
        """1w -> now + 7 days."""

        f = ReviewDueFilter(amount=1, unit=DurationUnit.WEEKS)
        result = _ListProjectsPipeline._expand_review_due(f)
        expected = datetime.now(UTC) + timedelta(weeks=1)
        assert abs((result - expected).total_seconds()) < 2

    def test_expand_review_due_now(self) -> None:
        """'now' -> approximately current time."""

        f = ReviewDueFilter(amount=None, unit=None)
        result = _ListProjectsPipeline._expand_review_due(f)
        now = datetime.now(UTC)
        assert abs((result - now).total_seconds()) < 2

    def test_expand_review_due_30d(self) -> None:
        """30d -> now + 30 days."""

        f = ReviewDueFilter(amount=30, unit=DurationUnit.DAYS)
        result = _ListProjectsPipeline._expand_review_due(f)
        expected = datetime.now(UTC) + timedelta(days=30)
        assert abs((result - expected).total_seconds()) < 2

    def test_expand_review_due_2m(self) -> None:
        """2m -> now + 2 months (calendar arithmetic)."""

        f = ReviewDueFilter(amount=2, unit=DurationUnit.MONTHS)
        result = _ListProjectsPipeline._expand_review_due(f)
        # Should be roughly 60 days from now
        assert result > datetime.now(UTC) + timedelta(days=50)
        assert result < datetime.now(UTC) + timedelta(days=70)

    def test_expand_review_due_1y(self) -> None:
        """1y -> now + 1 year."""

        f = ReviewDueFilter(amount=1, unit=DurationUnit.YEARS)
        result = _ListProjectsPipeline._expand_review_due(f)
        assert result > datetime.now(UTC) + timedelta(days=360)
        assert result < datetime.now(UTC) + timedelta(days=370)

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(id="proj-1", name="Review Soon"),
            make_project_dict(id="proj-2", name="No Review"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_pipeline_filters_by_review_due(self, service: OperatorService) -> None:
        """Full pipeline test: review_due_within='1y' includes projects with past review dates."""
        # Default nextReviewDate is 2024-01-17, which is in the past.
        # "1y" expands to ~now + 1 year, so projects with past review dates should match.
        result = await service.list_projects(ListProjectsQuery(review_due_within="1y"))
        proj_ids = {p.id for p in result.items}
        assert "proj-1" in proj_ids
        assert "proj-2" in proj_ids

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(id="proj-1", name="Review Soon"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_pipeline_none_review_due_passes_through(self, service: OperatorService) -> None:
        """No review_due_within -> no filtering by review date."""
        result = await service.list_projects(ListProjectsQuery())
        assert len(result.items) == 1


# ---------------------------------------------------------------------------
# matches_inbox_name: UNSET handling
# ---------------------------------------------------------------------------


class TestMatchesInboxName:
    """matches_inbox_name handles UNSET, None, and str correctly."""

    def test_unset_returns_false(self) -> None:
        assert matches_inbox_name(UNSET) is False

    def test_none_returns_false(self) -> None:

        assert matches_inbox_name(None) is False

    def test_inbox_string_returns_true(self) -> None:

        assert matches_inbox_name("inbox") is True

    def test_work_string_returns_false(self) -> None:

        assert matches_inbox_name("work") is False

    def test_int_returns_false(self) -> None:

        assert matches_inbox_name(42) is False


# ---------------------------------------------------------------------------
# Availability expansion: ALL -> full core enum list
# ---------------------------------------------------------------------------


class TestAvailabilityExpansion:
    """Pipeline expands AvailabilityFilter.ALL to all core Availability values."""

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-avail", name="Available task"),
            make_task_dict(id="t-dropped", name="Dropped task"),
        ],
        projects=[],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_tasks_all_returns_all_statuses(self, service: OperatorService) -> None:
        """availability=['ALL'] expands to all core Availability values."""

        result = await service.list_tasks(ListTasksQuery(availability=[AvailabilityFilter.ALL]))
        # Should return all tasks regardless of status
        assert len(result.items) >= 1
        assert result.warnings is None  # No mixed-ALL warning

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Task"),
        ],
        projects=[],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_tasks_mixed_all_warns(self, service: OperatorService) -> None:
        """availability=['ALL', 'available'] expands and adds warning."""

        result = await service.list_tasks(
            ListTasksQuery(availability=[AvailabilityFilter.ALL, AvailabilityFilter.AVAILABLE])
        )
        assert result.warnings is not None
        assert any("no other values are needed" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(id="proj-1", name="Project"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_projects_all_returns_all_statuses(self, service: OperatorService) -> None:
        """list_projects with availability=['ALL'] expands correctly."""

        result = await service.list_projects(
            ListProjectsQuery(availability=[AvailabilityFilter.ALL])
        )
        assert len(result.items) >= 1
        assert result.warnings is None

    @pytest.mark.snapshot(
        tasks=[],
        projects=[],
        tags=[
            make_tag_dict(id="tag-1", name="Tag"),
        ],
        folders=[],
        perspectives=[],
    )
    async def test_tags_all_returns_all_statuses(self, service: OperatorService) -> None:
        """list_tags with availability=['ALL'] expands correctly."""

        result = await service.list_tags(ListTagsQuery(availability=[TagAvailabilityFilter.ALL]))
        assert len(result.items) >= 1
        assert result.warnings is None

    @pytest.mark.snapshot(
        tasks=[],
        projects=[],
        tags=[],
        folders=[
            make_folder_dict(id="f1", name="Folder"),
        ],
        perspectives=[],
    )
    async def test_folders_all_returns_all_statuses(self, service: OperatorService) -> None:
        """list_folders with availability=['ALL'] expands correctly."""

        result = await service.list_folders(
            ListFoldersQuery(availability=[FolderAvailabilityFilter.ALL])
        )
        assert len(result.items) >= 1
        assert result.warnings is None

    @pytest.mark.snapshot(
        tasks=[],
        projects=[],
        tags=[
            make_tag_dict(id="tag-1", name="Tag"),
        ],
        folders=[],
        perspectives=[],
    )
    async def test_tags_mixed_all_warns(self, service: OperatorService) -> None:
        """list_tags with mixed ALL adds warning."""

        result = await service.list_tags(
            ListTagsQuery(availability=[TagAvailabilityFilter.ALL, TagAvailabilityFilter.AVAILABLE])
        )
        assert result.warnings is not None
        assert any("no other values are needed" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[],
        projects=[],
        tags=[],
        folders=[
            make_folder_dict(id="f1", name="Folder"),
        ],
        perspectives=[],
    )
    async def test_folders_mixed_all_warns(self, service: OperatorService) -> None:
        """list_folders with mixed ALL adds warning."""

        result = await service.list_folders(
            ListFoldersQuery(
                availability=[FolderAvailabilityFilter.ALL, FolderAvailabilityFilter.AVAILABLE]
            )
        )
        assert result.warnings is not None
        assert any("no other values are needed" in w for w in result.warnings)
