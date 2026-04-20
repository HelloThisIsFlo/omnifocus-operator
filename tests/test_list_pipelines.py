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

from omnifocus_operator.agent_messages.warnings import (
    FILTERED_SUBTREE_WARNING,
    PARENT_PROJECT_COMBINED_WARNING,
)
from omnifocus_operator.contracts.base import UNSET
from omnifocus_operator.contracts.use_cases.list._enums import (
    AvailabilityFilter,
    FolderAvailabilityFilter,
    TagAvailabilityFilter,
)
from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersQuery
from omnifocus_operator.contracts.use_cases.list.perspectives import ListPerspectivesQuery
from omnifocus_operator.contracts.use_cases.list.projects import (
    ListProjectsQuery,
)
from omnifocus_operator.contracts.use_cases.list.tags import ListTagsQuery
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksQuery, ListTasksRepoQuery
from omnifocus_operator.models.enums import Availability
from omnifocus_operator.service.service import matches_inbox_name

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
# list_tasks: true inheritance walk
# ---------------------------------------------------------------------------


class TestListTasksTrueInheritance:
    """list_tasks applies true inheritance walk -- self-echoed inherited fields stripped."""

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t1",
                name="Self-echo task",
                flagged=True,
                effectiveFlagged=True,
                dueDate=None,
                effectiveDueDate=None,
                project="proj-1",
                parent="proj-1",
            ),
        ],
        projects=[
            make_project_dict(id="proj-1", name="Proj", flagged=False),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_strips_self_echoed_inherited(self, service: OperatorService) -> None:
        """list_tasks applies true inheritance walk in pipeline."""
        result = await service.list_tasks(ListTasksQuery())
        assert len(result.items) == 1
        task = result.items[0]
        # Task has flagged=True but no ancestor sets flagged -> inherited_flagged=False
        assert task.inherited_flagged is False


# ---------------------------------------------------------------------------
# list_tasks: inbox filter
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
    """Verify review_due_within pipeline integration (unit tests in test_service_domain.py)."""

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
    """Pipeline expands AvailabilityFilter.REMAINING to AVAILABLE + BLOCKED."""

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-avail", name="Available task"),
            make_task_dict(id="t-blocked", name="Blocked task"),
        ],
        projects=[],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_tasks_remaining_returns_active_statuses(self, service: OperatorService) -> None:
        """availability=['remaining'] expands to AVAILABLE + BLOCKED."""

        result = await service.list_tasks(
            ListTasksQuery(availability=[AvailabilityFilter.REMAINING])
        )
        assert len(result.items) >= 1
        assert result.warnings is None  # No redundancy warning

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Task"),
        ],
        projects=[],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_tasks_mixed_remaining_warns(self, service: OperatorService) -> None:
        """availability=['remaining', 'available'] expands and adds redundancy warning."""

        result = await service.list_tasks(
            ListTasksQuery(
                availability=[AvailabilityFilter.REMAINING, AvailabilityFilter.AVAILABLE]
            )
        )
        assert result.warnings is not None
        assert any("already includes" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(id="proj-1", name="Project"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_projects_remaining_returns_active_statuses(
        self, service: OperatorService
    ) -> None:
        """list_projects with availability=['remaining'] expands correctly."""

        result = await service.list_projects(
            ListProjectsQuery(availability=[AvailabilityFilter.REMAINING])
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
        assert any("already includes every status" in w for w in result.warnings)

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
        assert any("already includes every status" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# list_tasks: date filtering (bridge path)
# ---------------------------------------------------------------------------


class TestListTasksDateFiltering:
    """Bridge path filters tasks by date using resolved datetime bounds."""

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-due-soon",
                name="Due soon",
                effectiveDueDate="2026-04-08T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-due-later",
                name="Due later",
                effectiveDueDate="2026-04-20T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-no-due",
                name="No due date",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_due_before_filters_and_excludes_null(self, service: OperatorService) -> None:
        """Tasks with effectiveDueDate before the boundary are included; None excluded."""

        repo = service._repository
        q = ListTasksRepoQuery(
            due_before=datetime(2026, 4, 15, 0, 0, 0, tzinfo=UTC),
            availability=list(Availability),
        )
        result = await repo.list_tasks(q)
        task_ids = {t.id for t in result.items}
        assert "t-due-soon" in task_ids  # 2026-04-08 < 2026-04-15
        assert "t-due-later" not in task_ids  # 2026-04-20 >= 2026-04-15
        assert "t-no-due" not in task_ids  # None excluded

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-due-early",
                name="Due early",
                effectiveDueDate="2026-04-01T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-due-late",
                name="Due late",
                effectiveDueDate="2026-04-20T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-no-due",
                name="No due date",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_due_after_includes_and_excludes_earlier(self, service: OperatorService) -> None:
        """Tasks with effectiveDueDate >= boundary included; earlier tasks excluded."""

        repo = service._repository
        q = ListTasksRepoQuery(
            due_after=datetime(2026, 4, 10, 0, 0, 0, tzinfo=UTC),
            availability=list(Availability),
        )
        result = await repo.list_tasks(q)
        task_ids = {t.id for t in result.items}
        assert "t-due-late" in task_ids  # 2026-04-20 >= 2026-04-10
        assert "t-due-early" not in task_ids  # 2026-04-01 < 2026-04-10
        assert "t-no-due" not in task_ids  # None excluded

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-completed-recent",
                name="Completed recently",
                effectiveCompletionDate="2026-04-05T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-completed-old",
                name="Completed long ago",
                effectiveCompletionDate="2026-01-01T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-not-completed",
                name="Not completed",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_completed_after_in_range_preserves_remaining(
        self, service: OperatorService
    ) -> None:
        """Lifecycle date filter is additive: remaining tasks (None) pass through."""

        repo = service._repository
        q = ListTasksRepoQuery(
            completed_after=datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC),
            availability=list(Availability),
        )
        result = await repo.list_tasks(q)
        task_ids = {t.id for t in result.items}
        assert "t-completed-recent" in task_ids  # 2026-04-05 >= 2026-03-01
        assert "t-completed-old" not in task_ids  # 2026-01-01 < 2026-03-01
        assert "t-not-completed" in task_ids  # remaining task preserved (additive)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-flagged-due",
                name="Flagged and due",
                flagged=True,
                effectiveDueDate="2026-04-05T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-flagged-no-due",
                name="Flagged no due",
                flagged=True,
                project="proj-1",
            ),
            make_task_dict(
                id="t-unflagged-due",
                name="Not flagged but due",
                effectiveDueDate="2026-04-05T10:00:00.000Z",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_date_filters_combine_with_existing(self, service: OperatorService) -> None:
        """flagged=True + due_before -> both apply (AND composition)."""

        repo = service._repository
        q = ListTasksRepoQuery(
            flagged=True,
            due_before=datetime(2026, 4, 10, 0, 0, 0, tzinfo=UTC),
            availability=list(Availability),
        )
        result = await repo.list_tasks(q)
        task_ids = {t.id for t in result.items}
        assert "t-flagged-due" in task_ids  # flagged + due before cutoff
        assert "t-flagged-no-due" not in task_ids  # flagged but None due -> excluded
        assert "t-unflagged-due" not in task_ids  # not flagged -> excluded

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-match",
                name="Match both",
                effectiveDueDate="2026-04-05T10:00:00.000Z",
                effectiveCompletionDate="2026-04-06T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-due-only",
                name="Due but not completed in range",
                effectiveDueDate="2026-04-05T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-completed-only",
                name="Completed but due too late",
                effectiveDueDate="2026-04-20T10:00:00.000Z",
                effectiveCompletionDate="2026-04-06T10:00:00.000Z",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_multiple_date_filters_and_composition(self, service: OperatorService) -> None:
        """due_before (restrictive) + completed_after (additive) -> intersection (AND).

        Lifecycle filter (completed_after) is additive: NULL completion passes through.
        Non-lifecycle filter (due_before) is restrictive: NULL due excluded.
        """

        repo = service._repository
        q = ListTasksRepoQuery(
            due_before=datetime(2026, 4, 10, 0, 0, 0, tzinfo=UTC),
            completed_after=datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC),
            availability=list(Availability),
        )
        result = await repo.list_tasks(q)
        task_ids = {t.id for t in result.items}
        assert "t-match" in task_ids  # due < 4/10 AND (completed is NULL OR >= 4/1)
        assert "t-due-only" in task_ids  # due < 4/10, NULL completion passes additive filter
        assert "t-completed-only" not in task_ids  # due >= 4/10 -> excluded by due_before


# ---------------------------------------------------------------------------
# list_tasks: date filter pipeline integration (service layer)
# ---------------------------------------------------------------------------


class TestListTasksDateFilterPipeline:
    """Pipeline resolves date filters to datetime bounds and merges lifecycle availability.

    These tests exercise the full service layer pipeline (_resolve_date_filters +
    _build_repo_query) for date filtering, verifying end-to-end behavior through
    the bridge path.
    """

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-overdue",
                name="Overdue task",
                effectiveDueDate="2020-01-15T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-future",
                name="Future task",
                effectiveDueDate="2099-06-15T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-no-due",
                name="No due date",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_due_overdue_returns_past_due_tasks(self, service: OperatorService) -> None:
        """due='overdue' returns only tasks whose effectiveDueDate is before now (RESOLVE-11)."""
        result = await service.list_tasks(ListTasksQuery(due="overdue"))
        task_ids = {t.id for t in result.items}
        assert "t-overdue" in task_ids
        assert "t-future" not in task_ids
        assert "t-no-due" not in task_ids

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-due-today",
                name="Due today",
                effectiveDueDate=datetime.now(UTC).strftime("%Y-%m-%dT15:00:00.000Z"),
                project="proj-1",
            ),
            make_task_dict(
                id="t-due-yesterday",
                name="Due yesterday",
                effectiveDueDate=(datetime.now(UTC) - timedelta(days=1)).strftime(
                    "%Y-%m-%dT10:00:00.000Z"
                ),
                project="proj-1",
            ),
            make_task_dict(
                id="t-due-tomorrow",
                name="Due tomorrow",
                effectiveDueDate=(datetime.now(UTC) + timedelta(days=1)).strftime(
                    "%Y-%m-%dT10:00:00.000Z"
                ),
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_due_today_returns_tasks_due_today(self, service: OperatorService) -> None:
        """due='today' returns only tasks due within today's date range."""
        result = await service.list_tasks(ListTasksQuery(due="today"))
        task_ids = {t.id for t in result.items}
        assert "t-due-today" in task_ids
        assert "t-due-yesterday" not in task_ids
        assert "t-due-tomorrow" not in task_ids

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-due-recent",
                name="Due recently",
                effectiveDueDate=(datetime.now(UTC) - timedelta(days=3)).strftime(
                    "%Y-%m-%dT10:00:00.000Z"
                ),
                project="proj-1",
            ),
            make_task_dict(
                id="t-due-old",
                name="Due long ago",
                effectiveDueDate="2020-01-01T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-due-future",
                name="Due in future",
                effectiveDueDate="2099-06-15T10:00:00.000Z",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_due_last_1w_returns_tasks_due_in_last_week(
        self, service: OperatorService
    ) -> None:
        """due={last: '1w'} returns tasks due in the last 7 days."""
        result = await service.list_tasks(ListTasksQuery(due={"last": "1w"}))
        task_ids = {t.id for t in result.items}
        assert "t-due-recent" in task_ids  # 3 days ago is within last week
        assert "t-due-old" not in task_ids  # 2020 is way outside
        assert "t-due-future" not in task_ids  # future is after now

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-completed-today",
                name="Completed today",
                status="Completed",
                completionDate=datetime.now(UTC).strftime("%Y-%m-%dT09:00:00.000Z"),
                effectiveCompletionDate=datetime.now(UTC).strftime("%Y-%m-%dT09:00:00.000Z"),
                project="proj-1",
            ),
            make_task_dict(
                id="t-completed-old",
                name="Completed long ago",
                status="Completed",
                completionDate="2020-01-01T09:00:00.000Z",
                effectiveCompletionDate="2020-01-01T09:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-available",
                name="Available task",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_completed_today_auto_includes_completed_availability(
        self, service: OperatorService
    ) -> None:
        """completed='today' auto-includes Availability.COMPLETED (EXEC-03).

        Default availability is [available, blocked] which excludes completed tasks.
        The pipeline should auto-add 'completed' to the availability list.
        Lifecycle date filter is additive: remaining tasks (NULL completion) pass through.
        """
        result = await service.list_tasks(ListTasksQuery(completed="today"))
        task_ids = {t.id for t in result.items}
        assert "t-completed-today" in task_ids
        assert "t-completed-old" not in task_ids  # completed outside today
        assert "t-available" in task_ids  # remaining task preserved (additive lifecycle filter)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-dropped-recent",
                name="Dropped recently",
                status="Dropped",
                dropDate=(datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%dT10:00:00.000Z"),
                effectiveDropDate=(datetime.now(UTC) - timedelta(days=2)).strftime(
                    "%Y-%m-%dT10:00:00.000Z"
                ),
                project="proj-1",
            ),
            make_task_dict(
                id="t-dropped-old",
                name="Dropped long ago",
                status="Dropped",
                dropDate="2020-01-01T10:00:00.000Z",
                effectiveDropDate="2020-01-01T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-available",
                name="Available task",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_dropped_last_1w_auto_includes_dropped_availability(
        self, service: OperatorService
    ) -> None:
        """dropped={last: '1w'} auto-includes Availability.DROPPED (EXEC-04).

        Lifecycle date filter is additive: remaining tasks (NULL drop date) pass through.
        """
        result = await service.list_tasks(ListTasksQuery(dropped={"last": "1w"}))
        task_ids = {t.id for t in result.items}
        assert "t-dropped-recent" in task_ids  # dropped 2 days ago, within last week
        assert "t-dropped-old" not in task_ids  # dropped in 2020
        assert "t-available" in task_ids  # remaining task preserved (additive lifecycle filter)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-completed-old",
                name="Completed long ago",
                status="Completed",
                completionDate="2020-01-01T09:00:00.000Z",
                effectiveCompletionDate="2020-01-01T09:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-completed-recent",
                name="Completed recently",
                status="Completed",
                completionDate=datetime.now(UTC).strftime("%Y-%m-%dT09:00:00.000Z"),
                effectiveCompletionDate=datetime.now(UTC).strftime("%Y-%m-%dT09:00:00.000Z"),
                project="proj-1",
            ),
            make_task_dict(
                id="t-available",
                name="Available task",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_completed_all_returns_all_completed_regardless_of_date(
        self, service: OperatorService
    ) -> None:
        """completed='all' adds lifecycle availability -- completed tasks appear (EXEC-05).

        "all" expands availability to include 'completed' but sets no date bounds.
        Available tasks remain visible (default availability unchanged).
        """
        result = await service.list_tasks(ListTasksQuery(completed="all"))
        task_ids = {t.id for t in result.items}
        # Both completed tasks visible regardless of completion date
        assert "t-completed-old" in task_ids
        assert "t-completed-recent" in task_ids
        # Available task still visible (default availability includes 'available')
        assert "t-available" in task_ids

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-dropped-old",
                name="Dropped long ago",
                status="Dropped",
                dropDate="2020-01-01T10:00:00.000Z",
                effectiveDropDate="2020-01-01T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-dropped-recent",
                name="Dropped recently",
                status="Dropped",
                dropDate=datetime.now(UTC).strftime("%Y-%m-%dT10:00:00.000Z"),
                effectiveDropDate=datetime.now(UTC).strftime("%Y-%m-%dT10:00:00.000Z"),
                project="proj-1",
            ),
            make_task_dict(
                id="t-available",
                name="Available task",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_dropped_all_returns_all_dropped_regardless_of_date(
        self, service: OperatorService
    ) -> None:
        """dropped='all' adds lifecycle availability -- dropped tasks appear (EXEC-06).

        "all" expands availability to include 'dropped' but sets no date bounds.
        Available tasks remain visible (default availability unchanged).
        """
        result = await service.list_tasks(ListTasksQuery(dropped="all"))
        task_ids = {t.id for t in result.items}
        assert "t-dropped-old" in task_ids
        assert "t-dropped-recent" in task_ids
        # Available task still visible (default availability includes 'available')
        assert "t-available" in task_ids

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-completed",
                name="Completed task",
                status="Completed",
                completionDate="2020-06-01T09:00:00.000Z",
                effectiveCompletionDate="2020-06-01T09:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-available",
                name="Available task",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_completed_all_with_empty_availability_only_completed(
        self, service: OperatorService
    ) -> None:
        """completed='all' + availability=[] returns only completed tasks."""
        result = await service.list_tasks(
            ListTasksQuery(
                completed="all",
                availability=[],
            )
        )
        task_ids = {t.id for t in result.items}
        assert "t-completed" in task_ids
        assert "t-available" not in task_ids

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-no-due",
                name="No due date",
                project="proj-1",
            ),
            make_task_dict(
                id="t-with-due",
                name="Has due date",
                effectiveDueDate="2020-06-15T10:00:00.000Z",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_null_effective_dates_excluded_from_date_filters(
        self, service: OperatorService
    ) -> None:
        """Tasks with NULL effective dates are excluded from date filter results (EXEC-07)."""
        result = await service.list_tasks(ListTasksQuery(due="overdue"))
        task_ids = {t.id for t in result.items}
        assert "t-with-due" in task_ids  # has a due date in 2020 (before now)
        assert "t-no-due" not in task_ids  # NULL excluded

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-flagged-overdue",
                name="Flagged and overdue",
                flagged=True,
                effectiveDueDate="2020-06-15T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-unflagged-overdue",
                name="Not flagged but overdue",
                effectiveDueDate="2020-06-15T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-flagged-future",
                name="Flagged but future",
                flagged=True,
                effectiveDueDate="2099-06-15T10:00:00.000Z",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_date_and_base_filters_compose_with_and(self, service: OperatorService) -> None:
        """due='overdue' + flagged=True returns intersection (EXEC-09)."""
        result = await service.list_tasks(ListTasksQuery(due="overdue", flagged=True))
        task_ids = {t.id for t in result.items}
        assert "t-flagged-overdue" in task_ids
        assert "t-unflagged-overdue" not in task_ids
        assert "t-flagged-future" not in task_ids

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-in-range",
                name="In range",
                effectiveDueDate="2026-04-07T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-before-range",
                name="Before range",
                effectiveDueDate="2026-03-01T10:00:00.000Z",
                project="proj-1",
            ),
            make_task_dict(
                id="t-after-range",
                name="After range",
                effectiveDueDate="2026-04-20T10:00:00.000Z",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_due_absolute_range_returns_tasks_in_range(
        self, service: OperatorService
    ) -> None:
        """due={after: '2026-04-01', before: '2026-04-14'} returns tasks in range."""
        result = await service.list_tasks(
            ListTasksQuery(due={"after": "2026-04-01", "before": "2026-04-14"})
        )
        task_ids = {t.id for t in result.items}
        assert "t-in-range" in task_ids  # 2026-04-07 is within [04-01, 04-15)
        assert "t-before-range" not in task_ids  # 2026-03-01 is before 04-01
        assert "t-after-range" not in task_ids  # 2026-04-20 is after 04-15

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-due-today",
                name="Due today",
                effectiveDueDate=datetime.now(UTC).strftime("%Y-%m-%dT15:00:00.000Z"),
                project="proj-1",
            ),
            make_task_dict(
                id="t-due-tomorrow",
                name="Due tomorrow",
                effectiveDueDate=(datetime.now(UTC) + timedelta(days=1)).strftime(
                    "%Y-%m-%dT10:00:00.000Z"
                ),
                project="proj-1",
            ),
            make_task_dict(
                id="t-overdue",
                name="Overdue task",
                effectiveDueDate="2020-01-15T10:00:00.000Z",
                project="proj-1",
            ),
        ],
        projects=[make_project_dict(id="proj-1", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_due_soon_uses_preferences_default_two_days(
        self, service: OperatorService
    ) -> None:
        """due='soon' uses OmniFocusPreferences factory default (TWO_DAYS).

        With default InMemoryBridge settings, OmniFocusPreferences returns
        TWO_DAYS (OmniFocus factory default). "soon" means after=None (no lower
        bound) + before=midnight+2days, so overdue tasks are also included.
        """
        result = await service.list_tasks(ListTasksQuery(due="soon"))
        task_ids = {t.id for t in result.items}
        # TWO_DAYS bounds: today, tomorrow, and overdue all match (after=None)
        assert "t-due-today" in task_ids
        assert "t-due-tomorrow" in task_ids
        assert "t-overdue" in task_ids


# ---------------------------------------------------------------------------
# list_projects: date filter pipeline integration (service layer)
# ---------------------------------------------------------------------------


class TestListProjectsDateFiltering:
    """Pipeline resolves date filters to datetime bounds for list_projects.

    Verifies end-to-end behavior through the service layer pipeline
    (_resolve_date_filters + _build_repo_query) for project date filtering.
    """

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(
                id="proj-due-soon",
                name="Due soon project",
                dueDate="2026-04-08T10:00:00.000Z",
            ),
            make_project_dict(
                id="proj-due-later",
                name="Due later project",
                dueDate="2026-04-20T10:00:00.000Z",
            ),
            make_project_dict(
                id="proj-no-due",
                name="No due date project",
            ),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_due_absolute_range_filters_projects(self, service: OperatorService) -> None:
        """due={after: ..., before: ...} filters projects by date range."""
        result = await service.list_projects(
            ListProjectsQuery(due={"after": "2026-04-01", "before": "2026-04-14"})
        )
        result_proj_id_set = {p.id for p in result.items}
        assert "proj-due-soon" in result_proj_id_set  # 2026-04-08 in range
        assert "proj-due-later" not in result_proj_id_set  # 2026-04-20 after range
        assert "proj-no-due" not in result_proj_id_set  # NULL excluded

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(
                id="proj-completed-today",
                name="Completed today",
                status="Active",
                taskStatus="Completed",
                completionDate=datetime.now(UTC).strftime("%Y-%m-%dT09:00:00.000Z"),
                effectiveCompletionDate=datetime.now(UTC).strftime("%Y-%m-%dT09:00:00.000Z"),
            ),
            make_project_dict(
                id="proj-completed-old",
                name="Completed long ago",
                status="Active",
                taskStatus="Completed",
                completionDate="2020-01-01T09:00:00.000Z",
                effectiveCompletionDate="2020-01-01T09:00:00.000Z",
            ),
            make_project_dict(
                id="proj-available",
                name="Available project",
            ),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_completed_today_auto_includes_completed_availability(
        self, service: OperatorService
    ) -> None:
        """completed='today' auto-includes Availability.COMPLETED for projects.

        Default availability is [available, blocked] which excludes completed projects.
        The pipeline should auto-add 'completed' to the availability list.
        Lifecycle date filter is additive: remaining projects (NULL completion) pass through.
        """
        result = await service.list_projects(ListProjectsQuery(completed="today"))
        result_proj_id_set = {p.id for p in result.items}
        assert "proj-completed-today" in result_proj_id_set
        assert "proj-completed-old" not in result_proj_id_set  # completed outside today
        assert "proj-available" in result_proj_id_set  # remaining project preserved (additive)

    @pytest.mark.snapshot(
        tasks=[],
        projects=[
            make_project_dict(
                id="proj-completed-old",
                name="Completed long ago",
                status="Active",
                taskStatus="Completed",
                completionDate="2020-06-01T09:00:00.000Z",
                effectiveCompletionDate="2020-06-01T09:00:00.000Z",
            ),
            make_project_dict(
                id="proj-completed-recent",
                name="Completed recently",
                status="Active",
                taskStatus="Completed",
                completionDate=datetime.now(UTC).strftime("%Y-%m-%dT09:00:00.000Z"),
                effectiveCompletionDate=datetime.now(UTC).strftime("%Y-%m-%dT09:00:00.000Z"),
            ),
            make_project_dict(
                id="proj-available",
                name="Available project",
            ),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_completed_all_returns_all_completed_regardless_of_date(
        self, service: OperatorService
    ) -> None:
        """completed='all' adds lifecycle availability -- all completed projects appear."""
        result = await service.list_projects(ListProjectsQuery(completed="all"))
        result_proj_id_set = {p.id for p in result.items}
        assert "proj-completed-old" in result_proj_id_set
        assert "proj-completed-recent" in result_proj_id_set
        assert (
            "proj-available" in result_proj_id_set
        )  # default availability still includes available


# ---------------------------------------------------------------------------
# Phase 57-02: parent filter pipeline tests
# ---------------------------------------------------------------------------
#
# Shared shape: tasks wired by `parent="<task-id>"` form a parent-child chain
# in the raw bridge format (see tests/conftest.py::make_task_dict). The
# repository adapter turns those into `parent.task.id` references, which
# service/subtree.py::expand_scope walks for subtree collection.


class TestListTasksParentFilter:
    """PARENT-01..06 pipeline coverage for ``list_tasks(parent=...)``."""

    @pytest.mark.snapshot(
        tasks=[
            # Anchor task with two children under proj-work.
            make_task_dict(id="anchor", name="Review Q3", project="proj-work", inInbox=False),
            make_task_dict(
                id="child-1",
                name="Draft section 1",
                project="proj-work",
                parent="anchor",
                inInbox=False,
            ),
            make_task_dict(
                id="child-2",
                name="Draft section 2",
                project="proj-work",
                parent="anchor",
                inInbox=False,
            ),
            # Unrelated sibling at project root.
            make_task_dict(id="unrelated", name="Other task", project="proj-work", inInbox=False),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_filter_by_task_name(self, service: OperatorService) -> None:
        """PARENT-01/04: resolving by task name returns anchor + descendants."""
        result = await service.list_tasks(ListTasksQuery(parent="Review Q3"))
        ids = {t.id for t in result.items}
        assert ids == {"anchor", "child-1", "child-2"}

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="anchor", name="Review Q3", project="proj-work", inInbox=False),
            make_task_dict(
                id="child-1",
                name="Draft section 1",
                project="proj-work",
                parent="anchor",
                inInbox=False,
            ),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_filter_by_task_id(self, service: OperatorService) -> None:
        """PARENT-01: resolving by task ID returns the same result as by name."""
        result = await service.list_tasks(ListTasksQuery(parent="anchor"))
        ids = {t.id for t in result.items}
        assert ids == {"anchor", "child-1"}

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="A", project="proj-work", inInbox=False),
            make_task_dict(id="t2", name="B", project="proj-work", inInbox=False),
            make_task_dict(id="t3", name="Inbox only"),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_filter_by_project_name(self, service: OperatorService) -> None:
        """PARENT-04: project-resolved ref returns project tasks WITHOUT the project ID."""
        result = await service.list_tasks(ListTasksQuery(parent="Work"))
        ids = {t.id for t in result.items}
        # Only tasks under the project appear; project ID itself is never a row.
        assert ids == {"t1", "t2"}
        assert "proj-work" not in ids

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="top", name="Top anchor", project="proj-work", inInbox=False),
            make_task_dict(
                id="mid",
                name="Middle",
                project="proj-work",
                parent="top",
                inInbox=False,
            ),
            make_task_dict(
                id="leaf",
                name="Leaf",
                project="proj-work",
                parent="mid",
                inInbox=False,
            ),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_filter_includes_deep_descendants(
        self, service: OperatorService
    ) -> None:
        """PARENT-03: descendants at any depth are included."""
        result = await service.list_tasks(ListTasksQuery(parent="Top anchor"))
        ids = {t.id for t in result.items}
        assert ids == {"top", "mid", "leaf"}

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Something", project="proj-work", inInbox=False),
        ],
        projects=[make_project_dict(id="proj-work", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_filter_no_match(self, service: OperatorService) -> None:
        """No-match: filter is skipped + FILTER_NO_MATCH-style warning."""
        result = await service.list_tasks(ListTasksQuery(parent="NoSuchThing"))
        # Filter skipped -> full result set returned.
        assert {t.id for t in result.items} == {"t1"}
        assert result.warnings is not None
        assert any("NoSuchThing" in w for w in result.warnings)
        assert any("skipped" in w.lower() for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            # Two tasks that both contain "Review" as a substring of their name.
            make_task_dict(
                id="task-review-a", name="Review Q3 plan", project="proj-work", inInbox=False
            ),
            make_task_dict(
                id="task-review-b",
                name="Review Q4 plan",
                project="proj-work",
                inInbox=False,
            ),
            # Child under task-review-a to prove union-of-subtrees.
            make_task_dict(
                id="child-a",
                name="Child of A",
                project="proj-work",
                parent="task-review-a",
                inInbox=False,
            ),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_multi_match_warning(self, service: OperatorService) -> None:
        """WARN-05 reuse: multi-match warning fires; subtrees are unioned."""
        result = await service.list_tasks(ListTasksQuery(parent="Review"))
        ids = {t.id for t in result.items}
        # Both anchors + child-a.
        assert ids == {"task-review-a", "task-review-b", "child-a"}
        assert result.warnings is not None
        assert any("task-review-a" in w and "task-review-b" in w for w in result.warnings)
        assert any("filter by ID" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-inbox", name="Inbox task"),
            make_task_dict(id="t-project", name="Project task", project="proj-work", inInbox=False),
        ],
        projects=[make_project_dict(id="proj-work", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_inbox_sentinel_equivalence(
        self, service: OperatorService
    ) -> None:
        """PARENT-07: parent='$inbox' produces byte-identical results to project='$inbox'."""
        result_parent = await service.list_tasks(ListTasksQuery(parent="$inbox"))
        result_project = await service.list_tasks(ListTasksQuery(project="$inbox"))

        dump_parent = [t.model_dump(mode="json", by_alias=True) for t in result_parent.items]
        dump_project = [t.model_dump(mode="json", by_alias=True) for t in result_project.items]
        assert dump_parent == dump_project
        assert result_parent.total == result_project.total
        assert result_parent.has_more == result_project.has_more

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t-inbox", name="Inbox task"),
        ],
        projects=[],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_inbox_with_in_inbox_false_raises(
        self, service: OperatorService
    ) -> None:
        """PARENT-08: parent='$inbox' + inInbox=false raises CONTRADICTORY_INBOX_FALSE."""
        with pytest.raises(ValueError, match=r"Contradictory filters"):
            await service.list_tasks(ListTasksQuery(parent="$inbox", in_inbox=False))

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t-project", name="Project task", project="proj-inbox", inInbox=False
            ),
        ],
        projects=[make_project_dict(id="proj-inbox", name="inbox style")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_inbox_name_substring_warning(
        self, service: OperatorService
    ) -> None:
        """WARN-05 reuse: parent='inb' (substring of Inbox) emits LIST_TASKS_INBOX_PROJECT_WARNING.

        The reused warning text says 'project="..."' -- documented agent-UX wart
        per D-14; the warning text is not parent-specific.
        """
        result = await service.list_tasks(ListTasksQuery(parent="inb"))
        assert result.warnings is not None
        assert any('project="inb"' in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            # Parent anchor has 3 children under proj-work. Two of them have tag 'Urgent'.
            make_task_dict(id="anchor", name="Big feature", project="proj-work", inInbox=False),
            make_task_dict(
                id="c1",
                name="Step 1",
                project="proj-work",
                parent="anchor",
                tags=[{"id": "tag-urgent", "name": "Urgent"}],
                inInbox=False,
            ),
            make_task_dict(
                id="c2",
                name="Step 2",
                project="proj-work",
                parent="anchor",
                inInbox=False,
            ),
            make_task_dict(
                id="c3",
                name="Step 3",
                project="proj-work",
                parent="anchor",
                tags=[{"id": "tag-urgent", "name": "Urgent"}],
                inInbox=False,
            ),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[make_tag_dict(id="tag-urgent", name="Urgent")],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_and_tags_filter_and_composition(
        self, service: OperatorService
    ) -> None:
        """PARENT-05: parent AND-composes with tags via scope-set intersection."""
        result = await service.list_tasks(ListTasksQuery(parent="Big feature", tags=["Urgent"]))
        assert {t.id for t in result.items} == {"c1", "c3"}

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Task A", project="proj-work", inInbox=False),
            make_task_dict(id="t2", name="Task B", project="proj-work", inInbox=False),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_resolves_to_project_warning(
        self, service: OperatorService
    ) -> None:
        """WARN-02: all resolved matches are projects -> PARENT_RESOLVES_TO_PROJECT fires."""
        result = await service.list_tasks(ListTasksQuery(parent="Work Projects"))
        assert result.warnings is not None
        assert any(
            "resolved only to projects" in w and 'parent="Work Projects"' in w
            for w in result.warnings
        )

    @pytest.mark.snapshot(
        tasks=[
            # A task whose name contains the project's name -- mixed match.
            make_task_dict(id="task-mix", name="Work review", project="proj-work", inInbox=False),
            make_task_dict(id="other", name="Other", project="proj-work", inInbox=False),
        ],
        projects=[make_project_dict(id="proj-work", name="Work")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_resolves_mixed_no_project_warning(
        self, service: OperatorService
    ) -> None:
        """WARN-02 negative: mixed project+task matches -> WARN-02 does NOT fire."""
        result = await service.list_tasks(ListTasksQuery(parent="Work"))
        if result.warnings is not None:
            assert not any("resolved only to projects" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="anchor", name="Big anchor", project="proj-work", inInbox=False),
            *[
                make_task_dict(
                    id=f"c{i}",
                    name=f"child {i}",
                    project="proj-work",
                    parent="anchor",
                    inInbox=False,
                )
                for i in range(1, 20)
            ],
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_pagination(self, service: OperatorService) -> None:
        """PARENT-06: subtree result paginates correctly (limit + offset)."""
        result = await service.list_tasks(ListTasksQuery(parent="Big anchor", limit=5, offset=10))
        assert len(result.items) == 5
        assert result.has_more is True

    @pytest.mark.snapshot(
        tasks=[
            # Task under proj-1 AND child of parent-anchor under proj-2 is structurally
            # impossible, so we verify intersection via: task X is under proj-1 AND
            # matches the parent-anchor subtree (which is also under proj-1).
            make_task_dict(id="anchor", name="Parent anchor", project="proj-1", inInbox=False),
            make_task_dict(
                id="in-both",
                name="Under both",
                project="proj-1",
                parent="anchor",
                inInbox=False,
            ),
            make_task_dict(
                id="not-in-subtree", name="Project only", project="proj-1", inInbox=False
            ),
            make_task_dict(
                id="wrong-project", name="Other project", project="proj-2", inInbox=False
            ),
        ],
        projects=[
            make_project_dict(id="proj-1", name="Primary"),
            make_project_dict(id="proj-2", name="Secondary"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_list_tasks_parent_and_project_intersection(
        self, service: OperatorService
    ) -> None:
        """D-05: project_scope ∩ parent_scope produces the AND-composed task set."""
        result = await service.list_tasks(ListTasksQuery(project="Primary", parent="Parent anchor"))
        # parent subtree = {anchor, in-both}; project scope = {anchor, in-both, not-in-subtree}
        # intersection = {anchor, in-both}.
        assert {t.id for t in result.items} == {"anchor", "in-both"}


class TestListTasksParentProjectEquivalence:
    """UNIFY-02 / D-15: cross-filter equivalence contract gate."""

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Task one", project="proj-work", inInbox=False),
            make_task_dict(id="t2", name="Task two", project="proj-work", inInbox=False),
            make_task_dict(id="unrelated", name="Unrelated", project="proj-other", inInbox=False),
        ],
        projects=[
            make_project_dict(id="proj-work", name="Work Projects"),
            make_project_dict(id="proj-other", name="Other"),
        ],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_parent_and_project_byte_identical_for_same_project(
        self, service: OperatorService
    ) -> None:
        """list_tasks(project='Work Projects') == list_tasks(parent='Work Projects')
        byte-identically when the value resolves to the same project. This is the
        UNIFY-02 / D-15 contract gate -- the load-bearing proof that the
        unification architecture works end-to-end."""
        project_result = await service.list_tasks(ListTasksQuery(project="Work Projects"))
        parent_result = await service.list_tasks(ListTasksQuery(parent="Work Projects"))

        project_dump = [t.model_dump(mode="json", by_alias=True) for t in project_result.items]
        parent_dump = [t.model_dump(mode="json", by_alias=True) for t in parent_result.items]

        # WARN-02 fires only on the parent path -- strip warnings from the byte
        # comparison since they're not part of the task list shape. The contract
        # under D-15 is that the task payload itself is byte-identical; the
        # parent-only warning surface is an orthogonal concern.
        assert project_dump == parent_dump
        assert project_result.total == parent_result.total
        assert project_result.has_more == parent_result.has_more


# ---------------------------------------------------------------------------
# Pipeline-level cross-filter warnings (WARN-01 FILTERED_SUBTREE,
# WARN-03 PARENT_PROJECT_COMBINED, Phase 57-03)
#
# These fire from _ListTasksPipeline.execute after all resolutions and before
# _delegate. The domain methods (check_filtered_subtree,
# check_parent_project_combined) own the trigger logic; this test surface
# proves the emission site is wired in and correct.
# ---------------------------------------------------------------------------


def _warnings_list(warnings: list[str] | None) -> list[str]:
    """Normalize result.warnings (may be None) into a list for in-checks."""
    return warnings or []


class TestListTasksFilteredSubtreeWarning:
    """WARN-01 pipeline emission: scope filter + other dimensional filter."""

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Task", project="proj-work", inInbox=False)],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_filtered_subtree_warning_project_only_no_other(
        self, service: OperatorService
    ) -> None:
        """project alone (no other dim filter) -> WARN-01 does NOT fire."""
        result = await service.list_tasks(ListTasksQuery(project="Work"))
        assert FILTERED_SUBTREE_WARNING not in _warnings_list(result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="anchor", name="Review", project="proj-work", inInbox=False),
            make_task_dict(
                id="child", name="Draft", project="proj-work", parent="anchor", inInbox=False
            ),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_filtered_subtree_warning_parent_only_no_other(
        self, service: OperatorService
    ) -> None:
        """parent alone (no other dim filter) -> WARN-01 does NOT fire."""
        result = await service.list_tasks(ListTasksQuery(parent="Review"))
        assert FILTERED_SUBTREE_WARNING not in _warnings_list(result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Task", project="proj-work", flagged=True, inInbox=False),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_filtered_subtree_warning_project_and_flagged(
        self, service: OperatorService
    ) -> None:
        """project + flagged -> WARN-01 fires EXACTLY ONCE."""
        result = await service.list_tasks(ListTasksQuery(project="Work", flagged=True))
        warnings = _warnings_list(result.warnings)
        assert warnings.count(FILTERED_SUBTREE_WARNING) == 1

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="anchor",
                name="Review",
                project="proj-work",
                tags=[{"id": "tag-1", "name": "Urgent"}],
                inInbox=False,
            ),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[make_tag_dict(id="tag-1", name="Urgent")],
        folders=[],
        perspectives=[],
    )
    async def test_filtered_subtree_warning_parent_and_tags(self, service: OperatorService) -> None:
        """parent + tags -> WARN-01 fires EXACTLY ONCE."""
        result = await service.list_tasks(ListTasksQuery(parent="Review", tags=["Urgent"]))
        warnings = _warnings_list(result.warnings)
        assert warnings.count(FILTERED_SUBTREE_WARNING) == 1

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="anchor",
                name="Review",
                project="proj-work",
                dueDate="2020-01-01T12:00:00.000Z",
                inInbox=False,
            ),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_filtered_subtree_warning_parent_and_due_filter(
        self, service: OperatorService
    ) -> None:
        """parent + due filter -> WARN-01 fires EXACTLY ONCE (date dim counts)."""
        result = await service.list_tasks(ListTasksQuery(parent="Review", due="overdue"))
        warnings = _warnings_list(result.warnings)
        assert warnings.count(FILTERED_SUBTREE_WARNING) == 1

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Task", project="proj-work", inInbox=False)],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_filtered_subtree_warning_availability_only_does_not_fire(
        self, service: OperatorService
    ) -> None:
        """project + non-default availability -> WARN-01 does NOT fire (D-13).

        availability is excluded from the "other filter" predicate because its
        default is non-empty. Including it would make the warning fire on every
        scope-filtered query, destroying signal.
        """
        result = await service.list_tasks(
            ListTasksQuery(project="Work", availability=[AvailabilityFilter.AVAILABLE])
        )
        assert FILTERED_SUBTREE_WARNING not in _warnings_list(result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="t1", name="Task", project="proj-work", flagged=True, inInbox=False),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_filtered_subtree_warning_no_scope_only_dimensional(
        self, service: OperatorService
    ) -> None:
        """flagged alone (no scope filter) -> WARN-01 does NOT fire."""
        result = await service.list_tasks(ListTasksQuery(flagged=True))
        assert FILTERED_SUBTREE_WARNING not in _warnings_list(result.warnings)


class TestListTasksParentProjectCombinedWarning:
    """WARN-03 pipeline emission: both project AND parent set."""

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Task", project="proj-work", inInbox=False)],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_parent_project_combined_project_only(self, service: OperatorService) -> None:
        """project only -> WARN-03 does NOT fire."""
        result = await service.list_tasks(ListTasksQuery(project="Work"))
        assert PARENT_PROJECT_COMBINED_WARNING not in _warnings_list(result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="anchor", name="Review", project="proj-work", inInbox=False),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_parent_project_combined_parent_only(self, service: OperatorService) -> None:
        """parent only -> WARN-03 does NOT fire."""
        result = await service.list_tasks(ListTasksQuery(parent="Review"))
        assert PARENT_PROJECT_COMBINED_WARNING not in _warnings_list(result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="anchor", name="Review", project="proj-work", inInbox=False),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_parent_project_combined_both_set_fires(self, service: OperatorService) -> None:
        """project + parent -> WARN-03 fires EXACTLY ONCE."""
        result = await service.list_tasks(ListTasksQuery(project="Work", parent="Review"))
        warnings = _warnings_list(result.warnings)
        assert warnings.count(PARENT_PROJECT_COMBINED_WARNING) == 1

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="anchor", name="X", project="proj-x", inInbox=False),
        ],
        projects=[make_project_dict(id="proj-x", name="X")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_parent_project_combined_both_same_value_still_fires(
        self, service: OperatorService
    ) -> None:
        """project='X' + parent='X' -> WARN-03 fires (D-13: presence-based)."""
        result = await service.list_tasks(ListTasksQuery(project="X", parent="X"))
        warnings = _warnings_list(result.warnings)
        assert warnings.count(PARENT_PROJECT_COMBINED_WARNING) == 1


class TestListTasksCrossFilterWarningsTogether:
    """Co-occurrence gate: both warnings fire together without interference."""

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="anchor",
                name="Review",
                project="proj-work",
                flagged=True,
                inInbox=False,
            ),
        ],
        projects=[make_project_dict(id="proj-work", name="Work Projects")],
        tags=[],
        folders=[],
        perspectives=[],
    )
    async def test_both_warnings_together(self, service: OperatorService) -> None:
        """project + parent + flagged -> both WARN-01 and WARN-03 fire (each once).

        FILTERED_SUBTREE fires ONCE even though both scope filters are set
        (scope predicate is OR -- single-element return). PARENT_PROJECT_COMBINED
        fires because both project and parent are present.
        """
        result = await service.list_tasks(
            ListTasksQuery(project="Work", parent="Review", flagged=True)
        )
        warnings = _warnings_list(result.warnings)
        assert warnings.count(FILTERED_SUBTREE_WARNING) == 1
        assert warnings.count(PARENT_PROJECT_COMBINED_WARNING) == 1
