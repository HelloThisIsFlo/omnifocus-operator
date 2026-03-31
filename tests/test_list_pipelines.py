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

from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersQuery
from omnifocus_operator.contracts.use_cases.list.projects import (
    DurationUnit,
    ListProjectsQuery,
    ReviewDueFilter,
)
from omnifocus_operator.contracts.use_cases.list.tags import ListTagsQuery
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksQuery
from omnifocus_operator.service.service import _ListProjectsPipeline

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


# ---------------------------------------------------------------------------
# list_projects: name resolution
# ---------------------------------------------------------------------------


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
        result = await service.list_perspectives()
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
        result = await service.list_perspectives()
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
