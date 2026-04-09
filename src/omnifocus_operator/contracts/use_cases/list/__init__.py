"""List-entity contracts: query models, repo queries, and result containers.

Re-exports all public names from submodules for convenient imports.
"""

from omnifocus_operator.contracts.use_cases.list._date_filter import DateFilter
from omnifocus_operator.contracts.use_cases.list._enums import (
    AvailabilityFilter,
    DueDateShortcut,
    FolderAvailabilityFilter,
    LifecycleDateShortcut,
    TagAvailabilityFilter,
)
from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult, ListResult
from omnifocus_operator.contracts.use_cases.list.folders import (
    ListFoldersQuery,
    ListFoldersRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.perspectives import (
    ListPerspectivesQuery,
    ListPerspectivesRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.projects import (
    ListProjectsQuery,
    ListProjectsRepoQuery,
    ReviewDueFilter,
)
from omnifocus_operator.contracts.use_cases.list.tags import (
    ListTagsQuery,
    ListTagsRepoQuery,
)
from omnifocus_operator.contracts.use_cases.list.tasks import (
    ListTasksQuery,
    ListTasksRepoQuery,
)

__all__ = [
    "AvailabilityFilter",
    "DateFilter",
    "DueDateShortcut",
    "FolderAvailabilityFilter",
    "LifecycleDateShortcut",
    "ListFoldersQuery",
    "ListFoldersRepoQuery",
    "ListPerspectivesQuery",
    "ListPerspectivesRepoQuery",
    "ListProjectsQuery",
    "ListProjectsRepoQuery",
    "ListRepoResult",
    "ListResult",
    "ListTagsQuery",
    "ListTagsRepoQuery",
    "ListTasksQuery",
    "ListTasksRepoQuery",
    "ReviewDueFilter",
    "TagAvailabilityFilter",
]
